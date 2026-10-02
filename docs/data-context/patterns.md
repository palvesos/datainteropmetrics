# Query Patterns & Pitfalls

## Current-customer filter
    WHERE IS_LAST_MONTH_REPORTED
      AND IS_CURRENT_CUSTOMER
      AND IS_CUSTOMER_POLICY
Why: CUSTOMERUNIFIEDINFO is a monthly snapshot; without a month filter you count every month.
`IS_LAST_MONTH_REPORTED` pins the query to the last fully-reported month (validated 2026-07-02:
= 2026-05-01, 2360 rows, all ARR_EUR populated). Do NOT use
`MONTH_DT = (SELECT MAX(MONTH_DT) FROM ...)`: MAX(MONTH_DT) is the current open month
(2026-07-01) where ARR_EUR is NULL for all ~2400 rows, making revenue-based queries return
nothing or misleading zeros.

## O11 infrastructure = enterprise only (business rule)
    WHERE product_family = 'O11'
      AND infrastructure_type = 'enterprise'
Whenever a query counts or joins a customer's O11 infrastructures / activation codes on
`CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE`, restrict to `infrastructure_type = 'enterprise'`.
**`enterprise-freemium` and `enterprise-trial` are out of scope** (decided 2026-10-02): a
customer with one production infra plus a trial/freemium one is not a "multiple O11
infrastructures" customer. `personal` and `cloud-cluster` carry no real customer usage and
are excluded by the same filter. `pge-enterprise` (5 codes, 3 companies) is also excluded by
this exact-match filter. Applied in q11, q21–q23 and q25–q35.
Consequence for Success Metrics Task 2: q21 ("Customers with Multiple O11 Infrastructures
Using Data Fabric") is the per-company view of the q31 Reach stage, not of q30 TAM. It equals
q31's live Reach list plus companies with any past O11 Data Fabric telemetry that are not
connected at month end (4 in Aug 2026).

## SCD2 date-range join
    INNER JOIN canonical.customersuccess.infrastructure infra
      ON infra.tenant_id = ext.tenant
      AND ext.event_sent::date >= infra.date_from
      AND ext.event_sent::date <  infra.date_to
      AND infra.is_active = TRUE
Always validate SUM/COUNT against the un-joined source to catch fan-out.

## Provider parsing
    CASE WHEN event_provider ILIKE 'o11cloud%' THEN 'cloud'
         WHEN event_provider ILIKE 'o11selfhosted%' THEN 'self-hosted' ELSE 'other' END AS hosting,
    SPLIT_PART(event_provider, '_', 2) AS engine   -- mssql | oracle

## Environment quality gate
    e.is_current AND e.is_active AND NOT e.is_deleted AND e.is_licensed
    AND e.environment_purpose = 'production'

## Pitfall: DECIMAL → JSON string
snow CLI returns DECIMAL/NUMERIC as strings. Coerce with pd.to_numeric() before arithmetic/parquet.

## Pitfall: monthly snapshot double-count
Any monthly-snapshot table (CUSTOMERUNIFIEDINFO, ODCAGENT) double-counts without a month filter.

## Pitfall: field-population-rate measured at the wrong grain
"% of rows with column X populated" across a whole table can be wildly misleading if most
rows belong to companies outside your actual cohort. Found on
`INFRASTRUCTURE.interoperability_related_activation_code`: ~0.7% populated across ALL 96,900
ODC infra rows system-wide, but ~79% populated when scoped to company-level within the
actual O11/ODC cohort (838 companies). Always measure population rate as
`COUNT(DISTINCT company) WHERE populated / COUNT(DISTINCT company)` within the relevant
cohort, never as a raw row-level fraction across the whole table.

## Pitfall: a CTE must re-join back to its cohort, not just re-derive it
When a downstream CTE (e.g. "Reach" or "Validated") recomputes an upstream population (e.g.
"TAM") from scratch instead of joining the upstream CTE's actual output, it can silently drop
the cohort restriction. Concretely: `tam_month AS (SELECT month, company_sfdc_id FROM
infra_count WHERE n_codes >= 2)` computes TAM over EVERY company with 2+ codes, not just the
O11/ODC ones — even if an earlier CTE in the same query already defined the correct O11/ODC
cohort. Fix: join back explicitly, e.g. `FROM o11_odc_month o JOIN infra_count ic ON ic.month
= o.month AND ic.company_sfdc_id = o.company_sfdc_id WHERE ic.n_codes >= 2`. Caught this in
`q31`/`q32`/`q33` (Task 2 Success Metrics funnel) — TAM read 1510 instead of matching q30's
258 until fixed.

## Funnel-stage % denominators
When building a multi-stage funnel (TAM → Reach → Validated → ...), each stage's % should be
relative to the PRIOR stage's count, not the whole population — otherwise it's not a funnel,
it's just three independent rates against the same base. See `_chart_funnel_stage` in
`render.py` (Success Metrics tab), which takes an explicit `denom_col` per stage rather than
hardcoding one shared denominator.

## SCD2 real-history vs. current-state-only snapshot
Not every "infra config" table is historized. `CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE` is
real SCD2 (`date_from`/`date_to`, current rows sentinel-closed at `2999-12-31`) and supports
genuine point-in-time reconstruction. `CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_*` (the O11
provisioning DB) is NOT — it's current-state only, no version history at all. Check for
`date_from`/`date_to` columns (and whether current rows close at a sentinel date) before
assuming a table can answer "what did this look like last month."

## Event-sourced config state (create/update/delete events)
For CRUD-event tables such as `ODC_METRIC.O11INFRASTRUCTURECONFIGURATION`, reconstruct state
at a cut-off by taking the latest event per entity key, then dropping entities whose latest
event is `deleted`:
```sql
SELECT * FROM ev
WHERE ts <= LAST_DAY(month)
QUALIFY ROW_NUMBER() OVER (PARTITION BY tenantid, infra_key, month ORDER BY ts DESC) = 1
-- then: WHERE op <> 'deleted'
```
Check the table's first event date before building a trend: if the event shipped without a
backfill, entities that existed before go-live are invisible until they are next touched, so
early months undercount.
