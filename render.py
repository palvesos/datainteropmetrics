import os
import pathlib
from datetime import datetime, timezone

import pandas as pd
from jinja2 import Environment, FileSystemLoader


def load_data(data_dir: str = "data") -> dict:
    file_map = {
        "q1": "q1_adoption_trend.parquet",
        "q2": "q2_by_product_family.parquet",
        "q3": "q3_by_arch_type.parquet",
        "q4": "q4_executions.parquet",
        "q5": "q5_ao_usage.parquet",
        "q6": "q6_population.parquet",
        "q7": "q7_data_fabric_monthly.parquet",
        "q8": "q8_data_fabric_providers.parquet",
        "q9": "q9_deployment_option.parquet",
        "q10": "q10_sku_gap_targeting.parquet",
        "q11": "q11_infra_no_telemetry.parquet",
    }
    result = {}
    for key, filename in file_map.items():
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing Parquet file: {path}. Run /refresh first.")
        result[key] = pd.read_parquet(path)
    return result


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
    sku = int(df[df["IS_INTEROPERABILITY"] & df["HAS_SKU_INTEROPERABILITY"]]["COMPANY_COUNT"].sum())
    no_sku = int(df[df["IS_INTEROPERABILITY"] & ~df["HAS_SKU_INTEROPERABILITY"]]["COMPANY_COUNT"].sum())
    non_interop = int(df[~df["IS_INTEROPERABILITY"]]["COMPANY_COUNT"].sum())
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


def _chart_data_fabric_trend(df: pd.DataFrame) -> dict:
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    return {
        "data": [
            {"x": months, "y": df["TOTAL_CONNECTIONS"].tolist(), "type": "bar",
             "name": "Connections", "marker": {"color": "#60a5fa"}, "yaxis": "y"},
            {"x": months, "y": df["UNIQUE_TENANTS"].tolist(), "type": "scatter",
             "mode": "lines+markers", "name": "Tenants", "line": {"color": "#34d399", "width": 2}, "yaxis": "y2"},
        ],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Connections", "gridcolor": "#334155"},
            "yaxis2": {"title": "Tenants", "overlaying": "y", "side": "right", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"}, "margin": {"t": 20, "b": 50, "l": 70, "r": 60}, "autosize": True,
        },
    }


def _chart_data_fabric_providers(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["label"] = df["HOSTING"] + " / " + df["ENGINE"]
    df = df.sort_values("TOTAL_CONNECTIONS", ascending=True)
    labels = df["label"].tolist()
    return {
        "data": [
            {"y": labels, "x": df["TOTAL_CONNECTIONS"].tolist(), "type": "bar", "orientation": "h",
             "name": "Connections", "marker": {"color": "#60a5fa"}},
            {"y": labels, "x": df["UNIQUE_TENANTS"].tolist(), "type": "bar", "orientation": "h",
             "name": "Tenants", "marker": {"color": "#34d399"}},
        ],
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"}, "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 130, "r": 20}, "autosize": True,
        },
    }


def _chart_deployment_option_bar(df: pd.DataFrame) -> dict:
    df = df.sort_values("USAGE_DEPLOYMENT_OPTION")
    opts = df["USAGE_DEPLOYMENT_OPTION"].tolist()
    return {
        "data": [
            {"x": opts, "y": df["TOTAL_CUSTOMERS"].tolist(), "type": "bar",
             "name": "Customers", "marker": {"color": "#334155"}},
            {"x": opts, "y": df["CUSTOMERS_WITH_AGENTS"].tolist(), "type": "bar",
             "name": "With ODC Agents", "marker": {"color": "#34d399"}},
        ],
        "layout": {
            "barmode": "overlay",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"}, "yaxis": {"title": "Customers", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"}, "margin": {"t": 20, "b": 50, "l": 60, "r": 20}, "autosize": True,
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
            "barmode": "group",
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
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a",
            "font": {"color": "#94a3b8"},
            "xaxis": {"title": "Companies", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 140, "r": 20},
            "autosize": True,
        },
    }


def compute_metrics(data: dict, _today: pd.Timestamp | None = None) -> dict:
    q1 = data["q1"].sort_values("MONTH_START", ascending=False).reset_index(drop=True)
    q4 = data["q4"].sort_values("MONTH", ascending=False).reset_index(drop=True)
    q5 = data["q5"].sort_values("REPORT_MONTH", ascending=False).reset_index(drop=True)
    q6 = data["q6"]

    cur = q1.iloc[0]
    prev = q1.iloc[1] if len(q1) > 1 else None

    adoption_pct = float(cur["ADOPTION_PCT"])
    adoption_delta = float(cur["ADOPTION_PCT"] - prev["ADOPTION_PCT"]) if prev is not None else 0.0

    active_customers = int(cur["INTEROP_CUSTOMERS"])
    customers_delta = int(cur["INTEROP_CUSTOMERS"] - prev["INTEROP_CUSTOMERS"]) if prev is not None else 0

    today = (_today or pd.Timestamp.today()).normalize()
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

    q5_cur = q5.iloc[0]
    q5_prev = q5.iloc[1] if len(q5) > 1 else None
    prod_ao = int(q5_cur["PROD_AO_LAST_WEEK"])
    if q5_prev is not None and q5_prev["PROD_AO_LAST_WEEK"] > 0:
        ao_delta_pct = float(
            (q5_cur["PROD_AO_LAST_WEEK"] - q5_prev["PROD_AO_LAST_WEEK"]) / q5_prev["PROD_AO_LAST_WEEK"] * 100
        )
    else:
        ao_delta_pct = 0.0

    sku_gap = int(q6[q6["IS_INTEROPERABILITY"] & ~q6["HAS_SKU_INTEROPERABILITY"]]["COMPANY_COUNT"].sum())

    # --- Data Fabric (q7 monthly totals, last complete month) ---
    q7 = data["q7"].sort_values("MONTH", ascending=False).reset_index(drop=True)
    q7_full = q7[q7["MONTH"] < current_month_start].reset_index(drop=True)
    df_cur = q7_full.iloc[0] if len(q7_full) else q7.iloc[0]
    df_prev = q7_full.iloc[1] if len(q7_full) > 1 else None

    def _pct_delta(cur, prev):
        if prev is None or pd.isna(prev) or prev == 0:
            return 0.0
        return float((cur - prev) / prev * 100)

    df_connections = int(df_cur["TOTAL_CONNECTIONS"])
    df_tenants = int(df_cur["UNIQUE_TENANTS"])
    conn_delta = _pct_delta(df_cur["TOTAL_CONNECTIONS"], df_prev["TOTAL_CONNECTIONS"] if df_prev is not None else None)
    tenant_delta = _pct_delta(df_cur["UNIQUE_TENANTS"], df_prev["UNIQUE_TENANTS"] if df_prev is not None else None)
    df_providers = int((data["q8"]["TOTAL_CONNECTIONS"] > 0).sum())

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

    # --- Targeting (q10 SKU gap, q11 no-telemetry) ---
    q10 = data["q10"]
    arr_at_risk = float(q10["ARR_EUR"].fillna(0).sum())
    sku_gap_count = int(len(q10))
    sku_gap_targeting = [
        {"company": r["COMPANY_NAME"], "segment": r["SEGMENT"],
         "deployment": r["USAGE_DEPLOYMENT_OPTION"], "arr_eur": float(r["ARR_EUR"]) if pd.notna(r["ARR_EUR"]) else 0.0}
        for _, r in q10.sort_values("ARR_EUR", ascending=False).head(20).iterrows()
    ]
    infra_no_telemetry = [
        {"company": r["COMPANY_NAME"], "arch": r["ARCHITECTURE_TYPE"],
         "deployment": r["USAGE_DEPLOYMENT_OPTION"], "activation_code": r["ACTIVATION_CODE"]}
        for _, r in data["q11"].head(20).iterrows()
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
            "df_connections": {"value": df_connections, "delta": round(conn_delta, 1), "is_pct": True,
                               "direction": "up" if conn_delta >= 0 else "down"},
            "df_tenants": {"value": df_tenants, "delta": round(tenant_delta, 1), "is_pct": True,
                           "direction": "up" if tenant_delta >= 0 else "down"},
            "df_providers": {"value": df_providers},
            "arr_at_risk": {"value": round(arr_at_risk, 2)},
        },
        "sku_gap": sku_gap,
        "sku_gap_count": sku_gap_count,
        "charts": {
            "adoption_trend": _chart_adoption_trend(q1),
            "population_donut": _chart_population_donut(q6),
            "executions_bar": _chart_executions_bar(data["q4"]),
            "ao_usage_line": _chart_ao_usage_line(data["q5"]),
            "product_family_bar": _chart_product_family_bar(data["q2"]),
            "arch_type_bar": _chart_arch_type_bar(data["q3"]),
            "data_fabric_trend": _chart_data_fabric_trend(data["q7"]),
            "data_fabric_providers": _chart_data_fabric_providers(data["q8"]),
            "deployment_option_bar": _chart_deployment_option_bar(data["q9"]),
        },
        "tables": {
            "adoption_trend": table_rows,
            "sku_gap_targeting": sku_gap_targeting,
            "infra_no_telemetry": infra_no_telemetry,
        },
    }


def render(
    metrics: dict,
    template_path: str = "templates/report.html.j2",
    output_path: str = "report.html",
) -> None:
    env = Environment(loader=FileSystemLoader(pathlib.Path(__file__).parent), autoescape=False)
    template = env.get_template(template_path)
    html = template.render(**metrics)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    data = load_data()
    metrics = compute_metrics(data)
    render(metrics)
    print("Report written to report.html")
