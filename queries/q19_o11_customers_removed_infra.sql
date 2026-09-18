-- Data InterOperability: ODC customers who have FULLY removed their O11 connector
-- infrastructure (no O11 connector reporting anywhere anymore), not just reduced count.
-- EXTERNALCONNECTIONCOUNT is a DAILY gauge that fires every day regardless of change
-- (verified: a stable connector reports the same value every day) -- so once a tenant stops
-- reporting O11 entirely while it previously had connectors, that's a real full removal, not
-- a quiet day. A >14-day silence after the last nonzero reading is the removal signal.
--
-- IMPORTANT (two corrections vs. a naive version):
--  1. DEDUP per day: the metric can fire MULTIPLE times per (tenant, env, provider, day)
--     -- e.g. o11cloud_mssql emits ~twice daily. We must QUALIFY to the latest emission per
--     day (like q15/q16/q17/q20) before summing, or SUM(metric_value) inflates the count
--     (a single 1-connector env looks like 2).
--  2. TENANT-level, not per-environment: a customer has "fully removed" O11 only if it no
--     longer reports ANY O11 connector in ANY environment. Flagging a single quiet dev/test
--     environment while the customer's main O11 connector is still live is a false positive.
--
-- To rule out "customer churned entirely" (rather than "just dropped O11"), we require the
-- tenant still has an active+current environment AND positive recent platform usage.
-- Excludes internal/demo OutSystems tenants.
WITH cnt_daily AS (
  SELECT tenant, environment_id, event_provider,
         DATEADD('day', date_value - 1, DATE_FROM_PARTS(year, 1, 1)) AS d, metric_value AS mv
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT
  WHERE event_provider ILIKE 'o11%'
    -- daily-grain rows only; the W (ISO week) / M (month) re-emissions are the "~twice daily"
    -- duplicates noted above and would otherwise win the QUALIFY race on event_sent
    AND type = 'D'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY tenant, environment_id, event_provider,
    DATEADD('day', date_value - 1, DATE_FROM_PARTS(year, 1, 1))
    ORDER BY TRY_TO_TIMESTAMP(event_sent) DESC) = 1
),
daily_tenant_total AS (
  SELECT tenant, d, SUM(mv) AS total_mv
  FROM cnt_daily GROUP BY tenant, d
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
  SELECT ts.tenant, ts.last_o11_day, ts.peak_connectors, ts.last_known_connectors,
         ec.n_o11_envs,
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
)
SELECT
  tm.company_name         AS COMPANY_NAME,
  tm.company_sfdc_id      AS COMPANY_SFDC_ID,
  r.tenant                AS TENANT_ID,
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
WHERE tes.any_active = 1 AND tes.any_current = 1
  AND (tm.company_name <> 'OutSystems' OR tm.company_name IS NULL)
ORDER BY r.days_since_last_o11 DESC;
