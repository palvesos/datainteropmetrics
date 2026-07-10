-- Data InterOperability: number of connector ADD/REMOVE changes per TENANT, by cloud region x
-- ring (ga/ea), last 12 months. A "change" here is ONLY an addition or deletion of a connector
-- (net change in the EXTERNALCONNECTIONCOUNT daily count gauge) -- reconfigurations are NOT counted.
-- Events counted per (tenant, region, ring), then aggregated to AVG and MEDIAN across tenants
-- within each region x ring cell. N_TENANTS/TOTAL_CHANGES give context (many ea cells have very
-- few tenants -> noisy). ga+ea rings only; NULL region -> 'Unknown'.
-- Daily-snapshot caveats: 1-day resolution; same-day add+remove nets to zero and is missed;
-- 12-month window censoring.
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
         ed.region, rt.ring
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
  SELECT tenant, COALESCE(region,'Unknown') AS region, ring, COUNT(*) AS changes FROM (
    SELECT tenant, region, ring, mv - LAG(mv) OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d) delta
    FROM cnt_daily
  ) WHERE delta IS NOT NULL AND delta<>0 GROUP BY 1,2,3
)
SELECT region AS REGION, ring AS RING,
       ROUND(AVG(changes),2) AS AVG_CHANGES_PER_TENANT,
       MEDIAN(changes) AS MEDIAN_CHANGES_PER_TENANT,
       COUNT(DISTINCT tenant) AS N_TENANTS,
       SUM(changes) AS TOTAL_CHANGES
FROM add_remove
GROUP BY 1,2 ORDER BY N_TENANTS DESC;
