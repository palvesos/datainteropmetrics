# Tables

## CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
- **Purpose:** monthly customer snapshot (deployment, ARR, interop flags).
- **Grain:** one row per company per `MONTH_DT`. ~103 months of history.
- **Key columns:** `COMPANY_SFDC_ID`, `COMPANY_NAME`, `MONTH_DT`, `SEGMENT`,
  `ARR_EUR`, `USAGE_DEPLOYMENT_OPTION` ('O11'|'ODC'|'O11/ODC'),
  `IS_CURRENT_CUSTOMER`, `IS_CUSTOMER_POLICY`, `IS_LAST_MONTH_REPORTED`,
  `IS_INTEROPERABILITY`, `HAS_SKU_INTEROPERABILITY`.
- **Gotcha:** NEVER query without a `MONTH_DT` filter — you sum all 103 months
  (188,715 rows for 4,259 companies). Use the current-customer filter.

## TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT
- **Purpose:** daily Data Fabric external-DB connection telemetry.
- **Grain:** one row per tenant × environment × provider × day.
- **Key columns:** `event_sent` (ts), `event_provider` (`o11cloud_mssql`,
  `o11cloud_oracle`, `o11selfhosted_mssql`, `o11selfhosted_oracle`), `tenant`,
  `environment_id`, `metric_value` (# connections).
- **Gotcha:** join to infrastructure via SCD2 date range; validate SUM(metric_value)
  against the raw table to ensure the join didn't fan out.

## CANONICAL.CUSTOMERSUCCESS.ODCAGENT
- **Purpose:** monthly ODC agent usage per customer/tenant.
- **Grain:** one row per company × tenant × `DATE_MONTH`.
- **Key columns:** `COMPANY_SFDC_ID`, `TENANT_ID`, `DATE_MONTH`, `N_AGENTS`,
  `N_EXECUTIONS`.

## CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE
- **Purpose:** infra config (SCD2). **Grain:** one current row per infra when
  `is_current AND is_active`. **Key:** `tenant_id`, `company_sfdc_id`,
  `activation_code`, `architecture_type`, `infrastructure_type`,
  `infrastructure_status`, `date_from`, `date_to`, `is_active`, `is_current`.

## CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT
- **Purpose:** environment metadata (SCD2). **Grain:** one row per environment
  (stage/purpose) per version — ~5 per infra. **Key:** `environment_id`,
  `activation_code`, `stage_id`, `environment_purpose`, `is_current`,
  `is_active`, `is_deleted`, `is_licensed`, `cloud_provider`.
- **Gotcha:** joining infra→environment is one-to-many; never expect per-infra grain.

## CANONICAL.CORE.COMPANY
- **Purpose:** company master. **Key:** `company_id`, `company_sfdc_id`,
  `company_name`, `type` ('customer'|'partner'|'licensee'), `region`, `geo`.

## CANONICAL.CUSTOMERSUCCESS.TENANTMETADATA
- **Key:** `tenant_id`, `ODC_RING`.

## CANONICAL.CUSTOMERSUCCESS.PLATFORMUTILIZATIONWEEKLY
- **Purpose:** weekly platform usage. **Key:** `infrastructure_id`,
  `environment_id`, `date_id`, `user_company_id`, `ao_usage`,
  `distinct_visitors`, `internal_users_count`, `external_users_count`.

## v1 tables (unchanged)
- `MONTHLYCOMPANYPRODUCTEDITIONCATEGORY` (q1/q2), `MONTHLYCOMPANYINFRAPRODUCTEDITIONCATEGORY` (q3),
  `PLATFORMUTILIZATIONDAILYINFRASTRUCTUREAGG` (q4), `PLATFORMUTILIZATIONMONTHLYINFRASTRUCTUREAGG_TOTAL` (q5).
  These aggregate with `COUNT(DISTINCT … )` per period and are not month-inflated.
