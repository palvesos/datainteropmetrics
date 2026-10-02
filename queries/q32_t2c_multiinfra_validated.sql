-- Data Interoperability Success Metrics -- Task 2, stage (c) Validated use case, monthly trend:
-- of the Task 2(b) Reach cohort, split by how many distinct O11 infrastructures the customer has
-- linked to its ODC tenant(s) at month end -- exactly 1 vs 2+ (2+ = different O11 infrastructures,
-- not just different environments within the same one; that's Task 1, see q28's caveat). A third
-- bucket (Unresolved) covers Reach customers with no live O11 infrastructure configuration event.
--
-- O11 INFRA SIGNAL: TELEMETRYANALYTICS.ODC_METRIC.O11INFRASTRUCTURECONFIGURATION -- the O11 Bridge
--   Service's created/updated/deleted event for each ODC tenant <-> O11 infra link, the setup step
--   that must exist before any O11 Data Fabric connector can be configured. Each O11 infra has a
--   unique LifeTime URL, so # distinct live (normalized) EVENT_LIFETIMEURLs per company = # O11
--   infras linked. State at month end = latest event per (tenant, infrastructure key) up to
--   LAST_DAY(month), live unless that event is 'deleted'. Internal pre-prod `pp-*` URLs excluded.
--   Replaces the earlier INTEROPERABILITY_RELATED_ACTIVATION_CODE signal, which records the O11
--   infra a tenant was PROVISIONED against, not what it connects to.
--
-- CAVEATS:
--   * Events start 2026-08-27 with NO BACKFILL: links created before then only appear once next
--     touched, so Unresolved is inflated early on and months before the first event are dropped.
--   * A linked infra is a prerequisite for, not proof of, a connector on it: the connection
--     telemetry (EXTERNALCONNECTIONCOUNT) carries no infra key, so "2+ linked + 1 live connection"
--     counts as validated. See docs/data-context/tables.md (O11INFRASTRUCTURECONFIGURATION).
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
    AND i.infrastructure_type = 'enterprise'   -- freemium/trial out of scope, see data-context
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
infra_cfg_ev AS (
  SELECT DISTINCT
    messageid,
    tenantid,
    event_infrastructurekey AS infra_key,
    LOWER(RTRIM(event_lifetimeurl, '/')) AS lifetime_url,
    event_operationtype AS op,
    TRY_TO_TIMESTAMP(eventdatetime) AS ts
  FROM TELEMETRYANALYTICS.ODC_METRIC.O11INFRASTRUCTURECONFIGURATION
  WHERE event_lifetimeurl IS NOT NULL
    AND LOWER(event_lifetimeurl) NOT LIKE 'https://pp-%'
),
cfg_months AS (
  SELECT month FROM month_series
  WHERE LAST_DAY(month) >= (SELECT DATE_TRUNC('month', MIN(ts)) FROM infra_cfg_ev)
),
infra_cfg_asof AS (
  SELECT m.month, e.tenantid, e.infra_key, e.lifetime_url, e.op
  FROM cfg_months m
  JOIN infra_cfg_ev e ON e.ts < DATEADD('day', 1, LAST_DAY(m.month))
  QUALIFY ROW_NUMBER() OVER (PARTITION BY m.month, e.tenantid, e.infra_key ORDER BY e.ts DESC) = 1
),
linked_count AS (
  SELECT a.month, odc.company_sfdc_id, COUNT(DISTINCT a.lifetime_url) AS n_linked_infras
  FROM infra_cfg_asof a
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE odc
    ON odc.tenant_id = a.tenantid AND odc.is_current AND odc.is_active
  WHERE a.op <> 'deleted'
  GROUP BY 1, 2
)
SELECT
  r.month AS MONTH,
  COUNT(DISTINCT CASE WHEN cc.n_linked_infras = 1 THEN r.company_sfdc_id END) AS ONE_INFRA_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN cc.n_linked_infras >= 2 THEN r.company_sfdc_id END) AS MULTI_INFRA_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN cc.company_sfdc_id IS NULL THEN r.company_sfdc_id END) AS UNRESOLVED_CUSTOMERS,
  COUNT(DISTINCT r.company_sfdc_id) AS REACH_CUSTOMERS
FROM reach_month r
JOIN cfg_months cm ON cm.month = r.month
LEFT JOIN linked_count cc ON cc.month = r.month AND cc.company_sfdc_id = r.company_sfdc_id
GROUP BY 1
ORDER BY 1
