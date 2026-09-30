-- Snapshot (NOT a monthly trend): O11 platform "Lifetime version" (LT release) status for
-- customers with a Data Fabric connection for O11 in DEVELOPMENT -- same customer set as the
-- "Customers with Data Fabric Connections for O11 -- Development" chart (q13, DEV_CUSTOMERS),
-- restricted to the latest reported month.
--
-- ACTIVATION CODE OF THE O11 CONNECTED ENVIRONMENT: the ODC-family
--   CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE row (matched via tenant_id, same as q13's
--   conn_daily) carries INTEROPERABILITY_RELATED_ACTIVATION_CODE -- the REAL O11 activation
--   code the Data Fabric connection points to. Two other candidates were tried and rejected:
--     - the customer's own ODC-style activation_code (used elsewhere for the ENVIRONMENT join)
--       is synthetic to ODC and doesn't exist in the live O11 platform DB at all.
--     - INFRASTRUCTURE(product_family='O11').activation_code (the licensing activation code)
--       only resolves for SOURCE='PROV' rows -- ~25% of O11 companies.
--   INTEROPERABILITY_RELATED_ACTIVATION_CODE does far better: checked against q13's actual
--   Development population (latest month, 189 customers), 152 have it populated and 142 (75%
--   of the whole population) resolve to a real row in CLOUDFRAMEWORKPRODUCTION.NOW.
--
-- ENVIRONMENTTYPEID on OSUSR_9PN_INFRASTRUCTUREENVIRONMENT: empirically verified (from the free
--   text NAME field on real rows) as 1=Development, 2=Lifetime (deployment-manager environment,
--   not a dev/nonprod/prod stage), 3=Non-Production, 4=Production. This CONTRADICTS the LABEL
--   column on the OSUSR_YDY_ENVIRONMENTTYPE lookup table (which claims 3=Production,
--   4=Non-Production) -- that lookup table's LABEL is not trustworthy; the mapping above is the
--   one backed by evidence. We want ENVIRONMENTTYPEID=1 here, matching the Development stage.
--
-- ISDELETED does not mean "not currently live": most rows are historical re-provisioning
--   generations. Per activation_code we keep the freshest Development-type generation
--   (ISDELETED=0 preferred, else highest ID).
--
-- "LIFETIME VERSION" = OSUSR_YDY_PLATFORMVERSION.ISLIFETIME='1' (an official LT/long-term
--   release), joined by exact VERSION string match (100% match rate; the PLATFORMVERSIONID FK
--   is only ~54% populated, so it's not used).
WITH cust AS (
  SELECT DISTINCT company_sfdc_id, DATE_TRUNC('month', month_dt) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
),
conn_daily AS (
  SELECT
    DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1)) AS day,
    odc.company_sfdc_id,
    odc.interoperability_related_activation_code AS o11_activation_code,
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
  -- month-end position, same as q13
  SELECT DATE_TRUNC('month', day) AS month, company_sfdc_id, o11_activation_code, environment_purpose
  FROM conn_daily
  QUALIFY day = MAX(day) OVER (PARTITION BY DATE_TRUNC('month', day))
),
dev_customers AS (
  SELECT DISTINCT c.company_sfdc_id, c.o11_activation_code
  FROM conn c
  INNER JOIN cust ON cust.company_sfdc_id = c.company_sfdc_id AND cust.month = c.month
  WHERE c.environment_purpose = 'development'
    AND c.month = (SELECT MAX(month) FROM conn)
),
raw_env AS (
  SELECT
    ie.activationcode,
    ie.version,
    ROW_NUMBER() OVER (
      PARTITION BY ie.activationcode
      ORDER BY ie.isdeleted ASC, TRY_TO_NUMBER(ie.id) DESC
    ) AS rn
  FROM CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_9PN_INFRASTRUCTUREENVIRONMENT ie
  WHERE ie.environmenttypeid = '1'  -- Development
),
current_dev_env AS (
  SELECT activationcode, version FROM raw_env WHERE rn = 1
),
platform_version AS (
  SELECT version, (islifetime = '1') AS is_lifetime, releasename
  FROM CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_PLATFORMVERSION
)
SELECT
  dc.company_sfdc_id        AS COMPANY_SFDC_ID,
  ce.version                 AS PLATFORM_VERSION,
  pv.is_lifetime               AS IS_LIFETIME_VERSION,
  pv.releasename               AS RELEASE_NAME,
  (ce.version IS NOT NULL)     AS HAS_O11_VERSION_DATA
FROM dev_customers dc
LEFT JOIN current_dev_env ce ON ce.activationcode = dc.o11_activation_code
LEFT JOIN platform_version pv ON pv.version = ce.version
ORDER BY dc.company_sfdc_id
