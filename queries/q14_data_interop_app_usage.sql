-- Data InterOperability: customers/apps whose apps CONSUME an O11 Data Fabric connection,
-- split by ODC stage (development / non-production / production).
--
-- WHAT COUNTS AS "AN APP USING A CONNECTION" -- the key modelling point:
--   In ODC a Data Fabric connection is itself an application (AOUSAGEAPPREVISION
--   event_type='ExternalConnection'), and IT is what PUBLISHES the ServerEntity elements.
--   So matching a connection's EVENT_ENTITYIDS against APPREVISIONPUBLICELEMENT lands back on
--   the connector, not on a business app (verified: 100% of such matches are ExternalConnection).
--   The consuming apps sit one hop further out and are found through
--   APPREVISIONREFERENCEDELEMENT, where event_producerapplicationtype='ExternalConnection':
--
--     connection usage (EVENT_ENTITYIDS)
--        -> APPREVISIONREFERENCEDELEMENT.event_elementkey   (same entity key)
--        -> APPREVISIONREFERENCEDELEMENT.applicationid      = the consuming app
--
--   Linking on the element key (rather than via the producer app's revision) keeps the join
--   direct: EVENT_REVISION on the referencing row is the CONSUMER's revision, which is not
--   comparable to the connection's own revision counter.
--
-- REVISION-ACCURATE: an app is credited only for the months in which the revision that
--   references the entity was actually the live one (app_rev_window), rather than applying each
--   app's current newest revision to all history.
-- ENVIRONMENT-ACCURATE: the app must be running in the SAME environment the connection is used
--   in; environment comes from AOUSAGEAPPREVISION, not from the connection row alone.
-- MONTH-END POSITION: matches q13 -- the month's closing day of connection telemetry.
-- NOTE: the customer filter is POINT-IN-TIME (is_customer_policy for that month).
-- NOTE: event_metricdate / metric day = delivery timestamp - 1; both sides use the metric day.
-- NOTE: built-in apps are excluded (event_isbuiltin = FALSE).
-- NOTE: AI Agents (AOUSAGEAPPREVISION event_type='Agent') consume Data Fabric entities the same
--   way applications do, so they are reported as their OWN series rather than folded into the
--   app counts. *_APPS and *_AGENTS are disjoint; add them for the all-consumers total.
WITH cust AS (
  SELECT DISTINCT company_sfdc_id, DATE_TRUNC('month', month_dt) AS month
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE is_customer_policy
),
-- the day-range each (app, tenant, environment, revision) was the live revision.
-- event_type is carried through so AI Agents can be reported as their own series.
app_rev_window AS (
  SELECT applicationid, tenantid, environmentid, event_revision, event_type,
         MIN(DATEADD('day', -1, TRY_TO_TIMESTAMP(eventdatetime)::date)) AS from_day,
         MAX(DATEADD('day', -1, TRY_TO_TIMESTAMP(eventdatetime)::date)) AS to_day
  FROM TELEMETRYANALYTICS.ODC_METRIC.AOUSAGEAPPREVISION
  WHERE event_isbuiltin = FALSE
  GROUP BY 1,2,3,4,5
),
-- elements each app revision references FROM an external connection
consumer_refs AS (
  SELECT DISTINCT applicationid, tenantid, event_revision, event_elementkey
  FROM TELEMETRYANALYTICS.ODC_METRIC.APPREVISIONREFERENCEDELEMENT
  WHERE event_producerapplicationtype = 'ExternalConnection'
),
-- entities each O11 connection exposes, per day / tenant / environment
usage AS (
  SELECT TRY_TO_DATE(ec.event_metricdate) AS day,
         f.value::string AS entity_id, ec.tenantid, ec.environmentid
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT ec,
       LATERAL FLATTEN(input => PARSE_JSON(ec.event_entityids)) f
  WHERE ec.event_provider ILIKE 'o11%'
    AND TRY_TO_DATE(ec.event_metricdate) >= DATEADD('month', -12, CURRENT_DATE)
),
-- month-end position: the last day in each month that reported connection telemetry
usage_month_end AS (
  SELECT * FROM usage
  QUALIFY day = MAX(day) OVER (PARTITION BY DATE_TRUNC('month', day))
),
app_conn AS (
  SELECT DISTINCT DATE_TRUNC('month', u.day) AS month,
         u.tenantid, u.environmentid, c.applicationid,
         COALESCE(w.event_type, 'Unknown') AS app_kind
  FROM usage_month_end u
  JOIN consumer_refs c
    ON c.event_elementkey = u.entity_id
   AND c.tenantid = u.tenantid
  JOIN app_rev_window w
    ON w.applicationid = c.applicationid
   AND w.tenantid = c.tenantid
   AND w.event_revision = c.event_revision
   AND w.environmentid = u.environmentid
   AND u.day BETWEEN w.from_day AND w.to_day
),
mapped AS (
  SELECT a.month, a.applicationid, a.app_kind, odc.company_sfdc_id, e.environment_purpose
  FROM app_conn a
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc
    ON odc.tenant_id = a.tenantid AND odc.is_current AND odc.is_active
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT e
    ON a.environmentid = e.stage_id AND e.activation_code = odc.activation_code
   AND e.is_current AND e.is_active
),
stage_counts AS (
  SELECT m.month,
    COUNT(DISTINCT CASE WHEN environment_purpose='development'    THEN m.company_sfdc_id END) AS dev_customers,
    COUNT(DISTINCT CASE WHEN environment_purpose='non-production' THEN m.company_sfdc_id END) AS nonprod_customers,
    COUNT(DISTINCT CASE WHEN environment_purpose='production'     THEN m.company_sfdc_id END) AS prod_customers,
    -- apps and agents are DISJOINT: an AI Agent never counts in the app columns
    COUNT(DISTINCT CASE WHEN environment_purpose='development'    AND m.app_kind <> 'Agent' THEN m.applicationid END) AS dev_apps,
    COUNT(DISTINCT CASE WHEN environment_purpose='non-production' AND m.app_kind <> 'Agent' THEN m.applicationid END) AS nonprod_apps,
    COUNT(DISTINCT CASE WHEN environment_purpose='production'     AND m.app_kind <> 'Agent' THEN m.applicationid END) AS prod_apps,
    COUNT(DISTINCT CASE WHEN environment_purpose='development'    AND m.app_kind =  'Agent' THEN m.applicationid END) AS dev_agents,
    COUNT(DISTINCT CASE WHEN environment_purpose='non-production' AND m.app_kind =  'Agent' THEN m.applicationid END) AS nonprod_agents,
    COUNT(DISTINCT CASE WHEN environment_purpose='production'     AND m.app_kind =  'Agent' THEN m.applicationid END) AS prod_agents
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
  s.nonprod_customers AS NONPROD_CUSTOMERS,
  s.prod_customers    AS PROD_CUSTOMERS,
  s.dev_apps          AS DEV_APPS,
  s.nonprod_apps      AS NONPROD_APPS,
  s.prod_apps         AS PROD_APPS,
  s.dev_agents        AS DEV_AGENTS,
  s.nonprod_agents    AS NONPROD_AGENTS,
  s.prod_agents       AS PROD_AGENTS,
  o.o11_odc_customers AS O11_ODC_CUSTOMERS
FROM stage_counts s
INNER JOIN o11_odc o ON o.month = s.month
ORDER BY s.month DESC
