-- Data InterOperability: frequency of connector changes (daily), last 12 months.
-- Telemetry is a DAILY SNAPSHOT, so "changes" are inferred by diffing consecutive days:
--   ADD_REMOVE  = day where a (tenant,env,provider) O11 connector COUNT changed vs prior day
--                 (net add/remove), from EXTERNALCONNECTIONCOUNT.
--   RECONFIGURE = day where an existing connection's selected entities/actions COUNT changed
--                 vs prior day, from EXTERNALCONNECTIONELEMENTSUSAGECOUNT (misses same-count swaps).
-- Covers all O11 connector tenants (not filtered to paying customers).
-- NOTE: snapshot fires ~00:00 UTC, so day-of-week is UTC and ~1 day after the actual edit.
WITH cnt_daily AS (
  SELECT tenant, environment_id, event_provider,
         TRY_TO_TIMESTAMP(event_sent)::date AS d, metric_value AS mv
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT
  WHERE event_provider ILIKE 'o11%'
    AND TRY_TO_TIMESTAMP(event_sent) >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY tenant, environment_id, event_provider,
    TRY_TO_TIMESTAMP(event_sent)::date ORDER BY TRY_TO_TIMESTAMP(event_sent) DESC) = 1
),
add_remove AS (
  SELECT d, COUNT(*) AS n FROM (
    SELECT d, mv - LAG(mv) OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d) AS delta
    FROM cnt_daily
  ) WHERE delta IS NOT NULL AND delta <> 0 GROUP BY d
),
elem_daily AS (
  SELECT tenantid, event_connectionid AS cid, TRY_TO_DATE(event_metricdate) AS d,
         MAX(event_selectedentitiescount) AS ents, MAX(event_selectedactionscount) AS acts
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT
  WHERE event_provider ILIKE 'o11%'
    AND TRY_TO_DATE(event_metricdate) >= DATEADD('month', -12, CURRENT_DATE)
  GROUP BY 1,2,3
),
reconfig AS (
  SELECT d, COUNT(*) AS n FROM (
    SELECT d,
      LAG(ents) OVER (PARTITION BY tenantid, cid ORDER BY d) AS pe, ents,
      LAG(acts) OVER (PARTITION BY tenantid, cid ORDER BY d) AS pa, acts
    FROM elem_daily
  ) WHERE pe IS NOT NULL AND (ents <> pe OR acts <> pa) GROUP BY d
)
SELECT COALESCE(a.d, r.d) AS DAY,
       COALESCE(a.n,0) AS ADD_REMOVE_EVENTS, COALESCE(r.n,0) AS RECONFIGURE_EVENTS
FROM add_remove a FULL OUTER JOIN reconfig r ON a.d = r.d
ORDER BY 1;
