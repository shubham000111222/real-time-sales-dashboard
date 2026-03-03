"""
Page 1: Overview — KPI cards + sales trends
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.api import get_kpis, get_trends, get_export_url
from utils.charts import revenue_trend_chart, matplotlib_orders_hist


def _kpi_card(col, label: str, value: str, delta: str | None = None,
              help_text: str = ""):
    col.metric(label=label, value=value, delta=delta, help=help_text)


def render(days: int = 30, region: str = "All", category: str = "All"):
    st.title("📊 Sales Overview")
    st.caption(f"Last **{days} days** · Region: **{region}** · Category: **{category}**")

    region_param    = None if region    == "All" else region
    category_param  = None if category  == "All" else category

    # ─── KPI Cards ────────────────────────────────────────────────────────────
    with st.spinner("Loading KPIs…"):
        kpis = get_kpis(days=days)

    if "error" in kpis:
        st.error(f"⚠ API error: {kpis['error']}")
        st.info("Make sure the FastAPI backend is running (`uvicorn app.main:app`)")
        # Show demo KPIs
        kpis = {
            "total_revenue": 2_847_320,
            "total_profit": 482_056,
            "total_orders": 14_823,
            "avg_order_value": 192,
            "profit_margin_pct": 16.9,
            "revenue_growth_pct": 8.3,
        }

    cols = st.columns(6)
    _kpi_card(cols[0], "Total Revenue",   f"${kpis['total_revenue']:,.0f}",
              help_text="Gross sales revenue excluding returns")
    _kpi_card(cols[1], "Total Profit",    f"${kpis['total_profit']:,.0f}",
              help_text="Net profit after discounts")
    _kpi_card(cols[2], "Orders",          f"{kpis['total_orders']:,}",
              help_text="Total valid orders in period")
    _kpi_card(cols[3], "Avg Order Value", f"${kpis['avg_order_value']:,.2f}",
              help_text="Revenue ÷ orders")
    _kpi_card(cols[4], "Profit Margin",   f"{kpis['profit_margin_pct']:.1f}%",
              delta=f"{kpis['profit_margin_pct'] - 15:.1f}% vs 15% target")
    _kpi_card(cols[5], "Revenue Growth",  f"{kpis['revenue_growth_pct']:+.1f}%",
              delta=f"{kpis['revenue_growth_pct']:+.1f}% vs prev period",
              help_text="Compared to the equivalent prior period")

    st.divider()

    # ─── Trend controls ───────────────────────────────────────────────────────
    c1, c2 = st.columns([3, 1])
    with c2:
        gran = st.selectbox("Granularity", ["day", "week", "month"], key="gran")

    with st.spinner("Loading trends…"):
        trends = get_trends(days=days, granularity=gran,
                            region=region_param, category=category_param)

    if isinstance(trends, list) and trends:
        fig = revenue_trend_chart(trends)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data for the selected filters. The stream may still be warming up.")

    # ─── Matplotlib histogram ─────────────────────────────────────────────────
    if isinstance(trends, list) and trends:
        st.subheader("Orders per Day Distribution")
        mpl_fig = matplotlib_orders_hist(trends)
        st.pyplot(mpl_fig, use_container_width=True)

    # ─── CSV Download ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("⬇ Export Data")
    csv_url = get_export_url(days=days, region=region_param, category=category_param)
    st.markdown(
        f'<a href="{csv_url}" target="_blank">'
        f'<button style="background:#6366f1;color:white;border:none;padding:8px 20px;'
        f'border-radius:8px;cursor:pointer;font-size:14px;">📥 Download CSV</button></a>',
        unsafe_allow_html=True,
    )
    st.caption(f"Downloads up to 100,000 rows — {csv_url}")
