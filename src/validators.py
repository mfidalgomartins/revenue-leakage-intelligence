"""
Validation Module
Pre-delivery quality checks: reconciliation, logic, completeness.
"""
import pandas as pd
import numpy as np


def run_all_validations(customers, revenue, scorecard, summary_metrics):
    """Run comprehensive validation suite and return results."""
    results = []

    # 1. Row count sanity
    results.append(_check(
        "Row Count - Customers",
        len(customers) == 500,
        f"Expected 500, got {len(customers)}"
    ))
    results.append(_check(
        "Row Count - Revenue",
        len(revenue) > 5000,
        f"Got {len(revenue)} rows (expect >5000 for 500 customers × 24 months)"
    ))

    # 2. Null checks on critical fields
    for col in ["customer_id", "mrr_billed", "mrr_collected", "month"]:
        nulls = revenue[col].isna().sum()
        results.append(_check(
            f"Null Check - revenue.{col}",
            nulls == 0,
            f"{nulls} nulls found"
        ))

    # 3. Reconciliation: billed >= collected (within tolerance)
    violations = (revenue["mrr_collected"] > revenue["mrr_billed"] * 1.01).sum()
    results.append(_check(
        "Reconciliation - collected <= billed",
        violations == 0,
        f"{violations} rows where collected > billed (tolerance 1%)"
    ))

    # 4. Aggregation logic: sum of parts = total
    total_arr_customers = customers["annual_contract_value"].sum()
    total_arr_scorecard = scorecard["annual_contract_value"].sum()
    results.append(_check(
        "Aggregation - ARR consistency",
        abs(total_arr_customers - total_arr_scorecard) < 1,
        f"Customer ARR: {total_arr_customers:,.0f}, Scorecard ARR: {total_arr_scorecard:,.0f}"
    ))

    # 5. Score bounds (0-100)
    risk_cols = [c for c in scorecard.columns if "risk_score" in c]
    for col in risk_cols:
        out_of_bounds = ((scorecard[col] < 0) | (scorecard[col] > 100)).sum()
        results.append(_check(
            f"Score Bounds - {col}",
            out_of_bounds == 0,
            f"{out_of_bounds} values outside [0, 100]"
        ))

    # 6. Composite score = weighted sum
    recomputed = (
        scorecard["risk_score_churn"] * 0.30 +
        scorecard["risk_score_deterioration"] * 0.25 +
        scorecard["risk_score_discount"] * 0.20 +
        scorecard["risk_score_payment"] * 0.25
    ).round(1)
    diff = (scorecard["composite_risk_score"] - recomputed).abs().max()
    results.append(_check(
        "Composite Score - weighted sum verification",
        diff < 0.2,
        f"Max difference: {diff:.2f}"
    ))

    # 7. Revenue at risk <= ARR
    excess = (scorecard["revenue_at_risk"] > scorecard["annual_contract_value"]).sum()
    results.append(_check(
        "Revenue at Risk <= ACV",
        excess == 0,
        f"{excess} customers with revenue_at_risk > ACV"
    ))

    # 8. Denominator check — no division by zero
    zero_billed = (revenue["mrr_billed"] == 0).sum()
    results.append(_check(
        "Denominator - zero billed amounts",
        True,  # Informational
        f"{zero_billed} rows with zero billed (handled by clip)"
    ))

    # 9. Date coverage
    rev_dates = pd.to_datetime(revenue["month"])
    months_covered = rev_dates.dt.to_period("M").nunique()
    results.append(_check(
        "Date Coverage",
        months_covered >= 20,
        f"{months_covered} months covered (target: 24)"
    ))

    # 10. Join explosion check
    cust_in_rev = revenue["customer_id"].nunique()
    results.append(_check(
        "Join Safety - customer coverage",
        cust_in_rev <= len(customers),
        f"{cust_in_rev} unique customers in revenue vs {len(customers)} in master"
    ))

    # 11. Partial period risk
    latest_month = rev_dates.max()
    latest_count = (rev_dates == latest_month).sum()
    prev_month = rev_dates[rev_dates < latest_month].max()
    prev_count = (rev_dates == prev_month).sum()
    ratio = latest_count / prev_count if prev_count > 0 else 0
    results.append(_check(
        "Partial Period - latest month completeness",
        ratio > 0.8,
        f"Latest month has {latest_count} records vs {prev_count} in prior month (ratio: {ratio:.2f})"
    ))

    return results


def _check(name, passed, detail):
    return {
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }


def format_validation_report(results):
    """Format validation results as a readable report."""
    lines = [
        "=" * 70,
        "VALIDATION REPORT",
        "=" * 70,
    ]
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    lines.append(f"Results: {pass_count} PASS / {fail_count} FAIL / {len(results)} total\n")

    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        lines.append(f"  {icon} {r['check']}")
        lines.append(f"     {r['detail']}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)
