# Data Fabric — Connector Count Fix (connector-days → existing connectors)

**Date:** 2026-07-08
**Status:** approved (design)
**Scope:** Data Fabric queries q7, q8, q12 + `render.py` + template + tests + refresh docs.

## Problem

`TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT.METRIC_VALUE` is a **daily gauge**: for
each `tenant × environment_id × event_provider` it reports the *current number of external
connectors*, re-emitted every day (verified — the same value repeats on consecutive days;
occasional same-day duplicate rows also occur).

q7 (`data_fabric_monthly`), q8 (`data_fabric_providers`), and q12 (`data_fabric_trialing_monthly`)
aggregate this with `SUM(metric_value)`. Summing a daily gauge over a month/12-month window counts
**connector-days**, not connectors — inflating the metric by roughly the number of days each
connector reported (~30× per month, ~365× per year).

Observed impact: the "production, all customers" figure read **20,187** as a `SUM`; the corrected
existing-connector count is **~160**. The `COUNT(DISTINCT …)` columns (`UNIQUE_TENANTS`,
`UNIQUE_CUSTOMERS`) were already correct and are unaffected — only the volume metric is wrong.

## Fix — end-of-month snapshot

For a gauge, the correct monthly value is a **point-in-time snapshot**, not a sum. We take, for
each `(month, tenant, environment_id, event_provider)`, the row with the **latest `event_sent`
within that month**, then `SUM(metric_value)` across entities. This reads as "how many connectors
existed at each month-end" and produces a clean month-over-month trend.

The new `QUALIFY` (latest-in-month per entity) also subsumes the old SCD2 fan-out / same-day
dedupe, so it fully replaces the previous `QUALIFY`. We additionally require `metric_value > 0`.

### q7 — `queries/q7_data_fabric_monthly.sql` (paying: customer/partner)

```sql
WITH monthly_snapshot AS (
  SELECT
    DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)) AS MONTH,
    ext.tenant, ext.environment_id, ext.event_provider, ext.metric_value,
    comp.company_sfdc_id
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
    ON infra.tenant_id = ext.tenant
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date >= infra.date_from::date
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date <  infra.date_to::date
    AND infra.is_active = TRUE
  INNER JOIN CANONICAL.CORE.COMPANY comp
    ON comp.company_sfdc_id = infra.company_sfdc_id
    AND comp.type IN ('customer', 'partner')
  WHERE ext.event_provider ILIKE 'o11%'
    AND ext.metric_value > 0
    AND TRY_TO_TIMESTAMP(ext.event_sent) >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)),
                 ext.tenant, ext.environment_id, ext.event_provider
    ORDER BY TRY_TO_TIMESTAMP(ext.event_sent) DESC, infra.date_from DESC) = 1
)
SELECT
  MONTH,
  COUNT(DISTINCT tenant)          AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id) AS UNIQUE_CUSTOMERS,
  SUM(metric_value)               AS TOTAL_CONNECTORS
FROM monthly_snapshot
GROUP BY 1
ORDER BY 1 DESC
```

### q12 — `queries/q12_data_fabric_trialing_monthly.sql` (trialing: prospect customer/partner)

Identical to q7 except the company filter: `comp.type IN ('prospect customer', 'prospect partner')`.

### q8 — `queries/q8_data_fabric_providers.sql` (per provider, last complete month)

Keep the last-complete-month scope; dedupe to the latest in-month snapshot per entity *before*
grouping by provider:

```sql
WITH monthly_snapshot AS (
  SELECT
    ext.tenant, ext.environment_id, ext.event_provider, ext.metric_value,
    comp.company_sfdc_id
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
    ON infra.tenant_id = ext.tenant
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date >= infra.date_from::date
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date <  infra.date_to::date
    AND infra.is_active = TRUE
  INNER JOIN CANONICAL.CORE.COMPANY comp
    ON comp.company_sfdc_id = infra.company_sfdc_id
    AND comp.type IN ('customer', 'partner')
  WHERE ext.event_provider ILIKE 'o11%'
    AND ext.metric_value > 0
    AND DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)) = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE))
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ext.tenant, ext.environment_id, ext.event_provider
    ORDER BY TRY_TO_TIMESTAMP(ext.event_sent) DESC, infra.date_from DESC) = 1
)
SELECT
  event_provider                                     AS PROVIDER,
  CASE WHEN event_provider ILIKE 'o11cloud%'      THEN 'cloud'
       WHEN event_provider ILIKE 'o11selfhosted%' THEN 'self-hosted'
       ELSE 'other' END                            AS HOSTING,
  SPLIT_PART(event_provider, '_', 2)               AS ENGINE,
  COUNT(DISTINCT tenant)                           AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id)                  AS UNIQUE_CUSTOMERS,
  SUM(metric_value)                                AS TOTAL_CONNECTORS
FROM monthly_snapshot
GROUP BY 1, 2, 3
ORDER BY TOTAL_CONNECTORS DESC
```

## Relabel — metric name matches meaning

The column and KPI keys are renamed so nothing still says "connections":

| Old | New |
|---|---|
| SQL/Parquet column `TOTAL_CONNECTIONS` | `TOTAL_CONNECTORS` (q7, q8, q12) |
| KPI key `df_connections` | `df_connectors` |
| KPI key `df_trialing_connections` | `df_trialing_connectors` |
| Card label `DF Connections (last full mo.)` | `DF Connectors (last full mo.)` |
| Card label `Trialing Conn. (last full mo.)` | `Trialing Connectors (last full mo.)` |
| Trend chart y-axis title `Connections` | `Connectors` |
| Providers chart trace name `Connections` | `Connectors` |

Unchanged names: trend traces `Customer/Partner`, `Trialing`, `Tenants`; section heading
`Connector Usage Trend (12 mo.)` (already correct); `df_tenants`, `df_trialing_tenants`,
`df_providers`, `df_providers.value` (derived from `TOTAL_CONNECTORS > 0`).

## render.py changes

- `_chart_data_fabric_trend(df, trialing_df)`: read `TOTAL_CONNECTORS` (both series); y-axis title
  `Connectors`. Trace names unchanged.
- `_chart_data_fabric_providers(df)`: read `TOTAL_CONNECTORS`; sort on `TOTAL_CONNECTORS`; trace
  name `Connectors`.
- `compute_metrics`:
  - Data Fabric block: `df_connectors = int(df_cur["TOTAL_CONNECTORS"])`; delta from
    `TOTAL_CONNECTORS`. `df_providers = int((data["q8"]["TOTAL_CONNECTORS"] > 0).sum())`.
  - Trialing block: `df_trialing_connectors = int(dft_cur["TOTAL_CONNECTORS"])`; delta from
    `TOTAL_CONNECTORS`.
  - `kpis` dict: keys `df_connectors`, `df_trialing_connectors` (rename in place; `is_pct`/
    `direction`/`delta` semantics unchanged).
- The "last full month" / MoM-delta logic (`current_month_start`, `_pct_delta`) is **unchanged**.

## Tests

The SQL semantic change is **not** unit-tested — consistent with the repo, SQL correctness is
validated by a real `/refresh` against Snowflake (manual, post-implementation). Unit tests cover
`render.py` only, and change by **rename**, not logic:

- `tests/conftest.py`: fixture q7/q8/q12 column `TOTAL_CONNECTIONS` → `TOTAL_CONNECTORS`. Values
  unchanged (synthetic connector counts): q7 May=1300/25, April=1000/20 → +30.0% / +25.0%; q12
  likewise per its fixture.
- `tests/test_render.py`: rename assertion keys `df_connections`→`df_connectors`,
  `df_trialing_connections`→`df_trialing_connectors`; column refs `TOTAL_CONNECTIONS`→
  `TOTAL_CONNECTORS`; trend/providers trace name assertions (`Connectors`). Asserted numeric
  values unchanged. Card-label assertions updated to the new labels.
- Full suite (`python -m pytest tests/ -q`) stays green, 0 warnings.

## refresh.md

In `.claude/commands/refresh.md`, the q7, q8, and q12 rows: numeric-col name
`'TOTAL_CONNECTIONS'` → `'TOTAL_CONNECTORS'`. Query count stays 12.

## Post-implementation validation (manual, requires Snowflake)

- Run `/refresh` (12 Parquet files) then `python render.py`.
- Confirm `TOTAL_CONNECTORS` collapses from the tens-of-thousands `SUM` range to the low hundreds
  (recent full month total in the ~500–600 range across paying+trialing; production-paying ≈ 160).
- Data Fabric tab: cards read "Connectors", trend bars are at connector (not connector-day) scale,
  providers chart axis reflects connectors.

## Non-goals

- No new metrics or KPI cards; no change to other tabs (Overview/Adoption/Usage/Segments/Targeting).
- The ad-hoc "112 entitled + connected customers" analysis is not persisted here.
- No change to `UNIQUE_TENANTS` / `UNIQUE_CUSTOMERS` definitions (already correct `COUNT(DISTINCT)`).
