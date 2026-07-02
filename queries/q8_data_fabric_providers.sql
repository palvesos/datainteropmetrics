-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Last complete month, per provider.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: QUALIFY partition = source natural key (tenant, environment_id, event_provider, event_sent); dedupes infra SCD2 fan-out only.
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
    AND DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)) = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE))
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ext.tenant, ext.environment_id, ext.event_provider, ext.event_sent ORDER BY infra.date_from DESC) = 1
)
SELECT
  event_provider                                     AS PROVIDER,
  CASE WHEN event_provider ILIKE 'o11cloud%'      THEN 'cloud'
       WHEN event_provider ILIKE 'o11selfhosted%' THEN 'self-hosted'
       ELSE 'other' END                            AS HOSTING,
  SPLIT_PART(event_provider, '_', 2)               AS ENGINE,
  COUNT(DISTINCT tenant)                           AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id)                  AS UNIQUE_CUSTOMERS,
  SUM(metric_value)                                AS TOTAL_CONNECTIONS
FROM deduped
GROUP BY 1, 2, 3
ORDER BY TOTAL_CONNECTIONS DESC
