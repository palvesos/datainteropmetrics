-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Pattern: SCD2 join, provider filter.
-- METRIC_VALUE is a DAILY GAUGE (current connector count per tenant/env/provider, re-emitted daily).
-- Connectors, NOT connector-days: take the latest snapshot per entity WITHIN each month, then SUM.
-- NOTE: QUALIFY keeps one row per (month, tenant, environment_id, event_provider) = that entity's
--   end-of-month snapshot; this also subsumes SCD2 fan-out / same-day duplicate dedupe.
-- NOTE: comp.type IN ('customer','partner') = paying tenants (excludes internal/prospect/former).
-- NOTE: type='D' keeps daily-grain rows only. The table mixes grains -- D/W/M, where DATE_VALUE
--   means day-of-year / ISO week / month number respectively. W and M rows re-emit the same gauge
--   value and would otherwise win the QUALIFY race.
-- NOTE: metric_day = YEAR + DATE_VALUE (day-of-year) = the day the gauge DESCRIBES. event_sent is
--   the day it was DELIVERED, always metric_day+1 for D rows, so bucketing by event_sent pushed
--   each month's last day into the next month. All date logic below uses metric_day; event_sent
--   survives only as a tiebreaker between repeated emissions of the same metric_day.
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
    DATE_TRUNC('month', ext.metric_day) AS MONTH,
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
  WHERE ext.metric_day >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY DATE_TRUNC('month', ext.metric_day),
                 ext.tenant, ext.environment_id, ext.event_provider
    ORDER BY ext.metric_day DESC, TRY_TO_TIMESTAMP(ext.event_sent) DESC, infra.date_from DESC) = 1
)
SELECT
  MONTH,
  COUNT(DISTINCT tenant)          AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id) AS UNIQUE_CUSTOMERS,
  SUM(metric_value)               AS TOTAL_CONNECTORS
FROM monthly_snapshot
GROUP BY 1
ORDER BY 1 DESC
