import os

import pandas as pd
import pytest

from render import compute_metrics, load_data, render


# --- load_data ---

def test_load_data_raises_if_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_data(str(tmp_path))


def test_load_data_returns_all_keys(tmp_path, sample_data):
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
        "q17": "q17_changes_per_customer_by_region_ring.parquet",
        "q18": "q18_change_heatmap_region_weekday.parquet",
        "q19": "q19_o11_customers_removed_infra.parquet",
        "q20": "q20_connector_removal_events_by_company.parquet",
        "q21": "q21_multi_o11_infra_with_df.parquet",
        "q22": "q22_connector_removal_events_multi_o11.parquet",
        "q23": "q23_o11_customers_removed_infra_multi_o11.parquet",
        "q26": "q26_t1a_multipipeline_tam_monthly.parquet",
        "q27": "q27_t1b_multipipeline_reach.parquet",
        "q28": "q28_t1c_multipipeline_validated.parquet",
        "q29": "q29_t1d_multipipeline_depth.parquet",
        "q30": "q30_t2a_multiinfra_tam_monthly.parquet",
        "q31": "q31_t2b_multiinfra_reach.parquet",
        "q32": "q32_t2c_multiinfra_validated.parquet",
        "q33": "q33_t2d_multiinfra_depth.parquet",
        "q34": "q34_t2c_multiinfra_validated_unification.parquet",
        "q35": "q35_t2d_multiinfra_depth_unification.parquet",
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
        "interop_dev", "interop_nonprod", "interop_prod",
        "interop_apps_dev", "interop_apps_nonprod", "interop_apps_prod",
        "connector_changes_monthly", "connector_changes_dow",
        "connector_changes_by_region",
        "changes_per_tenant_combo",
        "change_heatmap",
        "t1a_tam", "t1b_reach", "t1c_validated", "t1d_depth",
        "t2a_tam", "t2b_reach", "t2c_validated", "t2d_depth",
        "t2c_validated_unification", "t2d_depth_unification",
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


def test_compute_metrics_o11_infra_removals_table(sample_data):
    rows = compute_metrics(sample_data)["tables"]["o11_infra_removals"]
    assert len(rows) == 2
    assert rows[0]["company"] == "Umbrella"    # sorted by days_silent desc (170 > 101)
    assert rows[0]["days_silent"] == 170
    assert rows[0]["last_seen"] == "2026-01-28"
    assert rows[0]["n_envs"] == 1
    assert rows[0]["peak_count"] == 1
    assert rows[0]["last_count"] == 1
    assert rows[1]["company"] == "Stark Ind"
    assert rows[1]["n_envs"] == 2


def test_compute_metrics_removal_events_by_company_table(sample_data):
    rows = compute_metrics(sample_data)["tables"]["removal_events_by_company"]
    assert len(rows) == 3
    # sorted by removal_events desc, tie-broken by connectors_removed desc
    assert [r["company"] for r in rows] == ["Umbrella", "Stark Ind", "Wayne Enterprises"]
    assert rows[0]["removal_events"] == 4
    assert rows[0]["connectors_removed"] == 5
    assert rows[0]["peak_connectors"] == 8
    assert rows[0]["connectors_today"] == 8
    assert rows[1]["peak_connectors"] == 6
    assert rows[1]["connectors_today"] == 3


def test_compute_metrics_multi_o11_with_df_table(sample_data):
    rows = compute_metrics(sample_data)["tables"]["multi_o11_with_df"]
    assert len(rows) == 3
    # sorted by df_connectors desc, tie-broken by o11_infras desc
    assert [r["company"] for r in rows] == ["Cyberdyne", "Tyrell Corp", "Weyland"]
    assert rows[0]["o11_infras"] == 2
    assert rows[0]["df_connectors"] == 10
    assert rows[1]["o11_infras"] == 5   # Tyrell before Weyland on infra tie-break at 4 connectors


def test_render_has_multi_o11_with_df_table(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "Multiple O11 Infrastructures Using Data Fabric" in content
    assert "Cyberdyne" in content
    assert "toggleSql('multi_o11_with_df')" in content


def test_compute_metrics_removal_events_multi_o11_table(sample_data):
    rows = compute_metrics(sample_data)["tables"]["removal_events_multi_o11"]
    assert len(rows) == 2
    assert [r["company"] for r in rows] == ["MultiCorp A", "MultiCorp B"]
    assert rows[0]["o11_infras"] == 3
    assert rows[0]["removal_events"] == 2
    assert rows[0]["peak_connectors"] == 10
    assert rows[0]["connectors_today"] == 7


def test_compute_metrics_removal_events_multi_o11_empty(sample_data):
    """q22 is empty in production; compute must degrade to an empty list, not raise."""
    import pandas as pd
    data = dict(sample_data)
    data["q22"] = sample_data["q22"].iloc[0:0]  # empty, columns preserved
    assert compute_metrics(data)["tables"]["removal_events_multi_o11"] == []


def test_compute_metrics_o11_infra_removals_multi_o11_table(sample_data):
    rows = compute_metrics(sample_data)["tables"]["o11_infra_removals_multi_o11"]
    assert len(rows) == 1
    assert rows[0]["company"] == "MultiRemoved"
    assert rows[0]["o11_infras"] == 11
    assert rows[0]["days_silent"] == 101


def test_render_has_multi_o11_removal_tables(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "Connector Removal Events — Multi-O11-Infra Customers" in content
    assert "Fully Removed O11 Connector Infrastructure — Multi-O11-Infra Customers" in content
    assert "MultiCorp A" in content
    assert "MultiRemoved" in content


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


def _tab_slice(content: str, tab_id: str) -> str:
    """The HTML belonging to one tab: from its opening div to the next tab's."""
    start = content.index(f'id="tab-{tab_id}"')
    nxt = content.find('<div id="tab-', start + 1)
    return content[start:nxt if nxt != -1 else len(content)]


def test_render_has_connector_changes_tab(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "switchTab('connectorchanges')" in content
    assert 'id="tab-connectorchanges"' in content
    assert (">Data InterOperability - UI Telemetry</button>") in content


def test_connector_change_charts_live_on_their_own_tab(sample_data, tmp_path):
    """The q15-q18 change-frequency views moved off the Data InterOperability tab."""
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    changes = _tab_slice(content, "connectorchanges")
    interop = _tab_slice(content, "datainterop")
    for cid in ("chart-connector-changes-monthly", "chart-connector-changes-dow",
                "chart-connector-changes-by-region", "chart-changes-per-tenant",
                "chart-change-heatmap"):
        assert f'id="{cid}"' in changes, f"{cid} missing from Connector Changes tab"
        assert f'id="{cid}"' not in interop, f"{cid} still on Data InterOperability tab"
    # the freeze-window table is derived from the same q18 data and moves with it
    assert "Recommended Connector Freeze Window" in changes
    assert "Recommended Connector Freeze Window" not in interop
    # the interop customer/app charts stay put
    for cid in ("chart-interop-dev", "chart-interop-apps-dev"):
        assert f'id="{cid}"' in interop


def test_render_has_o11_infra_removals_table(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "Fully Removed Their O11 Connector Infrastructure" in content
    assert "Umbrella" in content
    assert "Stark Ind" in content


def test_render_has_removal_events_by_company_table(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    assert "Connector Removal Events by Company" in content
    assert "Wayne Enterprises" in content


def test_render_has_sql_panels_for_table_only_sections(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    for key in ("o11_infra_removals", "removal_events_by_company", "multi_o11_with_df",
                "removal_events_multi_o11", "o11_infra_removals_multi_o11"):
        assert f"toggleSql('{key}')" in content
        assert f'id="sqlcode-{key}"' in content
        assert f"copySql('{key}')" in content


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


def test_compute_metrics_interop_nonprod_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_nonprod"]
    assert chart["data"][0]["y"] == [81, 99, 118, 141]
    assert chart["data"][1]["y"][-1] == pytest.approx(round(141 / 785 * 100, 1))


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
    for cid in ("chart-interop-dev", "chart-interop-nonprod", "chart-interop-prod",
                "chart-interop-apps-dev", "chart-interop-apps-nonprod",
                "chart-interop-apps-prod"):
        assert f"'{cid}'" in content and f'id="{cid}"' in content


def test_compute_metrics_interop_apps_prod_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_apps_prod"]
    cust_bar, apps_bar, agents_bar, line = (
        chart["data"][0], chart["data"][1], chart["data"][2], chart["data"][3])
    # months ascending -> Mar, Apr, May, Jun
    assert cust_bar["type"] == "bar" and apps_bar["type"] == "bar"
    assert cust_bar["y"] == [23, 27, 34, 36]
    assert apps_bar["y"] == [23, 28, 36, 38]
    assert agents_bar["type"] == "bar"
    assert agents_bar["y"] == [4, 6, 8, 9]
    # % line uses customers / monthly O11+ODC base
    assert line["y"][-1] == pytest.approx(round(36 / 785 * 100, 1))


def test_compute_metrics_interop_apps_dev_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_apps_dev"]
    assert chart["data"][0]["y"] == [57, 83, 94, 109]
    assert chart["data"][1]["y"] == [62, 94, 112, 125]
    assert chart["data"][2]["y"] == [12, 19, 24, 30]


def test_interop_apps_agents_are_a_separate_series(sample_data):
    """Agents are reported alongside apps, not folded into the app count."""
    chart = compute_metrics(sample_data)["charts"]["interop_apps_dev"]
    names = [t["name"] for t in chart["data"]]
    assert sum("Agent" in n for n in names) == 1
    agents = next(t for t in chart["data"] if "Agent" in t["name"])
    apps = chart["data"][1]
    assert agents["y"] != apps["y"]


def test_compute_metrics_interop_apps_nonprod_chart(sample_data):
    metrics = compute_metrics(sample_data)
    chart = metrics["charts"]["interop_apps_nonprod"]
    cust_bar, apps_bar, agents_bar, line = (
        chart["data"][0], chart["data"][1], chart["data"][2], chart["data"][3])
    assert cust_bar["y"] == [29, 36, 46, 54]
    assert apps_bar["y"] == [59, 78, 100, 114]
    assert agents_bar["y"] == [9, 14, 18, 22]
    assert line["y"][-1] == pytest.approx(round(54 / 785 * 100, 1))


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


def test_changes_per_tenant_combo(sample_data):
    chart = compute_metrics(sample_data)["charts"]["changes_per_tenant_combo"]
    assert chart["layout"]["barmode"] == "group"
    # 4 traces: ga avg (bar), ga median (line), ea avg (bar), ea median (line)
    assert [t["name"] for t in chart["data"]] == ["ga avg", "ga median", "ea avg", "ea median"]
    ga_avg, ga_med, ea_avg, ea_med = chart["data"]
    assert ga_avg["type"] == "bar" and ga_med["type"] == "scatter"
    assert "+text" in ga_med["mode"]
    # regions ranked by total tenants; Frankfurt (36+1) is largest -> first on x
    assert ga_avg["x"][0] == "EU (Frankfurt)"
    assert ga_avg["y"][0] == 3.64          # Frankfurt ga avg
    assert ga_med["y"][0] == 2.0           # Frankfurt ga median
    assert ea_avg["y"][0] == 22.0          # Frankfurt ea avg (n=1)
    # value labels present on bars and median
    assert ga_avg["text"][0] == "3.6" and ga_med["text"][0] == "2"
    assert ga_avg["customdata"][0] == 36


def test_change_heatmap_variants(sample_data):
    obj = compute_metrics(sample_data)["charts"]["change_heatmap"]
    assert obj["default"] == "all|all|both"
    # 4 windows x 3 rings x 3 change-types
    assert len(obj["variants"]) == 36
    for window in ("all", "6m", "3m", "1m"):
        for ring in ("all", "ga", "ea"):
            for ctype in ("both", "add_remove", "reconfigure"):
                assert f"{window}|{ring}|{ctype}" in obj["variants"]
    hm = obj["variants"]["all|all|both"]["data"][0]
    assert hm["type"] == "heatmap"
    assert hm["x"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    # regions reversed so largest by tenants (Frankfurt: ga10+ea2=12) is at the top;
    # label carries per-ring tenant counts
    assert hm["y"][-1] == "EU (Frankfurt)  (ga 10 · ea 2)"
    # Frankfurt Tue = (ga add 8 + ea add 4)=12 / 12 tenants = 1.0
    assert hm["z"][-1][1] == 1.0
    # Frankfurt Wed = reconfigure 20 / 12 = 1.667
    assert hm["z"][-1][2] == round(20 / 12, 3)


def test_change_heatmap_type_and_ring_filter(sample_data):
    obj = compute_metrics(sample_data)["charts"]["change_heatmap"]
    # all-time, ga only + reconfigure only: Frankfurt Wed = 20 / 10 (ga tenants) = 2.0
    hm = obj["variants"]["all|ga|reconfigure"]["data"][0]
    assert "EU (Frankfurt)  (ga 10)" in hm["y"]
    fr = hm["y"].index("EU (Frankfurt)  (ga 10)")
    assert hm["z"][fr][2] == 2.0   # Wed reconfigure
    assert hm["z"][fr][1] == 0.0   # Tue (was add/remove) now empty


def test_freeze_windows_table(sample_data):
    rows = compute_metrics(sample_data)["tables"]["freeze_windows"]
    # regions with >=3 tenants, ordered by tenant count desc: Frankfurt(12), N.Virginia(5), Ireland(4)
    assert [r["region"] for r in rows] == [
        "EU (Frankfurt)", "US East (N. Virginia)", "EU (Ireland)"]
    fr = rows[0]
    assert fr["tenants"] == 12
    # Frankfurt busiest = Wed (reconfigure 20 / 12 = 1.67); quietest is a zero-activity day
    assert fr["busiest_day"] == "Wed"
    assert fr["busiest_avg"] == round(20 / 12, 2)
    assert fr["quietest_avg"] == 0.0
    # N. Virginia busiest = Wed (add/remove 10 / 5 = 2.0)
    assert rows[1]["busiest_day"] == "Wed" and rows[1]["busiest_avg"] == 2.0


def test_change_heatmap_window_filter(sample_data):
    obj = compute_metrics(sample_data)["charts"]["change_heatmap"]
    # last-month, ga, both: Frankfurt Tue add 3 / 8 tenants = 0.375; Wed reconfigure 5 / 8 = 0.625
    hm = obj["variants"]["1m|ga|both"]["data"][0]
    fr = [i for i, y in enumerate(hm["y"]) if y.startswith("EU (Frankfurt)")][0]
    assert hm["z"][fr][1] == round(3 / 8, 3)
    assert hm["z"][fr][2] == round(5 / 8, 3)
    # denominator is the 1m tenant count (8), reflected in the label
    assert "(ga 8)" in hm["y"][fr]


# --- SQL panels ---

def test_sql_map_has_entry_per_chart(sample_data):
    metrics = compute_metrics(sample_data)
    # every chart has a matching SQL entry (sql may also carry extra table-only entries)
    assert set(metrics["charts"].keys()) <= set(metrics["sql"].keys())
    # entries carry real SQL text
    assert "SELECT" in metrics["sql"]["interop_dev"].upper()
    assert "DEV_CUSTOMERS" in metrics["sql"]["interop_dev"]


def test_sql_map_has_entry_per_table_only_section(sample_data):
    metrics = compute_metrics(sample_data)
    for key in ("o11_infra_removals", "removal_events_by_company", "multi_o11_with_df",
                "removal_events_multi_o11", "o11_infra_removals_multi_o11"):
        assert key in metrics["sql"]
        assert "SELECT" in metrics["sql"][key].upper()


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


# --- Success Metrics tab ---

def test_funnel_stage_pct_is_relative_to_prior_stage(sample_data):
    chart = compute_metrics(sample_data)["charts"]["t2b_reach"]
    bars, pct = chart["data"]
    assert bars["x"] == ["2026-08", "2026-09"]
    assert bars["y"] == [43, 47]
    assert pct["y"] == [round(43 / 254 * 100, 1), round(47 / 258 * 100, 1)]


def test_infra_breakdown_stacks_one_multi_unresolved(sample_data):
    chart = compute_metrics(sample_data)["charts"]["t2c_validated"]
    assert chart["layout"]["barmode"] == "stack"
    by_name = {t["name"]: t["y"] for t in chart["data"]}
    assert by_name == {"1 O11 infra": [0, 2], "2+ O11 infras": [0, 0],
                       "Unresolved": [43, 45]}


def test_depth_trend_handles_empty_cohort(sample_data):
    chart = compute_metrics(sample_data)["charts"]["t2d_depth"]
    assert all(t["x"] == [] and t["y"] == [] for t in chart["data"])


def test_success_metrics_summary_uses_latest_month(sample_data):
    sm = compute_metrics(sample_data)["success_metrics"]
    assert "87 of 838 O11/ODC customers" in sm["task1_summary"]
    assert "19 of those 26" in sm["task1_summary"]
    t2 = sm["task2_summary"]
    assert "258 of 838 O11/ODC customers" in t2
    assert "2 have exactly 1 O11 infrastructure linked" in t2
    assert "45 are unresolved" in t2
    assert "No depth data" in t2


def test_render_has_success_metrics_tab(sample_data, tmp_path):
    metrics = compute_metrics(sample_data)
    output = str(tmp_path / "report.html")
    render(metrics, output_path=output)
    content = open(output).read()
    sm = _tab_slice(content, "successmetrics")
    for cid in ("chart-t1a-tam", "chart-t1b-reach", "chart-t1c-validated", "chart-t1d-depth",
                "chart-t2a-tam", "chart-t2b-reach", "chart-t2c-validated", "chart-t2d-depth",
                "chart-t2c-validated-unification", "chart-t2d-depth-unification"):
        assert f'id="{cid}"' in sm, f"{cid} missing from Success Metrics tab"
    assert "Signal: O11 Infra Configuration" in sm
