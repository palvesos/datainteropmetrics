-- Data InterOperability: q19 ("Customers Who Fully Removed Their O11 Connector Infrastructure")
-- RESTRICTED to the q21 population -- customers running >1 active O11 enterprise infrastructure
-- AND with a live O11 Data Fabric connection. Same tenant-level full-removal detection as q19
-- (daily-gauge dedup, >14-day silence, still active/current + recent usage), but only tenants
-- belonging to a multi-O11-infra customer are kept, and NUM_O11_INFRAS is surfaced.
-- Excludes internal OutSystems tenants.
WITH cnt_daily AS (
  SELECT tenant, environment_id, event_provider,
         DATEADD('day', date_value - 1, DATE_FROM_PARTS(year, 1, 1)) AS d, metric_value AS mv
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT
  WHERE event_provider ILIKE 'o11%'
    -- daily-grain rows only; the table also carries W (ISO week) / M (month) re-emissions
    AND type = 'D'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY tenant, environment_id, event_provider,
    DATEADD('day', date_value - 1, DATE_FROM_PARTS(year, 1, 1))
    ORDER BY TRY_TO_TIMESTAMP(event_sent) DESC) = 1
),
daily_tenant_total AS (
  SELECT tenant, d, SUM(mv) AS total_mv FROM cnt_daily GROUP BY tenant, d
),
bounds AS (SELECT MAX(d) AS global_max_day FROM daily_tenant_total),
tenant_summary AS (
  SELECT tenant,
         MAX(d) AS last_o11_day,
         MAX(total_mv) AS peak_connectors,
         (ARRAY_AGG(total_mv) WITHIN GROUP (ORDER BY d DESC))[0]::int AS last_known_connectors
  FROM daily_tenant_total GROUP BY tenant
),
env_count AS (
  SELECT tenant, COUNT(DISTINCT environment_id) AS n_o11_envs FROM cnt_daily GROUP BY tenant
),
removed AS (
  SELECT ts.tenant, ts.last_o11_day, ts.peak_connectors, ts.last_known_connectors, ec.n_o11_envs,
         DATEDIFF('day', ts.last_o11_day, b.global_max_day) AS days_since_last_o11
  FROM tenant_summary ts
  JOIN env_count ec ON ec.tenant = ts.tenant
  CROSS JOIN bounds b
  WHERE ts.peak_connectors > 0
    AND DATEDIFF('day', ts.last_o11_day, b.global_max_day) > 14
),
tm AS (
  SELECT tenant_id, MAX(company_name) AS company_name, MAX(company_sfdc_id) AS company_sfdc_id
  FROM CANONICAL.CUSTOMERSUCCESS.TENANTMETADATA GROUP BY 1
),
env_status AS (
  SELECT stage_id, MAX(is_active::int) AS any_active, MAX(is_current::int) AS any_current
  FROM CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT GROUP BY 1
),
tenant_env_status AS (
  SELECT c.tenant, MAX(es.any_active) AS any_active, MAX(es.any_current) AS any_current
  FROM (SELECT DISTINCT tenant, environment_id FROM cnt_daily) c
  JOIN env_status es ON es.stage_id = c.environment_id
  GROUP BY c.tenant
),
recent_usage AS (
  SELECT i.tenant_id, MAX(TO_DATE(d.day_date)) AS last_usage_day
  FROM CANONICAL.CUSTOMERSUCCESS.PLATFORMUTILIZATIONWEEKLY base
  JOIN CANONICAL.CORE.DATE d ON base.date_id = d.date_key_nr
  JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE i ON base.infrastructure_id = i.infrastructure_id
  WHERE base.ao_usage > 0 OR base.distinct_visitors > 0
  GROUP BY 1
),
-- ===== q21 population: >1 active O11 enterprise infra AND a live O11 DF connection =====
o11_conn_series AS (
  SELECT odc.company_sfdc_id
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT AS m
  INNER JOIN canonical.customersuccess.infrastructure AS odc ON odc.tenant_id = m.TENANT
  LEFT JOIN canonical.customersuccess.environment AS e ON m.environment_id = e.stage_id
  WHERE odc.is_current AND odc.is_active
    AND e.activation_code = odc.activation_code
    AND e.is_current AND e.is_active
    AND m.event_provider ILIKE 'o11%'
    AND m.type = 'D'
),
df_companies AS (SELECT DISTINCT company_sfdc_id FROM o11_conn_series),
multiple_o11 AS (
  SELECT cui.COMPANY_SFDC_ID, COUNT(DISTINCT o11.ACTIVATION_CODE) AS num_o11_infras
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO AS cui
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE AS o11 ON cui.COMPANY_SFDC_ID = o11.COMPANY_SFDC_ID
  WHERE cui.IS_LAST_MONTH_REPORTED AND cui.IS_CUSTOMER_POLICY
    AND o11.IS_ACTIVE AND o11.IS_CURRENT AND NOT o11.IS_DELETED
    AND o11.INFRASTRUCTURE_TYPE = 'enterprise'
  GROUP BY cui.company_name, cui.COMPANY_SFDC_ID
  HAVING COUNT(DISTINCT o11.ACTIVATION_CODE) > 1
),
q21_pop AS (
  SELECT DISTINCT cui.COMPANY_SFDC_ID, ms.num_o11_infras
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO AS cui
  INNER JOIN multiple_o11 ms ON ms.COMPANY_SFDC_ID = cui.COMPANY_SFDC_ID
  INNER JOIN df_companies df ON df.company_sfdc_id = cui.COMPANY_SFDC_ID
  WHERE cui.IS_LAST_MONTH_REPORTED AND cui.IS_CUSTOMER_POLICY
)
SELECT
  tm.company_name         AS COMPANY_NAME,
  tm.company_sfdc_id      AS COMPANY_SFDC_ID,
  r.tenant                AS TENANT_ID,
  p.num_o11_infras        AS NUM_O11_INFRAS,
  r.n_o11_envs            AS N_O11_ENVS,
  r.peak_connectors       AS PEAK_CONNECTORS,
  r.last_known_connectors AS LAST_KNOWN_CONNECTORS,
  r.last_o11_day          AS LAST_CONNECTOR_TELEMETRY_DAY,
  r.days_since_last_o11   AS DAYS_SINCE_CONNECTOR_TELEMETRY,
  ru.last_usage_day       AS LAST_PLATFORM_USAGE_DAY
FROM removed r
JOIN tenant_env_status tes ON tes.tenant = r.tenant
JOIN recent_usage ru ON ru.tenant_id = r.tenant
LEFT JOIN tm ON tm.tenant_id = r.tenant
JOIN q21_pop p ON p.COMPANY_SFDC_ID = tm.company_sfdc_id
WHERE tes.any_active = 1 AND tes.any_current = 1
  AND (tm.company_name <> 'OutSystems' OR tm.company_name IS NULL)
ORDER BY r.days_since_last_o11 DESC;
