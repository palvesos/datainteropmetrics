# Data Interoperability KPI Dashboard — Design Spec

**Date:** 2026-06-15  
**Status:** Approved

---

## Overview

A self-contained HTML report for monitoring Data Interoperability adoption KPIs. Data is fetched from Snowflake via Claude Code (avoiding direct auth wiring), stored locally as Parquet files, and rendered into a dark-themed, tabbed HTML dashboard using Plotly.js and Jinja2.

---

## Goals

- Monitor adoption and usage of Data Interoperability across OutSystems customers
- Refresh on demand via a single `/refresh` Claude Code slash command
- Output a single `report.html` file that opens directly in a browser (no server)
- All data derived from 6 canonical Snowflake queries; no hardcoded values in the template

---

## Project Structure

```
dataInterOpMetrics/
├── .claude/
│   ├── settings.local.json        (existing)
│   └── commands/
│       └── refresh.md             ← /refresh slash command definition
├── queries/                       ← one .sql file per KPI query
│   ├── q1_adoption_trend.sql
│   ├── q2_by_product_family.sql
│   ├── q3_by_arch_type.sql
│   ├── q4_executions.sql
│   ├── q5_ao_usage.sql
│   └── q6_population.sql
├── data/                          ← Parquet output (gitignored)
│   └── *.parquet
├── templates/
│   └── report.html.j2             ← Jinja2 HTML template
├── render.py                      ← Parquet → HTML renderer
├── report.html                    ← generated output (gitignored)
├── requirements.txt
├── .gitignore
└── docs/
    └── superpowers/specs/
        └── 2026-06-15-data-interop-kpi-dashboard-design.md
```

---

## Data Sources

Six queries against `CANONICAL` database on Snowflake account `AX81353-OUTSYSTEMS` (connection name: `os`):

| File | Table | Grain |
|---|---|---|
| `q1_adoption_trend.sql` | `MONTHLYCOMPANYPRODUCTEDITIONCATEGORY` | Monthly, last 12 months |
| `q2_by_product_family.sql` | `MONTHLYCOMPANYPRODUCTEDITIONCATEGORY` | Current month, by product family |
| `q3_by_arch_type.sql` | `MONTHLYCOMPANYINFRAPRODUCTEDITIONCATEGORY` | Current month, by arch type |
| `q4_executions.sql` | `PLATFORMUTILIZATIONDAILYINFRASTRUCTUREAGG` | Monthly, last 7 months |
| `q5_ao_usage.sql` | `PLATFORMUTILIZATIONMONTHLYINFRASTRUCTUREAGG_TOTAL` | Monthly, last 7 months |
| `q6_population.sql` | `CUSTOMERUNIFIEDINFO` | All-time snapshot |

---

## `/refresh` Command

Defined in `.claude/commands/refresh.md`. When invoked, Claude Code will:

1. Read each `.sql` file from `queries/`
2. Execute each query: `uvx --python 3.13 --from snowflake-cli snow sql --query "..." --format json --connection os`
3. Parse JSON results and save each to `data/<name>.parquet` via pandas + pyarrow
4. Run `python render.py`
5. Print a completion summary: row counts per file, timestamp, path to `report.html`

---

## `render.py`

Pure Python — no Snowflake dependency. Responsibilities:

- Read all 6 Parquet files with `pandas`
- Compute derived metrics:
  - Current-month KPIs (adoption %, active customers, prod executions, prod AO last week)
  - MoM deltas for each KPI card
  - SKU gap: customers where `IS_INTEROPERABILITY=true` but `HAS_SKU_INTEROPERABILITY=false`
- Serialise chart datasets as JSON strings
- Render `templates/report.html.j2` via Jinja2 → write `report.html`

---

## `templates/report.html.j2`

Self-contained HTML file. Key properties:

- **Theme:** Dark (navy/slate background, colored metric accents — green, blue, amber, purple)
- **Charts:** Plotly.js loaded from CDN — requires internet connection to open
- **Tabs:** 4 tabs implemented with plain JS (no framework)
- **Data injection:** All chart data passed as `{{ variable | tojson }}` from `render.py`

### Tab: Overview
- 4 KPI cards: Adoption Rate (%), Active Customers, Prod Executions (last full month), Prod AO Last Week
- Each card shows MoM delta (absolute + direction indicator)
- Adoption trend sparkline (12 months, line chart)
- Last-updated timestamp + data source label

### Tab: Adoption
- Line chart: interop customer count and adoption % over 12 months (dual Y-axis)
- Donut chart: all-time population split (interop w/ SKU / interop w/o SKU / non-interop)
- Data table: last 12 monthly rows

### Tab: Usage
- Grouped bar chart: prod / dev / nonprod executions by month (last 7 months)
- Line chart: prod AO and dev AO last-week values by month (last 7 months)
- Active infra count per month (shown as annotation or small table)

### Tab: Segments
- Horizontal bar chart: interop active count by product family (Q2)
- Horizontal bar chart: interop companies by arch type × product family (Q3)
- SKU gap callout: count of customers using interop without the SKU entitlement

---

## `requirements.txt`

```
pandas
pyarrow
jinja2
```

---

## `.gitignore`

```
data/
report.html
.superpowers/
__pycache__/
*.pyc
```

---

## Git

Repository initialised at project root. Initial commit includes: spec, queries, `.gitignore`, `requirements.txt`, `render.py`, and `templates/report.html.j2`. Generated files (`data/`, `report.html`) are never committed.

---

## Out of Scope

- Scheduled / automated refresh (no cron or CI)
- Offline-capable HTML (Plotly CDN required)
- Historical snapshots or diff-over-time across report runs
- Any write operations to Snowflake
