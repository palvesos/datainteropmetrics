-- Data Interoperability Success Metrics -- Task 2, stage (c) Validated use case, monthly trend:
-- of the Task 2(b) Reach cohort, split by how many distinct O11 activation codes their live
-- connections target at month end -- exactly 1 vs 2+ (2+ = connections targeting different O11
-- infrastructures, not just different environments within the same one; that's Task 1, see q28's
-- caveat for why the distinction matters). A third bucket (Unresolved) covers Reach customers
-- whose connections carry no attributable O11 code at all.
--
-- ACTIVATION CODE OF THE O11-SIDE INFRASTRUCTURE A CONNECTION TARGETS:
--   INTEROPERABILITY_RELATED_ACTIVATION_CODE on the ODC-family INFRASTRUCTURE row (matched via
--   tenant_id) -- the REAL O11 activation code the Data Fabric connection points to, as
--   established in q24. Re-verified at the company level within the O11/ODC cohort: ~79%
--   populated (not the ~0.7% row-level figure across ALL ODC infra rows system-wide, most of
--   which are irrelevant trial/unrelated tenants) -- this field is a solid signal, just a
--   tenant-level one (see q34 for an event-level alternative, TELEMETRYANALYTICS.METRICS
--   .LIFETIME_UNIFICATION, currently too new/sparse to use on its own).
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
conn_code_daily AS (
  SELECT
    DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1)) AS day,
    odc.company_sfdc_id,
    odc.interoperability_related_activation_code AS o11_code
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT m
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc ON odc.tenant_id = m.tenant
  WHERE odc.is_current AND odc.is_active
    AND m.event_provider ILIKE 'o11%'
    AND m.type = 'D'
    AND m.metric_value > 0
    AND DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1))
        >= DATEADD('month', -12, CURRENT_DATE)
),
conn_code AS (
  SELECT DATE_TRUNC('month', day) AS month, company_sfdc_id, o11_code
  FROM conn_code_daily
  QUALIFY day = MAX(day) OVER (PARTITION BY DATE_TRUNC('month', day))
),
code_count AS (
  SELECT month, company_sfdc_id, COUNT(DISTINCT o11_code) AS n_codes_connected
  FROM conn_code
  WHERE o11_code IS NOT NULL
  GROUP BY 1, 2
)
SELECT
  r.month AS MONTH,
  COUNT(DISTINCT CASE WHEN cc.n_codes_connected = 1 THEN r.company_sfdc_id END) AS ONE_INFRA_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN cc.n_codes_connected >= 2 THEN r.company_sfdc_id END) AS MULTI_INFRA_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN cc.company_sfdc_id IS NULL THEN r.company_sfdc_id END) AS UNRESOLVED_CUSTOMERS,
  COUNT(DISTINCT r.company_sfdc_id) AS REACH_CUSTOMERS
FROM reach_month r
LEFT JOIN code_count cc ON cc.month = r.month AND cc.company_sfdc_id = r.company_sfdc_id
GROUP BY 1
ORDER BY 1
