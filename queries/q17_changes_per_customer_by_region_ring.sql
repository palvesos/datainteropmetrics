-- Data InterOperability: number of connector changes per customer, by cloud region x ring (ga/ea),
-- last 12 months. Change = add/remove (count-gauge delta) OR reconfigure (entities/actions delta),
-- same detection as q15/q16. Counted per (customer, region, ring), then aggregated to AVG and
-- MEDIAN across customers within each region x ring cell. N_CUSTOMERS/TOTAL_CHANGES give context
-- (many ea cells have very few customers -> noisy). ga+ea rings only; NULL region -> 'Unknown'.
-- Daily-snapshot caveats identical to q15 (1-day resolution, window censoring).
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
  SELECT tenant_id, MAX(activation_code) AS activation_code, MAX(company_sfdc_id) AS company
  FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE
  WHERE is_current AND is_active AND infrastructure_type_label='Enterprise Phoenix' GROUP BY 1
),
cnt_daily AS (
  SELECT ext.tenant, ext.environment_id, ext.event_provider,
         TRY_TO_TIMESTAMP(ext.event_sent)::date AS d, ext.metric_value AS mv,
         ed.region, rt.ring, i.company
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
  SELECT company, COALESCE(region,'Unknown') AS region, ring, COUNT(*) n FROM (
    SELECT company, region, ring, mv - LAG(mv) OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d) delta
    FROM cnt_daily
  ) WHERE delta IS NOT NULL AND delta<>0 GROUP BY 1,2,3
),
elem_daily AS (
  SELECT u.tenantid, u.event_connectionid AS cid, TRY_TO_DATE(u.event_metricdate) AS d,
         MAX(u.event_selectedentitiescount) AS ents, MAX(u.event_selectedactionscount) AS acts,
         MAX(ed.region) AS region, MAX(rt.ring) AS ring, MAX(i.company) AS company
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT u
  JOIN ring_tenants rt ON rt.tenant_id = u.tenantid
  JOIN infra_dim i ON i.tenant_id = u.tenantid
  JOIN env_dim ed ON ed.stage_id = u.environmentid AND ed.activation_code = i.activation_code
  WHERE u.event_provider ILIKE 'o11%' AND TRY_TO_DATE(u.event_metricdate) >= DATEADD('month',-12,CURRENT_DATE)
  GROUP BY 1,2,3
),
reconfig AS (
  SELECT company, COALESCE(region,'Unknown') AS region, ring, COUNT(*) n FROM (
    SELECT company, region, ring, ents, acts,
      LAG(ents) OVER (PARTITION BY tenantid, cid ORDER BY d) pe, LAG(acts) OVER (PARTITION BY tenantid, cid ORDER BY d) pa
    FROM elem_daily
  ) WHERE pe IS NOT NULL AND (ents<>pe OR acts<>pa) GROUP BY 1,2,3
),
per_customer AS (
  SELECT COALESCE(a.company,r.company) AS company, COALESCE(a.region,r.region) AS region,
         COALESCE(a.ring,r.ring) AS ring, COALESCE(a.n,0)+COALESCE(r.n,0) AS changes
  FROM add_remove a FULL OUTER JOIN reconfig r
    ON a.company=r.company AND a.region=r.region AND a.ring=r.ring
)
SELECT region AS REGION, ring AS RING,
       ROUND(AVG(changes),2) AS AVG_CHANGES_PER_CUSTOMER,
       MEDIAN(changes) AS MEDIAN_CHANGES_PER_CUSTOMER,
       COUNT(DISTINCT company) AS N_CUSTOMERS,
       SUM(changes) AS TOTAL_CHANGES
FROM per_customer
GROUP BY 1,2 ORDER BY N_CUSTOMERS DESC;
