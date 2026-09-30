-- Data Interoperability Success Metrics -- Task 2 (multiple O11 infrastructures / distinct
-- activation codes), stage (a) TAM, monthly trend: # of O11/ODC customers holding >=2 distinct
-- O11 activation codes (enterprise infrastructures) AS OF each month-end.
--
-- COHORT = usage_deployment_option = 'O11/ODC' only (the hybrid bucket) -- ODC-only customers
-- (usage_deployment_option = 'ODC', no active O11 usage) and pure-O11 customers are excluded.
--
-- Unlike Task 1(a) (proxied, current-snapshot-only pipeline count -- see q26), this stage is a
-- GENUINE point-in-time reconstruction: CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE is a real SCD2
-- history table (DATE_FROM / DATE_TO, current rows sentinel to 2999-12-31), so we can ask "how
-- many distinct O11 activation codes did this company hold as of month-end M" directly, without
-- backfilling today's state onto the past.
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
  -- every O11 activation code the company held AS OF each month-end (real historization, not a
  -- current-snapshot backfill)
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
)
SELECT
  o.month AS MONTH,
  COUNT(DISTINCT CASE WHEN ic.n_codes >= 2 THEN o.company_sfdc_id END) AS TAM_CUSTOMERS,
  COUNT(DISTINCT o.company_sfdc_id) AS O11_ODC_CUSTOMERS
FROM o11_odc_month o
LEFT JOIN infra_count ic ON ic.month = o.month AND ic.company_sfdc_id = o.company_sfdc_id
GROUP BY 1
ORDER BY 1
