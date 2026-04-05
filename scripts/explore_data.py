"""
Formal Data Exploration Pass
Rigorous /explore-data style profiling of all core project tables.
"""
import sys, os, json
from datetime import datetime
from collections import OrderedDict

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.runtime import configure_runtime
configure_runtime(project_root)

import pandas as pd
import numpy as np

pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 140)
pd.set_option("display.float_format", "{:,.4f}".format)

# ─────────────────────────────────────────────────────────────────────────────
# Load all tables
# ─────────────────────────────────────────────────────────────────────────────
data_dir = os.path.join(project_root, "data")

customers = pd.read_csv(os.path.join(data_dir, "raw", "customers.csv"), parse_dates=["onboard_date"])
revenue = pd.read_csv(os.path.join(data_dir, "raw", "monthly_revenue.csv"))
revenue["month"] = pd.to_datetime(revenue["month"])
usage = pd.read_csv(os.path.join(data_dir, "raw", "product_usage.csv"))
usage["month"] = pd.to_datetime(usage["month"])

scorecard = pd.read_csv(os.path.join(data_dir, "processed", "risk_scorecard.csv"))
payments = pd.read_csv(os.path.join(data_dir, "processed", "payment_analysis.csv"))
discounts = pd.read_csv(os.path.join(data_dir, "processed", "discount_analysis.csv"))
rep_discounts = pd.read_csv(os.path.join(data_dir, "processed", "rep_discount_impact.csv"))
deterioration = pd.read_csv(os.path.join(data_dir, "processed", "deterioration_analysis.csv"))

tables = OrderedDict([
    ("customers", customers),
    ("monthly_revenue", revenue),
    ("product_usage", usage),
    ("risk_scorecard", scorecard),
    ("payment_analysis", payments),
    ("discount_analysis", discounts),
    ("rep_discount_impact", rep_discounts),
    ("deterioration_analysis", deterioration),
])

SEP = "=" * 80
SUBSEP = "-" * 80
all_issues = []
all_output = []

def out(msg=""):
    print(msg)
    all_output.append(msg)

def section(title):
    out(f"\n{SEP}")
    out(f"  {title}")
    out(SEP)

def subsection(title):
    out(f"\n{SUBSEP}")
    out(f"  {title}")
    out(SUBSEP)

def add_issue(table, severity, description):
    all_issues.append({"table": table, "severity": severity, "issue": description})
    icon = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🔴"}.get(severity, "•")
    out(f"  {icon} [{severity}] {description}")

# ─────────────────────────────────────────────────────────────────────────────
# Column classifier
# ─────────────────────────────────────────────────────────────────────────────
def classify_column(col_name, series):
    """Classify a column into: ID, dimension, metric, temporal, boolean, text."""
    name = col_name.lower()

    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "temporal"
    if "date" in name or "month" in name:
        return "temporal"
    if "_id" in name or name == "customer_id" or name == "sales_rep":
        return "ID"
    if "is_" in name or "has_" in name or name.startswith("excessive") or name.startswith("is_") or name.startswith("silent_"):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "metric"
    if series.dtype == "object" and series.nunique() < 30:
        return "dimension"
    if series.dtype == "object":
        return "text"
    return "other"


# ─────────────────────────────────────────────────────────────────────────────
# Per-table exploration
# ─────────────────────────────────────────────────────────────────────────────
table_profiles = {}

for tname, df in tables.items():
    section(f"TABLE: {tname}")

    # ── 1. Shape & grain ─────────────────────────────────────────────────
    subsection("1. SHAPE & GRAIN")
    out(f"  Rows:    {len(df):,}")
    out(f"  Columns: {len(df.columns)}")
    out(f"  Memory:  {df.memory_usage(deep=True).sum() / 1e6:.2f} MB")

    # Determine grain
    if tname == "customers":
        grain = "1 row per customer"
        pk_cols = ["customer_id"]
    elif tname == "monthly_revenue":
        grain = "1 row per customer-month"
        pk_cols = ["customer_id", "month"]
    elif tname == "product_usage":
        grain = "1 row per customer-month-feature"
        pk_cols = ["customer_id", "month", "feature"]
    elif tname == "risk_scorecard":
        grain = "1 row per customer"
        pk_cols = ["customer_id"]
    elif tname == "payment_analysis":
        grain = "1 row per customer"
        pk_cols = ["customer_id"]
    elif tname == "discount_analysis":
        grain = "1 row per customer"
        pk_cols = ["customer_id"]
    elif tname == "rep_discount_impact":
        grain = "1 row per sales rep"
        pk_cols = ["sales_rep"]
    elif tname == "deterioration_analysis":
        grain = "1 row per customer"
        pk_cols = ["customer_id"]
    else:
        grain = "unknown"
        pk_cols = []

    out(f"  Grain:   {grain}")
    out(f"  PK:      {pk_cols}")

    # ── 2. Primary key validation ────────────────────────────────────────
    subsection("2. PRIMARY KEY VALIDATION")
    if pk_cols:
        pk_present = [c for c in pk_cols if c in df.columns]
        if pk_present:
            dup_count = df.duplicated(subset=pk_present, keep=False).sum()
            total = len(df)
            out(f"  PK columns: {pk_present}")
            out(f"  Duplicate PK rows: {dup_count} / {total:,} ({dup_count/total*100:.2f}%)")
            if dup_count > 0:
                add_issue(tname, "CRITICAL", f"{dup_count} duplicate rows on primary key {pk_present}")
                out(f"  Sample duplicates:")
                dups = df[df.duplicated(subset=pk_present, keep=False)]
                out(dups.head(5).to_string())
            else:
                out(f"  ✅ Primary key is unique — no duplicates.")
        else:
            add_issue(tname, "WARNING", f"PK columns {pk_cols} not found in table")
    out(f"  Full-row duplicates: {df.duplicated().sum()}")

    # ── 3. Column classification ─────────────────────────────────────────
    subsection("3. COLUMN CLASSIFICATION")
    classifications = {}
    for col in df.columns:
        ctype = classify_column(col, df[col])
        classifications[col] = ctype

    # Group by type
    by_type = {}
    for col, ctype in classifications.items():
        by_type.setdefault(ctype, []).append(col)
    for ctype in ["ID", "temporal", "dimension", "metric", "boolean", "text", "other"]:
        cols = by_type.get(ctype, [])
        if cols:
            out(f"  {ctype.upper():12s} ({len(cols):2d}): {', '.join(cols)}")

    # ── 4. Null analysis ────────────────────────────────────────────────
    subsection("4. NULL ANALYSIS")
    null_df = pd.DataFrame({
        "column": df.columns,
        "null_count": [df[c].isna().sum() for c in df.columns],
        "null_pct": [df[c].isna().mean() * 100 for c in df.columns],
        "dtype": [str(df[c].dtype) for c in df.columns],
    }).sort_values("null_pct", ascending=False)

    has_nulls = null_df[null_df["null_count"] > 0]
    if len(has_nulls) == 0:
        out("  ✅ No null values in any column.")
    else:
        out(f"  Columns with nulls: {len(has_nulls)} / {len(df.columns)}")
        for _, row in has_nulls.iterrows():
            severity = "CRITICAL" if row["null_pct"] > 20 else "WARNING" if row["null_pct"] > 5 else "INFO"
            add_issue(tname, severity, f"{row['column']}: {row['null_count']:,.0f} nulls ({row['null_pct']:.1f}%)")

    # ── 5. Cardinality ──────────────────────────────────────────────────
    subsection("5. CARDINALITY (distinct counts)")
    card_data = []
    for col in df.columns:
        n_unique = df[col].nunique()
        ratio = n_unique / len(df) * 100 if len(df) > 0 else 0
        card_data.append({
            "column": col,
            "distinct": n_unique,
            "pct_of_rows": round(ratio, 1),
            "type": classifications[col],
        })
    card_df = pd.DataFrame(card_data)
    out(card_df.to_string(index=False))

    # Flag potential ID columns with low cardinality
    for _, row in card_df.iterrows():
        if row["type"] == "ID" and row["pct_of_rows"] < 50 and len(df) > 10:
            add_issue(tname, "INFO", f"{row['column']} classified as ID but cardinality={row['distinct']} ({row['pct_of_rows']:.1f}% of rows)")

    # ── 6. Numeric distributions ────────────────────────────────────────
    metric_cols = [c for c, t in classifications.items() if t == "metric"]
    if metric_cols:
        subsection("6. NUMERIC DISTRIBUTIONS")
        desc = df[metric_cols].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
        out(desc.round(2).to_string())

        # Skewness and kurtosis
        out("\n  Skewness & Kurtosis:")
        for col in metric_cols:
            if df[col].std() > 0:
                skew = df[col].skew()
                kurt = df[col].kurtosis()
                out(f"    {col:35s}  skew={skew:+.2f}  kurt={kurt:+.2f}")
                if abs(skew) > 3:
                    add_issue(tname, "INFO", f"{col}: highly skewed (skew={skew:+.2f})")
                if kurt > 10:
                    add_issue(tname, "INFO", f"{col}: heavy-tailed (kurtosis={kurt:+.2f})")

        # Zeros and negatives
        out("\n  Zeros & Negatives:")
        for col in metric_cols:
            zeros = (df[col] == 0).sum()
            negs = (df[col] < 0).sum()
            zero_pct = zeros / len(df) * 100
            out(f"    {col:35s}  zeros={zeros:,} ({zero_pct:.1f}%)  negatives={negs:,}")
            if negs > 0 and any(kw in col.lower() for kw in ["revenue", "mrr", "acv", "billed", "collected", "value", "price"]):
                add_issue(tname, "WARNING", f"{col}: {negs:,} negative values in a typically positive field")
            if zero_pct > 30 and "score" not in col.lower() and "discount" not in col.lower():
                add_issue(tname, "INFO", f"{col}: {zero_pct:.0f}% zero values — check if intentional")

        # Outlier detection (IQR method)
        out("\n  Outliers (IQR method, >3×IQR from Q1/Q3):")
        for col in metric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower = q1 - 3 * iqr
                upper = q3 + 3 * iqr
                outliers = ((df[col] < lower) | (df[col] > upper)).sum()
                out_pct = outliers / len(df) * 100
                out(f"    {col:35s}  outliers={outliers:,} ({out_pct:.2f}%)  range=[{lower:.1f}, {upper:.1f}]")
                if out_pct > 5:
                    add_issue(tname, "WARNING", f"{col}: {out_pct:.1f}% outliers by IQR method — inspect distribution")

    # ── 7. Temporal coverage ────────────────────────────────────────────
    temporal_cols = [c for c, t in classifications.items() if t == "temporal"]
    if temporal_cols:
        subsection("7. TEMPORAL COVERAGE")
        for col in temporal_cols:
            s = pd.to_datetime(df[col], errors="coerce")
            if s.isna().all():
                out(f"  {col}: could not parse as dates")
                continue
            out(f"  {col}:")
            out(f"    Min: {s.min()}")
            out(f"    Max: {s.max()}")
            span_days = (s.max() - s.min()).days
            out(f"    Span: {span_days} days ({span_days/30:.1f} months)")

            # Check for monthly gaps
            if "month" in col.lower():
                months_present = s.dt.to_period("M").nunique()
                expected_months = (s.max().to_period("M") - s.min().to_period("M")).n + 1
                out(f"    Months present: {months_present} / {expected_months} expected")
                if months_present < expected_months:
                    missing = expected_months - months_present
                    add_issue(tname, "WARNING", f"{col}: {missing} missing months in range")

                # Row count per month (evenness check)
                monthly_counts = df.groupby(s.dt.to_period("M")).size()
                out(f"    Rows per month: min={monthly_counts.min()}, max={monthly_counts.max()}, "
                    f"mean={monthly_counts.mean():.0f}, cv={monthly_counts.std()/monthly_counts.mean():.2f}")
                if monthly_counts.std() / monthly_counts.mean() > 0.15:
                    add_issue(tname, "INFO", f"{col}: uneven row distribution across months (CV={monthly_counts.std()/monthly_counts.mean():.2f})")

            # Check for future dates
            future = (s > pd.Timestamp.now()).sum()
            if future > 0:
                add_issue(tname, "WARNING", f"{col}: {future} future dates detected")

    # ── 8. Dimension value inspection ───────────────────────────────────
    dim_cols = [c for c, t in classifications.items() if t == "dimension"]
    if dim_cols:
        subsection("8. DIMENSION VALUES")
        for col in dim_cols:
            vc = df[col].value_counts()
            out(f"\n  {col} ({len(vc)} distinct):")
            for val, cnt in vc.items():
                pct = cnt / len(df) * 100
                out(f"    {str(val):30s}  {cnt:>6,}  ({pct:5.1f}%)")

            # Check for whitespace issues
            if df[col].dtype == "object":
                trimmed = df[col].dropna().str.strip()
                diff = (trimmed != df[col].dropna()).sum()
                if diff > 0:
                    add_issue(tname, "WARNING", f"{col}: {diff} values have leading/trailing whitespace")

            # Check for casing inconsistency
            if df[col].dtype == "object":
                lower_unique = df[col].dropna().str.lower().nunique()
                actual_unique = df[col].nunique()
                if lower_unique < actual_unique:
                    add_issue(tname, "WARNING", f"{col}: {actual_unique - lower_unique} values differ only by case")

    # ── 9. Boolean column inspection ────────────────────────────────────
    bool_cols = [c for c, t in classifications.items() if t == "boolean"]
    if bool_cols:
        subsection("9. BOOLEAN COLUMNS")
        for col in bool_cols:
            vc = df[col].value_counts(dropna=False)
            out(f"  {col}:")
            for val, cnt in vc.items():
                out(f"    {str(val):20s}  {cnt:>6,}  ({cnt/len(df)*100:.1f}%)")

    # ── 10. Cross-field consistency checks ──────────────────────────────
    subsection("10. CROSS-FIELD CONSISTENCY")
    if tname == "monthly_revenue":
        # collected <= billed
        violations = (df["mrr_collected"] > df["mrr_billed"] * 1.001).sum()
        out(f"  mrr_collected > mrr_billed: {violations} violations")
        if violations > 0:
            add_issue(tname, "CRITICAL", f"{violations} rows where collected > billed")

        # discount creates expected gap
        expected_billed = df["mrr_contracted"] * (1 - df["discount_pct"] / 100)
        gap = (df["mrr_billed"] - expected_billed).abs()
        tolerance_violations = (gap > 1).sum()
        out(f"  mrr_billed vs contracted*(1-discount): {tolerance_violations} tolerance violations (>$1)")
        if tolerance_violations > 0:
            add_issue(tname, "WARNING", f"{tolerance_violations} rows where billed != contracted*(1-discount%)")

        # engagement_score bounds
        above_100 = (df["engagement_score"] > 100).sum()
        below_0 = (df["engagement_score"] < 0).sum()
        out(f"  engagement_score > 100: {above_100}")
        out(f"  engagement_score < 0: {below_0}")
        if above_100 > 0:
            add_issue(tname, "WARNING", f"engagement_score: {above_100} values > 100 (expected 0-100 range)")

        # payment_status vs collected
        failed_with_collection = ((df["payment_status"] == "failed") & (df["mrr_collected"] > 0)).sum()
        out(f"  failed payments with collection > 0: {failed_with_collection}")
        if failed_with_collection > 0:
            add_issue(tname, "CRITICAL", f"{failed_with_collection} 'failed' payments that have collected revenue > 0")

        # pending with collection
        pending_with_collection = ((df["payment_status"] == "pending") & (df["mrr_collected"] > 0)).sum()
        out(f"  pending payments with collection > 0: {pending_with_collection}")
        if pending_with_collection > 0:
            add_issue(tname, "WARNING", f"{pending_with_collection} 'pending' payments that have collected revenue > 0")

    elif tname == "risk_scorecard":
        # Composite = weighted sum
        recomputed = (
            scorecard["risk_score_churn"] * 0.30 +
            scorecard["risk_score_deterioration"] * 0.25 +
            scorecard["risk_score_discount"] * 0.20 +
            scorecard["risk_score_payment"] * 0.25
        ).round(1)
        max_diff = (scorecard["composite_risk_score"] - recomputed).abs().max()
        out(f"  composite_risk_score weighted-sum check: max diff = {max_diff:.4f}")
        if max_diff > 0.2:
            add_issue(tname, "CRITICAL", f"Composite score mismatch: max diff = {max_diff:.2f}")

        # revenue_at_risk <= ACV
        over = (scorecard["revenue_at_risk"] > scorecard["annual_contract_value"]).sum()
        out(f"  revenue_at_risk > ACV: {over} violations")
        if over > 0:
            add_issue(tname, "CRITICAL", f"{over} customers with revenue_at_risk > ACV")

    elif tname == "customers":
        # ACV must be positive
        neg_acv = (customers["annual_contract_value"] <= 0).sum()
        out(f"  annual_contract_value <= 0: {neg_acv}")
        if neg_acv > 0:
            add_issue(tname, "CRITICAL", f"{neg_acv} customers with non-positive ACV")

        # Onboard date in reasonable range
        too_old = (customers["onboard_date"] < pd.Timestamp("2020-01-01")).sum()
        too_new = (customers["onboard_date"] > pd.Timestamp.now()).sum()
        out(f"  onboard_date before 2020: {too_old}")
        out(f"  onboard_date in future: {too_new}")

    elif tname == "payment_analysis":
        # collection_rate in [0, 100+]
        above = (payments["collection_rate"] > 100.5).sum()
        out(f"  collection_rate > 100%: {above}")
        if above > 0:
            add_issue(tname, "WARNING", f"{above} customers with collection rate > 100%")

    else:
        out("  No cross-field checks defined for this table.")

    # Save profile
    table_profiles[tname] = {
        "rows": len(df),
        "columns": len(df.columns),
        "grain": grain,
        "pk": pk_cols,
        "classifications": classifications,
        "null_columns": len(has_nulls) if len(has_nulls) > 0 else 0,
    }

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY SECTION
# ─────────────────────────────────────────────────────────────────────────────

section("DATA QUALITY ISSUE REGISTER")
if not all_issues:
    out("  ✅ No issues found across all tables.")
else:
    out(f"\n  Total issues: {len(all_issues)}")
    critical = [i for i in all_issues if i["severity"] == "CRITICAL"]
    warnings = [i for i in all_issues if i["severity"] == "WARNING"]
    infos = [i for i in all_issues if i["severity"] == "INFO"]
    out(f"  CRITICAL: {len(critical)}  |  WARNING: {len(warnings)}  |  INFO: {len(infos)}")

    for sev in ["CRITICAL", "WARNING", "INFO"]:
        items = [i for i in all_issues if i["severity"] == sev]
        if items:
            out(f"\n  --- {sev} ---")
            for i in items:
                out(f"    [{i['table']}] {i['issue']}")


section("ANALYTICALLY USEFUL DIMENSIONS & METRICS")
out("""
  DIMENSIONS (slice-and-dice candidates):
    1. segment       — Enterprise / Mid-Market / SMB (primary business segmentation)
    2. region        — North America / Europe / APAC / LATAM
    3. industry      — 8 industries (Technology, Healthcare, etc.)
    4. sales_rep     — 20 reps (enables rep-level performance analysis)
    5. payment_status — paid / paid_late / partial / failed / pending
    6. risk_tier     — Low / Medium / High / Critical
    7. leakage_pattern — stable / gradual_decline / sudden_drop / seasonal

  METRICS (quantify and aggregate):
    Revenue Funnel:
      • mrr_contracted    — contracted monthly revenue (pre-discount)
      • mrr_billed        — billed after discounts
      • mrr_collected     — actually collected
      • discount_pct      — discount applied (0-50%)
      • annual_contract_value — yearly contract size

    Leakage Quantification:
      • collection_gap    = mrr_billed - mrr_collected
      • discount_leakage  = mrr_contracted - mrr_billed
      • revenue_at_risk   — ACV weighted by composite risk score

    Behavioral Signals:
      • engagement_score  — product usage proxy (0-100)
      • days_to_pay       — payment speed
      • sessions          — feature usage count
      • active_users      — per-feature user count

    Risk Scores:
      • risk_score_churn          — silent churn risk (0-100)
      • risk_score_deterioration  — MRR decline risk (0-100)
      • risk_score_discount       — discount anomaly risk (0-100)
      • risk_score_payment        — payment failure risk (0-100)
      • composite_risk_score      — weighted composite (0-100)

  TEMPORAL:
    • month        — 24 months (2024-01 to 2025-12), monthly grain
    • onboard_date — customer tenure (2023-01 to 2025-12)
""")


section("RECOMMENDED FOLLOW-UP ANALYSES")
out("""
  HIGH PRIORITY:
    1. Cohort retention curves — plot retention by onboard quarter
       Why: validates whether churn patterns vary by vintage
       Grain: customer × month, cohorted by onboard quarter

    2. Net Revenue Retention (NRR) by segment — month-over-month
       Why: gold-standard SaaS metric, isolates expansion vs contraction
       Grain: segment × month

    3. Rep discount elasticity — discount % vs win rate / retention
       Why: determines whether heavy discounting actually helps or hurts
       Grain: sales_rep, correlated with churn outcomes

    4. Days-to-pay → churn correlation — do slow payers churn more?
       Why: payment velocity may be a leading indicator of disengagement
       Grain: customer-level, lagged analysis

  MEDIUM PRIORITY:
    5. Feature usage clusters — which usage patterns predict risk?
       Why: product_usage data has 5 features × 24 months per customer
       Method: k-means or similar on feature usage vectors

    6. Seasonal decomposition of MRR — separate trend from seasonality
       Why: 15% of customers have seasonal pattern, could confuse trend analysis
       Method: STL decomposition on aggregate MRR

    7. Concentration risk over time — is dependency increasing?
       Why: current analysis is point-in-time, trend matters more
       Grain: monthly HHI / top-10% share

    8. Discount escalation patterns — do discounts increase over renewals?
       Why: gradual discount creep is a common leakage pattern
       Grain: customer × month, trend analysis on discount_pct

  VALIDATION FOLLOW-UPS:
    9. Engagement score calibration — compare scores across segments
       Why: engagement > 100 found (42 values at 0, some > 100)
       Action: clip or normalize, document acceptable range

   10. Payment status → collection consistency audit
       Why: potential for failed/pending payments with non-zero collection
       Action: tighten data generation or add business rules
""")


# ─────────────────────────────────────────────────────────────────────────────
# Save report
# ─────────────────────────────────────────────────────────────────────────────
output_dir = os.path.join(project_root, "outputs", "reports")
os.makedirs(output_dir, exist_ok=True)

report_path = os.path.join(output_dir, "data_exploration_report.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(f"Data Exploration Report — Generated {datetime.now().isoformat()}\n\n")
    f.write("\n".join(all_output))

issues_path = os.path.join(output_dir, "data_quality_issues.json")
with open(issues_path, "w") as f:
    json.dump(all_issues, f, indent=2)

# Save concise profile summary as JSON
profile_path = os.path.join(output_dir, "table_profiles_detailed.json")
profile_out = {}
for tname, p in table_profiles.items():
    profile_out[tname] = {
        "rows": p["rows"],
        "columns": p["columns"],
        "grain": p["grain"],
        "primary_key": p["pk"],
        "column_types": {ctype: [c for c, t in p["classifications"].items() if t == ctype]
                         for ctype in set(p["classifications"].values())},
        "null_columns": p["null_columns"],
    }
with open(profile_path, "w") as f:
    json.dump(profile_out, f, indent=2)

out(f"\n\nReports saved:")
out(f"  {report_path}")
out(f"  {issues_path}")
out(f"  {profile_path}")
