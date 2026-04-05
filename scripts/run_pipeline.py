"""
Revenue Leakage Intelligence System — Main Pipeline
Orchestrates: data generation → profiling → analysis → visualization → dashboard → validation
"""
import sys
import os
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.runtime import configure_runtime
configure_runtime(project_root)

import pandas as pd
from src.data_generator import save_data
from src.data_profiler import profile_dataframe, print_profile, check_suspicious_values
from src.leakage_analyzer import (
    detect_silent_churn,
    detect_deterioration,
    analyze_discounts,
    analyze_payments,
    analyze_concentration,
    build_leakage_scorecard,
    compute_summary_metrics,
)
from src.visualizations import generate_all_charts
from src.dashboard_builder import build_dashboard
from src.validators import run_all_validations, format_validation_report


def main():
    data_dir = os.path.join(project_root, "data")
    output_dir = os.path.join(project_root, "outputs")
    charts_dir = os.path.join(output_dir, "charts")
    dashboard_path = os.path.join(project_root, "dashboard", "index.html")

    # =========================================================================
    # STEP 1: Generate Synthetic Data
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: GENERATING SYNTHETIC BUSINESS DATA")
    print("=" * 70)
    customers, revenue, usage = save_data(data_dir)

    # =========================================================================
    # STEP 2: Data Profiling
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: DATA PROFILING & EXPLORATION")
    print("=" * 70)

    profiles = {}
    for name, df in [("customers", customers), ("monthly_revenue", revenue), ("product_usage", usage)]:
        profile = profile_dataframe(df, name)
        print_profile(profile)
        profiles[name] = profile

    # Check suspicious values
    print("\nSuspicious Value Checks:")
    for name, df in [("customers", customers), ("monthly_revenue", revenue)]:
        issues = check_suspicious_values(df, name)
        if issues:
            for issue in issues:
                print(f"  ⚠️ {issue}")
        else:
            print(f"  ✅ {name}: No suspicious values found")

    # Save profiles
    os.makedirs(os.path.join(output_dir, "reports"), exist_ok=True)
    with open(os.path.join(output_dir, "reports", "data_profiles.json"), "w") as f:
        # Convert non-serializable items
        serializable = {}
        for k, v in profiles.items():
            serializable[k] = {
                "row_count": int(v["row_count"]),
                "column_count": int(v["column_count"]),
                "duplicate_rows": int(v["duplicate_rows"]),
                "memory_mb": float(v["memory_mb"]),
            }
        json.dump(serializable, f, indent=2)

    # =========================================================================
    # STEP 3: Core Analysis
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: REVENUE LEAKAGE ANALYSIS")
    print("=" * 70)

    # 3a. Silent Churn Detection
    print("\n--- Silent Churn Detection ---")
    churn_results = detect_silent_churn(revenue, lookback=3)
    silent_churn_count = churn_results["silent_churn_risk"].sum()
    print(f"  Customers with silent churn signals: {silent_churn_count}")

    # 3b. Gradual Deterioration
    print("\n--- Gradual Deterioration Analysis ---")
    deterioration_results = detect_deterioration(revenue)
    deteriorating_count = deterioration_results["is_deteriorating"].sum()
    print(f"  Customers with sustained MRR decline: {deteriorating_count}")

    # 3c. Discount Analysis
    print("\n--- Discount Anomaly Detection ---")
    cust_discounts, rep_discounts, monthly_discounts = analyze_discounts(revenue)
    excessive_count = cust_discounts["excessive_discount"].sum()
    print(f"  Customers with excessive discounts (>25%): {excessive_count}")
    top_rep = rep_discounts.nlargest(1, "discount_revenue_impact")
    if len(top_rep) > 0:
        print(f"  Highest discount impact rep: {top_rep.iloc[0]['sales_rep']} "
              f"(${top_rep.iloc[0]['discount_revenue_impact']:,.0f})")

    # 3d. Payment Anomalies
    print("\n--- Payment Anomaly Detection ---")
    cust_payments, monthly_payments = analyze_payments(revenue)
    total_gap = cust_payments["total_gap"].sum()
    print(f"  Total collection gap: ${total_gap:,.0f}")
    low_collection = (cust_payments["collection_rate"] < 80).sum()
    print(f"  Customers with <80% collection rate: {low_collection}")

    # 3e. Revenue Concentration
    print("\n--- Revenue Concentration Analysis ---")
    concentration = analyze_concentration(revenue)
    print(f"  Top 10% customers: {concentration['top_10pct_revenue_share']:.1f}% of revenue")
    print(f"  HHI: {concentration['hhi']} ({concentration['hhi_interpretation']})")

    # 3f. Composite Scorecard
    print("\n--- Building Composite Risk Scorecard ---")
    scorecard = build_leakage_scorecard(
        churn_results, deterioration_results, cust_discounts, cust_payments, customers
    )
    print(f"  Risk distribution:")
    print(scorecard["risk_tier"].value_counts().to_string())

    # Summary metrics
    summary = compute_summary_metrics(scorecard, revenue, concentration)
    print(f"\n  Total ARR: ${summary['total_arr']:,.0f}")
    print(f"  Revenue at Risk: ${summary['total_revenue_at_risk']:,.0f} ({summary['pct_revenue_at_risk']:.1f}%)")

    # Save processed data
    os.makedirs(os.path.join(data_dir, "processed"), exist_ok=True)
    scorecard.to_csv(os.path.join(data_dir, "processed", "risk_scorecard.csv"), index=False)
    cust_payments.to_csv(os.path.join(data_dir, "processed", "payment_analysis.csv"), index=False)
    cust_discounts.to_csv(os.path.join(data_dir, "processed", "discount_analysis.csv"), index=False)
    rep_discounts.to_csv(os.path.join(data_dir, "processed", "rep_discount_impact.csv"), index=False)
    deterioration_results.to_csv(os.path.join(data_dir, "processed", "deterioration_analysis.csv"), index=False)
    print(f"\n  Processed data saved to {data_dir}/processed/")

    # Save summary metrics
    with open(os.path.join(output_dir, "reports", "summary_metrics.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # =========================================================================
    # STEP 4: Visualizations
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 4: GENERATING VISUALIZATIONS")
    print("=" * 70)
    generate_all_charts(revenue, scorecard, summary, rep_discounts, monthly_payments, charts_dir)

    # =========================================================================
    # STEP 5: Executive Dashboard
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 5: BUILDING EXECUTIVE DASHBOARD")
    print("=" * 70)
    build_dashboard(scorecard, summary, concentration, charts_dir, dashboard_path)

    # =========================================================================
    # STEP 6: Validation
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 6: VALIDATION CHECKS")
    print("=" * 70)
    validation_results = run_all_validations(customers, revenue, scorecard, summary)
    report = format_validation_report(validation_results)
    print(report)

    # Save validation report
    with open(os.path.join(output_dir, "reports", "validation_report.txt"), "w") as f:
        f.write(report)

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nFiles generated:")
    print(f"  Data:       {data_dir}/raw/ (3 files)")
    print(f"  Processed:  {data_dir}/processed/ (5 files)")
    print(f"  Charts:     {charts_dir}/ (7 charts)")
    print(f"  Dashboard:  {dashboard_path}")
    print(f"  Reports:    {output_dir}/reports/ (3 files)")
    print(f"\nKey Findings:")
    print(f"  • ${summary['total_revenue_at_risk']:,.0f} revenue at risk ({summary['pct_revenue_at_risk']:.1f}% of ARR)")
    print(f"  • {summary['critical_risk_customers']} critical + {summary['high_risk_customers']} high risk customers")
    print(f"  • Collection rate: {summary['overall_collection_rate']:.1f}%")
    print(f"  • Top 10% concentration: {summary['top_10pct_concentration']:.1f}%")


if __name__ == "__main__":
    main()
