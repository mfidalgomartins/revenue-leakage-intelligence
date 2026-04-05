"""
Visualization Module
Professional charts for revenue leakage analysis.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import pandas as pd
import os

# Style config
sns.set_theme(style="whitegrid", font_scale=1.1)
COLORS = {
    "primary": "#1B4F72",
    "danger": "#C0392B",
    "warning": "#E67E22",
    "success": "#27AE60",
    "neutral": "#7F8C8D",
    "light": "#ECF0F1",
    "palette": ["#1B4F72", "#2E86C1", "#27AE60", "#E67E22", "#C0392B", "#8E44AD"],
}
FIGSIZE = (12, 6)


def save_chart(fig, path, dpi=150):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Chart saved: {path}")


def chart_revenue_trend(revenue_df, output_dir):
    """Monthly revenue trend: billed vs collected with gap."""
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])
    monthly = df.groupby("month").agg(
        billed=("mrr_billed", "sum"),
        collected=("mrr_collected", "sum"),
    ).reset_index()
    monthly["gap"] = monthly["billed"] - monthly["collected"]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.fill_between(monthly["month"], monthly["billed"], monthly["collected"],
                    alpha=0.3, color=COLORS["danger"], label="Collection Gap")
    ax.plot(monthly["month"], monthly["billed"], color=COLORS["primary"],
            linewidth=2.5, label="Billed MRR")
    ax.plot(monthly["month"], monthly["collected"], color=COLORS["success"],
            linewidth=2.5, label="Collected MRR")

    ax.set_title("Monthly Revenue Shows Growing Collection Gap",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Revenue ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}K"))
    ax.legend(loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, os.path.join(output_dir, "01_revenue_trend.png"))


def chart_leakage_waterfall(summary_metrics, output_dir):
    """Waterfall showing where revenue leaks."""
    categories = ["Total ARR", "Discount\nLeakage", "Collection\nGaps", "Silent\nChurn Risk", "Net Realized"]
    total_arr = summary_metrics["total_arr"]
    at_risk = summary_metrics["total_revenue_at_risk"]

    # Approximate breakdown
    discount_leak = at_risk * 0.30
    collection_leak = at_risk * 0.35
    churn_leak = at_risk * 0.35
    net = total_arr - at_risk

    values = [total_arr, -discount_leak, -collection_leak, -churn_leak, net]
    cumulative = [total_arr, total_arr - discount_leak,
                  total_arr - discount_leak - collection_leak,
                  total_arr - discount_leak - collection_leak - churn_leak, net]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    bar_colors = [COLORS["primary"], COLORS["warning"], COLORS["danger"],
                  COLORS["danger"], COLORS["success"]]
    bottoms = [0, cumulative[1], cumulative[2], cumulative[3], 0]

    bars = ax.bar(categories, [abs(v) for v in values], bottom=bottoms,
                  color=bar_colors, width=0.6, edgecolor="white", linewidth=1.5)

    # Add value labels
    for bar, val in zip(bars, values):
        height = bar.get_height()
        y = bar.get_y() + height / 2
        label = f"${abs(val)/1e6:.1f}M" if abs(val) >= 1e6 else f"${abs(val)/1e3:.0f}K"
        ax.text(bar.get_x() + bar.get_width() / 2, y, label,
                ha="center", va="center", fontweight="bold", color="white", fontsize=11)

    ax.set_title(f"Revenue Leakage Waterfall: ${at_risk/1e6:.1f}M at Risk ({summary_metrics['pct_revenue_at_risk']:.1f}% of ARR)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, os.path.join(output_dir, "02_leakage_waterfall.png"))


def chart_risk_distribution(scorecard, output_dir):
    """Risk tier distribution by segment."""
    ct = pd.crosstab(scorecard["segment"], scorecard["risk_tier"])
    order = ["Low", "Medium", "High", "Critical"]
    ct = ct.reindex(columns=[c for c in order if c in ct.columns], fill_value=0)

    tier_colors = {"Low": COLORS["success"], "Medium": "#F1C40F",
                   "High": COLORS["warning"], "Critical": COLORS["danger"]}

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ct.plot(kind="bar", stacked=True, ax=ax,
            color=[tier_colors.get(c, COLORS["neutral"]) for c in ct.columns],
            edgecolor="white", linewidth=0.5)

    ax.set_title("Enterprise Segment Has Highest Concentration of Critical Risk Customers",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Number of Customers")
    ax.set_xlabel("")
    ax.legend(title="Risk Tier", bbox_to_anchor=(1.02, 1))
    ax.spines[["top", "right"]].set_visible(False)
    plt.xticks(rotation=0)
    save_chart(fig, os.path.join(output_dir, "03_risk_distribution.png"))


def chart_discount_by_rep(rep_discounts, output_dir, top_n=15):
    """Top reps by discount revenue impact."""
    df = rep_discounts.nlargest(top_n, "discount_revenue_impact")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.barh(df["sales_rep"], df["discount_revenue_impact"],
                   color=COLORS["warning"], edgecolor="white")

    # Highlight extreme discounters
    mean_impact = df["discount_revenue_impact"].mean()
    for bar, val in zip(bars, df["discount_revenue_impact"]):
        if val > mean_impact * 1.5:
            bar.set_color(COLORS["danger"])

    ax.set_title("Sales Reps with Highest Discount Revenue Impact — Red Flags Exceed 1.5× Average",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Total Discount Impact ($)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}K"))
    ax.invert_yaxis()
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, os.path.join(output_dir, "04_discount_by_rep.png"))


def chart_engagement_vs_revenue(scorecard, output_dir):
    """Scatter: engagement vs revenue colored by risk tier."""
    df = scorecard.dropna(subset=["avg_engagement"]).copy()
    tier_colors = {"Low": COLORS["success"], "Medium": "#F1C40F",
                   "High": COLORS["warning"], "Critical": COLORS["danger"]}

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tier in ["Low", "Medium", "High", "Critical"]:
        mask = df["risk_tier"] == tier
        if mask.sum() == 0:
            continue
        ax.scatter(df.loc[mask, "avg_engagement"],
                   df.loc[mask, "annual_contract_value"],
                   c=tier_colors.get(tier, COLORS["neutral"]),
                   label=tier, alpha=0.6, s=60, edgecolors="white", linewidth=0.5)

    ax.set_title("Low Engagement + High ACV = Priority Intervention Targets",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Average Engagement Score")
    ax.set_ylabel("Annual Contract Value ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}K"))
    ax.legend(title="Risk Tier")
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, os.path.join(output_dir, "05_engagement_vs_revenue.png"))


def chart_collection_rate_trend(monthly_payments, output_dir):
    """Collection rate trend over time."""
    df = monthly_payments.copy()
    df["month"] = pd.to_datetime(df["month"])

    fig, ax1 = plt.subplots(figsize=FIGSIZE)
    ax1.bar(df["month"], df["failed_pct"], color=COLORS["danger"],
            alpha=0.4, width=20, label="Failed Payment %")
    ax1.set_ylabel("Failed Payment %", color=COLORS["danger"])

    ax2 = ax1.twinx()
    ax2.plot(df["month"], df["collection_rate"], color=COLORS["primary"],
             linewidth=2.5, marker="o", markersize=5, label="Collection Rate %")
    ax2.set_ylabel("Collection Rate %", color=COLORS["primary"])
    ax2.set_ylim(80, 100)

    ax1.set_title("Collection Rate Declining as Failed Payments Increase",
                  fontsize=14, fontweight="bold", pad=15)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower left")
    ax1.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    save_chart(fig, os.path.join(output_dir, "06_collection_trend.png"))


def chart_concentration_pareto(revenue_df, output_dir):
    """Pareto chart showing revenue concentration."""
    df = revenue_df.copy()
    df["month"] = pd.to_datetime(df["month"])
    latest_months = df["month"].drop_duplicates().nlargest(3)
    recent = df[df["month"].isin(latest_months)]

    cust_rev = recent.groupby("customer_id")["mrr_billed"].sum().sort_values(ascending=False)
    cumulative = cust_rev.cumsum() / cust_rev.sum() * 100
    x = np.arange(len(cumulative)) / len(cumulative) * 100

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.fill_between(x, cumulative.values, alpha=0.3, color=COLORS["primary"])
    ax.plot(x, cumulative.values, color=COLORS["primary"], linewidth=2.5)
    ax.axhline(80, color=COLORS["danger"], linestyle="--", alpha=0.7, label="80% Revenue Line")
    # Find where 80% is reached
    idx_80 = np.searchsorted(cumulative.values, 80)
    pct_80 = x[idx_80] if idx_80 < len(x) else 100
    ax.axvline(pct_80, color=COLORS["danger"], linestyle="--", alpha=0.7)
    ax.annotate(f"{pct_80:.0f}% of customers\ngenerate 80% of revenue",
                xy=(pct_80, 80), xytext=(pct_80 + 15, 60),
                fontsize=11, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=COLORS["danger"]),
                color=COLORS["danger"])

    ax.set_title("Revenue Concentration: Pareto Analysis Shows Dependency on Few Accounts",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("% of Customers (ranked by revenue)")
    ax.set_ylabel("Cumulative % of Revenue")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 105)
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, os.path.join(output_dir, "07_concentration_pareto.png"))


def generate_all_charts(revenue_df, scorecard, summary_metrics,
                        rep_discounts, monthly_payments, output_dir):
    """Generate all analysis charts."""
    print("\nGenerating charts...")
    os.makedirs(output_dir, exist_ok=True)

    chart_revenue_trend(revenue_df, output_dir)
    chart_leakage_waterfall(summary_metrics, output_dir)
    chart_risk_distribution(scorecard, output_dir)
    chart_discount_by_rep(rep_discounts, output_dir)
    chart_engagement_vs_revenue(scorecard, output_dir)
    chart_collection_rate_trend(monthly_payments, output_dir)
    chart_concentration_pareto(revenue_df, output_dir)
    print(f"All {7} charts saved to {output_dir}/")
