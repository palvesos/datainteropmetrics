-- Data InterOperability: customers with O11 Data Fabric connections by ODC stage (dev/prod).
-- Bars = distinct customers holding an O11 Data Fabric connection AT MONTH END, split by ODC stage.
-- MONTH-END POSITION, not month-wide activity: a customer who connected on the 3rd and
--   disconnected on the 20th does NOT count for that month. This matches how Analytics reports
--   the same metric. Counting anyone active at any point in the month instead would read higher.
-- Stages are development / non-production / production -- all three are reported; a customer can
--   appear in more than one, so the columns do not sum to a distinct customer total.
-- ODC stage bridge: EXTERNALCONNECTIONCOUNT.environment_id = ENVIRONMENT.stage_id (scoped by activation_code).
--   (canonical ENVIRONMENT.environment_id is numeric/O11; stage_id carries the ODC connection env UUID.)
-- % line denominator = monthly count of customers whose deployment is O11/ODC (cross-platform base).
-- NOTE: metric_day = YEAR + DATE_VALUE (day-of-year) = the day the gauge DESCRIBES; event_sent is
--   the delivery day (always metric_day+1 for D rows), which pushed each month's last day into the
--   next month. Months below are bucketed on metric_day.
-- NOTE: the customer filter is POINT-IN-TIME -- is_customer_policy is evaluated for the same month
--   the connection was observed, not from a single current snapshot. A customer who churned still
--   counts in the months they were a customer, so historical months stay stable as time passes.
WITH cust AS (
  SELECT DISTINCT company_sfdc_id, DATE_TRUNC('month', month_dt) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
),
conn_daily AS (
  SELECT
    DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1)) AS day,
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
    -- daily-grain rows only; the table also carries W (ISO week) / M (month) re-emissions
    AND m.type = 'D'
    AND m.metric_value > 0
    AND DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1))
        >= DATEADD('month', -12, CURRENT_DATE)
),
conn AS (
  -- Collapse each month to its closing day. MAX(day) per month is the last day that actually
  -- reported: the month's last calendar day for completed months, and the latest day so far for
  -- the in-progress month. Using the last day WITH DATA (rather than LAST_DAY()) means a missing
  -- month-end feed degrades to the nearest prior day instead of emptying the whole month.
  SELECT DATE_TRUNC('month', day) AS month, company_sfdc_id, environment_purpose
  FROM conn_daily
  QUALIFY day = MAX(day) OVER (PARTITION BY DATE_TRUNC('month', day))
),
stage_counts AS (
  SELECT c.month,
    COUNT(DISTINCT CASE WHEN c.environment_purpose='development'    THEN c.company_sfdc_id END) AS dev_customers,
    COUNT(DISTINCT CASE WHEN c.environment_purpose='non-production' THEN c.company_sfdc_id END) AS nonprod_customers,
    COUNT(DISTINCT CASE WHEN c.environment_purpose='production'     THEN c.company_sfdc_id END) AS prod_customers
  FROM conn c
  INNER JOIN cust ON cust.company_sfdc_id = c.company_sfdc_id AND cust.month = c.month
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
  s.nonprod_customers  AS NONPROD_CUSTOMERS,
  s.prod_customers     AS PROD_CUSTOMERS,
  o.o11_odc_customers  AS O11_ODC_CUSTOMERS
FROM stage_counts s
INNER JOIN o11_odc o ON o.month = s.month
ORDER BY s.month DESC
