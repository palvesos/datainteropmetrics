-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Pattern: SCD2 join, provider filter.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: QUALIFY deduplicates tenant rows that match multiple SCD2 infra intervals.
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
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ext.tenant, ext.event_sent ORDER BY infra.date_from DESC) = 1
)
SELECT
  DATE_TRUNC('month', TRY_TO_TIMESTAMP(event_sent)) AS MONTH,
  COUNT(DISTINCT tenant)                             AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id)                    AS UNIQUE_CUSTOMERS,
  SUM(metric_value)                                  AS TOTAL_CONNECTIONS
FROM deduped
GROUP BY 1
ORDER BY 1 DESC
