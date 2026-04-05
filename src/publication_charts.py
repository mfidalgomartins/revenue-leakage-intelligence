"""
Revenue Leakage Intelligence System — Publication-Quality Visualization Pack
=============================================================================
10 charts designed for executive presentation and portfolio demonstration.
Each chart follows a consistent design system with professional typography,
colour palette, and annotation standards.
"""

import json
import pathlib
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW  = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT  = ROOT / "outputs" / "charts" / "publication"
OUT.mkdir(parents=True, exist_ok=True)

# ── Design System ────────────────────────────────────────────────────────────
# Colour palette — professional dark-on-light scheme
C = {
    "bg":        "#FAFBFC",
    "text":      "#1B2A4A",
    "subtitle":  "#5A6B8A",
    "grid":      "#E8ECF1",
    "accent1":   "#2563EB",   # primary blue
    "accent2":   "#DC2626",   # alert red
    "accent3":   "#059669",   # success green
    "accent4":   "#D97706",   # warning amber
    "accent5":   "#7C3AED",   # purple
    "accent6":   "#0891B2",   # teal
    "light1":    "#DBEAFE",
    "light2":    "#FEE2E2",
    "light3":    "#D1FAE5",
}

TIER_COLORS = {
    "Critical": "#DC2626",
    "High":     "#D97706",
    "Medium":   "#2563EB",
    "Low":      "#059669",
}

SEGMENT_COLORS = {
    "Enterprise":  "#2563EB",
    "Mid-Market":  "#7C3AED",
    "SMB":         "#0891B2",
}

FONT = {
    "title": 18,
    "subtitle": 11,
    "axis": 10,
    "tick": 9,
    "annotation": 8,
    "legend": 9,
}

# Apply global style
plt.rcParams.update({
    "figure.facecolor": C["bg"],
    "axes.facecolor":   C["bg"],
    "axes.edgecolor":   C["grid"],
    "axes.labelcolor":  C["text"],
    "text.color":       C["text"],
    "xtick.color":      C["text"],
    "ytick.color":      C["text"],
    "grid.color":       C["grid"],
    "grid.alpha":       0.6,
    "font.family":      "sans-serif",
    "font.sans-serif":  ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
    "figure.dpi":       150,
    "savefig.dpi":      200,
    "savefig.bbox":     "tight",
    "savefig.pad_inches": 0.3,
})


# ── Helpers ──────────────────────────────────────────────────────────────────
def _save(fig, name):
    path = OUT / f"{name}.png"
    fig.savefig(path, facecolor=C["bg"])
    plt.close(fig)
    print(f"  ✓ {name}.png")
    return str(path)


def _dollars(x, _=None):
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"${x/1_000:.0f}K"
    return f"${x:,.0f}"


def _pct(x, _=None):
    return f"{x:.0f}%"


def _clean_axes(ax, grid_axis="y"):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(C["grid"])
    ax.spines["bottom"].set_color(C["grid"])
    if grid_axis:
        ax.grid(axis=grid_axis, alpha=0.4, linewidth=0.5)
    ax.tick_params(labelsize=FONT["tick"])


def _title_block(ax, title, subtitle=""):
    ax.set_title(title, fontsize=FONT["title"], fontweight="bold",
                 color=C["text"], loc="left", pad=16)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes,
                fontsize=FONT["subtitle"], color=C["subtitle"],
                va="bottom", ha="left")


# ── Data Loading ─────────────────────────────────────────────────────────────
def load_data():
    data = {}
    data["customers"]     = pd.read_csv(RAW / "customers.csv", parse_dates=["onboard_date"])
    data["monthly"]       = pd.read_csv(RAW / "monthly_revenue.csv", parse_dates=["month"])
    data["risk"]          = pd.read_csv(PROC / "risk_scorecard.csv")
    data["payments"]      = pd.read_csv(PROC / "payment_analysis.csv")
    data["rep_discount"]  = pd.read_csv(PROC / "rep_discount_impact.csv")
    data["deterioration"] = pd.read_csv(PROC / "deterioration_analysis.csv")
    data["discount"]      = pd.read_csv(PROC / "discount_analysis.csv")
    return data


# ═══════════════════════════════════════════════════════════════════════════
# CHART 01 — Revenue Waterfall: Contracted → Billed → Collected
# Type: Layered area chart showing magnitude erosion over time
# ═══════════════════════════════════════════════════════════════════════════
def chart_01_revenue_trend(data):
    m = data["monthly"].groupby("month").agg(
        contracted=("mrr_contracted", "sum"),
        billed=("mrr_billed", "sum"),
        collected=("mrr_collected", "sum"),
    ).sort_index()

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.fill_between(m.index, m["contracted"], alpha=0.15, color=C["accent1"], label="Contracted MRR")
    ax.fill_between(m.index, m["billed"],     alpha=0.20, color=C["accent4"], label="Billed MRR")
    ax.fill_between(m.index, m["collected"],   alpha=0.30, color=C["accent3"], label="Collected MRR")

    ax.plot(m.index, m["contracted"], color=C["accent1"], linewidth=2)
    ax.plot(m.index, m["billed"],     color=C["accent4"], linewidth=2)
    ax.plot(m.index, m["collected"],  color=C["accent3"], linewidth=2)

    # Annotate leakage band
    avg_gap = (m["contracted"] - m["collected"]).mean()
    ax.annotate(f"Avg. leakage gap: {_dollars(avg_gap)}/mo",
                xy=(m.index[len(m)//2], m["collected"].iloc[len(m)//2]),
                xytext=(0, -40), textcoords="offset points",
                fontsize=FONT["annotation"], color=C["accent2"],
                arrowprops=dict(arrowstyle="->", color=C["accent2"], lw=1),
                bbox=dict(boxstyle="round,pad=0.3", facecolor=C["light2"], edgecolor=C["accent2"], alpha=0.8))

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_dollars))
    _clean_axes(ax)
    _title_block(ax, "Revenue Erosion: From Contract to Collection",
                 "Gap between contracted, billed, and collected revenue reveals systematic leakage")
    ax.legend(fontsize=FONT["legend"], loc="upper left", framealpha=0.9)
    return _save(fig, "01_revenue_erosion_trend")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 02 — Risk Composition Over Time (stacked area by leakage channel)
# ═══════════════════════════════════════════════════════════════════════════
def chart_02_risk_over_time(data):
    m = data["monthly"].copy()
    # Merge risk scores
    risk = data["risk"][["customer_id", "risk_score_churn", "risk_score_deterioration",
                         "risk_score_discount", "risk_score_payment"]].copy()
    m = m.merge(risk, on="customer_id", how="left")

    agg = m.groupby("month").agg(
        churn=("risk_score_churn", "mean"),
        deterioration=("risk_score_deterioration", "mean"),
        discount=("risk_score_discount", "mean"),
        payment=("risk_score_payment", "mean"),
    ).sort_index()

    fig, ax = plt.subplots(figsize=(14, 6))

    colors = [C["accent2"], C["accent4"], C["accent5"], C["accent6"]]
    labels = ["Silent Churn", "Revenue Deterioration", "Excessive Discounting", "Payment Failures"]

    ax.stackplot(agg.index, agg["churn"], agg["deterioration"],
                 agg["discount"], agg["payment"],
                 colors=colors, alpha=0.7, labels=labels)

    _clean_axes(ax)
    _title_block(ax, "Leakage Risk Composition Over Time",
                 "Average risk scores by leakage channel — stacked to show relative contribution")
    ax.legend(fontsize=FONT["legend"], loc="upper left", framealpha=0.9)
    ax.set_ylabel("Avg. Risk Score (stacked)", fontsize=FONT["axis"])
    return _save(fig, "02_risk_composition_over_time")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 03 — Risk Drivers by Segment (grouped horizontal bar)
# ═══════════════════════════════════════════════════════════════════════════
def chart_03_risk_drivers(data):
    r = data["risk"].copy()
    drivers = ["risk_score_churn", "risk_score_deterioration",
               "risk_score_discount", "risk_score_payment"]
    nice = ["Churn", "Deterioration", "Discounting", "Payment"]
    segments = sorted(r["segment"].unique())

    fig, ax = plt.subplots(figsize=(12, 6))
    y_pos = np.arange(len(nice))
    bar_h = 0.22

    for i, seg in enumerate(segments):
        vals = [r.loc[r["segment"] == seg, d].mean() for d in drivers]
        offset = (i - len(segments)/2 + 0.5) * bar_h
        color = SEGMENT_COLORS.get(seg, C["accent1"])
        ax.barh(y_pos + offset, vals, height=bar_h, label=seg,
                color=color, alpha=0.85, edgecolor="white", linewidth=0.5)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(nice, fontsize=FONT["axis"])
    ax.set_xlabel("Average Risk Score", fontsize=FONT["axis"])
    _clean_axes(ax, grid_axis="x")
    _title_block(ax, "Risk Driver Intensity by Segment",
                 "Which leakage channels hit hardest, segmented by customer tier")
    ax.legend(fontsize=FONT["legend"], loc="lower right", framealpha=0.9)
    return _save(fig, "03_risk_drivers_by_segment")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 04 — Top 25 Customers by Revenue-at-Risk (lollipop)
# ═══════════════════════════════════════════════════════════════════════════
def chart_04_customer_ranking(data):
    r = data["risk"].nlargest(25, "revenue_at_risk").sort_values("revenue_at_risk")

    fig, ax = plt.subplots(figsize=(12, 8))

    colors = [TIER_COLORS.get(t, C["accent1"]) for t in r["risk_tier"]]
    ax.hlines(y=range(len(r)), xmin=0, xmax=r["revenue_at_risk"],
              color=colors, linewidth=1.5, alpha=0.7)
    ax.scatter(r["revenue_at_risk"], range(len(r)), color=colors, s=60, zorder=5)

    ax.set_yticks(range(len(r)))
    ax.set_yticklabels([f"{cid} ({seg})" for cid, seg in zip(r["customer_id"], r["segment"])],
                       fontsize=FONT["tick"])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_dollars))
    _clean_axes(ax, grid_axis="x")
    _title_block(ax, "Top 25 Customers by Revenue at Risk",
                 "Prioritized intervention list — colour indicates risk tier")

    # Legend for tiers
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=8, label=t)
               for t, c in TIER_COLORS.items()]
    ax.legend(handles=handles, fontsize=FONT["legend"], loc="lower right", framealpha=0.9)
    return _save(fig, "04_top25_revenue_at_risk")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 05 — Segment Mix: ARR vs Risk Distribution (paired donut)
# ═══════════════════════════════════════════════════════════════════════════
def chart_05_segment_mix(data):
    r = data["risk"].copy()
    seg_agg = r.groupby("segment").agg(
        arr=("annual_contract_value", "sum"),
        risk=("revenue_at_risk", "sum"),
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    segments = seg_agg.index.tolist()
    colors = [SEGMENT_COLORS.get(s, C["accent1"]) for s in segments]

    for ax, col, title in zip(axes, ["arr", "risk"],
                               ["Annual Revenue (ARR)", "Revenue at Risk"]):
        wedges, texts, autotexts = ax.pie(
            seg_agg[col], labels=segments, autopct="%1.1f%%",
            colors=colors, startangle=90, pctdistance=0.75,
            wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2))
        for t in autotexts:
            t.set_fontsize(FONT["annotation"])
            t.set_color(C["text"])
        for t in texts:
            t.set_fontsize(FONT["axis"])
        ax.set_title(title, fontsize=FONT["axis"] + 2, fontweight="bold",
                     color=C["text"], pad=10)
        # Centre label
        total = seg_agg[col].sum()
        ax.text(0, 0, _dollars(total), ha="center", va="center",
                fontsize=FONT["title"] - 2, fontweight="bold", color=C["text"])

    fig.suptitle("Segment Mix: Revenue vs Risk Concentration",
                 fontsize=FONT["title"], fontweight="bold", color=C["text"], y=1.02)
    fig.text(0.5, 0.97, "Disproportionate risk concentration signals segment-specific leakage patterns",
             ha="center", fontsize=FONT["subtitle"], color=C["subtitle"])
    plt.tight_layout()
    return _save(fig, "05_segment_mix_donuts")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 06 — Cohort Retention Heatmap
# ═══════════════════════════════════════════════════════════════════════════
def chart_06_cohort_retention(data):
    cust = data["customers"].copy()
    cust["cohort_q"] = cust["onboard_date"].dt.to_period("Q").astype(str)
    m = data["monthly"].merge(cust[["customer_id", "cohort_q"]], on="customer_id")
    m["month_num"] = m.groupby("customer_id")["month"].rank(method="dense").astype(int)

    # Retention = % customers still active (collected > 0) per cohort per month
    cohorts = m.groupby(["cohort_q", "month_num"]).agg(
        active=("mrr_collected", lambda x: (x > 0).sum()),
        total=("customer_id", "count"),
    )
    cohorts["retention"] = (cohorts["active"] / cohorts["total"] * 100).round(1)
    pivot = cohorts["retention"].unstack(level="month_num")

    # Limit to first 12 months and cohorts with enough data
    pivot = pivot.loc[:, pivot.columns[:12]]
    pivot = pivot.dropna(thresh=3)

    fig, ax = plt.subplots(figsize=(14, max(5, len(pivot) * 0.5 + 1)))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="RdYlGn", vmin=50, vmax=100,
                linewidths=0.5, linecolor="white", cbar_kws={"label": "Retention %", "shrink": 0.7},
                ax=ax, annot_kws={"size": FONT["annotation"]})

    ax.set_xlabel("Month #", fontsize=FONT["axis"])
    ax.set_ylabel("Onboard Cohort", fontsize=FONT["axis"])
    ax.tick_params(labelsize=FONT["tick"])
    _title_block(ax, "Cohort Revenue Retention Heatmap",
                 "Percentage of customers with positive collected revenue by onboarding quarter")
    return _save(fig, "06_cohort_retention_heatmap")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 07 — Payment Anomaly Trend (dual-axis: failures + engagement)
# ═══════════════════════════════════════════════════════════════════════════
def chart_07_anomaly_trend(data):
    m = data["monthly"].copy()
    agg = m.groupby("month").agg(
        failed=("payment_status", lambda x: (x == "failed").sum()),
        partial=("payment_status", lambda x: (x == "partial").sum()),
        avg_engagement=("engagement_score", "mean"),
    ).sort_index()

    fig, ax1 = plt.subplots(figsize=(14, 6))
    ax2 = ax1.twinx()

    w = 20  # bar width in days
    ax1.bar(agg.index - pd.Timedelta(days=w/2), agg["failed"], width=w,
            color=C["accent2"], alpha=0.7, label="Failed Payments")
    ax1.bar(agg.index + pd.Timedelta(days=w/2), agg["partial"], width=w,
            color=C["accent4"], alpha=0.7, label="Partial Payments")

    ax2.plot(agg.index, agg["avg_engagement"], color=C["accent1"],
             linewidth=2.5, marker="o", markersize=4, label="Avg Engagement", zorder=5)

    ax1.set_ylabel("Payment Issue Count", fontsize=FONT["axis"], color=C["accent2"])
    ax2.set_ylabel("Avg Engagement Score", fontsize=FONT["axis"], color=C["accent1"])
    ax2.spines["right"].set_color(C["accent1"])

    _clean_axes(ax1)
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(labelsize=FONT["tick"])

    # Combined legend
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=FONT["legend"], loc="upper left", framealpha=0.9)

    _title_block(ax1, "Payment Anomalies & Engagement Trajectory",
                 "Correlation between payment failures and declining engagement scores")
    return _save(fig, "07_payment_anomaly_trend")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 08 — Prioritization Matrix (bubble scatter with quadrants)
# ═══════════════════════════════════════════════════════════════════════════
def chart_08_prioritization_matrix(data):
    r = data["risk"].copy()

    fig, ax = plt.subplots(figsize=(12, 8))

    sizes = (r["annual_contract_value"] / r["annual_contract_value"].max() * 400) + 20
    colors = [TIER_COLORS.get(t, C["accent1"]) for t in r["risk_tier"]]

    ax.scatter(r["composite_risk_score"], r["revenue_at_risk"],
               s=sizes, c=colors, alpha=0.6, edgecolors="white", linewidth=0.5)

    # Quadrant lines
    risk_med = r["composite_risk_score"].median()
    rev_med  = r["revenue_at_risk"].median()
    ax.axvline(risk_med, color=C["grid"], linestyle="--", linewidth=1, alpha=0.8)
    ax.axhline(rev_med,  color=C["grid"], linestyle="--", linewidth=1, alpha=0.8)

    # Quadrant labels
    labels = {
        (0.95, 0.95): "URGENT\nHigh Risk + High Value",
        (0.05, 0.95): "MONITOR\nLow Risk + High Value",
        (0.95, 0.05): "REVIEW\nHigh Risk + Low Value",
        (0.05, 0.05): "STABLE\nLow Risk + Low Value",
    }
    for (x, y), txt in labels.items():
        ax.text(x, y, txt, transform=ax.transAxes, fontsize=FONT["annotation"] + 1,
                ha="right" if x > 0.5 else "left",
                va="top" if y > 0.5 else "bottom",
                alpha=0.7, color=C["subtitle"])

    # Label top outliers
    top5 = r.nlargest(5, "revenue_at_risk")
    for _, row in top5.iterrows():
        ax.annotate(row["customer_id"],
                    xy=(row["composite_risk_score"], row["revenue_at_risk"]),
                    xytext=(8, 8), textcoords="offset points",
                    fontsize=FONT["annotation"], color=C["text"], alpha=0.8)

    ax.set_xlabel("Composite Risk Score", fontsize=FONT["axis"])
    ax.set_ylabel("Revenue at Risk ($)", fontsize=FONT["axis"])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_dollars))
    _clean_axes(ax, grid_axis="both")
    _title_block(ax, "Customer Prioritization Matrix",
                 "Bubble size = contract value · Colour = risk tier · Quadrants guide intervention urgency")

    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=8, label=t)
               for t, c in TIER_COLORS.items()]
    ax.legend(handles=handles, fontsize=FONT["legend"], loc="upper left", framealpha=0.9)
    return _save(fig, "08_prioritization_matrix")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 09 — Collection Rate Distribution by Segment (violin + strip)
# ═══════════════════════════════════════════════════════════════════════════
def chart_09_collection_distribution(data):
    p = data["payments"].merge(
        data["customers"][["customer_id", "segment"]], on="customer_id")

    fig, ax = plt.subplots(figsize=(12, 6))
    segments = sorted(p["segment"].unique())
    palette = [SEGMENT_COLORS.get(s, C["accent1"]) for s in segments]

    sns.violinplot(data=p, x="segment", y="collection_rate", order=segments,
                   palette=palette, inner=None, alpha=0.3, ax=ax, cut=0)
    sns.stripplot(data=p, x="segment", y="collection_rate", order=segments,
                  palette=palette, size=5, alpha=0.6, jitter=0.25, ax=ax)

    # Median line
    for i, seg in enumerate(segments):
        med = p.loc[p["segment"] == seg, "collection_rate"].median()
        ax.hlines(med, i - 0.3, i + 0.3, color=C["text"], linewidth=2, zorder=10)
        ax.text(i + 0.35, med, f"{med:.1f}%", fontsize=FONT["annotation"],
                va="center", color=C["text"], fontweight="bold")

    # Danger zone
    ax.axhline(80, color=C["accent2"], linestyle="--", linewidth=1, alpha=0.6)
    ax.text(len(segments) - 0.5, 79, "80% threshold", fontsize=FONT["annotation"],
            color=C["accent2"], ha="right", va="top")

    ax.set_ylabel("Collection Rate (%)", fontsize=FONT["axis"])
    ax.set_xlabel("")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_pct))
    _clean_axes(ax)
    _title_block(ax, "Collection Rate Distribution by Segment",
                 "Violin + strip plot reveals variance and outliers beyond segment averages")
    return _save(fig, "09_collection_rate_distribution")


# ═══════════════════════════════════════════════════════════════════════════
# CHART 10 — Sales Rep Discount Impact (horizontal bar with threshold)
# ═══════════════════════════════════════════════════════════════════════════
def chart_10_rep_discount(data):
    rep = data["rep_discount"].sort_values("discount_revenue_impact", ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(6, len(rep) * 0.35)))

    threshold = rep["discount_revenue_impact"].quantile(0.75)
    colors = [C["accent2"] if v > threshold else C["accent1"] for v in rep["discount_revenue_impact"]]

    ax.barh(range(len(rep)), rep["discount_revenue_impact"],
            color=colors, alpha=0.8, edgecolor="white", linewidth=0.5)

    ax.set_yticks(range(len(rep)))
    ax.set_yticklabels(rep["sales_rep"], fontsize=FONT["tick"])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_dollars))

    # Threshold line
    ax.axvline(threshold, color=C["accent2"], linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(threshold, len(rep) - 0.5, f"  P75: {_dollars(threshold)}",
            fontsize=FONT["annotation"], color=C["accent2"], va="bottom")

    # Annotate values on top outliers
    for i, (_, row) in enumerate(rep.iterrows()):
        if row["discount_revenue_impact"] > threshold:
            ax.text(row["discount_revenue_impact"] + rep["discount_revenue_impact"].max() * 0.01,
                    i, _dollars(row["discount_revenue_impact"]),
                    fontsize=FONT["annotation"], va="center", color=C["accent2"])

    _clean_axes(ax, grid_axis="x")
    _title_block(ax, "Sales Rep Discount Revenue Impact",
                 "Revenue lost to discounting by rep — red bars exceed 75th percentile threshold")
    return _save(fig, "10_rep_discount_impact")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  PUBLICATION-QUALITY VISUALIZATION PACK")
    print("  Revenue Leakage Intelligence System")
    print("=" * 60)

    print("\n📂 Loading data...")
    data = load_data()
    print(f"  Customers: {len(data['customers']):,}")
    print(f"  Monthly records: {len(data['monthly']):,}")
    print(f"  Risk scorecard: {len(data['risk']):,}")

    print(f"\n🎨 Generating 10 publication charts → {OUT}/\n")

    manifest = {}

    chart_funcs = [
        ("01", "Revenue Erosion Trend",          chart_01_revenue_trend),
        ("02", "Risk Composition Over Time",     chart_02_risk_over_time),
        ("03", "Risk Drivers by Segment",        chart_03_risk_drivers),
        ("04", "Top 25 Revenue at Risk",         chart_04_customer_ranking),
        ("05", "Segment Mix Donuts",             chart_05_segment_mix),
        ("06", "Cohort Retention Heatmap",       chart_06_cohort_retention),
        ("07", "Payment Anomaly Trend",          chart_07_anomaly_trend),
        ("08", "Prioritization Matrix",          chart_08_prioritization_matrix),
        ("09", "Collection Rate Distribution",   chart_09_collection_distribution),
        ("10", "Rep Discount Impact",            chart_10_rep_discount),
    ]

    for num, desc, func in chart_funcs:
        try:
            path = func(data)
            manifest[f"chart_{num}"] = {
                "title": desc,
                "path": path,
                "status": "success",
            }
        except Exception as e:
            print(f"  ✗ Chart {num} failed: {e}")
            manifest[f"chart_{num}"] = {
                "title": desc,
                "status": "error",
                "error": str(e),
            }

    # Write manifest
    manifest_path = OUT / "chart_manifest.json"
    manifest["_meta"] = {
        "generated_at": datetime.now().isoformat(),
        "total_charts": len(chart_funcs),
        "successful": sum(1 for v in manifest.values() if isinstance(v, dict) and v.get("status") == "success"),
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n📋 Manifest → {manifest_path}")

    ok = manifest["_meta"]["successful"]
    total = manifest["_meta"]["total_charts"]
    print(f"\n✅ Done: {ok}/{total} charts generated successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
