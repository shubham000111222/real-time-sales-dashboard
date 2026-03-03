"""
Page 4: Forecast — Prophet / ARIMA revenue forecast
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.api import get_forecast, get_trends
from utils.charts import forecast_chart


def render():
    st.title("🔮 Revenue Forecast")
    st.caption("Powered by Facebook Prophet and ARIMA")

    c1, c2, c3 = st.columns(3)
    with c1:
        model = st.selectbox("Model", ["prophet", "arima"], format_func=str.upper)
    with c2:
        horizon = st.slider("Forecast horizon (days)", 7, 90, 30)
    with c3:
        hist_days = st.slider("Historical data (days)", 30, 365, 180)

    with st.spinner(f"Running {model.upper()} forecast…"):
        fc_result = get_forecast(model=model, horizon=horizon)
        hist_data = get_trends(days=hist_days, granularity="day")

    if isinstance(fc_result, dict) and "error" in fc_result:
        st.error(f"⚠ API error: {fc_result['error']}")
        st.info("Check that the FastAPI backend is running and has enough historical data.")
        return

    fc_list  = fc_result.get("forecast", []) if isinstance(fc_result, dict) else []
    hist_list = hist_data if isinstance(hist_data, list) else []

    # ─── Forecast chart ───────────────────────────────────────────────────────
    fig = forecast_chart(fc_list, hist_list)
    st.plotly_chart(fig, use_container_width=True)

    # ─── Forecast summary cards ───────────────────────────────────────────────
    if fc_list:
        df = pd.DataFrame(fc_list)
        total_fc  = df["yhat"].sum()
        avg_daily = df["yhat"].mean()
        peak_row  = df.loc[df["yhat"].idxmax()]
        lo_total  = df["yhat_lower"].sum()
        hi_total  = df["yhat_upper"].sum()

        st.divider()
        st.subheader(f"{model.upper()} Forecast Summary — Next {horizon} Days")
        cols = st.columns(4)
        cols[0].metric("Total Forecast Revenue", f"${total_fc:,.0f}",
                       help="Sum of yhat over the forecast horizon")
        cols[1].metric("Avg Daily Revenue",      f"${avg_daily:,.0f}")
        cols[2].metric("Peak Day",
                       f"${peak_row['yhat']:,.0f}",
                       delta=peak_row["date"])
        cols[3].metric("90% CI Range",
                       f"${lo_total:,.0f} – ${hi_total:,.0f}",
                       help="Lower and upper bounds of the 90% confidence interval")

        # ─── Forecast data table ──────────────────────────────────────────────
        st.divider()
        st.subheader("Forecast Data Table")
        display = df.copy()
        for col in ["yhat", "yhat_lower", "yhat_upper"]:
            display[col] = display[col].apply(lambda x: f"${x:,.2f}")
        display = display.rename(columns={
            "date": "Date",
            "yhat": "Forecast ($)",
            "yhat_lower": "Lower Bound ($)",
            "yhat_upper": "Upper Bound ($)",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

        # ─── CSV download ─────────────────────────────────────────────────────
        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇ Download Forecast CSV",
            data=csv,
            file_name=f"{model}_forecast_{horizon}d.csv",
            mime="text/csv",
        )

    # ─── Model info ───────────────────────────────────────────────────────────
    with st.expander("ℹ️ Model Details"):
        if model == "prophet":
            st.markdown("""
**Facebook Prophet**
- Handles daily/weekly/yearly seasonality automatically
- Robust to missing data and outliers
- Parameters: `changepoint_prior_scale=0.1`, `interval_width=0.90`
- Trained on your historical daily revenue data
            """)
        else:
            st.markdown("""
**ARIMA (Auto-Regressive Integrated Moving Average)**
- Order: `(5, 1, 2)` — 5 AR lags, 1 differencing step, 2 MA terms
- 90% confidence interval from `get_forecast(alpha=0.10)`
- Falls back to linear trend if convergence fails
- Trained on your historical daily revenue data
            """)
