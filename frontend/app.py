"""
Real-Time Sales Analytics Dashboard — Streamlit
================================================
Multi-page Streamlit app with live data refresh.

Pages:
  1. 📊 Overview      — KPI cards + revenue / profit trends
  2. 🗺  Regional      — Region-wise performance & drilldown
  3. 🏆 Top Products  — Best-selling products by revenue / profit
  4. 🔮 Forecast      — Prophet / ARIMA 30-day revenue forecast
"""

import streamlit as st

st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Main navigation ──────────────────────────────────────────────────────────
PAGES = {
    "📊 Overview":     "pages/overview",
    "🗺 Regional":     "pages/regional",
    "🏆 Top Products": "pages/products",
    "🔮 Forecast":     "pages/forecast",
}

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("Sales Dashboard")
    st.caption("Real-Time Analytics")
    st.divider()

    page = st.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

    st.divider()
    st.markdown("**Filters**")
    days = st.selectbox(
        "Lookback window",
        [7, 14, 30, 60, 90, 180, 365],
        index=4,
        key="global_days",
    )
    region_filter = st.selectbox(
        "Region",
        ["All", "West", "East", "Central", "South"],
        key="global_region",
    )
    category_filter = st.selectbox(
        "Category",
        ["All", "Technology", "Furniture", "Office Supplies"],
        key="global_category",
    )

    st.divider()
    refresh = st.button("🔄 Refresh Now")
    auto = st.checkbox("Auto-refresh (30s)", value=True)
    if auto:
        st.caption("Page refreshes every 30 seconds")

# Auto-refresh via meta tag injection
if auto:
    st.markdown(
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True,
    )

# ─── Route to page ────────────────────────────────────────────────────────────
if page == "📊 Overview":
    from pages.overview import render
    render(days=days, region=region_filter, category=category_filter)

elif page == "🗺 Regional":
    from pages.regional import render
    render(days=days)

elif page == "🏆 Top Products":
    from pages.products import render
    render(days=days, category=category_filter)

elif page == "🔮 Forecast":
    from pages.forecast import render
    render()
