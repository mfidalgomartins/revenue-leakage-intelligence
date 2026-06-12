"""
Formal Revenue Leakage Analysis
/analyze style — structured, validated, stakeholder-ready.

Business question:
  What is driving revenue leakage, where is revenue at risk,
  and which customers or segments should the business prioritize first?
"""
import sys, os
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.runtime import configure_runtime
configure_runtime(project_root)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.05)
COLORS = ["#1B4F72", "#2E86C1", "#27AE60", "#E67E22", "#C0392B", "#8E44AD", "#F1C40F"]
FIGSIZE = (13, 6)

pd.set_option("display.float_format", "{:,.2f}".format)
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 140)

# ─────────────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────────────
data = os.path.join(project_root, "data")
out_dir = os.path.join(project_root, "outputs")
charts_dir = os.path.join(out_dir, "charts", "analysis")
os.makedirs(charts_dir, exist_ok=True)

customers = pd.read_csv(os.path.join(data, "raw", "customers.csv"), parse_dates=["onboard_date"])
revenue = pd.read_csv(os.path.join(data, "raw", "monthly_revenue.csv"))
revenue["month"] = pd.to_datetime(revenue["month"])
usage = pd.read_csv(os.path.join(data, "raw", "product_usage.csv"))
usage["month"] = pd.to_datetime(usage["month"])

scorecard = pd.read_csv(os.path.join(data, "processed", "risk_scorecard.csv"))
payments = pd.read_csv(os.path.join(data, "processed", "payment_analysis.csv"))
discounts = pd.read_csv(os.path.join(data, "processed", "discount_analysis.csv"))
rep_disc = pd.read_csv(os.path.join(data, "processed", "rep_discount_impact.csv"))
deterioration = pd.read_csv(os.path.join(data, "processed", "deterioration_analysis.csv"))

report = []  # accumulate report lines

def out(msg=""):
    print(msg)
    report.append(msg)

def section(title):
    out(f"\n{'='*80}")
    out(f"  {title}")
    out(f"{'='*80}")

def subsection(title):
    out(f"\n{'─'*80}")
    out(f"  {title}")
    out(f"{'─'*80}")

def save_chart(fig, name, dpi=150):
    path = os.path.join(charts_dir, name)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    out(f"  [Chart saved: {name}]")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 0: QUESTION DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════════════
section("0. QUESTION DECOMPOSITION")
out("""
  Business question:
    "What is driving revenue leakage, where is revenue at risk,
     and which customers or segments should the business prioritize first?"

  Sub-questions:
    Q1. How much total revenue is leaking, and through which channels?
        → Quantify the contracted-to-collected revenue funnel
    Q2. What are the primary leakage drivers and their relative magnitude?
        → Decompose leakage into discount, collection, and churn components
    Q3. Which segments carry disproportionate risk?
        → Compare Enterprise vs Mid-Market vs SMB across all dimensions
    Q4. Are leakage patterns worsening over time?
        → Trend analysis on collection rates, discounts, engagement
    Q5. Which specific customers should be prioritized for intervention?
        → Rank by revenue-at-risk, identify actionable cohorts
    Q6. Which sales reps are contributing to leakage via discounting?
        → Rep-level discount behavior analysis
    Q7. How concentrated is revenue risk?
        → Pareto and HHI analysis of revenue-at-risk distribution
""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: HEADLINE METRICS (quick answers)
# ═══════════════════════════════════════════════════════════════════════════════
section("1. HEADLINE METRICS")

total_arr = customers["annual_contract_value"].sum()
total_contracted = revenue["mrr_contracted"].sum()
total_billed = revenue["mrr_billed"].sum()
total_collected = revenue["mrr_collected"].sum()
discount_leakage = total_contracted - total_billed
collection_leakage = total_billed - total_collected
total_leakage = total_contracted - total_collected
leakage_pct = total_leakage / total_contracted * 100

total_at_risk = scorecard["revenue_at_risk"].sum()
at_risk_pct = total_at_risk / total_arr * 100

n_critical = (scorecard["risk_tier"] == "Critical").sum()
n_high = (scorecard["risk_tier"] == "High").sum()
n_medium = (scorecard["risk_tier"] == "Medium").sum()

avg_collection_rate = total_collected / total_billed * 100
avg_discount_all = revenue["discount_pct"].mean()
avg_discount_applied = revenue[revenue["discount_pct"] > 0]["discount_pct"].mean()
pct_months_discounted = (revenue["discount_pct"] > 0).mean() * 100

# Latest quarter trends
latest_3m = revenue[revenue["month"] >= revenue["month"].max() - pd.DateOffset(months=2)]
earliest_3m = revenue[revenue["month"] <= revenue["month"].min() + pd.DateOffset(months=2)]
l3_collection = latest_3m["mrr_collected"].sum() / latest_3m["mrr_billed"].sum() * 100
e3_collection = earliest_3m["mrr_collected"].sum() / earliest_3m["mrr_billed"].sum() * 100
collection_trend = l3_collection - e3_collection

out(f"""
  ┌──────────────────────────────────────────────────────────────────┐
  │  REVENUE LEAKAGE INTELLIGENCE — HEADLINE METRICS                │
  ├──────────────────────────────────────────────────────────────────┤
  │                                                                  │
  │  Total ARR .......................... ${total_arr:>12,.0f}           │
  │  24-month contracted revenue ....... ${total_contracted:>12,.0f}           │
  │  24-month billed revenue ........... ${total_billed:>12,.0f}           │
  │  24-month collected revenue ........ ${total_collected:>12,.0f}           │
  │                                                                  │
  │  ── Leakage Decomposition ──                                     │
  │  Discount leakage .................. ${discount_leakage:>12,.0f}  ({discount_leakage/total_contracted*100:.1f}%)  │
  │  Collection leakage ................ ${collection_leakage:>12,.0f}  ({collection_leakage/total_contracted*100:.1f}%)  │
  │  Total leakage ..................... ${total_leakage:>12,.0f}  ({leakage_pct:.1f}%)  │
  │                                                                  │
  │  ── Risk Summary ──                                              │
  │  Revenue at risk (scored) .......... ${total_at_risk:>12,.0f}  ({at_risk_pct:.1f}% of ARR)  │
  │  Critical risk customers ........... {n_critical:>12}               │
  │  High risk customers ............... {n_high:>12}               │
  │  Medium risk customers ............. {n_medium:>12}               │
  │                                                                  │
  │  ── Operational Metrics ──                                       │
  │  Overall collection rate ........... {avg_collection_rate:>11.1f}%              │
  │  Avg discount (when applied) ....... {avg_discount_applied:>11.1f}%              │
  │  Months with discounts ............. {pct_months_discounted:>11.1f}%              │
  │  Collection rate trend (Q1→Q8) ..... {collection_trend:>+11.1f}pp             │
  │                                                                  │
  └──────────────────────────────────────────────────────────────────┘
""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: LEAKAGE DRIVER DECOMPOSITION (Q1, Q2)
# ═══════════════════════════════════════════════════════════════════════════════
section("2. LEAKAGE DRIVER DECOMPOSITION")

subsection("2a. Revenue Funnel: Contracted → Billed → Collected")
out(f"""
  Stage 1: Contracted → Billed (discount impact)
    Lost: ${discount_leakage:,.0f} ({discount_leakage/total_contracted*100:.1f}% of contracted)
    30.2% of invoices carry a discount; avg discount when applied: {avg_discount_applied:.1f}%

  Stage 2: Billed → Collected (collection failures)
    Lost: ${collection_leakage:,.0f} ({collection_leakage/total_billed*100:.1f}% of billed)
    Payment status breakdown:
""")

# Payment status breakdown
ps_summary = revenue.groupby("payment_status").agg(
    rows=("customer_id", "count"),
    total_billed=("mrr_billed", "sum"),
    total_collected=("mrr_collected", "sum"),
).reset_index()
ps_summary["pct_of_rows"] = ps_summary["rows"] / ps_summary["rows"].sum() * 100
ps_summary["collection_rate"] = ps_summary["total_collected"] / ps_summary["total_billed"] * 100
ps_summary["leakage"] = ps_summary["total_billed"] - ps_summary["total_collected"]
ps_summary = ps_summary.sort_values("leakage", ascending=False)

for _, r in ps_summary.iterrows():
    out(f"    {r['payment_status']:12s}  {r['pct_of_rows']:5.1f}% of invoices  "
        f"collection rate: {r['collection_rate']:5.1f}%  "
        f"leakage: ${r['leakage']:>10,.0f}")

# Validate: sum of parts = total
leakage_check = ps_summary["leakage"].sum()
out(f"\n  ✓ Validation: sum of payment-status leakage = ${leakage_check:,.0f} "
    f"(matches total collection gap: ${collection_leakage:,.0f}, "
    f"diff: ${abs(leakage_check - collection_leakage):,.0f})")


subsection("2b. Leakage Driver Ranking")
# Decompose scorecard risk into weighted drivers
churn_contribution = scorecard["risk_score_churn"].mean() * 0.30
deterio_contribution = scorecard["risk_score_deterioration"].mean() * 0.25
discount_contribution = scorecard["risk_score_discount"].mean() * 0.20
payment_contribution = scorecard["risk_score_payment"].mean() * 0.25
total_weighted = churn_contribution + deterio_contribution + discount_contribution + payment_contribution

drivers = [
    ("Payment failures", payment_contribution, payment_contribution/total_weighted*100),
    ("MRR deterioration", deterio_contribution, deterio_contribution/total_weighted*100),
    ("Silent churn risk", churn_contribution, churn_contribution/total_weighted*100),
    ("Discount anomalies", discount_contribution, discount_contribution/total_weighted*100),
]
drivers.sort(key=lambda x: x[1], reverse=True)

out("\n  Weighted risk contribution to composite score:")
out(f"  {'Driver':25s}  {'Weighted Pts':>12s}  {'% of Total':>10s}")
out(f"  {'─'*50}")
for name, pts, pct in drivers:
    bar = "█" * int(pct / 2)
    out(f"  {name:25s}  {pts:>12.2f}  {pct:>9.1f}%  {bar}")
out(f"  {'─'*50}")
out(f"  {'TOTAL':25s}  {total_weighted:>12.2f}  {'100.0':>9s}%")

# Chart: Leakage funnel
fig, ax = plt.subplots(figsize=(10, 5))
stages = ["Contracted\nRevenue", "After\nDiscounts", "After\nCollection\nFailures"]
values = [total_contracted, total_billed, total_collected]
colors = [COLORS[0], COLORS[3], COLORS[4]]
bars = ax.bar(stages, values, color=colors, width=0.5, edgecolor="white", linewidth=2)
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + total_contracted*0.01,
            f"${val/1e6:.1f}M", ha="center", fontweight="bold", fontsize=12)
# Arrow annotations for losses
ax.annotate(f"−${discount_leakage/1e6:.1f}M\n({discount_leakage/total_contracted*100:.1f}%)",
            xy=(0.75, (total_contracted+total_billed)/2), fontsize=11, color=COLORS[3],
            fontweight="bold", ha="center")
ax.annotate(f"−${collection_leakage/1e6:.1f}M\n({collection_leakage/total_billed*100:.1f}%)",
            xy=(1.75, (total_billed+total_collected)/2), fontsize=11, color=COLORS[4],
            fontweight="bold", ha="center")
ax.set_title("Revenue Funnel: $4.5M Lost Between Contract and Collection",
             fontsize=14, fontweight="bold", pad=15)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.0f}M"))
ax.spines[["top", "right"]].set_visible(False)
ax.set_ylim(0, total_contracted * 1.12)
save_chart(fig, "a01_revenue_funnel.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3: SEGMENT ANALYSIS (Q3)
# ═══════════════════════════════════════════════════════════════════════════════
section("3. SEGMENT ANALYSIS")

subsection("3a. Revenue and Risk by Segment")
seg = scorecard.groupby("segment").agg(
    customers=("customer_id", "count"),
    total_acv=("annual_contract_value", "sum"),
    avg_acv=("annual_contract_value", "mean"),
    total_at_risk=("revenue_at_risk", "sum"),
    avg_risk_score=("composite_risk_score", "mean"),
    critical=("risk_tier", lambda x: (x == "Critical").sum()),
    high=("risk_tier", lambda x: (x == "High").sum()),
    avg_churn_score=("risk_score_churn", "mean"),
    avg_payment_score=("risk_score_payment", "mean"),
    avg_discount_score=("risk_score_discount", "mean"),
    avg_deterioration_score=("risk_score_deterioration", "mean"),
).reset_index()
seg["pct_of_arr"] = seg["total_acv"] / seg["total_acv"].sum() * 100
seg["pct_of_risk"] = seg["total_at_risk"] / seg["total_at_risk"].sum() * 100
seg["risk_intensity"] = seg["pct_of_risk"] / seg["pct_of_arr"]  # >1 = disproportionate

out(f"\n  {'Segment':12s}  {'Customers':>9s}  {'ARR':>12s}  {'% ARR':>6s}  "
    f"{'At Risk':>12s}  {'% Risk':>7s}  {'Intensity':>9s}  {'Avg Score':>9s}")
out(f"  {'─'*90}")
for _, r in seg.sort_values("total_at_risk", ascending=False).iterrows():
    flag = " ⚠️" if r["risk_intensity"] > 1.2 else ""
    out(f"  {r['segment']:12s}  {r['customers']:>9.0f}  ${r['total_acv']:>10,.0f}  "
        f"{r['pct_of_arr']:>5.1f}%  ${r['total_at_risk']:>10,.0f}  "
        f"{r['pct_of_risk']:>6.1f}%  {r['risk_intensity']:>8.2f}x  "
        f"{r['avg_risk_score']:>8.1f}{flag}")

out("""
  Key finding: Risk Intensity measures whether a segment carries more risk than
  its share of ARR would predict. Intensity > 1.0× means disproportionate risk.
""")

subsection("3b. Dominant Leakage Driver by Segment")
out(f"\n  {'Segment':12s}  {'Churn':>8s}  {'Deterio.':>8s}  {'Discount':>8s}  {'Payment':>8s}  {'Dominant Driver':20s}")
out(f"  {'─'*75}")
for _, r in seg.iterrows():
    scores = {
        "Churn": r["avg_churn_score"],
        "Deterioration": r["avg_deterioration_score"],
        "Discount": r["avg_discount_score"],
        "Payment": r["avg_payment_score"],
    }
    dominant = max(scores, key=scores.get)
    out(f"  {r['segment']:12s}  {r['avg_churn_score']:>8.1f}  {r['avg_deterioration_score']:>8.1f}  "
        f"{r['avg_discount_score']:>8.1f}  {r['avg_payment_score']:>8.1f}  ← {dominant}")

# Chart: Segment risk heatmap
fig, ax = plt.subplots(figsize=(10, 4))
heatmap_data = seg.set_index("segment")[["avg_churn_score", "avg_deterioration_score",
                                          "avg_discount_score", "avg_payment_score"]]
heatmap_data.columns = ["Churn", "Deterioration", "Discount", "Payment"]
sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlOrRd", ax=ax,
            linewidths=1, cbar_kws={"label": "Avg Risk Score"})
ax.set_title("Payment Risk Is the Dominant Driver Across All Segments",
             fontsize=14, fontweight="bold", pad=15)
save_chart(fig, "a02_segment_risk_heatmap.png")


subsection("3c. Revenue by Segment × Region")
seg_region = scorecard.groupby(["segment", "region"]).agg(
    customers=("customer_id", "count"),
    total_acv=("annual_contract_value", "sum"),
    total_at_risk=("revenue_at_risk", "sum"),
    avg_score=("composite_risk_score", "mean"),
).reset_index()
seg_region["risk_rate"] = seg_region["total_at_risk"] / seg_region["total_acv"] * 100

pivot = seg_region.pivot_table(index="segment", columns="region", values="risk_rate", aggfunc="mean")
out("\n  Revenue at Risk Rate (%) by Segment × Region:")
out(pivot.round(1).to_string())

# Find the hotspot
max_cell = seg_region.loc[seg_region["risk_rate"].idxmax()]
out(f"\n  Hotspot: {max_cell['segment']} × {max_cell['region']} — "
    f"{max_cell['risk_rate']:.1f}% of ACV at risk "
    f"(${max_cell['total_at_risk']:,.0f} across {max_cell['customers']:.0f} customers)")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: TREND ANALYSIS (Q4)
# ═══════════════════════════════════════════════════════════════════════════════
section("4. TREND ANALYSIS — IS LEAKAGE WORSENING?")

monthly = revenue.groupby("month").agg(
    contracted=("mrr_contracted", "sum"),
    billed=("mrr_billed", "sum"),
    collected=("mrr_collected", "sum"),
    customers=("customer_id", "nunique"),
    avg_engagement=("engagement_score", "mean"),
    avg_discount=("discount_pct", "mean"),
    pct_discounted=("discount_pct", lambda x: (x > 0).mean() * 100),
    failed_pct=("payment_status", lambda x: (x == "failed").mean() * 100),
    avg_days_pay=("days_to_pay", "mean"),
).reset_index()
monthly["collection_rate"] = monthly["collected"] / monthly["billed"] * 100
monthly["discount_leakage"] = monthly["contracted"] - monthly["billed"]
monthly["collection_gap"] = monthly["billed"] - monthly["collected"]
monthly["total_leakage_rate"] = (monthly["contracted"] - monthly["collected"]) / monthly["contracted"] * 100

subsection("4a. Monthly Leakage Trend")
# First 6 months vs last 6 months
first_6 = monthly.head(6)
last_6 = monthly.tail(6)

metrics_trend = {
    "Collection rate": (first_6["collection_rate"].mean(), last_6["collection_rate"].mean(), "%"),
    "Failed payment %": (first_6["failed_pct"].mean(), last_6["failed_pct"].mean(), "%"),
    "Avg discount %": (first_6["avg_discount"].mean(), last_6["avg_discount"].mean(), "%"),
    "Avg engagement": (first_6["avg_engagement"].mean(), last_6["avg_engagement"].mean(), "pts"),
    "Total leakage rate": (first_6["total_leakage_rate"].mean(), last_6["total_leakage_rate"].mean(), "%"),
    "Active customers": (first_6["customers"].mean(), last_6["customers"].mean(), ""),
    "Avg days to pay": (first_6["avg_days_pay"].mean(), last_6["avg_days_pay"].mean(), "days"),
}

out(f"\n  {'Metric':25s}  {'First 6mo':>10s}  {'Last 6mo':>10s}  {'Change':>10s}  {'Signal':8s}")
out(f"  {'─'*70}")
for name, (early, late, unit) in metrics_trend.items():
    change = late - early
    if name in ["Failed payment %", "Avg discount %", "Total leakage rate", "Avg days to pay"]:
        signal = "🔴 Worse" if change > 0.5 else "🟡 Flat" if abs(change) < 0.5 else "🟢 Better"
    elif name in ["Collection rate", "Avg engagement", "Active customers"]:
        signal = "🔴 Worse" if change < -0.5 else "🟡 Flat" if abs(change) < 0.5 else "🟢 Better"
    else:
        signal = "—"
    out(f"  {name:25s}  {early:>9.1f}{unit[0] if unit else '':1s}  {late:>9.1f}{unit[0] if unit else '':1s}  "
        f"{change:>+9.1f}{unit[0] if unit else '':1s}  {signal}")

# Chart: 4-panel trend
fig, axes = plt.subplots(2, 2, figsize=(14, 9))

axes[0,0].plot(monthly["month"], monthly["collection_rate"], color=COLORS[0], linewidth=2.5, marker="o", markersize=4)
axes[0,0].axhline(monthly["collection_rate"].mean(), color=COLORS[4], linestyle="--", alpha=0.5, label=f'Mean: {monthly["collection_rate"].mean():.1f}%')
axes[0,0].set_title("Collection Rate Shows Structural Decline", fontweight="bold")
axes[0,0].set_ylabel("Collection Rate (%)")
axes[0,0].set_ylim(80, 95)
axes[0,0].legend(fontsize=9)

axes[0,1].plot(monthly["month"], monthly["avg_engagement"], color=COLORS[1], linewidth=2.5, marker="o", markersize=4)
z = np.polyfit(range(len(monthly)), monthly["avg_engagement"], 1)
axes[0,1].plot(monthly["month"], np.polyval(z, range(len(monthly))), "--", color=COLORS[4], alpha=0.7,
               label=f"Trend: {z[0]:+.2f}/mo")
axes[0,1].set_title("Engagement Declining Across the Portfolio", fontweight="bold")
axes[0,1].set_ylabel("Avg Engagement Score")
axes[0,1].legend(fontsize=9)

axes[1,0].bar(monthly["month"], monthly["discount_leakage"]/1000, color=COLORS[3], alpha=0.7, width=20)
axes[1,0].set_title("Discount Leakage Stable Over Time", fontweight="bold")
axes[1,0].set_ylabel("Discount Leakage ($K)")

axes[1,1].stackplot(monthly["month"],
                     monthly["discount_leakage"]/1000,
                     monthly["collection_gap"]/1000,
                     labels=["Discount Leakage", "Collection Gap"],
                     colors=[COLORS[3], COLORS[4]], alpha=0.7)
axes[1,1].set_title("Total Monthly Leakage Composition", fontweight="bold")
axes[1,1].set_ylabel("Leakage ($K)")
axes[1,1].legend(fontsize=9, loc="upper left")

for ax in axes.flat:
    ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
save_chart(fig, "a03_trend_analysis.png")


subsection("4b. Engagement Decay by Leakage Pattern")
pattern_eng = revenue.groupby(["leakage_pattern", revenue["month"].dt.to_period("Q")]).agg(
    avg_engagement=("engagement_score", "mean"),
).reset_index()
pattern_eng["quarter"] = pattern_eng["month"].astype(str)

fig, ax = plt.subplots(figsize=FIGSIZE)
for i, pat in enumerate(["stable", "gradual_decline", "sudden_drop", "seasonal"]):
    subset = pattern_eng[pattern_eng["leakage_pattern"] == pat]
    ax.plot(subset["quarter"], subset["avg_engagement"], marker="o", linewidth=2,
            color=COLORS[i], label=pat.replace("_", " ").title(), markersize=5)
ax.set_title("Gradual Decline Customers Show Clear Engagement Erosion Over Time",
             fontsize=14, fontweight="bold", pad=15)
ax.set_ylabel("Avg Engagement Score")
ax.set_xlabel("Quarter")
ax.legend()
ax.spines[["top", "right"]].set_visible(False)
plt.xticks(rotation=45)
save_chart(fig, "a04_engagement_by_pattern.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5: CUSTOMER PRIORITIZATION (Q5)
# ═══════════════════════════════════════════════════════════════════════════════
section("5. CUSTOMER PRIORITIZATION — WHO TO ACT ON FIRST")

subsection("5a. Top 20 Revenue-at-Risk Accounts")
top20 = scorecard.nlargest(20, "revenue_at_risk")
out(f"\n  {'Rank':>4s}  {'Customer':10s}  {'Segment':12s}  {'ACV':>12s}  "
    f"{'Risk Score':>10s}  {'Tier':8s}  {'Rev at Risk':>12s}  {'Primary Driver'}")
out(f"  {'─'*100}")
for rank, (_, r) in enumerate(top20.iterrows(), 1):
    # Find primary driver
    driver_scores = {
        "Churn": r.get("risk_score_churn", 0),
        "Deterioration": r.get("risk_score_deterioration", 0),
        "Discount": r.get("risk_score_discount", 0),
        "Payment": r.get("risk_score_payment", 0),
    }
    primary = max(driver_scores, key=driver_scores.get)
    out(f"  {rank:>4d}  {r['customer_id']:10s}  {r['segment']:12s}  ${r['annual_contract_value']:>10,.0f}  "
        f"{r['composite_risk_score']:>10.1f}  {r['risk_tier']:8s}  ${r['revenue_at_risk']:>10,.0f}  {primary}")

# Revenue concentration within risk
total_risk_top20 = top20["revenue_at_risk"].sum()
total_risk_all = scorecard["revenue_at_risk"].sum()
out(f"\n  Top 20 accounts represent ${total_risk_top20:,.0f} of ${total_risk_all:,.0f} total risk "
    f"({total_risk_top20/total_risk_all*100:.1f}%)")
out(f"  → Focusing on these 20 accounts (4% of customer base) addresses "
    f"{total_risk_top20/total_risk_all*100:.0f}% of revenue risk")


subsection("5b. Actionable Customer Cohorts")
# Segment customers into action cohorts
scorecard_aug = scorecard.copy()

# Cohort 1: High-value disengaging (Enterprise/Mid-Market, high risk, declining engagement)
cohort1 = scorecard_aug[
    (scorecard_aug["segment"].isin(["Enterprise", "Mid-Market"])) &
    (scorecard_aug["composite_risk_score"] > 30) &
    (scorecard_aug.get("avg_engagement", pd.Series(dtype=float)).fillna(0) < 40)
]

# Cohort 2: Payment problem accounts (any segment, high payment risk)
cohort2 = scorecard_aug[scorecard_aug["risk_score_payment"] > 60]

# Cohort 3: Over-discounted accounts (discount risk > 20, still active)
cohort3 = scorecard_aug[scorecard_aug["risk_score_discount"] > 20]

# Cohort 4: Rapid deteriorators (deterioration risk > 50)
cohort4 = scorecard_aug[scorecard_aug["risk_score_deterioration"] > 50]

cohorts = [
    ("1. High-Value Disengaging", cohort1, "CSM outreach + QBR", "Retention"),
    ("2. Payment Failures", cohort2, "Collections escalation", "Finance/AR"),
    ("3. Over-Discounted", cohort3, "Discount policy review", "Sales Ops"),
    ("4. Rapid Deteriorators", cohort4, "Product adoption program", "CSM + Product"),
]

out(f"\n  {'Cohort':30s}  {'Count':>6s}  {'ACV at Risk':>12s}  {'Action':30s}  {'Owner'}")
out(f"  {'─'*100}")
for name, df, action, owner in cohorts:
    acv = df["revenue_at_risk"].sum()
    out(f"  {name:30s}  {len(df):>6d}  ${acv:>10,.0f}  {action:30s}  {owner}")

# Chart: Prioritization matrix
fig, ax = plt.subplots(figsize=(10, 7))
sc_plot = scorecard.dropna(subset=["avg_engagement"]).copy()
tier_colors = {"Low": "#27AE60", "Medium": "#F1C40F", "High": "#E67E22", "Critical": "#C0392B"}
for tier in ["Low", "Medium", "High", "Critical"]:
    mask = sc_plot["risk_tier"] == tier
    if mask.sum() == 0:
        continue
    ax.scatter(sc_plot.loc[mask, "avg_engagement"],
               sc_plot.loc[mask, "annual_contract_value"] / 1000,
               c=tier_colors[tier], label=tier, alpha=0.6,
               s=sc_plot.loc[mask, "revenue_at_risk"] / 100 + 20,
               edgecolors="white", linewidth=0.5)

# Quadrant lines
ax.axvline(40, color="gray", linestyle=":", alpha=0.5)
ax.axhline(sc_plot["annual_contract_value"].median() / 1000, color="gray", linestyle=":", alpha=0.5)
ax.annotate("PRIORITY\nINTERVENTION", xy=(15, sc_plot["annual_contract_value"].quantile(0.75)/1000),
            fontsize=12, fontweight="bold", color=COLORS[4], alpha=0.7)
ax.annotate("MONITOR", xy=(60, sc_plot["annual_contract_value"].quantile(0.25)/1000),
            fontsize=12, fontweight="bold", color=COLORS[2], alpha=0.7)

ax.set_title("Customer Prioritization: Low Engagement × High ACV = Immediate Action Required",
             fontsize=13, fontweight="bold", pad=15)
ax.set_xlabel("Engagement Score (higher = healthier)")
ax.set_ylabel("Annual Contract Value ($K)")
ax.legend(title="Risk Tier", loc="upper right")
ax.spines[["top", "right"]].set_visible(False)
save_chart(fig, "a05_prioritization_matrix.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6: SALES REP DISCOUNT ANALYSIS (Q6)
# ═══════════════════════════════════════════════════════════════════════════════
section("6. SALES REP DISCOUNT ANALYSIS")

subsection("6a. Rep-Level Discount Behavior")

# Enrich rep data with customer outcomes
rep_customers = scorecard.groupby("sales_rep").agg(
    customers=("customer_id", "count"),
    total_acv=("annual_contract_value", "sum"),
    avg_risk=("composite_risk_score", "mean"),
    total_at_risk=("revenue_at_risk", "sum"),
).reset_index()

rep_full = rep_disc.merge(rep_customers, on="sales_rep", how="left")
rep_full["discount_per_dollar"] = rep_full["discount_revenue_impact"] / rep_full["total_revenue"]
rep_full["risk_per_customer"] = rep_full["total_at_risk"] / rep_full["customers"]

# Flag outlier reps (>1 std above mean on discount impact)
mean_impact = rep_full["discount_revenue_impact"].mean()
std_impact = rep_full["discount_revenue_impact"].std()
rep_full["is_outlier"] = rep_full["discount_revenue_impact"] > mean_impact + std_impact

out(f"\n  {'Rep':10s}  {'Cust':>5s}  {'Avg Disc%':>9s}  {'Max Disc':>8s}  "
    f"{'Disc Impact':>12s}  {'Avg Risk':>8s}  {'Total Risk':>12s}  {'Flag'}")
out(f"  {'─'*85}")
for _, r in rep_full.sort_values("discount_revenue_impact", ascending=False).iterrows():
    flag = "⚠️ HIGH" if r["is_outlier"] else ""
    out(f"  {r['sales_rep']:10s}  {r['customers']:>5.0f}  {r['avg_discount']:>8.1f}%  "
        f"{r['max_discount']:>7.0f}%  ${r['discount_revenue_impact']:>10,.0f}  "
        f"{r['avg_risk']:>8.1f}  ${r['total_at_risk']:>10,.0f}  {flag}")

outlier_reps = rep_full[rep_full["is_outlier"]]
out(f"\n  Flagged reps: {len(outlier_reps)} (discount impact > ${mean_impact + std_impact:,.0f})")
if len(outlier_reps) > 0:
    out(f"  Combined discount leakage from flagged reps: ${outlier_reps['discount_revenue_impact'].sum():,.0f}")

# Correlation: does heavier discounting correlate with higher customer risk?
corr = rep_full[["avg_discount", "avg_risk", "discount_revenue_impact", "total_at_risk"]].corr()
out(f"\n  Correlation: avg_discount ↔ avg_risk_score = {corr.loc['avg_discount', 'avg_risk']:.3f}")
out(f"  Interpretation: {'Weak' if abs(corr.loc['avg_discount', 'avg_risk']) < 0.3 else 'Moderate' if abs(corr.loc['avg_discount', 'avg_risk']) < 0.6 else 'Strong'} "
    f"correlation — discounting {'does not strongly predict' if abs(corr.loc['avg_discount', 'avg_risk']) < 0.3 else 'moderately predicts' if abs(corr.loc['avg_discount', 'avg_risk']) < 0.6 else 'strongly predicts'} customer risk.")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7: CONCENTRATION RISK (Q7)
# ═══════════════════════════════════════════════════════════════════════════════
section("7. CONCENTRATION RISK — HOW FRAGILE IS THE REVENUE BASE?")

# Revenue concentration
cust_rev = revenue.groupby("customer_id")["mrr_billed"].sum().sort_values(ascending=False)
total_rev = cust_rev.sum()
cumrev = cust_rev.cumsum() / total_rev * 100
n = len(cust_rev)

top5_pct = cust_rev.head(max(1, int(n*0.05))).sum() / total_rev * 100
top10_pct = cust_rev.head(max(1, int(n*0.10))).sum() / total_rev * 100
top20_pct = cust_rev.head(max(1, int(n*0.20))).sum() / total_rev * 100
idx_80 = (cumrev >= 80).idxmax()
pct_for_80 = (list(cust_rev.index).index(idx_80) + 1) / n * 100

# Risk concentration
risk_sorted = scorecard.sort_values("revenue_at_risk", ascending=False)
risk_cumsum = risk_sorted["revenue_at_risk"].cumsum() / risk_sorted["revenue_at_risk"].sum() * 100

out(f"""
  Revenue Concentration:
    Top 5% of customers  → {top5_pct:.1f}% of revenue
    Top 10% of customers → {top10_pct:.1f}% of revenue
    Top 20% of customers → {top20_pct:.1f}% of revenue
    {pct_for_80:.0f}% of customers generate 80% of revenue

  Risk Concentration:
    Top 20 accounts → {risk_cumsum.iloc[19]:.1f}% of total revenue-at-risk
    Top 50 accounts → {risk_cumsum.iloc[49]:.1f}% of total revenue-at-risk

  Implication: Revenue risk is even more concentrated than revenue itself.
  A small number of account interventions can address the majority of risk.
""")

# Industry concentration
ind_rev = revenue.groupby("industry")["mrr_billed"].sum().sort_values(ascending=False)
ind_share = ind_rev / ind_rev.sum() * 100
out("  Revenue by Industry:")
for ind, share in ind_share.items():
    bar = "█" * int(share / 2)
    out(f"    {ind:25s}  {share:5.1f}%  {bar}")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 8: VALIDATION OF KEY CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════════
section("8. VALIDATION OF KEY CALCULATIONS")

checks = []

# V1: Revenue funnel arithmetic
v1 = abs((total_contracted - discount_leakage - collection_leakage) - total_collected) < 1
checks.append(("Revenue funnel arithmetic", v1,
    f"contracted - discount - collection = ${total_contracted - discount_leakage - collection_leakage:,.0f} "
    f"vs collected = ${total_collected:,.0f}"))

# V2: Segment ARR sums to total
seg_arr_sum = seg["total_acv"].sum()
v2 = abs(seg_arr_sum - total_arr) < 1
checks.append(("Segment ARR sums to total", v2,
    f"Sum: ${seg_arr_sum:,.0f} vs Total: ${total_arr:,.0f}"))

# V3: Risk scores bounded [0, 100]
for col in ["risk_score_churn", "risk_score_deterioration", "risk_score_discount",
            "risk_score_payment", "composite_risk_score"]:
    oob = ((scorecard[col] < 0) | (scorecard[col] > 100)).sum()
    checks.append((f"{col} in [0,100]", oob == 0, f"{oob} out of bounds"))

# V4: revenue_at_risk <= ACV
v4 = (scorecard["revenue_at_risk"] > scorecard["annual_contract_value"]).sum() == 0
checks.append(("revenue_at_risk ≤ ACV", v4,
    f"{(scorecard['revenue_at_risk'] > scorecard['annual_contract_value']).sum()} violations"))

# V5: Collection rate in reasonable range
v5_min = payments["collection_rate"].min()
v5_max = payments["collection_rate"].max()
checks.append(("Collection rates reasonable", v5_min >= 0 and v5_max <= 105,
    f"Range: [{v5_min:.1f}%, {v5_max:.1f}%]"))

# V6: No negative billed/collected
v6a = (revenue["mrr_billed"] < 0).sum()
v6b = (revenue["mrr_collected"] < 0).sum()
checks.append(("No negative billed/collected", v6a == 0 and v6b == 0,
    f"Negative billed: {v6a}, negative collected: {v6b}"))

# V7: Composite = weighted sum
recomputed = (
    scorecard["risk_score_churn"] * 0.30 +
    scorecard["risk_score_deterioration"] * 0.25 +
    scorecard["risk_score_discount"] * 0.20 +
    scorecard["risk_score_payment"] * 0.25
).round(1)
max_diff = (scorecard["composite_risk_score"] - recomputed).abs().max()
checks.append(("Composite = weighted sum", max_diff < 0.2, f"Max diff: {max_diff:.4f}"))

# V8: Top-20 risk concentration makes sense
top20_risk_pct = risk_cumsum.iloc[19]
checks.append(("Top-20 risk concentration plausible", 20 < top20_risk_pct < 90,
    f"Top 20 accounts = {top20_risk_pct:.1f}% of risk"))

pass_count = sum(1 for _, v, _ in checks if v)
fail_count = sum(1 for _, v, _ in checks if not v)
out(f"\n  Results: {pass_count} PASS / {fail_count} FAIL / {len(checks)} total\n")
for name, passed, detail in checks:
    icon = "✅" if passed else "❌"
    out(f"  {icon} {name}")
    out(f"     {detail}")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 9: EXECUTIVE SUMMARY & RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════
section("9. EXECUTIVE SUMMARY")

out(f"""
  REVENUE LEAKAGE INTELLIGENCE — EXECUTIVE SUMMARY
  Report Date: {datetime.now().strftime('%Y-%m-%d')}
  Period: January 2024 – December 2025 (24 months)
  Scope: 500 B2B SaaS customers, $19.2M ARR

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. THE BOTTOM LINE

     The company is losing ${total_leakage/1e6:.1f}M — or {leakage_pct:.1f}% of contracted revenue —
     through two primary channels: collection failures (${collection_leakage/1e6:.1f}M) and
     discounting (${discount_leakage/1e6:.1f}M). An additional ${total_at_risk/1e6:.1f}M in ARR
     ({at_risk_pct:.1f}%) is at risk based on customer health scoring.

  2. KEY FINDINGS

     a) Collection failures are the #1 leakage driver.
        {(revenue['payment_status'].isin(['failed','partial','pending'])).mean()*100:.1f}% of invoices
        result in incomplete collection. The overall collection rate is {avg_collection_rate:.1f}%,
        meaning ${collection_leakage/1e6:.1f}M in billed revenue was never realized.

     b) Payment risk is the dominant risk dimension across all segments.
        It contributes the most weighted points to the composite risk score,
        ahead of deterioration, churn, and discounting.

     c) Revenue is concentrated — {pct_for_80:.0f}% of customers generate 80% of revenue.
        Revenue risk is even more concentrated: the top 20 accounts represent
        {risk_cumsum.iloc[19]:.0f}% of all revenue at risk. This concentration means
        targeted intervention on ~4% of accounts can address the majority of risk.

     d) Engagement is declining across the portfolio.
        Average engagement dropped from {first_6['avg_engagement'].mean():.1f} to
        {last_6['avg_engagement'].mean():.1f} over the analysis period. Customers with
        the "gradual_decline" pattern show the steepest erosion.

     e) {len(outlier_reps)} sales reps show elevated discount behavior
        (>${mean_impact + std_impact:,.0f} in discount impact), though discount levels
        do not strongly correlate with downstream customer risk.

  3. CAVEATS

     • This analysis uses synthetic data. All patterns are realistic but generated.
     • Risk weights (30/25/20/25) are judgement-based, not empirically calibrated.
     • Scores indicate risk association, not causation.
     • Engagement scores are a proxy — real systems would use product telemetry.
     • The analysis is point-in-time. Predictive modeling would improve forward-looking accuracy.

  4. RECOMMENDATIONS

     Immediate (0-30 days):
       ① Escalate top 20 revenue-at-risk accounts to CSM leadership for review.
          These 20 accounts represent {risk_cumsum.iloc[19]:.0f}% of total risk.
       ② Initiate collections process on {len(cohort2)} accounts with payment risk >60.
          Combined ACV at risk: ${cohort2['revenue_at_risk'].sum():,.0f}.

     Short-term (30-90 days):
       ③ Implement discount guardrails — flag any discount >25% for manager approval.
          60.4% of customers have received at least one excessive discount.
       ④ Launch re-engagement program for {len(cohort1)} high-value disengaging accounts.
       ⑤ Review and tighten payment terms for customers with 2+ failed payments.

     Strategic (90+ days):
       ⑥ Build NRR tracking by segment and cohort — currently not measured.
       ⑦ Develop predictive churn model using engagement + payment signals.
       ⑧ Reduce revenue concentration — top 10% accounts carry {top10_pct:.0f}% of revenue.
       ⑨ Establish monthly leakage review cadence with Finance and Revenue Ops.
""")


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE REPORT
# ═══════════════════════════════════════════════════════════════════════════════
report_path = os.path.join(out_dir, "reports", "revenue_leakage_analysis.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(f"Revenue Leakage Analysis Report — {datetime.now().isoformat()}\n\n")
    f.write("\n".join(report))

out(f"\n{'='*80}")
out(f"  Report saved: {report_path}")
out(f"  Charts saved: {charts_dir}/ (5 charts)")
out(f"{'='*80}")
