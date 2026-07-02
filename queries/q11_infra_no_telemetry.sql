-- Data context: PLATFORMUTILIZATIONWEEKLY, INFRASTRUCTURE, ENVIRONMENT, COMPANY, CUSTOMERUNIFIEDINFO.
WITH o11_infra_without_telemetry AS (
  SELECT DISTINCT activation_code
  FROM (
    SELECT DISTINCT
      i.activation_code,
      base.ao_usage, base.distinct_visitors,
      base.internal_users_count, base.external_users_count
    FROM canonical.customersuccess.platformutilizationweekly base
      INNER JOIN canonical.core.date d_date  ON base.date_id = d_date.date_key_nr
      INNER JOIN canonical.customersuccess.infrastructure i ON base.infrastructure_id = i.infrastructure_id
      INNER JOIN canonical.customersuccess.environment e   ON base.environment_id = e.environment_id
      INNER JOIN canonical.core.company d_account          ON base.user_company_id = d_account.company_id
    WHERE d_account.type IN ('customer', 'licensee')
      AND TO_DATE(d_date.day_date) >= DATEADD(week, -1, CURRENT_DATE())
      AND e.environment_purpose = 'production'
      AND i.infrastructure_type = 'enterprise'
      AND i.infrastructure_status = 'active'
  )
  WHERE ao_usage IS NULL AND distinct_visitors IS NULL
    AND internal_users_count IS NULL AND external_users_count IS NULL
)
SELECT DISTINCT
  i.activation_code        AS ACTIVATION_CODE,
  i.company_sfdc_id        AS COMPANY_SFDC_ID,
  c.company_name           AS COMPANY_NAME,
  i.architecture_type      AS ARCHITECTURE_TYPE,
  i.infrastructure_status  AS INFRASTRUCTURE_STATUS,
  c.usage_deployment_option AS USAGE_DEPLOYMENT_OPTION
FROM o11_infra_without_telemetry t
INNER JOIN canonical.customersuccess.infrastructure i
  ON t.activation_code = i.activation_code AND i.is_current AND i.is_active
INNER JOIN canonical.customersuccess.customerunifiedinfo c
  ON i.company_sfdc_id = c.company_sfdc_id
  AND c.is_customer_policy AND c.is_last_month_reported
ORDER BY c.company_name
