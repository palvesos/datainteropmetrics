# Refresh Data Interoperability KPI Report

Fetch fresh data from Snowflake and regenerate the HTML report.

## Steps

Run these steps in order. Stop and report any error.

### 1. Run the 6 queries and save as Parquet

For each query below, execute it with `snow sql`, parse the JSON response
into a pandas DataFrame, convert date columns, and save to `data/`.

Use this pattern for each query:

```python
import json, pandas as pd

result_json = <output from snow sql command>
rows = json.loads(result_json)
df = pd.DataFrame(rows)
# Convert date column
df['<DATE_COL>'] = pd.to_datetime(df['<DATE_COL>'])
df.to_parquet('data/<filename>.parquet', index=False)
```

**q1 — Monthly adoption trend → data/q1_adoption_trend.parquet**
- SQL file: `queries/q1_adoption_trend.sql`
- Run: `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q1_adoption_trend.sql)" --format json --connection os`
- Date column to convert: `MONTH_START`

**q2 — By product family → data/q2_by_product_family.parquet**
- SQL file: `queries/q2_by_product_family.sql`
- Run: `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q2_by_product_family.sql)" --format json --connection os`
- No date columns.

**q3 — By architecture type → data/q3_by_arch_type.parquet**
- SQL file: `queries/q3_by_arch_type.sql`
- Run: `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q3_by_arch_type.sql)" --format json --connection os`
- No date columns.

**q4 — Executions by month → data/q4_executions.parquet**
- SQL file: `queries/q4_executions.sql`
- Run: `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q4_executions.sql)" --format json --connection os`
- Date column to convert: `MONTH`

**q5 — AO usage trend → data/q5_ao_usage.parquet**
- SQL file: `queries/q5_ao_usage.sql`
- Run: `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q5_ao_usage.sql)" --format json --connection os`
- Date column to convert: `REPORT_MONTH`

**q6 — All-time population → data/q6_population.parquet**
- SQL file: `queries/q6_population.sql`
- Run: `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q6_population.sql)" --format json --connection os`
- Boolean columns: `IS_INTEROPERABILITY`, `HAS_SKU_INTEROPERABILITY` (convert with `df[col] = df[col].astype(bool)`)

### 2. Render the report

```bash
python render.py
```

### 3. Report completion

Print a summary:
- Row counts for each Parquet file
- File sizes in KB
- Timestamp
- Path to report.html
