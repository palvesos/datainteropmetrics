-- Data Interoperability Success Metrics -- Task 2, stage (c) Validated use case, monthly trend
-- -- ALTERNATE SIGNAL, built from O11 Lifetime's new "Unification" handshake telemetry instead
-- of the ODC-side INTEROPERABILITY_RELATED_ACTIVATION_CODE field (see q32 for that version).
--
-- Of the Task 2(b) Reach cohort, split by how many distinct O11 activation codes
-- (ENV_ACTIVATION_CODE) they handshook with that month -- exactly 1 vs 2+ (2+ = the ODC tenant
-- handshook with 2+ different O11 Lifetime instances, a direct signal of cross-infrastructure
-- interop rather than the indirect, tenant-level code inferred in q32). Unresolved = Reach
-- customers with no matching handshake event that month at all.
--
-- >>> WHY THIS IS A SEPARATE QUERY, NOT A REPLACEMENT FOR q32 <<<
--   TELEMETRYANALYTICS.METRICS.LIFETIME_UNIFICATION is a BRAND NEW telemetry stream: as of this
--   writing it holds exactly 8 rows, all from 2026-09-28/29 ("Handshake_v1" -- a v1 event type),
--   and none of its DOMAIN_ODCTENANTID values currently resolve to a real company in
--   CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE (likely internal/test traffic from the feature's
--   early rollout, or a sync lag). This query will read as empty/near-empty for months until the
--   feature matures and starts covering real customer tenants -- that is expected, not a bug.
--   Once it does, this is the BETTER signal: event-driven and per-handshake, vs. q32's static,
--   tenant-level field.
--
-- MONTH SEMANTICS DIFFER FROM q32: LIFETIME_UNIFICATION logs discrete handshake EVENTS (not a
--   daily gauge), so a company counts for a month if it had ANY qualifying handshake sometime
--   that month -- there is no "month-end position" here, unlike the day-level connector-count
--   tables used elsewhere in this report.
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
unification_month AS (
  SELECT
    DATE_TRUNC('month', u.event_date) AS month,
    odc.company_sfdc_id,
    u.env_activation_code
  FROM TELEMETRYANALYTICS.METRICS.LIFETIME_UNIFICATION u
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc
    ON odc.tenant_id = u.domain_odctenantid
  WHERE odc.is_current AND odc.is_active
    AND u.env_activation_code IS NOT NULL
    AND DATE_TRUNC('month', u.event_date) >= DATEADD('month', -12, CURRENT_DATE)
),
code_count AS (
  SELECT month, company_sfdc_id, COUNT(DISTINCT env_activation_code) AS n_codes_handshaked
  FROM unification_month
  GROUP BY 1, 2
)
SELECT
  r.month AS MONTH,
  COUNT(DISTINCT CASE WHEN cc.n_codes_handshaked = 1 THEN r.company_sfdc_id END) AS ONE_INFRA_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN cc.n_codes_handshaked >= 2 THEN r.company_sfdc_id END) AS MULTI_INFRA_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN cc.company_sfdc_id IS NULL THEN r.company_sfdc_id END) AS UNRESOLVED_CUSTOMERS,
  COUNT(DISTINCT r.company_sfdc_id) AS REACH_CUSTOMERS
FROM reach_month r
LEFT JOIN code_count cc ON cc.month = r.month AND cc.company_sfdc_id = r.company_sfdc_id
GROUP BY 1
ORDER BY 1
