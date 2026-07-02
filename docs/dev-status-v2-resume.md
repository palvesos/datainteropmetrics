# Dashboard v2 — Resume Checkpoint

**Saved:** 2026-07-02 (paused at user request after Task 9)
**Branch:** `feature/dashboard-v2` (NOT merged to main)
**HEAD:** `8b615c7`
**Tests:** `python -m pytest tests/ -q` → **21 passed**
**Execution method:** superpowers:subagent-driven-development (fresh subagent per task + task review + fix loops)

---

## How to resume (next session)

1. `git checkout feature/dashboard-v2` and confirm HEAD is `8b615c7` (or later).
2. Read the plan: `docs/superpowers/plans/2026-07-02-data-interop-dashboard-v2.md` (the executable source of truth).
3. Read the spec (context): `docs/superpowers/specs/2026-07-02-data-interop-dashboard-v2-design.md`.
4. Read the **progress ledger**: `.superpowers/sdd/progress.md` — lists every completed task with commit ranges and outstanding MINOR findings. (This dir is git-ignored but persists on disk across sessions. Task briefs/reports live there too as `task-N-brief.md` / `task-N-report.md`.)
5. Re-invoke **superpowers:subagent-driven-development** and continue at **Task 10**. Do NOT re-dispatch Tasks 1–9 (ledger + git log prove they're done).
6. Snowflake connection is `os` (auth cached per-session; a browser login may reappear once). Run SQL via:
   `uvx --python 3.13 --from snowflake-cli snow sql --query "$(cat queries/QN.sql)" --format json --connection os`

---

## Completed (Tasks 1–9 + 2 cross-cutting fixes)

| Task | What | Commits | Notes |
|---|---|---|---|
| 1 | Data-context docs (`docs/data-context/{README,tables,patterns}.md`) | `1447d6d..03c9138` | Maintained source-of-truth; keep updated |
| 2 | Harden `q6_population.sql` | `..92e82de` | Fixed 103-month inflation (was 188k→ correct) |
| 3 | `q7_data_fabric_monthly.sql` + `q8_data_fabric_providers.sql` | `..87893b9` | Needed `TRY_TO_TIMESTAMP` (event_sent is VARCHAR) + QUALIFY natural-key dedupe (fixed ~2× under-count) |
| 4 | `q9_deployment_option.sql` | `..d6a421c` | 3 rows O11/ODC/O11-ODC |
| 5 | `q10_sku_gap_targeting.sql` | `..abeb7b9` | 58 rows |
| — | **Cross-fix: `IS_LAST_MONTH_REPORTED`** on q6/q9/q10 | `98e0c2e..fe9198f` | `MONTH_DT=MAX` = open month (2026-07) with NULL ARR; switched to last reported month (2026-05). Amended q6+q9 too. patterns.md updated. |
| 6 | `q11_infra_no_telemetry.sql` | `..f2139c0` | 637 rows, 1:1 grain |
| 7 | Fixtures q7–q11 in `tests/conftest.py` | `..c1a4d6e` | additive |
| 8 | `load_data` reads q7–q11 | `..dbd387d` | TDD, 18 passed |
| 9 | `compute_metrics` Data Fabric KPIs (df_connections/df_tenants/df_providers) | `..8b615c7` | TDD, 21 passed; reuses injected `_today` |

Every task above passed an independent task review (spec + quality); Tasks 3 and the month-filter each went through one fix loop.

## Remaining (Tasks 10–15) — not started

- **Task 10:** `compute_metrics` — 3 chart helpers (`_chart_data_fabric_trend`, `_chart_data_fabric_providers`, `_chart_deployment_option_bar`) + wire into `charts`. TDD.
- **Task 11:** `compute_metrics` — targeting tables (`sku_gap_targeting`, `infra_no_telemetry`, `deployment_option`) + `arr_at_risk` KPI + `sku_gap_count`. TDD.
- **Task 12:** `templates/report.html.j2` — add **Data Fabric** + **Targeting** tabs, deployment-option chart in Segments, wire new charts into the `<script>` block.
- **Task 13:** render tests for new tabs/values. TDD.
- **Task 14:** `.claude/commands/refresh.md` — add q7–q11 rows (Date/Bool/Numeric coercion cols); "11 Parquet files".
- **Task 15:** live `/refresh` end-to-end, verify report (6 tabs), update `docs/dev-status.md`.
- Then: final whole-branch code review + superpowers:finishing-a-development-branch (merge decision).

## Key decisions & learnings (carry forward)

- **Current-customer filter is `IS_LAST_MONTH_REPORTED AND IS_CURRENT_CUSTOMER AND IS_CUSTOMER_POLICY`** — never `MONTH_DT = MAX` (that's the open month, ARR unpopulated). Documented in `docs/data-context/patterns.md`.
- **`EXTERNALCONNECTIONCOUNT.event_sent` is VARCHAR** — wrap in `TRY_TO_TIMESTAMP()` for any date op; its source grain is `tenant × environment_id × event_provider × day` (QUALIFY dedupe must partition on all four).
- **Time-coupling:** `compute_metrics(data, _today=...)` — the DF/executions "last complete month" logic must reuse the injected `current_month_start`; tests inject `_today=pd.Timestamp("2026-06-15")`.
- Plan Global Constraints (color palette, numeric coercion, SCD2 join form) still bind Tasks 10–15.

## Outstanding MINOR findings (for the final whole-branch review — in ledger)

- **T3:** q7 vs raw connection gap is large in older months — data-quality follow-up (customer/partner filter attribution unverified). Consider a one-off `TRY_TO_TIMESTAMP IS NULL` diagnostic count.
- **T8:** `test_load_data_returns_six_keys` was repurposed to assert 11 keys — now misnamed and duplicates `test_load_data_returns_eleven_keys`; remove or rename.
- **T9:** `_pct_delta` guard `prev not in (None, 0)` misses `NaN` — use `pd.isna(prev)`. It's reused in Tasks 10/11, so worth fixing there.

## Metrics dict contract (produced by compute_metrics, consumed by template)

Already present: `kpis.{adoption_pct,active_customers,prod_executions,prod_ao_last_week,df_connections,df_tenants,df_providers}`, `sku_gap`, `charts.{adoption_trend,population_donut,executions_bar,ao_usage_line,product_family_bar,arch_type_bar,data_fabric_*(pending T10)}`, `tables.adoption_trend`.
To add (T10/T11): `charts.{data_fabric_trend,data_fabric_providers,deployment_option_bar}`, `kpis.arr_at_risk`, `sku_gap_count`, `tables.{sku_gap_targeting,infra_no_telemetry,deployment_option}`.
