-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Pattern: SCD2 join, provider filter.
-- METRIC_VALUE is a DAILY GAUGE (current connector count per tenant/env/provider, re-emitted daily).
-- Connectors, NOT connector-days: take the latest snapshot per entity WITHIN each month, then SUM.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: QUALIFY keeps one row per (month, tenant, environment_id, event_provider) = that entity's
--   end-of-month snapshot; this also subsumes SCD2 fan-out / same-day duplicate dedupe.
-- NOTE: comp.type IN ('customer','partner') = paying tenants (excludes internal/prospect/former).
WITH monthly_snapshot AS (
  SELECT
    DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)) AS MONTH,
    ext.tenant,
    ext.environment_id,
    ext.event_provider,
    ext.metric_value,
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
