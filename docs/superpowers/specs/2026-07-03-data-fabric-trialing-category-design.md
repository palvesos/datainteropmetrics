# Data Fabric — Trialing-customer category (design)

**Date:** 2026-07-03
**Status:** approved (brainstorming)
**Scope:** Data Fabric tab only (q7/q8 family). No change to other tabs.

## Motivation

Data Fabric telemetry (`q7`/`q8`) is filtered to `comp.type IN ('customer','partner')`,
which intentionally excludes non-paying tenants. The 2026-07-02 investigation
(see `.superpowers/sdd/progress.md`, T3 RESOLVED) confirmed the excluded bucket is
dominated by OutSystems `internal` tenants plus a meaningful `prospect customer`
slice (~1.1k connections in June 2026). Those prospects are **trialing** the product
— useful pipeline signal that is currently invisible on the dashboard.

This feature adds **trialing** as a distinct, additive category in the Data Fabric
tab, without altering the existing paying (customer/partner) numbers.

## Definition

**Trialing** = `COMPANY.type IN ('prospect customer', 'prospect partner')`.

`COMPANY.type` reflects a company's *current* status (documented in
`docs/data-context/tables.md`). Paying (customer/partner) and trialing are disjoint
sets, so the new series never double-counts the existing ones.

## Approach (chosen: A — new parallel query)

Add a new query mirroring `q7`, filtered to the prospect types. `q7`/`q8` stay
untouched, so the proven v2 pipeline and its KPIs/tests remain stable. This follows
the codebase's existing "one query per view" convention (q7 monthly vs q8 providers).
Rejected alternative B (generalize q7 with a `CATEGORY` column) because it changes
q7's output contract and ripples through `load_data`/`compute_metrics`/template/tests.

## Components

### 1. `queries/q12_data_fabric_trialing_monthly.sql` (new)

Exact copy of `q7_data_fabric_monthly.sql` — same INFRASTRUCTURE SCD2 date-range join,
COMPANY join, `event_provider ILIKE 'o11%'` filter, 12-month window, `TRY_TO_TIMESTAMP`
casts, and QUALIFY natural-key dedupe `(tenant, environment_id, event_provider,
event_sent)` — with the single change:

```sql
AND comp.type IN ('prospect customer', 'prospect partner')
```

Output columns (identical to q7): `MONTH, UNIQUE_TENANTS, UNIQUE_CUSTOMERS,
TOTAL_CONNECTIONS`. Header comment cross-references q7 as the paying counterpart.

### 2. `render.py`

- **`load_data()`**: read `data/q12_data_fabric_trialing_monthly.parquet` into a new
  key `data_fabric_trialing`. Total keys: 11 → 12.
- **`compute_metrics()`**:
  - New KPIs for the last complete month, reusing the existing `current_month_start`
    selection and `_pct_delta` helper (same logic path as `df_connections`/`df_tenants`):
    - `kpis.df_trialing_connections` (+ MoM delta)
    - `kpis.df_trialing_tenants` (+ MoM delta)
  - **`_chart_data_fabric_trend`**: add a second trace **"Trialing"** (trialing
    `TOTAL_CONNECTIONS` per month) alongside the existing paying trace, now labelled
    **"Customer/Partner"**. Trialing uses a distinct color from the plan's palette.
    Traces are independent (Plotly handles differing month coverage per trace).

### 3. `templates/report.html.j2`

Add a **Trialing** KPI card to the Data Fabric tab showing trialing connections and
trialing tenants (each with MoM delta), styled like the existing paying cards. The
trend chart renders from the `charts` dict, so the second trace flows through with no
template change beyond what already exists.

### 4. `.claude/commands/refresh.md`

Add a q12 row to the per-query table: SQL file `queries/q12_data_fabric_trialing_monthly.sql`,
Parquet `data/q12_data_fabric_trialing_monthly.parquet`, Date col `'MONTH'`, no Bool
cols, Numeric cols `'UNIQUE_TENANTS','UNIQUE_CUSTOMERS','TOTAL_CONNECTIONS'`. Update the
count "11 Parquet files" → "12" in the header and the confirm step.

## Data flow (shape unchanged)

`/refresh` runs q1–q12 → 12 Parquet files → `load_data` → `compute_metrics` →
Jinja2 template → `report.html`.

## Testing (TDD)

- `tests/conftest.py`: q12 trialing fixture (≥2 months so MoM delta is exercised),
  aligned to the pinned `_today = 2026-06-15` used by existing df tests.
- `load_data` returns **12** keys (extend/replace the 11-key assertion).
- `compute_metrics`: `df_trialing_connections`/`df_trialing_tenants` present with
  correct value + MoM delta for the pinned month.
- Trend chart has **2** traces.
- Render: trialing card label and value appear in the Data Fabric tab HTML.

## Non-goals

- No trialing breakdown in the by-provider chart (q8 unchanged).
- No trialing category on other tabs (Overview/Adoption/Usage/Segments/Targeting).
- No change to the paying (customer/partner) KPIs or their query logic.
