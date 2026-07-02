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
