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
- **Real SCD2 history (verified 2026-10-01):** `date_from`/`date_to` are genuine version
  ranges, not just current/historical flags — current rows are sentinel-closed at
  `date_to = 2999-12-31`. Point-in-time reconstruction:
  `date_from <= LAST_DAY(month) AND date_to > LAST_DAY(month)`. Used in
  `queries/q30_t2a_multiinfra_tam_monthly.sql` to count distinct O11 `activation_code`s a
  company held as of each past month-end — a genuine historical trend, not a current-state
  backfill.
- **`interoperability_related_activation_code`** (on ODC-family rows, i.e.
  `product_family = 'ODC'`): the real O11 `activation_code` an ODC tenant's Data Fabric
  connection targets, matched via `tenant_id`. **Grain is per ODC TENANT, not per
  connection/environment** — a company only shows 2+ distinct values if it holds 2+ separate
  ODC tenants each linked to a different O11 infra. Population rate must be measured at the
  **company level within the relevant cohort** (e.g. O11/ODC customers): ~79% there, vs. a
  misleading ~0.7% if measured as raw-row-count across all 96,900 ODC infra rows
  system-wide (most of which are irrelevant trial/unrelated tenants). See
  `queries/q32_t2c_multiinfra_validated.sql` for the full write-up.

## CANONICAL.CUSTOMERSUCCESS.ENVIRONMENT
- **Purpose:** environment metadata (SCD2). **Grain:** one row per environment
  (stage/purpose) per version — ~5 per infra. **Key:** `environment_id`,
  `activation_code`, `stage_id`, `environment_purpose`, `is_current`,
  `is_active`, `is_deleted`, `is_licensed`, `cloud_provider`.
- **Gotcha:** joining infra→environment is one-to-many; never expect per-infra grain.

## CANONICAL.CORE.COMPANY
- **Purpose:** company master. **Key:** `company_id`, `company_sfdc_id`,
  `company_name`, `type`, `region`, `geo`.
- **`type` domain (verified 2026-07-02):** `customer`, `partner`, `licensee`,
  `former customer`, `former partner`, `prospect customer`, `prospect partner`,
  `internal`, `undefined`, `other`. **NOT** just customer/partner/licensee.
- **Gotcha:** `type` reflects a company's **current** status, not its status at
  any past point. A churned customer is now `former customer`; OutSystems' own
  tenants are `internal`. Filtering telemetry by `type IN ('customer','partner')`
  therefore drops historical rows for since-churned/internal tenants — the older
  the month, the larger this exclusion (see q7 note).

## CANONICAL.CUSTOMERSUCCESS.TENANTMETADATA
- **Key:** `tenant_id`, `ODC_RING`.

## CANONICAL.CUSTOMERSUCCESS.PLATFORMUTILIZATIONWEEKLY
- **Purpose:** weekly platform usage. **Key:** `infrastructure_id`,
  `environment_id`, `date_id`, `user_company_id`, `ao_usage`,
  `distinct_visitors`, `internal_users_count`, `external_users_count`.

## TELEMETRYANALYTICS.ODC_METRIC.EXTERNALCONNECTIONELEMENTSUSAGECOUNT
- **Purpose:** daily gauge of entities imported per Data Fabric connection (depth/breadth).
- **Grain:** one row per tenant × environment × connection × day.
- **Key columns:** `TENANTID`, `ENVIRONMENTID` (note: no underscore, unlike
  `EXTERNALCONNECTIONCOUNT`'s `tenant`/`environment_id`), `EVENT_CONNECTIONID`,
  `EVENT_SELECTEDENTITIESCOUNT` (the entity count), `EVENT_PROVIDER`, `EVENT_METRICDATE`.
- **Gotcha:** no `type` (D/W/M) column like `EXTERNALCONNECTIONCOUNT` — it's daily-only.
  Used in q29/q33/q35 for Success Metrics Depth/breadth stages.

## TELEMETRYANALYTICS.METRICS.LIFETIME_UNIFICATION
- **Purpose:** new (as of 2026-09-28) O11 Lifetime telemetry logging ODC↔O11
  "Unification" handshakes — the first per-event signal for which O11 infra a specific ODC
  tenant talks to, as opposed to the static per-tenant
  `INFRASTRUCTURE.interoperability_related_activation_code` field above.
- **Key columns:** `DOMAIN_ODCTENANTID` (ODC tenant_id), `ENV_ACTIVATION_CODE` (O11
  activation code), `DOMAIN_ACTION` (`Handshake_v1`, `ODC_Info_Put_v1`), `EVENT_DATE`.
- **Status (checked 2026-10-01): too new/sparse to use alone.** Only 8 rows total, all from
  2026-09-28/29, and none of its `DOMAIN_ODCTENANTID` values resolve to a real company in
  `CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE` yet (early rollout/test traffic, or sync lag).
  One sample row already showed a single tenant handshaking with 2 distinct O11 codes —
  promising once it matures. Wired in as `queries/q34`/`q35`, kept separate from the
  `interoperability_related_activation_code`-based `q32`/`q33` rather than merged.

## CLOUDFRAMEWORKPRODUCTION.NOW.OSUSR_YDY_INFRASTRUCTURE / ..SLOT / ..ENVIRONMENT
- **Purpose:** the O11 cloud provisioning DB — infra → slots (environments) with
  `slottypeid` (1=Dev, 2=Lifetime, 3=Production, 4=Non-Production in this module — note this
  is the REVERSE of 3/4 vs. `OSUSR_9PN_INFRASTRUCTUREENVIRONMENT.ENVIRONMENTTYPEID`, don't
  mix conventions) and `infrastructureslotstateid` (`'6'` = live; `'5'` = decommissioned
  leftovers, would badly inflate counts if included).
- **Gotcha: CURRENT-STATE SNAPSHOT ONLY — no `date_from`/`date_to`, no history at all.**
  Unlike `CANONICAL.CUSTOMERSUCCESS.INFRASTRUCTURE`, there is no way to reconstruct what an
  infra's shape looked like in a past month. Used as the pipeline-count proxy for Success
  Metrics Task 1 (`queries/q25`–`q29`): "# pipelines" := # of live Production slots, since
  there's no real pipeline/path identifier anywhere in this schema. Monthly trends built on
  this data apply TODAY's shape retroactively to historical cohort membership — see the
  warning banner in the report UI.
- `LIFETIMEKEY` on `OSUSR_YDY_ENVIRONMENT` is per-ENVIRONMENT (21,131 distinct / 23,066
  rows) — **wrong grain** for identifying "which O11 infra", don't reach for it there.

## v1 tables (unchanged)
- `MONTHLYCOMPANYPRODUCTEDITIONCATEGORY` (q1/q2), `MONTHLYCOMPANYINFRAPRODUCTEDITIONCATEGORY` (q3),
  `PLATFORMUTILIZATIONDAILYINFRASTRUCTUREAGG` (q4), `PLATFORMUTILIZATIONMONTHLYINFRASTRUCTUREAGG_TOTAL` (q5).
  These aggregate with `COUNT(DISTINCT … )` per period and are not month-inflated.
