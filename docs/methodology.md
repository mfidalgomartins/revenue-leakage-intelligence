# Methodology

## Revenue Leakage Intelligence System

### Problem Statement

Revenue leakage is the silent erosion of expected revenue through discount abuse, collection failures, silent customer churn, and revenue concentration risk. Most companies only detect leakage retroactively during quarterly reviews. This system provides early detection and quantification.

### Data Architecture

#### Source Tables

| Table | Grain | Rows | Description |
|-------|-------|------|-------------|
| `customers` | 1 row per customer | 500 | Customer master with segment, industry, region, ACV |
| `monthly_revenue` | 1 row per customer-month | ~11,500 | Monthly billing, collection, engagement |
| `product_usage` | 1 row per customer-month-feature | 60,000 | Feature-level usage metrics |

#### Analytical Tables (Processed)

| Table | Grain | Description |
|-------|-------|-------------|
| `risk_scorecard` | 1 row per customer | Composite risk score across 4 dimensions |
| `payment_analysis` | 1 row per customer | Payment behavior and collection gaps |
| `discount_analysis` | 1 row per customer | Discount patterns and anomalies |
| `rep_discount_impact` | 1 row per sales rep | Rep-level discount behavior |
| `deterioration_analysis` | 1 row per customer | MRR trend analysis |

### Analysis Dimensions

#### 1. Silent Churn Detection (Weight: 30%)
- **Method**: 3-month rolling engagement trend + absolute engagement threshold
- **Signal**: Engagement slope < -2 AND average engagement < 30
- **Why it matters**: Customers who stop using the product before formally churning represent the highest-risk retention opportunities

#### 2. Gradual Deterioration (Weight: 25%)
- **Method**: First-half vs second-half MRR comparison + rolling 3-month trend slope
- **Signal**: MRR change > -10% AND negative trend slope
- **Why it matters**: Gradual downgrades and scope reductions compound silently

#### 3. Discount Anomalies (Weight: 20%)
- **Method**: Customer-level and rep-level discount frequency and magnitude analysis
- **Signal**: Maximum discount > 25%, high discount frequency
- **Why it matters**: Uncontrolled discounting erodes margins and sets precedent

#### 4. Payment Anomalies (Weight: 25%)
- **Method**: Collection rate analysis, failed/partial payment tracking
- **Signal**: Collection rate < 80%, recurring failed payments
- **Why it matters**: Billed revenue that is never collected is direct leakage

### Composite Risk Score

```
composite_score = (
    churn_risk × 0.30 +
    deterioration_risk × 0.25 +
    discount_risk × 0.20 +
    payment_risk × 0.25
)
```

Risk tiers:
- **Low** (0-20): Healthy accounts
- **Medium** (20-40): Monitor
- **High** (40-60): Intervention needed
- **Critical** (60-100): Immediate action required

Revenue at risk = ACV × (composite_score / 100)

### Validation Checks

19 automated checks covering:
- Row count sanity
- Null completeness on critical fields
- Reconciliation (collected ≤ billed)
- Aggregation consistency (customer ARR = scorecard ARR)
- Score bounds (0-100)
- Composite score weighted-sum verification
- Revenue at risk ≤ ACV
- Date coverage completeness
- Join explosion prevention
- Partial period detection

### Data Exploration Findings

A rigorous formal exploration was performed across all 8 project tables (3 source + 5 analytical). Full report: `outputs/reports/data_exploration_report.txt`.

#### Table Census

| Table | Rows | Cols | Grain | PK Unique | Nulls |
|-------|------|------|-------|-----------|-------|
| `customers` | 500 | 9 | customer | ✅ | 0 |
| `monthly_revenue` | 11,492 | 14 | customer × month | ✅ | 0 |
| `product_usage` | 60,000 | 5 | customer × month × feature | ✅ | 0 |
| `risk_scorecard` | 500 | 20 | customer | ✅ | 2 cols (14.6%) |
| `payment_analysis` | 500 | 10 | customer | ✅ | 0 |
| `discount_analysis` | 500 | 8 | customer | ✅ | 0 |
| `rep_discount_impact` | 20 | 7 | sales rep | ✅ | 0 |
| `deterioration_analysis` | 500 | 7 | customer | ✅ | 0 |

#### Column Classification Summary

- **IDs**: `customer_id` (PK in 7 tables), `sales_rep` (FK, 20 distinct values)
- **Dimensions**: `segment` (3), `region` (4), `industry` (8), `payment_status` (5), `risk_tier` (4), `leakage_pattern` (4), `feature` (5)
- **Metrics**: 40+ numeric columns across tables — revenue funnel (contracted → billed → collected), risk scores (4 dimensions + composite), behavioral (engagement, sessions, active_users, days_to_pay)
- **Temporal**: `month` (24 months, 2024-01 to 2025-12, no gaps), `onboard_date` (2023-01 to 2025-12)
- **Booleans**: `is_churned` (18.4% true), `is_deteriorating` (41.6%), `excessive_discount` (60.4%), `silent_churn_risk`

#### Data Quality Issue Register

**24 issues found: 0 CRITICAL, 13 WARNING, 11 INFO**

Key findings:
1. **Engagement score exceeds expected 0-100 range**: 1 value at 103.4 in `monthly_revenue`. Impact: minimal (1 row), but signals need for clamping in data generation.
2. **Scorecard nulls**: `avg_engagement` and `engagement_slope` have 73 nulls (14.6%) in `risk_scorecard` — these are churned customers who dropped out before the lookback window. The nulls are structurally expected, not data quality failures.
3. **Right-skewed revenue distributions**: MRR fields show skew of +2.0 to +2.4 (expected for enterprise SaaS where a few large accounts dominate). IQR-based outlier rates of 5-7% are driven by Enterprise segment, not errors.
4. **`mrr_change_pct` flagged as "negative in a typically positive field"**: This is a false positive — negative change is the expected signal for deterioration. The column name does not imply positivity.
5. **`median_discount` is 100% zeros** across all 20 reps: Most months have no discount (69.8% of revenue rows have discount_pct = 0), so median is correctly 0. Column is uninformative and could be dropped.
6. **`total_gap` highly skewed** (skew +3.58, kurtosis +18.21): A few Enterprise accounts drive massive collection gaps. This is analytically meaningful, not an error.
7. **`discount_months`/`total_months` misclassified as temporal**: The classifier interprets "months" in the name as temporal, but these are integer count columns. No functional impact.

#### Analytically Useful Dimensions & Metrics

**Best slicing dimensions** (ordered by analytical value):
1. `segment` — primary business segmentation (Enterprise/Mid-Market/SMB)
2. `risk_tier` — actionable prioritization lens
3. `leakage_pattern` — root cause grouping (stable/gradual_decline/sudden_drop/seasonal)
4. `sales_rep` — enables rep-level accountability analysis
5. `region` / `industry` — geographic and vertical cuts

**Most powerful metrics**:
- Revenue funnel: `mrr_contracted` → `mrr_billed` → `mrr_collected` (3-stage leakage measurement)
- `composite_risk_score` — single number for prioritization
- `revenue_at_risk` — dollar quantification of composite risk
- `engagement_score` — leading indicator of churn
- `collection_rate` — realized vs billed ratio

#### Temporal Coverage

- **Monthly revenue**: 24 months (Jan 2024 – Dec 2025), all months present, no gaps
- **Rows per month**: 414-500 (CV = 0.06) — declining count reflects customer churn, not data gaps
- **Product usage**: 2,500 rows/month (perfectly balanced: 500 customers × 5 features)

### Analysis Results

A formal business analysis (`scripts/run_analysis.py`) was executed against the full dataset. Full report: `outputs/reports/revenue_leakage_analysis.txt`.

#### Revenue Funnel (24 months)

| Stage | Amount | Leakage |
|-------|--------|---------|
| Contracted revenue | $33.1M | — |
| After discounts (billed) | $31.6M | −$1.5M (4.6%) |
| After collection failures (collected) | $27.0M | −$4.5M (14.3% of billed) |
| **Total leakage** | | **$6.0M (18.2%)** |

#### Leakage Driver Ranking (weighted risk contribution)

| Driver | Weighted Points | % of Total |
|--------|----------------|------------|
| Payment failures | 9.77 | 44.3% |
| MRR deterioration | 5.62 | 25.5% |
| Silent churn risk | 3.71 | 16.8% |
| Discount anomalies | 2.94 | 13.4% |

Payment risk is the dominant driver across all three segments.

#### Segment Risk Analysis

| Segment | Customers | ARR | % of Risk | Risk Intensity |
|---------|-----------|-----|-----------|----------------|
| Enterprise | 89 | $11.5M | 57.4% | 0.96× |
| Mid-Market | 152 | $5.6M | 31.4% | 1.08× |
| SMB | 259 | $2.2M | 11.1% | 0.99× |

Mid-Market shows slightly disproportionate risk (1.08× intensity).
Hotspot: Enterprise × Europe — 27.2% of ACV at risk.

#### Trend Analysis (first 6 months vs last 6 months)

| Metric | Early | Late | Change | Signal |
|--------|-------|------|--------|--------|
| Collection rate | 86.3% | 84.8% | −1.5pp | Worsening |
| Avg engagement | 66.7 | 52.0 | −14.8 | Worsening |
| Total leakage rate | 17.8% | 18.9% | +1.1pp | Worsening |
| Active customers | 500 | 433 | −67 | Worsening |

#### Validation

12 calculation checks executed — all PASS. Covers revenue funnel arithmetic, segment ARR consistency, score bounds, weighted-sum verification, and revenue-at-risk caps.

### Limitations

1. **Synthetic data**: Patterns are generated, not observed from real business operations
2. **Static weights**: The 30/25/20/25 weighting is judgement-based, not empirically optimized
3. **No causal modeling**: Scores indicate correlation with risk, not causation
4. **Point-in-time**: Scores represent current state, not trajectory prediction
5. **No external signals**: Does not incorporate market conditions, competitor actions, or macroeconomic factors

### Reproducibility

- Fixed random seed (42) ensures identical synthetic data across runs
- All transformations are deterministic
- Pipeline can be re-run end-to-end via `python scripts/run_pipeline.py`
