-- TRIALING counterpart to q7. Identical shape/logic; only the COMPANY.type filter differs.
-- METRIC_VALUE is a DAILY GAUGE; connectors = latest snapshot per entity within each month, then SUM.
-- NOTE: comp.type IN ('prospect customer','prospect partner') = non-paying tenants trialing the product.
--   Disjoint from q7's ('customer','partner') set, so the two series never double-count.
-- NOTE: metric_day = YEAR + DATE_VALUE (day-of-year) = the day the gauge DESCRIBES; event_sent is
--   the delivery day (metric_day+1). See q7 for the full rationale.
WITH ext AS (
  SELECT
    tenant, environment_id, event_provider, metric_value, event_sent,
    DATEADD('day', date_value - 1, DATE_FROM_PARTS(year, 1, 1)) AS metric_day
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT
  WHERE event_provider ILIKE 'o11%'
    -- daily-grain rows only; the table also carries W (ISO week) / M (month) re-emissions
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
    AND comp.type IN ('prospect customer', 'prospect partner')
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
