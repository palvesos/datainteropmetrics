# Trialing-category — Resume Checkpoint

**Saved:** 2026-07-07 (paused at user request — user rebooting)
**Branch:** `feature/data-fabric-trialing-category` (off `main` @ `b3dcaf8`)
**HEAD:** `f8fe831` — "docs: trialing-category design + q7 gap resolved"
**Tests:** `python -m pytest tests/ -q` → **26 passed** (pristine, 0 warnings)
**Working tree:** clean

---

## Where we are in the flow

Following **superpowers:brainstorming** → next step is **superpowers:writing-plans**.

- [x] Investigated q7-vs-raw gap (follow-up #1) → RESOLVED: not a defect. Gap is 100% the
      `type IN ('customer','partner')` filter, dominated by OutSystems `internal` tenants
      (22 tenants, ~17k conns/yr) + `prospect customer`. Infra SCD2 join drops nothing.
      Fixed `docs/data-context/tables.md` COMPANY.type domain + added q7 note. (committed)
- [x] Brainstormed the trialing feature; design approved by user.
- [x] Wrote + committed spec: `docs/superpowers/specs/2026-07-03-data-fabric-trialing-category-design.md`
- [x] Spec self-review passed.
- [ ] **NEXT: user was reviewing the spec.** They rebooted mid-review. On resume, ask if
      they approve the spec or want changes. Once approved → invoke **superpowers:writing-plans**.

## How to resume (next session)

1. `git checkout feature/data-fabric-trialing-category` — confirm HEAD `f8fe831`, tree clean.
2. Re-read the spec: `docs/superpowers/specs/2026-07-03-data-fabric-trialing-category-design.md`.
3. Ask the user: approve spec as-is, or changes? (They were at the "review the written spec" gate.)
4. On approval → invoke **superpowers:writing-plans** to produce the implementation plan, then
   execute TDD (subagent-driven-development is how v2 was built; optional here).
5. Snowflake: connection `os` (account `AX81353-OUTSYSTEMS`), auth cached per-session (one
   browser login may reappear). Run SQL via:
   `uvx --python 3.13 --from snowflake-cli snow sql --query "..." --format json --connection os`

## Design summary (approved)

Add **trialing** = `COMPANY.type IN ('prospect customer','prospect partner')` as a distinct
additive category in the **Data Fabric tab only**. Approach A (new parallel query; q7/q8 untouched):

- **New** `queries/q12_data_fabric_trialing_monthly.sql` = copy of q7 with the prospect filter.
  Output shape identical to q7 (`MONTH, UNIQUE_TENANTS, UNIQUE_CUSTOMERS, TOTAL_CONNECTIONS`).
- **`render.py`**: `load_data` reads it into key `data_fabric_trialing` (11→12 keys);
  `compute_metrics` adds `kpis.df_trialing_connections` + `df_trialing_tenants` (w/ MoM delta,
  reusing `current_month_start` + `_pct_delta`); `_chart_data_fabric_trend` gets a 2nd trace
  "Trialing" alongside "Customer/Partner".
- **Template**: add a Trialing KPI card (connections + tenants) to the Data Fabric tab.
- **`.claude/commands/refresh.md`**: add q12 row (Date `MONTH`; Numeric `UNIQUE_TENANTS,
  UNIQUE_CUSTOMERS, TOTAL_CONNECTIONS`); bump 11→12.
- **Tests (TDD)**: q12 fixture (pinned `_today=2026-06-15`); load_data 12 keys; trialing KPIs
  value+delta; trend chart has 2 traces; render asserts trialing card + value.

Non-goals: no trialing in q8/providers chart; no other tabs; paying KPIs unchanged.

## Key facts to carry forward

- `COMPANY.type` domain (verified): customer, partner, licensee, former customer, former
  partner, prospect customer, prospect partner, internal, undefined, other. Reflects CURRENT
  status (churned → "former customer"; OutSystems → "internal").
- Paying vs trialing are disjoint → no double-count.
- df "last complete month" logic reuses injected `current_month_start`; tests pin `_today=2026-06-15`.
- `event_sent` is VARCHAR → wrap in `TRY_TO_TIMESTAMP`; QUALIFY partitions on
  (tenant, environment_id, event_provider, event_sent).
