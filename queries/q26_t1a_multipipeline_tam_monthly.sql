-- Data Interoperability Success Metrics -- Task 1 (multi-pipeline within one O11 infra), stage
-- (a) TAM, monthly trend: # of O11/ODC customers whose O11 infra has >=2 parallel production
-- environments (pipeline proxy), against the total monthly O11/ODC cohort.
--
-- See q25 (the original point-in-time version of this stage) for the full pipeline-proxy
-- rationale: "pipeline" is INFERRED as the count of live Production slots (SLOTTYPEID='3') in
-- an infrastructure, because the O11 provisioning schema has no pipeline/path identifier at all.
-- q25 also documents customer->O11-infra resolution coverage (~74% PROV-sourced, ~46%
-- LIC-sourced) and the live-slot-state filter (INFRASTRUCTURESLOTSTATEID='6').
--
-- >>> HISTORIZATION CAVEAT -- read before trusting month-over-month movement <<<
--   CLOUDFRAMEWORKPRODUCTION.NOW (the O11 provisioning DB backing the pipeline proxy) is a
--   CURRENT-STATE snapshot only: OSUSR_YDY_INFRASTRUCTURE / ..SLOT / ..ENVIRONMENT carry no
--   valid-from/valid-to history. There is no way to know what a customer's infra shape looked
--   like in a past month. This query applies TODAY's infra shape retroactively to each month's
--   O11/ODC cohort membership (CUSTOMERUNIFIEDINFO, which IS historized). Movement in this
--   trend reflects cohort growth/churn, NOT actual historical changes to pipeline count --
--   a flat line here does not mean "no pipelines were added or removed," it means "we only know
--   today's shape." See the "Data InterOperability Success Metrics" tab's warning banner.
WITH o11_odc_month AS (
  SELECT DISTINCT company_sfdc_id, DATE_TRUNC('month', month_dt) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
    AND usage_deployment_option = 'O11/ODC'
    AND DATE_TRUNC('month', month_dt) >= DATEADD('month', -12, CURRENT_DATE)
),
o11_codes AS (
  -- every currently active O11 activation code the customer holds (both LIC and PROV sourced)
  SELECT DISTINCT company_sfdc_id, activation_code
  FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE
  WHERE is_current AND is_active
    AND product_family = 'O11'
    AND company_sfdc_id IS NOT NULL
    AND activation_code IS NOT NULL
),
live_slots AS (
  -- live environments of each O11 infrastructure, by slot type (current snapshot)
  SELECT i.activationcode, s.slottypeid
  FROM CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_INFRASTRUCTURE i
  JOIN CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_INFRASTRUCTURESLOT s
    ON s.infrastructureid = i.id
  JOIN CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_ENVIRONMENT e
    ON e.id = s.environmentid
  WHERE i.isdeleted = '0'
    AND e.isdeleted = '0'
    AND s.infrastructureslotstateid = '6'   -- live slot, see q25 header
),
infra_shape AS (
  SELECT activationcode,
         COUNT(CASE WHEN slottypeid = '3' THEN 1 END) AS prod_envs   -- pipeline proxy
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
)
SELECT
  m.month AS MONTH,
  COUNT(DISTINCT CASE WHEN cs.resolved_infras > 0 AND cs.max_pipelines_in_one_infra >= 2
                       THEN m.company_sfdc_id END) AS TAM_CUSTOMERS,
  COUNT(DISTINCT m.company_sfdc_id) AS O11_ODC_CUSTOMERS
FROM o11_odc_month m
LEFT JOIN company_shape cs ON cs.company_sfdc_id = m.company_sfdc_id
GROUP BY 1
ORDER BY 1
