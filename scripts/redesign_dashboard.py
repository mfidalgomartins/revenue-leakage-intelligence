#!/usr/bin/env python3
"""Rebuild the executive dashboard with a publication-ready design.

Reads the data object already embedded in the current dashboard HTML
(so the underlying numbers stay identical) and re-emits a fully
redesigned single-file dashboard: Geist typography, a restrained
indigo/neutral/red colour system, dominant KPI numbers, a leakage-gap
hero chart, a driver heatmap and a polished light + dark theme.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "executive_dashboard.html"


class _NumpySafe(json.JSONEncoder):
    """Serialise numpy scalars/arrays emitted by the analysis pipeline."""

    def default(self, obj):
        if hasattr(obj, "item"):  # numpy scalar
            return obj.item()
        if hasattr(obj, "tolist"):  # numpy array
            return obj.tolist()
        return super().default(obj)


def extract_data(html: str) -> dict:
    m = re.search(r"const D = (\{.*?\});", html, re.S)
    if not m:
        raise SystemExit("Could not locate embedded data object in dashboard HTML.")
    return json.loads(m.group(1))


def render(data: dict) -> str:
    """Render the publication-ready dashboard from a prepared data object.

    `data` must match the structure produced by the analysis pipeline
    (kpis, monthly_trend, segment_leakage_trend, risk_drivers,
    tier_breakdown, segment_summary, accounts, filters, meta).
    """
    payload = json.dumps(data, separators=(",", ":"), cls=_NumpySafe)
    return TEMPLATE.replace("__DATA__", payload)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Revenue Leakage Intelligence — Executive Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
@import url('https://cdn.jsdelivr.net/npm/@fontsource-variable/geist@5.2.6/index.min.css');
@import url('https://cdn.jsdelivr.net/npm/@fontsource-variable/geist-mono@5.2.6/index.min.css');

:root {
    --sans: "Geist Variable", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --mono: "Geist Mono Variable", ui-monospace, "SF Mono", Menlo, monospace;

    --bg:          #f6f7f9;
    --surface:     #ffffff;
    --surface-2:   #fbfbfc;
    --hover:       #f4f5f7;
    --border:      #e6e8ec;
    --border-strong:#d7dae0;

    --text:        #0b1320;
    --text-2:      #5b6573;
    --text-3:      #8b93a1;

    --accent:      #4f46e5;
    --accent-soft: rgba(79,70,229,0.10);
    --accent-line: rgba(79,70,229,0.22);

    --risk:        #d23f35;
    --risk-soft:   rgba(210,63,53,0.10);
    --pos:         #1f8a55;

    --ring:        rgba(79,70,229,0.30);
    --shadow:      0 1px 2px rgba(11,19,32,0.04), 0 8px 24px -12px rgba(11,19,32,0.10);
    --radius:      14px;
}

[data-theme="dark"] {
    --bg:          #0a0c10;
    --surface:     #121620;
    --surface-2:   #0e121a;
    --hover:       #1a1f2b;
    --border:      #222834;
    --border-strong:#2c3340;

    --text:        #f3f5f8;
    --text-2:      #98a2b3;
    --text-3:      #6b7280;

    --accent:      #837dff;
    --accent-soft: rgba(131,125,255,0.14);
    --accent-line: rgba(131,125,255,0.30);

    --risk:        #f0655c;
    --risk-soft:   rgba(240,101,92,0.14);
    --pos:         #3ec07b;

    --ring:        rgba(131,125,255,0.35);
    --shadow:      0 1px 2px rgba(0,0,0,0.4), 0 12px 32px -16px rgba(0,0,0,0.7);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

html { -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
body {
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    min-height: 100vh;
    font-feature-settings: "ss01", "cv01";
}
.tnum { font-variant-numeric: tabular-nums; }

/* ── Top bar ───────────────────────────────── */
.topbar {
    border-bottom: 1px solid var(--border);
    background: color-mix(in srgb, var(--surface) 80%, transparent);
    backdrop-filter: saturate(140%) blur(8px);
    position: sticky; top: 0; z-index: 40;
}
.topbar-inner {
    max-width: 1320px; margin: 0 auto;
    padding: 18px 32px;
    display: flex; align-items: center; justify-content: space-between; gap: 20px;
}
.brand { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.brand h1 {
    font-size: 17px; font-weight: 600; letter-spacing: -0.02em; color: var(--text);
}
.brand .tag {
    font-size: 11px; font-weight: 500; color: var(--text-3);
    text-transform: uppercase; letter-spacing: 0.08em;
}
.topbar-right { display: flex; align-items: center; gap: 14px; }
.period {
    font-family: var(--mono); font-size: 12px; color: var(--text-2);
    letter-spacing: -0.01em; white-space: nowrap;
}
.theme-toggle {
    width: 34px; height: 34px; border-radius: 9px;
    border: 1px solid var(--border); background: var(--surface);
    color: var(--text-2); cursor: pointer; display: grid; place-items: center;
    transition: color .15s, border-color .15s, background .15s;
}
.theme-toggle:hover { color: var(--text); border-color: var(--border-strong); background: var(--hover); }
.theme-toggle svg { width: 16px; height: 16px; }
.theme-toggle .moon { display: none; }
[data-theme="dark"] .theme-toggle .sun { display: none; }
[data-theme="dark"] .theme-toggle .moon { display: block; }

/* ── Layout ────────────────────────────────── */
.container { max-width: 1320px; margin: 0 auto; padding: 28px 32px 72px; }

.lede {
    display: flex; align-items: flex-start; gap: 14px;
    margin: 4px 0 26px;
}
.lede .mark { width: 3px; align-self: stretch; border-radius: 2px; background: var(--risk); flex: none; }
.lede p { font-size: 15px; color: var(--text-2); max-width: 760px; letter-spacing: -0.01em; }
.lede strong { color: var(--text); font-weight: 600; }
.lede .num { font-family: var(--mono); color: var(--risk); font-weight: 600; font-variant-numeric: tabular-nums; }

.section-head {
    display: flex; align-items: baseline; gap: 10px;
    margin: 38px 0 14px;
}
.section-head .idx {
    font-family: var(--mono); font-size: 11px; color: var(--text-3);
    border: 1px solid var(--border); border-radius: 5px; padding: 1px 6px;
}
.section-head h2 { font-size: 13px; font-weight: 600; letter-spacing: -0.01em; color: var(--text); }
.section-head .hint { font-size: 12px; color: var(--text-3); }
.section-head:first-of-type { margin-top: 6px; }

/* ── KPI cards ─────────────────────────────── */
.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.kpi {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 18px 18px 16px;
    display: flex; flex-direction: column; min-height: 132px;
    transition: border-color .15s, box-shadow .15s, transform .15s;
}
.kpi:hover { border-color: var(--border-strong); box-shadow: var(--shadow); }
.kpi .label {
    font-size: 11px; font-weight: 500; color: var(--text-2);
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: auto;
}
.kpi .value {
    font-family: var(--mono); font-weight: 500;
    font-size: 38px; line-height: 1; letter-spacing: -0.03em;
    color: var(--text); font-variant-numeric: tabular-nums;
    margin-top: 14px;
}
.kpi .value.risk { color: var(--risk); }
.kpi .meta { display: flex; align-items: center; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.kpi .sub { font-size: 12px; color: var(--text-3); letter-spacing: -0.01em; }
.delta {
    display: inline-flex; align-items: center; gap: 3px;
    font-family: var(--mono); font-size: 11.5px; font-weight: 500;
    padding: 2px 7px; border-radius: 6px; letter-spacing: -0.02em;
}
.delta.bad  { color: var(--risk); background: var(--risk-soft); }
.delta.good { color: var(--pos);  background: color-mix(in srgb, var(--pos) 12%, transparent); }
.delta svg { width: 11px; height: 11px; }

/* ── Panels ────────────────────────────────── */
.grid { display: grid; gap: 14px; }
.grid.c2 { grid-template-columns: 1fr 1fr; }
.grid.c12-5 { grid-template-columns: 7fr 5fr; }
.grid.c5-7 { grid-template-columns: 5fr 7fr; }

.panel {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px 22px;
    min-width: 0;
}
.panel-head { margin-bottom: 18px; }
.panel-head h3 { font-size: 13.5px; font-weight: 600; letter-spacing: -0.01em; color: var(--text); }
.panel-head p { font-size: 12px; color: var(--text-3); margin-top: 3px; letter-spacing: -0.01em; }
.panel-head .row { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.panel-head .stat { font-family: var(--mono); font-size: 12px; color: var(--text-2); font-variant-numeric: tabular-nums; }
.chart-wrap { position: relative; width: 100%; }

.legend { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 16px; }
.legend span { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: var(--text-2); }
.legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.legend i.dash { height: 0; border-top: 2px dashed var(--risk); width: 14px; border-radius: 0; }

/* ── Heatmap ───────────────────────────────── */
.heat { width: 100%; border-collapse: separate; border-spacing: 4px; table-layout: fixed; }
.heat col.segcol { width: 28%; }
.heat th {
    font-size: 10px; font-weight: 500; color: var(--text-3);
    text-transform: uppercase; letter-spacing: 0.04em; text-align: center; padding: 0 0 6px;
    overflow-wrap: break-word; line-height: 1.25;
}
.heat th:first-child { text-align: left; }
.heat td.seg {
    font-size: 12.5px; font-weight: 500; color: var(--text); white-space: nowrap;
    padding-right: 10px; letter-spacing: -0.01em;
}
.heat td.cell {
    font-family: var(--mono); font-variant-numeric: tabular-nums;
    text-align: center; padding: 13px 8px; border-radius: 8px;
    font-size: 13px; font-weight: 500; position: relative;
}
.heat-scale { display: flex; align-items: center; gap: 8px; margin-top: 16px; font-size: 11px; color: var(--text-3); }
.heat-scale .ramp { height: 7px; width: 120px; border-radius: 4px;
    background: linear-gradient(90deg, var(--accent-soft), var(--accent)); }

/* ── Filter bar + table ────────────────────── */
.toolbar {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    margin-bottom: 14px;
}
.field { display: inline-flex; flex-direction: column; gap: 5px; }
.field label {
    font-size: 10px; font-weight: 500; color: var(--text-3);
    text-transform: uppercase; letter-spacing: 0.06em; padding-left: 2px;
}
.field select {
    appearance: none; -webkit-appearance: none;
    font-family: var(--sans); font-size: 13px; color: var(--text);
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 9px; padding: 8px 32px 8px 12px; cursor: pointer;
    transition: border-color .15s, box-shadow .15s; min-width: 150px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238b93a1' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 11px center;
}
.field select:hover { border-color: var(--border-strong); }
.field select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--ring); }
.toolbar .spacer { flex: 1; }
.result {
    font-family: var(--mono); font-size: 12px; color: var(--text-2);
    font-variant-numeric: tabular-nums; align-self: flex-end; padding-bottom: 9px;
}
.result b { color: var(--text); font-weight: 600; }
.result .at-risk { color: var(--risk); }
.reset {
    align-self: flex-end; font-family: var(--sans); font-size: 12px; color: var(--text-2);
    background: transparent; border: 1px solid var(--border); border-radius: 9px;
    padding: 8px 14px; cursor: pointer; transition: all .15s; margin-bottom: 0;
}
.reset:hover { color: var(--text); border-color: var(--border-strong); background: var(--hover); }

.table-wrap { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: var(--surface); }
.table-scroll { max-height: 540px; overflow: auto; }
table.accts { width: 100%; border-collapse: collapse; font-size: 12.5px; }
table.accts thead th {
    position: sticky; top: 0; z-index: 2;
    background: var(--surface-2); color: var(--text-3);
    font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; padding: 11px 14px; white-space: nowrap;
    border-bottom: 1px solid var(--border); cursor: pointer; user-select: none;
}
table.accts thead th.num { text-align: right; }
table.accts thead th:hover { color: var(--text); }
table.accts thead th .arr { opacity: 0; margin-left: 4px; font-size: 9px; }
table.accts thead th.sorted .arr { opacity: 1; color: var(--accent); }
table.accts tbody td {
    padding: 11px 14px; border-bottom: 1px solid var(--border);
    white-space: nowrap; color: var(--text-2);
}
table.accts tbody tr:last-child td { border-bottom: 0; }
table.accts tbody tr { transition: background .12s; }
table.accts tbody tr:hover { background: var(--hover); }
td.id { font-family: var(--mono); color: var(--text); font-weight: 500; letter-spacing: -0.02em; }
td.co { color: var(--text); }
td.num { font-family: var(--mono); text-align: right; font-variant-numeric: tabular-nums; color: var(--text); letter-spacing: -0.01em; }
td.num.dim { color: var(--text-3); }

.scorecell { display: flex; align-items: center; justify-content: flex-end; gap: 9px; }
.scorebar { width: 46px; height: 5px; border-radius: 3px; background: var(--border); overflow: hidden; }
.scorebar i { display: block; height: 100%; border-radius: 3px; }
.scoreval { font-family: var(--mono); width: 30px; text-align: right; color: var(--text); }

.badge {
    display: inline-block; padding: 2px 9px; border-radius: 20px;
    font-size: 10px; font-weight: 600; letter-spacing: 0.04em;
    font-family: var(--sans); text-transform: uppercase;
    border: 1px solid transparent;
}
.badge.critical { color: var(--risk); background: var(--risk-soft); border-color: color-mix(in srgb, var(--risk) 28%, transparent); }
.badge.high     { color: var(--risk); background: var(--risk-soft); }
.badge.medium   { color: var(--text-2); background: var(--hover); border-color: var(--border); }
.badge.low      { color: var(--text-3); background: transparent; border-color: var(--border); }

/* ── Footer ────────────────────────────────── */
.foot {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    flex-wrap: wrap; margin-top: 44px; padding-top: 20px;
    border-top: 1px solid var(--border);
    font-size: 11.5px; color: var(--text-3); letter-spacing: -0.01em;
}
.foot .mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }

/* ── Responsive ────────────────────────────── */
@media (max-width: 1080px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    .grid.c2, .grid.c12-5, .grid.c5-7 { grid-template-columns: 1fr; }
}
@media (max-width: 680px) {
    .topbar-inner, .container { padding-left: 18px; padding-right: 18px; }
    .kpi-grid { grid-template-columns: 1fr; }
    .period { display: none; }
    .kpi .value { font-size: 34px; }
    .result { width: 100%; }
}
</style>
</head>
<body>

<div class="topbar">
    <div class="topbar-inner">
        <div class="brand">
            <h1>Revenue Leakage Intelligence</h1>
            <span class="tag">Executive Dashboard</span>
        </div>
        <div class="topbar-right">
            <span class="period" id="period"></span>
            <button class="theme-toggle" id="themeToggle" type="button" aria-label="Toggle theme">
                <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
                <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
            </button>
        </div>
    </div>
</div>

<div class="container">

    <div class="lede">
        <span class="mark"></span>
        <p id="lede"></p>
    </div>

    <!-- 01 · Overview -->
    <div class="section-head" style="margin-top:6px">
        <span class="idx">01</span><h2>Portfolio at a glance</h2>
        <span class="hint">trailing 24 months · full book of business</span>
    </div>
    <div class="kpi-grid">
        <div class="kpi">
            <div class="label">Annual Recurring Rev.</div>
            <div class="value tnum" id="kArr"></div>
            <div class="meta"><span class="sub" id="kArrSub"></span></div>
        </div>
        <div class="kpi">
            <div class="label">Revenue Leakage</div>
            <div class="value risk tnum" id="kLeak"></div>
            <div class="meta"><span class="delta bad" id="kLeakDelta"></span><span class="sub" id="kLeakSub"></span></div>
        </div>
        <div class="kpi">
            <div class="label">Revenue at Risk</div>
            <div class="value tnum" id="kRisk"></div>
            <div class="meta"><span class="sub" id="kRiskSub"></span></div>
        </div>
        <div class="kpi">
            <div class="label">Collection Rate</div>
            <div class="value tnum" id="kColl"></div>
            <div class="meta"><span class="delta bad" id="kCollDelta"></span><span class="sub">vs prior yr</span></div>
        </div>
        <div class="kpi">
            <div class="label">High-Risk Accounts</div>
            <div class="value tnum" id="kHigh"></div>
            <div class="meta"><span class="sub" id="kHighSub"></span></div>
        </div>
    </div>

    <!-- 02 · Trend -->
    <div class="section-head">
        <span class="idx">02</span><h2>The gap is structural, not seasonal</h2>
        <span class="hint">contracted vs collected, monthly</span>
    </div>
    <div class="grid c5-7">
        <div class="panel">
            <div class="panel-head">
                <h3>Leakage by segment</h3>
                <p>Monthly contracted-minus-collected gap, stacked by tier</p>
            </div>
            <div class="chart-wrap" style="height:300px"><canvas id="cSeg"></canvas></div>
        </div>
        <div class="panel">
            <div class="panel-head row">
                <div>
                    <h3>Contracted vs collected revenue</h3>
                    <p>The shaded band is revenue contracted but never collected</p>
                </div>
            </div>
            <div class="chart-wrap" style="height:300px"><canvas id="cRev"></canvas></div>
            <div class="legend">
                <span><i style="background:var(--text-3)"></i>Contracted</span>
                <span><i style="background:var(--accent)"></i>Collected</span>
                <span><i style="background:var(--risk-soft);border:1px solid var(--risk)"></i>Leakage gap</span>
            </div>
        </div>
    </div>

    <!-- 03 · Risk -->
    <div class="section-head">
        <span class="idx">03</span><h2>Where the risk concentrates</h2>
        <span class="hint">drivers, tiers and segment exposure</span>
    </div>
    <div class="grid c12-5">
        <div class="panel">
            <div class="panel-head">
                <h3>Risk drivers by segment</h3>
                <p>Average contribution of each leakage channel to the risk score (0–100)</p>
            </div>
            <table class="heat" id="heat"></table>
            <div class="heat-scale"><span>lower</span><span class="ramp"></span><span>higher exposure</span></div>
        </div>
        <div class="panel">
            <div class="panel-head row">
                <div><h3>Revenue at risk by tier</h3><p>Share of at-risk dollars</p></div>
                <span class="stat" id="tierStat"></span>
            </div>
            <div class="chart-wrap" style="height:230px"><canvas id="cTier"></canvas></div>
            <div class="legend" id="tierLegend"></div>
        </div>
    </div>

    <div class="grid c2" style="margin-top:14px">
        <div class="panel">
            <div class="panel-head">
                <h3>Segment exposure</h3>
                <p>Portfolio ARR against revenue at risk, by segment</p>
            </div>
            <div class="chart-wrap" style="height:240px"><canvas id="cSegBar"></canvas></div>
            <div class="legend">
                <span><i style="background:var(--accent)"></i>Portfolio ARR</span>
                <span><i style="background:var(--risk)"></i>Revenue at risk</span>
            </div>
        </div>
        <div class="panel">
            <div class="panel-head">
                <h3>Risk intensity vs scale</h3>
                <p>Risk-weighted exposure per dollar of ARR — higher means leakier relative to size</p>
            </div>
            <div class="chart-wrap" style="height:240px"><canvas id="cIntensity"></canvas></div>
        </div>
    </div>

    <!-- 04 · Action -->
    <div class="section-head">
        <span class="idx">04</span><h2>Prioritised intervention list</h2>
        <span class="hint">act top-down by composite risk score</span>
    </div>
    <div class="toolbar">
        <div class="field"><label>Segment</label><select id="fSeg"></select></div>
        <div class="field"><label>Region</label><select id="fReg"></select></div>
        <div class="field"><label>Risk tier</label><select id="fTier"></select></div>
        <button class="reset" id="reset" type="button">Clear</button>
        <span class="spacer"></span>
        <span class="result" id="result"></span>
    </div>
    <div class="table-wrap">
        <div class="table-scroll">
            <table class="accts">
                <thead><tr>
                    <th data-col="id">Account<span class="arr">▼</span></th>
                    <th data-col="segment">Segment<span class="arr">▼</span></th>
                    <th data-col="region">Region<span class="arr">▼</span></th>
                    <th data-col="acv" data-type="num" class="num">ACV<span class="arr">▼</span></th>
                    <th data-col="score" data-type="num" class="num">Risk score<span class="arr">▼</span></th>
                    <th data-col="tier">Tier<span class="arr">▼</span></th>
                    <th data-col="at_risk" data-type="num" class="num">At risk<span class="arr">▼</span></th>
                    <th data-col="churn" data-type="num" class="num">Churn<span class="arr">▼</span></th>
                    <th data-col="payment" data-type="num" class="num">Payment<span class="arr">▼</span></th>
                    <th data-col="collection" data-type="num" class="num">Coll.<span class="arr">▼</span></th>
                </tr></thead>
                <tbody id="tbody"></tbody>
            </table>
        </div>
    </div>

    <div class="foot">
        <span>Revenue Leakage Intelligence — composite risk model across churn, deterioration, discount, payment &amp; engagement signals.</span>
        <span class="mono" id="footMeta"></span>
    </div>
</div>

<script>
const D = __DATA__;

/* ── formatting ─────────────────────────────── */
const f$ = v => {
    const a = Math.abs(v);
    if (a >= 1e6) return '$' + (v/1e6).toFixed(a >= 1e7 ? 1 : 2) + 'M';
    if (a >= 1e3) return '$' + Math.round(v/1e3) + 'K';
    return '$' + Math.round(v).toLocaleString();
};
const f$full = v => '$' + Math.round(v).toLocaleString();
const pct = v => (v > 0 && v < 1) ? '<1%' : v.toFixed(0) + '%';
const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/* ── palette (theme-aware) ──────────────────── */
let C = {};
function readPalette() {
    C = {
        accent:  cssVar('--accent'),
        risk:    cssVar('--risk'),
        text:    cssVar('--text-2'),
        text3:   cssVar('--text-3'),
        grid:    cssVar('--border'),
        surface: cssVar('--surface'),
        riskFill: getComputedStyle(document.documentElement).getPropertyValue('--risk').trim(),
    };
    // tonal indigo ramp for stacked segments (dark→light)
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    C.ramp = dark
        ? ['#837dff', '#5d57c9', '#3b3a73']
        : ['#4f46e5', '#8884e8', '#c3c0f2'];
    C.tierRamp = dark
        ? ['#f0655c', '#c4564f', '#5a6473', '#3a4150']
        : ['#d23f35', '#e08a84', '#9aa3b2', '#cdd2da'];
}
const alpha = (hex, a) => {
    const h = hex.replace('#','');
    const n = parseInt(h.length === 3 ? h.split('').map(c=>c+c).join('') : h, 16);
    return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${a})`;
};

function chartBase() {
    return {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: cssVar('--surface'),
                titleColor: cssVar('--text'), bodyColor: cssVar('--text-2'),
                borderColor: cssVar('--border-strong'), borderWidth: 1,
                padding: 11, cornerRadius: 9, boxPadding: 5, usePointStyle: true,
                titleFont: { family: cssVar('--sans'), size: 12, weight: '600' },
                bodyFont:  { family: cssVar('--mono'), size: 12 },
            }
        },
        scales: {
            x: { grid: { display: false }, border: { color: C.grid },
                 ticks: { color: C.text3, font: { family: cssVar('--sans'), size: 11 }, maxRotation: 0, autoSkipPadding: 16 } },
            y: { grid: { color: C.grid, drawTicks: false }, border: { display: false },
                 ticks: { color: C.text3, font: { family: cssVar('--mono'), size: 11 }, padding: 8 } },
        }
    };
}

/* ── charts ─────────────────────────────────── */
let ch = {};
function destroyAll() { Object.values(ch).forEach(c => c && c.destroy()); ch = {}; }

function revChart() {
    const m = D.monthly_trend, lbl = m.map(d => d.month.slice(2));
    ch.rev = new Chart(document.getElementById('cRev'), {
        type: 'line',
        data: { labels: lbl, datasets: [
            { label: 'Contracted', data: m.map(d=>d.contracted), borderColor: C.text3,
              borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 4, tension: 0.35,
              fill: '+1', backgroundColor: alpha(C.risk, 0.13) },
            { label: 'Collected', data: m.map(d=>d.collected), borderColor: C.accent,
              borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 4, tension: 0.35, fill: false },
        ]},
        options: { ...chartBase(), plugins: { ...chartBase().plugins, tooltip: { ...chartBase().plugins.tooltip,
            callbacks: { label: c => `  ${c.dataset.label}: ${f$full(c.raw)}`,
                afterBody: items => { const c=items[0].chart.data.datasets; const i=items[0].dataIndex;
                    return `  Gap: ${f$full(c[0].data[i]-c[1].data[i])}`; } } } },
            scales: { ...chartBase().scales, y: { ...chartBase().scales.y, ticks: { ...chartBase().scales.y.ticks, callback: f$ } } } }
    });
}

function segChart() {
    const s = D.segment_leakage_trend, segs = Object.keys(s);
    const lbl = s[segs[0]].months.map(x => x.slice(2));
    ch.seg = new Chart(document.getElementById('cSeg'), {
        type: 'line',
        data: { labels: lbl, datasets: segs.map((seg,i)=>({
            label: seg, data: s[seg].gaps, borderColor: C.ramp[i], backgroundColor: alpha(C.ramp[i], 0.55),
            borderWidth: 1, pointRadius: 0, pointHoverRadius: 3, tension: 0.3, fill: true,
        })) },
        options: { ...chartBase(), plugins: { ...chartBase().plugins,
            legend: { display: true, position: 'bottom', labels: { color: C.text, usePointStyle: true, pointStyle:'circle',
                boxWidth: 7, boxHeight: 7, padding: 16, font: { family: cssVar('--sans'), size: 12 } } },
            tooltip: { ...chartBase().plugins.tooltip, callbacks: { label: c => `  ${c.dataset.label}: ${f$full(c.raw)}` } } },
            scales: { x: { ...chartBase().scales.x, stacked: true },
                      y: { ...chartBase().scales.y, stacked: true, ticks: { ...chartBase().scales.y.ticks, callback: f$ } } } }
    });
}

function tierChart() {
    const t = D.tier_breakdown.filter(x => x.total_risk > 0);
    const total = t.reduce((s,x)=>s+x.total_risk,0);
    ch.tier = new Chart(document.getElementById('cTier'), {
        type: 'doughnut',
        data: { labels: t.map(x=>x.tier), datasets: [{ data: t.map(x=>x.total_risk),
            backgroundColor: t.map((_,i)=>C.tierRamp[i]), borderColor: cssVar('--surface'),
            borderWidth: 3, hoverOffset: 6 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '68%',
            plugins: { legend: { display: false }, tooltip: { ...chartBase().plugins.tooltip,
                callbacks: { label: c => { const x=t[c.dataIndex];
                    return `  ${f$full(x.total_risk)} · ${x.count} acct${x.count>1?'s':''} · ${pct(x.total_risk/total*100)}`; } } } } }
    });
    document.getElementById('tierStat').textContent = f$(total) + ' at risk';
    document.getElementById('tierLegend').innerHTML = t.map((x,i)=>
        `<span><i style="background:${C.tierRamp[i]}"></i>${x.tier} · ${pct(x.total_risk/total*100)}</span>`).join('');
}

function segBarChart() {
    const s = D.segment_summary;
    ch.segbar = new Chart(document.getElementById('cSegBar'), {
        type: 'bar',
        data: { labels: s.map(x=>x.segment), datasets: [
            { label: 'Portfolio ARR', data: s.map(x=>x.total_arr), backgroundColor: alpha(C.accent,0.85),
              borderRadius: 5, maxBarThickness: 34 },
            { label: 'Revenue at risk', data: s.map(x=>x.total_risk), backgroundColor: C.risk,
              borderRadius: 5, maxBarThickness: 34 },
        ]},
        options: { ...chartBase(), plugins: { ...chartBase().plugins, tooltip: { ...chartBase().plugins.tooltip,
            callbacks: { label: c => `  ${c.dataset.label}: ${f$full(c.raw)}` } } },
            scales: { ...chartBase().scales, y: { ...chartBase().scales.y, ticks: { ...chartBase().scales.y.ticks, callback: f$ } } } }
    });
}

function intensityChart() {
    const s = [...D.segment_summary].sort((a,b)=>b.risk_intensity-a.risk_intensity);
    ch.intensity = new Chart(document.getElementById('cIntensity'), {
        type: 'bar',
        data: { labels: s.map(x=>x.segment), datasets: [{ data: s.map(x=>x.risk_intensity),
            backgroundColor: s.map(x=> x.risk_intensity >= 1 ? C.risk : alpha(C.accent,0.85)),
            borderRadius: 5, maxBarThickness: 30 }] },
        options: { ...chartBase(), indexAxis: 'y',
            plugins: { ...chartBase().plugins, tooltip: { ...chartBase().plugins.tooltip,
                callbacks: { label: c => `  Risk intensity: ${c.raw.toFixed(2)}×  ·  ${f$full(s[c.dataIndex].total_risk)} at risk` } } },
            scales: { x: { ...chartBase().scales.x, grid: { color: C.grid, drawTicks:false },
                ticks: { ...chartBase().scales.x.ticks, font:{family:cssVar('--mono'),size:11}, callback: v => v.toFixed(1)+'×' } },
                y: { ...chartBase().scales.y, grid: { display:false },
                ticks: { ...chartBase().scales.y.ticks, font:{family:cssVar('--sans'),size:12} } } } }
    });
}

/* ── heatmap ────────────────────────────────── */
function heatmap() {
    const cols = [['churn','Churn'],['deterioration','Deterio&shy;ration'],['discount','Dis&shy;count'],['payment','Payment']];
    const rows = D.risk_drivers;
    let max = 0; rows.forEach(r => cols.forEach(([k]) => max = Math.max(max, r[k])));
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    let html = '<colgroup><col class="segcol">' + cols.map(()=>'<col>').join('') + '</colgroup>'
             + '<thead><tr><th>Segment</th>' + cols.map(c=>`<th>${c[1]}</th>`).join('') + '</tr></thead><tbody>';
    rows.forEach(r => {
        html += `<tr><td class="seg">${r.segment}</td>` + cols.map(([k]) => {
            const v = r[k], t = v / max;
            const bg = alpha(C.accent, 0.06 + t * 0.84);
            const fg = t > 0.5 ? (dark ? '#0b0d12' : '#ffffff') : cssVar('--text');
            return `<td class="cell" style="background:${bg};color:${fg}">${v.toFixed(0)}</td>`;
        }).join('') + '</tr>';
    });
    document.getElementById('heat').innerHTML = html + '</tbody>';
}

/* ── KPIs + lede ────────────────────────────── */
function fillKPIs() {
    const k = D.kpis;
    document.getElementById('kArr').textContent = f$(k.total_arr);
    document.getElementById('kArrSub').textContent = k.total_customers.toLocaleString() + ' active accounts';
    document.getElementById('kLeak').textContent = f$(k.total_leakage);
    document.getElementById('kLeakSub').textContent = k.leakage_rate + '% of contracted';
    document.getElementById('kLeakDelta').innerHTML = arrow(true) + Math.abs(k.leakage_trend).toFixed(1) + 'pp';
    document.getElementById('kRisk').textContent = f$(k.total_at_risk);
    document.getElementById('kRiskSub').textContent = k.at_risk_pct + '% of ARR';
    document.getElementById('kColl').textContent = k.avg_collection + '%';
    document.getElementById('kCollDelta').innerHTML = arrow(false) + Math.abs(k.coll_trend).toFixed(1) + 'pp';
    document.getElementById('kHigh').textContent = k.high_risk_count;
    document.getElementById('kHighSub').textContent = 'critical + high tier';

    document.getElementById('lede').innerHTML =
        `<strong>${f$(k.total_leakage)} is leaking from the book every year</strong> — ${k.leakage_rate}% of contracted ` +
        `revenue never converts to cash. A further <span class="num">${f$(k.total_at_risk)}</span> sits at elevated risk across ` +
        `${k.high_risk_count} accounts, while collection has slipped <span class="num">${Math.abs(k.coll_trend)}pp</span> year on year.`;

    const mt = D.meta;
    document.getElementById('period').textContent = mt.period_start + ' → ' + mt.period_end;
    document.getElementById('footMeta').textContent = 'Generated ' + mt.generated_at + ' · ' + mt.total_months + ' months';
}
const arrow = up => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">${up?'<path d="M12 19V5M5 12l7-7 7 7"/>':'<path d="M12 5v14M5 12l7 7 7-7"/>'}</svg>`;

/* ── table + filters ────────────────────────── */
let sortCol = 'score', sortDir = -1;
const tierClass = t => t.toLowerCase();

function populateFilters() {
    const fill = (id, arr, lbl) => {
        const el = document.getElementById(id);
        el.innerHTML = `<option value="">All ${lbl}</option>` + arr.map(v=>`<option>${v}</option>`).join('');
    };
    fill('fSeg', D.filters.segments, 'segments');
    fill('fReg', D.filters.regions, 'regions');
    fill('fTier', D.filters.tiers, 'tiers');
}

function filtered() {
    const s = document.getElementById('fSeg').value, r = document.getElementById('fReg').value, t = document.getElementById('fTier').value;
    return D.accounts.filter(a => (!s||a.segment===s) && (!r||a.region===r) && (!t||a.tier===t));
}

function scoreColor(v) { return v >= 45 ? cssVar('--risk') : v >= 30 ? cssVar('--accent') : cssVar('--text-3'); }

function renderTable() {
    const rows = filtered().sort((a,b)=>{
        let x=a[sortCol], y=b[sortCol];
        return typeof x === 'string' ? sortDir*x.localeCompare(y) : sortDir*(x-y);
    });
    document.getElementById('tbody').innerHTML = rows.map(a=>`
        <tr>
            <td class="id">${a.id}</td>
            <td class="co">${a.segment}</td>
            <td>${a.region}</td>
            <td class="num">${f$(a.acv)}</td>
            <td class="num"><div class="scorecell">
                <span class="scorebar"><i style="width:${Math.min(a.score,100)}%;background:${scoreColor(a.score)}"></i></span>
                <span class="scoreval">${a.score.toFixed(0)}</span></div></td>
            <td><span class="badge ${tierClass(a.tier)}">${a.tier}</span></td>
            <td class="num" style="color:var(--risk)">${f$(a.at_risk)}</td>
            <td class="num dim">${a.churn.toFixed(0)}</td>
            <td class="num dim">${a.payment.toFixed(0)}</td>
            <td class="num">${a.collection.toFixed(0)}%</td>
        </tr>`).join('');

    const totalRisk = rows.reduce((s,a)=>s+a.at_risk,0);
    document.getElementById('result').innerHTML =
        `<b>${rows.length}</b> of ${D.accounts.length} accounts · <span class="at-risk">${f$(totalRisk)}</span> at risk`;

    document.querySelectorAll('thead th').forEach(th=>{
        const on = th.dataset.col === sortCol;
        th.classList.toggle('sorted', on);
        const a = th.querySelector('.arr'); if (a) a.textContent = on ? (sortDir===1?'▲':'▼') : '▼';
    });
}

document.querySelectorAll('thead th').forEach(th=>{
    th.addEventListener('click', ()=>{
        const c = th.dataset.col; if (!c) return;
        if (sortCol===c) sortDir*=-1; else { sortCol=c; sortDir = th.dataset.type==='num' ? -1 : 1; }
        renderTable();
    });
});
['fSeg','fReg','fTier'].forEach(id=>document.getElementById(id).addEventListener('change', renderTable));
document.getElementById('reset').addEventListener('click', ()=>{
    ['fSeg','fReg','fTier'].forEach(id=>document.getElementById(id).value='');
    renderTable();
});

/* ── theme ──────────────────────────────────── */
function renderCharts() { readPalette(); destroyAll(); revChart(); segChart(); tierChart(); segBarChart(); intensityChart(); heatmap(); }
function setTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('rliTheme', t);
    renderCharts();
}
document.getElementById('themeToggle').addEventListener('click', ()=>{
    setTheme(document.documentElement.getAttribute('data-theme')==='dark' ? 'light' : 'dark');
});

/* ── init ───────────────────────────────────── */
(function init(){
    const saved = localStorage.getItem('rliTheme');
    const theme = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    readPalette();
    fillKPIs();
    populateFilters();
    renderTable();
    renderCharts();
})();
</script>
</body>
</html>
"""


def main() -> None:
    html = DASH.read_text(encoding="utf-8")
    data = extract_data(html)
    out = render(data)
    DASH.write_text(out, encoding="utf-8")
    print(f"Wrote redesigned dashboard → {DASH.relative_to(ROOT)} ({len(out):,} bytes)")


if __name__ == "__main__":
    main()
