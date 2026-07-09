# Data InterOperability Tab — Scaffold Design

**Goal:** Add a new top-level tab labelled **"Data InterOperability"** to the KPI report as an empty scaffold (button + panel with a heading), to be populated with content later.

**Scope:** Template-only (`templates/report.html.j2`) plus one regression test. No new Snowflake query, no `render.py` change, no new parquet, no data wiring.

## Decisions

- **Label:** `Data InterOperability`
- **Internal tab id:** `datainterop` (matches the existing `switchTab('id')` / `id="tab-id"` convention: `overview`, `adoption`, `usage`, `segments`, `datafabric`, `targeting`).
- **Position:** Last — after the `Targeting` tab.
- **Panel content:** A single `.section` block with an `<h3>Data InterOperability</h3>` heading and a placeholder paragraph `Content coming soon.` — matching the existing panel idiom (`.section` + `<h3>`; note there is no `.muted` class in the CSS, so a plain `<p>` is used).
- **Not active by default:** the panel is `class="tab-content"` (not `active`); `overview` remains the default active tab.

## Changes

1. **Tab button** — add after the Targeting button (`templates/report.html.j2:60`):
   ```html
   <button class="tab-btn" onclick="switchTab('datainterop')">Data InterOperability</button>
   ```
2. **Tab panel** — add after the closing `</div>` of `#tab-targeting` (`templates/report.html.j2:251`), before the `<script>` block:
   ```html
   <div id="tab-datainterop" class="tab-content">
     <div class="section">
       <h3>Data InterOperability</h3>
       <p>Content coming soon.</p>
     </div>
   </div>
   ```
3. **Test** — add one assertion in `tests/test_render.py` that the rendered HTML contains both the tab button (`switchTab('datainterop')`) and the panel (`id="tab-datainterop"`).

## Out of scope (YAGNI)

No KPIs, charts, tables, or query wiring. Those are a separate spec once the tab's content is decided. The existing `switchTab` JS already handles arbitrary tab ids, so no JS change is needed.

## Success criteria

- `python render.py` produces `report.html` with a seventh tab "Data InterOperability" (last), clickable, showing the heading and placeholder.
- Clicking it hides other panels and shows the scaffold; `overview` is still the default on load.
- `python -m pytest tests/ -q` is green (32 tests), 0 warnings.
