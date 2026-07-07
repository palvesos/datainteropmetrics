# Data Fabric — Trialing-category Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a **trialing** (prospect-customer/partner) connection category to the Data Fabric tab, additive alongside the existing paying (customer/partner) numbers.

**Architecture:** Approach A — a new query `q12` mirrors `q7` with the prospect filter; `q7`/`q8` stay untouched. `render.py` reads the new Parquet into key `data_fabric_trialing` (referenced by pandas key `q12`), computes two new KPIs, and adds a second connections trace to the existing Data Fabric trend chart. The Jinja2 template gains two Trialing KPI cards. All new behaviour is covered by fixture-driven pytest — no Snowflake needed to test.

**Tech Stack:** Python 3.13, pandas, Jinja2, Plotly (client-side), pytest, Snowflake (snow CLI, refresh only).

## Global Constraints

Every task's requirements implicitly include these (copied verbatim from the spec):

- **Data Fabric tab only.** No change to Overview/Adoption/Usage/Segments/Targeting.
- **`q7`/`q8` and the paying (customer/partner) KPIs and their query logic are UNCHANGED.**
- Trialing filter is exactly: `AND comp.type IN ('prospect customer', 'prospect partner')`.
- `q12` output columns are **identical to q7**: `MONTH, UNIQUE_TENANTS, UNIQUE_CUSTOMERS, TOTAL_CONNECTIONS`.
- Paying and trialing are **disjoint** sets → the new series never double-counts.
- Tests that exercise "last complete month" logic pin `_today = pd.Timestamp("2026-06-15")` (June is the partial current month; **May is the last full month**), matching existing df tests.
- `event_sent` is VARCHAR (ISO-8601) → wrap in `TRY_TO_TIMESTAMP`; QUALIFY partitions on the natural key `(tenant, environment_id, event_provider, event_sent)`.
- Pipeline shape after this change: `/refresh` runs q1–q12 → **12** Parquet files → `load_data` → `compute_metrics` → template → `report.html`.

---

## File Structure

- **Create** `queries/q12_data_fabric_trialing_monthly.sql` — the trialing counterpart to q7 (SQL only, no unit test; verified by inspection + real `/refresh`).
- **Modify** `.claude/commands/refresh.md` — add q12 row; bump 11→12 (docs/config).
- **Modify** `tests/conftest.py` — add the `q12` fixture DataFrame.
- **Modify** `render.py` — `load_data` file_map (+q12); `compute_metrics` trialing KPIs; `_chart_data_fabric_trend` gains a trialing trace + a `trialing_df` parameter.
- **Modify** `tests/test_render.py` — update the keys test (11→12); add trialing KPI, chart, and render tests.
- **Modify** `templates/report.html.j2` — two Trialing KPI cards on the Data Fabric tab.

Task order follows the data pipeline so each task's deliverable is independently testable: SQL/config → fixture+load_data → KPIs → chart → template.

---

### Task 1: New q12 trialing query + refresh config

**Files:**
- Create: `queries/q12_data_fabric_trialing_monthly.sql`
- Modify: `.claude/commands/refresh.md`

**Interfaces:**
- Consumes: nothing (mirrors `queries/q7_data_fabric_monthly.sql`).
- Produces: SQL that outputs columns `MONTH, UNIQUE_TENANTS, UNIQUE_CUSTOMERS, TOTAL_CONNECTIONS`; `/refresh` will write `data/q12_data_fabric_trialing_monthly.parquet`.

This task is SQL + docs (no Python unit test — SQL correctness is validated by the real `/refresh` against Snowflake, which is a manual post-implementation step). Reviewer gate: filter and output shape are correct and refresh docs are consistent.

- [ ] **Step 1: Create the q12 SQL file**

Create `queries/q12_data_fabric_trialing_monthly.sql` — an exact copy of q7 with the single filter change (`prospect customer`/`prospect partner`) and an updated header comment cross-referencing q7:

```sql
-- Data context: EXTERNALCONNECTIONCOUNT, INFRASTRUCTURE (SCD2), COMPANY. Pattern: SCD2 join, provider filter.
-- TRIALING counterpart to q7 (paying customer/partner). Identical shape/logic; only the COMPANY.type filter differs.
-- NOTE: event_sent is VARCHAR (ISO-8601); cast to TIMESTAMP before date operations.
-- NOTE: QUALIFY partition = source natural key (tenant, environment_id, event_provider, event_sent); dedupes infra SCD2 fan-out only.
-- NOTE: comp.type IN ('prospect customer','prospect partner') = non-paying tenants trialing the product.
--   Disjoint from q7's ('customer','partner') set, so the two series never double-count.
--   COMPANY.type reflects CURRENT status (also 'former customer', 'internal', etc.).
WITH deduped AS (
  SELECT
    ext.event_sent,
    ext.tenant,
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
    AND TRY_TO_TIMESTAMP(ext.event_sent) >= DATEADD('month', -12, CURRENT_DATE)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ext.tenant, ext.environment_id, ext.event_provider, ext.event_sent ORDER BY infra.date_from DESC) = 1
)
SELECT
  DATE_TRUNC('month', TRY_TO_TIMESTAMP(event_sent)) AS MONTH,
  COUNT(DISTINCT tenant)                             AS UNIQUE_TENANTS,
  COUNT(DISTINCT company_sfdc_id)                    AS UNIQUE_CUSTOMERS,
  SUM(metric_value)                                  AS TOTAL_CONNECTIONS
FROM deduped
GROUP BY 1
ORDER BY 1 DESC
```

- [ ] **Step 2: Verify the filter is the only functional difference**

Run: `diff <(sed -n '9,$p' queries/q7_data_fabric_monthly.sql) <(sed -n '9,$p' queries/q12_data_fabric_trialing_monthly.sql)`
Expected: the only differing line in the query body is the `comp.type IN (...)` filter (line with `prospect customer`/`prospect partner` vs `customer`/`partner`).

- [ ] **Step 3: Add the q12 row to refresh.md**

In `.claude/commands/refresh.md`, add this row to the per-query table immediately after the q11 row (line ~57):

```markdown
| q12 | `queries/q12_data_fabric_trialing_monthly.sql` | `data/q12_data_fabric_trialing_monthly.parquet` | `'MONTH'` | — | `'UNIQUE_TENANTS'`, `'UNIQUE_CUSTOMERS'`, `'TOTAL_CONNECTIONS'` |
```

- [ ] **Step 4: Bump the "11" counts to "12" in refresh.md**

Three edits in `.claude/commands/refresh.md`:
1. Heading `### 1. Run the 11 queries and save as Parquet` → `### 1. Run the 12 queries and save as Parquet`
2. Sentence `After running all 11 queries, confirm 11 Parquet files exist in `data/` before continuing.` → `After running all 12 queries, confirm 12 Parquet files exist in `data/` before continuing.`

Run: `grep -n "12 queries\|12 Parquet\|q12" .claude/commands/refresh.md`
Expected: heading, confirm sentence, and the q12 table row all present; no remaining `11 queries` / `11 Parquet` strings.

- [ ] **Step 5: Commit**

```bash
git add queries/q12_data_fabric_trialing_monthly.sql .claude/commands/refresh.md
git commit -m "feat: q12 trialing Data Fabric query + refresh config"
```

---

### Task 2: Fixture + load_data (11 → 12 keys)

**Files:**
- Modify: `tests/conftest.py` (add `q12` to `sample_data`)
- Modify: `render.py:9-29` (`load_data` file_map)
- Test: `tests/test_render.py` (rename/extend the keys test)

**Interfaces:**
- Consumes: the q7 fixture shape (same columns).
- Produces: `sample_data["q12"]` DataFrame (columns `MONTH, UNIQUE_TENANTS, UNIQUE_CUSTOMERS, TOTAL_CONNECTIONS`); `load_data` returns a dict whose keys are `q1..q12`, with `q12` read from `data/q12_data_fabric_trialing_monthly.parquet`.

- [ ] **Step 1: Add the q12 fixture to conftest.py**

In `tests/conftest.py`, add this DataFrame after the `q11` block (after line 85, before the `return`). Values are chosen so that with `_today=2026-06-15` the last full month is **May** (`TOTAL_CONNECTIONS=1300`, `UNIQUE_TENANTS=25`), with April as the prior full month (`1000`/`20`) → connections MoM `+30.0%`, tenants MoM `+25.0%`:

```python
    q12 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "UNIQUE_TENANTS": [22, 25, 20, 15],
        "UNIQUE_CUSTOMERS": [18, 20, 16, 12],
        "TOTAL_CONNECTIONS": [1100, 1300, 1000, 800],
    })
```

Then extend the return dict (line 86-87) to include `q12`:

```python
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6,
            "q7": q7, "q8": q8, "q9": q9, "q10": q10, "q11": q11, "q12": q12}
```

- [ ] **Step 2: Update the keys test to expect 12 (write the failing test)**

In `tests/test_render.py`, replace `test_load_data_returns_eleven_keys` (lines 16-28) with:

```python
def test_load_data_returns_twelve_keys(tmp_path, sample_data):
    files = {
        "q1": "q1_adoption_trend.parquet", "q2": "q2_by_product_family.parquet",
        "q3": "q3_by_arch_type.parquet", "q4": "q4_executions.parquet",
        "q5": "q5_ao_usage.parquet", "q6": "q6_population.parquet",
        "q7": "q7_data_fabric_monthly.parquet", "q8": "q8_data_fabric_providers.parquet",
        "q9": "q9_deployment_option.parquet", "q10": "q10_sku_gap_targeting.parquet",
        "q11": "q11_infra_no_telemetry.parquet",
        "q12": "q12_data_fabric_trialing_monthly.parquet",
    }
    for key, fn in files.items():
        sample_data[key].to_parquet(tmp_path / fn, index=False)
    result = load_data(str(tmp_path))
    assert set(result.keys()) == set(files.keys())
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_render.py::test_load_data_returns_twelve_keys -v`
Expected: FAIL — `load_data` returns 11 keys, so `set(result.keys())` (11) != `set(files.keys())` (12).

- [ ] **Step 4: Add q12 to the load_data file_map**

In `render.py`, add the q12 entry to `file_map` (after the `q11` line at line 21):

```python
        "q11": "q11_infra_no_telemetry.parquet",
        "q12": "q12_data_fabric_trialing_monthly.parquet",
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_render.py::test_load_data_returns_twelve_keys -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_render.py render.py
git commit -m "feat: load q12 trialing parquet (11 -> 12 keys) + fixture"
```

---

### Task 3: Trialing KPIs in compute_metrics

**Files:**
- Modify: `render.py:270-285` (add trialing block after the q7 df block) and the returned `kpis` dict (line ~338-342)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `data["q12"]` (columns `MONTH, UNIQUE_TENANTS, UNIQUE_CUSTOMERS, TOTAL_CONNECTIONS`); the existing local `current_month_start` and the local `_pct_delta(cur, prev)` closure defined at `render.py:276`.
- Produces: `metrics["kpis"]["df_trialing_connections"]` and `metrics["kpis"]["df_trialing_tenants"]`, each a dict `{"value": int, "delta": float, "is_pct": True, "direction": "up"|"down"}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_render.py`:

```python
def test_compute_metrics_df_trialing_connections_last_full_month(sample_data):
    # today=2026-06-15 → June is partial; May (1300) is the last full month
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    assert metrics["kpis"]["df_trialing_connections"]["value"] == 1300


def test_compute_metrics_df_trialing_tenants_last_full_month(sample_data):
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    assert metrics["kpis"]["df_trialing_tenants"]["value"] == 25


def test_compute_metrics_df_trialing_connections_mom_delta(sample_data):
    # May 1300 vs April 1000 → +30.0%
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    kpi = metrics["kpis"]["df_trialing_connections"]
    assert kpi["delta"] == pytest.approx(30.0, rel=1e-3)
    assert kpi["is_pct"] is True
    assert kpi["direction"] == "up"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_render.py -k df_trialing -v`
Expected: FAIL with `KeyError: 'df_trialing_connections'`.

- [ ] **Step 3: Compute the trialing KPIs**

In `render.py`, immediately after the `df_providers = ...` line (line 285, still inside `compute_metrics` so `_pct_delta` and `current_month_start` are in scope), add:

```python
    # --- Data Fabric trialing (q12 monthly totals, last complete month) ---
    q12 = data["q12"].sort_values("MONTH", ascending=False).reset_index(drop=True)
    q12_full = q12[q12["MONTH"] < current_month_start].reset_index(drop=True)
    dft_cur = q12_full.iloc[0] if len(q12_full) else q12.iloc[0]
    dft_prev = q12_full.iloc[1] if len(q12_full) > 1 else None
    df_trialing_connections = int(dft_cur["TOTAL_CONNECTIONS"])
    df_trialing_tenants = int(dft_cur["UNIQUE_TENANTS"])
    trialing_conn_delta = _pct_delta(dft_cur["TOTAL_CONNECTIONS"], dft_prev["TOTAL_CONNECTIONS"] if dft_prev is not None else None)
    trialing_tenant_delta = _pct_delta(dft_cur["UNIQUE_TENANTS"], dft_prev["UNIQUE_TENANTS"] if dft_prev is not None else None)
```

- [ ] **Step 4: Add the KPIs to the returned dict**

In `render.py`, in the `kpis` dict, add these two entries immediately after the `df_tenants` entry (after line 341, before `df_providers`):

```python
            "df_trialing_connections": {"value": df_trialing_connections, "delta": round(trialing_conn_delta, 1), "is_pct": True,
                                        "direction": "up" if trialing_conn_delta >= 0 else "down"},
            "df_trialing_tenants": {"value": df_trialing_tenants, "delta": round(trialing_tenant_delta, 1), "is_pct": True,
                                    "direction": "up" if trialing_tenant_delta >= 0 else "down"},
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_render.py -k df_trialing -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: df_trialing_connections + df_trialing_tenants KPIs"
```

---

### Task 4: Trialing trace on the Data Fabric trend chart

**Files:**
- Modify: `render.py:123-139` (`_chart_data_fabric_trend`) and its call site at `render.py:354`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `data["q7"]` (paying) and `data["q12"]` (trialing), both with `MONTH` + `TOTAL_CONNECTIONS` + `UNIQUE_TENANTS`.
- Produces: chart `metrics["charts"]["data_fabric_trend"]` whose `data` list contains three traces named `"Customer/Partner"` (paying connections, bar), `"Trialing"` (trialing connections, bar), and `"Tenants"` (paying tenants, line on y2).

> Note on the spec's "trend chart has 2 traces" testing line: the existing trend chart already has two traces (a connections bar + a tenants line). The spec's intent is a **second connections category**, so after this task there are two connections bars (`Customer/Partner`, `Trialing`) plus the unchanged tenants line = 3 traces total. The test asserts trace *names* (robust) rather than a raw count.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_render.py`:

```python
def test_data_fabric_trend_has_trialing_trace(sample_data):
    metrics = compute_metrics(sample_data)
    trend = metrics["charts"]["data_fabric_trend"]
    names = [t.get("name") for t in trend["data"]]
    assert "Customer/Partner" in names
    assert "Trialing" in names
    assert "Tenants" in names
    # Trialing connections series, months sorted ascending (Mar..Jun): 800,1000,1300,1100
    trialing = next(t for t in trend["data"] if t.get("name") == "Trialing")
    assert trialing["y"] == [800, 1000, 1300, 1100]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_render.py::test_data_fabric_trend_has_trialing_trace -v`
Expected: FAIL — no `"Trialing"` trace (and the paying trace is still named `"Connections"`), plus `_chart_data_fabric_trend` takes only one arg.

- [ ] **Step 3: Rewrite `_chart_data_fabric_trend` to take the trialing df and add the trace**

In `render.py`, replace the entire `_chart_data_fabric_trend` function (lines 123-139) with:

```python
def _chart_data_fabric_trend(df: pd.DataFrame, trialing_df: pd.DataFrame) -> dict:
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    trialing_df = trialing_df.sort_values("MONTH")
    trialing_months = trialing_df["MONTH"].dt.strftime("%Y-%m").tolist()
    return {
        "data": [
            {"x": months, "y": df["TOTAL_CONNECTIONS"].tolist(), "type": "bar",
             "name": "Customer/Partner", "marker": {"color": "#60a5fa"}, "yaxis": "y"},
            {"x": trialing_months, "y": trialing_df["TOTAL_CONNECTIONS"].tolist(), "type": "bar",
             "name": "Trialing", "marker": {"color": "#f59e0b"}, "yaxis": "y"},
            {"x": months, "y": df["UNIQUE_TENANTS"].tolist(), "type": "scatter",
             "mode": "lines+markers", "name": "Tenants", "line": {"color": "#34d399", "width": 2}, "yaxis": "y2"},
        ],
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Connections", "gridcolor": "#334155"},
            "yaxis2": {"title": "Tenants", "overlaying": "y", "side": "right", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"}, "margin": {"t": 20, "b": 50, "l": 70, "r": 60}, "autosize": True,
        },
    }
```

- [ ] **Step 4: Update the call site**

In `render.py`, in the `charts` dict (line 354), change:

```python
            "data_fabric_trend": _chart_data_fabric_trend(data["q7"]),
```

to:

```python
            "data_fabric_trend": _chart_data_fabric_trend(data["q7"], data["q12"]),
```

- [ ] **Step 5: Run the new test plus the chart-invariant tests to verify they pass**

Run: `python -m pytest tests/test_render.py -k "trend or has_all_charts or chart_has_data" -v`
Expected: PASS — new trialing-trace test passes; `test_compute_metrics_has_all_charts` and `test_compute_metrics_chart_has_data_and_layout` still pass (chart set and non-empty data unchanged).

- [ ] **Step 6: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: add Trialing trace to Data Fabric trend chart"
```

---

### Task 5: Trialing KPI cards in the template

**Files:**
- Modify: `templates/report.html.j2:195-198` (Data Fabric tab kpi-grid)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `kpis.df_trialing_connections` and `kpis.df_trialing_tenants` (from Task 3).
- Produces: rendered HTML in the Data Fabric tab containing the labels `Trialing Conn. (last full mo.)` and `Trialing Tenants (last full mo.)` with comma-formatted values and MoM deltas.

- [ ] **Step 1: Write the failing render test**

Append to `tests/test_render.py`:

```python
def test_render_shows_trialing_cards(sample_data, tmp_path):
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    # Card labels are unique to the template (the "Trialing" chart trace name has no comma-formatted value)
    assert "Trialing Conn. (last full mo.)" in content
    assert "Trialing Tenants (last full mo.)" in content
    assert "1,300" in content   # trialing connections, last full month, comma-formatted (KPI card only)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_render.py::test_render_shows_trialing_cards -v`
Expected: FAIL — the card labels and the comma-formatted `1,300` are not in the HTML yet.

- [ ] **Step 3: Add the two Trialing cards to the Data Fabric tab**

In `templates/report.html.j2`, inside the Data Fabric `kpi-grid`, add these two cards immediately after the "Active Providers" card (after line 198, `</div>` closing that kpi-card, before the `</div>` closing the kpi-grid at line 199):

```html
    <div class="kpi-card">
      <div class="kpi-label">Trialing Conn. (last full mo.)</div>
      <div class="kpi-value kpi-customers">{{ "{:,}".format(kpis.df_trialing_connections.value) }}</div>
      <div class="kpi-delta {{ kpis.df_trialing_connections.direction }}">
        {{ "▲" if kpis.df_trialing_connections.direction == "up" else "▼" }} {{ "%+.1f"|format(kpis.df_trialing_connections.delta) }}% MoM
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Trialing Tenants (last full mo.)</div>
      <div class="kpi-value kpi-adoption">{{ "{:,}".format(kpis.df_trialing_tenants.value) }}</div>
      <div class="kpi-delta {{ kpis.df_trialing_tenants.direction }}">
        {{ "▲" if kpis.df_trialing_tenants.direction == "up" else "▼" }} {{ "%+.1f"|format(kpis.df_trialing_tenants.delta) }}% MoM
      </div>
    </div>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_render.py::test_render_shows_trialing_cards -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS — all prior tests (26) plus the new trialing tests, 0 warnings.

- [ ] **Step 6: Commit**

```bash
git add templates/report.html.j2 tests/test_render.py
git commit -m "feat: Trialing KPI cards on Data Fabric tab"
```

---

## Post-implementation validation (manual, requires Snowflake)

Not part of the TDD cycle — the feature is only "live" once real data flows in.

- [ ] Run `/refresh` (writes all 12 Parquet files, including `data/q12_data_fabric_trialing_monthly.parquet`, then `python render.py`).
  - Connection `os` (account `AX81353-OUTSYSTEMS`); one browser login may reappear.
  - Note: after Task 2, `python render.py` **requires** the q12 Parquet — `load_data` raises `FileNotFoundError` until `/refresh` produces it.
- [ ] Open `report.html` → Data Fabric tab: confirm the two Trialing cards render and the trend chart shows a distinct amber "Trialing" bar series alongside the blue "Customer/Partner" bars.
- [ ] Sanity-check trialing < paying and non-zero for recent months (spec cited ~1.1k prospect connections in June 2026).

---

## Self-Review

**1. Spec coverage.**
- New `q12_data_fabric_trialing_monthly.sql` (copy of q7 + prospect filter, identical output) → Task 1. ✓
- `load_data` 11→12 key `data_fabric_trialing` → Task 2 (dict key `q12`, Parquet `q12_data_fabric_trialing_monthly.parquet`). ✓
- `compute_metrics` `df_trialing_connections` + `df_trialing_tenants` with MoM delta, reusing `current_month_start` + `_pct_delta` → Task 3. ✓
- `_chart_data_fabric_trend` 2nd "Trialing" trace, paying relabelled "Customer/Partner", distinct color → Task 4. ✓
- Template Trialing KPI card(s) → Task 5. ✓
- `refresh.md` q12 row + 11→12 bumps → Task 1. ✓
- Tests: q12 fixture pinned to 2026-06-15; load_data 12 keys; trialing KPIs value+delta; trend trace; render card+value → Tasks 2–5. ✓
- Non-goals (no q8/providers change, no other tabs, paying KPIs untouched) → enforced by Global Constraints; q7/q8/q9 code paths untouched. ✓

**2. Placeholder scan.** No TBD/TODO/"handle edge cases"/"similar to Task N"; every code step shows full code. ✓

**3. Type consistency.** KPI keys `df_trialing_connections`/`df_trialing_tenants` identical across Task 3 (compute), Task 5 (template), and tests. Chart trace names `Customer/Partner`/`Trialing`/`Tenants` identical across Task 4 code and test. `_chart_data_fabric_trend(df, trialing_df)` signature matches its single call site `_chart_data_fabric_trend(data["q7"], data["q12"])`. Fixture values (May=1300/25, April=1000/20 → +30.0%/+25.0%) match every asserted number. ✓

**Deviation noted:** the spec's "trend chart has 2 traces" test line is superseded by a name-based assertion (3 traces total: two connections bars + the unchanged tenants line), because the existing chart already carries a tenants line. Rationale documented in Task 4.
