import pandas as pd

from src.leakage_analyzer import (
    analyze_discounts,
    analyze_payments,
    build_leakage_scorecard,
    detect_silent_churn,
)


def _sample_revenue():
    return pd.DataFrame(
        {
            "customer_id": ["C1", "C1", "C1", "C2", "C2", "C2"],
            "month": ["2025-01-01", "2025-02-01", "2025-03-01", "2025-01-01", "2025-02-01", "2025-03-01"],
            "engagement_score": [60, 50, 40, 70, 71, 72],
            "mrr_contracted": [1000, 1000, 1000, 1200, 1200, 1200],
            "mrr_billed": [900, 900, 900, 1200, 1140, 1080],
            "mrr_collected": [900, 700, 0, 1200, 1100, 1000],
            "discount_pct": [10, 10, 10, 0, 5, 10],
            "sales_rep": ["REP-001", "REP-001", "REP-001", "REP-002", "REP-002", "REP-002"],
            "payment_status": ["paid", "partial", "failed", "paid", "paid_late", "partial"],
            "days_to_pay": [10, 25, 40, 7, 18, 22],
            "segment": ["SMB", "SMB", "SMB", "Enterprise", "Enterprise", "Enterprise"],
            "industry": ["Tech", "Tech", "Tech", "Finance", "Finance", "Finance"],
        }
    )


def test_detect_silent_churn_missing_columns_raises():
    revenue = _sample_revenue().drop(columns=["engagement_score"])
    try:
        detect_silent_churn(revenue)
    except ValueError as exc:
        assert "engagement_score" in str(exc)
    else:
        raise AssertionError("Era esperado ValueError para coluna em falta.")


def test_analyze_discounts_rep_impact_matches_direct_calculation():
    revenue = _sample_revenue()
    _, rep_discounts, _ = analyze_discounts(revenue)

    expected = (
        revenue.assign(discount_impact=revenue["mrr_contracted"] - revenue["mrr_billed"])
        .groupby("sales_rep")["discount_impact"]
        .sum()
    )
    got = rep_discounts.set_index("sales_rep")["discount_revenue_impact"]
    pd.testing.assert_series_equal(got.sort_index(), expected.sort_index(), check_names=False)


def test_analyze_payments_collection_rate_is_valid():
    revenue = _sample_revenue()
    customer_payments, monthly = analyze_payments(revenue)

    assert (customer_payments["collection_rate"] >= 0).all()
    assert (customer_payments["collection_rate"] <= 100).all()
    assert (monthly["collection_rate"] >= 0).all()
    assert (monthly["collection_rate"] <= 100).all()


def test_build_leakage_scorecard_composite_formula():
    customers = pd.DataFrame(
        {
            "customer_id": ["C1"],
            "company_name": ["Company 1"],
            "segment": ["SMB"],
            "region": ["Europe"],
            "industry": ["Tech"],
            "annual_contract_value": [12000],
            "sales_rep": ["REP-001"],
        }
    )
    churn = pd.DataFrame({"customer_id": ["C1"], "risk_score_churn": [20], "avg_engagement": [35], "engagement_slope": [-3]})
    deterioration = pd.DataFrame({"customer_id": ["C1"], "risk_score_deterioration": [40], "mrr_change_pct": [-18]})
    discounts = pd.DataFrame({"customer_id": ["C1"], "risk_score_discount": [30], "avg_discount": [10]})
    payments = pd.DataFrame({"customer_id": ["C1"], "risk_score_payment": [50], "collection_rate": [82], "total_gap": [500]})

    scorecard = build_leakage_scorecard(churn, deterioration, discounts, payments, customers)
    expected = round(20 * 0.30 + 40 * 0.25 + 30 * 0.20 + 50 * 0.25, 1)
    assert scorecard.iloc[0]["composite_risk_score"] == expected

