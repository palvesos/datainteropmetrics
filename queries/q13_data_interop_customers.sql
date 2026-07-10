-- Data InterOperability: customers with O11 Data Fabric connections by ODC stage (dev/prod).
-- Bars = distinct current customers with an active O11 Data Fabric connection, split by ODC stage.
-- ODC stage bridge: EXTERNALCONNECTIONCOUNT.environment_id = ENVIRONMENT.stage_id (scoped by activation_code).
--   (canonical ENVIRONMENT.environment_id is numeric/O11; stage_id carries the ODC connection env UUID.)
-- % line denominator = monthly count of customers whose deployment is O11/ODC (cross-platform base).
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: comp filter = current customers (is_customer_policy).
WITH cust AS (
  SELECT DISTINCT company_sfdc_id
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy AND is_last_month_reported
),
conn AS (
  SELECT
    DATE_TRUNC('month', TRY_TO_TIMESTAMP(m.event_sent)) AS month,
    odc.company_sfdc_id,
    e.environment_purpose
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT m
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc ON odc.tenant_id = m.tenant
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT e
    ON m.environment_id = e.stage_id
    AND e.activation_code = odc.activation_code
    AND e.is_current AND e.is_active
  WHERE odc.is_current AND odc.is_active
    AND m.event_provider ILIKE 'o11%'
    AND m.metric_value > 0
    AND TRY_TO_TIMESTAMP(m.event_sent) >= DATEADD('month', -12, CURRENT_DATE)
),
stage_counts AS (
  SELECT c.month,
    COUNT(DISTINCT CASE WHEN c.environment_purpose='development' THEN c.company_sfdc_id END) AS dev_customers,
    COUNT(DISTINCT CASE WHEN c.environment_purpose='production'  THEN c.company_sfdc_id END) AS prod_customers
  FROM conn c INNER JOIN cust ON cust.company_sfdc_id = c.company_sfdc_id
  GROUP BY 1
),
o11_odc AS (
  SELECT DATE_TRUNC('month', month_dt) AS month,
    COUNT(DISTINCT CASE WHEN usage_deployment_option='O11/ODC' THEN company_sfdc_id END) AS o11_odc_customers
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
  GROUP BY 1
)
SELECT
  s.month              AS MONTH,
  s.dev_customers      AS DEV_CUSTOMERS,
  s.prod_customers     AS PROD_CUSTOMERS,
  o.o11_odc_customers  AS O11_ODC_CUSTOMERS
FROM stage_counts s
INNER JOIN o11_odc o ON o.month = s.month
ORDER BY s.month DESC
