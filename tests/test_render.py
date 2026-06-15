import os

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
