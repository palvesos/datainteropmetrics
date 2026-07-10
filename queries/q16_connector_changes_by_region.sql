-- Data InterOperability: connector change events by cloud region, ga+ea rings only, last 12 months.
-- Same change-detection as q15 (ADD_REMOVE = count delta; RECONFIGURE = entities/actions delta),
-- but restricted to tenants whose ODC_RING IN ('ga','ea') and grouped by the environment's
-- AWS cloud region (ENVIRONMENT.aws_region_name). Region resolved via the stage_id bridge
-- (env.stage_id = telemetry environment_id, scoped by activation_code).
-- NULL region -> 'Unknown'. Daily-snapshot caveats identical to q15.
WITH env_dim AS (
  SELECT activation_code, stage_id, MAX(aws_region_name) AS region
  FROM CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT
  WHERE is_current AND is_active AND stage_id IS NOT NULL
  GROUP BY 1,2
),
ring_tenants AS (
  SELECT DISTINCT tenant_id FROM CANONICAL.CUSTOMERSUCCESS.TENANTMETADATA WHERE odc_ring IN ('ga','ea')
),
infra_dim AS (
  SELECT tenant_id, MAX(activation_code) AS activation_code
  FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE
  WHERE is_current AND is_active AND infrastructure_type_label='Enterprise Phoenix' GROUP BY 1
),
cnt_daily AS (
  SELECT ext.tenant, ext.environment_id, ext.event_provider,
         TRY_TO_TIMESTAMP(ext.event_sent)::date AS d, ext.metric_value AS mv, ed.region
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
  JOIN ring_tenants rt ON rt.tenant_id = ext.tenant
  JOIN infra_dim i ON i.tenant_id = ext.tenant
  JOIN env_dim ed ON ed.stage_id = ext.environment_id AND ed.activation_code = i.activation_code
  WHERE ext.event_provider ILIKE 'o11%'
    AND TRY_TO_TIMESTAMP(ext.event_sent) >= DATEADD('month',-12,CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ext.tenant, ext.environment_id, ext.event_provider,
    TRY_TO_TIMESTAMP(ext.event_sent)::date ORDER BY TRY_TO_TIMESTAMP(ext.event_sent) DESC)=1
),
add_remove AS (
  SELECT COALESCE(region,'Unknown') AS region, COUNT(*) n FROM (
    SELECT region, mv - LAG(mv) OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d) delta FROM cnt_daily
  ) WHERE delta IS NOT NULL AND delta<>0 GROUP BY 1
),
elem_daily AS (
  SELECT u.tenantid, u.event_connectionid AS cid, TRY_TO_DATE(u.event_metricdate) AS d,
         MAX(u.event_selectedentitiescount) AS ents, MAX(u.event_selectedactionscount) AS acts, MAX(ed.region) AS region
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT u
  JOIN ring_tenants rt ON rt.tenant_id = u.tenantid
  JOIN infra_dim i ON i.tenant_id = u.tenantid
  JOIN env_dim ed ON ed.stage_id = u.environmentid AND ed.activation_code = i.activation_code
  WHERE u.event_provider ILIKE 'o11%' AND TRY_TO_DATE(u.event_metricdate) >= DATEADD('month',-12,CURRENT_DATE)
  GROUP BY 1,2,3
),
reconfig AS (
  SELECT COALESCE(region,'Unknown') AS region, COUNT(*) n FROM (
    SELECT region, ents, acts,
      LAG(ents) OVER (PARTITION BY tenantid, cid ORDER BY d) pe, LAG(acts) OVER (PARTITION BY tenantid, cid ORDER BY d) pa
    FROM elem_daily
  ) WHERE pe IS NOT NULL AND (ents<>pe OR acts<>pa) GROUP BY 1
)
SELECT COALESCE(a.region, r.region) AS REGION,
       COALESCE(a.n,0) AS ADD_REMOVE_EVENTS, COALESCE(r.n,0) AS RECONFIGURE_EVENTS
FROM add_remove a FULL OUTER JOIN reconfig r ON a.region=r.region
ORDER BY (COALESCE(a.n,0)+COALESCE(r.n,0)) DESC;
