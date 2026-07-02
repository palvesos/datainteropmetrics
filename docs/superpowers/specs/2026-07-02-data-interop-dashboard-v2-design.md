# Data Interoperability Dashboard v2 — Design Spec

**Date:** 2026-07-02
**Status:** Approved; refined by the implementation plan.
**Builds on:** the v1 dashboard (`render.py`, `templates/report.html.j2`, `queries/q1–q6`, `/refresh`).

> **Revision (2026-07-02, during planning):** deliverable A's single month×provider
> Data Fabric query is split into **q7** (monthly totals — exact distinct tenants/
> customers) + **q8** (last-complete-month provider breakdown). Pre-aggregated
> per-provider rows can't yield exact cross-provider distinct counts, so the split is
> required for correctness. This shifts numbering: deployment-option → **q9**,
> SKU-gap → **q10**, infra-no-telemetry → **q11**. See
> `docs/superpowers/plans/2026-07-02-data-interop-dashboard-v2.md`.

---

## Goal

Enlarge the Data Interoperability KPI dashboard with **direct Data Fabric connector
telemetry**, **deployment-option segmentation**, **hardened population counts**, and
**actionable targeting lists** — sourced from tables surfaced by the
`OutSystems/pm-workspace-hub` repo (read-only reference). Capture the underlying
schema knowledge in maintained **data-context docs** so future queries are grounded.

## Context & motivation

v1 infers interoperability from generic `IS_INTEROPERABILITY` flags and aggregated
execution counts. Investigation of `pm-workspace-hub` revealed richer, validated
sources we don't use. All findings below were **verified live against Snowflake
(connection `os`)** on 2026-07-02:

- `TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT` — actual Data Fabric
  external-DB connections. 45,710 rows / 178 tenants over 90d, current through today.
  4 providers: `o11cloud_mssql` (158 tenants), `o11cloud_oracle` (11),
  `o11selfhosted_mssql` (6), `o11selfhosted_oracle` (2).
- `CUSTOMERUNIFIEDINFO.USAGE_DEPLOYMENT_OPTION` (`O11`/`ODC`/`O11/ODC`) with
  `IS_CURRENT_CUSTOMER`, `IS_CUSTOMER_POLICY`, `MONTH_DT`, `ARR_EUR`, `SEGMENT`.
- `CANONICAL.CUSTOMERSUCCESS.ODCAGENT` (`N_AGENTS`, `N_EXECUTIONS`, `DATE_MONTH`).
- **Bug proven:** `q6_population.sql` has no `MONTH_DT` filter → it counts every
  company across **103 months** (188,715 rows for 4,259 distinct companies).
  Hardened (`MONTH_DT = MAX AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY`) → 2,400
  current customers, one month.

## Non-goals

- No changes to the v1 chart theme, tab framework, or `/refresh` execution model.
- No speculative refactoring of q1–q5 beyond a correctness review.
- Not rebuilding pm-workspace-hub features (slides, transcripts, etc.); we only
  reuse its SQL patterns and table knowledge.

---

## Deliverables

### A. New query files (`queries/`, following the `q1–q6` pattern)

All new customer-scoped queries filter to the current month and real customers using
the validated pattern `MONTH_DT = (SELECT MAX(MONTH_DT) …) AND IS_CURRENT_CUSTOMER
AND IS_CUSTOMER_POLICY` (or `IS_LAST_MONTH_REPORTED` where that is the table's idiom).

1. **`q7_data_fabric_monthly.sql`**
   Source: `EXTERNALCONNECTIONCOUNT ext` → `infrastructure infra` (SCD2:
   `ext.event_sent::date >= infra.date_from AND < infra.date_to`, `infra.is_active`)
   → `company comp` (`comp.type IN ('customer','partner')`).
   Filter: `event_provider ILIKE 'o11%'`, `event_sent >= DATEADD('month',-12,CURRENT_DATE)`.
   Output (one row per month × provider):
   `MONTH, PROVIDER, HOSTING, ENGINE, UNIQUE_TENANTS, UNIQUE_CUSTOMERS, TOTAL_CONNECTIONS`.
   `HOSTING` = `cloud` if provider `ILIKE 'o11cloud%'` else `self-hosted`;
   `ENGINE` = `SPLIT_PART(provider,'_',-1)` (`mssql`/`oracle`).

2. **`q8_deployment_option.sql`** (adapted from pm-workspace-hub Query 2)
   Source: `CUSTOMERUNIFIEDINFO c` LEFT JOIN aggregated `ODCAGENT a` on
   `COMPANY_SFDC_ID`, `a.DATE_MONTH = MAX(DATE_MONTH)`.
   Output (one row per option `O11`/`ODC`/`O11/ODC`):
   `USAGE_DEPLOYMENT_OPTION, TOTAL_CUSTOMERS, CUSTOMERS_WITH_AGENTS,
   ADOPTION_RATE_PCT, TOTAL_AGENTS, TOTAL_EXECUTIONS`.

3. **`q9_sku_gap_targeting.sql`**
   Source: `CUSTOMERUNIFIEDINFO`, current month + policy, `IS_INTEROPERABILITY
   AND NOT HAS_SKU_INTEROPERABILITY`.
   Output (one row per company): `COMPANY_SFDC_ID, COMPANY_NAME, SEGMENT,
   USAGE_DEPLOYMENT_OPTION, ARR_EUR`, ordered by `ARR_EUR DESC`.

4. **`q10_infra_no_telemetry.sql`** (adapted from pm-workspace-hub Query 11)
   Active enterprise **production** infra not reporting telemetry in the last week.
   Output (one row per activation_code): `ACTIVATION_CODE, COMPANY_SFDC_ID,
   COMPANY_NAME, ARCHITECTURE_TYPE, INFRASTRUCTURE_STATUS, USAGE_DEPLOYMENT_OPTION`.

The current-month Data Fabric snapshot (per-provider breakdown, KPI values) is
**derived in Python** from q7's latest complete month — no separate query.

### B. Harden existing queries

- **`q6_population.sql`** — add `WHERE MONTH_DT = (SELECT MAX(MONTH_DT) FROM …)
  AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY`. Output shape (columns) unchanged;
  counts corrected. `population_donut` becomes accurate.
- **q1–q5** — correctness review only. They aggregate with `COUNT(DISTINCT … )`
  per period and are not month-inflated. Apply a filter change only if the review
  finds a concrete defect; otherwise leave unchanged and record the review outcome
  in the data-context docs.

### C. `render.py` + `templates/report.html.j2`

- **`load_data`** — extend the file_map to include `q7`–`q10` parquet files.
- **`compute_metrics`** — add:
  - KPIs (all Data Fabric month-based metrics use the **last complete month** —
    skip the partial current month, same rule v1 applies to `prod_executions`):
    `df_tenants` (Data Fabric tenants), `df_connections` (total connections),
    `df_providers` (# active providers), `arr_at_risk` (Σ `ARR_EUR` of q9 rows).
    MoM deltas where a prior month exists.
  - Charts: `data_fabric_trend` (connections + unique tenants, 12mo dual-axis —
    shows all months incl. partial current, like v1's trend charts),
    `data_fabric_providers` (grouped bar by hosting × engine, last complete month),
    `deployment_option_bar` (customers + customers-with-agents by option).
  - Tables: `sku_gap_targeting` (top-N by ARR, N=20), `infra_no_telemetry`
    (first N ordered by `COMPANY_NAME`, N=20). Full row counts surfaced as a
    KPI/label so truncation is explicit.
- **Template** — new `_chart_*` helpers per chart; two new tabs:
  - **Data Fabric**: trend chart + provider breakdown chart + KPI cards.
  - **Targeting**: SKU-gap table (with ARR) + no-telemetry table.
  - **Segments**: add `deployment_option_bar`.
  - **Overview / Adoption**: population donut now uses corrected q6.

### D. `/refresh` (`.claude/commands/refresh.md`)

- Add q7–q10 rows to the per-query table with correct Date / Bool / Numeric
  coercion columns (numeric coercion is mandatory — see data-context pitfall).
- Keep the existing tempfile-capture + empty-result guards.

### E. Tests (TDD — failing tests first)

- Extend `tests/conftest.py` with representative sample DataFrames for q7–q10 and
  the corrected q6 shape.
- Add `compute_metrics` tests for each new KPI, chart (data + layout present,
  non-empty), and table; update existing q6-dependent assertions.
- `render` tests assert the two new tabs and a Data Fabric KPI value appear in
  the HTML.

### F. Data-context docs (`docs/data-context/`) — maintained source of truth

- **`README.md`** — purpose; "read before writing a query, update after validating
  a new table/column."
- **`tables.md`** — one entry per table we query (v1 + v2): fully-qualified name,
  purpose, key columns, **grain**, and validated gotchas.
- **`patterns.md`** — reusable patterns & learnings:
  - SCD2 date-range join (`event_date >= date_from AND < date_to`).
  - Current-customer filter (`MONTH_DT = MAX AND IS_CURRENT_CUSTOMER AND
    IS_CUSTOMER_POLICY`) and why (avoids the 103-month inflation).
  - Provider-string parsing (`o11cloud_mssql` → hosting + engine).
  - Environment quality gate (`is_current AND is_active AND NOT is_deleted AND
    is_licensed AND environment_purpose='production'`).
  - Pitfall: snow CLI serializes `DECIMAL`/`NUMERIC` as JSON strings → coerce with
    `pd.to_numeric()`.
  - Pitfall: monthly snapshot tables double-count without a `MONTH_DT` filter.

**Definition of done** includes updating these docs to reflect every table/column/
pattern the new queries introduce, and each `queries/q*.sql` header naming the
data-context entries it relies on.

---

## Architecture & data flow (unchanged model)

```
/refresh → snow sql (q1–q10) → data/*.parquet
        → render.py: load_data → compute_metrics → render(Jinja2) → report.html
```

New queries slot into the existing pipeline; no new runtime components. The dashboard
stays a single self-contained HTML file with Plotly-from-CDN.

## Risks & mitigations

- **q6 hardening changes headline numbers.** Expected and correct; called out in the
  change and reflected in tests + data-context.
- **Provider taxonomy may evolve** (`o11cloud_*`/`o11selfhosted_*`). Parsing uses
  `ILIKE`/`SPLIT_PART` and falls back to the raw provider string; documented in
  `patterns.md`.
- **SCD2 / customer-policy joins can fan out.** Grain is asserted per query during
  implementation (row count = distinct-key count), the same validation approach used
  to finish `DataInterOpMetrics.sql`.

## Testing strategy

TDD at the `compute_metrics` layer with in-memory fixtures (no live Snowflake in the
test suite). Live validation of each new query's grain/values happens during
implementation via `snow sql`, and results feed the data-context docs.

## Out of scope / future

- `q10_infra_no_telemetry` could grow into a full data-quality tab — deferred.
- Per-customer Data Fabric drill-down (customer × provider) — deferred.
