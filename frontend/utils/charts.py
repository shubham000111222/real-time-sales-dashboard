"""
Reusable chart builders — Plotly, Matplotlib, Seaborn
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns

# ─── Plotly charts ────────────────────────────────────────────────────────────

PALETTE = px.colors.qualitative.Vivid
TEMPLATE = "plotly_dark"


def revenue_trend_chart(data: list[dict]) -> go.Figure:
    """Dual-axis line chart — revenue (bar) + profit (line)."""
    if not data:
        return _empty_fig("No trend data")

    df = pd.DataFrame(data)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date"], y=df["revenue"],
        name="Revenue", marker_color="rgba(99,102,241,0.8)",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["profit"],
        name="Profit", mode="lines+markers",
        line=dict(color="#10b981", width=2),
        yaxis="y2",
    ))
    fig.update_layout(
        template=TEMPLATE,
        title="Revenue & Profit Trend",
        yaxis=dict(title="Revenue ($)", gridcolor="rgba(255,255,255,0.05)"),
        yaxis2=dict(title="Profit ($)", overlaying="y", side="right",
                    gridcolor="rgba(255,255,255,0.05)"),
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def region_bar_chart(data: list[dict]) -> go.Figure:
    """Grouped horizontal bar: revenue vs profit by region."""
    if not data:
        return _empty_fig("No regional data")

    df = pd.DataFrame(data).sort_values("total_revenue", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["region"], x=df["total_revenue"],
        name="Revenue", orientation="h",
        marker_color="rgba(99,102,241,0.85)",
    ))
    fig.add_trace(go.Bar(
        y=df["region"], x=df["total_profit"],
        name="Profit", orientation="h",
        marker_color="rgba(16,185,129,0.85)",
    ))
    fig.update_layout(
        template=TEMPLATE,
        barmode="group",
        title="Region-wise Revenue & Profit",
        xaxis_title="Amount ($)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def region_pie_chart(data: list[dict]) -> go.Figure:
    """Donut chart — revenue share by region."""
    if not data:
        return _empty_fig("No regional data")

    df = pd.DataFrame(data)
    fig = px.pie(
        df, values="total_revenue", names="region",
        hole=0.45, color_discrete_sequence=PALETTE,
        title="Revenue Share by Region",
    )
    fig.update_layout(template=TEMPLATE, paper_bgcolor="rgba(0,0,0,0)")
    return fig


def top_products_chart(data: list[dict], top_n: int = 10) -> go.Figure:
    """Horizontal bar chart — top products by revenue."""
    if not data:
        return _empty_fig("No product data")

    df = pd.DataFrame(data).head(top_n).sort_values("total_revenue", ascending=True)
    fig = px.bar(
        df, y="product_name", x="total_revenue",
        orientation="h", color="category",
        color_discrete_sequence=PALETTE,
        title=f"Top {top_n} Products by Revenue",
        labels={"total_revenue": "Revenue ($)", "product_name": "Product"},
        text="total_revenue",
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig.update_layout(
        template=TEMPLATE,
        showlegend=True,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def product_scatter(data: list[dict]) -> go.Figure:
    """Scatter: profit vs revenue, sized by units sold."""
    if not data:
        return _empty_fig("No product data")

    df = pd.DataFrame(data)
    fig = px.scatter(
        df, x="total_revenue", y="total_profit",
        size="units_sold", color="category",
        hover_name="product_name",
        color_discrete_sequence=PALETTE,
        size_max=40,
        title="Profit vs Revenue (bubble = units sold)",
        labels={"total_revenue": "Revenue ($)", "total_profit": "Profit ($)"},
    )
    fig.update_layout(
        template=TEMPLATE,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def forecast_chart(fc_data: list[dict], hist_data: list[dict] | None = None) -> go.Figure:
    """Forecast ribbon chart with confidence interval."""
    if not fc_data:
        return _empty_fig("No forecast data available")

    df = pd.DataFrame(fc_data)
    fig = go.Figure()

    # Historical actuals
    if hist_data:
        hdf = pd.DataFrame(hist_data).tail(60)
        fig.add_trace(go.Scatter(
            x=hdf["date"], y=hdf["revenue"],
            name="Historical", mode="lines",
            line=dict(color="rgba(139,92,246,0.8)", width=2),
        ))

    # CI ribbon
    fig.add_trace(go.Scatter(
        x=list(df["date"]) + list(reversed(df["date"])),
        y=list(df["yhat_upper"]) + list(reversed(df["yhat_lower"])),
        fill="toself",
        fillcolor="rgba(99,102,241,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        name="90% CI",
    ))

    # Forecast line
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["yhat"],
        name="Forecast", mode="lines+markers",
        line=dict(color="rgba(99,102,241,1)", width=2, dash="dash"),
        marker=dict(size=5),
    ))

    fig.update_layout(
        template=TEMPLATE,
        title="Revenue Forecast",
        xaxis_title="Date",
        yaxis_title="Revenue ($)",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─── Seaborn / Matplotlib charts (returned as bytes for st.image) ─────────────

def seaborn_heatmap(data: list[dict]) -> plt.Figure:
    """Seaborn heatmap: average daily revenue by region × category."""
    if not data:
        fig, ax = plt.subplots(); ax.text(0.5, 0.5, "No data"); return fig

    df = pd.DataFrame(data)
    if "region" not in df.columns or "category" not in df.columns:
        fig, ax = plt.subplots(); ax.text(0.5, 0.5, "No data"); return fig

    pivot = df.pivot_table(
        index="region", columns="category",
        values="total_revenue", aggfunc="sum", fill_value=0,
    )

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")

    sns.heatmap(
        pivot / 1000, annot=True, fmt=".0f", cmap="RdYlGn",
        linewidths=0.5, ax=ax, cbar_kws={"label": "Revenue ($K)"},
        annot_kws={"color": "white"},
    )
    ax.set_title("Revenue Heatmap (Region × Category, $K)", color="white", pad=12)
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    plt.tight_layout()
    return fig


def matplotlib_orders_hist(data: list[dict]) -> plt.Figure:
    """Matplotlib histogram — orders per day distribution."""
    if not data:
        fig, ax = plt.subplots(); ax.text(0.5, 0.5, "No data"); return fig

    df = pd.DataFrame(data)
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")

    ax.hist(df["orders"], bins=20, color="#6366f1", edgecolor="white", alpha=0.85)
    ax.set_title("Orders Per Day Distribution", color="white", pad=10)
    ax.set_xlabel("Orders", color="white")
    ax.set_ylabel("Frequency", color="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("white")
    plt.tight_layout()
    return fig


# ─── Helper ───────────────────────────────────────────────────────────────────

def _empty_fig(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
    fig.update_layout(template=TEMPLATE, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", xaxis_visible=False, yaxis_visible=False)
    return fig
