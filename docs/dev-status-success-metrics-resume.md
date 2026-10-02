# Data InterOperability Success Metrics — Resume Checkpoint

**Saved:** 2026-10-01
**Branch:** `main`
**HEAD:** `e962f10` — "feat: Data InterOperability Success Metrics tab (Task 1/2 funnels)"
**Working tree:** 1 file modified, **not committed**: `templates/report.html.j2`
  (adds the "What 'Unresolved' means" caption under the (c) ODC-Interop-Code chart — small,
  safe to commit whenever; not pushed yet).
**Tests:** not run this session — run `python -m pytest tests/ -q` before trusting/extending.

---

## Where we are

Built out the full adoption-metrics funnel from the Google Doc ("Data Interoperability:
Adoption Metrics for new capabilities") as a new **"Data InterOperability Success Metrics"**
report tab: TAM → Reach → Validated use case → Depth/breadth, for both tasks in the doc.

- [x] Reviewed the doc, flagged issues (see "Doc review findings" below).
- [x] Drafted Task 1 (q26–q29) and Task 2 (q30–q33) funnel queries, wired into `render.py`
      + `templates/report.html.j2`, committed + pushed (`e962f10`).
- [x] Fixed a real bug found along the way: q31/q32/q33's `tam_month` wasn't joined back to
      the cohort, silently counting ANY company with 2+ O11 codes instead of just the O11/ODC
      ones (inflated TAM to 1510 vs q30's 258). Fixed in all three files.
- [x] User asked to broaden the Task 2 cohort to "ODC customers" (ODC-only + O11/ODC hybrid),
      then reverted it ("drop that, O11/ODC only") in the same session — **final state is
      O11/ODC-only**, bug fix kept.
- [x] Investigated why Task 2(c) Validated always read 0 — confirmed genuine, not a bug (see
      "Key findings" below). Found a better long-term signal (`LIFETIME_UNIFICATION`) but it's
      too new/sparse to use alone.
- [x] Per user decision: built `q34`/`q35` as a **separate**, parallel Task 2(c)/(d) pair
      sourced from `LIFETIME_UNIFICATION`, instead of merging/replacing q32/q33.
- [x] Per user decision: changed q32 + q34's output from a single `VALIDATED_CUSTOMERS` count
      to a 3-way breakdown (`ONE_INFRA_CUSTOMERS` / `MULTI_INFRA_CUSTOMERS` /
      `UNRESOLVED_CUSTOMERS`, out of `REACH_CUSTOMERS`), rendered as a stacked bar
      (`_chart_infra_breakdown` in `render.py`).
- [x] Added a data-driven executive summary + glossary to the tab (computed live from the
      Parquet data each render, not static copy).
- [x] Added explanatory caption for "Unresolved" — **uncommitted**, see Working tree above.

## Next steps (pick up here)

1. `git add templates/report.html.j2 && git commit -m "..." && git push` the pending
   "Unresolved" caption (or fold it into whatever you do next).
2. ~~Watch the **Unresolved** count~~ — **investigated 2026-10-02, closed.** Not a backfill
   lag and not "field only exists since July": the field is set by a provisioning job (90%
   of coded tenants had it before first connecting; late fills are rare), and NULL means an
   ODC tenant bought without an O11 infra link. The rise in Unresolved is a growing share of
   such tenants among recent connections (small n). Details in `docs/data-context/tables.md`
   (INFRASTRUCTURE → `interoperability_related_activation_code`).
2b. **2026-10-02: q32/q33 switched to `ODC_METRIC.O11INFRASTRUCTURECONFIGURATION`** (O11
   Bridge Service link events; distinct live LifeTime URLs per Reach customer). Data only from
   2026-08-27, no backfill → most Reach customers read Unresolved (Sep 2026: 2 one-infra,
   0 multi, 45 unresolved of 47). Follow-up: ask Unification Charlie
   (vincent.verapen@outsystems.com) for a backfill/snapshot of pre-2026-08-27 links; watch for
   eventVersion 1.1 (`o11UnificationPortfolioKey`) landing in prod.
3. Revisit `LIFETIME_UNIFICATION` (q34/q35) periodically — it had exactly 8 rows (all
   2026-09-28/29) and zero resolvable tenant IDs as of this session. Once it has real
   customer coverage, reconsider whether it should become the primary signal (event-level,
   more precise) with q32/q33 kept as the long-history fallback.
4. Possible later cleanup: reconcile `q21` ("Customers with Multiple O11 Infrastructures
   Using Data Fabric", pre-existing table in the Data InterOperability tab) against the new
   `q30` Task 2(a) TAM definition — they measure similar but not identical populations (q21
   filters `infrastructure_type='enterprise'` + current-month snapshot; q30 is unrestricted
   by infra type and uses real SCD2 historization). Not reconciled, just flagging the overlap.
5. `q25` (`q25_t1a_multipipeline_tam.sql`, the point-in-time segment/coverage breakdown for
   Task 1 TAM) and `q24` (O11 lifetime-version check) exist in `queries/` but are **not**
   wired into the Success Metrics tab's narrative — they predate it and were left as
   standalone/reference queries. Could surface q25 as a supplementary detail table under
   Task 1(a) if useful later.

## Doc review findings (still open, not fixed in the source doc)

The Google Doc itself (not this repo) has a few rough edges, reported to the user but not
resolved there:
- Stage (b)/(c) metric *names* in both task tables read "...% of cohort customers (cohort)
  adoption Data Interop..." — looks like unfilled template text.
- Task 1(c) "Validated" can't actually prove cross-**pipeline** usage (only cross-
  **environment**), because the O11 schema has no pipeline/path identifier — this repo's
  `q28` implements it as literally specified in the doc anyway, with a warning banner in the
  UI rather than silently diverging from the spec.
- TAM coverage gaps (resolution rate for customer→O11-infra matching) aren't caveated in the
  doc.
- Stage (b) "Reach" doesn't specify whether it's point-in-time or ever-connected (this repo
  treats it as point-in-time/month-end, consistent with the rest of the report).

## Key findings (carry forward, don't re-derive)

- **`INTEROPERABILITY_RELATED_ACTIVATION_CODE`** (on `CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE`,
  ODC-family rows, matched via `tenant_id`) is the field linking an ODC tenant to "the O11
  activation code its Data Fabric connection targets." **Grain is per ODC TENANT, not per
  connection/environment** — a company only shows 2+ distinct codes if it holds 2+ *separate*
  ODC tenants each linked to a different O11 infra.
  - Row-level population across ALL 96,900 ODC infra rows system-wide is only ~0.7% — **this
    figure is misleading**, most of those rows are irrelevant (trial/unrelated tenants).
  - Properly scoped to the actual O11/ODC cohort (838 companies), it's **~79% populated**
    (659/838) — a solid signal, consistent with `q24`'s earlier ~80% finding on the Dev
    population. Always measure population rate at the company level within the relevant
    cohort, never at the raw row level across the whole table.
  - Exactly **5 companies system-wide** hold 2+ distinct values: British Car Auctions Limited,
    Far East Management (Private) Limited, Samsung Electronics Co., Ltd., Singapore
    Management University, TXT NOVIGO SRL (Customer). Of those, 3 have zero connected tenants
    and 2 (Far East Management, Samsung) have exactly 1 connected tenant each — **none
    currently has simultaneous live connections across both linked infras**. The "0 Validated"
    reading is a genuine finding, not a bug. (Reproduce via the ad-hoc query in this session's
    transcript if needed again — not saved as a tracked query file.)
- **`TELEMETRYANALYTICS.METRICS.LIFETIME_UNIFICATION`** — O11 Lifetime's new handshake
  telemetry (`DOMAIN_ODCTENANTID` + `ENV_ACTIVATION_CODE`, event types `Handshake_v1` /
  `ODC_Info_Put_v1`). This is the **better long-term signal** (event-level, not tenant-level)
  but as of this session has only 8 rows total (2026-09-28/29) and none of its tenant IDs
  resolve to a real company yet — likely early rollout/test traffic. Re-check periodically.
- Tables/fields checked and ruled out as NOT useful for per-connection O11-infra attribution:
  `OSUSR_YDY_ENVIRONMENT.LIFETIMEKEY` (wrong grain, unique per environment not per infra),
  `TELEMETRYANALYTICS.METRICS.SERVICECENTER_DBPROVIDERCONNECTIONCONFIGURATION` (unrelated
  generic external-DB connection telemetry, zero O11 hosts), `F_27_ODC_CUST_DATAFABRIC`
  (pre-aggregated KPI rollup, no connection-level grain).
- `CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE` **is real SCD2 history** — `DATE_FROM`/`DATE_TO`
  with current rows sentinel-closed at `2999-12-31`. This enables genuine point-in-time
  reconstruction (`date_from <= LAST_DAY(month) AND date_to > LAST_DAY(month)`), used in q30
  for Task 2 TAM. Contrast with `CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_*` (the O11
  provisioning DB backing the Task 1 pipeline-count proxy), which is **current-state only,
  no history at all** — Task 1's monthly trend necessarily backfills today's shape onto
  historical cohort membership (documented via the warning banner in the UI).
- `TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT` —
  `EVENT_SELECTEDENTITIESCOUNT` is the entities-imported-per-connection gauge used for all
  Depth/breadth stages (q29/q33/q35). Same day/month-end convention as
  `EXTERNALCONNECTIONCOUNT`, but no `type` (D/W/M) column and no `tenant`/`environment_id`
  column names (uses `TENANTID`/`ENVIRONMENTID` instead — mind the naming difference).

## Where things live

- Queries: `queries/q26`–`q29` (Task 1), `q30`–`q33` (Task 2, ODC-code signal), `q34`–`q35`
  (Task 2, Unification signal). Each file's header comment has the full rationale/caveats —
  read those before touching the logic.
- `render.py`: `_chart_funnel_stage` (TAM/Reach bar+% combo), `_chart_infra_breakdown`
  (1-infra/2+-infra/unresolved stacked bar), `_chart_depth_trend` (3-line entities chart),
  `_build_success_metrics_summary` (exec text + glossary, data-driven).
- `templates/report.html.j2`: `tab-successmetrics` section, near the end before the
  `<script>` block.
- Refresh: `/refresh` skill runs all 23 "core" queries; q24–q35 are **not** in that list (run
  them manually via `snow sql` + the conversion pattern used this session if you need fresh
  data — see the session transcript for the exact `uvx --python 3.13 --from snowflake-cli
  snow sql --connection os` invocation and the pandas conversion script).
