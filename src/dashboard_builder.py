"""
Executive Dashboard Builder
Self-contained HTML dashboard with KPIs, charts, filters, and detail table.
"""
import os
import base64
import json
import pandas as pd


def encode_image(path):
    """Encode image to base64 for embedding in HTML."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def build_dashboard(scorecard, summary_metrics, concentration, charts_dir, output_path):
    """Build self-contained HTML dashboard."""

    # Prepare chart images as base64
    chart_files = sorted([f for f in os.listdir(charts_dir) if f.endswith(".png")])
    charts_b64 = {}
    for cf in chart_files:
        charts_b64[cf] = encode_image(os.path.join(charts_dir, cf))

    # Prepare table data
    table_cols = ["customer_id", "company_name", "segment", "region", "industry",
                  "annual_contract_value", "composite_risk_score", "risk_tier",
                  "revenue_at_risk", "risk_score_churn", "risk_score_deterioration",
                  "risk_score_discount", "risk_score_payment"]
    table_data = scorecard[table_cols].head(100).to_dict("records")

    # Format currency values
    for row in table_data:
        row["annual_contract_value"] = f"${row['annual_contract_value']:,.0f}"
        row["revenue_at_risk"] = f"${row['revenue_at_risk']:,.0f}"

    html = _build_html(summary_metrics, concentration, charts_b64, table_data, table_cols)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nDashboard saved: {output_path}")
    return output_path


def _build_html(metrics, concentration, charts, table_data, table_cols):
    """Generate the full HTML string."""

    # Chart sections
    chart_sections = ""
    chart_titles = {
        "01_revenue_trend.png": "Revenue Trend & Collection Gap",
        "02_leakage_waterfall.png": "Revenue Leakage Waterfall",
        "03_risk_distribution.png": "Risk Distribution by Segment",
        "04_discount_by_rep.png": "Discount Impact by Sales Rep",
        "05_engagement_vs_revenue.png": "Engagement vs Revenue",
        "06_collection_trend.png": "Collection Rate Trend",
        "07_concentration_pareto.png": "Revenue Concentration (Pareto)",
    }
    for fname, b64 in charts.items():
        title = chart_titles.get(fname, fname)
        chart_sections += f'''
        <div class="chart-container">
            <h3>{title}</h3>
            <img src="data:image/png;base64,{b64}" alt="{title}">
        </div>
        '''

    # Table rows
    header_labels = {
        "customer_id": "Customer ID", "company_name": "Company",
        "segment": "Segment", "region": "Region", "industry": "Industry",
        "annual_contract_value": "ACV", "composite_risk_score": "Risk Score",
        "risk_tier": "Risk Tier", "revenue_at_risk": "Revenue at Risk",
        "risk_score_churn": "Churn", "risk_score_deterioration": "Deterioration",
        "risk_score_discount": "Discount", "risk_score_payment": "Payment",
    }
    th = "".join(f'<th>{header_labels.get(c, c)}</th>' for c in table_cols)
    rows = ""
    for row in table_data:
        tier = row.get("risk_tier", "")
        tier_class = f'tier-{tier.lower()}' if tier else ''
        cells = ""
        for c in table_cols:
            val = row.get(c, "")
            if c == "risk_tier":
                cells += f'<td><span class="badge {tier_class}">{val}</span></td>'
            else:
                cells += f'<td>{val}</td>'
        rows += f'<tr class="{tier_class}-row">{cells}</tr>\n'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Revenue Leakage Intelligence Dashboard</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #f5f7fa;
        color: #2c3e50;
        line-height: 1.6;
    }}
    .header {{
        background: linear-gradient(135deg, #1B4F72 0%, #2E86C1 100%);
        color: white;
        padding: 30px 40px;
    }}
    .header h1 {{ font-size: 28px; margin-bottom: 5px; }}
    .header p {{ opacity: 0.85; font-size: 14px; }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 20px 40px; }}

    /* KPI Cards */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin: 25px 0;
    }}
    .kpi-card {{
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border-left: 4px solid #2E86C1;
    }}
    .kpi-card.danger {{ border-left-color: #C0392B; }}
    .kpi-card.warning {{ border-left-color: #E67E22; }}
    .kpi-card.success {{ border-left-color: #27AE60; }}
    .kpi-label {{ font-size: 12px; text-transform: uppercase; color: #7f8c8d; letter-spacing: 0.5px; }}
    .kpi-value {{ font-size: 28px; font-weight: 700; margin: 4px 0; }}
    .kpi-detail {{ font-size: 12px; color: #95a5a6; }}

    /* Charts */
    .charts-grid {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 24px;
        margin: 25px 0;
    }}
    .chart-container {{
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .chart-container h3 {{ margin-bottom: 12px; font-size: 16px; }}
    .chart-container img {{ width: 100%; height: auto; border-radius: 8px; }}

    /* Filters */
    .filters {{
        background: white;
        border-radius: 12px;
        padding: 16px 24px;
        margin: 25px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        display: flex;
        gap: 16px;
        align-items: center;
        flex-wrap: wrap;
    }}
    .filters label {{ font-size: 13px; font-weight: 600; }}
    .filters select {{
        padding: 6px 12px;
        border: 1px solid #ddd;
        border-radius: 6px;
        font-size: 13px;
    }}

    /* Table */
    .table-container {{
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        overflow-x: auto;
        margin: 25px 0;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{
        background: #f8f9fa;
        padding: 10px 12px;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid #e9ecef;
        white-space: nowrap;
    }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }}
    tr:hover {{ background: #f8f9fa; }}

    .badge {{
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }}
    .tier-critical {{ background: #fde8e8; color: #C0392B; }}
    .tier-high {{ background: #fef3e2; color: #E67E22; }}
    .tier-medium {{ background: #fef9e7; color: #b7950b; }}
    .tier-low {{ background: #e8f8f5; color: #27AE60; }}

    .footer {{
        text-align: center;
        padding: 30px;
        color: #95a5a6;
        font-size: 12px;
    }}
    @media (max-width: 768px) {{
        .container {{ padding: 10px 16px; }}
        .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
</style>
</head>
<body>
<div class="header">
    <h1>Revenue Leakage Intelligence Dashboard</h1>
    <p>Executive summary of revenue risk across churn, deterioration, discounting, and payment dimensions</p>
</div>

<div class="container">
    <!-- KPI Cards -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Total ARR</div>
            <div class="kpi-value">${metrics['total_arr']/1e6:.1f}M</div>
            <div class="kpi-detail">Annual Recurring Revenue</div>
        </div>
        <div class="kpi-card danger">
            <div class="kpi-label">Revenue at Risk</div>
            <div class="kpi-value">${metrics['total_revenue_at_risk']/1e6:.1f}M</div>
            <div class="kpi-detail">{metrics['pct_revenue_at_risk']:.1f}% of ARR</div>
        </div>
        <div class="kpi-card warning">
            <div class="kpi-label">Critical Risk Customers</div>
            <div class="kpi-value">{metrics['critical_risk_customers']}</div>
            <div class="kpi-detail">+ {metrics['high_risk_customers']} High Risk</div>
        </div>
        <div class="kpi-card success">
            <div class="kpi-label">Collection Rate</div>
            <div class="kpi-value">{metrics['overall_collection_rate']:.1f}%</div>
            <div class="kpi-detail">Overall collected / billed</div>
        </div>
        <div class="kpi-card warning">
            <div class="kpi-label">Avg Discount (when applied)</div>
            <div class="kpi-value">{metrics['avg_discount_when_applied']:.1f}%</div>
            <div class="kpi-detail">Across all discounted invoices</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">MRR Growth</div>
            <div class="kpi-value">{metrics['mrr_growth_pct']:+.1f}%</div>
            <div class="kpi-detail">Month-over-month</div>
        </div>
        <div class="kpi-card warning">
            <div class="kpi-label">Top 10% Customer Share</div>
            <div class="kpi-value">{metrics['top_10pct_concentration']:.1f}%</div>
            <div class="kpi-detail">Revenue concentration</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">HHI Index</div>
            <div class="kpi-value">{metrics['hhi']:.0f}</div>
            <div class="kpi-detail">{concentration['hhi_interpretation']} concentration</div>
        </div>
    </div>

    <!-- Filters -->
    <div class="filters">
        <label>Filter Table:</label>
        <select id="filterSegment" onchange="filterTable()">
            <option value="">All Segments</option>
            <option value="Enterprise">Enterprise</option>
            <option value="Mid-Market">Mid-Market</option>
            <option value="SMB">SMB</option>
        </select>
        <select id="filterTier" onchange="filterTable()">
            <option value="">All Risk Tiers</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
        </select>
        <select id="filterRegion" onchange="filterTable()">
            <option value="">All Regions</option>
            <option value="North America">North America</option>
            <option value="Europe">Europe</option>
            <option value="APAC">APAC</option>
            <option value="LATAM">LATAM</option>
        </select>
    </div>

    <!-- Charts -->
    <div class="charts-grid">
        {chart_sections}
    </div>

    <!-- Detail Table -->
    <div class="table-container">
        <h3>Customer Risk Scorecard (Top 100 by Risk Score)</h3>
        <table id="riskTable">
            <thead><tr>{th}</tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
</div>

<div class="footer">
    Revenue Leakage Intelligence System &mdash; Generated automatically &mdash; Data is synthetic for demonstration purposes
</div>

<script>
function filterTable() {{
    const seg = document.getElementById('filterSegment').value;
    const tier = document.getElementById('filterTier').value;
    const region = document.getElementById('filterRegion').value;
    const rows = document.querySelectorAll('#riskTable tbody tr');
    rows.forEach(row => {{
        const cells = row.querySelectorAll('td');
        const rowSeg = cells[2]?.textContent || '';
        const rowRegion = cells[3]?.textContent || '';
        const rowTier = cells[7]?.textContent?.trim() || '';
        const show = (!seg || rowSeg === seg) &&
                     (!tier || rowTier === tier) &&
                     (!region || rowRegion === region);
        row.style.display = show ? '' : 'none';
    }});
}}
</script>
</body>
</html>'''
