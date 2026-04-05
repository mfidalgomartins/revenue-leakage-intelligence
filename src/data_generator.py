"""
Synthetic Business Data Generator
Generates realistic B2B SaaS revenue data with embedded leakage patterns.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

SEED = 42
np.random.seed(SEED)


def generate_customers(n=500):
    """Generate customer master table with realistic B2B attributes."""
    segments = np.random.choice(
        ["Enterprise", "Mid-Market", "SMB"],
        size=n,
        p=[0.15, 0.35, 0.50],
    )
    industries = np.random.choice(
        ["Technology", "Healthcare", "Financial Services", "Manufacturing",
         "Retail", "Education", "Media", "Professional Services"],
        size=n,
    )
    regions = np.random.choice(
        ["North America", "Europe", "APAC", "LATAM"],
        size=n,
        p=[0.40, 0.30, 0.20, 0.10],
    )
    # Onboarding dates spread over 3 years
    start = datetime(2023, 1, 1)
    onboard_days = np.random.randint(0, 365 * 3, size=n)
    onboard_dates = [start + timedelta(days=int(d)) for d in onboard_days]

    # Contract values depend on segment
    base_acv = {"Enterprise": 120000, "Mid-Market": 35000, "SMB": 8000}
    acv = [
        int(base_acv[s] * np.random.lognormal(0, 0.3))
        for s in segments
    ]

    # Churn flag — ~18% overall but segment-dependent
    churn_prob = {"Enterprise": 0.08, "Mid-Market": 0.15, "SMB": 0.25}
    churned = [np.random.random() < churn_prob[s] for s in segments]

    # Sales rep assignment
    reps = [f"REP-{np.random.randint(1, 21):03d}" for _ in range(n)]

    df = pd.DataFrame({
        "customer_id": [f"CUST-{i+1:04d}" for i in range(n)],
        "company_name": [f"Company_{i+1}" for i in range(n)],
        "segment": segments,
        "industry": industries,
        "region": regions,
        "onboard_date": onboard_dates,
        "annual_contract_value": acv,
        "sales_rep": reps,
        "is_churned": churned,
    })
    return df


def generate_monthly_revenue(customers_df, months=24):
    """
    Generate monthly revenue records with embedded leakage patterns:
    - Gradual deterioration (declining MRR)
    - Silent churn (activity drops before formal churn)
    - Payment delays and failures
    """
    records = []
    base_date = datetime(2024, 1, 1)

    for _, cust in customers_df.iterrows():
        cid = cust["customer_id"]
        acv = cust["annual_contract_value"]
        mrr_base = acv / 12
        churned = cust["is_churned"]
        segment = cust["segment"]

        # Determine leakage pattern
        pattern = np.random.choice(
            ["stable", "gradual_decline", "sudden_drop", "seasonal"],
            p=[0.45, 0.25, 0.15, 0.15],
        )

        churn_month = np.random.randint(12, months) if churned else None

        for m in range(months):
            month_date = base_date + pd.DateOffset(months=m)

            # Skip if churned
            if churn_month is not None and m > churn_month:
                continue

            # Base MRR with pattern
            if pattern == "gradual_decline":
                decay = max(0.4, 1 - 0.025 * m)
                mrr = mrr_base * decay
            elif pattern == "sudden_drop" and m > 8:
                mrr = mrr_base * 0.55
            elif pattern == "seasonal":
                seasonal_factor = 1 + 0.15 * np.sin(2 * np.pi * m / 12)
                mrr = mrr_base * seasonal_factor
            else:
                mrr = mrr_base

            # Add noise
            mrr *= np.random.normal(1, 0.05)

            # Discount leakage — some reps give excessive discounts
            discount_pct = 0
            if np.random.random() < 0.30:
                if segment == "Enterprise":
                    discount_pct = np.random.choice([5, 10, 15, 20, 25, 30, 40],
                                                     p=[0.25, 0.25, 0.20, 0.15, 0.08, 0.05, 0.02])
                else:
                    discount_pct = np.random.choice([5, 10, 15, 20, 25, 30, 35, 40, 50],
                                                     p=[0.20, 0.20, 0.20, 0.15, 0.10, 0.07, 0.04, 0.02, 0.02])

            billed = mrr * (1 - discount_pct / 100)

            # Payment anomalies
            days_to_pay = int(np.random.lognormal(3, 0.5))
            payment_status = np.random.choice(
                ["paid", "paid_late", "partial", "failed", "pending"],
                p=[0.70, 0.12, 0.08, 0.05, 0.05],
            )
            collected = billed
            if payment_status == "partial":
                collected = billed * np.random.uniform(0.3, 0.8)
            elif payment_status == "failed":
                collected = 0
            elif payment_status == "pending":
                collected = 0

            # Usage / engagement proxy (0-100)
            if pattern == "gradual_decline":
                engagement = max(5, 80 - 3 * m + np.random.normal(0, 8))
            elif churned and churn_month and m >= churn_month - 3:
                engagement = max(0, 30 - 10 * (m - churn_month + 3) + np.random.normal(0, 5))
            else:
                engagement = min(100, max(0, 65 + np.random.normal(0, 15)))

            records.append({
                "customer_id": cid,
                "month": month_date.strftime("%Y-%m-01"),
                "segment": segment,
                "region": cust["region"],
                "industry": cust["industry"],
                "sales_rep": cust["sales_rep"],
                "mrr_contracted": round(mrr, 2),
                "discount_pct": discount_pct,
                "mrr_billed": round(billed, 2),
                "mrr_collected": round(collected, 2),
                "payment_status": payment_status,
                "days_to_pay": days_to_pay,
                "engagement_score": round(engagement, 1),
                "leakage_pattern": pattern,
            })

    return pd.DataFrame(records)


def generate_product_usage(customers_df, months=24):
    """Generate product feature usage data to detect silent churn signals."""
    records = []
    base_date = datetime(2024, 1, 1)
    features = ["Core Platform", "Analytics", "API", "Integrations", "Support Portal"]

    for _, cust in customers_df.iterrows():
        cid = cust["customer_id"]
        churned = cust["is_churned"]

        for m in range(months):
            month_date = base_date + pd.DateOffset(months=m)

            for feat in features:
                # Declining usage for churning customers
                base_usage = np.random.poisson(50)
                if churned and m > 12:
                    base_usage = int(base_usage * max(0.1, 1 - 0.08 * (m - 12)))

                records.append({
                    "customer_id": cid,
                    "month": month_date.strftime("%Y-%m-01"),
                    "feature": feat,
                    "sessions": max(0, base_usage),
                    "active_users": max(0, int(base_usage * 0.3 + np.random.normal(0, 3))),
                })

    return pd.DataFrame(records)


def save_data(output_dir):
    """Generate and save all datasets."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "raw"), exist_ok=True)

    print("Generating customers...")
    customers = generate_customers(500)
    customers.to_csv(os.path.join(output_dir, "raw", "customers.csv"), index=False)

    print("Generating monthly revenue...")
    revenue = generate_monthly_revenue(customers, months=24)
    revenue.to_csv(os.path.join(output_dir, "raw", "monthly_revenue.csv"), index=False)

    print("Generating product usage...")
    usage = generate_product_usage(customers, months=24)
    usage.to_csv(os.path.join(output_dir, "raw", "product_usage.csv"), index=False)

    print(f"Data saved to {output_dir}/raw/")
    print(f"  customers: {len(customers)} rows")
    print(f"  monthly_revenue: {len(revenue)} rows")
    print(f"  product_usage: {len(usage)} rows")

    return customers, revenue, usage


if __name__ == "__main__":
    save_data(os.path.join(os.path.dirname(__file__), "..", "data"))
