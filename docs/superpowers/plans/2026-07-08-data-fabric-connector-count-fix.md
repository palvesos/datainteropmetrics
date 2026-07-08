# Data Fabric — Connector Count Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Data Fabric volume metric so it reports **existing connectors** (a point-in-time gauge) instead of `SUM(metric_value)` over days (connector-days), and rename the metric to "Connectors" throughout.

**Architecture:** `EXTERNALCONNECTIONCOUNT.METRIC_VALUE` is a daily gauge. In q7/q8/q12 the `QUALIFY` changes to keep the **latest `event_sent` within each month** per `(tenant, environment_id, event_provider)`, then `SUM(metric_value)` = connectors at month-end. The output column `TOTAL_CONNECTIONS` becomes `TOTAL_CONNECTORS`; `render.py` KPI keys `df_connections`/`df_trialing_connections` become `df_connectors`/`df_trialing_connectors`; the template + tests + refresh docs follow the rename.

**Tech Stack:** Python 3.13, pandas, Jinja2, Plotly (client-side), pytest, Snowflake (snow CLI, refresh only).

## Global Constraints

Every task's requirements implicitly include these (copied from the spec):

- **Data Fabric only** (q7/q8/q12 + Data Fabric tab). No change to other tabs or the paying-vs-trialing category logic.
- The new per-entity dedupe key is `(month, tenant, environment_id, event_provider)` for q7/q12 and `(tenant, environment_id, event_provider)` for q8 (single last-complete-month scope), ordered `TRY_TO_TIMESTAMP(event_sent) DESC, infra.date_from DESC`.
- Add `AND ext.metric_value > 0` to all three queries.
- Output column is renamed **exactly** `TOTAL_CONNECTIONS` → `TOTAL_CONNECTORS` (q7, q8, q12).
- KPI keys renamed **exactly**: `df_connections` → `df_connectors`; `df_trialing_connections` → `df_trialing_connectors`. `df_tenants`, `df_trialing_tenants`, `df_providers` unchanged.
- The "last full month" / MoM-delta logic (`current_month_start`, `_pct_delta`) is UNCHANGED. Fixture numeric values are UNCHANGED — only column/key/label names change.
- SQL has no unit test (repo convention); SQL correctness is validated by a real `/refresh` (manual, Task 3).
- Full suite `python -m pytest tests/ -q` must end green, 0 warnings.

---

## File Structure

- **Modify** `queries/q7_data_fabric_monthly.sql` — snapshot QUALIFY + `metric_value>0` + `TOTAL_CONNECTORS`.
- **Modify** `queries/q12_data_fabric_trialing_monthly.sql` — same as q7, prospect filter retained.
- **Modify** `queries/q8_data_fabric_providers.sql` — in-month snapshot dedupe + `TOTAL_CONNECTORS`.
- **Modify** `.claude/commands/refresh.md` — q7/q8/q12 numeric-col name → `'TOTAL_CONNECTORS'`.
- **Modify** `tests/conftest.py` — q7/q8/q12 fixture column → `TOTAL_CONNECTORS` (values unchanged).
- **Modify** `tests/test_render.py` — rename assertion keys/labels/columns (values unchanged).
- **Modify** `render.py` — 2 chart fns + `compute_metrics` column/key renames.
- **Modify** `templates/report.html.j2` — card labels + KPI-key refs + relabel.

Two tasks: SQL+docs (Task 1, no unit test) and the Python/template/test rename (Task 2, atomic — the shared fixture-column rename forces render/template/tests to move together to stay green). Task 3 is manual Snowflake validation.

---

### Task 1: Snapshot logic + column rename in the three SQL queries + refresh docs

**Files:**
- Modify: `queries/q7_data_fabric_monthly.sql`
- Modify: `queries/q12_data_fabric_trialing_monthly.sql`
- Modify: `queries/q8_data_fabric_providers.sql`
- Modify: `.claude/commands/refresh.md`

**Interfaces:**
- Consumes: nothing new.
- Produces: q7/q8/q12 SQL emitting `TOTAL_CONNECTORS` at connector (not connector-day) scale; `/refresh` will write the same three Parquet paths with the renamed column. No Python unit test (validated by real `/refresh` in Task 3).

- [ ] **Step 1: Rewrite `queries/q7_data_fabric_monthly.sql`**

Replace the whole file with:

```sql
-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Pattern: SCD2 join, provider filter.
-- METRIC_VALUE is a DAILY GAUGE (current connector count per tenant/env/provider, re-emitted daily).
-- Connectors, NOT connector-days: take the latest snapshot per entity WITHIN each month, then SUM.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: QUALIFY keeps one row per (month, tenant, environment_id, event_provider) = that entity's
--   end-of-month snapshot; this also subsumes SCD2 fan-out / same-day duplicate dedupe.
-- NOTE: comp.type IN ('customer','partner') = paying tenants (excludes internal/prospect/former).
WITH monthly_snapshot AS (
  SELECT
    DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)) AS MONTH,
    ext.tenant,
    ext.environment_id,
    ext.event_provider,
    ext.metric_value,
    comp.company_sfdc_id
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
    ON infra.tenant_id = ext.tenant
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date >= infra.date_from::date
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date <  infra.date_to::date
    AND infra.is_active = TRUE
  INNER JOIN CANONICAL.CORE.COMPANY comp
    ON comp.company_sfdc_id = infra.company_sfdc_id
    AND comp.type IN ('customer', 'partner')
  WHERE ext.event_provider ILIKE 'o11%'
    AND ext.metric_value > 0
    AND TRY_TO_TIMESTAMP(ext.event_sent) >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)),
                 ext.tenant, ext.environment_id, ext.event_provider
    ORDER BY TRY_TO_TIMESTAMP(ext.event_sent) DESC, infra.date_from DESC) = 1
)
SELECT
  MONTH,
  COUNT(DISTINCT tenant)          AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id) AS UNIQUE_CUSTOMERS,
  SUM(metric_value)               AS TOTAL_CONNECTORS
FROM monthly_snapshot
GROUP BY 1
ORDER BY 1 DESC
```

- [ ] **Step 2: Rewrite `queries/q12_data_fabric_trialing_monthly.sql`**

Replace the whole file with the same query as Step 1, changing only the header note and the company filter to the prospect set:

```sql
-- TRIALING counterpart to q7. Identical shape/logic; only the COMPANY.type filter differs.
-- METRIC_VALUE is a DAILY GAUGE; connectors = latest snapshot per entity within each month, then SUM.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: comp.type IN ('prospect customer','prospect partner') = non-paying tenants trialing the product.
--   Disjoint from q7's ('customer','partner') set, so the two series never double-count.
WITH monthly_snapshot AS (
  SELECT
    DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)) AS MONTH,
    ext.tenant,
    ext.environment_id,
    ext.event_provider,
    ext.metric_value,
    comp.company_sfdc_id
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
    ON infra.tenant_id = ext.tenant
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date >= infra.date_from::date
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date <  infra.date_to::date
    AND infra.is_active = TRUE
  INNER JOIN CANONICAL.CORE.COMPANY comp
    ON comp.company_sfdc_id = infra.company_sfdc_id
    AND comp.type IN ('prospect customer', 'prospect partner')
  WHERE ext.event_provider ILIKE 'o11%'
    AND ext.metric_value > 0
    AND TRY_TO_TIMESTAMP(ext.event_sent) >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)),
                 ext.tenant, ext.environment_id, ext.event_provider
    ORDER BY TRY_TO_TIMESTAMP(ext.event_sent) DESC, infra.date_from DESC) = 1
)
SELECT
  MONTH,
  COUNT(DISTINCT tenant)          AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id) AS UNIQUE_CUSTOMERS,
  SUM(metric_value)               AS TOTAL_CONNECTORS
FROM monthly_snapshot
GROUP BY 1
ORDER BY 1 DESC
```

- [ ] **Step 3: Rewrite `queries/q8_data_fabric_providers.sql`**

Replace the whole file with:

```sql
-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Last complete month, per provider.
-- METRIC_VALUE is a DAILY GAUGE; connectors = latest in-month snapshot per entity, then SUM by provider.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
WITH monthly_snapshot AS (
  SELECT
    ext.tenant,
    ext.environment_id,
    ext.event_provider,
    ext.metric_value,
    comp.company_sfdc_id
  FROM TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONCOUNT ext
  INNER JOIN CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE infra
    ON infra.tenant_id = ext.tenant
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date >= infra.date_from::date
    AND TRY_TO_TIMESTAMP(ext.event_sent)::date <  infra.date_to::date
    AND infra.is_active = TRUE
  INNER JOIN CANONICAL.CORE.COMPANY comp
    ON comp.company_sfdc_id = infra.company_sfdc_id
    AND comp.type IN ('customer', 'partner')
  WHERE ext.event_provider ILIKE 'o11%'
    AND ext.metric_value > 0
    AND DATE_TRUNC('month', TRY_TO_TIMESTAMP(ext.event_sent)) = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE))
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ext.tenant, ext.environment_id, ext.event_provider
    ORDER BY TRY_TO_TIMESTAMP(ext.event_sent) DESC, infra.date_from DESC) = 1
)
SELECT
  event_provider                                     AS PROVIDER,
  CASE WHEN event_provider ILIKE 'o11cloud%'      THEN 'cloud'
       WHEN event_provider ILIKE 'o11selfhosted%' THEN 'self-hosted'
       ELSE 'other' END                            AS HOSTING,
  SPLIT_PART(event_provider, '_', 2)               AS ENGINE,
  COUNT(DISTINCT tenant)                           AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id)                  AS UNIQUE_CUSTOMERS,
  SUM(metric_value)                                AS TOTAL_CONNECTORS
FROM monthly_snapshot
GROUP BY 1, 2, 3
ORDER BY TOTAL_CONNECTORS DESC
```

- [ ] **Step 4: Rename the numeric column in `.claude/commands/refresh.md`**

In the per-query table, change `'TOTAL_CONNECTIONS'` to `'TOTAL_CONNECTORS'` in the q7, q8, and q12 rows (three occurrences).

Run: `grep -n "TOTAL_CONNECTIONS\|TOTAL_CONNECTORS" .claude/commands/refresh.md`
Expected: three `TOTAL_CONNECTORS` (q7, q8, q12); zero `TOTAL_CONNECTIONS`.

- [ ] **Step 5: Verify the q7/q12 difference is only the company filter**

Run: `diff <(sed -n '/WITH monthly_snapshot/,$p' queries/q7_data_fabric_monthly.sql) <(sed -n '/WITH monthly_snapshot/,$p' queries/q12_data_fabric_trialing_monthly.sql)`
Expected: the only differing line in the query body is the `comp.type IN (...)` filter.

- [ ] **Step 6: Commit**

```bash
git add queries/q7_data_fabric_monthly.sql queries/q12_data_fabric_trialing_monthly.sql queries/q8_data_fabric_providers.sql .claude/commands/refresh.md
git commit -m "fix: Data Fabric connectors = end-of-month snapshot, not SUM of daily gauge"
```

---

### Task 2: Rename to Connectors in render.py + template + tests (atomic)

**Files:**
- Modify: `tests/conftest.py:49-62,86-91` (q7/q8/q12 fixture column rename)
- Modify: `tests/test_render.py` (assertion key/label/column renames)
- Modify: `render.py:124-166,287-301,354-361` (chart fns + compute_metrics)
- Modify: `templates/report.html.j2:182-185,199-205` (labels + key refs)

**Interfaces:**
- Consumes: fixture DataFrames with column `TOTAL_CONNECTORS` (q7/q8/q12).
- Produces: `metrics["kpis"]["df_connectors"]` and `metrics["kpis"]["df_trialing_connectors"]` (same dict shape as before: `value`, `delta`, `is_pct`, `direction`); trend chart y-axis title `Connectors`; providers chart trace name `Connectors`; rendered HTML card labels `DF Connectors (last full mo.)` and `Trialing Connectors (last full mo.)`.

- [ ] **Step 1: Rename the fixture column in `tests/conftest.py`**

In the `q7` DataFrame (line 53), `q8` DataFrame (line 61), and `q12` DataFrame (line 90), rename the dict key `"TOTAL_CONNECTIONS"` to `"TOTAL_CONNECTORS"`. Leave the value lists unchanged:
- q7: `"TOTAL_CONNECTORS": [18000, 21000, 17500, 14000],`
- q8: `"TOTAL_CONNECTORS": [18307, 1136, 412, 112],`
- q12: `"TOTAL_CONNECTORS": [1100, 1300, 1000, 800],`

- [ ] **Step 2: Rename keys/labels/columns in `tests/test_render.py`**

Make these exact replacements (values unchanged):
- `test_compute_metrics_df_connections_last_full_month` → rename function to `test_compute_metrics_df_connectors_last_full_month`; body key `metrics["kpis"]["df_connections"]` → `metrics["kpis"]["df_connectors"]`.
- In `test_compute_metrics_df_trialing_connections_last_full_month`, `..._mom_delta`: key `df_trialing_connections` → `df_trialing_connectors` (rename functions to `...connectors...` too).
- In `test_render_shows_trialing_cards` (line 262): `"Trialing Conn. (last full mo.)"` → `"Trialing Connectors (last full mo.)"`.
- The comment on line 220 (`# df_connections last full month`) → `# df_connectors last full month` (cosmetic).

- [ ] **Step 3: Run the suite to verify it fails**

Run: `python -m pytest tests/ -q`
Expected: FAIL — `render.py` still reads `df["TOTAL_CONNECTIONS"]` (now absent) → `KeyError: 'TOTAL_CONNECTIONS'`, and `kpis["df_connectors"]` is missing.

- [ ] **Step 4: Update the two chart functions in `render.py`**

In `_chart_data_fabric_trend` (lines 124-145): replace both `df["TOTAL_CONNECTIONS"]` and `trialing_df["TOTAL_CONNECTIONS"]` reads with `TOTAL_CONNECTORS`, and change the y-axis title. The three trace names (`Customer/Partner`, `Trialing`, `Tenants`) are unchanged. Resulting data/layout lines:

```python
            {"x": months, "y": df["TOTAL_CONNECTORS"].tolist(), "type": "bar",
             "name": "Customer/Partner", "marker": {"color": "#60a5fa"}, "yaxis": "y"},
            {"x": trialing_months, "y": trialing_df["TOTAL_CONNECTORS"].tolist(), "type": "bar",
             "name": "Trialing", "marker": {"color": "#f59e0b"}, "yaxis": "y"},
```
```python
            "yaxis": {"title": "Connectors", "gridcolor": "#334155"},
```

In `_chart_data_fabric_providers` (lines 148-166): replace the two `TOTAL_CONNECTIONS` references and the trace name:

```python
    df = df.sort_values("TOTAL_CONNECTORS", ascending=True)
```
```python
            {"y": labels, "x": df["TOTAL_CONNECTORS"].tolist(), "type": "bar", "orientation": "h",
             "name": "Connectors", "marker": {"color": "#60a5fa"}},
```

- [ ] **Step 5: Update `compute_metrics` in `render.py`**

In the Data Fabric block (lines 287-291):

```python
    df_connectors = int(df_cur["TOTAL_CONNECTORS"])
    df_tenants = int(df_cur["UNIQUE_TENANTS"])
    conn_delta = _pct_delta(df_cur["TOTAL_CONNECTORS"], df_prev["TOTAL_CONNECTORS"] if df_prev is not None else None)
    tenant_delta = _pct_delta(df_cur["UNIQUE_TENANTS"], df_prev["UNIQUE_TENANTS"] if df_prev is not None else None)
    df_providers = int((data["q8"]["TOTAL_CONNECTORS"] > 0).sum())
```

In the trialing block (lines 298-301):

```python
    df_trialing_connectors = int(dft_cur["TOTAL_CONNECTORS"])
    df_trialing_tenants = int(dft_cur["UNIQUE_TENANTS"])
    trialing_conn_delta = _pct_delta(dft_cur["TOTAL_CONNECTORS"], dft_prev["TOTAL_CONNECTORS"] if dft_prev is not None else None)
    trialing_tenant_delta = _pct_delta(dft_cur["UNIQUE_TENANTS"], dft_prev["UNIQUE_TENANTS"] if dft_prev is not None else None)
```

In the `kpis` dict (lines 354-361), rename the two keys and their local values:

```python
            "df_connectors": {"value": df_connectors, "delta": round(conn_delta, 1), "is_pct": True,
                              "direction": "up" if conn_delta >= 0 else "down"},
            "df_tenants": {"value": df_tenants, "delta": round(tenant_delta, 1), "is_pct": True,
                           "direction": "up" if tenant_delta >= 0 else "down"},
            "df_trialing_connectors": {"value": df_trialing_connectors, "delta": round(trialing_conn_delta, 1), "is_pct": True,
                                       "direction": "up" if trialing_conn_delta >= 0 else "down"},
            "df_trialing_tenants": {"value": df_trialing_tenants, "delta": round(trialing_tenant_delta, 1), "is_pct": True,
                                    "direction": "up" if trialing_tenant_delta >= 0 else "down"},
```

- [ ] **Step 6: Update the template `templates/report.html.j2`**

Data Fabric first card (lines 182-185): label + key refs:

```html
      <div class="kpi-label">DF Connectors (last full mo.)</div>
      <div class="kpi-value kpi-customers">{{ "{:,}".format(kpis.df_connectors.value) }}</div>
      <div class="kpi-delta {{ kpis.df_connectors.direction }}">
        {{ "▲" if kpis.df_connectors.direction == "up" else "▼" }} {{ "%+.1f"|format(kpis.df_connectors.delta) }}% MoM
```

Trialing connectors card (lines 200-203): label + key refs:

```html
      <div class="kpi-label">Trialing Connectors (last full mo.)</div>
      <div class="kpi-value kpi-customers">{{ "{:,}".format(kpis.df_trialing_connectors.value) }}</div>
      <div class="kpi-delta {{ kpis.df_trialing_connectors.direction }}">
        {{ "▲" if kpis.df_trialing_connectors.direction == "up" else "▼" }} {{ "%+.1f"|format(kpis.df_trialing_connectors.delta) }}% MoM
```

- [ ] **Step 7: Run the full suite to verify it passes**

Run: `python -m pytest tests/ -q`
Expected: PASS — all tests green (same count as before, currently 31), 0 warnings.

- [ ] **Step 8: Commit**

```bash
git add render.py templates/report.html.j2 tests/conftest.py tests/test_render.py
git commit -m "refactor: rename Data Fabric metric Connections -> Connectors (col, KPI keys, labels)"
```

---

### Task 3: Post-implementation validation (manual, requires Snowflake)

Not part of the TDD cycle — validates the SQL semantic change against live data.

- [ ] **Step 1: Run `/refresh`** (writes all 12 Parquet files with the renamed column, then `python render.py`).
  - Connection `os` (account `AX81353-OUTSYSTEMS`); one browser login may reappear.
- [ ] **Step 2: Sanity-check the corrected scale.** Confirm `TOTAL_CONNECTORS` collapsed from tens-of-thousands to low hundreds:
  - `python -c "import pandas as pd; print(pd.read_parquet('data/q7_data_fabric_monthly.parquet')[['MONTH','TOTAL_CONNECTORS']])"` — recent full month in the ~400–500 range (paying), not ~20k.
  - `python -c "import pandas as pd; print(pd.read_parquet('data/q8_data_fabric_providers.parquet')[['PROVIDER','TOTAL_CONNECTORS']])"` — provider totals sum to the low hundreds.
- [ ] **Step 3: Open `report.html` → Data Fabric tab.** Cards read "DF Connectors" / "Trialing Connectors"; trend y-axis reads "Connectors"; bars are at connector scale; providers chart legend reads "Connectors".

---

## Self-Review

**1. Spec coverage.**
- Snapshot QUALIFY in q7/q12/q8 + `metric_value>0` → Task 1 Steps 1–3. ✓
- Column rename `TOTAL_CONNECTIONS`→`TOTAL_CONNECTORS` (SQL) → Task 1; (fixtures/render/refresh) → Tasks 1–2. ✓
- KPI-key rename `df_connections`/`df_trialing_connections` → Task 2 Steps 5–6. ✓
- Chart y-axis + providers trace relabel → Task 2 Step 4. ✓
- Card-label relabel → Task 2 Step 6; asserted in Task 2 Step 2 (`Trialing Connectors...`). ✓
- refresh.md numeric-col rename → Task 1 Step 4. ✓
- SQL validated by `/refresh`, not unit tests → Task 3. ✓
- "last full month"/`_pct_delta` unchanged; fixture values unchanged → Global Constraints + Task 2 (rename-only). ✓

**2. Placeholder scan.** No TBD/TODO/"similar to"/"handle edge cases"; every code step shows full code or exact replacements. ✓

**3. Type consistency.** `TOTAL_CONNECTORS` identical across SQL (Task 1), fixtures (Task 2 Step 1), render reads (Task 2 Steps 4–5), refresh docs (Task 1 Step 4). KPI keys `df_connectors`/`df_trialing_connectors` identical across compute (Task 2 Step 5), template (Step 6), and tests (Step 2). `df_providers` still derives from `data["q8"]["TOTAL_CONNECTORS"]`. Trend trace names (`Customer/Partner`, `Trialing`, `Tenants`) untouched, so `test_data_fabric_trend_has_trialing_trace` still passes (its `y` assertion reads the `Trialing` series values 800/1000/1300/1100, unchanged). ✓
