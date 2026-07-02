# Data Interoperability Dashboard v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enlarge the Data Interoperability dashboard with Data Fabric connector telemetry, deployment-option segmentation, hardened population counts, targeting lists, and maintained data-context docs.

**Architecture:** Same pipeline as v1 — `/refresh` runs SQL via `snow`, saves Parquet to `data/`, then `render.py` (`load_data` → `compute_metrics` → Jinja2 `render`) writes `report.html`. This plan adds 5 queries (q7–q11), hardens q6, and extends `render.py` + the template with new KPIs, charts, tables, and two tabs.

**Tech Stack:** Python 3.11+, pandas, pyarrow, jinja2, Plotly.js (CDN), Snowflake CLI (`uvx snowflake-cli`, connection `os`), pytest.

## Global Constraints

- Snowflake connection name is `os`; run SQL via `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat <file>)" --format json --connection os`.
- snow CLI serializes `DECIMAL`/`NUMERIC` as JSON **strings** — every numeric column must be coerced with `pd.to_numeric()` before `to_parquet`.
- Customer-scoped queries filter current customers with: `MONTH_DT = (SELECT MAX(MONTH_DT) FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO) AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY`.
- SCD2 joins use `event_date::date >= t.date_from AND event_date::date < t.date_to`.
- Provider parsing: `HOSTING = cloud|self-hosted` from `ILIKE 'o11cloud%'`/`'o11selfhosted%'`; `ENGINE = SPLIT_PART(provider,'_',2)`.
- Tests use in-memory fixtures only — no live Snowflake in the test suite. Live grain validation happens per SQL task and feeds `docs/data-context/`.
- Chart color palette (match v1): blue `#60a5fa`, green `#34d399`, amber `#f59e0b`, purple `#a78bfa`, pink `#f472b6`, slate grid `#334155`, panel `#1e293b`, bg `#0f172a`, muted text `#94a3b8`.
- "Last complete month" for KPIs = latest month strictly before the current calendar month (same rule v1 uses for `prod_executions`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `docs/data-context/README.md` | Create | How/why to use + maintain data-context |
| `docs/data-context/tables.md` | Create | Per-table: purpose, key columns, grain, gotchas |
| `docs/data-context/patterns.md` | Create | Reusable SQL patterns + proven pitfalls |
| `queries/q6_population.sql` | Modify | Add current-customer filter (fix month inflation) |
| `queries/q7_data_fabric_monthly.sql` | Create | Monthly DF totals (exact distincts), 12mo |
| `queries/q8_data_fabric_providers.sql` | Create | Last-complete-month per-provider breakdown |
| `queries/q9_deployment_option.sql` | Create | O11/ODC/O11-ODC customers + ODC-agent adoption |
| `queries/q10_sku_gap_targeting.sql` | Create | Interop-without-SKU customers w/ ARR |
| `queries/q11_infra_no_telemetry.sql` | Create | Active prod infra not reporting telemetry |
| `render.py` | Modify | Extend `load_data`, `compute_metrics`, add `_chart_*` helpers |
| `templates/report.html.j2` | Modify | Data Fabric + Targeting tabs, new charts, corrected donut |
| `tests/conftest.py` | Modify | Fixtures for corrected q6 + q7–q11 |
| `tests/test_render.py` | Modify | Tests for new KPIs/charts/tables/tabs |
| `.claude/commands/refresh.md` | Modify | Add q7–q11 to per-query table |
| `docs/dev-status.md` | Modify | Update checkpoint after e2e |

**Metrics dict contract** (produced by `compute_metrics`, consumed by template — additive to v1):
- `kpis.df_connections`, `kpis.df_tenants` — `{value:int, delta:float, is_pct:True, direction:str}`
- `kpis.df_providers` — `{value:int}`
- `kpis.arr_at_risk` — `{value:float}`; `sku_gap_count` — `int`
- `charts.data_fabric_trend`, `charts.data_fabric_providers`, `charts.deployment_option_bar` — `{data:list, layout:dict}`
- `tables.sku_gap_targeting` — list of `{company, segment, deployment, arr_eur}`
- `tables.infra_no_telemetry` — list of `{company, arch, deployment, activation_code}`
- `tables.deployment_option` — list of `{option, customers, with_agents, adoption_pct, agents, executions}`

---

## Task 1: Data-context docs

**Files:**
- Create: `docs/data-context/README.md`
- Create: `docs/data-context/tables.md`
- Create: `docs/data-context/patterns.md`

- [ ] **Step 1: Write `docs/data-context/README.md`**

```markdown
# Data Context

Source-of-truth notes for the Snowflake tables and query patterns behind this
dashboard. **Read `tables.md` + `patterns.md` before writing a new query; update
them after validating a new table, column, or pattern against Snowflake.**

All facts here are validated live on connection `os` (account AX81353-OUTSYSTEMS).
Each `queries/q*.sql` header names the entries it relies on.
```

- [ ] **Step 2: Write `docs/data-context/tables.md`** (one entry per table used by q1–q11)

```markdown
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
```

- [ ] **Step 3: Write `docs/data-context/patterns.md`**

```markdown
# Query Patterns & Pitfalls

## Current-customer filter
    WHERE MONTH_DT = (SELECT MAX(MONTH_DT) FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO)
      AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY
Why: CUSTOMERUNIFIEDINFO is a monthly snapshot; without it you count every month.

## SCD2 date-range join
    INNER JOIN canonical.customersuccess.infrastructure infra
      ON infra.tenant_id = ext.tenant
      AND ext.event_sent::date >= infra.date_from
      AND ext.event_sent::date <  infra.date_to
      AND infra.is_active = TRUE
Always validate SUM/COUNT against the un-joined source to catch fan-out.

## Provider parsing
    CASE WHEN event_provider ILIKE 'o11cloud%' THEN 'cloud'
         WHEN event_provider ILIKE 'o11selfhosted%' THEN 'self-hosted' ELSE 'other' END AS hosting,
    SPLIT_PART(event_provider, '_', 2) AS engine   -- mssql | oracle

## Environment quality gate
    e.is_current AND e.is_active AND NOT e.is_deleted AND e.is_licensed
    AND e.environment_purpose = 'production'

## Pitfall: DECIMAL → JSON string
snow CLI returns DECIMAL/NUMERIC as strings. Coerce with pd.to_numeric() before arithmetic/parquet.

## Pitfall: monthly snapshot double-count
Any monthly-snapshot table (CUSTOMERUNIFIEDINFO, ODCAGENT) double-counts without a month filter.
```

- [ ] **Step 4: Commit**

```bash
git add docs/data-context/
git commit -m "docs: add maintained data-context (tables, patterns, pitfalls)"
```

---

## Task 2: Harden q6 (fix month inflation)

**Files:**
- Modify: `queries/q6_population.sql`

**Interfaces:**
- Produces: `q6` parquet columns unchanged — `IS_INTEROPERABILITY`(bool), `HAS_SKU_INTEROPERABILITY`(bool), `COMPANY_COUNT`(int). Counts now reflect current customers only.

- [ ] **Step 1: Replace `queries/q6_population.sql`**

```sql
SELECT
  IS_INTEROPERABILITY,
  HAS_SKU_INTEROPERABILITY,
  COUNT(*) AS COMPANY_COUNT
FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
WHERE MONTH_DT = (SELECT MAX(MONTH_DT) FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO)
  AND IS_CURRENT_CUSTOMER
  AND IS_CUSTOMER_POLICY
GROUP BY 1, 2
ORDER BY 1, 2
```

- [ ] **Step 2: Validate live — total equals distinct companies (no inflation)**

Run:
```bash
uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q6_population.sql)" --format json --connection os
```
Expected: a handful of rows; `SUM(COMPANY_COUNT)` ≈ 2,400 (current customers), not ~188k.

- [ ] **Step 3: Commit**

```bash
git add queries/q6_population.sql
git commit -m "fix: q6 population — filter to current customers (was summing 103 months)"
```

---

## Task 3: Data Fabric SQL — q7 (monthly totals) + q8 (provider breakdown)

**Files:**
- Create: `queries/q7_data_fabric_monthly.sql`
- Create: `queries/q8_data_fabric_providers.sql`

**Interfaces:**
- Produces `q7`: `MONTH`(date), `UNIQUE_TENANTS`(int), `UNIQUE_CUSTOMERS`(int), `TOTAL_CONNECTIONS`(int).
- Produces `q8`: `PROVIDER`(str), `HOSTING`(str), `ENGINE`(str), `UNIQUE_TENANTS`(int), `UNIQUE_CUSTOMERS`(int), `TOTAL_CONNECTIONS`(int).

- [ ] **Step 1: Write `queries/q7_data_fabric_monthly.sql`**

```sql
-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Pattern: SCD2 join, provider filter.
SELECT
  DATE_TRUNC('month', ext.event_sent) AS MONTH,
  COUNT(DISTINCT ext.tenant)              AS UNIQUE_TENANTS,
  COUNT(DISTINCT comp.company_sfdc_id)    AS UNIQUE_CUSTOMERS,
  SUM(ext.metric_value)                   AS TOTAL_CONNECTIONS
FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
  ON infra.tenant_id = ext.tenant
  AND ext.event_sent::date >= infra.date_from
  AND ext.event_sent::date <  infra.date_to
  AND infra.is_active = TRUE
INNER JOIN CANONICAL.CORE.COMPANY comp
  ON comp.company_sfdc_id = infra.company_sfdc_id
  AND comp.type IN ('customer', 'partner')
WHERE ext.event_provider ILIKE 'o11%'
  AND ext.event_sent >= DATEADD('month', -12, CURRENT_DATE)
GROUP BY 1
ORDER BY 1 DESC
```

- [ ] **Step 2: Write `queries/q8_data_fabric_providers.sql`**

```sql
-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Last complete month, per provider.
SELECT
  ext.event_provider AS PROVIDER,
  CASE WHEN ext.event_provider ILIKE 'o11cloud%'      THEN 'cloud'
       WHEN ext.event_provider ILIKE 'o11selfhosted%' THEN 'self-hosted'
       ELSE 'other' END                           AS HOSTING,
  SPLIT_PART(ext.event_provider, '_', 2)          AS ENGINE,
  COUNT(DISTINCT ext.tenant)                      AS UNIQUE_TENANTS,
  COUNT(DISTINCT comp.company_sfdc_id)            AS UNIQUE_CUSTOMERS,
  SUM(ext.metric_value)                           AS TOTAL_CONNECTIONS
FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
  ON infra.tenant_id = ext.tenant
  AND ext.event_sent::date >= infra.date_from
  AND ext.event_sent::date <  infra.date_to
  AND infra.is_active = TRUE
INNER JOIN CANONICAL.CORE.COMPANY comp
  ON comp.company_sfdc_id = infra.company_sfdc_id
  AND comp.type IN ('customer', 'partner')
WHERE ext.event_provider ILIKE 'o11%'
  AND DATE_TRUNC('month', ext.event_sent) = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE))
GROUP BY 1, 2, 3
ORDER BY TOTAL_CONNECTIONS DESC
```

- [ ] **Step 3: Validate live — grain + no join fan-out**

Run q7, then compare its latest-month `TOTAL_CONNECTIONS` to the raw table:
```bash
uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q7_data_fabric_monthly.sql)" --format json --connection os
uvx --python 3.13 --from snowflake-cli snow sql --query "SELECT DATE_TRUNC('month',event_sent) m, SUM(metric_value) raw_conn FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT WHERE event_provider ILIKE 'o11%' AND event_sent >= DATEADD('month',-12,CURRENT_DATE) GROUP BY 1 ORDER BY 1 DESC" --format json --connection os
```
Expected: q7 `TOTAL_CONNECTIONS` per month ≤ raw (customer/partner filter removes some); if q7 > raw, the infra join fanned out → add `QUALIFY ROW_NUMBER() OVER (PARTITION BY ext.tenant, ext.event_sent ORDER BY infra.date_from DESC)=1` to the infra join subquery and re-validate. Confirm `ENGINE` values are `mssql`/`oracle` (fix `SPLIT_PART` index if not).

- [ ] **Step 4: Commit**

```bash
git add queries/q7_data_fabric_monthly.sql queries/q8_data_fabric_providers.sql
git commit -m "feat: add Data Fabric telemetry queries (q7 monthly, q8 by provider)"
```

---

## Task 4: q9 deployment-option adoption SQL

**Files:**
- Create: `queries/q9_deployment_option.sql`

**Interfaces:**
- Produces `q9`: `USAGE_DEPLOYMENT_OPTION`(str), `TOTAL_CUSTOMERS`(int), `CUSTOMERS_WITH_AGENTS`(int), `ADOPTION_RATE_PCT`(float), `TOTAL_AGENTS`(int), `TOTAL_EXECUTIONS`(int).

- [ ] **Step 1: Write `queries/q9_deployment_option.sql`**

```sql
-- Data context: CUSTOMERUNIFIEDINFO (current-customer filter), ODCAGENT (latest DATE_MONTH).
WITH customer_counts AS (
  SELECT USAGE_DEPLOYMENT_OPTION, COUNT(DISTINCT COMPANY_SFDC_ID) AS total_customers
  FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
  WHERE USAGE_DEPLOYMENT_OPTION IN ('O11', 'ODC', 'O11/ODC')
    AND MONTH_DT = (SELECT MAX(MONTH_DT) FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO)
    AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY
  GROUP BY 1
),
agent_stats AS (
  SELECT c.USAGE_DEPLOYMENT_OPTION,
         COUNT(DISTINCT a.COMPANY_SFDC_ID) AS customers_with_agents,
         SUM(a.N_AGENTS)                   AS total_agents,
         SUM(a.N_EXECUTIONS)               AS total_executions
  FROM CANONICAL.CUSTOMERSUCCESS.ODCAGENT a
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO c
    ON a.COMPANY_SFDC_ID = c.COMPANY_SFDC_ID
  WHERE c.USAGE_DEPLOYMENT_OPTION IN ('O11', 'ODC', 'O11/ODC')
    AND c.MONTH_DT = (SELECT MAX(MONTH_DT) FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO)
    AND c.IS_CURRENT_CUSTOMER AND c.IS_CUSTOMER_POLICY
    AND a.DATE_MONTH = (SELECT MAX(DATE_MONTH) FROM CANONICAL.CUSTOMERSUCCESS.ODCAGENT)
  GROUP BY 1
)
SELECT
  cc.USAGE_DEPLOYMENT_OPTION,
  cc.total_customers,
  COALESCE(ag.customers_with_agents, 0) AS customers_with_agents,
  ROUND(COALESCE(ag.customers_with_agents, 0)::FLOAT / NULLIF(cc.total_customers, 0)::FLOAT * 100, 1) AS adoption_rate_pct,
  COALESCE(ag.total_agents, 0)     AS total_agents,
  COALESCE(ag.total_executions, 0) AS total_executions
FROM customer_counts cc
LEFT JOIN agent_stats ag ON cc.USAGE_DEPLOYMENT_OPTION = ag.USAGE_DEPLOYMENT_OPTION
ORDER BY cc.USAGE_DEPLOYMENT_OPTION
```

- [ ] **Step 2: Validate live**

Run:
```bash
uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q9_deployment_option.sql)" --format json --connection os
```
Expected: 3 rows (O11, ODC, O11/ODC); `adoption_rate_pct` between 0 and 100.

- [ ] **Step 3: Commit**

```bash
git add queries/q9_deployment_option.sql
git commit -m "feat: add q9 deployment-option adoption query"
```

---

## Task 5: q10 SKU-gap targeting SQL

**Files:**
- Create: `queries/q10_sku_gap_targeting.sql`

**Interfaces:**
- Produces `q10`: `COMPANY_SFDC_ID`(str), `COMPANY_NAME`(str), `SEGMENT`(str), `USAGE_DEPLOYMENT_OPTION`(str), `ARR_EUR`(float).

- [ ] **Step 1: Write `queries/q10_sku_gap_targeting.sql`**

```sql
-- Data context: CUSTOMERUNIFIEDINFO (current-customer filter). Interop active but no SKU.
SELECT
  COMPANY_SFDC_ID,
  COMPANY_NAME,
  SEGMENT,
  USAGE_DEPLOYMENT_OPTION,
  ARR_EUR
FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
WHERE MONTH_DT = (SELECT MAX(MONTH_DT) FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO)
  AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY
  AND IS_INTEROPERABILITY = TRUE
  AND HAS_SKU_INTEROPERABILITY = FALSE
ORDER BY ARR_EUR DESC NULLS LAST
```

- [ ] **Step 2: Validate live**

Run:
```bash
uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q10_sku_gap_targeting.sql)" --format json --connection os
```
Expected: N rows (interop-without-SKU customers); one row per company; ARR descending.

- [ ] **Step 3: Commit**

```bash
git add queries/q10_sku_gap_targeting.sql
git commit -m "feat: add q10 SKU-gap targeting query"
```

---

## Task 6: q11 infra-without-telemetry SQL

**Files:**
- Create: `queries/q11_infra_no_telemetry.sql`

**Interfaces:**
- Produces `q11`: `ACTIVATION_CODE`(str), `COMPANY_SFDC_ID`(str), `COMPANY_NAME`(str), `ARCHITECTURE_TYPE`(str), `INFRASTRUCTURE_STATUS`(str), `USAGE_DEPLOYMENT_OPTION`(str).

- [ ] **Step 1: Write `queries/q11_infra_no_telemetry.sql`**

```sql
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
```

- [ ] **Step 2: Validate live — one row per activation_code (no fan-out)**

Run:
```bash
uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/q11_infra_no_telemetry.sql)" --format json --connection os
```
Expected: rows returned; if row count > distinct `ACTIVATION_CODE`, tighten the CUI join (it should be 1:1 given `is_last_month_reported`). Re-run until 1:1.

- [ ] **Step 3: Commit**

```bash
git add queries/q11_infra_no_telemetry.sql
git commit -m "feat: add q11 infra-without-telemetry targeting query"
```

---

## Task 7: Extend test fixtures

**Files:**
- Modify: `tests/conftest.py`

**Interfaces:**
- Produces: `sample_data` fixture now also has keys `q7`,`q8`,`q9`,`q10`,`q11`; `q6` frame unchanged in shape.

- [ ] **Step 1: Add new frames to the `sample_data` fixture**

Insert before the `return {...}` line in `tests/conftest.py`:

```python
    q7 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "UNIQUE_TENANTS": [160, 178, 150, 120],
        "UNIQUE_CUSTOMERS": [140, 155, 130, 100],
        "TOTAL_CONNECTIONS": [18000, 21000, 17500, 14000],
    })
    q8 = pd.DataFrame({
        "PROVIDER": ["o11cloud_mssql", "o11cloud_oracle", "o11selfhosted_mssql", "o11selfhosted_oracle"],
        "HOSTING": ["cloud", "cloud", "self-hosted", "self-hosted"],
        "ENGINE": ["mssql", "oracle", "mssql", "oracle"],
        "UNIQUE_TENANTS": [158, 11, 6, 2],
        "UNIQUE_CUSTOMERS": [140, 10, 5, 2],
        "TOTAL_CONNECTIONS": [18307, 1136, 412, 112],
    })
    q9 = pd.DataFrame({
        "USAGE_DEPLOYMENT_OPTION": ["O11", "ODC", "O11/ODC"],
        "TOTAL_CUSTOMERS": [900, 400, 658],
        "CUSTOMERS_WITH_AGENTS": [50, 300, 409],
        "ADOPTION_RATE_PCT": [5.6, 75.0, 62.2],
        "TOTAL_AGENTS": [200, 8000, 11852],
        "TOTAL_EXECUTIONS": [150, 6000, 9077],
    })
    q10 = pd.DataFrame({
        "COMPANY_SFDC_ID": ["001A", "001B", "001C"],
        "COMPANY_NAME": ["Acme Corp", "Globex", "Initech"],
        "SEGMENT": ["Enterprise", "Mid-Market", "Enterprise"],
        "USAGE_DEPLOYMENT_OPTION": ["O11/ODC", "O11", "O11/ODC"],
        "ARR_EUR": [500000.0, 250000.0, 120000.0],
    })
    q11 = pd.DataFrame({
        "ACTIVATION_CODE": ["AC1", "AC2"],
        "COMPANY_SFDC_ID": ["001D", "001E"],
        "COMPANY_NAME": ["Umbrella", "Stark Ind"],
        "ARCHITECTURE_TYPE": ["cloud", "on-premises"],
        "INFRASTRUCTURE_STATUS": ["active", "active"],
        "USAGE_DEPLOYMENT_OPTION": ["O11", "O11/ODC"],
    })
```

- [ ] **Step 2: Update the `return` dict to include the new frames**

```python
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6,
            "q7": q7, "q8": q8, "q9": q9, "q10": q10, "q11": q11}
```

- [ ] **Step 3: Run existing suite — still green (fixtures are additive)**

Run: `pytest tests/ -q`
Expected: 17 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add q7–q11 sample fixtures"
```

---

## Task 8: Extend `load_data` for q7–q11

**Files:**
- Modify: `render.py` (the `load_data` `file_map`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: parquet files `q7_data_fabric_monthly.parquet` … `q11_infra_no_telemetry.parquet`.
- Produces: `load_data()` returns keys `q1`–`q11`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_render.py`:

```python
def test_load_data_returns_eleven_keys(tmp_path, sample_data):
    files = {
        "q1": "q1_adoption_trend.parquet", "q2": "q2_by_product_family.parquet",
        "q3": "q3_by_arch_type.parquet", "q4": "q4_executions.parquet",
        "q5": "q5_ao_usage.parquet", "q6": "q6_population.parquet",
        "q7": "q7_data_fabric_monthly.parquet", "q8": "q8_data_fabric_providers.parquet",
        "q9": "q9_deployment_option.parquet", "q10": "q10_sku_gap_targeting.parquet",
        "q11": "q11_infra_no_telemetry.parquet",
    }
    for key, fn in files.items():
        sample_data[key].to_parquet(tmp_path / fn, index=False)
    result = load_data(str(tmp_path))
    assert set(result.keys()) == set(files.keys())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_render.py::test_load_data_returns_eleven_keys -v`
Expected: FAIL (missing q7 file / KeyError — only q1–q6 in file_map).

- [ ] **Step 3: Extend the `file_map` in `load_data`**

In `render.py`, add to the `file_map` dict:

```python
        "q7": "q7_data_fabric_monthly.parquet",
        "q8": "q8_data_fabric_providers.parquet",
        "q9": "q9_deployment_option.parquet",
        "q10": "q10_sku_gap_targeting.parquet",
        "q11": "q11_infra_no_telemetry.parquet",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_render.py::test_load_data_returns_eleven_keys -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: load_data reads q7–q11 parquet files"
```

---

## Task 9: `compute_metrics` — Data Fabric KPIs + corrected q6 unchanged

**Files:**
- Modify: `render.py` (`compute_metrics`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `data["q7"]`, `data["q8"]`.
- Produces: `metrics["kpis"]["df_connections"]` `{value,delta,is_pct,direction}`, `["df_tenants"]` same shape, `["df_providers"]` `{value}`.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_render.py`:

```python
def test_compute_metrics_df_connections_last_full_month(sample_data):
    # June is partial current month; May (21000) is the last full month
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["df_connections"]["value"] == 21000

def test_compute_metrics_df_tenants_last_full_month(sample_data):
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["df_tenants"]["value"] == 178

def test_compute_metrics_df_providers_count(sample_data):
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["df_providers"]["value"] == 4
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_render.py -k df_ -v`
Expected: FAIL (KeyError `df_connections`).

- [ ] **Step 3: Implement in `compute_metrics`**

Add before the `return {` in `compute_metrics` (reuse the existing `current_month_start` if present, else compute):

```python
    # --- Data Fabric (q7 monthly totals, last complete month) ---
    q7 = data["q7"].sort_values("MONTH", ascending=False).reset_index(drop=True)
    _cms = pd.Timestamp.today().normalize().replace(day=1)
    q7_full = q7[q7["MONTH"] < _cms].reset_index(drop=True)
    df_cur = q7_full.iloc[0] if len(q7_full) else q7.iloc[0]
    df_prev = q7_full.iloc[1] if len(q7_full) > 1 else None

    def _pct_delta(cur, prev):
        return float((cur - prev) / prev * 100) if prev not in (None, 0) else 0.0

    df_connections = int(df_cur["TOTAL_CONNECTIONS"])
    df_tenants = int(df_cur["UNIQUE_TENANTS"])
    conn_delta = _pct_delta(df_cur["TOTAL_CONNECTIONS"], df_prev["TOTAL_CONNECTIONS"] if df_prev is not None else None)
    tenant_delta = _pct_delta(df_cur["UNIQUE_TENANTS"], df_prev["UNIQUE_TENANTS"] if df_prev is not None else None)
    df_providers = int((data["q8"]["TOTAL_CONNECTIONS"] > 0).sum())
```

Then add to the `"kpis": { ... }` dict:

```python
            "df_connections": {"value": df_connections, "delta": round(conn_delta, 1), "is_pct": True,
                               "direction": "up" if conn_delta >= 0 else "down"},
            "df_tenants": {"value": df_tenants, "delta": round(tenant_delta, 1), "is_pct": True,
                           "direction": "up" if tenant_delta >= 0 else "down"},
            "df_providers": {"value": df_providers},
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_render.py -k df_ -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: compute_metrics — Data Fabric KPIs"
```

---

## Task 10: `compute_metrics` — new charts

**Files:**
- Modify: `render.py` (add 3 `_chart_*` helpers + wire into `charts`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `data["q7"]`, `data["q8"]`, `data["q9"]`.
- Produces: `metrics["charts"]["data_fabric_trend"]`, `["data_fabric_providers"]`, `["deployment_option_bar"]` — each `{data:list,layout:dict}`.

- [ ] **Step 1: Write failing test**

Add to `tests/test_render.py`:

```python
def test_compute_metrics_new_charts_present(sample_data):
    metrics = compute_metrics(sample_data)
    for name in ("data_fabric_trend", "data_fabric_providers", "deployment_option_bar"):
        assert name in metrics["charts"], f"missing {name}"
        assert len(metrics["charts"][name]["data"]) > 0
        assert "layout" in metrics["charts"][name]
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_render.py::test_compute_metrics_new_charts_present -v`
Expected: FAIL (missing key).

- [ ] **Step 3: Add three chart helpers to `render.py`** (near the other `_chart_*` fns)

```python
def _chart_data_fabric_trend(df: pd.DataFrame) -> dict:
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    return {
        "data": [
            {"x": months, "y": df["TOTAL_CONNECTIONS"].tolist(), "type": "bar",
             "name": "Connections", "marker": {"color": "#60a5fa"}, "yaxis": "y"},
            {"x": months, "y": df["UNIQUE_TENANTS"].tolist(), "type": "scatter",
             "mode": "lines+markers", "name": "Tenants", "line": {"color": "#34d399", "width": 2}, "yaxis": "y2"},
        ],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Connections", "gridcolor": "#334155"},
            "yaxis2": {"title": "Tenants", "overlaying": "y", "side": "right", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"}, "margin": {"t": 20, "b": 50, "l": 70, "r": 60}, "autosize": True,
        },
    }


def _chart_data_fabric_providers(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["label"] = df["HOSTING"] + " / " + df["ENGINE"]
    df = df.sort_values("TOTAL_CONNECTIONS", ascending=True)
    labels = df["label"].tolist()
    return {
        "data": [
            {"y": labels, "x": df["TOTAL_CONNECTIONS"].tolist(), "type": "bar", "orientation": "h",
             "name": "Connections", "marker": {"color": "#60a5fa"}},
            {"y": labels, "x": df["UNIQUE_TENANTS"].tolist(), "type": "bar", "orientation": "h",
             "name": "Tenants", "marker": {"color": "#34d399"}},
        ],
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"}, "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 130, "r": 20}, "autosize": True,
        },
    }


def _chart_deployment_option_bar(df: pd.DataFrame) -> dict:
    df = df.sort_values("USAGE_DEPLOYMENT_OPTION")
    opts = df["USAGE_DEPLOYMENT_OPTION"].tolist()
    return {
        "data": [
            {"x": opts, "y": df["TOTAL_CUSTOMERS"].tolist(), "type": "bar",
             "name": "Customers", "marker": {"color": "#334155"}},
            {"x": opts, "y": df["CUSTOMERS_WITH_AGENTS"].tolist(), "type": "bar",
             "name": "With ODC Agents", "marker": {"color": "#34d399"}},
        ],
        "layout": {
            "barmode": "overlay",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"}, "yaxis": {"title": "Customers", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"}, "margin": {"t": 20, "b": 50, "l": 60, "r": 20}, "autosize": True,
        },
    }
```

- [ ] **Step 4: Wire them into the `"charts": { ... }` dict in `compute_metrics`**

```python
            "data_fabric_trend": _chart_data_fabric_trend(data["q7"]),
            "data_fabric_providers": _chart_data_fabric_providers(data["q8"]),
            "deployment_option_bar": _chart_deployment_option_bar(data["q9"]),
```

- [ ] **Step 5: Run to verify pass**

Run: `pytest tests/test_render.py::test_compute_metrics_new_charts_present -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: compute_metrics — Data Fabric + deployment-option charts"
```

---

## Task 11: `compute_metrics` — targeting tables + ARR-at-risk

**Files:**
- Modify: `render.py` (`compute_metrics`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `data["q9"]`, `data["q10"]`, `data["q11"]`.
- Produces: `metrics["kpis"]["arr_at_risk"]` `{value:float}`; `metrics["sku_gap_count"]` int; `metrics["tables"]["sku_gap_targeting"]`, `["infra_no_telemetry"]`, `["deployment_option"]` lists.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_render.py`:

```python
def test_compute_metrics_arr_at_risk(sample_data):
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["arr_at_risk"]["value"] == pytest.approx(870000.0)
    assert metrics["sku_gap_count"] == 3

def test_compute_metrics_targeting_tables(sample_data):
    metrics = compute_metrics(sample_data)
    sku = metrics["tables"]["sku_gap_targeting"]
    assert sku[0]["company"] == "Acme Corp"          # highest ARR first
    assert sku[0]["arr_eur"] == 500000.0
    assert len(metrics["tables"]["infra_no_telemetry"]) == 2
    assert len(metrics["tables"]["deployment_option"]) == 3
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_render.py -k "arr_at_risk or targeting" -v`
Expected: FAIL (KeyError).

- [ ] **Step 3: Implement in `compute_metrics`**

Add before the `return {`:

```python
    # --- Targeting (q10 SKU gap, q11 no-telemetry) + deployment table (q9) ---
    q10 = data["q10"]
    arr_at_risk = float(q10["ARR_EUR"].fillna(0).sum())
    sku_gap_count = int(len(q10))
    sku_gap_targeting = [
        {"company": r["COMPANY_NAME"], "segment": r["SEGMENT"],
         "deployment": r["USAGE_DEPLOYMENT_OPTION"], "arr_eur": float(r["ARR_EUR"] or 0)}
        for _, r in q10.sort_values("ARR_EUR", ascending=False).head(20).iterrows()
    ]
    infra_no_telemetry = [
        {"company": r["COMPANY_NAME"], "arch": r["ARCHITECTURE_TYPE"],
         "deployment": r["USAGE_DEPLOYMENT_OPTION"], "activation_code": r["ACTIVATION_CODE"]}
        for _, r in data["q11"].head(20).iterrows()
    ]
    deployment_option = [
        {"option": r["USAGE_DEPLOYMENT_OPTION"], "customers": int(r["TOTAL_CUSTOMERS"]),
         "with_agents": int(r["CUSTOMERS_WITH_AGENTS"]), "adoption_pct": float(r["ADOPTION_RATE_PCT"]),
         "agents": int(r["TOTAL_AGENTS"]), "executions": int(r["TOTAL_EXECUTIONS"])}
        for _, r in data["q9"].iterrows()
    ]
```

Add `"arr_at_risk": {"value": round(arr_at_risk, 2)},` to the `"kpis"` dict, add
`"sku_gap_count": sku_gap_count,` at the top level of the returned dict, and add to
the `"tables": { ... }` dict:

```python
            "sku_gap_targeting": sku_gap_targeting,
            "infra_no_telemetry": infra_no_telemetry,
            "deployment_option": deployment_option,
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_render.py -k "arr_at_risk or targeting" -v`
Expected: PASS.

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: compute_metrics — targeting tables and ARR-at-risk"
```

---

## Task 12: Template — Data Fabric + Targeting tabs, corrected donut

**Files:**
- Modify: `templates/report.html.j2`

**Interfaces:**
- Consumes: metrics keys added in Tasks 9–11.

- [ ] **Step 1: Add two nav buttons** — in the `<nav>` block, after the Segments button:

```html
  <button class="tab-btn" onclick="switchTab('datafabric')">Data Fabric</button>
  <button class="tab-btn" onclick="switchTab('targeting')">Targeting</button>
```

- [ ] **Step 2: Add the Data Fabric tab** — after the Segments `</div>` tab block:

```html
<!-- DATA FABRIC -->
<div id="tab-datafabric" class="tab-content">
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">DF Connections (last full mo.)</div>
      <div class="kpi-value kpi-customers">{{ "{:,}".format(kpis.df_connections.value) }}</div>
      <div class="kpi-delta {{ kpis.df_connections.direction }}">
        {{ "▲" if kpis.df_connections.direction == "up" else "▼" }} {{ "%+.1f"|format(kpis.df_connections.delta) }}% MoM
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">DF Tenants (last full mo.)</div>
      <div class="kpi-value kpi-adoption">{{ "{:,}".format(kpis.df_tenants.value) }}</div>
      <div class="kpi-delta {{ kpis.df_tenants.direction }}">
        {{ "▲" if kpis.df_tenants.direction == "up" else "▼" }} {{ "%+.1f"|format(kpis.df_tenants.delta) }}% MoM
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Active Providers</div>
      <div class="kpi-value kpi-executions">{{ kpis.df_providers.value }}</div>
    </div>
  </div>
  <div class="chart-row">
    <div class="section"><h3>Connector Usage Trend (12 mo.)</h3><div id="chart-df-trend" class="chart-container tall"></div></div>
    <div class="section"><h3>By Provider (last full mo.)</h3><div id="chart-df-providers" class="chart-container tall"></div></div>
  </div>
</div>

<!-- TARGETING -->
<div id="tab-targeting" class="tab-content">
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">ARR at Risk (interop, no SKU)</div>
      <div class="kpi-value kpi-ao">€{{ "{:,.0f}".format(kpis.arr_at_risk.value) }}</div>
      <div class="kpi-delta">{{ sku_gap_count }} customers</div>
    </div>
  </div>
  <div class="section">
    <h3>SKU Gap — Interop customers without SKU (top 20 by ARR)</h3>
    <table>
      <thead><tr><th>Company</th><th>Segment</th><th>Deployment</th><th>ARR (EUR)</th></tr></thead>
      <tbody>
        {% for r in tables.sku_gap_targeting %}
        <tr><td>{{ r.company }}</td><td>{{ r.segment }}</td><td>{{ r.deployment }}</td><td>{{ "{:,.0f}".format(r.arr_eur) }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="section">
    <h3>Active Production Infra Not Reporting Telemetry (top 20)</h3>
    <table>
      <thead><tr><th>Company</th><th>Architecture</th><th>Deployment</th><th>Activation Code</th></tr></thead>
      <tbody>
        {% for r in tables.infra_no_telemetry %}
        <tr><td>{{ r.company }}</td><td>{{ r.arch }}</td><td>{{ r.deployment }}</td><td>{{ r.activation_code }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
```

- [ ] **Step 3: Add the deployment-option chart to the Segments tab** — inside `#tab-segments`, before its closing `</div>`, add a section:

```html
  <div class="section">
    <h3>Adoption by Deployment Option (ODC agents)</h3>
    <div id="chart-deployment-option" class="chart-container"></div>
  </div>
```

- [ ] **Step 4: Register the new charts in the `<script>` `charts` object and `Plotly.newPlot` calls**

Add to the `var charts = { ... }` object:
```javascript
    data_fabric_trend:     {{ charts.data_fabric_trend | tojson }},
    data_fabric_providers: {{ charts.data_fabric_providers | tojson }},
    deployment_option_bar: {{ charts.deployment_option_bar | tojson }},
```
Add after the existing `Plotly.newPlot` calls:
```javascript
  Plotly.newPlot('chart-df-trend',           charts.data_fabric_trend.data,     charts.data_fabric_trend.layout,     cfg);
  Plotly.newPlot('chart-df-providers',       charts.data_fabric_providers.data, charts.data_fabric_providers.layout, cfg);
  Plotly.newPlot('chart-deployment-option',  charts.deployment_option_bar.data, charts.deployment_option_bar.layout, cfg);
```

- [ ] **Step 5: Commit**

```bash
git add templates/report.html.j2
git commit -m "feat: template — Data Fabric + Targeting tabs, deployment-option chart"
```

---

## Task 13: Render tests for new tabs

**Files:**
- Test: `tests/test_render.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_render.py`:

```python
def test_render_has_new_tabs(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    for tab in ("Data Fabric", "Targeting"):
        assert tab in content

def test_render_shows_df_kpi_and_sku_gap(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "21,000" in content        # df_connections last full month
    assert "Acme Corp" in content     # top SKU-gap target
```

- [ ] **Step 2: Run to verify** (fails before Task 12 template exists; passes after)

Run: `pytest tests/test_render.py -k "new_tabs or df_kpi" -v`
Expected: PASS (Task 12 already added the template markup).

- [ ] **Step 3: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_render.py
git commit -m "test: render asserts Data Fabric + Targeting tabs and values"
```

---

## Task 14: Wire q7–q11 into `/refresh`

**Files:**
- Modify: `.claude/commands/refresh.md`

- [ ] **Step 1: Add rows to the per-query table** (matching the existing Date/Bool/Numeric column format)

```markdown
| q7 | `queries/q7_data_fabric_monthly.sql` | `data/q7_data_fabric_monthly.parquet` | `'MONTH'` | — | `'UNIQUE_TENANTS'`, `'UNIQUE_CUSTOMERS'`, `'TOTAL_CONNECTIONS'` |
| q8 | `queries/q8_data_fabric_providers.sql` | `data/q8_data_fabric_providers.parquet` | — | — | `'UNIQUE_TENANTS'`, `'UNIQUE_CUSTOMERS'`, `'TOTAL_CONNECTIONS'` |
| q9 | `queries/q9_deployment_option.sql` | `data/q9_deployment_option.parquet` | — | — | `'TOTAL_CUSTOMERS'`, `'CUSTOMERS_WITH_AGENTS'`, `'ADOPTION_RATE_PCT'`, `'TOTAL_AGENTS'`, `'TOTAL_EXECUTIONS'` |
| q10 | `queries/q10_sku_gap_targeting.sql` | `data/q10_sku_gap_targeting.parquet` | — | — | `'ARR_EUR'` |
| q11 | `queries/q11_infra_no_telemetry.sql` | `data/q11_infra_no_telemetry.parquet` | — | — | — |
```

- [ ] **Step 2: Update the count-check sentence** — change "confirm 6 Parquet files exist" to "confirm 11 Parquet files exist".

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/refresh.md
git commit -m "feat: /refresh runs q7–q11 (Data Fabric, deployment, targeting)"
```

---

## Task 15: End-to-end live refresh + dev-status

**Files:**
- Modify: `docs/dev-status.md`

- [ ] **Step 1: Run `/refresh` end-to-end** (in a Claude Code session)

Run `/refresh`. Expected: 11 Parquet files written to `data/`, `report.html` regenerated, summary printed with row counts.

- [ ] **Step 2: Verify the report opens with the new content**

```bash
open report.html
```
Verify: 6 tabs (Overview, Adoption, Usage, Segments, Data Fabric, Targeting); Data Fabric KPIs + both charts render; population donut looks sane (thousands, not hundreds of thousands); SKU-gap table populated with ARR; deployment-option chart in Segments.

- [ ] **Step 3: Update `docs/dev-status.md`** — bump the completed-tasks table with the v2 work (queries q7–q11, q6 fix, new tabs, data-context docs) and the new "11 Parquet files" note.

- [ ] **Step 4: Commit**

```bash
git add docs/dev-status.md
git commit -m "docs: dev-status — dashboard v2 complete"
```

---

## Self-Review

**Spec coverage:**
- A (Data Fabric queries) → Task 3 (split into q7+q8 for exact distincts — refinement noted below).
- A (deployment option) → Task 4; (SKU gap) → Task 5; (infra no telemetry) → Task 6.
- B (harden q6) → Task 2; q1–q5 review → covered in `tables.md` note (Task 1) — no code change, per spec.
- C (render/template) → Tasks 8–13.
- D (/refresh) → Task 14.
- E (tests) → Tasks 7, 8, 9, 10, 11, 13.
- F (data-context docs) → Task 1; per-query citations in q7–q11 headers (Tasks 3–6).

**Spec deviation (intentional):** the spec's single month×provider Data Fabric query is split into q7 (monthly totals, exact distinct tenants/customers) + q8 (last-month provider breakdown). Reason: distinct counts can't be recovered from pre-aggregated per-provider rows. Spec deliverable A should be updated to match; flagged to the user.

**Placeholder scan:** none — all steps contain concrete SQL/Python/HTML.

**Type consistency:** metrics keys (`df_connections`, `df_tenants`, `df_providers`, `arr_at_risk`, `sku_gap_count`, `sku_gap_targeting`, `infra_no_telemetry`, `deployment_option`, `data_fabric_trend`, `data_fabric_providers`, `deployment_option_bar`) are consistent across Tasks 9–13 and the template. Fixture keys `q7`–`q11` consistent across Tasks 7, 8, and the load_data map.
