-- Data InterOperability: connector change events by cloud region x ISO weekday (1=Mon..7=Sun),
-- split by change type (add_remove | reconfigure), ga+ea rings, last 12 months. EVENTS = count of
-- change events; N_TENANTS = distinct tenants with O11 connectors in that region x ring (the
-- denominator for "avg changes per tenant", computed in render.py: EVENTS / N_TENANTS per cell).
-- Powers the Region x Weekday heatmap with ring + change-type dropdowns. NULL region -> 'Unknown'.
-- add_remove = count-gauge delta; reconfigure = entities/actions delta. Daily-snapshot caveats
-- as q15; WEEKDAY is UTC snapshot-day (~1 day after the actual edit).
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
ar_events AS (
  SELECT region, ring, DAYOFWEEKISO(d) AS wd FROM (
    SELECT tenant, environment_id, event_provider, d, region, ring,
           mv - LAG(mv) OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d) delta
    FROM cnt_daily
  ) WHERE delta IS NOT NULL AND delta<>0
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
rc_events AS (
  SELECT region, ring, DAYOFWEEKISO(d) AS wd FROM (
    SELECT tenantid, cid, d, region, ring, ents, acts,
      LAG(ents) OVER (PARTITION BY tenantid, cid ORDER BY d) pe, LAG(acts) OVER (PARTITION BY tenantid, cid ORDER BY d) pa
    FROM elem_daily
  ) WHERE pe IS NOT NULL AND (ents<>pe OR acts<>pa)
),
tenants AS (
  SELECT region, ring, COUNT(DISTINCT tenant) AS n_tenants FROM (
    SELECT DISTINCT tenant, region, ring FROM cnt_daily
    UNION
    SELECT DISTINCT tenantid, region, ring FROM elem_daily
  ) GROUP BY 1,2
),
events AS (
  SELECT region, ring, wd, 'add_remove' AS change_type, COUNT(*) AS events FROM ar_events GROUP BY 1,2,3
  UNION ALL
  SELECT region, ring, wd, 'reconfigure', COUNT(*) FROM rc_events GROUP BY 1,2,3
)
SELECT e.region AS REGION, e.ring AS RING, e.wd AS WEEKDAY, e.change_type AS CHANGE_TYPE,
       e.events AS EVENTS, t.n_tenants AS N_TENANTS
FROM events e JOIN tenants t ON t.region=e.region AND t.ring=e.ring
ORDER BY REGION, RING, WEEKDAY, CHANGE_TYPE;
