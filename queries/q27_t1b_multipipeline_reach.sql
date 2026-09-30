-- Data Interoperability Success Metrics -- Task 1, stage (b) Reach, monthly trend: of the
-- Task 1(a) TAM cohort (customers whose O11 infra has >=2 parallel pipelines -- see q26 for the
-- pipeline-proxy and historization caveats), the count with >=1 live O11 Data Fabric connection
-- (o11cloud_mssql) in ANY environment at month end. Baseline connectivity only -- no claim about
-- which pipeline/environment holds the connection.
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
    -- daily-grain rows only; the table also carries W (ISO week) / M (month) re-emissions
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
)
SELECT
  t.month AS MONTH,
  COUNT(DISTINCT r.company_sfdc_id) AS REACH_CUSTOMERS,
  COUNT(DISTINCT t.company_sfdc_id) AS TAM_CUSTOMERS
FROM tam_month t
LEFT JOIN reach_month r ON r.month = t.month AND r.company_sfdc_id = t.company_sfdc_id
GROUP BY 1
ORDER BY 1
