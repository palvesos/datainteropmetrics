-- Data InterOperability: customers/apps whose published ServerEntity elements are referenced
-- by an O11 external connection, split by ODC stage (dev/prod), where the app is runtime-live
-- in that stage that month.
-- App -> connector link: APPREVISIONPUBLICELEMENT (latest revision, ServerEntity) EVENT_ELEMENTKEY
--   matched to the flattened EVENT_ENTITYIDS of EXTERNALCONNECTIONELEMENTSUSAGECOUNT (o11 provider).
-- Runtime-live gate: app must appear in AOUSAGEAPPREVISION for the same tenant/env/month.
-- Stage bridge: usage ENVIRONMENTID = ENVIRONMENT.stage_id (scoped by activation_code).
-- % line denominator (O11_ODC_CUSTOMERS) = monthly count of O11/ODC customers (same as q13).
-- NOTE: active_elements uses each app's CURRENT max revision applied to all months, so historical
--   months are approximate (they drift as apps publish new revisions).
-- NOTE: the customer filter is POINT-IN-TIME -- is_customer_policy is evaluated for the same month
--   the usage was observed, not from a single current snapshot, so a customer who churned still
--   counts in the months they were a customer.
WITH cust AS (
  SELECT DISTINCT company_sfdc_id, DATE_TRUNC('month', month_dt) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
),
max_rev AS (
  SELECT APPLICATIONID, TENANTID, MAX(EVENT_REVISION) AS max_revision
  FROM TELEMETRYANALYTICS.ODC_METRIC.APPREVISIONPUBLICELEMENT GROUP BY 1, 2
),
active_elements AS (
  SELECT app.APPLICATIONID, app.TENANTID, app.EVENT_ELEMENTKEY
  FROM TELEMETRYANALYTICS.ODC_METRIC.APPREVISIONPUBLICELEMENT app
  JOIN max_rev mr ON app.APPLICATIONID = mr.APPLICATIONID AND app.TENANTID = mr.TENANTID
                 AND app.EVENT_REVISION = mr.max_revision
  WHERE app.EVENT_ELEMENTTYPE = 'ServerEntity'
),
usage_entity_ids AS (
  SELECT f.VALUE::STRING AS entity_id, ec.TENANTID, ec.ENVIRONMENTID,
         DATE_TRUNC('month', TRY_TO_TIMESTAMP(ec.event_metricdate)) AS month
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT ec,
       LATERAL FLATTEN(input => PARSE_JSON(ec.EVENT_ENTITYIDS)) f
  WHERE ec.event_provider ILIKE 'o11%'
),
app_usage AS (
  SELECT DISTINCT u.month, u.TENANTID, u.ENVIRONMENTID, a.APPLICATIONID
  FROM usage_entity_ids u
  JOIN active_elements a ON u.entity_id = a.EVENT_ELEMENTKEY AND u.TENANTID = a.TENANTID
),
live AS (
  SELECT DISTINCT APPLICATIONID, TENANTID, ENVIRONMENTID,
         DATE_TRUNC('month', TRY_TO_TIMESTAMP(eventdatetime)) AS month
  FROM TELEMETRYANALYTICS.ODC_METRIC.AOUSAGEAPPREVISION
),
mapped AS (
  SELECT au.month, au.APPLICATIONID, odc.company_sfdc_id, e.environment_purpose
  FROM app_usage au
  INNER JOIN live l ON l.APPLICATIONID = au.APPLICATIONID AND l.TENANTID = au.TENANTID
                   AND l.ENVIRONMENTID = au.ENVIRONMENTID AND l.month = au.month
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc ON odc.tenant_id = au.TENANTID
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT e
    ON au.ENVIRONMENTID = e.stage_id AND e.activation_code = odc.activation_code
    AND e.is_current AND e.is_active AND e.is_licensed AND NOT e.is_deleted
  WHERE odc.is_current AND odc.is_active
),
stage_counts AS (
  SELECT m.month,
    COUNT(DISTINCT CASE WHEN environment_purpose='development' THEN m.company_sfdc_id END) AS dev_customers,
    COUNT(DISTINCT CASE WHEN environment_purpose='production'  THEN m.company_sfdc_id END) AS prod_customers,
    COUNT(DISTINCT CASE WHEN environment_purpose='development' THEN m.APPLICATIONID END)   AS dev_apps,
    COUNT(DISTINCT CASE WHEN environment_purpose='production'  THEN m.APPLICATIONID END)   AS prod_apps
  FROM mapped m
  INNER JOIN cust ON cust.company_sfdc_id = m.company_sfdc_id AND cust.month = m.month
  GROUP BY 1
),
o11_odc AS (
  SELECT DATE_TRUNC('month', month_dt) AS month,
    COUNT(DISTINCT CASE WHEN usage_deployment_option='O11/ODC' THEN company_sfdc_id END) AS o11_odc_customers
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO WHERE is_customer_policy GROUP BY 1
)
SELECT
  s.month             AS MONTH,
  s.dev_customers     AS DEV_CUSTOMERS,
  s.prod_customers    AS PROD_CUSTOMERS,
  s.dev_apps          AS DEV_APPS,
  s.prod_apps         AS PROD_APPS,
  o.o11_odc_customers AS O11_ODC_CUSTOMERS
FROM stage_counts s
INNER JOIN o11_odc o ON o.month = s.month
WHERE s.month >= DATEADD('month', -12, DATE_TRUNC('month', CURRENT_DATE))
ORDER BY s.month DESC
