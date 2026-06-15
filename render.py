import os
from datetime import datetime, timezone

import pandas as pd


def load_data(data_dir: str = "data") -> dict:
    file_map = {
        "q1": "q1_adoption_trend.parquet",
        "q2": "q2_by_product_family.parquet",
        "q3": "q3_by_arch_type.parquet",
        "q4": "q4_executions.parquet",
        "q5": "q5_ao_usage.parquet",
        "q6": "q6_population.parquet",
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
        },
        "sku_gap": sku_gap,
        "charts": {
            "adoption_trend": _chart_adoption_trend(q1),
            "population_donut": _chart_population_donut(q6),
            "executions_bar": _chart_executions_bar(data["q4"]),
            "ao_usage_line": _chart_ao_usage_line(data["q5"]),
            "product_family_bar": _chart_product_family_bar(data["q2"]),
            "arch_type_bar": _chart_arch_type_bar(data["q3"]),
        },
        "tables": {
            "adoption_trend": table_rows,
        },
    }


def render(
    metrics: dict,
    template_path: str = "templates/report.html.j2",
    output_path: str = "report.html",
) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    data = load_data()
    metrics = compute_metrics(data)
    render(metrics)
    print("Report written to report.html")
