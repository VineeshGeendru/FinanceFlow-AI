"""
app.py — Streamlit dashboard for FinanceFlow-AI.

WHAT IT DOES (in finance terms):
  This is the web application a finance analyst opens in a browser.
  It runs the full pipeline (load → engine → commentary → report) and
  displays the results as interactive charts, KPI cards, anomaly alerts,
  and a downloadable Excel report.

  Sections:
    1. Sidebar      — settings, thresholds, download button
    2. KPI Cards    — Revenue, OpEx, Operating Income, Material Variance count
    3. Waterfall    — Operating Income bridge: Budget → variances → Actual
    4. Anomalies    — Spike, trend, and missing-driver alerts
    5. Heatmap      — Net impact by line item and month
    6. Trend        — Budget vs Actual line chart with line item selector
    7. YTD Table    — Full YTD variance detail with commentary

RUN WITH:
  streamlit run app.py
"""

import os
import sys
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main   import run_pipeline
from src        import config


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinanceFlow-AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal CSS — tighten metric cards and remove top padding ─────────────────
st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #f8f9fc;
    border: 1px solid #e0e4ed;
    border-radius: 10px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { font-size: 0.82rem; color: #555; }
[data-testid="stMetricValue"] { font-size: 1.45rem; font-weight: 700; }
.section-header {
    font-size: 1.05rem; font-weight: 600;
    color: #1F3864; margin: 0.8rem 0 0.4rem 0;
    border-left: 4px solid #1F3864; padding-left: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Colors ────────────────────────────────────────────────────────────────────
C_DARK_BLUE = "#1F3864"
C_RED       = "#E53E3E"
C_GREEN     = "#38A169"
C_NEUTRAL   = "#718096"


# ── Cached pipeline runner ────────────────────────────────────────────────────
# @st.cache_data means: if the arguments haven't changed, return the stored
# result instead of re-running. This is what makes the trend explorer dropdown
# feel instant — the 10-second pipeline only runs once per session.
@st.cache_data(show_spinner=False)
def _cached_pipeline(budget_path, actuals_path, drivers_path,
                     mat_dollars, mat_pct):
    return run_pipeline(
        budget_path  = budget_path,
        actuals_path = actuals_path,
        drivers_path = drivers_path,
        mat_dollars  = mat_dollars,
        mat_pct      = mat_pct,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def _build_sidebar() -> dict:
    """Render sidebar controls. Returns a dict of current settings."""
    with st.sidebar:
        st.markdown(f"### FinanceFlow-AI")
        st.markdown("FP&A Variance Analysis")
        st.divider()

        st.markdown("**Materiality Thresholds**")
        mat_dollars = st.number_input(
            "Absolute dollar threshold ($)",
            min_value=0, max_value=1_000_000,
            value=int(config.MATERIALITY_THRESHOLD_DOLLARS),
            step=5_000,
            help="A variance is material if it clears EITHER threshold.",
        )
        mat_pct = st.number_input(
            "Percent of budget threshold (%)",
            min_value=0.0, max_value=100.0,
            value=float(config.MATERIALITY_THRESHOLD_PERCENT),
            step=0.5,
            help="5.0 means 5% of the budget amount.",
        )

        st.divider()

        # ── FILE PATHS (Phase 8 will replace these with upload widgets) ───────
        st.markdown("**Data Files**")
        budget_path  = st.text_input("Budget file",  config.BUDGET_PATH)
        actuals_path = st.text_input("Actuals file", config.ACTUALS_PATH)
        drivers_path = st.text_input("Drivers file", config.DRIVERS_PATH)

        st.divider()
        run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

    return {
        "budget_path":   budget_path,
        "actuals_path":  actuals_path,
        "drivers_path":  drivers_path,
        "mat_dollars":   mat_dollars,
        "mat_pct":       mat_pct,
        "run_clicked":   run_btn,
    }


# ══════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════
def _show_kpi_cards(results: dict):
    pl      = results["results"]["pl_summary"]
    monthly = results["results"]["monthly"]

    def pl_row(name):
        rows = pl[pl["Line"] == name]
        return rows.iloc[0] if not rows.empty else None

    rev  = pl_row("Revenue")
    opex = pl_row("Opex")
    oi   = pl_row("Operating Income")
    mat_count = int(monthly["Material"].sum())
    anom_count = len(results["results"]["anomalies"])

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if rev is not None:
            st.metric(
                label="YTD Revenue",
                value=f"${rev['Actual']:,.0f}",
                delta=f"${rev['Variance $']:+,.0f} vs budget",
                delta_color="normal",
                help="Positive delta = favorable (above budget)"
            )

    with c2:
        if opex is not None:
            st.metric(
                label="YTD Operating Expenses",
                value=f"${opex['Actual']:,.0f}",
                delta=f"${opex['Variance $']:+,.0f} vs budget",
                delta_color="inverse",  # for costs: positive = bad (over budget)
                help="Negative delta = favorable (under budget)"
            )

    with c3:
        if oi is not None:
            st.metric(
                label="YTD Operating Income",
                value=f"${oi['Actual']:,.0f}",
                delta=f"${oi['Variance $']:+,.0f} vs budget",
                delta_color="normal",
                help="Positive delta = favorable (above budget)"
            )

    with c4:
        st.metric(
            label="Material Variances",
            value=f"{mat_count}",
            delta=f"{anom_count} anomalies detected",
            delta_color="off",
            help="Variances clearing $" + f"{config.MATERIALITY_THRESHOLD_DOLLARS:,.0f}"
                 + f" or {config.MATERIALITY_THRESHOLD_PERCENT:.0f}% threshold"
        )


# ══════════════════════════════════════════════════════════════════════════════
# WATERFALL CHART
# ══════════════════════════════════════════════════════════════════════════════
def _show_waterfall(results: dict):
    st.markdown('<p class="section-header">Operating Income Bridge: Budget to Actual</p>',
                unsafe_allow_html=True)

    pl = results["results"]["pl_summary"]

    def pl_val(name, col):
        rows = pl[pl["Line"] == name]
        return rows.iloc[0][col] if not rows.empty else 0

    budget_oi  = pl_val("Operating Income", "Budget")
    rev_impact = pl_val("Revenue",          "Net Impact $")
    cogs_impact= pl_val("COGS",             "Net Impact $")
    opex_impact= pl_val("Opex",             "Net Impact $")
    actual_oi  = pl_val("Operating Income", "Actual")

    labels   = ["Budget OI", "Revenue", "COGS", "Opex", "Actual OI"]
    measures = ["absolute",  "relative","relative","relative","total"]
    values   = [budget_oi,  rev_impact, cogs_impact, opex_impact, actual_oi]
    texts    = [f"${v:,.0f}" for v in values]

    fig = go.Figure(go.Waterfall(
        orientation = "v",
        measure     = measures,
        x           = labels,
        y           = values,
        text        = texts,
        textposition= "outside",
        textfont    = {"size": 12},
        decreasing  = {"marker": {"color": C_RED,      "line": {"color": C_RED,      "width": 1}}},
        increasing  = {"marker": {"color": C_GREEN,    "line": {"color": C_GREEN,    "width": 1}}},
        totals      = {"marker": {"color": C_DARK_BLUE,"line": {"color": C_DARK_BLUE,"width": 1}}},
        connector   = {"line": {"color": "#999", "dash": "dot", "width": 1}},
    ))

    fig.update_layout(
        height        = 400,
        margin        = {"t": 30, "b": 20, "l": 60, "r": 20},
        plot_bgcolor  = "white",
        paper_bgcolor = "white",
        yaxis         = {"tickformat": "$,.0f", "gridcolor": "#eee", "title": ""},
        xaxis         = {"tickfont": {"size": 12}},
        showlegend    = False,
    )

    # Zero line
    fig.add_hline(y=0, line_color="#aaa", line_width=1)

    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANOMALY ALERTS
# ══════════════════════════════════════════════════════════════════════════════
def _show_anomalies(results: dict):
    anomalies = results["results"]["anomalies"]

    if anomalies.empty:
        st.info("No anomalies detected.")
        return

    st.markdown('<p class="section-header">Anomaly Detection</p>',
                unsafe_allow_html=True)

    type_config = {
        "Spike": {
            "icon": "spike",
            "color": "error",
            "label": "Spikes — single-month variance unusually large vs this line's own history",
        },
        "Consecutive Deterioration": {
            "icon": "trend",
            "color": "warning",
            "label": "Consecutive Deterioration — net impact on OI worsening 3+ months in a row",
        },
        "Missing Driver": {
            "icon": "missing",
            "color": "error",
            "label": "Missing Drivers — material variances with no budget owner explanation on file",
        },
    }

    for anom_type, cfg in type_config.items():
        subset = anomalies[anomalies["Type"] == anom_type]
        if subset.empty:
            continue

        with st.expander(f"{cfg['label']}  ({len(subset)} flagged)", expanded=(anom_type == "Missing Driver")):
            for _, row in subset.iterrows():
                if cfg["color"] == "error":
                    st.error(row["Description"])
                else:
                    st.warning(row["Description"])


# ══════════════════════════════════════════════════════════════════════════════
# VARIANCE HEATMAP
# ══════════════════════════════════════════════════════════════════════════════
def _show_heatmap(results: dict):
    st.markdown('<p class="section-header">Net Impact on Operating Income — Line Item x Month</p>',
                unsafe_allow_html=True)

    monthly = results["results"]["monthly"]

    pivot = monthly.pivot_table(
        index   = "Line Item",
        columns = "Month",
        values  = "Net Impact $",
        aggfunc = "sum",
        fill_value = 0,
    )

    # Text overlay: formatted dollar amounts with sign
    text_vals = [[f"${v:+,.0f}" for v in row] for row in pivot.values]

    fig = go.Figure(go.Heatmap(
        z             = pivot.values,
        x             = list(pivot.columns),
        y             = list(pivot.index),
        colorscale    = [
            [0.0,  C_RED],
            [0.45, "#FFCCCC"],
            [0.5,  "#F7F7F7"],
            [0.55, "#CCEEDD"],
            [1.0,  C_GREEN],
        ],
        zmid          = 0,
        text          = text_vals,
        texttemplate  = "%{text}",
        textfont      = {"size": 11},
        hovertemplate = "<b>%{y}</b><br>%{x}<br>Net Impact: %{text}<extra></extra>",
        showscale     = True,
        colorbar      = {"title": "Net Impact $", "tickformat": "$,.0f"},
    ))

    fig.update_layout(
        height        = 420,
        margin        = {"t": 20, "b": 20, "l": 180, "r": 20},
        plot_bgcolor  = "white",
        paper_bgcolor = "white",
        xaxis         = {"side": "top", "tickfont": {"size": 11}},
        yaxis         = {"tickfont": {"size": 11}, "autorange": "reversed"},
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Green = favorable impact on operating income.  "
        "Red = unfavorable.  "
        "Revenue: above budget is green.  "
        "Costs: below budget is green."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TREND EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
def _show_trend_explorer(results: dict):
    st.markdown('<p class="section-header">Budget vs Actual — Trend Explorer</p>',
                unsafe_allow_html=True)

    monthly    = results["results"]["monthly"]
    line_items = sorted(monthly["Line Item"].unique().tolist())

    col_sel, col_dept = st.columns([3, 2])
    with col_sel:
        selected = st.selectbox("Select line item", line_items,
                                index=line_items.index("Subscription Revenue")
                                if "Subscription Revenue" in line_items else 0)
    with col_dept:
        # Filter by department when multiple depts share the same line item
        depts_for_item = monthly[monthly["Line Item"] == selected]["Department"].unique()
        selected_dept  = st.selectbox("Department", ["All"] + sorted(depts_for_item.tolist()))

    filtered = monthly[monthly["Line Item"] == selected]
    if selected_dept != "All":
        filtered = filtered[filtered["Department"] == selected_dept]

    if filtered.empty:
        st.warning("No data for this selection.")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x       = filtered["Month"],
        y       = filtered["Amount_budget"],
        name    = "Budget",
        mode    = "lines+markers",
        line    = {"dash": "dash", "color": C_DARK_BLUE, "width": 2},
        marker  = {"size": 7},
    ))

    fig.add_trace(go.Scatter(
        x       = filtered["Month"],
        y       = filtered["Amount_actual"],
        name    = "Actual",
        mode    = "lines+markers",
        line    = {"color": "#2196F3", "width": 2.5},
        marker  = {"size": 8},
    ))

    # Shade the gap between Budget and Actual
    fig.add_trace(go.Scatter(
        x       = list(filtered["Month"]) + list(filtered["Month"])[::-1],
        y       = list(filtered["Amount_actual"]) + list(filtered["Amount_budget"])[::-1],
        fill    = "toself",
        fillcolor = "rgba(231,76,60,0.08)",
        line    = {"color": "rgba(0,0,0,0)"},
        showlegend = False,
        hoverinfo  = "skip",
    ))

    # Mark material variance months with a vertical line
    material_months = filtered[filtered["Material"]]["Month"].tolist()
    for m in material_months:
        fig.add_vline(x=m, line_dash="dot", line_color=C_RED,
                      line_width=1, opacity=0.6)

    category = filtered["Category"].iloc[0] if not filtered.empty else ""
    fig.update_layout(
        height        = 380,
        margin        = {"t": 30, "b": 20, "l": 60, "r": 20},
        plot_bgcolor  = "white",
        paper_bgcolor = "white",
        yaxis         = {"tickformat": "$,.0f", "gridcolor": "#eee", "title": ""},
        xaxis         = {"title": "", "gridcolor": "#eee"},
        legend        = {"orientation": "h", "y": -0.12},
        title         = f"{selected}  |  Category: {category}  "
                        f"{'(red dashes = material variance month)' if material_months else ''}",
        title_font    = {"size": 13},
    )

    st.plotly_chart(fig, use_container_width=True)

    # Mini variance table below the chart
    display_cols = ["Month", "Department", "Amount_budget",
                    "Amount_actual", "Variance $", "Variance %", "F/U", "Material"]
    mini = filtered[display_cols].copy()
    mini["Amount_budget"] = mini["Amount_budget"].map("${:,.0f}".format)
    mini["Amount_actual"] = mini["Amount_actual"].map("${:,.0f}".format)
    mini["Variance $"]    = mini["Variance $"].map("${:+,.0f}".format)
    mini["Variance %"]    = mini["Variance %"].map("{:+.1f}%".format)
    mini["Material"]      = mini["Material"].map({True: "Yes", False: ""})
    st.dataframe(mini, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# YTD VARIANCE TABLE
# ══════════════════════════════════════════════════════════════════════════════
def _show_ytd_table(results: dict):
    st.markdown('<p class="section-header">YTD Variance Detail</p>',
                unsafe_allow_html=True)

    ytd = results["results"]["ytd"].copy()
    commentary = results["commentary"]["line_commentary"]

    # Add commentary: match on Department + Line Item (most recent month's note)
    def get_comment(dept, line):
        matches = {k: v for k, v in commentary.items()
                   if k[1] == dept and k[2] == line}
        if not matches:
            return ""
        return matches[max(matches.keys(), key=lambda k: k[0])]

    ytd["Commentary"] = ytd.apply(
        lambda r: get_comment(r["Department"], r["Line Item"]), axis=1
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        dept_options = ["All"] + sorted(ytd["Department"].unique())
        dept_filter  = st.selectbox("Department", dept_options, key="ytd_dept")
    with col_f2:
        cat_options  = ["All"] + sorted(ytd["Category"].unique())
        cat_filter   = st.selectbox("Category", cat_options, key="ytd_cat")
    with col_f3:
        mat_filter   = st.selectbox("Show", ["All", "Material only", "Non-material only"],
                                    key="ytd_mat")

    filtered = ytd.copy()
    if dept_filter != "All":
        filtered = filtered[filtered["Department"] == dept_filter]
    if cat_filter != "All":
        filtered = filtered[filtered["Category"] == cat_filter]
    if mat_filter == "Material only":
        filtered = filtered[filtered["YTD_Material"]]
    elif mat_filter == "Non-material only":
        filtered = filtered[~filtered["YTD_Material"]]

    # ── Format for display ────────────────────────────────────────────────────
    display = filtered[[
        "Department", "Line Item", "Category",
        "YTD_Budget", "YTD_Actual", "YTD_Var", "YTD_Var_Pct",
        "YTD_FU", "YTD_Material", "Commentary"
    ]].copy()

    display.columns = [
        "Department", "Line Item", "Category",
        "YTD Budget", "YTD Actual", "Variance $", "Variance %",
        "F/U", "Material", "Commentary"
    ]

    display["YTD Budget"] = display["YTD Budget"].map("${:,.0f}".format)
    display["YTD Actual"] = display["YTD Actual"].map("${:,.0f}".format)
    display["Variance $"] = display["Variance $"].map("${:+,.0f}".format)
    display["Variance %"] = display["Variance %"].map("{:+.1f}%".format)
    display["Material"]   = display["Material"].map({True: "Yes", False: ""})

    def _row_color(row):
        if row["Material"] == "Yes":
            if row["F/U"] == "Favorable":
                return ["background-color: #C6EFCE"] * len(row)
            else:
                return ["background-color: #FFD7D7"] * len(row)
        return [""] * len(row)

    styled = display.style.apply(_row_color, axis=1)

    st.dataframe(styled, use_container_width=True, hide_index=True,
                 column_config={"Commentary": st.column_config.TextColumn(width="large")})

    st.caption(f"Showing {len(display)} of {len(ytd)} line items. "
               f"Green = material favorable.  Red = material unfavorable.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.title("FinanceFlow-AI")
    st.markdown("FP&A variance analysis — budget vs. actual with AI commentary")
    st.divider()

    settings = _build_sidebar()

    # Clear cache and rerun if user clicked "Run Analysis"
    if settings["run_clicked"]:
        st.cache_data.clear()
        st.rerun()

    # ── Run pipeline (cached) ─────────────────────────────────────────────────
    with st.spinner("Running variance analysis..."):
        try:
            output = _cached_pipeline(
                budget_path  = settings["budget_path"],
                actuals_path = settings["actuals_path"],
                drivers_path = settings["drivers_path"],
                mat_dollars  = settings["mat_dollars"],
                mat_pct      = settings["mat_pct"],
            )
        except (FileNotFoundError, ValueError) as e:
            st.error(f"Pipeline error: {e}")
            st.info("Check that your file paths in the sidebar are correct.")
            return

    # ── Sidebar: download button (needs pipeline to have run first) ───────────
    with st.sidebar:
        if os.path.exists(output["report_path"]):
            with open(output["report_path"], "rb") as f:
                st.download_button(
                    label             = "Download Excel Report",
                    data              = f,
                    file_name         = "FinanceFlow_Variance_Report.xlsx",
                    mime              = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width = True,
                )
        ai_mode = output["commentary"]["ai_used"]
        st.caption(f"Commentary: {'Claude AI' if ai_mode else 'Template fallback'}")

    # ── 1. KPI Cards ──────────────────────────────────────────────────────────
    _show_kpi_cards(output)

    st.divider()

    # ── 2. Waterfall ──────────────────────────────────────────────────────────
    _show_waterfall(output)

    # ── 3. Anomaly Alerts ─────────────────────────────────────────────────────
    _show_anomalies(output)

    st.divider()

    # ── 4. Heatmap ────────────────────────────────────────────────────────────
    _show_heatmap(output)

    st.divider()

    # ── 5. Trend Explorer ─────────────────────────────────────────────────────
    _show_trend_explorer(output)

    st.divider()

    # ── 6. YTD Table ──────────────────────────────────────────────────────────
    _show_ytd_table(output)


main()
