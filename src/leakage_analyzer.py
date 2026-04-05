"""
Revenue Leakage Analyzer
Core analysis engine: silent churn, deterioration, discount abuse, payment anomalies,
concentration risk, and composite leakage scoring.
"""
import pandas as pd
import numpy as np


def _require_columns(df, required_cols, context):
    """Fail fast when required columns are missing."""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"{context}: colunas obrigatórias em falta: {missing_str}")


# ---------------------------------------------------------------------------
# 1. Silent Churn Detection
# ---------------------------------------------------------------------------

def detect_silent_churn(revenue_df, lookback=3, engagement_threshold=30):
    """
    Identify customers showing pre-churn signals:
    - Engagement declining over lookback months
    - Low absolute engagement
    - Still paying but disengaging
    """
    _require_columns(
        revenue_df,
        ["customer_id", "month", "engagement_score", "mrr_billed"],
        "detect_silent_churn",
    )
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values(["customer_id", "month"])

    # Calculate engagement trend per customer (slope over recent months)
    latest_months = df["month"].drop_duplicates().nlargest(lookback).tolist()
    recent = df[df["month"].isin(latest_months)]

    engagement_trend = (
        recent.groupby("customer_id")
        .apply(lambda g: _slope(g["engagement_score"]), include_groups=False)
        .reset_index()
        .rename(columns={0: "engagement_slope"})
    )

    latest = recent.groupby("customer_id").agg(
        avg_engagement=("engagement_score", "mean"),
        avg_mrr=("mrr_billed", "mean"),
    ).reset_index()

    result = latest.merge(engagement_trend, on="customer_id")
    result["silent_churn_risk"] = (
        (result["engagement_slope"] < -2) &
        (result["avg_engagement"] < engagement_threshold)
    )
    result["risk_score_churn"] = np.clip(
        (engagement_threshold - result["avg_engagement"]) / engagement_threshold * 50 +
        np.abs(np.minimum(result["engagement_slope"], 0)) * 5,
        0, 100
    ).round(1)

    return result


def _slope(series):
    """Simple linear slope over a series."""
    if len(series) < 2:
        return 0
    x = np.arange(len(series))
    coeffs = np.polyfit(x, series.values, 1)
    return round(coeffs[0], 3)


# ---------------------------------------------------------------------------
# 2. Gradual Deterioration
# ---------------------------------------------------------------------------

def detect_deterioration(revenue_df, min_months=6):
    """
    Identify customers with sustained MRR decline (not just seasonal dips).
    Uses 3-month rolling average to smooth noise.
    """
    _require_columns(
        revenue_df,
        ["customer_id", "month", "mrr_billed"],
        "detect_deterioration",
    )
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values(["customer_id", "month"])

    # Rolling average per customer
    df["mrr_rolling3"] = (
        df.groupby("customer_id")["mrr_billed"]
        .transform(lambda x: x.rolling(3, min_periods=2).mean())
    )

    # Compare first half vs second half of each customer's history
    cust_stats = []
    for cid, grp in df.groupby("customer_id"):
        if len(grp) < min_months:
            continue
        mid = len(grp) // 2
        first_half_avg = grp.iloc[:mid]["mrr_billed"].mean()
        second_half_avg = grp.iloc[mid:]["mrr_billed"].mean()

        if first_half_avg > 0:
            change_pct = (second_half_avg - first_half_avg) / first_half_avg * 100
        else:
            change_pct = 0

        # Trend slope
        slope = _slope(grp["mrr_rolling3"].dropna())

        cust_stats.append({
            "customer_id": cid,
            "mrr_first_half": round(first_half_avg, 2),
            "mrr_second_half": round(second_half_avg, 2),
            "mrr_change_pct": round(change_pct, 1),
            "mrr_trend_slope": slope,
            "is_deteriorating": change_pct < -10 and slope < 0,
            "risk_score_deterioration": round(np.clip(abs(min(change_pct, 0)) * 1.5, 0, 100), 1),
        })

    return pd.DataFrame(cust_stats)


# ---------------------------------------------------------------------------
# 3. Discount Abuse / Anomaly
# ---------------------------------------------------------------------------

def analyze_discounts(revenue_df):
    """
    Flag abnormal discounting patterns:
    - Discounts > 25% (excessive)
    - Reps with systematically high discounts
    - Discount trends over time
    """
    _require_columns(
        revenue_df,
        ["customer_id", "month", "sales_rep", "discount_pct", "mrr_billed", "mrr_contracted"],
        "analyze_discounts",
    )
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])

    # Customer-level discount summary
    cust_discounts = df.groupby("customer_id").agg(
        avg_discount=("discount_pct", "mean"),
        max_discount=("discount_pct", "max"),
        discount_months=("discount_pct", lambda x: (x > 0).sum()),
        total_months=("discount_pct", "count"),
    ).reset_index()

    cust_discounts["discount_frequency"] = round(
        cust_discounts["discount_months"] / cust_discounts["total_months"] * 100, 1
    )
    cust_discounts["excessive_discount"] = cust_discounts["max_discount"] > 25
    cust_discounts["risk_score_discount"] = np.clip(
        cust_discounts["avg_discount"] * 3, 0, 100
    ).round(1)

    # Rep-level analysis
    rep_discounts = df.groupby("sales_rep").agg(
        avg_discount=("discount_pct", "mean"),
        median_discount=("discount_pct", "median"),
        max_discount=("discount_pct", "max"),
        total_revenue=("mrr_billed", "sum"),
        customer_count=("customer_id", "nunique"),
    ).reset_index()

    rep_impact = (
        df.assign(discount_impact=(df["mrr_contracted"] - df["mrr_billed"]))
        .groupby("sales_rep", as_index=False)["discount_impact"]
        .sum()
        .rename(columns={"discount_impact": "discount_revenue_impact"})
    )
    rep_discounts = rep_discounts.merge(rep_impact, on="sales_rep", how="left")
    rep_discounts["discount_revenue_impact"] = rep_discounts["discount_revenue_impact"].fillna(0).round(2)

    # Monthly trend
    monthly_discounts = df.groupby("month").agg(
        avg_discount=("discount_pct", "mean"),
        pct_discounted=("discount_pct", lambda x: (x > 0).mean() * 100),
    ).reset_index()

    return cust_discounts, rep_discounts, monthly_discounts


# ---------------------------------------------------------------------------
# 4. Payment Anomalies
# ---------------------------------------------------------------------------

def analyze_payments(revenue_df):
    """
    Detect payment leakage:
    - Collection gap (billed vs collected)
    - Late payments
    - Failed/partial patterns
    """
    _require_columns(
        revenue_df,
        ["customer_id", "month", "mrr_billed", "mrr_collected", "days_to_pay", "payment_status"],
        "analyze_payments",
    )
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])
    df["collection_gap"] = df["mrr_billed"] - df["mrr_collected"]

    # Customer-level
    cust_payments = df.groupby("customer_id").agg(
        total_billed=("mrr_billed", "sum"),
        total_collected=("mrr_collected", "sum"),
        avg_days_to_pay=("days_to_pay", "mean"),
        failed_count=("payment_status", lambda x: (x == "failed").sum()),
        partial_count=("payment_status", lambda x: (x == "partial").sum()),
        late_count=("payment_status", lambda x: (x == "paid_late").sum()),
    ).reset_index()

    cust_payments["collection_rate"] = round(
        cust_payments["total_collected"] / cust_payments["total_billed"].clip(lower=1) * 100, 1
    )
    cust_payments["total_gap"] = round(
        cust_payments["total_billed"] - cust_payments["total_collected"], 2
    )
    cust_payments["risk_score_payment"] = np.clip(
        (100 - cust_payments["collection_rate"]) * 2 +
        cust_payments["failed_count"] * 10,
        0, 100
    ).round(1)

    # Monthly trend
    monthly_payments = df.groupby("month").agg(
        total_billed=("mrr_billed", "sum"),
        total_collected=("mrr_collected", "sum"),
        failed_pct=("payment_status", lambda x: (x == "failed").mean() * 100),
    ).reset_index()
    monthly_payments["collection_rate"] = round(
        monthly_payments["total_collected"] / monthly_payments["total_billed"].clip(lower=1) * 100, 1
    )

    return cust_payments, monthly_payments


# ---------------------------------------------------------------------------
# 5. Revenue Concentration Risk
# ---------------------------------------------------------------------------

def analyze_concentration(revenue_df):
    """
    Measure revenue concentration risk:
    - Top 10/20 customer share
    - HHI (Herfindahl-Hirschman Index)
    - Segment concentration
    """
    _require_columns(
        revenue_df,
        ["customer_id", "month", "mrr_billed", "segment", "industry"],
        "analyze_concentration",
    )
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])

    # Latest 3 months for current state
    latest_months = df["month"].drop_duplicates().nlargest(3)
    recent = df[df["month"].isin(latest_months)]

    cust_rev = recent.groupby("customer_id")["mrr_billed"].sum().sort_values(ascending=False)
    total_rev = cust_rev.sum()

    n = len(cust_rev)
    top10_share = cust_rev.head(max(1, int(n * 0.1))).sum() / total_rev * 100 if total_rev > 0 else 0
    top20_share = cust_rev.head(max(1, int(n * 0.2))).sum() / total_rev * 100 if total_rev > 0 else 0

    # HHI
    shares = (cust_rev / total_rev * 100) if total_rev > 0 else cust_rev
    hhi = round((shares ** 2).sum(), 1)

    # Segment concentration
    seg_rev = recent.groupby("segment")["mrr_billed"].sum()
    seg_share = round(seg_rev / seg_rev.sum() * 100, 1).to_dict()

    # Industry concentration
    ind_rev = recent.groupby("industry")["mrr_billed"].sum()
    ind_share = round(ind_rev / ind_rev.sum() * 100, 1).to_dict()

    return {
        "top_10pct_revenue_share": round(top10_share, 1),
        "top_20pct_revenue_share": round(top20_share, 1),
        "hhi": hhi,
        "hhi_interpretation": "Low" if hhi < 1500 else "Moderate" if hhi < 2500 else "High",
        "segment_shares": seg_share,
        "industry_shares": ind_share,
        "customer_count": n,
        "total_recent_revenue": round(total_rev, 2),
    }


# ---------------------------------------------------------------------------
# 6. Composite Leakage Score
# ---------------------------------------------------------------------------

def build_leakage_scorecard(churn_df, deterioration_df, discount_df, payment_df, customers_df):
    """
    Combine all risk dimensions into a single customer-level scorecard.
    Weights: churn 30%, deterioration 25%, discount 20%, payment 25%.
    """
    scorecard = customers_df[["customer_id", "company_name", "segment", "region",
                               "industry", "annual_contract_value", "sales_rep"]].copy()

    # Merge risk scores
    if "risk_score_churn" in churn_df.columns:
        scorecard = scorecard.merge(
            churn_df[["customer_id", "risk_score_churn", "avg_engagement", "engagement_slope"]],
            on="customer_id", how="left"
        )
    if "risk_score_deterioration" in deterioration_df.columns:
        scorecard = scorecard.merge(
            deterioration_df[["customer_id", "risk_score_deterioration", "mrr_change_pct"]],
            on="customer_id", how="left"
        )
    if "risk_score_discount" in discount_df.columns:
        scorecard = scorecard.merge(
            discount_df[["customer_id", "risk_score_discount", "avg_discount"]],
            on="customer_id", how="left"
        )
    if "risk_score_payment" in payment_df.columns:
        scorecard = scorecard.merge(
            payment_df[["customer_id", "risk_score_payment", "collection_rate", "total_gap"]],
            on="customer_id", how="left"
        )

    # Fill missing scores
    risk_cols = ["risk_score_churn", "risk_score_deterioration",
                 "risk_score_discount", "risk_score_payment"]
    for col in risk_cols:
        if col not in scorecard.columns:
            scorecard[col] = 0
        scorecard[col] = scorecard[col].fillna(0)

    # Composite score (weighted)
    scorecard["composite_risk_score"] = (
        scorecard["risk_score_churn"] * 0.30 +
        scorecard["risk_score_deterioration"] * 0.25 +
        scorecard["risk_score_discount"] * 0.20 +
        scorecard["risk_score_payment"] * 0.25
    ).round(1)

    # Risk tier
    scorecard["risk_tier"] = pd.cut(
        scorecard["composite_risk_score"],
        bins=[-1, 20, 40, 60, 100],
        labels=["Low", "Medium", "High", "Critical"],
    )

    # Revenue at risk
    scorecard["revenue_at_risk"] = (
        scorecard["annual_contract_value"] * scorecard["composite_risk_score"] / 100
    ).round(2)

    return scorecard.sort_values("composite_risk_score", ascending=False)


# ---------------------------------------------------------------------------
# 7. Summary Metrics
# ---------------------------------------------------------------------------

def compute_summary_metrics(scorecard, revenue_df, concentration):
    """Compute executive-level KPI metrics."""
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])

    total_arr = scorecard["annual_contract_value"].sum()
    total_at_risk = scorecard["revenue_at_risk"].sum()

    latest_month = df["month"].max()
    prev_month = latest_month - pd.DateOffset(months=1)

    latest_rev = df[df["month"] == latest_month]["mrr_billed"].sum()
    prev_rev = df[df["month"] == prev_month]["mrr_billed"].sum()
    mrr_growth = (latest_rev - prev_rev) / prev_rev * 100 if prev_rev > 0 else 0

    total_billed = df["mrr_billed"].sum()
    total_collected = df["mrr_collected"].sum()
    overall_collection_rate = total_collected / total_billed * 100 if total_billed > 0 else 0

    avg_discount = df[df["discount_pct"] > 0]["discount_pct"].mean()

    return {
        "total_arr": float(round(total_arr, 0)),
        "total_revenue_at_risk": float(round(total_at_risk, 0)),
        "pct_revenue_at_risk": float(round(total_at_risk / total_arr * 100, 1)) if total_arr > 0 else 0,
        "latest_mrr": float(round(latest_rev, 0)),
        "mrr_growth_pct": float(round(mrr_growth, 1)),
        "overall_collection_rate": float(round(overall_collection_rate, 1)),
        "avg_discount_when_applied": float(round(avg_discount, 1)),
        "critical_risk_customers": int((scorecard["risk_tier"] == "Critical").sum()),
        "high_risk_customers": int((scorecard["risk_tier"] == "High").sum()),
        "top_10pct_concentration": float(concentration["top_10pct_revenue_share"]),
        "hhi": float(concentration["hhi"]),
    }
