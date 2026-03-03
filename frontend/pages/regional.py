"""
Page 2: Regional — region-wise revenue, profit & heatmap
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.api import get_regions, get_trends
from utils.charts import region_bar_chart, region_pie_chart, seaborn_heatmap


def render(days: int = 90):
    st.title("🗺 Regional Performance")
    st.caption(f"Last **{days} days**")

    with st.spinner("Loading regional data…"):
        regions = get_regions(days=days)

    if isinstance(regions, dict) and "error" in regions:
        st.error(f"⚠ API error: {regions['error']}")
        # Demo fallback
        regions = [
            {"region": "West",    "total_revenue": 892000, "total_profit": 152000, "order_count": 4200, "profit_margin": 17.0},
            {"region": "East",    "total_revenue": 741000, "total_profit": 118000, "order_count": 3500, "profit_margin": 15.9},
            {"region": "Central", "total_revenue": 612000, "total_profit":  89000, "order_count": 2900, "profit_margin": 14.5},
            {"region": "South",   "total_revenue": 425000, "total_profit":  61000, "order_count": 2100, "profit_margin": 14.4},
        ]

    df = pd.DataFrame(regions) if isinstance(regions, list) else pd.DataFrame()

    # ─── Summary table ────────────────────────────────────────────────────────
    if not df.empty:
        st.subheader("Region Scorecard")
        display = df.copy()
        display["total_revenue"] = display["total_revenue"].apply(lambda x: f"${x:,.0f}")
        display["total_profit"]  = display["total_profit"].apply(lambda x: f"${x:,.0f}")
        display["profit_margin"] = display["profit_margin"].apply(lambda x: f"{x:.1f}%")
        display = display.rename(columns={
            "region": "Region", "total_revenue": "Revenue",
            "total_profit": "Profit", "order_count": "Orders",
            "profit_margin": "Margin",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # ─── Charts ───────────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(region_bar_chart(regions), use_container_width=True)
    with c2:
        st.plotly_chart(region_pie_chart(regions), use_container_width=True)

    # ─── Seaborn heatmap — region × category ──────────────────────────────────
    st.subheader("Revenue Heatmap (Region × Category)")
    st.caption("Seaborn heatmap — values in $K")

    # Fetch per-region+category breakdown
    all_trends: list[dict] = []
    for region_name in ["West", "East", "Central", "South"]:
        for cat in ["Technology", "Furniture", "Office Supplies"]:
            row_data = get_trends(days=days, granularity="month",
                                  region=region_name, category=cat)
            if isinstance(row_data, list) and row_data:
                total_rev = sum(r["revenue"] for r in row_data)
                all_trends.append({"region": region_name, "category": cat,
                                   "total_revenue": total_rev})

    if all_trends:
        fig = seaborn_heatmap(all_trends)
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Not enough data for heatmap — stream still warming up.")

    # ─── Region drilldown ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Region Drilldown")
    selected_region = st.selectbox("Select region", ["West", "East", "Central", "South"])
    with st.spinner(f"Loading {selected_region} trend…"):
        region_trends = get_trends(days=days, granularity="week", region=selected_region)

    if isinstance(region_trends, list) and region_trends:
        from utils.charts import revenue_trend_chart
        st.plotly_chart(revenue_trend_chart(region_trends), use_container_width=True)
    else:
        st.info(f"No data for {selected_region} in this period.")
