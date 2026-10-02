-- Task 1 (a) TAM: # of O11 Multi-Pipeline customers in Interoperability
--   "Count of O11/ODC customers whose O11 infra has >=2 parallel environment packs (pipelines)"
--
-- COHORT: O11/ODC customers = CUSTOMERUNIFIEDINFO.usage_deployment_option='O11/ODC' for the
--   latest month (same definition q13/q14 use for their % denominator), point-in-time.
--
-- >>> KEY MODELLING CAVEAT -- "pipeline" is INFERRED, not read directly <<<
--   The O11 cloud provisioning DB (CLOUDFRAMEWORKPRODUCTION.NOW) stores the ENVIRONMENTS of an
--   infrastructure (OSUSR_YDY_INFRASTRUCTURE -> ..SLOT -> ..ENVIRONMENT) but NOT the deployment
--   PATHS between them. Which environment promotes to which (Test1->QA1->PRD1 vs Test2->QA2->PRD2)
--   is configured in the customer's own LifeTime server and is not replicated here -- there is no
--   pipeline/pack id, parent-slot, or path column anywhere in the schema (checked: SLOT carries
--   only SLOTTYPEID / SLOTNAME / ORDER, and ORDER is a flat display sequence across ALL slots of
--   the infra, not a per-pipeline position).
--   PROXY USED: a pipeline terminates in its own Production environment, so
--       # parallel pipelines := # of live Production slots (SLOTTYPEID='3') in the infrastructure.
--   Verified against real infra 175279, whose slots read as 4 clean parallel paths, each ending in
--   its own production env (Production US East / Production EU Frankfurt / US Wallet Prod /
--   Send2Corrections Prod). The proxy OVERCOUNTS where a single pipeline has several production
--   environments for non-pipeline reasons (multi-region actives, DR/failover pairs -- note
--   "Production US (Failover)" rows do exist) and UNDERCOUNTS a parallel path that stops before
--   production (Test2->QA2 with no PRD2).
--
-- SLOTTYPEID (YDY module): 1=Development, 2=Lifetime, 3=Production, 4=Non-Production.
--   This matches the OSUSR_YDY_ENVIRONMENTTYPE lookup, and is the REVERSE of 3/4 in the 9PN
--   module's OSUSR_9PN_INFRASTRUCTUREENVIRONMENT.ENVIRONMENTTYPEID (1=Dev, 2=Lifetime,
--   3=Non-Production, 4=Production). Do not mix the two conventions.
--
-- LIVE SLOT FILTER: INFRASTRUCTURESLOTSTATEID='6' -- 5,214 of 5,226 such slots have a started
--   environment, vs 1 of 11,720 for state '5'. State 5 rows are decommissioned/never-started
--   leftovers (old failover pairs, "production environment # 2" placeholders) and would badly
--   inflate the pipeline count if included.
--
-- COVERAGE: customer -> O11 infra is matched on activation_code
--   (CANONICAL...INFRASTRUCTURE.product_family='O11' -> OSUSR_YDY_INFRASTRUCTURE.ACTIVATIONCODE).
--   This resolves for 847/1,148 companies on source='PROV' (74%) and 1,864/4,030 on source='LIC'
--   (46%). Unresolved customers cannot be classified and are reported separately below rather
--   than being silently counted as single-pipeline.
WITH latest_month AS (
  SELECT MAX(DATE_TRUNC('month', month_dt)) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
),
cohort AS (
  -- O11/ODC customers at the latest month
  SELECT DISTINCT c.company_sfdc_id
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO c, latest_month lm
  WHERE c.is_customer_policy
    AND c.usage_deployment_option = 'O11/ODC'
    AND DATE_TRUNC('month', c.month_dt) = lm.month
),
o11_codes AS (
  -- every O11 activation code the customer holds (both LIC and PROV sourced)
  SELECT DISTINCT company_sfdc_id, activation_code
  FROM CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE
  WHERE is_current AND is_active
    AND product_family = 'O11'
    AND infrastructure_type = 'enterprise'   -- freemium/trial out of scope, see data-context
    AND company_sfdc_id IS NOT NULL
    AND activation_code IS NOT NULL
),
live_slots AS (
  -- live environments of each O11 infrastructure, by slot type
  SELECT i.activationcode, s.slottypeid
  FROM CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_INFRASTRUCTURE i
  JOIN CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_INFRASTRUCTURESLOT s
    ON s.infrastructureid = i.id
  JOIN CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_ENVIRONMENT e
    ON e.id = s.environmentid
  WHERE i.isdeleted = '0'
    AND e.isdeleted = '0'
    AND s.infrastructureslotstateid = '6'   -- live slot, see header
),
infra_shape AS (
  SELECT activationcode,
         COUNT(CASE WHEN slottypeid = '3' THEN 1 END) AS prod_envs,      -- pipeline proxy
         COUNT(CASE WHEN slottypeid = '4' THEN 1 END) AS nonprod_envs,
         COUNT(CASE WHEN slottypeid = '1' THEN 1 END) AS dev_envs
  FROM live_slots
  GROUP BY 1
),
customer_shape AS (
  SELECT
    ch.company_sfdc_id,
    MAX(sh.prod_envs)                                      AS max_pipelines_in_one_infra,
    COUNT(DISTINCT CASE WHEN sh.activationcode IS NOT NULL
                        THEN oc.activation_code END)       AS resolved_infras
  FROM cohort ch
  LEFT JOIN o11_codes oc ON oc.company_sfdc_id = ch.company_sfdc_id
  LEFT JOIN infra_shape sh ON sh.activationcode = oc.activation_code
  GROUP BY 1
)
SELECT
  CASE
    WHEN resolved_infras = 0                THEN 'unknown - O11 infra not resolvable'
    WHEN max_pipelines_in_one_infra >= 2    THEN 'TAM: multi-pipeline (>=2 prod envs)'
    WHEN max_pipelines_in_one_infra = 1     THEN 'single pipeline'
    ELSE 'resolved but no live production env'
  END                                    AS SEGMENT,
  COUNT(*)                               AS CUSTOMERS,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS PCT_OF_O11_ODC
FROM customer_shape
GROUP BY 1
ORDER BY CUSTOMERS DESC
