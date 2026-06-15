# Data Interoperability KPI Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dark-themed, tabbed HTML report that visualises Data Interoperability adoption KPIs, refreshed on demand via a `/refresh` Claude Code slash command that fetches from Snowflake and stores results as Parquet.

**Architecture:** Claude Code executes the `/refresh` command, which runs 6 SQL queries via `snow sql`, persists each result as a Parquet file in `data/`, then runs `render.py`. `render.py` reads the Parquet files with pandas, computes derived metrics (KPI cards, MoM deltas, chart datasets), and renders `templates/report.html.j2` via Jinja2 into `report.html`. The HTML is self-contained and opens directly in a browser.

**Tech Stack:** Python 3.11+, pandas, pyarrow, jinja2, Plotly.js (CDN), Snowflake CLI (`uvx snowflake-cli`), pytest

---

## File Map

| File | Purpose |
|---|---|
| `.gitignore` | Exclude `data/`, `report.html`, `.superpowers/`, `__pycache__/` |
| `requirements.txt` | pandas, pyarrow, jinja2, pytest |
| `queries/q1_adoption_trend.sql` | Monthly adoption trend — last 12 months |
| `queries/q2_by_product_family.sql` | Current snapshot by product family |
| `queries/q3_by_arch_type.sql` | By architecture type — current month |
| `queries/q4_executions.sql` | Connector executions by month |
| `queries/q5_ao_usage.sql` | Monthly AO usage trend |
| `queries/q6_population.sql` | All-time population snapshot |
| `data/*.parquet` | Parquet output — gitignored, written by `/refresh` |
| `render.py` | Loads Parquet → computes metrics → renders Jinja2 template |
| `templates/report.html.j2` | Jinja2 template — dark theme, 4 tabs, Plotly charts |
| `report.html` | Generated output — gitignored |
| `tests/conftest.py` | pytest fixtures — in-memory sample DataFrames |
| `tests/test_render.py` | Unit tests for `load_data`, `compute_metrics`, `render` |
| `.claude/commands/refresh.md` | `/refresh` slash command definition |

---

## Task 1: Bootstrap project

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `data/.gitkeep`

- [ ] **Step 1: Create .gitignore**

```
data/
report.html
.superpowers/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
```

Write to `.gitignore`.

- [ ] **Step 2: Create requirements.txt**

```
pandas
pyarrow
jinja2
pytest
```

Write to `requirements.txt`.

- [ ] **Step 3: Create data directory placeholder**

```bash
mkdir -p data && touch data/.gitkeep
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: packages install without errors.

- [ ] **Step 5: Commit**

```bash
git add .gitignore requirements.txt data/.gitkeep
git commit -m "chore: bootstrap project structure"
```

---

## Task 2: SQL query files

**Files:**
- Create: `queries/q1_adoption_trend.sql`
- Create: `queries/q2_by_product_family.sql`
- Create: `queries/q3_by_arch_type.sql`
- Create: `queries/q4_executions.sql`
- Create: `queries/q5_ao_usage.sql`
- Create: `queries/q6_population.sql`

- [ ] **Step 1: Create queries directory**

```bash
mkdir -p queries
```

- [ ] **Step 2: Write q1_adoption_trend.sql**

```sql
SELECT
  TO_DATE(CAST(DATE_ID AS VARCHAR), 'YYYYMMDD') AS MONTH_START,
  COUNT(DISTINCT CASE WHEN IS_INTEROPERABILITY = TRUE THEN COMPANY_ID END) AS INTEROP_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN HAS_SKU_INTEROPERABILITY = TRUE THEN COMPANY_ID END) AS SKU_INTEROP_CUSTOMERS,
  COUNT(DISTINCT COMPANY_ID) AS TOTAL_CUSTOMERS,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN IS_INTEROPERABILITY = TRUE THEN COMPANY_ID END) / NULLIF(COUNT(DISTINCT COMPANY_ID), 0), 2) AS ADOPTION_PCT
FROM CANONICAL.CUSTOMERSUCCESS.MONTHLYCOMPANYPRODUCTEDITIONCATEGORY
WHERE DATE_ID >= REPLACE(CAST(DATEADD('month', -12, CURRENT_DATE) AS VARCHAR(10)), '-', '')
GROUP BY 1
ORDER BY 1 DESC
```

- [ ] **Step 3: Write q2_by_product_family.sql**

```sql
SELECT
  PRODUCT_FAMILY,
  PRODUCT_CATEGORY,
  COUNT(DISTINCT COMPANY_ID) AS TOTAL_CUSTOMERS,
  COUNT(DISTINCT CASE WHEN IS_INTEROPERABILITY = TRUE THEN COMPANY_ID END) AS INTEROP_ACTIVE,
  COUNT(DISTINCT CASE WHEN HAS_SKU_INTEROPERABILITY = TRUE THEN COMPANY_ID END) AS HAS_SKU_INTEROP
FROM CANONICAL.CUSTOMERSUCCESS.MONTHLYCOMPANYPRODUCTEDITIONCATEGORY
WHERE DATE_ID = (SELECT MAX(DATE_ID) FROM CANONICAL.CUSTOMERSUCCESS.MONTHLYCOMPANYPRODUCTEDITIONCATEGORY)
GROUP BY 1, 2
ORDER BY INTEROP_ACTIVE DESC
```

- [ ] **Step 4: Write q3_by_arch_type.sql**

```sql
SELECT
  INFRA_ARCH_TYPE,
  PRODUCT_FAMILY,
  COUNT(DISTINCT COMPANY_SFDC_ID) AS COMPANIES,
  COUNT(DISTINCT CASE WHEN IS_INTEROPERABILITY = TRUE THEN COMPANY_SFDC_ID END) AS INTEROP_COMPANIES,
  COUNT(DISTINCT CASE WHEN HAS_SKU_INTEROPERABILITY = TRUE THEN COMPANY_SFDC_ID END) AS SKU_INTEROP
FROM CANONICAL.CUSTOMERSUCCESS.MONTHLYCOMPANYINFRAPRODUCTEDITIONCATEGORY
WHERE USAGEDATE = (SELECT MAX(USAGEDATE) FROM CANONICAL.CUSTOMERSUCCESS.MONTHLYCOMPANYINFRAPRODUCTEDITIONCATEGORY)
GROUP BY 1, 2
ORDER BY INTEROP_COMPANIES DESC
```

- [ ] **Step 5: Write q4_executions.sql**

```sql
SELECT
  DATE_TRUNC('month', DATE) AS MONTH,
  COUNT(DISTINCT INFRASTRUCTURE_ID) AS ACTIVE_INFRA,
  SUM(INTEROPERABILITY_AGGREGATED_EXECUTIONS_PROD_SUM) AS PROD_EXECUTIONS,
  SUM(INTEROPERABILITY_AGGREGATED_EXECUTIONS_DEV_SUM) AS DEV_EXECUTIONS,
  SUM(INTEROPERABILITY_AGGREGATED_EXECUTIONS_NONPROD_SUM) AS NONPROD_EXECUTIONS,
  SUM(INTEROPERABILITY_AGGREGATED_USAGE_AO_VALUE_PROD_SUM) AS PROD_AO_USAGE
FROM CANONICAL.CUSTOMERSUCCESS.PLATFORMUTILIZATIONDAILYINFRASTRUCTUREAGG
WHERE DATE >= DATEADD('month', -7, CURRENT_DATE)
  AND (INTEROPERABILITY_AGGREGATED_EXECUTIONS_PROD_SUM > 0
       OR INTEROPERABILITY_AGGREGATED_EXECUTIONS_DEV_SUM > 0
       OR INTEROPERABILITY_AGGREGATED_EXECUTIONS_NONPROD_SUM > 0)
GROUP BY 1
ORDER BY 1 DESC
```

- [ ] **Step 6: Write q5_ao_usage.sql**

```sql
SELECT
  TO_DATE(CAST(DATE_ID AS VARCHAR), 'YYYYMMDD') AS REPORT_MONTH,
  COUNT(DISTINCT INFRASTRUCTURE_ID) AS ACTIVE_INFRA,
  SUM(INTEROPERABILITY_AGGREGATED_USAGE_AO_VALUE_PROD_LASTWEEK) AS PROD_AO_LAST_WEEK,
  SUM(INTEROPERABILITY_AGGREGATED_USAGE_AO_VALUE_DEV_LASTWEEK) AS DEV_AO_LAST_WEEK,
  SUM(INTEROPERABILITY_AGGREGATED_USAGE_AO_VALUE_PROD_MAXWEEK) AS PROD_AO_MAX_WEEK,
  SUM(INTEROPERABILITY_AGGREGATED_USAGE_AO_VALUE_DEV_MAXWEEK) AS DEV_AO_MAX_WEEK
FROM CANONICAL.CUSTOMERSUCCESS.PLATFORMUTILIZATIONMONTHLYINFRASTRUCTUREAGG_TOTAL
WHERE DATE_ID >= REPLACE(CAST(DATEADD('month', -7, CURRENT_DATE) AS VARCHAR(10)), '-', '')
  AND (INTEROPERABILITY_AGGREGATED_USAGE_AO_VALUE_PROD_LASTWEEK > 0
       OR INTEROPERABILITY_AGGREGATED_USAGE_AO_VALUE_DEV_LASTWEEK > 0)
GROUP BY 1
ORDER BY 1 DESC
```

- [ ] **Step 7: Write q6_population.sql**

```sql
SELECT
  IS_INTEROPERABILITY,
  HAS_SKU_INTEROPERABILITY,
  COUNT(*) AS COMPANY_COUNT
FROM CANONICAL.CUSTOMERSUCCESS.CUSTOMERUNIFIEDINFO
GROUP BY 1, 2
ORDER BY 1, 2
```

- [ ] **Step 8: Commit**

```bash
git add queries/
git commit -m "feat: add 6 KPI SQL queries"
```

---

## Task 3: render.py skeleton + test fixtures

**Files:**
- Create: `render.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_render.py`

- [ ] **Step 1: Create render.py with function stubs**

```python
import json
import os
from datetime import date

import pandas as pd
from jinja2 import Environment, FileSystemLoader


def load_data(data_dir: str = "data") -> dict:
    raise NotImplementedError


def compute_metrics(data: dict) -> dict:
    raise NotImplementedError


def render(metrics: dict, template_path: str = "templates/report.html.j2", output_path: str = "report.html") -> None:
    raise NotImplementedError


if __name__ == "__main__":
    data = load_data()
    metrics = compute_metrics(data)
    render(metrics)
    print(f"Report written to report.html")
```

- [ ] **Step 2: Create tests/__init__.py**

Empty file:
```bash
mkdir -p tests && touch tests/__init__.py
```

- [ ] **Step 3: Create tests/conftest.py with sample DataFrames**

```python
import pandas as pd
import pytest


@pytest.fixture
def sample_data():
    q1 = pd.DataFrame({
        "MONTH_START": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "INTEROP_CUSTOMERS": [582, 573, 555, 517],
        "SKU_INTEROP_CUSTOMERS": [522, 513, 497, 461],
        "TOTAL_CUSTOMERS": [2884, 2913, 2914, 2927],
        "ADOPTION_PCT": [20.18, 19.67, 19.05, 17.66],
    })
    q2 = pd.DataFrame({
        "PRODUCT_FAMILY": ["O11/ODC", "O11", "ODC", "O11", "O11"],
        "PRODUCT_CATEGORY": ["O11/ODC", "O11 Cloud", "ODC", "O11 On-Prem", "O11 Mix"],
        "TOTAL_CUSTOMERS": [775, 668, 469, 913, 45],
        "INTEROP_ACTIVE": [582, 0, 0, 0, 0],
        "HAS_SKU_INTEROP": [522, 0, 0, 0, 0],
    })
    q3 = pd.DataFrame({
        "INFRA_ARCH_TYPE": ["cloud", "cloud", "on-premises", "hybrid"],
        "PRODUCT_FAMILY": ["ODC", "O11", "O11", "O11"],
        "COMPANIES": [1241, 1263, 1212, 31],
        "INTEROP_COMPANIES": [582, 414, 163, 6],
        "SKU_INTEROP": [522, 370, 146, 4],
    })
    q4 = pd.DataFrame({
        "MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "ACTIVE_INFRA": [157, 237, 215, 311],
        "PROD_EXECUTIONS": [38462, 114734, 74750, 34260],
        "DEV_EXECUTIONS": [33788, 119536, 98094, 40394],
        "NONPROD_EXECUTIONS": [4208, 16460, 8502, 13002],
        "PROD_AO_USAGE": [1788454, 4952590, 4138558, 4454132],
    })
    q5 = pd.DataFrame({
        "REPORT_MONTH": pd.to_datetime(["2026-06-01", "2026-05-01", "2026-04-01", "2026-03-01"]),
        "ACTIVE_INFRA": [1153, 1141, 1095, 1028],
        "PROD_AO_LAST_WEEK": [2050181, 2033225, 1996318, 1915323],
        "DEV_AO_LAST_WEEK": [3517256, 3508328, 3368541, 3210840],
        "PROD_AO_MAX_WEEK": [2060337, 2122011, 2050587, 1964686],
        "DEV_AO_MAX_WEEK": [3534152, 3543463, 3413880, 3225250],
    })
    q6 = pd.DataFrame({
        "IS_INTEROPERABILITY": [False, True, True],
        "HAS_SKU_INTEROPERABILITY": [False, False, True],
        "COMPANY_COUNT": [182420, 430, 3451],
    })
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6}
```

- [ ] **Step 4: Create tests/test_render.py with all failing tests**

```python
import os
import tempfile

import pandas as pd
import pytest

from render import compute_metrics, load_data, render


# --- load_data ---

def test_load_data_returns_six_keys(tmp_path, sample_data):
    for name, filename in [
        ("q1", "q1_adoption_trend.parquet"),
        ("q2", "q2_by_product_family.parquet"),
        ("q3", "q3_by_arch_type.parquet"),
        ("q4", "q4_executions.parquet"),
        ("q5", "q5_ao_usage.parquet"),
        ("q6", "q6_population.parquet"),
    ]:
        sample_data[name].to_parquet(tmp_path / filename, index=False)

    result = load_data(str(tmp_path))

    assert set(result.keys()) == {"q1", "q2", "q3", "q4", "q5", "q6"}
    assert len(result["q1"]) == 4


def test_load_data_raises_if_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_data(str(tmp_path))


# --- compute_metrics ---

def test_compute_metrics_kpi_adoption_pct(sample_data):
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["adoption_pct"]["value"] == pytest.approx(20.18, rel=1e-3)


def test_compute_metrics_kpi_active_customers(sample_data):
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["active_customers"]["value"] == 582


def test_compute_metrics_mom_delta_adoption(sample_data):
    metrics = compute_metrics(sample_data)
    delta = metrics["kpis"]["adoption_pct"]["delta"]
    assert delta == pytest.approx(20.18 - 19.67, rel=1e-2)
    assert metrics["kpis"]["adoption_pct"]["direction"] == "up"


def test_compute_metrics_mom_delta_customers(sample_data):
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["active_customers"]["delta"] == 9
    assert metrics["kpis"]["active_customers"]["direction"] == "up"


def test_compute_metrics_prod_executions_uses_last_full_month(sample_data):
    # June is the current partial month; May (114734) should be the KPI value
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["prod_executions"]["value"] == 114734


def test_compute_metrics_prod_ao_last_week(sample_data):
    metrics = compute_metrics(sample_data)
    assert metrics["kpis"]["prod_ao_last_week"]["value"] == 2050181


def test_compute_metrics_sku_gap(sample_data):
    # IS_INTEROP=True, HAS_SKU=False → 430 companies
    metrics = compute_metrics(sample_data)
    assert metrics["sku_gap"] == 430


def test_compute_metrics_has_all_charts(sample_data):
    metrics = compute_metrics(sample_data)
    expected = {
        "adoption_trend", "population_donut",
        "executions_bar", "ao_usage_line",
        "product_family_bar", "arch_type_bar",
    }
    assert set(metrics["charts"].keys()) == expected


def test_compute_metrics_chart_has_data_and_layout(sample_data):
    metrics = compute_metrics(sample_data)
    for name, chart in metrics["charts"].items():
        assert "data" in chart, f"{name} missing 'data'"
        assert "layout" in chart, f"{name} missing 'layout'"
        assert len(chart["data"]) > 0, f"{name} has empty data"


def test_compute_metrics_adoption_trend_table(sample_data):
    metrics = compute_metrics(sample_data)
    rows = metrics["tables"]["adoption_trend"]
    assert len(rows) == 4
    assert rows[0]["month"] == "2026-06"
    assert rows[0]["interop"] == 582
    assert rows[0]["adoption_pct"] == pytest.approx(20.18, rel=1e-3)


def test_compute_metrics_has_generated_at(sample_data):
    metrics = compute_metrics(sample_data)
    assert "generated_at" in metrics
    assert len(metrics["generated_at"]) > 0


# --- render ---

def test_render_writes_html_file(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    assert os.path.exists(output)


def test_render_output_contains_plotly(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "plotly" in content.lower()


def test_render_output_contains_kpi_value(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "20.18" in content


def test_render_output_has_four_tabs(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    for tab in ("Overview", "Adoption", "Usage", "Segments"):
        assert tab in content
```

- [ ] **Step 5: Run tests — verify all fail**

```bash
pytest tests/test_render.py -v 2>&1 | head -40
```

Expected: all tests fail with `NotImplementedError` or `ImportError`.

- [ ] **Step 6: Commit skeleton**

```bash
git add render.py tests/
git commit -m "test: add render.py skeleton and all failing tests"
```

---

## Task 4: Implement load_data()

**Files:**
- Modify: `render.py`

- [ ] **Step 1: Write the failing test for load_data (already in test file — confirm)**

```bash
pytest tests/test_render.py::test_load_data_returns_six_keys tests/test_render.py::test_load_data_raises_if_file_missing -v
```

Expected: both FAIL with `NotImplementedError`.

- [ ] **Step 2: Implement load_data()**

Replace the `load_data` stub in `render.py`:

```python
def load_data(data_dir: str = "data") -> dict:
    file_map = {
        "q1": "q1_adoption_trend.parquet",
        "q2": "q2_by_product_family.parquet",
        "q3": "q3_by_arch_type.parquet",
        "q4": "q4_executions.parquet",
        "q5": "q5_ao_usage.parquet",
        "q6": "q6_population.parquet",
    }
    result = {}
    for key, filename in file_map.items():
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing Parquet file: {path}. Run /refresh first.")
        result[key] = pd.read_parquet(path)
    return result
```

- [ ] **Step 3: Run load_data tests**

```bash
pytest tests/test_render.py::test_load_data_returns_six_keys tests/test_render.py::test_load_data_raises_if_file_missing -v
```

Expected: both PASS.

- [ ] **Step 4: Commit**

```bash
git add render.py
git commit -m "feat: implement load_data()"
```

---

## Task 5: Implement compute_metrics()

**Files:**
- Modify: `render.py`

- [ ] **Step 1: Run compute_metrics tests — confirm they fail**

```bash
pytest tests/test_render.py -k "compute_metrics" -v 2>&1 | tail -20
```

Expected: all fail with `NotImplementedError`.

- [ ] **Step 2: Implement chart helper functions**

Add these private functions to `render.py` (before `compute_metrics`):

```python
def _chart_adoption_trend(df: pd.DataFrame) -> dict:
    df = df.sort_values("MONTH_START")
    months = df["MONTH_START"].dt.strftime("%Y-%m").tolist()
    return {
        "data": [
            {
                "x": months, "y": df["INTEROP_CUSTOMERS"].tolist(),
                "type": "scatter", "mode": "lines+markers", "name": "Interop Customers",
                "line": {"color": "#60a5fa", "width": 2}, "yaxis": "y",
            },
            {
                "x": months, "y": df["ADOPTION_PCT"].tolist(),
                "type": "scatter", "mode": "lines+markers", "name": "Adoption %",
                "line": {"color": "#34d399", "width": 2}, "yaxis": "y2",
            },
        ],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a",
            "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Customers", "gridcolor": "#334155"},
            "yaxis2": {"title": "Adoption %", "overlaying": "y", "side": "right", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b", "bordercolor": "#334155"},
            "margin": {"t": 20, "b": 50, "l": 60, "r": 60},
            "autosize": True,
        },
    }


def _chart_population_donut(df: pd.DataFrame) -> dict:
    sku = int(df[(df["IS_INTEROPERABILITY"] == True) & (df["HAS_SKU_INTEROPERABILITY"] == True)]["COMPANY_COUNT"].sum())
    no_sku = int(df[(df["IS_INTEROPERABILITY"] == True) & (df["HAS_SKU_INTEROPERABILITY"] == False)]["COMPANY_COUNT"].sum())
    non_interop = int(df[df["IS_INTEROPERABILITY"] == False]["COMPANY_COUNT"].sum())
    return {
        "data": [{
            "values": [sku, no_sku, non_interop],
            "labels": ["Interop w/ SKU", "Interop w/o SKU", "No Interop"],
            "type": "pie", "hole": 0.6,
            "marker": {"colors": ["#34d399", "#f59e0b", "#1e293b"]},
            "textinfo": "label+percent",
        }],
        "layout": {
            "paper_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "margin": {"t": 20, "b": 20, "l": 20, "r": 20},
            "legend": {"bgcolor": "#1e293b"}, "autosize": True,
        },
    }


def _chart_executions_bar(df: pd.DataFrame) -> dict:
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    return {
        "data": [
            {"x": months, "y": df["PROD_EXECUTIONS"].tolist(), "type": "bar", "name": "Prod", "marker": {"color": "#60a5fa"}},
            {"x": months, "y": df["DEV_EXECUTIONS"].tolist(), "type": "bar", "name": "Dev", "marker": {"color": "#34d399"}},
            {"x": months, "y": df["NONPROD_EXECUTIONS"].tolist(), "type": "bar", "name": "Nonprod", "marker": {"color": "#f59e0b"}},
        ],
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a",
            "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"},
            "yaxis": {"title": "Executions", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 70, "r": 20},
            "autosize": True,
        },
    }


def _chart_ao_usage_line(df: pd.DataFrame) -> dict:
    df = df.sort_values("REPORT_MONTH")
    months = df["REPORT_MONTH"].dt.strftime("%Y-%m").tolist()
    return {
        "data": [
            {"x": months, "y": df["PROD_AO_LAST_WEEK"].tolist(), "type": "scatter", "mode": "lines+markers",
             "name": "Prod AO", "line": {"color": "#a78bfa", "width": 2}},
            {"x": months, "y": df["DEV_AO_LAST_WEEK"].tolist(), "type": "scatter", "mode": "lines+markers",
             "name": "Dev AO", "line": {"color": "#f472b6", "width": 2}},
        ],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a",
            "font": {"color": "#94a3b8"},
            "yaxis": {"title": "AO Value (last week)", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 80, "r": 20},
            "autosize": True,
        },
    }


def _chart_product_family_bar(df: pd.DataFrame) -> dict:
    df = df.sort_values("INTEROP_ACTIVE", ascending=True)
    labels = (df["PRODUCT_FAMILY"] + " / " + df["PRODUCT_CATEGORY"]).tolist()
    return {
        "data": [
            {"y": labels, "x": df["TOTAL_CUSTOMERS"].tolist(), "type": "bar", "orientation": "h",
             "name": "Total", "marker": {"color": "#334155"}},
            {"y": labels, "x": df["HAS_SKU_INTEROP"].tolist(), "type": "bar", "orientation": "h",
             "name": "Has SKU", "marker": {"color": "#34d399"}},
            {"y": labels, "x": df["INTEROP_ACTIVE"].tolist(), "type": "bar", "orientation": "h",
             "name": "Interop Active", "marker": {"color": "#60a5fa"}},
        ],
        "layout": {
            "barmode": "overlay",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a",
            "font": {"color": "#94a3b8"},
            "xaxis": {"title": "Customers", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 130, "r": 20},
            "autosize": True,
        },
    }


def _chart_arch_type_bar(df: pd.DataFrame) -> dict:
    df = df.sort_values("INTEROP_COMPANIES", ascending=True)
    labels = (df["INFRA_ARCH_TYPE"] + " / " + df["PRODUCT_FAMILY"]).tolist()
    return {
        "data": [
            {"y": labels, "x": df["COMPANIES"].tolist(), "type": "bar", "orientation": "h",
             "name": "Total", "marker": {"color": "#334155"}},
            {"y": labels, "x": df["SKU_INTEROP"].tolist(), "type": "bar", "orientation": "h",
             "name": "Has SKU", "marker": {"color": "#34d399"}},
            {"y": labels, "x": df["INTEROP_COMPANIES"].tolist(), "type": "bar", "orientation": "h",
             "name": "Interop", "marker": {"color": "#60a5fa"}},
        ],
        "layout": {
            "barmode": "overlay",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a",
            "font": {"color": "#94a3b8"},
            "xaxis": {"title": "Companies", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 140, "r": 20},
            "autosize": True,
        },
    }
```

- [ ] **Step 3: Implement compute_metrics()**

Replace the `compute_metrics` stub in `render.py`:

```python
def compute_metrics(data: dict) -> dict:
    from datetime import datetime, timezone

    q1 = data["q1"].sort_values("MONTH_START", ascending=False).reset_index(drop=True)
    q4 = data["q4"].sort_values("MONTH", ascending=False).reset_index(drop=True)
    q5 = data["q5"].sort_values("REPORT_MONTH", ascending=False).reset_index(drop=True)
    q6 = data["q6"]

    # Current month from q1 (most recent row)
    cur = q1.iloc[0]
    prev = q1.iloc[1] if len(q1) > 1 else None

    adoption_pct = float(cur["ADOPTION_PCT"])
    adoption_delta = float(cur["ADOPTION_PCT"] - prev["ADOPTION_PCT"]) if prev is not None else 0.0

    active_customers = int(cur["INTEROP_CUSTOMERS"])
    customers_delta = int(cur["INTEROP_CUSTOMERS"] - prev["INTEROP_CUSTOMERS"]) if prev is not None else 0

    # Last FULL month for executions: skip current partial month
    today = pd.Timestamp.today().normalize()
    current_month_start = today.replace(day=1)
    q4_full = q4[q4["MONTH"] < current_month_start].reset_index(drop=True)
    q4_last = q4_full.iloc[0] if len(q4_full) > 0 else q4.iloc[0]
    q4_prev = q4_full.iloc[1] if len(q4_full) > 1 else None
    prod_executions = int(q4_last["PROD_EXECUTIONS"])
    if q4_prev is not None and q4_prev["PROD_EXECUTIONS"] > 0:
        executions_delta_pct = float(
            (q4_last["PROD_EXECUTIONS"] - q4_prev["PROD_EXECUTIONS"]) / q4_prev["PROD_EXECUTIONS"] * 100
        )
    else:
        executions_delta_pct = 0.0

    # Current month AO from q5 (most recent row)
    q5_cur = q5.iloc[0]
    q5_prev = q5.iloc[1] if len(q5) > 1 else None
    prod_ao = int(q5_cur["PROD_AO_LAST_WEEK"])
    if q5_prev is not None and q5_prev["PROD_AO_LAST_WEEK"] > 0:
        ao_delta_pct = float(
            (q5_cur["PROD_AO_LAST_WEEK"] - q5_prev["PROD_AO_LAST_WEEK"]) / q5_prev["PROD_AO_LAST_WEEK"] * 100
        )
    else:
        ao_delta_pct = 0.0

    # SKU gap: using interop but no SKU
    sku_gap = int(
        q6[(q6["IS_INTEROPERABILITY"] == True) & (q6["HAS_SKU_INTEROPERABILITY"] == False)]["COMPANY_COUNT"].sum()
    )

    # Adoption trend table (sorted newest first)
    table_rows = [
        {
            "month": row["MONTH_START"].strftime("%Y-%m"),
            "interop": int(row["INTEROP_CUSTOMERS"]),
            "sku": int(row["SKU_INTEROP_CUSTOMERS"]),
            "total": int(row["TOTAL_CUSTOMERS"]),
            "adoption_pct": float(row["ADOPTION_PCT"]),
        }
        for _, row in q1.iterrows()
    ]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "kpis": {
            "adoption_pct": {
                "value": adoption_pct,
                "delta": round(adoption_delta, 2),
                "direction": "up" if adoption_delta >= 0 else "down",
            },
            "active_customers": {
                "value": active_customers,
                "delta": customers_delta,
                "direction": "up" if customers_delta >= 0 else "down",
            },
            "prod_executions": {
                "value": prod_executions,
                "delta": round(executions_delta_pct, 1),
                "is_pct": True,
                "direction": "up" if executions_delta_pct >= 0 else "down",
            },
            "prod_ao_last_week": {
                "value": prod_ao,
                "delta": round(ao_delta_pct, 1),
                "is_pct": True,
                "direction": "up" if ao_delta_pct >= 0 else "down",
            },
        },
        "sku_gap": sku_gap,
        "charts": {
            "adoption_trend": _chart_adoption_trend(q1),
            "population_donut": _chart_population_donut(q6),
            "executions_bar": _chart_executions_bar(data["q4"]),
            "ao_usage_line": _chart_ao_usage_line(data["q5"]),
            "product_family_bar": _chart_product_family_bar(data["q2"]),
            "arch_type_bar": _chart_arch_type_bar(data["q3"]),
        },
        "tables": {
            "adoption_trend": table_rows,
        },
    }
```

- [ ] **Step 4: Run compute_metrics tests**

```bash
pytest tests/test_render.py -k "compute_metrics" -v
```

Expected: all 10 compute_metrics tests PASS.

- [ ] **Step 5: Commit**

```bash
git add render.py
git commit -m "feat: implement compute_metrics() and chart helpers"
```

---

## Task 6: Build HTML template

**Files:**
- Create: `templates/report.html.j2`

- [ ] **Step 1: Create templates directory**

```bash
mkdir -p templates
```

- [ ] **Step 2: Write templates/report.html.j2**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Data Interoperability KPIs</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0f172a; color: #94a3b8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }
    header { background: #1e3a5f; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155; }
    header h1 { color: #60a5fa; font-size: 18px; font-weight: 600; }
    .updated { font-size: 11px; color: #475569; }
    nav { background: #1e293b; padding: 0 24px; border-bottom: 1px solid #334155; display: flex; gap: 4px; }
    .tab-btn { background: none; border: none; color: #64748b; padding: 12px 18px; cursor: pointer; font-size: 13px; border-bottom: 2px solid transparent; transition: color 0.15s; }
    .tab-btn:hover { color: #94a3b8; }
    .tab-btn.active { color: #60a5fa; border-bottom-color: #60a5fa; }
    .tab-content { display: none; padding: 24px; }
    .tab-content.active { display: block; }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .kpi-card { background: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; }
    .kpi-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .kpi-value { font-size: 28px; font-weight: 700; line-height: 1; margin-bottom: 6px; }
    .kpi-delta { font-size: 12px; }
    .kpi-delta.up { color: #34d399; }
    .kpi-delta.down { color: #f87171; }
    .kpi-adoption { color: #34d399; }
    .kpi-customers { color: #60a5fa; }
    .kpi-executions { color: #f59e0b; }
    .kpi-ao { color: #a78bfa; }
    .section { background: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; margin-bottom: 16px; }
    .section h3 { color: #cbd5e1; font-size: 13px; font-weight: 600; margin-bottom: 12px; }
    .chart-container { width: 100%; height: 320px; }
    .chart-container.tall { height: 420px; }
    .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { color: #64748b; text-align: left; padding: 8px 12px; border-bottom: 1px solid #334155; font-weight: 500; text-transform: uppercase; font-size: 10px; letter-spacing: 0.05em; }
    td { padding: 8px 12px; border-bottom: 1px solid #1e293b; color: #94a3b8; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #1e293b; }
    .callout { background: #1e3a5f; border: 1px solid #2563eb; border-radius: 6px; padding: 12px 16px; display: flex; align-items: center; gap: 12px; }
    .callout-value { font-size: 22px; font-weight: 700; color: #f59e0b; }
    .callout-text { font-size: 12px; color: #94a3b8; }
    @media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .chart-row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>

<header>
  <h1>📊 Data Interoperability KPIs</h1>
  <span class="updated">Last updated: {{ generated_at }} · Source: Snowflake CANONICAL</span>
</header>

<nav>
  <button class="tab-btn active" onclick="switchTab('overview')">Overview</button>
  <button class="tab-btn" onclick="switchTab('adoption')">Adoption</button>
  <button class="tab-btn" onclick="switchTab('usage')">Usage</button>
  <button class="tab-btn" onclick="switchTab('segments')">Segments</button>
</nav>

<!-- OVERVIEW -->
<div id="tab-overview" class="tab-content active">
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Adoption Rate</div>
      <div class="kpi-value kpi-adoption">{{ "%.2f"|format(kpis.adoption_pct.value) }}%</div>
      <div class="kpi-delta {{ kpis.adoption_pct.direction }}">
        {{ "▲" if kpis.adoption_pct.direction == "up" else "▼" }}
        {{ "%+.2f"|format(kpis.adoption_pct.delta) }}pp MoM
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Active Customers</div>
      <div class="kpi-value kpi-customers">{{ "{:,}".format(kpis.active_customers.value) }}</div>
      <div class="kpi-delta {{ kpis.active_customers.direction }}">
        {{ "▲" if kpis.active_customers.direction == "up" else "▼" }}
        {{ "%+d"|format(kpis.active_customers.delta) }} MoM
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Prod Executions (last full mo.)</div>
      <div class="kpi-value kpi-executions">{{ "{:,}".format(kpis.prod_executions.value) }}</div>
      <div class="kpi-delta {{ kpis.prod_executions.direction }}">
        {{ "▲" if kpis.prod_executions.direction == "up" else "▼" }}
        {{ "%+.1f"|format(kpis.prod_executions.delta) }}% MoM
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Prod AO Last Week</div>
      <div class="kpi-value kpi-ao">{{ "{:,.0f}".format(kpis.prod_ao_last_week.value / 1000) }}K</div>
      <div class="kpi-delta {{ kpis.prod_ao_last_week.direction }}">
        {{ "▲" if kpis.prod_ao_last_week.direction == "up" else "▼" }}
        {{ "%+.1f"|format(kpis.prod_ao_last_week.delta) }}% MoM
      </div>
    </div>
  </div>

  <div class="section">
    <h3>Adoption Trend (12 months)</h3>
    <div id="chart-overview-sparkline" class="chart-container"></div>
  </div>
</div>

<!-- ADOPTION -->
<div id="tab-adoption" class="tab-content">
  <div class="chart-row">
    <div class="section">
      <h3>Monthly Adoption Trend</h3>
      <div id="chart-adoption-trend" class="chart-container tall"></div>
    </div>
    <div class="section">
      <h3>All-Time Population</h3>
      <div id="chart-population-donut" class="chart-container tall"></div>
    </div>
  </div>
  <div class="section">
    <h3>Monthly Detail</h3>
    <table>
      <thead>
        <tr><th>Month</th><th>Interop Customers</th><th>SKU Customers</th><th>Total</th><th>Adoption %</th></tr>
      </thead>
      <tbody>
        {% for row in tables.adoption_trend %}
        <tr>
          <td>{{ row.month }}</td>
          <td>{{ "{:,}".format(row.interop) }}</td>
          <td>{{ "{:,}".format(row.sku) }}</td>
          <td>{{ "{:,}".format(row.total) }}</td>
          <td>{{ "%.2f"|format(row.adoption_pct) }}%</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<!-- USAGE -->
<div id="tab-usage" class="tab-content">
  <div class="section">
    <h3>Connector Executions by Month (Prod / Dev / Nonprod)</h3>
    <div id="chart-executions-bar" class="chart-container tall"></div>
  </div>
  <div class="section">
    <h3>AO Usage Trend — Last Week Value</h3>
    <div id="chart-ao-usage-line" class="chart-container"></div>
  </div>
</div>

<!-- SEGMENTS -->
<div id="tab-segments" class="tab-content">
  <div class="chart-row">
    <div class="section">
      <h3>By Product Family</h3>
      <div id="chart-product-family-bar" class="chart-container tall"></div>
    </div>
    <div class="section">
      <h3>By Architecture Type</h3>
      <div id="chart-arch-type-bar" class="chart-container tall"></div>
    </div>
  </div>
  <div class="section">
    <div class="callout">
      <div class="callout-value">{{ sku_gap }}</div>
      <div class="callout-text">
        <strong style="color:#f59e0b">SKU Gap</strong><br>
        Companies actively using Data Interoperability without a formal SKU entitlement.
      </div>
    </div>
  </div>
</div>

<script>
  var charts = {
    adoption_trend:    {{ charts.adoption_trend | tojson }},
    population_donut:  {{ charts.population_donut | tojson }},
    executions_bar:    {{ charts.executions_bar | tojson }},
    ao_usage_line:     {{ charts.ao_usage_line | tojson }},
    product_family_bar:{{ charts.product_family_bar | tojson }},
    arch_type_bar:     {{ charts.arch_type_bar | tojson }}
  };

  var cfg = {responsive: true, displayModeBar: false};

  Plotly.newPlot('chart-overview-sparkline',  charts.adoption_trend.data,     charts.adoption_trend.layout,     cfg);
  Plotly.newPlot('chart-adoption-trend',      charts.adoption_trend.data,     charts.adoption_trend.layout,     cfg);
  Plotly.newPlot('chart-population-donut',    charts.population_donut.data,   charts.population_donut.layout,   cfg);
  Plotly.newPlot('chart-executions-bar',      charts.executions_bar.data,     charts.executions_bar.layout,     cfg);
  Plotly.newPlot('chart-ao-usage-line',       charts.ao_usage_line.data,      charts.ao_usage_line.layout,      cfg);
  Plotly.newPlot('chart-product-family-bar',  charts.product_family_bar.data, charts.product_family_bar.layout, cfg);
  Plotly.newPlot('chart-arch-type-bar',       charts.arch_type_bar.data,      charts.arch_type_bar.layout,      cfg);

  function switchTab(name) {
    document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
    document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
    document.getElementById('tab-' + name).classList.add('active');
    document.querySelector('[onclick="switchTab(\'' + name + '\')"]').classList.add('active');
    window.dispatchEvent(new Event('resize'));
  }
</script>
</body>
</html>
```

- [ ] **Step 3: Commit template**

```bash
git add templates/
git commit -m "feat: add Jinja2 HTML report template (dark theme, 4 tabs, Plotly)"
```

---

## Task 7: Implement render() + end-to-end test

**Files:**
- Modify: `render.py`

- [ ] **Step 1: Run render tests — confirm they fail**

```bash
pytest tests/test_render.py -k "render" -v
```

Expected: all fail with `NotImplementedError`.

- [ ] **Step 2: Implement render()**

Replace the `render` stub in `render.py`:

```python
def render(
    metrics: dict,
    template_path: str = "templates/report.html.j2",
    output_path: str = "report.html",
) -> None:
    env = Environment(loader=FileSystemLoader("."), autoescape=False)
    template = env.get_template(template_path)
    html = template.render(**metrics)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
```

- [ ] **Step 3: Run all render tests**

```bash
pytest tests/test_render.py -k "render" -v
```

Expected: all 4 render tests PASS.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/test_render.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Smoke test with real Parquet data (skip if data/ is empty)**

If `data/*.parquet` files exist (from a prior `/refresh` run):

```bash
python render.py
open report.html   # macOS — verify the report opens and all 4 tabs render charts
```

- [ ] **Step 6: Commit**

```bash
git add render.py
git commit -m "feat: implement render() — Jinja2 HTML output"
```

---

## Task 8: /refresh command

**Files:**
- Create: `.claude/commands/refresh.md`

- [ ] **Step 1: Create .claude/commands/ directory**

```bash
mkdir -p .claude/commands
```

- [ ] **Step 2: Write .claude/commands/refresh.md**

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/refresh.md
git commit -m "feat: add /refresh Claude Code slash command"
```

---

## Task 9: Final integration commit

- [ ] **Step 1: Run full test suite one last time**

```bash
pytest tests/ -v
```

Expected: all tests PASS, zero failures.

- [ ] **Step 2: Verify project structure is clean**

```bash
git status
```

Expected: working tree clean. `data/` and `report.html` should not appear (they are gitignored).

- [ ] **Step 3: Final commit**

```bash
git add -A
git status   # verify nothing sensitive is staged
git commit -m "chore: complete KPI dashboard implementation" --allow-empty-message || true
# Only commit if there are staged changes
```

- [ ] **Step 4: Verify /refresh works end-to-end**

In Claude Code, run:
```
/refresh
```

Then open `report.html` in a browser and verify:
- All 4 tabs are present and clickable
- KPI cards show correct values with MoM deltas
- All 6 charts render with data
- SKU gap callout is visible in Segments tab
- "Last updated" timestamp is current
