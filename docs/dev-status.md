# Development Status

**Last updated:** 2026-06-15  
**Current HEAD:** `ad7142a`  
**Branch:** main

---

## What's Been Built

The project is a Data Interoperability KPI monitoring dashboard. Data is fetched from Snowflake via a `/refresh` Claude Code slash command, stored as Parquet files, and rendered into a self-contained dark-themed HTML report using Jinja2 and Plotly.js.

### Completed Tasks

| # | Task | Commit | Status |
|---|---|---|---|
| 1 | Bootstrap (`.gitignore`, `requirements.txt`, `data/`) | `8e74b85` | ✅ |
| 2 | SQL query files (`queries/q*.sql`) | `199038d` | ✅ |
| 3 | `render.py` skeleton + all 17 tests | `359992c` | ✅ |
| 4 | `load_data()` implementation | `4acebb7` | ✅ |
| 5 | `compute_metrics()` + 6 `_chart_*` helpers | `3826ba6` | ✅ |
| — | Code quality fixes (imports, boolean ops, barmode, time-coupled test) | `ad7142a` | ✅ |

### Test State

```
13 passed, 4 failed
```

- **Passing (13):** `load_data` (2) + `compute_metrics` (11)
- **Failing (4):** `render` tests — intentionally failing stubs, waiting for Task 6+7

---

## What Remains

### Task 6: Build HTML template

**File to create:** `templates/report.html.j2`

Dark-themed Jinja2 template. 4 tabs: Overview, Adoption, Usage, Segments. Plotly.js via CDN. Full template content is in the implementation plan at:

`docs/superpowers/plans/2026-06-15-data-interop-kpi-dashboard.md` → **Task 6**

Key template variables expected from `render()`:
- `{{ generated_at }}` — UTC timestamp string
- `{{ kpis.adoption_pct.value }}`, `{{ kpis.adoption_pct.delta }}`, `{{ kpis.adoption_pct.direction }}`
- `{{ kpis.active_customers.value/delta/direction }}`
- `{{ kpis.prod_executions.value/delta/direction }}`
- `{{ kpis.prod_ao_last_week.value/delta/direction }}`
- `{{ charts.adoption_trend | tojson }}` (and 5 others)
- `{{ tables.adoption_trend }}` — list of dicts with keys: month, interop, sku, total, adoption_pct
- `{{ sku_gap }}` — int

Chart div IDs required (Plotly.newPlot targets):
- `chart-overview-sparkline` (Overview tab — reuses adoption_trend data)
- `chart-adoption-trend` (Adoption tab)
- `chart-population-donut` (Adoption tab)
- `chart-executions-bar` (Usage tab)
- `chart-ao-usage-line` (Usage tab)
- `chart-product-family-bar` (Segments tab)
- `chart-arch-type-bar` (Segments tab)

### Task 7: Implement `render()`

**File to modify:** `render.py`

Replace the `raise NotImplementedError` stub in `render()` with:

```python
def render(
    metrics: dict,
    template_path: str = "templates/report.html.j2",
    output_path: str = "report.html",
) -> None:
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("."), autoescape=False)
    template = env.get_template(template_path)
    html = template.render(**metrics)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
```

After this, all 17 tests should pass.

### Task 8: `/refresh` command

**File to create:** `.claude/commands/refresh.md`

Full content is in the implementation plan → **Task 8**.

The command instructs Claude Code to:
1. Run each `queries/q*.sql` via `uvx --python 3.13 --from snowflake-cli snow sql --query "..." --format json --connection os`
2. Save each result to `data/*.parquet` (with date column parsing)
3. Run `python render.py`
4. Print summary (row counts, file sizes, timestamp)

### Task 9: Final integration

Run `pytest tests/ -v`, verify clean `git status`, end-to-end `/refresh` smoke test.

---

## Project Structure (current)

```
dataInterOpMetrics/
├── .claude/
│   └── settings.local.json
├── .gitignore
├── data/
│   └── .gitkeep              ← Parquet files go here (gitignored)
├── docs/
│   ├── dev-status.md         ← this file
│   └── superpowers/
│       ├── plans/2026-06-15-data-interop-kpi-dashboard.md
│       └── specs/2026-06-15-data-interop-kpi-dashboard-design.md
├── queries/
│   ├── q1_adoption_trend.sql
│   ├── q2_by_product_family.sql
│   ├── q3_by_arch_type.sql
│   ├── q4_executions.sql
│   ├── q5_ao_usage.sql
│   └── q6_population.sql
├── render.py                 ← load_data ✅, compute_metrics ✅, render 🔲
├── requirements.txt
├── templates/                ← DOES NOT EXIST YET (Task 6)
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_render.py
```

---

## How to Resume

In a new Claude Code session, from this directory:

1. Read this file (`docs/dev-status.md`)
2. Read the implementation plan (`docs/superpowers/plans/2026-06-15-data-interop-kpi-dashboard.md`)
3. Run `pytest tests/ -v` to confirm current state (13 pass, 4 fail)
4. Continue from **Task 6** using `superpowers:subagent-driven-development`

Snowflake connection name: `os` (account: `AX81353-OUTSYSTEMS`)
