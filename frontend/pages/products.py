"""
Page 3: Top Products — best sellers by revenue, profit & units
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.api import get_top_products
from utils.charts import top_products_chart, product_scatter


def render(days: int = 90, category: str = "All"):
    st.title("🏆 Top Products")
    st.caption(f"Last **{days} days** · Category: **{category}**")

    cat_param = None if category == "All" else category

    c1, c2 = st.columns([3, 1])
    with c2:
        top_n = st.slider("Show top N", min_value=5, max_value=25, value=10)

    with st.spinner("Loading products…"):
        products = get_top_products(days=days, limit=top_n * 2, category=cat_param)

    if isinstance(products, dict) and "error" in products:
        st.error(f"⚠ API error: {products['error']}")
        products = []   # will show empty charts

    # ─── Bar chart ────────────────────────────────────────────────────────────
    st.plotly_chart(top_products_chart(products, top_n=top_n), use_container_width=True)

    st.divider()

    # ─── Scatter: profit vs revenue ───────────────────────────────────────────
    st.subheader("Profit vs Revenue (all products)")
    st.plotly_chart(product_scatter(products), use_container_width=True)

    st.divider()

    # ─── Data table ───────────────────────────────────────────────────────────
    st.subheader("Product Detail Table")
    if products:
        df = pd.DataFrame(products).head(top_n)
        df = df.rename(columns={
            "product_name": "Product",
            "category": "Category",
            "total_revenue": "Revenue ($)",
            "units_sold": "Units Sold",
            "total_profit": "Profit ($)",
        })
        df["Revenue ($)"] = df["Revenue ($)"].apply(lambda x: f"${x:,.2f}")
        df["Profit ($)"]  = df["Profit ($)"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ─── Category breakdown ───────────────────────────────────────────────
        st.divider()
        st.subheader("Revenue by Category")
        raw_df = pd.DataFrame(products)
        if "category" in raw_df.columns:
            cat_df = (
                raw_df.groupby("category")["total_revenue"]
                .sum().reset_index()
                .sort_values("total_revenue", ascending=False)
            )
            import plotly.express as px
            fig = px.bar(
                cat_df,
                x="category", y="total_revenue",
                color="category",
                labels={"total_revenue": "Revenue ($)", "category": "Category"},
                template="plotly_dark",
                title="Total Revenue by Category",
                color_discrete_sequence=px.colors.qualitative.Vivid,
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No product data yet. Ensure the data stream is running.")
