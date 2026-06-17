# Refresh Data Interoperability KPI Report

Fetch fresh data from Snowflake and regenerate the HTML report.

## Steps

Run these steps in order. If any step fails (non-zero exit code or exception), stop and print the error.

### 1. Run the 6 queries and save as Parquet

For each query, run the `snow sql` command to capture JSON output to a temp file, then parse it into a pandas DataFrame, convert date/boolean columns, and save to `data/`. Guard the date conversion so empty result sets don't fail.

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
df.to_parquet('data/<QN_FILE>.parquet', index=False)
```

Per-query values:

| Key | SQL file | Output Parquet | Date cols | Bool cols |
|-----|----------|----------------|-----------|-----------|
| q1 | `queries/q1_adoption_trend.sql` | `data/q1_adoption_trend.parquet` | `'MONTH_START'` | — |
| q2 | `queries/q2_by_product_family.sql` | `data/q2_by_product_family.parquet` | — | — |
| q3 | `queries/q3_by_arch_type.sql` | `data/q3_by_arch_type.parquet` | — | — |
| q4 | `queries/q4_executions.sql` | `data/q4_executions.parquet` | `'MONTH'` | — |
| q5 | `queries/q5_ao_usage.sql` | `data/q5_ao_usage.parquet` | `'REPORT_MONTH'` | — |
| q6 | `queries/q6_population.sql` | `data/q6_population.parquet` | — | `'IS_INTEROPERABILITY'`, `'HAS_SKU_INTEROPERABILITY'` |

For queries with no date cols, leave `[<DATE_COLS>]` as `[]`. For queries with no bool cols, leave `[<BOOL_COLS>]` as `[]`.

After running all 6 queries, confirm 6 Parquet files exist in `data/` before continuing.

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