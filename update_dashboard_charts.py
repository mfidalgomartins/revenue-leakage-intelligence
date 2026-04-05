#!/usr/bin/env python3
"""Update dashboard HTML with 10 publication-quality charts."""

import base64
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DASHBOARD = PROJECT_ROOT / "dashboard" / "index.html"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts" / "publication"

CHARTS = [
    ("01_revenue_erosion_trend.png", "Revenue Erosion: Contract to Collection"),
    ("02_risk_composition_over_time.png", "Leakage Risk Composition Over Time"),
    ("03_risk_drivers_by_segment.png", "Risk Driver Intensity by Segment"),
    ("04_top25_revenue_at_risk.png", "Top 25 Customers by Revenue at Risk"),
    ("05_segment_mix_donuts.png", "Segment Mix: Revenue vs Risk"),
    ("06_cohort_retention_heatmap.png", "Cohort Revenue Retention"),
    ("07_payment_anomaly_trend.png", "Payment Anomalies & Engagement"),
    ("08_prioritization_matrix.png", "Customer Prioritization Matrix"),
    ("09_collection_rate_distribution.png", "Collection Rate Distribution"),
    ("10_rep_discount_impact.png", "Sales Rep Discount Impact"),
]

if not DASHBOARD.exists():
    raise FileNotFoundError(f"Dashboard não encontrado: {DASHBOARD}")
if not CHARTS_DIR.exists():
    raise FileNotFoundError(f"Pasta de charts não encontrada: {CHARTS_DIR}")

html = DASHBOARD.read_text(encoding="utf-8")

# 1. Update CSS: change .charts-grid to 2-column layout
html = html.replace(
    "grid-template-columns: 1fr;",
    "grid-template-columns: repeat(2, 1fr);"
)

# 2. Build new charts section
chart_blocks = []
for filename, title in CHARTS:
    img_path = CHARTS_DIR / filename
    if not img_path.exists():
        raise FileNotFoundError(f"Chart não encontrado: {img_path}")
    b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
    chart_blocks.append(
        f'        <div class="chart-container">\n'
        f'            <h3>{title}</h3>\n'
        f'            <img src="data:image/png;base64,{b64}" alt="{title}">\n'
        f'        </div>'
    )

new_section = (
    '    <!-- Charts -->\n'
    '    <h2 style="margin: 30px 0 15px; font-size: 22px; color: #1B4F72;">Publication-Quality Analysis</h2>\n'
    '    <div class="charts-grid">\n'
    + "\n".join(chart_blocks) + "\n"
    '    </div>\n'
)

# 3. Replace old charts section (between <!-- Charts --> and <!-- Detail Table -->)
pattern = r'    <!-- Charts -->.*?(?=    <!-- Detail Table -->)'
html = re.sub(pattern, new_section, html, flags=re.DOTALL)

DASHBOARD.write_text(html, encoding="utf-8")
print(f"Dashboard updated: {DASHBOARD}")
print(f"File size: {DASHBOARD.stat().st_size:,} bytes")
