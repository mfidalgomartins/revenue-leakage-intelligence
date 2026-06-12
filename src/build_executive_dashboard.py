"""
Revenue Leakage Intelligence System — Executive Dashboard Builder
==================================================================
Generates the tracked public HTML dashboard with:
  - KPI cards with trend indicators
  - Interactive Chart.js visualizations
  - Segment/Region/Tier filters that update all sections
  - High-risk accounts detail table with sorting
  - Responsive design for executive presentation

Uses embedded JSON data and the shared publication template.
"""

import json
import pathlib
from datetime import datetime

import pandas as pd
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW  = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT  = ROOT / "dashboard"
OUT.mkdir(parents=True, exist_ok=True)


def load_and_prepare():
    """Load all datasets and compute dashboard data."""
    customers = pd.read_csv(RAW / "customers.csv", parse_dates=["onboard_date"])
    monthly   = pd.read_csv(RAW / "monthly_revenue.csv", parse_dates=["month"])
    risk      = pd.read_csv(PROC / "risk_scorecard.csv")

    data = {}

    # ── KPI Metrics ──────────────────────────────────────────────────────
    total_contracted = monthly["mrr_contracted"].sum()
    total_billed     = monthly["mrr_billed"].sum()
    total_collected  = monthly["mrr_collected"].sum()
    total_leakage    = total_contracted - total_collected
    leakage_rate     = total_leakage / total_contracted * 100
    total_arr        = customers["annual_contract_value"].sum()
    total_at_risk    = risk["revenue_at_risk"].sum()
    at_risk_pct      = total_at_risk / total_arr * 100
    avg_collection   = total_collected / total_billed * 100
    high_risk_count  = len(risk[risk["risk_tier"].isin(["High", "Critical"])])

    # Trend: compare last 6 months vs first 6 months
    monthly_agg = monthly.groupby("month").agg(
        contracted=("mrr_contracted", "sum"),
        billed=("mrr_billed", "sum"),
        collected=("mrr_collected", "sum"),
        avg_engagement=("engagement_score", "mean"),
        failed=("payment_status", lambda x: (x == "failed").sum()),
    ).sort_index()

    first6 = monthly_agg.head(6)
    last6  = monthly_agg.tail(6)
    leakage_rate_f6 = ((first6["contracted"] - first6["collected"]) / first6["contracted"] * 100).mean()
    leakage_rate_l6 = ((last6["contracted"] - last6["collected"]) / last6["contracted"] * 100).mean()
    leakage_trend   = leakage_rate_l6 - leakage_rate_f6

    coll_rate_f6 = (first6["collected"] / first6["billed"] * 100).mean()
    coll_rate_l6 = (last6["collected"] / last6["billed"] * 100).mean()
    coll_trend   = coll_rate_l6 - coll_rate_f6

    data["kpis"] = {
        "total_leakage":    round(total_leakage, 0),
        "leakage_rate":     round(leakage_rate, 1),
        "leakage_trend":    round(leakage_trend, 1),
        "total_at_risk":    round(total_at_risk, 0),
        "at_risk_pct":      round(at_risk_pct, 1),
        "high_risk_count":  int(high_risk_count),
        "avg_collection":   round(avg_collection, 1),
        "coll_trend":       round(coll_trend, 1),
        "total_customers":  len(customers),
        "total_arr":        round(total_arr, 0),
    }

    # ── Monthly Revenue Trend ────────────────────────────────────────────
    trend_records = []
    for month, row in monthly_agg.iterrows():
        trend_records.append({
            "month": month.strftime("%Y-%m"),
            "contracted": round(row["contracted"], 0),
            "billed":     round(row["billed"], 0),
            "collected":  round(row["collected"], 0),
            "leakage":    round(row["contracted"] - row["collected"], 0),
        })
    data["monthly_trend"] = trend_records

    # ── Revenue at Risk by Segment Over Time (monthly) ──────────────────
    # Use monthly revenue merged with risk tiers
    m_risk = monthly.merge(risk[["customer_id", "risk_tier", "composite_risk_score",
                                  "revenue_at_risk", "risk_score_churn",
                                  "risk_score_deterioration", "risk_score_discount",
                                  "risk_score_payment"]], on="customer_id", how="left")

    seg_month = m_risk.groupby(["month", "segment"]).agg(
        contracted=("mrr_contracted", "sum"),
        collected=("mrr_collected", "sum"),
    ).reset_index()
    seg_month["gap"] = seg_month["contracted"] - seg_month["collected"]

    seg_trend = {}
    for seg in sorted(monthly["segment"].unique()):
        subset = seg_month[seg_month["segment"] == seg].sort_values("month")
        seg_trend[seg] = {
            "months": [m.strftime("%Y-%m") for m in subset["month"]],
            "gaps":   [round(v, 0) for v in subset["gap"]],
        }
    data["segment_leakage_trend"] = seg_trend

    # ── Risk Driver Comparison ───────────────────────────────────────────
    driver_data = []
    for seg in sorted(risk["segment"].unique()):
        sr = risk[risk["segment"] == seg]
        driver_data.append({
            "segment": seg,
            "churn":         round(sr["risk_score_churn"].mean(), 1),
            "deterioration": round(sr["risk_score_deterioration"].mean(), 1),
            "discount":      round(sr["risk_score_discount"].mean(), 1),
            "payment":       round(sr["risk_score_payment"].mean(), 1),
        })
    data["risk_drivers"] = driver_data

    # ── Tier Breakdown ───────────────────────────────────────────────────
    tier_data = []
    for tier in ["Critical", "High", "Medium", "Low"]:
        subset = risk[risk["risk_tier"] == tier]
        if len(subset) == 0:
            continue
        tier_data.append({
            "tier":       tier,
            "count":      int(len(subset)),
            "total_arr":  round(subset["annual_contract_value"].sum(), 0),
            "total_risk": round(subset["revenue_at_risk"].sum(), 0),
            "avg_score":  round(subset["composite_risk_score"].mean(), 1),
        })
    data["tier_breakdown"] = tier_data

    # ── Segment Summary ──────────────────────────────────────────────────
    seg_summary = []
    for seg in sorted(risk["segment"].unique()):
        sr = risk[risk["segment"] == seg]
        seg_summary.append({
            "segment":    seg,
            "count":      int(len(sr)),
            "total_arr":  round(sr["annual_contract_value"].sum(), 0),
            "total_risk": round(sr["revenue_at_risk"].sum(), 0),
            "avg_score":  round(sr["composite_risk_score"].mean(), 1),
            "risk_intensity": round(
                (sr["revenue_at_risk"].sum() / risk["revenue_at_risk"].sum() * 100) /
                (sr["annual_contract_value"].sum() / risk["annual_contract_value"].sum() * 100), 2),
        })
    data["segment_summary"] = seg_summary

    # ── High-Risk Accounts Table ─────────────────────────────────────────
    top_risk = risk.nlargest(100, "composite_risk_score")
    accounts = []
    for _, r in top_risk.iterrows():
        accounts.append({
            "id":          r["customer_id"],
            "company":     r["company_name"],
            "segment":     r["segment"],
            "region":      r["region"],
            "industry":    r["industry"],
            "acv":         int(r["annual_contract_value"]),
            "score":       round(r["composite_risk_score"], 1),
            "tier":        r["risk_tier"],
            "at_risk":     int(round(r["revenue_at_risk"], 0)),
            "churn":       round(r["risk_score_churn"], 1),
            "deterioration": round(r["risk_score_deterioration"], 1),
            "discount":    round(r["risk_score_discount"], 1),
            "payment":     round(r["risk_score_payment"], 1),
            "engagement":  round(r["avg_engagement"], 1) if pd.notna(r["avg_engagement"]) else 0,
            "collection":  round(r["collection_rate"], 1) if pd.notna(r["collection_rate"]) else 0,
        })
    data["accounts"] = accounts

    # ── Filter options ───────────────────────────────────────────────────
    data["filters"] = {
        "segments": sorted(risk["segment"].unique().tolist()),
        "regions":  sorted(risk["region"].unique().tolist()),
        "tiers":    ["Critical", "High", "Medium", "Low"],
    }

    # ── Metadata ─────────────────────────────────────────────────────────
    data["meta"] = {
        "generated_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period_start":  monthly["month"].min().strftime("%Y-%m"),
        "period_end":    monthly["month"].max().strftime("%Y-%m"),
        "total_months":  int(monthly["month"].nunique()),
    }

    return data


def build_html(data):
    """Generate self-contained HTML dashboard."""

    # Convert numpy types to native Python for JSON serialization
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    json_data = json.dumps(data, indent=None, cls=NpEncoder)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Revenue Leakage Intelligence — Executive Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root {{
    --bg: #0F172A;
    --bg-card: #1E293B;
    --bg-card-hover: #263548;
    --border: #334155;
    --text: #F1F5F9;
    --text-muted: #94A3B8;
    --text-dim: #64748B;
    --blue: #3B82F6;
    --blue-light: #60A5FA;
    --red: #EF4444;
    --red-light: #F87171;
    --green: #10B981;
    --green-light: #34D399;
    --amber: #F59E0B;
    --amber-light: #FBBF24;
    --purple: #8B5CF6;
    --teal: #06B6D4;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
    --radius: 12px;
    --shadow: 0 4px 20px rgba(0,0,0,0.3);
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    min-height: 100vh;
}}

/* ── Header ───────────────────────────────── */
.header {{
    background: linear-gradient(135deg, #1E3A5F 0%, #0F172A 50%, #1a1a2e 100%);
    border-bottom: 1px solid var(--border);
    padding: 28px 40px 24px;
}}
.header-inner {{
    max-width: 1440px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 16px;
}}
.header h1 {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, var(--blue-light), var(--teal));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.header .subtitle {{
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 4px;
}}
.header .meta {{
    font-size: 12px;
    color: var(--text-dim);
    text-align: right;
}}

/* ── Container ────────────────────────────── */
.container {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 24px 40px 60px;
}}

/* ── Filters ──────────────────────────────── */
.filter-bar {{
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 24px;
    padding: 14px 20px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
}}
.filter-bar label {{
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.filter-bar select {{
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 32px 7px 12px;
    font-size: 13px;
    font-family: var(--font);
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    transition: border-color 0.2s;
}}
.filter-bar select:hover {{ border-color: var(--blue); }}
.filter-bar select:focus {{ outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }}
.filter-reset {{
    margin-left: auto;
    padding: 7px 16px;
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 12px;
    font-family: var(--font);
    cursor: pointer;
    transition: all 0.2s;
}}
.filter-reset:hover {{ background: var(--bg-card-hover); color: var(--text); border-color: var(--text-dim); }}

/* ── KPI Cards ────────────────────────────── */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}}
.kpi-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 24px;
    transition: transform 0.2s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
}}
.kpi-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow); }}
.kpi-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}}
.kpi-card.accent-red::before    {{ background: var(--red); }}
.kpi-card.accent-amber::before  {{ background: var(--amber); }}
.kpi-card.accent-blue::before   {{ background: var(--blue); }}
.kpi-card.accent-green::before  {{ background: var(--green); }}

.kpi-label {{
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    margin-bottom: 8px;
}}
.kpi-value {{
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -1px;
    line-height: 1.1;
}}
.kpi-sub {{
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 6px;
}}
.kpi-trend {{
    display: inline-flex;
    align-items: center;
    gap: 3px;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    margin-top: 8px;
}}
.kpi-trend.negative {{ background: rgba(239,68,68,0.12); color: var(--red-light); }}
.kpi-trend.positive {{ background: rgba(16,185,129,0.12); color: var(--green-light); }}

/* ── Chart Panels ─────────────────────────── */
.chart-row {{
    display: grid;
    gap: 16px;
    margin-bottom: 16px;
}}
.chart-row.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.chart-row.cols-3 {{ grid-template-columns: 2fr 1fr 1fr; }}
.chart-row.cols-1 {{ grid-template-columns: 1fr; }}

.chart-panel {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 24px;
}}
.chart-panel h3 {{
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 4px;
}}
.chart-panel .chart-subtitle {{
    font-size: 11px;
    color: var(--text-dim);
    margin-bottom: 16px;
}}
.chart-wrapper {{
    position: relative;
    width: 100%;
}}

/* ── Table ─────────────────────────────────── */
.table-panel {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 24px;
    margin-top: 16px;
    overflow-x: auto;
}}
.table-panel h3 {{
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 4px;
}}
.table-panel .table-subtitle {{
    font-size: 11px;
    color: var(--text-dim);
    margin-bottom: 16px;
}}
.table-panel .table-info {{
    font-size: 12px;
    color: var(--text-dim);
    margin-bottom: 12px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}}
thead th {{
    position: sticky;
    top: 0;
    background: var(--bg-card);
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.5px;
    border-bottom: 2px solid var(--border);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}}
thead th:hover {{ color: var(--blue-light); }}
thead th .sort-arrow {{ margin-left: 4px; opacity: 0.4; }}
thead th.sorted .sort-arrow {{ opacity: 1; }}

tbody td {{
    padding: 10px 12px;
    border-bottom: 1px solid rgba(51,65,85,0.5);
    white-space: nowrap;
}}
tbody tr {{ transition: background 0.15s; }}
tbody tr:hover {{ background: var(--bg-card-hover); }}

.badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.badge-critical {{ background: rgba(239,68,68,0.15); color: var(--red-light); }}
.badge-high     {{ background: rgba(245,158,11,0.15); color: var(--amber-light); }}
.badge-medium   {{ background: rgba(59,130,246,0.15); color: var(--blue-light); }}
.badge-low      {{ background: rgba(16,185,129,0.15); color: var(--green-light); }}

.risk-bar {{
    display: inline-block;
    height: 6px;
    border-radius: 3px;
    vertical-align: middle;
    margin-right: 6px;
}}

/* ── Footer ───────────────────────────────── */
.footer {{
    text-align: center;
    padding: 24px;
    font-size: 11px;
    color: var(--text-dim);
    border-top: 1px solid var(--border);
    margin-top: 40px;
}}

/* ── Responsive ───────────────────────────── */
@media (max-width: 1200px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .chart-row.cols-2 {{ grid-template-columns: 1fr; }}
    .chart-row.cols-3 {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 768px) {{
    .container {{ padding: 16px; }}
    .header {{ padding: 20px 16px; }}
    .kpi-grid {{ grid-template-columns: 1fr; }}
    .kpi-value {{ font-size: 26px; }}
}}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <div class="header-inner">
        <div>
            <h1>Revenue Leakage Intelligence</h1>
            <div class="subtitle">Executive Dashboard &mdash; Monitoring revenue erosion, risk concentration, and intervention priorities</div>
        </div>
        <div class="meta">
            <div>Period: {data['meta']['period_start']} to {data['meta']['period_end']} ({data['meta']['total_months']} months)</div>
            <div>Generated: {data['meta']['generated_at']}</div>
        </div>
    </div>
</div>

<div class="container">

    <!-- Filters -->
    <div class="filter-bar">
        <label>Segment</label>
        <select id="fSegment" onchange="applyFilters()">
            <option value="">All Segments</option>
            {"".join(f'<option value="{s}">{s}</option>' for s in data["filters"]["segments"])}
        </select>
        <label>Region</label>
        <select id="fRegion" onchange="applyFilters()">
            <option value="">All Regions</option>
            {"".join(f'<option value="{r}">{r}</option>' for r in data["filters"]["regions"])}
        </select>
        <label>Risk Tier</label>
        <select id="fTier" onchange="applyFilters()">
            <option value="">All Tiers</option>
            {"".join(f'<option value="{t}">{t}</option>' for t in data["filters"]["tiers"])}
        </select>
        <button class="filter-reset" onclick="resetFilters()">Reset</button>
    </div>

    <!-- KPI Cards -->
    <div class="kpi-grid">
        <div class="kpi-card accent-red">
            <div class="kpi-label">Total Revenue Leakage</div>
            <div class="kpi-value" id="kpiLeakage"></div>
            <div class="kpi-sub" id="kpiLeakageSub"></div>
            <div class="kpi-trend negative" id="kpiLeakageTrend"></div>
        </div>
        <div class="kpi-card accent-amber">
            <div class="kpi-label">Revenue at Risk</div>
            <div class="kpi-value" id="kpiAtRisk"></div>
            <div class="kpi-sub" id="kpiAtRiskSub"></div>
        </div>
        <div class="kpi-card accent-blue">
            <div class="kpi-label">High-Risk Accounts</div>
            <div class="kpi-value" id="kpiHighRisk"></div>
            <div class="kpi-sub" id="kpiHighRiskSub"></div>
        </div>
        <div class="kpi-card accent-green">
            <div class="kpi-label">Avg Collection Rate</div>
            <div class="kpi-value" id="kpiCollection"></div>
            <div class="kpi-trend" id="kpiCollTrend"></div>
        </div>
    </div>

    <!-- Row 1: Revenue Trend (full width) -->
    <div class="chart-row cols-1">
        <div class="chart-panel">
            <h3>Monthly Revenue: Contracted vs Collected</h3>
            <div class="chart-subtitle">The persistent gap between contracted and collected revenue reveals systematic leakage</div>
            <div class="chart-wrapper" style="height: 300px;">
                <canvas id="chartRevenue"></canvas>
            </div>
        </div>
    </div>

    <!-- Row 2: Risk Drivers + Tier Breakdown -->
    <div class="chart-row cols-2">
        <div class="chart-panel">
            <h3>Risk Driver Comparison by Segment</h3>
            <div class="chart-subtitle">Which leakage channels hit hardest across customer tiers</div>
            <div class="chart-wrapper" style="height: 280px;">
                <canvas id="chartDrivers"></canvas>
            </div>
        </div>
        <div class="chart-panel">
            <h3>Portfolio Risk Distribution</h3>
            <div class="chart-subtitle">Customer count and revenue at risk by tier</div>
            <div class="chart-wrapper" style="height: 280px;">
                <canvas id="chartTiers"></canvas>
            </div>
        </div>
    </div>

    <!-- Row 3: Segment Leakage Trend + Segment Summary -->
    <div class="chart-row cols-2">
        <div class="chart-panel">
            <h3>Leakage Gap by Segment Over Time</h3>
            <div class="chart-subtitle">Monthly contracted-minus-collected gap by customer segment</div>
            <div class="chart-wrapper" style="height: 280px;">
                <canvas id="chartSegTrend"></canvas>
            </div>
        </div>
        <div class="chart-panel">
            <h3>Segment Risk Summary</h3>
            <div class="chart-subtitle">Revenue concentration vs risk intensity</div>
            <div class="chart-wrapper" style="height: 280px;">
                <canvas id="chartSegSummary"></canvas>
            </div>
        </div>
    </div>

    <!-- Detail Table -->
    <div class="table-panel">
        <h3>High-Risk Accounts — Prioritized Intervention List</h3>
        <div class="table-subtitle">Top 100 accounts by composite risk score — click column headers to sort</div>
        <div class="table-info" id="tableInfo"></div>
        <div style="max-height: 500px; overflow-y: auto;">
            <table>
                <thead>
                    <tr>
                        <th data-col="id">Customer <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="segment">Segment <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="region">Region <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="acv" data-type="num">ACV <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="score" data-type="num">Risk Score <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="tier">Tier <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="at_risk" data-type="num">At Risk <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="churn" data-type="num">Churn <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="deterioration" data-type="num">Deter. <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="discount" data-type="num">Disc. <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="payment" data-type="num">Payment <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="engagement" data-type="num">Engage. <span class="sort-arrow">&#9650;</span></th>
                        <th data-col="collection" data-type="num">Coll. % <span class="sort-arrow">&#9650;</span></th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>
</div>

<div class="footer">
    Revenue Leakage Intelligence System &mdash; Data is synthetic for portfolio demonstration &mdash; Built with Chart.js
</div>

<script>
// ── Embedded Data ──────────────────────────────────────────────────────
const D = {json_data};

// ── Utility Functions ──────────────────────────────────────────────────
function fmt$(v) {{
    if (Math.abs(v) >= 1e6) return '$' + (v/1e6).toFixed(1) + 'M';
    if (Math.abs(v) >= 1e3) return '$' + (v/1e3).toFixed(0) + 'K';
    return '$' + v.toLocaleString();
}}

function fmtN(v) {{
    return v.toLocaleString();
}}

const tierClass = t => 'badge-' + t.toLowerCase();
const tierOrder = {{'Critical':0, 'High':1, 'Medium':2, 'Low':3}};

// ── Chart Theme ────────────────────────────────────────────────────────
const COLORS = {{
    blue: '#3B82F6', blueFaded: 'rgba(59,130,246,0.15)',
    red: '#EF4444', redFaded: 'rgba(239,68,68,0.15)',
    green: '#10B981', greenFaded: 'rgba(16,185,129,0.15)',
    amber: '#F59E0B', amberFaded: 'rgba(245,158,11,0.15)',
    purple: '#8B5CF6', purpleFaded: 'rgba(139,92,246,0.15)',
    teal: '#06B6D4', tealFaded: 'rgba(6,182,212,0.15)',
    text: '#94A3B8',
    grid: 'rgba(51,65,85,0.5)',
}};

const chartDefaults = {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
        legend: {{
            labels: {{ color: COLORS.text, font: {{ size: 11 }}, padding: 16, usePointStyle: true, pointStyleWidth: 10 }}
        }}
    }},
    scales: {{
        x: {{ ticks: {{ color: COLORS.text, font: {{ size: 10 }} }}, grid: {{ color: COLORS.grid }} }},
        y: {{ ticks: {{ color: COLORS.text, font: {{ size: 10 }} }}, grid: {{ color: COLORS.grid }} }}
    }}
}};

// ── Chart Instances (global for redraws) ───────────────────────────────
let chartRevenue, chartDrivers, chartTiers, chartSegTrend, chartSegSummary;

// ── Initialize KPIs ────────────────────────────────────────────────────
function renderKPIs(filtered) {{
    const k = D.kpis;
    document.getElementById('kpiLeakage').textContent = fmt$(k.total_leakage);
    document.getElementById('kpiLeakageSub').textContent = k.leakage_rate + '% of contracted revenue';
    const trendDir = k.leakage_trend > 0 ? 'negative' : 'positive';
    const trendArrow = k.leakage_trend > 0 ? '\\u2191' : '\\u2193';
    document.getElementById('kpiLeakageTrend').className = 'kpi-trend ' + trendDir;
    document.getElementById('kpiLeakageTrend').textContent = trendArrow + ' ' + Math.abs(k.leakage_trend).toFixed(1) + 'pp vs prior period';

    // At Risk — may be filtered
    const accts = filtered || D.accounts;
    const totalRisk = accts.reduce((s, a) => s + a.at_risk, 0);
    const totalACV = accts.reduce((s, a) => s + a.acv, 0);
    document.getElementById('kpiAtRisk').textContent = fmt$(totalRisk);
    document.getElementById('kpiAtRiskSub').textContent = (totalACV > 0 ? (totalRisk/totalACV*100).toFixed(1) : '0') + '% of portfolio ARR';

    const highCount = accts.filter(a => a.tier === 'High' || a.tier === 'Critical').length;
    document.getElementById('kpiHighRisk').textContent = highCount;
    document.getElementById('kpiHighRiskSub').textContent = 'of ' + accts.length + ' accounts shown require intervention';

    document.getElementById('kpiCollection').textContent = k.avg_collection + '%';
    const collTrend = document.getElementById('kpiCollTrend');
    const collDir = k.coll_trend < 0 ? 'negative' : 'positive';
    const collArrow = k.coll_trend < 0 ? '\\u2193' : '\\u2191';
    collTrend.className = 'kpi-trend ' + collDir;
    collTrend.textContent = collArrow + ' ' + Math.abs(k.coll_trend).toFixed(1) + 'pp vs prior period';
}}

// ── Revenue Trend Chart ────────────────────────────────────────────────
function renderRevenueTrend() {{
    const ctx = document.getElementById('chartRevenue').getContext('2d');
    if (chartRevenue) chartRevenue.destroy();

    const labels = D.monthly_trend.map(d => d.month);
    chartRevenue = new Chart(ctx, {{
        type: 'line',
        data: {{
            labels,
            datasets: [
                {{
                    label: 'Contracted',
                    data: D.monthly_trend.map(d => d.contracted),
                    borderColor: COLORS.blue,
                    backgroundColor: COLORS.blueFaded,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    borderWidth: 2,
                }},
                {{
                    label: 'Collected',
                    data: D.monthly_trend.map(d => d.collected),
                    borderColor: COLORS.green,
                    backgroundColor: COLORS.greenFaded,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    borderWidth: 2,
                }},
                {{
                    label: 'Leakage Gap',
                    data: D.monthly_trend.map(d => d.leakage),
                    borderColor: COLORS.red,
                    backgroundColor: 'transparent',
                    borderDash: [5, 3],
                    tension: 0.3,
                    pointRadius: 0,
                    borderWidth: 1.5,
                    yAxisID: 'y1',
                }},
            ]
        }},
        options: {{
            ...chartDefaults,
            interaction: {{ mode: 'index', intersect: false }},
            plugins: {{
                ...chartDefaults.plugins,
                tooltip: {{
                    callbacks: {{
                        label: ctx => ctx.dataset.label + ': ' + fmt$(ctx.raw)
                    }}
                }}
            }},
            scales: {{
                x: {{ ...chartDefaults.scales.x }},
                y: {{
                    ...chartDefaults.scales.y,
                    ticks: {{ ...chartDefaults.scales.y.ticks, callback: v => fmt$(v) }},
                    position: 'left',
                }},
                y1: {{
                    ...chartDefaults.scales.y,
                    ticks: {{ ...chartDefaults.scales.y.ticks, callback: v => fmt$(v) }},
                    position: 'right',
                    grid: {{ drawOnChartArea: false }},
                }}
            }}
        }}
    }});
}}

// ── Risk Drivers Chart ─────────────────────────────────────────────────
function renderDrivers() {{
    const ctx = document.getElementById('chartDrivers').getContext('2d');
    if (chartDrivers) chartDrivers.destroy();

    const drivers = D.risk_drivers;
    chartDrivers = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: drivers.map(d => d.segment),
            datasets: [
                {{ label: 'Churn',         data: drivers.map(d => d.churn),         backgroundColor: COLORS.red,    borderRadius: 4 }},
                {{ label: 'Deterioration',  data: drivers.map(d => d.deterioration), backgroundColor: COLORS.amber,  borderRadius: 4 }},
                {{ label: 'Discount',       data: drivers.map(d => d.discount),      backgroundColor: COLORS.purple, borderRadius: 4 }},
                {{ label: 'Payment',        data: drivers.map(d => d.payment),       backgroundColor: COLORS.teal,   borderRadius: 4 }},
            ]
        }},
        options: {{
            ...chartDefaults,
            indexAxis: 'y',
            plugins: {{ ...chartDefaults.plugins }},
            scales: {{
                x: {{ ...chartDefaults.scales.x, title: {{ display: true, text: 'Avg Risk Score', color: COLORS.text, font: {{ size: 10 }} }} }},
                y: {{ ...chartDefaults.scales.y }},
            }}
        }}
    }});
}}

// ── Tier Distribution Chart ────────────────────────────────────────────
function renderTiers(filtered) {{
    const ctx = document.getElementById('chartTiers').getContext('2d');
    if (chartTiers) chartTiers.destroy();

    // Recompute from filtered accounts
    const accts = filtered || D.accounts;
    const tierMap = {{}};
    accts.forEach(a => {{
        if (!tierMap[a.tier]) tierMap[a.tier] = {{ count: 0, risk: 0 }};
        tierMap[a.tier].count++;
        tierMap[a.tier].risk += a.at_risk;
    }});

    const tiers = ['Critical', 'High', 'Medium', 'Low'].filter(t => tierMap[t]);
    const tierColors = {{ Critical: COLORS.red, High: COLORS.amber, Medium: COLORS.blue, Low: COLORS.green }};

    chartTiers = new Chart(ctx, {{
        type: 'doughnut',
        data: {{
            labels: tiers,
            datasets: [{{
                data: tiers.map(t => tierMap[t]?.risk || 0),
                backgroundColor: tiers.map(t => tierColors[t]),
                borderColor: '#1E293B',
                borderWidth: 3,
                hoverOffset: 8,
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            cutout: '55%',
            plugins: {{
                legend: {{
                    position: 'right',
                    labels: {{ color: COLORS.text, font: {{ size: 11 }}, padding: 12, usePointStyle: true }}
                }},
                tooltip: {{
                    callbacks: {{
                        label: ctx => {{
                            const tier = tiers[ctx.dataIndex];
                            const info = tierMap[tier];
                            return tier + ': ' + fmt$(info.risk) + ' (' + info.count + ' accounts)';
                        }}
                    }}
                }}
            }}
        }}
    }});
}}

// ── Segment Leakage Trend ──────────────────────────────────────────────
function renderSegTrend() {{
    const ctx = document.getElementById('chartSegTrend').getContext('2d');
    if (chartSegTrend) chartSegTrend.destroy();

    const segColors = {{ Enterprise: COLORS.blue, 'Mid-Market': COLORS.purple, SMB: COLORS.teal }};
    const segFaded = {{ Enterprise: COLORS.blueFaded, 'Mid-Market': COLORS.purpleFaded, SMB: COLORS.tealFaded }};
    const st = D.segment_leakage_trend;
    const segs = Object.keys(st);

    chartSegTrend = new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: st[segs[0]].months,
            datasets: segs.map(s => ({{
                label: s,
                data: st[s].gaps,
                borderColor: segColors[s] || COLORS.blue,
                backgroundColor: segFaded[s] || COLORS.blueFaded,
                fill: true,
                tension: 0.3,
                pointRadius: 2,
                borderWidth: 2,
            }}))
        }},
        options: {{
            ...chartDefaults,
            interaction: {{ mode: 'index', intersect: false }},
            scales: {{
                x: {{ ...chartDefaults.scales.x }},
                y: {{ ...chartDefaults.scales.y, stacked: true,
                      ticks: {{ ...chartDefaults.scales.y.ticks, callback: v => fmt$(v) }} }},
            }}
        }}
    }});
}}

// ── Segment Summary Chart ──────────────────────────────────────────────
function renderSegSummary() {{
    const ctx = document.getElementById('chartSegSummary').getContext('2d');
    if (chartSegSummary) chartSegSummary.destroy();

    const ss = D.segment_summary;
    const segColors = {{ Enterprise: COLORS.blue, 'Mid-Market': COLORS.purple, SMB: COLORS.teal }};

    chartSegSummary = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: ss.map(s => s.segment),
            datasets: [
                {{
                    label: 'Portfolio ARR',
                    data: ss.map(s => s.total_arr),
                    backgroundColor: ss.map(s => segColors[s.segment] || COLORS.blue),
                    borderRadius: 4,
                }},
                {{
                    label: 'Revenue at Risk',
                    data: ss.map(s => s.total_risk),
                    backgroundColor: ss.map(s => segColors[s.segment]?.replace(')', ',0.4)').replace('rgb', 'rgba') || COLORS.blueFaded),
                    borderColor: ss.map(s => segColors[s.segment] || COLORS.blue),
                    borderWidth: 2,
                    borderRadius: 4,
                    borderDash: [3, 3],
                }}
            ]
        }},
        options: {{
            ...chartDefaults,
            plugins: {{
                ...chartDefaults.plugins,
                tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmt$(ctx.raw) }} }}
            }},
            scales: {{
                x: {{ ...chartDefaults.scales.x }},
                y: {{ ...chartDefaults.scales.y,
                      ticks: {{ ...chartDefaults.scales.y.ticks, callback: v => fmt$(v) }} }}
            }}
        }}
    }});
}}

// ── Table Rendering ────────────────────────────────────────────────────
let sortCol = 'score';
let sortDir = -1;  // -1 = desc

function renderTable(filtered) {{
    const accts = filtered || D.accounts;

    // Sort
    const sorted = [...accts].sort((a, b) => {{
        let va = a[sortCol], vb = b[sortCol];
        if (typeof va === 'string') return sortDir * va.localeCompare(vb);
        return sortDir * (va - vb);
    }});

    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = sorted.map(a => `
        <tr>
            <td><strong>${{a.id}}</strong></td>
            <td>${{a.segment}}</td>
            <td>${{a.region}}</td>
            <td>${{fmt$(a.acv)}}</td>
            <td>
                <span class="risk-bar" style="width:${{Math.min(a.score, 100) * 0.6}}px;background:${{
                    a.score >= 40 ? COLORS.red : a.score >= 25 ? COLORS.amber : COLORS.blue
                }}"></span>
                ${{a.score}}
            </td>
            <td><span class="badge ${{tierClass(a.tier)}}">${{a.tier}}</span></td>
            <td>${{fmt$(a.at_risk)}}</td>
            <td>${{a.churn}}</td>
            <td>${{a.deterioration}}</td>
            <td>${{a.discount}}</td>
            <td>${{a.payment}}</td>
            <td>${{a.engagement}}</td>
            <td>${{a.collection}}%</td>
        </tr>
    `).join('');

    document.getElementById('tableInfo').textContent = `Showing ${{sorted.length}} of ${{D.accounts.length}} accounts`;

    // Update header sort indicators
    document.querySelectorAll('thead th').forEach(th => {{
        th.classList.toggle('sorted', th.dataset.col === sortCol);
        const arrow = th.querySelector('.sort-arrow');
        if (arrow) arrow.innerHTML = th.dataset.col === sortCol ? (sortDir === 1 ? '&#9650;' : '&#9660;') : '&#9650;';
    }});
}}

// ── Column sort click handler ──────────────────────────────────────────
document.querySelectorAll('thead th').forEach(th => {{
    th.addEventListener('click', () => {{
        const col = th.dataset.col;
        if (!col) return;
        if (sortCol === col) sortDir *= -1;
        else {{ sortCol = col; sortDir = th.dataset.type === 'num' ? -1 : 1; }}
        applyFilters();
    }});
}});

// ── Filter Logic ───────────────────────────────────────────────────────
function getFiltered() {{
    const seg  = document.getElementById('fSegment').value;
    const reg  = document.getElementById('fRegion').value;
    const tier = document.getElementById('fTier').value;

    return D.accounts.filter(a =>
        (!seg  || a.segment === seg) &&
        (!reg  || a.region  === reg) &&
        (!tier || a.tier    === tier)
    );
}}

function applyFilters() {{
    const filtered = getFiltered();
    renderKPIs(filtered);
    renderTiers(filtered);
    renderTable(filtered);
}}

function resetFilters() {{
    document.getElementById('fSegment').value = '';
    document.getElementById('fRegion').value = '';
    document.getElementById('fTier').value = '';
    applyFilters();
}}

// ── Init ───────────────────────────────────────────────────────────────
renderKPIs();
renderRevenueTrend();
renderDrivers();
renderTiers();
renderSegTrend();
renderSegSummary();
renderTable();
</script>
</body>
</html>"""

    return html


def _render_publication_dashboard(data):
    """Render via the shared publication-ready template in scripts/redesign_dashboard.py.

    Keeping a single source of truth for the design means re-running this builder
    never reverts the dashboard to the legacy template. Falls back to the in-file
    legacy ``build_html`` only if the template module cannot be loaded.
    """
    import importlib.util

    template_path = ROOT / "scripts" / "redesign_dashboard.py"
    try:
        spec = importlib.util.spec_from_file_location("redesign_dashboard", template_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.render(data)
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"   ! template module unavailable ({exc}); using legacy layout")
        return build_html(data)


def main():
    print("=" * 60)
    print("  EXECUTIVE DASHBOARD BUILDER")
    print("  Revenue Leakage Intelligence System")
    print("=" * 60)

    print("\n1. Loading and preparing data...")
    data = load_and_prepare()

    print("2. Building HTML dashboard...")
    html = _render_publication_dashboard(data)

    out_path = OUT / "executive_dashboard.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = out_path.stat().st_size / 1024
    print(f"\n3. Dashboard saved: {out_path}")
    print(f"   Size: {size_kb:.0f} KB")
    print(f"   Accounts embedded: {len(data['accounts'])}")
    print(f"   Monthly data points: {len(data['monthly_trend'])}")
    print(f"   Segments: {', '.join(data['filters']['segments'])}")
    print(f"   Regions: {', '.join(data['filters']['regions'])}")
    print(f"\n   Open in browser: file://{out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
