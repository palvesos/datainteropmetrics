-- Data Interoperability Success Metrics -- Task 1, stage (d) Depth/breadth, monthly trend:
-- avg # of entities imported per O11 Data Fabric connection, broken out dev / non-prod / prod,
-- restricted to the Task 1(c) Validated cohort each month (see q28 for the full stage chain and
-- its cross-pipeline caveat, which also applies here: this is depth among customers holding
-- >=2 pipelines and >=2 connected non-dev environments, not proven cross-pipeline depth).
--
-- ENTITY COUNT SOURCE: TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT,
--   EVENT_SELECTEDENTITIESCOUNT -- a daily gauge per (tenant, environment, connection) reporting
--   how many entities are currently selected/imported for that Data Fabric connection. Same
--   month-end-position convention as the connector-count metric elsewhere in this report.
WITH o11_odc_month AS (
  SELECT DISTINCT company_sfdc_id, DATE_TRUNC('month', month_dt) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
    AND usage_deployment_option = 'O11/ODC'
    AND DATE_TRUNC('month', month_dt) >= DATEADD('month', -12, CURRENT_DATE)
),
o11_codes AS (
  SELECT DISTINCT company_sfdc_id, activation_code
  FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE
  WHERE is_current AND is_active
    AND product_family = 'O11'
    AND company_sfdc_id IS NOT NULL
    AND activation_code IS NOT NULL
),
live_slots AS (
  SELECT i.activationcode, s.slottypeid
  FROM CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_INFRASTRUCTURE i
  JOIN CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_INFRASTRUCTURESLOT s
    ON s.infrastructureid = i.id
  JOIN CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_ENVIRONMENT e
    ON e.id = s.environmentid
  WHERE i.isdeleted = '0'
    AND e.isdeleted = '0'
    AND s.infrastructureslotstateid = '6'
),
infra_shape AS (
  SELECT activationcode,
         COUNT(CASE WHEN slottypeid = '3' THEN 1 END) AS prod_envs
  FROM live_slots
  GROUP BY 1
),
company_shape AS (
  SELECT
    oc.company_sfdc_id,
    MAX(sh.prod_envs) AS max_pipelines_in_one_infra,
    COUNT(DISTINCT CASE WHEN sh.activationcode IS NOT NULL THEN oc.activation_code END) AS resolved_infras
  FROM o11_codes oc
  LEFT JOIN infra_shape sh ON sh.activationcode = oc.activation_code
  GROUP BY 1
),
tam_month AS (
  SELECT m.month, m.company_sfdc_id
  FROM o11_odc_month m
  JOIN company_shape cs ON cs.company_sfdc_id = m.company_sfdc_id
  WHERE cs.resolved_infras > 0 AND cs.max_pipelines_in_one_infra >= 2
),
conn_daily AS (
  SELECT
    DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1)) AS day,
    odc.company_sfdc_id
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT m
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc ON odc.tenant_id = m.tenant
  WHERE odc.is_current AND odc.is_active
    AND m.event_provider ILIKE 'o11%'
    AND m.type = 'D'
    AND m.metric_value > 0
    AND DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1))
        >= DATEADD('month', -12, CURRENT_DATE)
),
conn AS (
  SELECT DATE_TRUNC('month', day) AS month, company_sfdc_id
  FROM conn_daily
  QUALIFY day = MAX(day) OVER (PARTITION BY DATE_TRUNC('month', day))
),
reach_month AS (
  SELECT DISTINCT t.month, t.company_sfdc_id
  FROM tam_month t
  JOIN conn c ON c.month = t.month AND c.company_sfdc_id = t.company_sfdc_id
),
conn_env_daily AS (
  SELECT
    DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1)) AS day,
    odc.company_sfdc_id, m.tenant, m.environment_id, e.environment_purpose
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT m
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc ON odc.tenant_id = m.tenant
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT e
    ON m.environment_id = e.stage_id
    AND e.activation_code = odc.activation_code
    AND e.is_current AND e.is_active
  WHERE odc.is_current AND odc.is_active
    AND m.event_provider ILIKE 'o11%'
    AND m.type = 'D'
    AND m.metric_value > 0
    AND DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1))
        >= DATEADD('month', -12, CURRENT_DATE)
),
conn_env AS (
  SELECT DATE_TRUNC('month', day) AS month, company_sfdc_id, tenant, environment_id, environment_purpose
  FROM conn_env_daily
  QUALIFY day = MAX(day) OVER (PARTITION BY DATE_TRUNC('month', day))
),
nondev_env_count AS (
  SELECT month, company_sfdc_id,
         COUNT(DISTINCT tenant || ':' || environment_id) AS n_nondev_envs
  FROM conn_env
  WHERE environment_purpose IN ('non-production', 'production')
  GROUP BY 1, 2
),
validated_month AS (
  SELECT r.month, r.company_sfdc_id
  FROM reach_month r
  JOIN nondev_env_count n ON n.month = r.month AND n.company_sfdc_id = r.company_sfdc_id
  WHERE n.n_nondev_envs >= 2
),
ent_daily AS (
  SELECT
    m.EVENT_METRICDATE::DATE AS day,
    odc.company_sfdc_id,
    e.environment_purpose,
    m.TENANTID AS tenant,
    m.ENVIRONMENTID AS environment_id,
    m.EVENT_CONNECTIONID AS connection_id,
    m.EVENT_SELECTEDENTITIESCOUNT AS entities
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT m
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc ON odc.tenant_id = m.TENANTID
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT e
    ON m.ENVIRONMENTID = e.stage_id
    AND e.activation_code = odc.activation_code
    AND e.is_current AND e.is_active
  WHERE odc.is_current AND odc.is_active
    AND m.EVENT_PROVIDER ILIKE 'o11%'
    AND m.EVENT_METRICDATE::DATE >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY m.TENANTID, m.ENVIRONMENTID, m.EVENT_CONNECTIONID, m.EVENT_METRICDATE
    ORDER BY m.EVENTDATETIME DESC
  ) = 1
),
ent_month AS (
  SELECT DATE_TRUNC('month', day) AS month, company_sfdc_id, environment_purpose, entities
  FROM ent_daily
  QUALIFY day = MAX(day) OVER (PARTITION BY DATE_TRUNC('month', day))
),
ent_scoped AS (
  SELECT em.*
  FROM ent_month em
  JOIN validated_month v ON v.month = em.month AND v.company_sfdc_id = em.company_sfdc_id
)
SELECT
  month AS MONTH,
  AVG(CASE WHEN environment_purpose = 'development' THEN entities END) AS AVG_ENTITIES_DEV,
  AVG(CASE WHEN environment_purpose = 'non-production' THEN entities END) AS AVG_ENTITIES_NONPROD,
  AVG(CASE WHEN environment_purpose = 'production' THEN entities END) AS AVG_ENTITIES_PROD
FROM ent_scoped
GROUP BY 1
ORDER BY 1
