-- Data InterOperability: per-company rollup of O11 connector REMOVAL events (any day-over-day
-- decrease in EXTERNALCONNECTIONCOUNT, per tenant/environment/provider) -- partial removals
-- included, not just full disconnects (see q19 for full-removal detection). All-time.
-- Excludes internal OutSystems tenants.
-- Dedups multiple same-day emissions with QUALIFY before diffing/summing (the gauge can fire
-- more than once per day, which would otherwise inflate counts).
-- Adds two footprint columns per company:
--   PEAK_TOTAL_CONNECTORS = max over days of the company's total live connector count
--                           (summed across all its tenants/envs/providers on each day).
--   CONNECTORS_TODAY      = sum of each series' latest value, counting only series still
--                           reporting within 14 days of the latest telemetry day (a series
--                           silent longer is treated as removed -> 0).
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
  r.removal_events            AS REMOVAL_EVENTS,
  r.total_connectors_removed  AS TOTAL_CONNECTORS_REMOVED,
  p.peak_connectors           AS PEAK_TOTAL_CONNECTORS,
  t.connectors_today          AS CONNECTORS_TODAY
FROM removals r
JOIN peak p ON p.company_key = r.company_key
JOIN today t ON t.company_key = r.company_key
WHERE r.company_name <> 'OutSystems' OR r.company_name IS NULL
ORDER BY r.removal_events DESC, r.total_connectors_removed DESC;
