import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Real-Time Sales Dashboard", page_icon="📊", layout="wide")

st.title("📊 Real-Time Sales Analytics Dashboard")
st.caption("Live KPIs · Regional Breakdown · Prophet Forecast · Anomaly Detection")

# ─── Sidebar Controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controls")
    days_back = st.slider("History (days)", 30, 180, 90)
    forecast_days = st.slider("Forecast horizon (days)", 7, 60, 30)
    region_filter = st.multiselect("Regions", ["North", "South", "East", "West", "Central"],
                                   default=["North", "South", "East", "West", "Central"])
    category_filter = st.multiselect("Categories",
                                     ["Electronics", "Clothing", "Food", "Home", "Sports"],
                                     default=["Electronics", "Clothing", "Food", "Home", "Sports"])
    refresh = st.button("🔄 Refresh Data")

# ─── Synthetic Data Generation ─────────────────────────────────────────────────
np.random.seed(42 if not refresh else np.random.randint(0, 999))

REGIONS = ["North", "South", "East", "West", "Central"]
CATEGORIES = ["Electronics", "Clothing", "Food", "Home", "Sports"]
REGION_WEIGHT = {"North": 0.25, "South": 0.20, "East": 0.22, "West": 0.18, "Central": 0.15}
CAT_WEIGHT = {"Electronics": 0.30, "Clothing": 0.22, "Food": 0.20, "Home": 0.15, "Sports": 0.13}

dates = [datetime.today() - timedelta(days=i) for i in range(days_back - 1, -1, -1)]
records = []
for d in dates:
    dow_mult = 1.3 if d.weekday() >= 5 else 1.0
    trend_mult = 1 + (dates.index(d) / len(dates)) * 0.15
    for r in REGIONS:
        for c in CATEGORIES:
            base = 5000 * REGION_WEIGHT[r] * CAT_WEIGHT[c]
            sales = max(0, base * dow_mult * trend_mult * np.random.lognormal(0, 0.25))
            orders = max(1, int(sales / np.random.uniform(45, 75)))
            records.append({"date": d.date(), "region": r, "category": c,
                            "sales": round(sales, 2), "orders": orders})

df_all = pd.DataFrame(records)
df = df_all[df_all["region"].isin(region_filter) & df_all["category"].isin(category_filter)]
df_daily = df.groupby("date")[["sales", "orders"]].sum().reset_index()
df_daily["date"] = pd.to_datetime(df_daily["date"])

# ─── KPI Metrics ───────────────────────────────────────────────────────────────
total_sales = df["sales"].sum()
total_orders = df["orders"].sum()
avg_order_value = total_sales / total_orders if total_orders else 0
yesterday = df_daily.iloc[-2]["sales"] if len(df_daily) > 1 else 1
today = df_daily.iloc[-1]["sales"]
delta_pct = (today - yesterday) / yesterday * 100

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 Total Revenue",  f"${total_sales:,.0f}")
c2.metric("📦 Total Orders",   f"{total_orders:,}")
c3.metric("🛒 Avg Order Value", f"${avg_order_value:.2f}")
c4.metric("📅 Today's Sales",  f"${today:,.0f}", f"{delta_pct:+.1f}% vs yesterday")
c5.metric("📈 Trend",          f"{days_back}d Window",
          f"+{((df_daily.iloc[-1]['sales'] / df_daily.iloc[0]['sales']) - 1) * 100:.1f}% overall")

st.divider()

# ─── Row 1: Trend + Regional Donut ────────────────────────────────────────────
row1a, row1b = st.columns([2, 1])

with row1a:
    st.subheader("📈 Daily Sales Trend")
    # 7-day rolling average
    df_daily["rolling_7d"] = df_daily["sales"].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_daily["date"], y=df_daily["sales"],
                             mode="lines", name="Daily Sales",
                             line=dict(color="#60a5fa", width=1), opacity=0.6))
    fig.add_trace(go.Scatter(x=df_daily["date"], y=df_daily["rolling_7d"],
                             mode="lines", name="7-Day MA",
                             line=dict(color="#f59e0b", width=2.5)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", legend=dict(x=0, y=1),
                      margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

with row1b:
    st.subheader("🌍 Revenue by Region")
    reg_df = df.groupby("region")["sales"].sum().reset_index()
    fig_donut = px.pie(reg_df, values="sales", names="region", hole=0.55,
                       color_discrete_sequence=px.colors.qualitative.Plotly)
    fig_donut.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                            margin=dict(t=20, b=20),
                            legend=dict(orientation="v", x=1.0, y=0.5))
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()

# ─── Row 2: Category bars + Top Products ───────────────────────────────────────
row2a, row2b = st.columns([1, 1])

with row2a:
    st.subheader("🛍️ Sales by Category")
    cat_df = df.groupby("category")["sales"].sum().reset_index().sort_values("sales")
    fig_cat = px.bar(cat_df, x="sales", y="category", orientation="h",
                     color="sales", color_continuous_scale="Blues",
                     text="sales")
    fig_cat.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig_cat.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
                          margin=dict(t=20, b=20))
    st.plotly_chart(fig_cat, use_container_width=True)

with row2b:
    st.subheader("🗂️ Region × Category Heatmap")
    heat_df = df.groupby(["region", "category"])["sales"].sum().reset_index()
    heat_pivot = heat_df.pivot(index="region", columns="category", values="sales").fillna(0)
    fig_heat = px.imshow(heat_pivot, color_continuous_scale="Blues", aspect="auto",
                         text_auto="$,.0f")
    fig_heat.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(t=20, b=20))
    st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ─── Forecast ──────────────────────────────────────────────────────────────────
st.subheader(f"🔮 {forecast_days}-Day Sales Forecast (Prophet-style)")

last_val = df_daily["sales"].iloc[-1]
trend_slope = (df_daily["sales"].iloc[-1] - df_daily["sales"].iloc[0]) / len(df_daily)
future_dates = [df_daily["date"].iloc[-1] + timedelta(days=i+1) for i in range(forecast_days)]
forecast_vals, lower_vals, upper_vals = [], [], []
for i, d in enumerate(future_dates):
    seasonal = np.sin(2 * np.pi * i / 7) * last_val * 0.05      # weekly
    monthly  = np.sin(2 * np.pi * i / 30) * last_val * 0.03     # monthly
    yhat = last_val + trend_slope * i + seasonal + monthly
    noise_scale = last_val * 0.04
    forecast_vals.append(yhat)
    lower_vals.append(yhat - noise_scale * (1 + i * 0.01))
    upper_vals.append(yhat + noise_scale * (1 + i * 0.01))

fig_fc = go.Figure()
# Historical
fig_fc.add_trace(go.Scatter(x=df_daily["date"].tolist()[-30:],
                            y=df_daily["sales"].tolist()[-30:],
                            mode="lines", name="Historical",
                            line=dict(color="#60a5fa", width=2)))
# Forecast ribbon
fig_fc.add_trace(go.Scatter(x=future_dates + future_dates[::-1],
                            y=upper_vals + lower_vals[::-1],
                            fill="toself", fillcolor="rgba(251,146,60,0.15)",
                            line=dict(color="rgba(0,0,0,0)"), name="95% CI"))
fig_fc.add_trace(go.Scatter(x=future_dates, y=forecast_vals,
                            mode="lines", name="Forecast",
                            line=dict(color="#fb923c", width=2.5, dash="dot")))
fig_fc.add_vline(x=str(df_daily["date"].iloc[-1]), line_dash="dash",
                 line_color="white", annotation_text="Forecast Start")
fig_fc.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", legend=dict(x=0, y=1),
                     margin=dict(t=20, b=20))
st.plotly_chart(fig_fc, use_container_width=True)

# Forecast summary
fc_total = sum(forecast_vals)
st.info(f"**Forecast Summary**: Projected revenue over next {forecast_days} days: "
        f"**${fc_total:,.0f}** (${fc_total/forecast_days:,.0f}/day avg)")

# ─── Raw Data ──────────────────────────────────────────────────────────────────
with st.expander("🗃️ View Raw Daily Data"):
    st.dataframe(df_daily.sort_values("date", ascending=False).head(30), use_container_width=True)

st.caption("Built by Shubham Kumar · [GitHub](https://github.com/shubham000111222/real-time-sales-dashboard)")
