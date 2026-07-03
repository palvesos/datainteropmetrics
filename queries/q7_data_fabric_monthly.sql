-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Pattern: SCD2 join, provider filter.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: QUALIFY partition = source natural key (tenant, environment_id, event_provider, event_sent); dedupes infra SCD2 fan-out only.
-- NOTE: comp.type IN ('customer','partner') intentionally excludes non-paying telemetry. Verified 2026-07-02:
--   the raw-vs-q7 gap is 100% this filter (infra SCD2 join drops nothing) and is dominated by OutSystems
--   'internal' tenants (dogfooding) plus some 'prospect customer'. The gap is larger in older months because
--   early Data Fabric usage was internal-dominated pre-GA; this is a real adoption curve, not a data defect.
--   COMPANY.type reflects CURRENT status (also 'former customer', 'internal', 'prospect customer', etc.).
WITH deduped AS (
  SELECT
    ext.event_sent,
    ext.tenant,
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
    AND TRY_TO_TIMESTAMP(ext.event_sent) >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ext.tenant, ext.environment_id, ext.event_provider, ext.event_sent ORDER BY infra.date_from DESC) = 1
)
SELECT
  DATE_TRUNC('month', TRY_TO_TIMESTAMP(event_sent)) AS MONTH,
  COUNT(DISTINCT tenant)                             AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id)                    AS UNIQUE_CUSTOMERS,
  SUM(metric_value)                                  AS TOTAL_CONNECTIONS
FROM deduped
GROUP BY 1
ORDER BY 1 DESC
