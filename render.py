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


def _chart_data_fabric_trend(df: pd.DataFrame, trialing_df: pd.DataFrame) -> dict:
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    trialing_df = trialing_df.sort_values("MONTH")
    trialing_months = trialing_df["MONTH"].dt.strftime("%Y-%m").tolist()
    return {
        "data": [
            {"x": months, "y": df["TOTAL_CONNECTORS"].tolist(), "type": "bar",
             "name": "Customer/Partner", "marker": {"color": "#60a5fa"}, "yaxis": "y"},
            {"x": trialing_months, "y": trialing_df["TOTAL_CONNECTORS"].tolist(), "type": "bar",
             "name": "Trialing", "marker": {"color": "#f59e0b"}, "yaxis": "y"},
            {"x": months, "y": df["UNIQUE_TENANTS"].tolist(), "type": "scatter",
             "mode": "lines+markers", "name": "Tenants", "line": {"color": "#34d399", "width": 2}, "yaxis": "y2"},
        ],
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Connectors", "gridcolor": "#334155"},
            "yaxis2": {"title": "Tenants", "overlaying": "y", "side": "right", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"}, "margin": {"t": 20, "b": 50, "l": 70, "r": 60}, "autosize": True,
        },
    }


def _chart_data_fabric_providers(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["label"] = df["HOSTING"] + " / " + df["ENGINE"]
    df = df.sort_values("TOTAL_CONNECTORS", ascending=True)
    labels = df["label"].tolist()
    return {
        "data": [
            {"y": labels, "x": df["TOTAL_CONNECTORS"].tolist(), "type": "bar", "orientation": "h",
             "name": "Connectors", "marker": {"color": "#60a5fa"}},
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


def _chart_interop_customers(df: pd.DataFrame, count_col: str, bar_color: str) -> dict:
    """Combo chart: bar = # customers with O11 Data Fabric connections in a stage;
    dashed line = that count as a % of the monthly O11+ODC customer base."""
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    counts = [int(c) for c in df[count_col].tolist()]
    denom = df["O11_ODC_CUSTOMERS"].tolist()
    pct = [round(c / d * 100, 1) if d else 0.0 for c, d in zip(counts, denom)]
    return {
        "data": [
            {"x": months, "y": counts, "type": "bar",
             "name": "# Customers w/ Data Connectors to O11",
             "marker": {"color": bar_color}, "yaxis": "y",
             "text": counts, "textposition": "auto"},
            {"x": months, "y": pct, "type": "scatter", "mode": "lines+markers+text",
             "name": "% Customers have O11 and ODC",
             "text": [f"{p}%" for p in pct], "textposition": "top center",
             "line": {"color": "#94a3b8", "width": 2, "dash": "dash"}, "yaxis": "y2"},
        ],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Customers", "gridcolor": "#334155"},
            "yaxis2": {"title": "% O11 + ODC", "overlaying": "y", "side": "right",
                       "gridcolor": "#334155", "ticksuffix": "%"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.12},
            "margin": {"t": 20, "b": 50, "l": 60, "r": 60}, "autosize": True,
        },
    }


def _chart_interop_app_usage(df: pd.DataFrame, cust_col: str, apps_col: str,
                             agents_col: str) -> dict:
    """Grouped bars (customers + apps + agents consuming an O11 data connection in a stage)
    plus a dashed line = customers as a % of the monthly O11+ODC customer base.
    Apps and agents are disjoint: an AI Agent is never counted in the app bar."""
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    custs = [int(c) for c in df[cust_col].tolist()]
    apps = [int(a) for a in df[apps_col].tolist()]
    agents = [int(a) for a in df[agents_col].tolist()]
    denom = df["O11_ODC_CUSTOMERS"].tolist()
    pct = [round(c / d * 100, 1) if d else 0.0 for c, d in zip(custs, denom)]
    return {
        "data": [
            {"x": months, "y": custs, "type": "bar", "name": "# Customers w/ Data Connections in Apps",
             "marker": {"color": "#60a5fa"}, "yaxis": "y", "text": custs, "textposition": "auto"},
            {"x": months, "y": apps, "type": "bar", "name": "# Apps w/ Data Connections",
             "marker": {"color": "#64748b"}, "yaxis": "y", "text": apps, "textposition": "auto"},
            {"x": months, "y": agents, "type": "bar", "name": "# Agents w/ Data Connections",
             "marker": {"color": "#34d399"}, "yaxis": "y", "text": agents, "textposition": "auto"},
            {"x": months, "y": pct, "type": "scatter", "mode": "lines+markers+text",
             "name": "% Customers have O11 and ODC",
             "text": [f"{p}%" for p in pct], "textposition": "top center",
             "line": {"color": "#94a3b8", "width": 2, "dash": "dash"}, "yaxis": "y2"},
        ],
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Customers / Apps / Agents", "gridcolor": "#334155"},
            "yaxis2": {"title": "% O11 + ODC", "overlaying": "y", "side": "right",
                       "gridcolor": "#334155", "ticksuffix": "%"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.12},
            "margin": {"t": 20, "b": 50, "l": 60, "r": 60}, "autosize": True,
        },
    }


def _chart_funnel_stage(df: pd.DataFrame, count_col: str, denom_col: str,
                         count_label: str, pct_label: str, bar_color: str) -> dict:
    """Combo chart for a single Success Metrics funnel stage: bar = customer count at this
    stage, dashed line = that count as a % of the PRIOR stage's count (the funnel denominator
    passed in as denom_col), monthly. Same shape as _chart_interop_customers, generalized so
    the denominator isn't hardcoded to the O11+ODC base -- each funnel stage's % is relative to
    the stage before it (TAM -> Reach -> Validated), not the whole customer base."""
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()
    counts = [int(c) if pd.notna(c) else 0 for c in df[count_col].tolist()]
    denom = df[denom_col].tolist()
    pct = [round(c / d * 100, 1) if d else 0.0 for c, d in zip(counts, denom)]
    return {
        "data": [
            {"x": months, "y": counts, "type": "bar", "name": count_label,
             "marker": {"color": bar_color}, "yaxis": "y",
             "text": counts, "textposition": "auto"},
            {"x": months, "y": pct, "type": "scatter", "mode": "lines+markers+text",
             "name": pct_label,
             "text": [f"{p}%" for p in pct], "textposition": "top center",
             "line": {"color": "#94a3b8", "width": 2, "dash": "dash"}, "yaxis": "y2"},
        ],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Customers", "gridcolor": "#334155"},
            "yaxis2": {"title": pct_label, "overlaying": "y", "side": "right",
                       "gridcolor": "#334155", "ticksuffix": "%"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.12},
            "margin": {"t": 20, "b": 50, "l": 60, "r": 60}, "autosize": True,
        },
    }


def _chart_infra_breakdown(df: pd.DataFrame) -> dict:
    """Stacked bar: Reach customers split by # distinct O11 infras linked (q32: LifeTime URLs) or
    handshaken with (q34: activation codes) that month -- 1, 2+, or Unresolved (connected but no
    O11 infra can be attributed yet). Replaces a single 'validated' count with the full breakdown."""
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()

    def col(name):
        return [int(v) if pd.notna(v) else 0 for v in df[name].tolist()]

    return {
        "data": [
            {"x": months, "y": col("ONE_INFRA_CUSTOMERS"), "type": "bar",
             "name": "1 O11 infra", "marker": {"color": "#60a5fa"}},
            {"x": months, "y": col("MULTI_INFRA_CUSTOMERS"), "type": "bar",
             "name": "2+ O11 infras", "marker": {"color": "#34d399"}},
            {"x": months, "y": col("UNRESOLVED_CUSTOMERS"), "type": "bar",
             "name": "Unresolved", "marker": {"color": "#64748b"}},
        ],
        "layout": {
            "barmode": "stack",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"},
            "yaxis": {"title": "Reach customers", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.12},
            "margin": {"t": 20, "b": 50, "l": 60, "r": 20}, "autosize": True,
        },
    }


def _chart_depth_trend(df: pd.DataFrame) -> dict:
    """3-line monthly trend: avg entities imported per O11 Data Fabric connection, dev / non-prod
    / prod. Handles an empty (0-row) input cleanly -- e.g. Task 2(d) has no validated cohort."""
    df = df.sort_values("MONTH")
    months = df["MONTH"].dt.strftime("%Y-%m").tolist()

    def series(col, name, color):
        y = [round(float(v), 1) if pd.notna(v) else None for v in df[col].tolist()]
        return {"x": months, "y": y, "type": "scatter", "mode": "lines+markers",
                "name": name, "line": {"color": color, "width": 2}}

    return {
        "data": [
            series("AVG_ENTITIES_DEV", "Dev", "#60a5fa"),
            series("AVG_ENTITIES_NONPROD", "Non-Prod", "#a78bfa"),
            series("AVG_ENTITIES_PROD", "Prod", "#34d399"),
        ],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "yaxis": {"title": "Avg entities / connection", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b"},
            "margin": {"t": 20, "b": 50, "l": 70, "r": 20}, "autosize": True,
        },
    }


def _chart_connector_changes_monthly(df: pd.DataFrame) -> dict:
    """Stacked bar of connector change events per month (add/remove + reconfigure)."""
    df = df.sort_values("DAY")
    g = df.groupby(df["DAY"].dt.strftime("%Y-%m"))[["ADD_REMOVE_EVENTS", "RECONFIGURE_EVENTS"]].sum()
    months = g.index.tolist()
    return {
        "data": [
            {"x": months, "y": [int(v) for v in g["ADD_REMOVE_EVENTS"]], "type": "bar",
             "name": "Add / Remove", "marker": {"color": "#60a5fa"}},
            {"x": months, "y": [int(v) for v in g["RECONFIGURE_EVENTS"]], "type": "bar",
             "name": "Reconfigure", "marker": {"color": "#f59e0b"}},
        ],
        "layout": {
            "barmode": "stack",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"},
            "yaxis": {"title": "Change events", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.12},
            "margin": {"t": 20, "b": 50, "l": 60, "r": 20}, "autosize": True,
        },
    }


def _chart_connector_changes_dow(df: pd.DataFrame) -> dict:
    """Stacked bar of connector change events by day of week (Mon-Sun)."""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow = df["DAY"].dt.dayofweek
    ar = [int(df.loc[dow == i, "ADD_REMOVE_EVENTS"].sum()) for i in range(7)]
    rc = [int(df.loc[dow == i, "RECONFIGURE_EVENTS"].sum()) for i in range(7)]
    return {
        "data": [
            {"x": names, "y": ar, "type": "bar", "name": "Add / Remove", "marker": {"color": "#60a5fa"}},
            {"x": names, "y": rc, "type": "bar", "name": "Reconfigure", "marker": {"color": "#f59e0b"}},
        ],
        "layout": {
            "barmode": "stack",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"},
            "yaxis": {"title": "Change events (12 mo.)", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.12},
            "margin": {"t": 20, "b": 50, "l": 60, "r": 20}, "autosize": True,
        },
    }


_RING_COLORS = {"ga": "#60a5fa", "ea": "#f59e0b"}


def _chart_connector_changes_by_region(df: pd.DataFrame, top_n: int = 6) -> dict:
    """Horizontal grouped bar of connector change events (add/remove + reconfigure) by cloud
    region (top-N + Other), one bar per ring (ga/ea) — only for rings present in the data."""
    data = []
    if len(df):
        g = df.copy()
        g["events"] = g["ADD_REMOVE_EVENTS"] + g["RECONFIGURE_EVENTS"]
        # rank regions by total events across rings, keep top-N + Other
        totals = g.groupby("REGION")["events"].sum().sort_values(ascending=False)
        top_regions = totals.head(top_n).index.tolist()
        keep = totals.index.isin(top_regions)
        region_order = top_regions + (["Other"] if (~keep).any() else [])
        g["region_label"] = g["REGION"].where(g["REGION"].isin(top_regions), "Other")
        pivot = g.groupby(["region_label", "RING"])["events"].sum().unstack("RING").fillna(0)
        # display largest region at top, "Other" at the bottom
        y = region_order[::-1]
        for ring in ("ga", "ea"):  # deterministic order; only rings present in the data
            if ring in pivot.columns:
                data.append({
                    "y": y,
                    "x": [int(pivot.loc[r, ring]) if r in pivot.index else 0 for r in y],
                    "type": "bar", "orientation": "h", "name": ring,
                    "marker": {"color": _RING_COLORS[ring]},
                })
    return {
        "data": data,
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"title": "Change events", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.08},
            "margin": {"t": 20, "b": 50, "l": 160, "r": 20}, "autosize": True,
        },
    }


def _chart_changes_per_tenant_combo(df: pd.DataFrame, top_n: int = 8) -> dict:
    """Vertical combo by region (top-N by tenants): grouped bars = AVG add/removes per tenant
    per ring, dashed line+markers = MEDIAN per ring. Value labels on both bars and median."""
    data = []
    if len(df):
        regions = (df.drop_duplicates(["REGION", "RING"]).groupby("REGION")["N_TENANTS"].sum()
                     .sort_values(ascending=False).head(top_n).index.tolist())
        for ring in ("ga", "ea"):
            sub = df[df["RING"] == ring].set_index("REGION")
            avg = [round(float(sub.loc[r, "AVG_CHANGES_PER_TENANT"]), 2) if r in sub.index else 0 for r in regions]
            med = [round(float(sub.loc[r, "MEDIAN_CHANGES_PER_TENANT"]), 2) if r in sub.index else 0 for r in regions]
            ns = [int(sub.loc[r, "N_TENANTS"]) if r in sub.index else 0 for r in regions]
            col = _RING_COLORS[ring]
            data.append({
                "x": regions, "y": avg, "type": "bar", "name": ring + " avg",
                "marker": {"color": col}, "customdata": ns,
                "text": [f"{v:.1f}" if v else "" for v in avg], "textposition": "outside",
                "textfont": {"color": "#e2e8f0"},
                "hovertemplate": "%{x} · " + ring + " avg: %{y} (n=%{customdata})<extra></extra>",
            })
            data.append({
                "x": regions, "y": med, "type": "scatter", "mode": "lines+markers+text",
                "name": ring + " median", "line": {"color": col, "width": 2, "dash": "dash"},
                "marker": {"color": col, "size": 7},
                "text": [f"{v:g}" if v else "" for v in med], "textposition": "top center",
                "textfont": {"color": "#e2e8f0"},
                "hovertemplate": "%{x} · " + ring + " median: %{y}<extra></extra>",
            })
    return {
        "data": data,
        "layout": {
            "barmode": "group",
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155", "tickangle": -30},
            "yaxis": {"title": "Add/removes per tenant (12 mo.)", "gridcolor": "#334155"},
            "legend": {"bgcolor": "#1e293b", "orientation": "h", "y": 1.12},
            "margin": {"t": 20, "b": 110, "l": 60, "r": 20}, "autosize": True,
        },
    }


_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _heatmap_region_weekday(df: pd.DataFrame, window: str, ring: str, ctype: str, top_n: int = 10) -> dict:
    """Region x weekday heatmap; cell = avg changes per tenant. `window` in 1m/3m/6m/all,
    `ring` in all/ga/ea, `ctype` in both/add_remove/reconfigure. Denominator = tenants in
    region x ring for that window (rings are disjoint, so ring='all' sums the per-ring counts)."""
    df = df[df["WINDOW_KEY"] == window]
    sub = df if ring == "all" else df[df["RING"] == ring]
    ev = sub if ctype == "both" else sub[sub["CHANGE_TYPE"] == ctype]
    # tenant denominator per region (one N per region x ring, summed across rings for 'all')
    tn = sub.drop_duplicates(["REGION", "RING"])
    nt = tn.groupby("REGION")["N_TENANTS"].sum()
    nt = nt[nt > 0].sort_values(ascending=False).head(top_n)
    regions = nt.index.tolist()
    events = (ev.groupby(["REGION", "WEEKDAY"])["EVENTS"].sum()
                if len(ev) else pd.Series(dtype=float))

    def _label(r):  # region name + tenant count per ring, e.g. "EU (Frankfurt)  (ga 10 · ea 2)"
        rows = tn[tn["REGION"] == r]
        parts = [f"{rg} {int(rows[rows['RING'] == rg]['N_TENANTS'].iloc[0])}"
                 for rg in ("ga", "ea") if (rows["RING"] == rg).any()]
        return f"{r}  ({' · '.join(parts)})" if parts else r

    labels, z = [], []
    for r in regions:
        labels.append(_label(r))
        z.append([round(int(events.get((r, wd), 0)) / nt[r], 3) if nt[r] else 0.0
                  for wd in range(1, 8)])
    # reverse so the largest region is at the top of the heatmap
    labels, z = labels[::-1], z[::-1]
    return {
        "data": [{
            "type": "heatmap", "x": _WEEKDAYS, "y": labels, "z": z,
            "colorscale": [[0, "#0f172a"], [0.5, "#1e40af"], [1, "#60a5fa"]],
            "colorbar": {"title": "avg/tenant", "titlefont": {"color": "#94a3b8"},
                         "tickfont": {"color": "#94a3b8"}},
            "hovertemplate": "%{y} · %{x}: %{z} changes/tenant<extra></extra>",
        }],
        "layout": {
            "paper_bgcolor": "#0f172a", "plot_bgcolor": "#0f172a", "font": {"color": "#94a3b8"},
            "xaxis": {"side": "top", "gridcolor": "#334155"},
            "yaxis": {"gridcolor": "#334155", "automargin": True},
            "margin": {"t": 30, "b": 20, "l": 160, "r": 20}, "autosize": True,
        },
    }


def _freeze_windows(df: pd.DataFrame, min_tenants: int = 3) -> list:
    """Per region (all-time, ga+ea, both change types): the weekday with the lowest avg changes
    per tenant (best freeze day), the quietest business day (Mon-Fri), and the busiest day to
    avoid. Weekday-level only — time-of-day isn't in the daily-snapshot telemetry."""
    df = df[df["WINDOW_KEY"] == "all"]
    if df.empty:
        return []
    names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    biz = {1, 2, 3, 4, 5}
    nt = df.drop_duplicates(["REGION", "RING"]).groupby("REGION")["N_TENANTS"].sum()
    ev = df.groupby(["REGION", "WEEKDAY"])["EVENTS"].sum()
    out = []
    for region in nt[nt >= min_tenants].sort_values(ascending=False).index:
        n = int(nt[region])
        avgs = {wd: 0.0 for wd in range(1, 8)}
        for wd in range(1, 8):
            if (region, wd) in ev.index:
                avgs[wd] = ev.loc[(region, wd)] / n
        qd = min(range(1, 8), key=lambda k: (avgs[k], k))            # lowest avg, earliest on tie
        qb = min(biz, key=lambda k: (avgs[k], k))
        bd = max(range(1, 8), key=lambda k: (avgs[k], -k))           # highest avg, earliest on tie
        out.append({
            "region": region, "tenants": n,
            "quietest_day": names[qd], "quietest_avg": round(avgs[qd], 2),
            "quietest_biz_day": names[qb], "quietest_biz_avg": round(avgs[qb], 2),
            "busiest_day": names[bd], "busiest_avg": round(avgs[bd], 2),
        })
    return out


def _build_heatmap_variants(df: pd.DataFrame) -> dict:
    """Precompute the region x weekday heatmap for every window x ring x change-type selection."""
    variants = {}
    for window in ("all", "6m", "3m", "1m"):
        for ring in ("all", "ga", "ea"):
            for ctype in ("both", "add_remove", "reconfigure"):
                variants[f"{window}|{ring}|{ctype}"] = _heatmap_region_weekday(df, window, ring, ctype)
    return {"variants": variants, "default": "all|all|both"}


def _build_region_variants(df: pd.DataFrame, top_n: int = 6) -> dict:
    """Precompute the by-region (one bar per ring) chart for every month selection, so the
    month dropdown just swaps a variant. Keys are the month string or 'all'."""
    df = df.copy()
    months = sorted(df["MONTH"].dt.strftime("%Y-%m").unique().tolist())
    variants = {"all": _chart_connector_changes_by_region(df, top_n)}
    for month in months:
        dfm = df[df["MONTH"].dt.strftime("%Y-%m") == month]
        variants[month] = _chart_connector_changes_by_region(dfm, top_n)
    return {"variants": variants, "months": months, "default": "all"}


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


# Maps each chart to the query file(s) that build it (order = display order).
CHART_SQL = {
    "adoption_trend": ["q1_adoption_trend"],
    "population_donut": ["q6_population"],
    "executions_bar": ["q4_executions"],
    "ao_usage_line": ["q5_ao_usage"],
    "product_family_bar": ["q2_by_product_family"],
    "arch_type_bar": ["q3_by_arch_type"],
    "data_fabric_trend": ["q7_data_fabric_monthly", "q12_data_fabric_trialing_monthly"],
    "data_fabric_providers": ["q8_data_fabric_providers"],
    "deployment_option_bar": ["q9_deployment_option"],
    "interop_dev": ["q13_data_interop_customers"],
    "interop_nonprod": ["q13_data_interop_customers"],
    "interop_prod": ["q13_data_interop_customers"],
    "interop_apps_dev": ["q14_data_interop_app_usage"],
    "interop_apps_nonprod": ["q14_data_interop_app_usage"],
    "interop_apps_prod": ["q14_data_interop_app_usage"],
    "connector_changes_monthly": ["q15_connector_change_frequency"],
    "connector_changes_dow": ["q15_connector_change_frequency"],
    "connector_changes_by_region": ["q16_connector_changes_by_region"],
    "changes_per_tenant_combo": ["q17_changes_per_customer_by_region_ring"],
    "change_heatmap": ["q18_change_heatmap_region_weekday"],
    "t1a_tam": ["q26_t1a_multipipeline_tam_monthly"],
    "t1b_reach": ["q27_t1b_multipipeline_reach"],
    "t1c_validated": ["q28_t1c_multipipeline_validated"],
    "t1d_depth": ["q29_t1d_multipipeline_depth"],
    "t2a_tam": ["q30_t2a_multiinfra_tam_monthly"],
    "t2b_reach": ["q31_t2b_multiinfra_reach"],
    "t2c_validated": ["q32_t2c_multiinfra_validated"],
    "t2d_depth": ["q33_t2d_multiinfra_depth"],
    "t2c_validated_unification": ["q34_t2c_multiinfra_validated_unification"],
    "t2d_depth_unification": ["q35_t2d_multiinfra_depth_unification"],
}

# Maps each table-only section (no chart) to its source query file(s), so it can still
# get a toggleable SQL panel via the same sql_panel() macro used for charts.
TABLE_SQL = {
    "o11_infra_removals": ["q19_o11_customers_removed_infra"],
    "removal_events_by_company": ["q20_connector_removal_events_by_company"],
    "multi_o11_with_df": ["q21_multi_o11_infra_with_df"],
    "removal_events_multi_o11": ["q22_connector_removal_events_multi_o11"],
    "o11_infra_removals_multi_o11": ["q23_o11_customers_removed_infra_multi_o11"],
}


def _funnel_latest(df: pd.DataFrame, count_col: str, denom_col: str) -> dict:
    """Latest-month (count, denominator, %) for one funnel stage, guarded for empty data."""
    if df.empty:
        return {"count": 0, "denom": 0, "pct": 0.0}
    row = df.sort_values("MONTH").iloc[-1]
    count = int(row[count_col]) if pd.notna(row[count_col]) else 0
    denom = int(row[denom_col]) if pd.notna(row[denom_col]) else 0
    pct = round(count / denom * 100, 1) if denom else 0.0
    return {"count": count, "denom": denom, "pct": pct}


def _depth_latest(df: pd.DataFrame) -> dict:
    """Latest month with any depth data (dev/nonprod/prod avg entities), guarded for 0 rows."""
    df = df.dropna(subset=["AVG_ENTITIES_DEV", "AVG_ENTITIES_NONPROD", "AVG_ENTITIES_PROD"], how="all")
    if df.empty:
        return None
    row = df.sort_values("MONTH").iloc[-1]
    return {
        "month": row["MONTH"].strftime("%Y-%m"),
        "dev": round(float(row["AVG_ENTITIES_DEV"]), 1) if pd.notna(row["AVG_ENTITIES_DEV"]) else None,
        "nonprod": round(float(row["AVG_ENTITIES_NONPROD"]), 1) if pd.notna(row["AVG_ENTITIES_NONPROD"]) else None,
        "prod": round(float(row["AVG_ENTITIES_PROD"]), 1) if pd.notna(row["AVG_ENTITIES_PROD"]) else None,
    }


def _breakdown_latest(df: pd.DataFrame) -> dict:
    """Latest-month (one_infra, multi_infra, unresolved, reach) counts from a q32/q34-style
    infra-breakdown table, guarded for empty data."""
    if df.empty:
        return {"one_infra": 0, "multi_infra": 0, "unresolved": 0, "reach": 0}
    row = df.sort_values("MONTH").iloc[-1]
    return {
        "one_infra": int(row["ONE_INFRA_CUSTOMERS"]) if pd.notna(row["ONE_INFRA_CUSTOMERS"]) else 0,
        "multi_infra": int(row["MULTI_INFRA_CUSTOMERS"]) if pd.notna(row["MULTI_INFRA_CUSTOMERS"]) else 0,
        "unresolved": int(row["UNRESOLVED_CUSTOMERS"]) if pd.notna(row["UNRESOLVED_CUSTOMERS"]) else 0,
        "reach": int(row["REACH_CUSTOMERS"]) if pd.notna(row["REACH_CUSTOMERS"]) else 0,
    }


def _build_success_metrics_summary(data: dict) -> dict:
    """Executive summary text for the Data InterOperability Success Metrics tab: the latest
    funnel numbers for each task, spelled out in one sentence per stage, plus the business-concept
    definitions behind each stage so the numbers are legible without reading the SQL."""
    t1_tam = _funnel_latest(data["q26"], "TAM_CUSTOMERS", "O11_ODC_CUSTOMERS")
    t1_reach = _funnel_latest(data["q27"], "REACH_CUSTOMERS", "TAM_CUSTOMERS")
    t1_validated = _funnel_latest(data["q28"], "VALIDATED_CUSTOMERS", "REACH_CUSTOMERS")
    t1_depth = _depth_latest(data["q29"])

    t2_tam = _funnel_latest(data["q30"], "TAM_CUSTOMERS", "O11_ODC_CUSTOMERS")
    t2_reach = _funnel_latest(data["q31"], "REACH_CUSTOMERS", "TAM_CUSTOMERS")
    t2_breakdown = _breakdown_latest(data["q32"])
    t2_depth = _depth_latest(data["q33"])

    t1_depth_txt = (
        f"Among validated customers, connections carry an average of {t1_depth['dev']} entities "
        f"in Dev, {t1_depth['nonprod']} in Non-Prod, and {t1_depth['prod']} in Prod ({t1_depth['month']})."
        if t1_depth else
        "No depth data yet: too few validated customers have entity-usage telemetry this period."
    )
    t2_depth_txt = (
        f"Among validated customers, connections carry an average of {t2_depth['dev']} entities "
        f"in Dev, {t2_depth['nonprod']} in Non-Prod, and {t2_depth['prod']} in Prod ({t2_depth['month']})."
        if t2_depth else
        "No depth data: zero customers have validated this stage yet (see warning banner below), "
        "so there is no connection population to measure entity depth on."
    )

    task1_summary = (
        f"{t1_tam['count']} of {t1_tam['denom']} O11/ODC customers ({t1_tam['pct']}%) are TAM -- "
        f"their O11 infrastructure has 2+ parallel pipelines. Of those, {t1_reach['count']} "
        f"({t1_reach['pct']}%) reach baseline adoption (at least one live O11 Data Fabric "
        f"connection), and {t1_validated['count']} of those {t1_reach['count']} ({t1_validated['pct']}%) "
        f"are validated -- connected to 2+ distinct non-development O11 environments. {t1_depth_txt}"
    )
    task2_summary = (
        f"{t2_tam['count']} of {t2_tam['denom']} O11/ODC customers ({t2_tam['pct']}%) are TAM -- "
        f"they hold 2+ distinct O11 activation codes (separate infrastructures). Of those, "
        f"{t2_reach['count']} ({t2_reach['pct']}%) reach baseline adoption (at least one live O11 "
        f"Data Fabric connection). Of those {t2_breakdown['reach']} reach customers: "
        f"{t2_breakdown['one_infra']} have exactly 1 O11 infrastructure linked, "
        f"{t2_breakdown['multi_infra']} have 2+ (validated), and "
        f"{t2_breakdown['unresolved']} are unresolved (no O11 infrastructure configuration event "
        f"yet -- this signal only exists from 2026-08-27). {t2_depth_txt}"
    )

    return {
        "task1_summary": task1_summary,
        "task2_summary": task2_summary,
    }


def _build_sql_map(query_dir: str = "queries") -> dict:
    """Return {key: sql_text} for every chart and table-only section, by reading the
    source .sql files. Multi-query charts concatenate their queries, each prefixed
    with a `-- filename.sql` header."""
    out = {}
    for chart, files in {**CHART_SQL, **TABLE_SQL}.items():
        parts = []
        for fn in files:
            path = os.path.join(query_dir, fn + ".sql")
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read().strip()
            except FileNotFoundError:
                text = f"-- {fn}.sql not found"
            if len(files) > 1:
                text = f"-- {fn}.sql\n{text}"
            parts.append(text)
        out[chart] = "\n\n".join(parts)
    return out


def compute_metrics(data: dict, _today: pd.Timestamp | None = None, query_dir: str = "queries") -> dict:
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

    df_connectors = int(df_cur["TOTAL_CONNECTORS"])
    df_tenants = int(df_cur["UNIQUE_TENANTS"])
    conn_delta = _pct_delta(df_cur["TOTAL_CONNECTORS"], df_prev["TOTAL_CONNECTORS"] if df_prev is not None else None)
    tenant_delta = _pct_delta(df_cur["UNIQUE_TENANTS"], df_prev["UNIQUE_TENANTS"] if df_prev is not None else None)
    df_providers = int((data["q8"]["TOTAL_CONNECTORS"] > 0).sum())

    # --- Data Fabric trialing (q12 monthly totals, last complete month) ---
    q12 = data["q12"].sort_values("MONTH", ascending=False).reset_index(drop=True)
    q12_full = q12[q12["MONTH"] < current_month_start].reset_index(drop=True)
    dft_cur = q12_full.iloc[0] if len(q12_full) else q12.iloc[0]
    dft_prev = q12_full.iloc[1] if len(q12_full) > 1 else None
    df_trialing_connectors = int(dft_cur["TOTAL_CONNECTORS"])
    df_trialing_tenants = int(dft_cur["UNIQUE_TENANTS"])
    trialing_conn_delta = _pct_delta(dft_cur["TOTAL_CONNECTORS"], dft_prev["TOTAL_CONNECTORS"] if dft_prev is not None else None)
    trialing_tenant_delta = _pct_delta(dft_cur["UNIQUE_TENANTS"], dft_prev["UNIQUE_TENANTS"] if dft_prev is not None else None)

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
    o11_infra_removals = [
        {"company": r["COMPANY_NAME"], "tenant_id": r["TENANT_ID"], "n_envs": int(r["N_O11_ENVS"]),
         "peak_count": int(r["PEAK_CONNECTORS"]), "last_count": int(r["LAST_KNOWN_CONNECTORS"]),
         "last_seen": r["LAST_CONNECTOR_TELEMETRY_DAY"].strftime("%Y-%m-%d"),
         "days_silent": int(r["DAYS_SINCE_CONNECTOR_TELEMETRY"])}
        for _, r in data["q19"].sort_values("DAYS_SINCE_CONNECTOR_TELEMETRY", ascending=False).iterrows()
    ]
    removal_events_by_company = [
        {"company": r["COMPANY_NAME"], "removal_events": int(r["REMOVAL_EVENTS"]),
         "connectors_removed": int(r["TOTAL_CONNECTORS_REMOVED"]),
         "peak_connectors": int(r["PEAK_TOTAL_CONNECTORS"]),
         "connectors_today": int(r["CONNECTORS_TODAY"])}
        for _, r in data["q20"].sort_values(
            ["REMOVAL_EVENTS", "TOTAL_CONNECTORS_REMOVED"], ascending=False).iterrows()
    ]
    multi_o11_with_df = [
        {"company": r["COMPANY_NAME"], "o11_infras": int(r["NUM_O11_INFRAS"]),
         "df_providers": int(r["NUM_DF_PROVIDERS"]), "df_connectors": int(r["CURRENT_DF_CONNECTORS"])}
        for _, r in data["q21"].sort_values(
            ["CURRENT_DF_CONNECTORS", "NUM_O11_INFRAS"], ascending=False).iterrows()
    ]
    # q22/q23: removal events + full removals restricted to the q21 (multi-O11-infra) population.
    # Guarded for empty results (e.g. q22 currently has no multi-infra customers with removals).
    q22 = data["q22"]
    removal_events_multi_o11 = (
        [{"company": r["COMPANY_NAME"], "o11_infras": int(r["NUM_O11_INFRAS"]),
          "removal_events": int(r["REMOVAL_EVENTS"]), "connectors_removed": int(r["TOTAL_CONNECTORS_REMOVED"]),
          "peak_connectors": int(r["PEAK_TOTAL_CONNECTORS"]), "connectors_today": int(r["CONNECTORS_TODAY"])}
         for _, r in q22.sort_values(["REMOVAL_EVENTS", "TOTAL_CONNECTORS_REMOVED"], ascending=False).iterrows()]
        if not q22.empty else []
    )
    q23 = data["q23"]
    o11_infra_removals_multi_o11 = (
        [{"company": r["COMPANY_NAME"], "tenant_id": r["TENANT_ID"], "o11_infras": int(r["NUM_O11_INFRAS"]),
          "n_envs": int(r["N_O11_ENVS"]), "peak_count": int(r["PEAK_CONNECTORS"]),
          "last_count": int(r["LAST_KNOWN_CONNECTORS"]),
          "last_seen": r["LAST_CONNECTOR_TELEMETRY_DAY"].strftime("%Y-%m-%d"),
          "days_silent": int(r["DAYS_SINCE_CONNECTOR_TELEMETRY"])}
         for _, r in q23.sort_values("DAYS_SINCE_CONNECTOR_TELEMETRY", ascending=False).iterrows()]
        if not q23.empty else []
    )

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
            "df_connectors": {"value": df_connectors, "delta": round(conn_delta, 1), "is_pct": True,
                              "direction": "up" if conn_delta >= 0 else "down"},
            "df_tenants": {"value": df_tenants, "delta": round(tenant_delta, 1), "is_pct": True,
                           "direction": "up" if tenant_delta >= 0 else "down"},
            "df_trialing_connectors": {"value": df_trialing_connectors, "delta": round(trialing_conn_delta, 1), "is_pct": True,
                                       "direction": "up" if trialing_conn_delta >= 0 else "down"},
            "df_trialing_tenants": {"value": df_trialing_tenants, "delta": round(trialing_tenant_delta, 1), "is_pct": True,
                                    "direction": "up" if trialing_tenant_delta >= 0 else "down"},
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
            "data_fabric_trend": _chart_data_fabric_trend(data["q7"], data["q12"]),
            "data_fabric_providers": _chart_data_fabric_providers(data["q8"]),
            "deployment_option_bar": _chart_deployment_option_bar(data["q9"]),
            "interop_dev": _chart_interop_customers(data["q13"], "DEV_CUSTOMERS", "#60a5fa"),
            "interop_nonprod": _chart_interop_customers(data["q13"], "NONPROD_CUSTOMERS", "#a78bfa"),
            "interop_prod": _chart_interop_customers(data["q13"], "PROD_CUSTOMERS", "#64748b"),
            "interop_apps_dev": _chart_interop_app_usage(
                data["q14"], "DEV_CUSTOMERS", "DEV_APPS", "DEV_AGENTS"),
            "interop_apps_nonprod": _chart_interop_app_usage(
                data["q14"], "NONPROD_CUSTOMERS", "NONPROD_APPS", "NONPROD_AGENTS"),
            "interop_apps_prod": _chart_interop_app_usage(
                data["q14"], "PROD_CUSTOMERS", "PROD_APPS", "PROD_AGENTS"),
            "connector_changes_monthly": _chart_connector_changes_monthly(data["q15"]),
            "connector_changes_dow": _chart_connector_changes_dow(data["q15"]),
            "connector_changes_by_region": _build_region_variants(data["q16"]),
            "changes_per_tenant_combo": _chart_changes_per_tenant_combo(data["q17"]),
            "change_heatmap": _build_heatmap_variants(data["q18"]),
            "t1a_tam": _chart_funnel_stage(
                data["q26"], "TAM_CUSTOMERS", "O11_ODC_CUSTOMERS",
                "# Multi-Pipeline TAM Customers", "% of O11+ODC Customers", "#60a5fa"),
            "t1b_reach": _chart_funnel_stage(
                data["q27"], "REACH_CUSTOMERS", "TAM_CUSTOMERS",
                "# Reach Customers", "% of TAM", "#a78bfa"),
            "t1c_validated": _chart_funnel_stage(
                data["q28"], "VALIDATED_CUSTOMERS", "REACH_CUSTOMERS",
                "# Validated Customers", "% of Reach", "#34d399"),
            "t1d_depth": _chart_depth_trend(data["q29"]),
            "t2a_tam": _chart_funnel_stage(
                data["q30"], "TAM_CUSTOMERS", "O11_ODC_CUSTOMERS",
                "# Multi-Infra TAM Customers", "% of O11+ODC Customers", "#60a5fa"),
            "t2b_reach": _chart_funnel_stage(
                data["q31"], "REACH_CUSTOMERS", "TAM_CUSTOMERS",
                "# Reach Customers", "% of TAM", "#a78bfa"),
            "t2c_validated": _chart_infra_breakdown(data["q32"]),
            "t2d_depth": _chart_depth_trend(data["q33"]),
            "t2c_validated_unification": _chart_infra_breakdown(data["q34"]),
            "t2d_depth_unification": _chart_depth_trend(data["q35"]),
        },
        "tables": {
            "adoption_trend": table_rows,
            "sku_gap_targeting": sku_gap_targeting,
            "infra_no_telemetry": infra_no_telemetry,
            "freeze_windows": _freeze_windows(data["q18"]),
            "o11_infra_removals": o11_infra_removals,
            "removal_events_by_company": removal_events_by_company,
            "multi_o11_with_df": multi_o11_with_df,
            "removal_events_multi_o11": removal_events_multi_o11,
            "o11_infra_removals_multi_o11": o11_infra_removals_multi_o11,
        },
        "success_metrics": _build_success_metrics_summary(data),
        "sql": _build_sql_map(query_dir),
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
