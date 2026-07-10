import os

import pandas as pd
import pytest

from render import compute_metrics, load_data, render


# --- load_data ---

def test_load_data_raises_if_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_data(str(tmp_path))


def test_load_data_returns_sixteen_keys(tmp_path, sample_data):
    files = {
        "q1": "q1_adoption_trend.parquet", "q2": "q2_by_product_family.parquet",
        "q3": "q3_by_arch_type.parquet", "q4": "q4_executions.parquet",
        "q5": "q5_ao_usage.parquet", "q6": "q6_population.parquet",
        "q7": "q7_data_fabric_monthly.parquet", "q8": "q8_data_fabric_providers.parquet",
        "q9": "q9_deployment_option.parquet", "q10": "q10_sku_gap_targeting.parquet",
        "q11": "q11_infra_no_telemetry.parquet",
        "q12": "q12_data_fabric_trialing_monthly.parquet",
        "q13": "q13_data_interop_customers.parquet",
        "q14": "q14_data_interop_app_usage.parquet",
        "q15": "q15_connector_change_frequency.parquet",
        "q16": "q16_connector_changes_by_region.parquet",
    }
    for key, fn in files.items():
        sample_data[key].to_parquet(tmp_path / fn, index=False)
    result = load_data(str(tmp_path))
    assert set(result.keys()) == set(files.keys())


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
    # Inject today=2026-06-15 so June is always treated as the current partial month
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
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
        "data_fabric_trend", "data_fabric_providers", "deployment_option_bar",
        "interop_dev", "interop_prod",
        "interop_apps_dev", "interop_apps_prod",
        "connector_changes_monthly", "connector_changes_dow",
        "connector_changes_by_region",
    }
    assert set(metrics["charts"].keys()) == expected


def test_compute_metrics_chart_has_data_and_layout(sample_data):
    metrics = compute_metrics(sample_data)
    for name, chart in metrics["charts"].items():
        if "variants" in chart:  # dropdown-driven chart: each variant holds data/layout
            for key, v in chart["variants"].items():
                assert "data" in v and "layout" in v, f"{name}[{key}] missing data/layout"
            continue
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


def test_compute_metrics_df_connectors_last_full_month(sample_data):
    # Inject today=2026-06-15 so June is the partial current month; May (21000) is last full month
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    assert metrics["kpis"]["df_connectors"]["value"] == 21000

def test_compute_metrics_df_tenants_last_full_month(sample_data):
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    assert metrics["kpis"]["df_tenants"]["value"] == 178

def test_compute_metrics_df_providers_count(sample_data):
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    assert metrics["kpis"]["df_providers"]["value"] == 4


def test_compute_metrics_new_charts_present(sample_data):
    metrics = compute_metrics(sample_data)
    for name in ("data_fabric_trend", "data_fabric_providers", "deployment_option_bar"):
        assert name in metrics["charts"], f"missing {name}"
        assert len(metrics["charts"][name]["data"]) > 0
        assert "layout" in metrics["charts"][name]


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


def test_compute_metrics_nan_arr_coerced_to_zero(sample_data):
    """Regression test: NaN/None ARR should become 0.0, not leak as nan into JSON."""
    # Build q10 directly from records so no pd.concat FutureWarning is triggered.
    # The null-ARR row sorts last (ARR=None → 0.0 after fillna) so it sits within
    # the top-20 window on this small fixture — the assertion is unconditional.
    q10_with_nan = pd.DataFrame([
        {"COMPANY_SFDC_ID": "001A", "COMPANY_NAME": "Acme Corp",
         "SEGMENT": "Enterprise", "USAGE_DEPLOYMENT_OPTION": "O11/ODC", "ARR_EUR": 500000.0},
        {"COMPANY_SFDC_ID": "001B", "COMPANY_NAME": "Globex",
         "SEGMENT": "Mid-Market", "USAGE_DEPLOYMENT_OPTION": "O11", "ARR_EUR": 250000.0},
        {"COMPANY_SFDC_ID": "001C", "COMPANY_NAME": "Initech",
         "SEGMENT": "Enterprise", "USAGE_DEPLOYMENT_OPTION": "O11/ODC", "ARR_EUR": 120000.0},
        {"COMPANY_SFDC_ID": "001X", "COMPANY_NAME": "NullARR Corp",
         "SEGMENT": "Small", "USAGE_DEPLOYMENT_OPTION": "O11", "ARR_EUR": None},
    ])

    test_data = sample_data.copy()
    test_data["q10"] = q10_with_nan

    metrics = compute_metrics(test_data)
    sku = metrics["tables"]["sku_gap_targeting"]

    null_row = next((row for row in sku if row["company"] == "NullARR Corp"), None)
    assert null_row is not None, "NullARR Corp must appear in sku_gap_targeting top-20"
    assert null_row["arr_eur"] == 0.0, f"Expected arr_eur=0.0 for None ARR, got {null_row['arr_eur']}"
    assert isinstance(null_row["arr_eur"], float)


def test_render_has_new_tabs(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    for tab in ("Data Fabric", "Targeting"):
        assert tab in content


def test_render_has_data_interoperability_tab(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "switchTab('datainterop')" in content
    assert 'id="tab-datainterop"' in content
    assert "Data InterOperability" in content


def test_compute_metrics_interop_dev_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_dev"]
    bar, line = chart["data"][0], chart["data"][1]
    # months sorted ascending -> Mar, Apr, May, Jun
    assert bar["type"] == "bar"
    assert bar["y"] == [86, 110, 133, 153]
    # % line = stage customers / monthly O11+ODC base
    assert line["y"][-1] == pytest.approx(round(153 / 785 * 100, 1))
    assert line["y"][0] == pytest.approx(round(86 / 714 * 100, 1))


def test_compute_metrics_interop_prod_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_prod"]
    assert chart["data"][0]["y"] == [63, 78, 97, 119]
    assert chart["data"][1]["y"][-1] == pytest.approx(round(119 / 785 * 100, 1))


def test_render_has_interop_charts(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    for cid in ("chart-interop-dev", "chart-interop-prod",
                "chart-interop-apps-dev", "chart-interop-apps-prod"):
        assert f"'{cid}'" in content and f'id="{cid}"' in content


def test_compute_metrics_interop_apps_prod_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_apps_prod"]
    cust_bar, apps_bar, line = chart["data"][0], chart["data"][1], chart["data"][2]
    # months ascending -> Mar, Apr, May, Jun
    assert cust_bar["type"] == "bar" and apps_bar["type"] == "bar"
    assert cust_bar["y"] == [23, 27, 34, 36]
    assert apps_bar["y"] == [23, 28, 36, 38]
    # % line uses customers / monthly O11+ODC base
    assert line["y"][-1] == pytest.approx(round(36 / 785 * 100, 1))


def test_compute_metrics_interop_apps_dev_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_apps_dev"]
    assert chart["data"][0]["y"] == [57, 83, 94, 109]
    assert chart["data"][1]["y"] == [62, 94, 112, 125]


def test_compute_metrics_connector_changes_monthly(sample_data):
    chart = compute_metrics(sample_data)["charts"]["connector_changes_monthly"]
    ar, rc = chart["data"][0], chart["data"][1]
    assert chart["layout"]["barmode"] == "stack"
    # months ascending: 2026-05 (add 4+2=6, recfg 3+4=7), 2026-06 (add 3+2+1=6, recfg 5+1+0=6)
    assert ar["x"] == ["2026-05", "2026-06"]
    assert ar["y"] == [6, 6]
    assert rc["y"] == [7, 6]


def test_compute_metrics_connector_changes_dow(sample_data):
    chart = compute_metrics(sample_data)["charts"]["connector_changes_dow"]
    ar, rc = chart["data"][0], chart["data"][1]
    assert ar["x"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    # Tue = 2026-06-02 (3) + 2026-05-05 (4) + 2026-05-12 (2) = 9 add/remove
    assert ar["y"][1] == 9
    # Sat = 2026-06-06 -> add/remove 1
    assert ar["y"][5] == 1
    # Reconfigure Tue = 5 + 3 + 4 = 12
    assert rc["y"][1] == 12


def test_compute_metrics_region_variants_shape(sample_data):
    obj = compute_metrics(sample_data)["charts"]["connector_changes_by_region"]
    assert obj["default"] == "all"
    assert obj["months"] == ["2026-05", "2026-06"]
    # one variant per month + "all" (no ring dimension anymore)
    assert set(obj["variants"].keys()) == {"all", "2026-05", "2026-06"}


def test_region_variant_all_has_one_bar_per_ring(sample_data):
    obj = compute_metrics(sample_data)["charts"]["connector_changes_by_region"]
    chart = obj["variants"]["all"]
    assert chart["layout"]["barmode"] == "group"
    # one trace (bar) per ring present in the data: ga then ea
    assert [t["name"] for t in chart["data"]] == ["ga", "ea"]
    ga, ea = chart["data"][0], chart["data"][1]
    assert ga["orientation"] == "h"
    # y reversed so largest region (Frankfurt, all-ga: 130+23=153) is last (top), Other first
    assert ga["y"][-1] == "EU (Frankfurt)"
    assert ga["x"][-1] == 153 and ea["x"][-1] == 0
    assert ga["y"][0] == "Other"  # 8 regions -> top 6 + Other
    # Other = AP Tokyo (ga, 3) + AP Mumbai (ea, 2)
    assert ga["x"][0] == 3 and ea["x"][0] == 2


def test_region_variant_month_filter(sample_data):
    obj = compute_metrics(sample_data)["charts"]["connector_changes_by_region"]
    # June only: Frankfurt is ga with 40+90=130 (excludes the 2026-05 rows)
    chart = obj["variants"]["2026-06"]
    ga = chart["data"][0]
    assert ga["name"] == "ga"
    assert ga["y"][-1] == "EU (Frankfurt)"
    assert ga["x"][-1] == 130


# --- SQL panels ---

def test_sql_map_has_entry_per_chart(sample_data):
    metrics = compute_metrics(sample_data)
    # every chart has a matching SQL entry
    assert set(metrics["sql"].keys()) == set(metrics["charts"].keys())
    # entries carry real SQL text
    assert "SELECT" in metrics["sql"]["interop_dev"].upper()
    assert "DEV_CUSTOMERS" in metrics["sql"]["interop_dev"]


def test_sql_map_multi_query_chart_includes_both(sample_data):
    metrics = compute_metrics(sample_data)
    trend = metrics["sql"]["data_fabric_trend"]
    assert "-- q7_data_fabric_monthly.sql" in trend
    assert "-- q12_data_fabric_trialing_monthly.sql" in trend


def test_sql_map_missing_file_degrades(sample_data, tmp_path):
    metrics = compute_metrics(sample_data, query_dir=str(tmp_path))
    assert "not found" in metrics["sql"]["adoption_trend"]


def test_render_has_sql_panels(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    # toggle + panel + copy button present for a sample of charts
    for key in ("adoption_trend", "interop_apps_prod", "data_fabric_trend"):
        assert f"toggleSql('{key}')" in content
        assert f'id="sqlcode-{key}"' in content
        assert f"copySql('{key}')" in content
    # SQL text is HTML-escaped in the <pre> (e.g. metric_value > 0 -> &gt;)
    assert "&gt;" in content
    # the reused adoption_trend chart gets a distinct DOM id on the Overview tab
    # (no duplicate element ids)
    assert 'id="sqlcode-adoption_overview"' in content
    import re
    ids = re.findall(r'id="(sql-[^"]+|sqlcode-[^"]+|sqlbtn-[^"]+)"', content)
    assert len(ids) == len(set(ids)), "duplicate SQL panel element ids"


def test_render_shows_df_kpi_and_sku_gap(sample_data, tmp_path):
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "21,000" in content        # df_connectors last full month
    assert "Acme Corp" in content     # top SKU-gap target


def test_compute_metrics_df_trialing_connectors_last_full_month(sample_data):
    # today=2026-06-15 → June is partial; May (1300) is the last full month
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    assert metrics["kpis"]["df_trialing_connectors"]["value"] == 1300


def test_compute_metrics_df_trialing_tenants_last_full_month(sample_data):
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    assert metrics["kpis"]["df_trialing_tenants"]["value"] == 25


def test_compute_metrics_df_trialing_connectors_mom_delta(sample_data):
    # May 1300 vs April 1000 → +30.0%
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    kpi = metrics["kpis"]["df_trialing_connectors"]
    assert kpi["delta"] == pytest.approx(30.0, rel=1e-3)
    assert kpi["is_pct"] is True
    assert kpi["direction"] == "up"


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


def test_render_shows_trialing_cards(sample_data, tmp_path):
    metrics = compute_metrics(sample_data, _today=pd.Timestamp("2026-06-15"))
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    # Card labels are unique to the template (the "Trialing" chart trace name has no comma-formatted value)
    assert "Trialing Connectors (last full mo.)" in content
    assert "Trialing Tenants (last full mo.)" in content
    assert "1,300" in content   # trialing connections, last full month, comma-formatted (KPI card only)
