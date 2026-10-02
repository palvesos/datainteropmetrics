-- Data Interoperability Success Metrics -- Task 2, stage (d) Depth/breadth, monthly trend:
-- avg # of entities imported per O11 Data Fabric connection, broken out dev / non-prod / prod,
-- restricted to the Task 2(c) Validated cohort each month (see q32 for the full stage chain):
-- Reach customers with 2+ distinct live O11 LifeTime URLs linked via
-- ODC_METRIC.O11INFRASTRUCTURECONFIGURATION (no data before 2026-08-27 -- see q32 caveats).
--
-- "BY ACTIVATION CODE" SIMPLIFICATION: the doc asks for this broken out by O11 infra as
-- well as by stage. This query reports the average PER CONNECTION across all of a customer's O11
-- infrastructures combined (i.e. a customer with 3 linked infras contributes all 3 infras'
-- connections to the same average) -- a true per-activation-code breakdown would need a
-- per-company detail table rather than a single monthly trend line and isn't built here.
--
-- ENTITY COUNT SOURCE: TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT,
--   EVENT_SELECTEDENTITIESCOUNT -- see q29 for details (same convention).
WITH o11_odc_month AS (
  SELECT DISTINCT company_sfdc_id, DATE_TRUNC('month', month_dt) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
    AND usage_deployment_option = 'O11/ODC'
    AND DATE_TRUNC('month', month_dt) >= DATEADD('month', -12, CURRENT_DATE)
),
month_series AS (
  SELECT DISTINCT month FROM o11_odc_month
),
infra_asof AS (
  SELECT m.month, i.company_sfdc_id, i.activation_code
  FROM month_series m
  JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE i
    ON i.product_family = 'O11'
    AND NOT i.is_deleted
    AND i.is_active
    AND i.date_from <= LAST_DAY(m.month)
    AND i.date_to > LAST_DAY(m.month)
  WHERE i.company_sfdc_id IS NOT NULL
    AND i.activation_code IS NOT NULL
),
infra_count AS (
  SELECT month, company_sfdc_id, COUNT(DISTINCT activation_code) AS n_codes
  FROM infra_asof
  GROUP BY 1, 2
),
tam_month AS (
  SELECT o.month, o.company_sfdc_id
  FROM o11_odc_month o
  JOIN infra_count ic ON ic.month = o.month AND ic.company_sfdc_id = o.company_sfdc_id
  WHERE ic.n_codes >= 2
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
infra_cfg_ev AS (
  SELECT DISTINCT
    messageid,
    tenantid,
    event_infrastructurekey AS infra_key,
    LOWER(RTRIM(event_lifetimeurl, '/')) AS lifetime_url,
    event_operationtype AS op,
    TRY_TO_TIMESTAMP(eventdatetime) AS ts
  FROM TELEMETRYANALYTICS.ODC_METRIC.O11INFRASTRUCTURECONFIGURATION
  WHERE event_lifetimeurl IS NOT NULL
    AND LOWER(event_lifetimeurl) NOT LIKE 'https://pp-%'
),
cfg_months AS (
  SELECT month FROM month_series
  WHERE LAST_DAY(month) >= (SELECT DATE_TRUNC('month', MIN(ts)) FROM infra_cfg_ev)
),
infra_cfg_asof AS (
  SELECT m.month, e.tenantid, e.infra_key, e.lifetime_url, e.op
  FROM cfg_months m
  JOIN infra_cfg_ev e ON e.ts < DATEADD('day', 1, LAST_DAY(m.month))
  QUALIFY ROW_NUMBER() OVER (PARTITION BY m.month, e.tenantid, e.infra_key ORDER BY e.ts DESC) = 1
),
linked_count AS (
  SELECT a.month, odc.company_sfdc_id, COUNT(DISTINCT a.lifetime_url) AS n_linked_infras
  FROM infra_cfg_asof a
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc
    ON odc.tenant_id = a.tenantid AND odc.is_current AND odc.is_active
  WHERE a.op <> 'deleted'
  GROUP BY 1, 2
),
validated_month AS (
  SELECT r.month, r.company_sfdc_id
  FROM reach_month r
  JOIN linked_count lc ON lc.month = r.month AND lc.company_sfdc_id = r.company_sfdc_id
  WHERE lc.n_linked_infras >= 2
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
