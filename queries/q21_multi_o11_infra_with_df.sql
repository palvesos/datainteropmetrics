-- Data InterOperability: customers that run MORE THAN ONE active O11 enterprise infrastructure
-- (activation code) AND have at least one live O11 Data Fabric connection. Enriched with:
--   NUM_O11_INFRAS        = distinct active O11 enterprise activation codes for the company (>1)
--   NUM_DF_PROVIDERS      = distinct O11 Data Fabric providers with telemetry
--   CURRENT_DF_CONNECTORS = sum of the latest connector-count reading across the company's
--                           tenants/envs/providers (deduped to one reading per day, then the
--                           latest per (tenant, env, provider) series).
-- Co-authored with CoCo.
WITH o11_conn_series AS (
    SELECT
        odc.company_sfdc_id,
        m.tenant, m.environment_id, m.event_provider,
        DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1)) AS d,
        m.metric_value AS mv
    FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT AS m
    INNER JOIN canonical.customersuccess.infrastructure AS odc ON odc.tenant_id = m.TENANT
    LEFT JOIN canonical.customersuccess.environment AS e ON m.environment_id = e.stage_id
    WHERE odc.is_current AND odc.is_active
      AND e.activation_code = odc.activation_code
      AND e.is_current AND e.is_active
      AND m.event_provider ILIKE 'o11%'
      -- daily-grain rows only; the table also carries W (ISO week) / M (month) re-emissions
      AND m.type = 'D'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY m.tenant, m.environment_id, m.event_provider,
        DATEADD('day', m.date_value - 1, DATE_FROM_PARTS(m.year, 1, 1))
        ORDER BY TRY_TO_TIMESTAMP(m.event_sent) DESC) = 1
),
df_latest AS (
    -- latest reading per (tenant, env, provider) series
    SELECT company_sfdc_id, tenant, environment_id, event_provider, mv AS last_val
    FROM o11_conn_series
    QUALIFY ROW_NUMBER() OVER (PARTITION BY tenant, environment_id, event_provider ORDER BY d DESC) = 1
),
df_agg AS (
    SELECT company_sfdc_id,
           COUNT(DISTINCT event_provider) AS num_df_providers,
           SUM(last_val) AS current_df_connectors
    FROM df_latest GROUP BY company_sfdc_id
),
multiple_o11 AS (
    SELECT
        cui.COMPANY_SFDC_ID,
        COUNT(DISTINCT o11.ACTIVATION_CODE) AS num_o11_infras
    FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO AS cui
    INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE AS o11
        ON cui.COMPANY_SFDC_ID = o11.COMPANY_SFDC_ID
    WHERE cui.IS_LAST_MONTH_REPORTED
      AND cui.IS_CUSTOMER_POLICY
      AND o11.IS_ACTIVE AND o11.IS_CURRENT AND NOT o11.IS_DELETED
      AND o11.INFRASTRUCTURE_TYPE = 'enterprise'
    GROUP BY cui.company_name, cui.COMPANY_SFDC_ID
    HAVING COUNT(DISTINCT o11.ACTIVATION_CODE) > 1
)
SELECT
    DISTINCT cui.company_name       AS COMPANY_NAME,
    cui.COMPANY_SFDC_ID             AS COMPANY_SFDC_ID,
    ms.num_o11_infras               AS NUM_O11_INFRAS,
    da.num_df_providers             AS NUM_DF_PROVIDERS,
    da.current_df_connectors        AS CURRENT_DF_CONNECTORS
FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO AS cui
INNER JOIN df_agg AS da ON da.company_sfdc_id = cui.COMPANY_SFDC_ID
INNER JOIN multiple_o11 AS ms ON ms.COMPANY_SFDC_ID = cui.COMPANY_SFDC_ID
WHERE cui.IS_LAST_MONTH_REPORTED
  AND cui.IS_CUSTOMER_POLICY
ORDER BY CURRENT_DF_CONNECTORS DESC, NUM_O11_INFRAS DESC;
