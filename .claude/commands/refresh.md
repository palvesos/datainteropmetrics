# Refresh Data Interoperability KPI Report

Fetch fresh data from Snowflake and regenerate the HTML report.

## Steps

Run these steps in order. If any step fails (non-zero exit code or exception), stop and print the error.

### 1. Run the 23 queries and save as Parquet

For each query, run the `snow sql` command to capture JSON output to a temp file, then parse it into a pandas DataFrame, convert date/boolean/numeric columns, and save to `data/`. Guard the conversions so empty result sets don't fail.

**Important:** snow CLI serializes Snowflake `DECIMAL`/`NUMERIC` columns as JSON **strings** (to preserve precision). Any column that should be a float or int must be explicitly coerced with `pd.to_numeric()` after parsing, otherwise downstream arithmetic in `render.py` will raise `TypeError: unsupported operand type(s) for -: 'str' and 'str'`.

General pattern (use the per-query values from the table below):

```bash
# Capture
uvx --python 3.13 --from snowflake-cli snow sql --filename queries/<QN_FILE>.sql --format json --connection os > /tmp/<QN>.json
```

```python
# Parse & save (replace placeholders with per-query values from the table)
import json, pandas as pd
with open('/tmp/<QN>.json') as f:
    rows = json.load(f)
df = pd.DataFrame(rows)
# Date column conversion — guarded so empty results don't KeyError
for col in [<DATE_COLS>]:
    if not df.empty and col in df.columns:
        df[col] = pd.to_datetime(df[col])
# Boolean column normalization (q6 only)
for col in [<BOOL_COLS>]:
    if col in df.columns:
        df[col] = df[col].map({'TRUE': True, 'FALSE': False, True: True, False: False, 1: True, 0: False})
# Numeric column coercion — Snowflake DECIMAL/NUMERIC arrives as JSON strings
for col in [<NUM_COLS>]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col])
df.to_parquet('data/<QN_FILE>.parquet', index=False)
```

Per-query values:

| Key | SQL file | Output Parquet | Date cols | Bool cols | Numeric cols |
|-----|----------|----------------|-----------|-----------|--------------|
| q1 | `queries/q1_adoption_trend.sql` | `data/q1_adoption_trend.parquet` | `'MONTH_START'` | — | `'INTEROP_CUSTOMERS'`, `'SKU_INTEROP_CUSTOMERS'`, `'TOTAL_CUSTOMERS'`, `'ADOPTION_PCT'` |
| q2 | `queries/q2_by_product_family.sql` | `data/q2_by_product_family.parquet` | — | — | `'TOTAL_CUSTOMERS'`, `'INTEROP_ACTIVE'`, `'HAS_SKU_INTEROP'` |
| q3 | `queries/q3_by_arch_type.sql` | `data/q3_by_arch_type.parquet` | — | — | `'COMPANIES'`, `'INTEROP_COMPANIES'`, `'SKU_INTEROP'` |
| q4 | `queries/q4_executions.sql` | `data/q4_executions.parquet` | `'MONTH'` | — | `'ACTIVE_INFRA'`, `'PROD_EXECUTIONS'`, `'DEV_EXECUTIONS'`, `'NONPROD_EXECUTIONS'`, `'PROD_AO_USAGE'` |
| q5 | `queries/q5_ao_usage.sql` | `data/q5_ao_usage.parquet` | `'REPORT_MONTH'` | — | `'ACTIVE_INFRA'`, `'PROD_AO_LAST_WEEK'`, `'DEV_AO_LAST_WEEK'`, `'PROD_AO_MAX_WEEK'`, `'DEV_AO_MAX_WEEK'` |
| q6 | `queries/q6_population.sql` | `data/q6_population.parquet` | — | `'IS_INTEROPERABILITY'`, `'HAS_SKU_INTEROPERABILITY'` | `'COMPANY_COUNT'` |
| q7 | `queries/q7_data_fabric_monthly.sql` | `data/q7_data_fabric_monthly.parquet` | `'MONTH'` | — | `'UNIQUE_TENANTS'`, `'UNIQUE_CUSTOMERS'`, `'TOTAL_CONNECTORS'` |
| q8 | `queries/q8_data_fabric_providers.sql` | `data/q8_data_fabric_providers.parquet` | — | — | `'UNIQUE_TENANTS'`, `'UNIQUE_CUSTOMERS'`, `'TOTAL_CONNECTORS'` |
| q9 | `queries/q9_deployment_option.sql` | `data/q9_deployment_option.parquet` | — | — | `'TOTAL_CUSTOMERS'`, `'CUSTOMERS_WITH_AGENTS'`, `'ADOPTION_RATE_PCT'`, `'TOTAL_AGENTS'`, `'TOTAL_EXECUTIONS'` |
| q10 | `queries/q10_sku_gap_targeting.sql` | `data/q10_sku_gap_targeting.parquet` | — | — | `'ARR_EUR'` |
| q11 | `queries/q11_infra_no_telemetry.sql` | `data/q11_infra_no_telemetry.parquet` | — | — | — |
| q12 | `queries/q12_data_fabric_trialing_monthly.sql` | `data/q12_data_fabric_trialing_monthly.parquet` | `'MONTH'` | — | `'UNIQUE_TENANTS'`, `'UNIQUE_CUSTOMERS'`, `'TOTAL_CONNECTORS'` |
| q13 | `queries/q13_data_interop_customers.sql` | `data/q13_data_interop_customers.parquet` | `'MONTH'` | — | `'DEV_CUSTOMERS'`, `'NONPROD_CUSTOMERS'`, `'PROD_CUSTOMERS'`, `'O11_ODC_CUSTOMERS'` |
| q14 | `queries/q14_data_interop_app_usage.sql` | `data/q14_data_interop_app_usage.parquet` | `'MONTH'` | — | `'DEV_CUSTOMERS'`, `'PROD_CUSTOMERS'`, `'DEV_APPS'`, `'PROD_APPS'`, `'O11_ODC_CUSTOMERS'` |
| q15 | `queries/q15_connector_change_frequency.sql` | `data/q15_connector_change_frequency.parquet` | `'DAY'` | — | `'ADD_REMOVE_EVENTS'`, `'RECONFIGURE_EVENTS'` |
| q16 | `queries/q16_connector_changes_by_region.sql` | `data/q16_connector_changes_by_region.parquet` | `'MONTH'` | — | `'ADD_REMOVE_EVENTS'`, `'RECONFIGURE_EVENTS'` |
| q17 | `queries/q17_changes_per_customer_by_region_ring.sql` | `data/q17_changes_per_customer_by_region_ring.parquet` | — | — | `'AVG_CHANGES_PER_TENANT'`, `'MEDIAN_CHANGES_PER_TENANT'`, `'N_TENANTS'`, `'TOTAL_CHANGES'` |
| q18 | `queries/q18_change_heatmap_region_weekday.sql` | `data/q18_change_heatmap_region_weekday.parquet` | — | — | `'WEEKDAY'`, `'EVENTS'`, `'N_TENANTS'` |
| q19 | `queries/q19_o11_customers_removed_infra.sql` | `data/q19_o11_customers_removed_infra.parquet` | `'LAST_CONNECTOR_TELEMETRY_DAY'`, `'LAST_PLATFORM_USAGE_DAY'` | — | `'N_O11_ENVS'`, `'PEAK_CONNECTORS'`, `'LAST_KNOWN_CONNECTORS'`, `'DAYS_SINCE_CONNECTOR_TELEMETRY'` |
| q20 | `queries/q20_connector_removal_events_by_company.sql` | `data/q20_connector_removal_events_by_company.parquet` | — | — | `'REMOVAL_EVENTS'`, `'TOTAL_CONNECTORS_REMOVED'`, `'PEAK_TOTAL_CONNECTORS'`, `'CONNECTORS_TODAY'` |
| q21 | `queries/q21_multi_o11_infra_with_df.sql` | `data/q21_multi_o11_infra_with_df.parquet` | — | — | `'NUM_O11_INFRAS'`, `'NUM_DF_PROVIDERS'`, `'CURRENT_DF_CONNECTORS'` |
| q22 | `queries/q22_connector_removal_events_multi_o11.sql` | `data/q22_connector_removal_events_multi_o11.parquet` | — | — | `'NUM_O11_INFRAS'`, `'REMOVAL_EVENTS'`, `'TOTAL_CONNECTORS_REMOVED'`, `'PEAK_TOTAL_CONNECTORS'`, `'CONNECTORS_TODAY'` |
| q23 | `queries/q23_o11_customers_removed_infra_multi_o11.sql` | `data/q23_o11_customers_removed_infra_multi_o11.parquet` | `'LAST_CONNECTOR_TELEMETRY_DAY'`, `'LAST_PLATFORM_USAGE_DAY'` | — | `'NUM_O11_INFRAS'`, `'N_O11_ENVS'`, `'PEAK_CONNECTORS'`, `'LAST_KNOWN_CONNECTORS'`, `'DAYS_SINCE_CONNECTOR_TELEMETRY'` |

For queries with no date/bool/numeric cols, leave the corresponding placeholder as `[]`.

After running all 23 queries, confirm 23 Parquet files exist in `data/` before continuing.

### 2. Render the report

```bash
python render.py
```

### 3. Report completion

Print a summary:
- Row counts for each Parquet file (use `pd.read_parquet(path).shape[0]`)
- File sizes in KB (use `os.path.getsize(path) / 1024`)
- Timestamp (UTC)
- Path to report.html