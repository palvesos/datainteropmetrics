-- Data InterOperability: q20 ("Connector Removal Events by Company", all-time) RESTRICTED to
-- the q21 population -- customers running >1 active O11 enterprise infrastructure AND with a
-- live O11 Data Fabric connection. Same removal-event / peak / today logic as q20, but only
-- multi-O11-infra customers are kept, and NUM_O11_INFRAS is surfaced. Excludes internal OutSystems.
WITH cnt_daily AS (
  SELECT tenant, environment_id, event_provider,
         TRY_TO_TIMESTAMP(event_sent)::date AS d, metric_value AS mv
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT
  WHERE event_provider ILIKE 'o11%'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY tenant, environment_id, event_provider,
    TRY_TO_TIMESTAMP(event_sent)::date ORDER BY TRY_TO_TIMESTAMP(event_sent) DESC) = 1
),
tm AS (
  SELECT tenant_id, MAX(company_name) AS company_name, MAX(company_sfdc_id) AS company_sfdc_id
  FROM CANONICAL.CUSTOMERSUCCESS.TENANTMETADATA GROUP BY 1
),
cnt_company AS (
  SELECT COALESCE(tm.company_sfdc_id, c.tenant) AS company_key, tm.company_name,
         c.tenant, c.environment_id, c.event_provider, c.d, c.mv
  FROM cnt_daily c LEFT JOIN tm ON tm.tenant_id = c.tenant
),
bounds AS (SELECT MAX(d) AS global_max_day FROM cnt_daily),
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
),
-- ===== q20 removal-event / footprint logic =====
deltas AS (
  SELECT company_key, company_name, d,
         mv - LAG(mv) OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d) AS delta
  FROM cnt_company
),
removals AS (
  SELECT company_key, MAX(company_name) AS company_name,
         COUNT(*) AS removal_events, SUM(-delta) AS total_connectors_removed
  FROM deltas WHERE delta < 0 GROUP BY company_key
),
company_daily_total AS (
  SELECT company_key, d, SUM(mv) AS total_mv FROM cnt_company GROUP BY company_key, d
),
peak AS (
  SELECT company_key, MAX(total_mv) AS peak_connectors FROM company_daily_total GROUP BY company_key
),
series_last AS (
  SELECT company_key, tenant, environment_id, event_provider,
         MAX(d) AS last_d,
         (ARRAY_AGG(mv) WITHIN GROUP (ORDER BY d DESC))[0]::int AS last_val
  FROM cnt_company GROUP BY 1,2,3,4
),
today AS (
  SELECT s.company_key,
         SUM(CASE WHEN DATEDIFF('day', s.last_d, b.global_max_day) <= 14 THEN s.last_val ELSE 0 END)
           AS connectors_today
  FROM series_last s CROSS JOIN bounds b
  GROUP BY s.company_key
)
SELECT
  r.company_name              AS COMPANY_NAME,
  r.company_key               AS COMPANY_SFDC_ID,
  p.num_o11_infras            AS NUM_O11_INFRAS,
  r.removal_events            AS REMOVAL_EVENTS,
  r.total_connectors_removed  AS TOTAL_CONNECTORS_REMOVED,
  pk.peak_connectors          AS PEAK_TOTAL_CONNECTORS,
  t.connectors_today          AS CONNECTORS_TODAY
FROM removals r
JOIN q21_pop p ON p.COMPANY_SFDC_ID = r.company_key
JOIN peak pk ON pk.company_key = r.company_key
JOIN today t ON t.company_key = r.company_key
WHERE r.company_name <> 'OutSystems' OR r.company_name IS NULL
ORDER BY r.removal_events DESC, r.total_connectors_removed DESC;
