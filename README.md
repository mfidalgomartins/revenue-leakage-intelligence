# Revenue Leakage Intelligence System

A production-grade analytics system that detects hidden revenue leakage across four dimensions: silent churn, gradual customer deterioration, discount anomalies, and payment failures. Built to demonstrate senior-level analytical methodology, data validation, and stakeholder-ready outputs.

## Key Findings

**The company is losing $6.0M (18.2%) of contracted revenue** through collection failures ($4.5M) and discounting ($1.5M).

| Metric | Value |
|--------|-------|
| Total ARR | $19.2M |
| 24-month contracted revenue | $33.1M |
| Total leakage | $6.0M (18.2% of contracted) |
| Revenue at risk (scored) | $4.2M (21.7% of ARR) |
| Collection rate | 85.7% |
| #1 leakage driver | Payment failures (44% of risk score) |
| Critical + High risk customers | 1 + 47 |
| Top 10% revenue concentration | 42.4% |
| Engagement trend | Declining (66.7 → 52.0) |

Top 20 accounts (4% of customer base) represent 25% of all revenue at risk — targeted intervention on these accounts is the highest-leverage action.

## Architecture

```
├── src/
│   ├── data_generator.py      # Synthetic B2B SaaS data with embedded leakage patterns
│   ├── data_profiler.py       # Formal data profiling (types, nulls, distributions)
│   ├── leakage_analyzer.py    # Core analysis: churn, deterioration, discounts, payments
│   ├── visualizations.py      # 7 professional charts with insight-driven titles
│   ├── dashboard_builder.py   # Self-contained HTML dashboard with KPIs + filters
│   └── validators.py          # 19 automated validation checks
├── scripts/
│   ├── run_pipeline.py        # End-to-end orchestrator
│   ├── explore_data.py        # Formal data exploration (8 tables, 10 checks each)
│   └── run_analysis.py        # Formal business analysis (9 sections, 12 validations)
├── notebooks/
│   └── analysis.ipynb         # Exploratory analysis notebook
├── data/
│   ├── raw/                   # Generated source data (3 tables)
│   └── processed/             # Analytical tables (5 tables)
├── outputs/
│   ├── charts/                # 7 publication-quality visualizations
│   └── reports/               # Validation report, metrics, profiles
├── dashboard/
│   └── executive_dashboard.html  # Executive dashboard (open in browser)
└── docs/
    └── methodology.md         # Full methodology documentation
```

## Analysis Dimensions

### 1. Silent Churn Detection (30% weight)
Identifies customers with declining engagement who haven't formally churned. Uses rolling engagement trends and absolute thresholds to flag pre-churn signals before revenue impact materializes.

### 2. Gradual Deterioration (25% weight)
Detects sustained MRR decline using first-half vs second-half comparison and 3-month rolling trends. Separates genuine deterioration from seasonal variation.

### 3. Discount Anomaly Detection (20% weight)
Flags excessive discounting at both customer and sales rep level. Quantifies the revenue impact of discount patterns and identifies reps who systematically give above-average discounts.

### 4. Payment Anomalies (25% weight)
Tracks the gap between billed and collected revenue. Identifies customers with recurring failed payments, partial payments, and declining collection rates.

## Quick Start

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt

# Run full pipeline (data generation + profiling + analysis + charts + dashboard)
python scripts/run_pipeline.py

# Run formal business analysis
python scripts/run_analysis.py

# Run data exploration
python scripts/explore_data.py

# Run automated tests
python -m pytest tests/

# Open dashboard
open dashboard/executive_dashboard.html
```

## Outputs

- **Executive Dashboard** (`dashboard/executive_dashboard.html`): Self-contained HTML with KPI cards, interactive charts, filters, and a sortable risk scorecard table. Can be shared via email or Slack.
- **Risk Scorecard** (`data/processed/risk_scorecard.csv`): Customer-level composite risk scores with dimensional breakdown.
- **Business Analysis Report** (`outputs/reports/revenue_leakage_analysis.txt`): Formal 9-section analysis with question decomposition, leakage driver ranking, segment analysis, trend analysis, customer prioritization, and executive summary.
- **Data Exploration Report** (`outputs/reports/data_exploration_report.txt`): Formal profiling of all 8 tables — grain, PKs, column classification, nulls, cardinality, distributions, outliers, cross-field consistency, and quality issue register.
- **Validation Report** (`outputs/reports/validation_report.txt`): 19 automated checks — all passing.
- **Charts** (`outputs/charts/`): 7 publication-quality visualizations with insight-driven titles.

## Data Exploration

A formal exploration pass profiles all 8 project tables across 10 dimensions:

| Check | Result |
|-------|--------|
| Primary key uniqueness | ✅ All 8 tables unique on declared PK |
| Null completeness | ✅ 6/8 tables zero nulls; 2 scorecard cols have structural nulls (14.6%) |
| Temporal coverage | ✅ 24/24 months present, no gaps |
| Cross-field consistency | ✅ collected ≤ billed, composite = weighted sum |
| Issues found | 0 CRITICAL, 13 WARNING, 11 INFO |

Run it: `python scripts/explore_data.py`

## Validation

19 automated checks verify data quality and analytical integrity:
- Row counts, null checks, reconciliation (collected ≤ billed)
- Score bounds (0-100), weighted-sum verification
- Join safety, partial-period detection, date coverage

All 19 checks PASS.

## Methodology

See [docs/methodology.md](docs/methodology.md) for complete documentation of data architecture, scoring methodology, and limitations.

## Tech Stack

- **Python 3** (pandas, numpy, scikit-learn, matplotlib, seaborn)
- **HTML/CSS/JS** (self-contained dashboard)

## Limitations

1. Uses synthetic data — patterns are realistic but generated
2. Risk weights are judgement-based, not empirically calibrated
3. Scores indicate risk correlation, not causation
4. Point-in-time analysis without predictive modeling
5. No external market signals incorporated
