-- Data Interoperability Success Metrics -- Task 2, stage (d) Depth/breadth, monthly trend --
-- ALTERNATE SIGNAL companion to q33, scoped to the q34 (LIFETIME_UNIFICATION-based) Validated
-- cohort instead of the q32 (O11INFRASTRUCTURECONFIGURATION-based) one. See q34's
-- header for why this reads empty today (brand-new telemetry stream, no real customer tenants
-- resolved yet) and q29/q33 for the entity-count source and convention.
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
    AND i.infrastructure_type = 'enterprise'   -- freemium/trial out of scope, see data-context
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
unification_month AS (
  SELECT
    DATE_TRUNC('month', u.event_date) AS month,
    odc.company_sfdc_id,
    u.env_activation_code
  FROM TELEMETRYANALYTICS.METRICS.LIFETIME_UNIFICATION u
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc
    ON odc.tenant_id = u.domain_odctenantid
  WHERE odc.is_current AND odc.is_active
    AND u.env_activation_code IS NOT NULL
    AND DATE_TRUNC('month', u.event_date) >= DATEADD('month', -12, CURRENT_DATE)
),
code_count AS (
  SELECT month, company_sfdc_id, COUNT(DISTINCT env_activation_code) AS n_codes_handshaked
  FROM unification_month
  GROUP BY 1, 2
),
validated_month AS (
  SELECT r.month, r.company_sfdc_id
  FROM reach_month r
  JOIN code_count cc ON cc.month = r.month AND cc.company_sfdc_id = r.company_sfdc_id
  WHERE cc.n_codes_handshaked >= 2
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
