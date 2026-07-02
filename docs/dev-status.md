# Development Status

**Last updated:** 2026-07-02  
**Current HEAD:** `feature/dashboard-v2` (post-Task 15; not yet merged to `main`)  
**Branch:** feature/dashboard-v2

---

## What's Been Built

The Data Interoperability KPI monitoring dashboard is fully implemented. Data is fetched from Snowflake via the `/refresh` Claude Code slash command, stored as Parquet files, and rendered into a self-contained dark-themed HTML report using Jinja2 and Plotly.js.

**Dashboard v2** (branch `feature/dashboard-v2`) enlarges the report with Data Fabric connector telemetry, deployment-option segmentation, targeting lists, a hardened population count, and maintained data-context docs. The pipeline now runs **11 queries → 11 Parquet files** and the report has **6 tabs**.

### Completed Tasks

| # | Task | Commit | Status |
|---|---|---|---|
| 1 | Bootstrap (`.gitignore`, `requirements.txt`, `data/`) | `8e74b85` | ✅ |
| 2 | SQL query files (`queries/q*.sql`) | `199038d` | ✅ |
| 3 | `render.py` skeleton + all 17 tests | `359992c` | ✅ |
| 4 | `load_data()` implementation | `4acebb7` | ✅ |
| 5 | `compute_metrics()` + 6 `_chart_*` helpers | `3826ba6` | ✅ |
| — | Code quality fixes (imports, boolean ops, barmode, time-coupled test) | `ad7142a` | ✅ |
| 6 | Jinja2 HTML template (`templates/report.html.j2`) | `1230be7` | ✅ |
| 7 | `render()` implementation | `8c7db69` | ✅ |
| — | Anchor Jinja2 template loader to `render.py`'s directory | `da8ee96` | ✅ |
| 8 | `/refresh` slash command | `f49e3e0` | ✅ |
| — | Harden `/refresh`: `--filename`, tempfile capture, guarded empty results | `43cbf85` | ✅ |

### Completed Tasks — Dashboard v2 (`feature/dashboard-v2`)

| # | Task | Commit | Status |
|---|---|---|---|
| 1 | Maintained data-context docs (`docs/data-context/{README,tables,patterns}.md`) | `03c9138` | ✅ |
| 2 | Harden `q6_population.sql` — current-customer filter (fix 103-month inflation) | `92e82de` | ✅ |
| 3 | Data Fabric SQL: `q7_data_fabric_monthly` + `q8_data_fabric_providers` | `87893b9` | ✅ |
| 4 | `q9_deployment_option.sql` (O11/ODC/O11-ODC + ODC-agent adoption) | `d6a421c` | ✅ |
| 5 | `q10_sku_gap_targeting.sql` (interop without SKU, w/ ARR) | `abeb7b9` | ✅ |
| — | Cross-fix: `IS_LAST_MONTH_REPORTED` current-customer filter on q6/q9/q10 | `fe9198f` | ✅ |
| 6 | `q11_infra_no_telemetry.sql` (active prod infra not reporting) | `f2139c0` | ✅ |
| 7 | q7–q11 test fixtures (`tests/conftest.py`) | `c1a4d6e` | ✅ |
| 8 | `load_data` reads q7–q11 Parquet | `dbd387d` | ✅ |
| 9 | `compute_metrics` — Data Fabric KPIs (connections/tenants/providers) | `8b615c7` | ✅ |
| 10 | `compute_metrics` — Data Fabric + deployment-option charts | `318f475` | ✅ |
| 11 | `compute_metrics` — targeting tables + ARR-at-risk (+NaN-ARR fix) | `ba177a0` | ✅ |
| 12 | Template — Data Fabric + Targeting tabs, deployment-option chart | `ea05015` | ✅ |
| 13 | Render tests for new tabs/values | `f175a40` | ✅ |
| 14 | `/refresh` runs q7–q11 (coercion table + 11-file count) | `3e4d00d` | ✅ |
| 15 | Live end-to-end refresh + dev-status | _this commit_ | ✅ |

### Test State

```
27 passed, 0 failed
```

- v1 baseline (17) + v2 additions (10): Data Fabric KPIs (3), new charts (1), targeting tables + ARR-at-risk + NaN-ARR regression (3), new render tabs (2), plus the load_data 11-key test.

### Latest Live Refresh (2026-07-02)

11 Parquet files written; `report.html` regenerated (6 tabs). Notable live values:
- Population donut total ≈ **2,360** current customers (no longer month-inflated).
- Data Fabric last full month (June 2026): **13,734** connections, **158** tenants (+14.8% MoM), **4** active providers.
- SKU-gap targeting: **58** interop-without-SKU customers; top target **PACCAR Inc**.
- Infra-without-telemetry: **637** rows.

---

## How to Use

1. From a Claude Code session in this directory, run `/refresh` to fetch fresh data from Snowflake and regenerate the HTML report.
2. Open `report.html` in a browser.

## End-to-End Smoke Test (Manual)

Requires Snowflake auth on connection `os` (account `AX81353-OUTSYSTEMS`):

```
/refresh
open report.html
```

Verify:
- All 6 tabs (Overview, Adoption, Usage, Segments, Data Fabric, Targeting) render and switch.
- KPI cards show values with MoM deltas (incl. Data Fabric connections/tenants and ARR-at-risk).
- All 9 charts render with data (incl. Data Fabric trend, by-provider, and the Segments deployment-option chart).
- SKU gap callout is visible in Segments tab; the Targeting tab lists SKU-gap customers (with ARR) and infra-without-telemetry.
- Population donut shows thousands (current customers), not ~188k.
- "Last updated" timestamp is current.

---

## Project Structure

```
dataInterOpMetrics/
├── .claude/
│   ├── commands/refresh.md
│   └── settings.local.json
├── .gitignore
├── data/                    ← Parquet files (gitignored, written by /refresh)
│   └── .gitkeep
├── docs/
│   ├── dev-status.md        ← this file
│   ├── data-context/        ← maintained Snowflake source-of-truth (v2)
│   │   ├── README.md
│   │   ├── tables.md
│   │   └── patterns.md
│   └── superpowers/
│       ├── plans/2026-06-15-data-interop-kpi-dashboard.md
│       ├── plans/2026-07-02-data-interop-dashboard-v2.md
│       ├── specs/2026-06-15-data-interop-kpi-dashboard-design.md
│       └── specs/2026-07-02-data-interop-dashboard-v2-design.md
├── queries/
│   ├── q1_adoption_trend.sql
│   ├── q2_by_product_family.sql
│   ├── q3_by_arch_type.sql
│   ├── q4_executions.sql
│   ├── q5_ao_usage.sql
│   ├── q6_population.sql
│   ├── q7_data_fabric_monthly.sql
│   ├── q8_data_fabric_providers.sql
│   ├── q9_deployment_option.sql
│   ├── q10_sku_gap_targeting.sql
│   └── q11_infra_no_telemetry.sql
├── render.py                ← load_data + compute_metrics + render
├── report.html              ← generated output (gitignored)
├── requirements.txt
├── templates/
│   └── report.html.j2
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_render.py
```
