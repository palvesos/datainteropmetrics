# Query Patterns & Pitfalls

## Current-customer filter
    WHERE MONTH_DT = (SELECT MAX(MONTH_DT) FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO)
      AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY
Why: CUSTOMERUNIFIEDINFO is a monthly snapshot; without it you count every month.

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
