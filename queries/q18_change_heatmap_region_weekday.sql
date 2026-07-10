-- Data InterOperability: connector change events by cloud region x ISO weekday (1=Mon..7=Sun),
-- split by change type (add_remove | reconfigure) AND time window, ga+ea rings.
-- WINDOW_KEY in {1m,3m,6m,all}: a change/tenant is included if its day is within that window
-- (all = last 12 months). N_TENANTS is recomputed PER WINDOW (distinct tenants with O11 connectors
-- in that region x ring within the window) so "avg changes per tenant" = EVENTS / N_TENANTS is
-- correct for each window. Powers the Region x Weekday heatmap with time-range + ring + change-type
-- dropdowns. NULL region -> 'Unknown'. WEEKDAY is UTC snapshot-day (~1 day after the actual edit).
WITH env_dim AS (
  SELECT activation_code, stage_id, MAX(aws_region_name) AS region
  FROM CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT
  WHERE is_current AND is_active AND stage_id IS NOT NULL GROUP BY 1,2
),
ring_tenants AS (
  SELECT tenant_id, MAX(odc_ring) AS ring FROM CANONICAL.CUSTOMERSUCCESS.TENANTMETADATA
  WHERE odc_ring IN ('ga','ea') GROUP BY 1
),
infra_dim AS (
  SELECT tenant_id, MAX(activation_code) AS activation_code
  FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE
  WHERE is_current AND is_active AND infrastructure_type_label='Enterprise Phoenix' GROUP BY 1
),
cnt_daily AS (
  SELECT ext.tenant, ext.environment_id, ext.event_provider,
         TRY_TO_TIMESTAMP(ext.event_sent)::date AS d, ext.metric_value AS mv,
         COALESCE(ed.region,'Unknown') AS region, rt.ring
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
  JOIN ring_tenants rt ON rt.tenant_id = ext.tenant
  JOIN infra_dim i ON i.tenant_id = ext.tenant
  JOIN env_dim ed ON ed.stage_id = ext.environment_id AND ed.activation_code = i.activation_code
  WHERE ext.event_provider ILIKE 'o11%'
    AND TRY_TO_TIMESTAMP(ext.event_sent) >= DATEADD('month',-12,CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ext.tenant, ext.environment_id, ext.event_provider,
    TRY_TO_TIMESTAMP(ext.event_sent)::date ORDER BY TRY_TO_TIMESTAMP(ext.event_sent) DESC)=1
),
elem_daily AS (
  SELECT u.tenantid, u.event_connectionid AS cid, TRY_TO_DATE(u.event_metricdate) AS d,
         MAX(u.event_selectedentitiescount) AS ents, MAX(u.event_selectedactionscount) AS acts,
         MAX(COALESCE(ed.region,'Unknown')) AS region, MAX(rt.ring) AS ring
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT u
  JOIN ring_tenants rt ON rt.tenant_id = u.tenantid
  JOIN infra_dim i ON i.tenant_id = u.tenantid
  JOIN env_dim ed ON ed.stage_id = u.environmentid AND ed.activation_code = i.activation_code
  WHERE u.event_provider ILIKE 'o11%' AND TRY_TO_DATE(u.event_metricdate) >= DATEADD('month',-12,CURRENT_DATE)
  GROUP BY 1,2,3
),
change_events AS (
  SELECT region, ring, d, DAYOFWEEKISO(d) AS wd, 'add_remove' AS change_type FROM (
    SELECT region, ring, d, mv - LAG(mv) OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d) delta
    FROM cnt_daily
  ) WHERE delta IS NOT NULL AND delta<>0
  UNION ALL
  SELECT region, ring, d, DAYOFWEEKISO(d), 'reconfigure' FROM (
    SELECT region, ring, d, ents, acts,
      LAG(ents) OVER (PARTITION BY tenantid, cid ORDER BY d) pe, LAG(acts) OVER (PARTITION BY tenantid, cid ORDER BY d) pa
    FROM elem_daily
  ) WHERE pe IS NOT NULL AND (ents<>pe OR acts<>pa)
),
tenant_days AS (
  SELECT tenant, region, ring, d FROM cnt_daily
  UNION
  SELECT tenantid, region, ring, d FROM elem_daily
),
windows AS (
  SELECT '1m' AS wk, DATEADD('month',-1,CURRENT_DATE) AS cutoff
  UNION ALL SELECT '3m', DATEADD('month',-3,CURRENT_DATE)
  UNION ALL SELECT '6m', DATEADD('month',-6,CURRENT_DATE)
  UNION ALL SELECT 'all', DATEADD('month',-12,CURRENT_DATE)
),
events_w AS (
  SELECT w.wk, e.region, e.ring, e.wd, e.change_type, COUNT(*) AS events
  FROM change_events e JOIN windows w ON e.d >= w.cutoff
  GROUP BY 1,2,3,4,5
),
tenants_w AS (
  SELECT w.wk, td.region, td.ring, COUNT(DISTINCT td.tenant) AS n_tenants
  FROM tenant_days td JOIN windows w ON td.d >= w.cutoff
  GROUP BY 1,2,3
)
SELECT ev.wk AS WINDOW_KEY, ev.region AS REGION, ev.ring AS RING, ev.wd AS WEEKDAY,
       ev.change_type AS CHANGE_TYPE, ev.events AS EVENTS, t.n_tenants AS N_TENANTS
FROM events_w ev JOIN tenants_w t ON t.wk=ev.wk AND t.region=ev.region AND t.ring=ev.ring
ORDER BY WINDOW_KEY, REGION, RING, WEEKDAY, CHANGE_TYPE;
