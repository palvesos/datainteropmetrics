-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Last complete month, per provider.
-- METRIC_VALUE is a DAILY GAUGE; connectors = latest in-month snapshot per entity, then SUM by provider.
-- NOTE: type='D' keeps daily-grain rows only; the table also carries W (ISO week) and M (month)
--   re-emissions of the same gauge, which would otherwise win the QUALIFY race.
-- NOTE: metric_day = YEAR + DATE_VALUE (day-of-year) = the day the gauge DESCRIBES. event_sent is
--   the delivery day (always metric_day+1 for D rows); bucketing by it pushed each month's last
--   day into the next month. event_sent survives only as a same-metric_day tiebreaker.
WITH ext AS (
  SELECT
    tenant, environment_id, event_provider, metric_value, event_sent,
    DATEADD('day', date_value - 1, DATE_FROM_PARTS(year, 1, 1)) AS metric_day
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT
  WHERE event_provider ILIKE 'o11%'
    AND type = 'D'
    AND metric_value > 0
),
monthly_snapshot AS (
  SELECT
    ext.tenant,
    ext.environment_id,
    ext.event_provider,
    ext.metric_value,
    comp.company_sfdc_id
  FROM ext
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
    ON infra.tenant_id = ext.tenant
    AND ext.metric_day >= infra.date_from::date
    AND ext.metric_day <  infra.date_to::date
    AND infra.is_active = TRUE
  INNER JOIN CANONICAL.CORE.COMPANY comp
    ON comp.company_sfdc_id = infra.company_sfdc_id
    AND comp.type IN ('customer', 'partner')
  WHERE DATE_TRUNC('month', ext.metric_day) = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE))
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ext.tenant, ext.environment_id, ext.event_provider
    ORDER BY ext.metric_day DESC, TRY_TO_TIMESTAMP(ext.event_sent) DESC, infra.date_from DESC) = 1
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
