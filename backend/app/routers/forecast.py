"""
Forecast router — ARIMA + Prophet revenue forecasting
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import ForecastResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["Forecast"])


async def _fetch_daily_revenue(db: AsyncSession, days_back: int = 365) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days_back)
    q = await db.execute(
        text("""
            SELECT
                DATE_TRUNC('day', order_date)::DATE::TEXT AS ds,
                SUM(sales)                                AS y
            FROM sales
            WHERE order_date >= :since AND returned = FALSE
            GROUP BY 1
            ORDER BY 1
        """),
        {"since": since},
    )
    return [{"ds": r.ds, "y": float(r.y)} for r in q.fetchall()]


@router.get("/prophet", response_model=ForecastResponse)
async def forecast_prophet(
    horizon: int = Query(30, ge=7, le=180, description="Days to forecast"),
    days_back: int = Query(180, ge=30, le=730),
    db: AsyncSession = Depends(get_db),
):
    """Revenue forecast using Facebook Prophet."""
    try:
        from prophet import Prophet  # type: ignore
        import pandas as pd

        data = await _fetch_daily_revenue(db, days_back)
        if len(data) < 14:
            return ForecastResponse(model="prophet", horizon=horizon, forecast=[])

        df = pd.DataFrame(data)
        df["ds"] = pd.to_datetime(df["ds"])

        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.1,
            interval_width=0.90,
        )
        m.fit(df)

        future = m.make_future_dataframe(periods=horizon, freq="D")
        fc = m.predict(future).tail(horizon)

        return ForecastResponse(
            model="prophet",
            horizon=horizon,
            forecast=[
                {
                    "date": str(r["ds"].date()),
                    "yhat": round(max(r["yhat"], 0), 2),
                    "yhat_lower": round(max(r["yhat_lower"], 0), 2),
                    "yhat_upper": round(max(r["yhat_upper"], 0), 2),
                }
                for _, r in fc.iterrows()
            ],
        )
    except ImportError:
        log.warning("prophet not installed — falling back to ARIMA")
        return await forecast_arima(horizon=horizon, days_back=days_back, db=db)


@router.get("/arima", response_model=ForecastResponse)
async def forecast_arima(
    horizon: int = Query(30, ge=7, le=180),
    days_back: int = Query(180, ge=30, le=730),
    db: AsyncSession = Depends(get_db),
):
    """Revenue forecast using ARIMA(p,d,q) with auto-order selection."""
    import pandas as pd
    import numpy as np

    data = await _fetch_daily_revenue(db, days_back)
    if len(data) < 14:
        return ForecastResponse(model="arima", horizon=horizon, forecast=[])

    df = pd.DataFrame(data)
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.set_index("ds").resample("D").sum().fillna(method="ffill")  # type: ignore
    series = df["y"].values

    try:
        from statsmodels.tsa.arima.model import ARIMA  # type: ignore
        from statsmodels.tools.sm_exceptions import ConvergenceWarning  # type: ignore
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            model = ARIMA(series, order=(5, 1, 2))
            fit = model.fit()
            pred = fit.get_forecast(steps=horizon)
            means  = pred.predicted_mean
            conf   = pred.conf_int(alpha=0.10)  # 90% CI
    except Exception as exc:
        log.warning("ARIMA failed (%s) — using linear trend fallback", exc)
        slope = (series[-1] - series[0]) / max(len(series), 1)
        means = [series[-1] + slope * i for i in range(1, horizon + 1)]
        std   = float(np.std(series)) * 0.5
        conf  = [[m - std, m + std] for m in means]

    last_date = df.index[-1]
    results = []
    for i in range(horizon):
        dt   = (last_date + pd.Timedelta(days=i + 1)).date()
        yhat = max(float(means[i] if hasattr(means, "__iter__") else means), 0)
        lo   = max(float(conf[i][0] if hasattr(conf[0], "__iter__") else conf[i]), 0)
        hi   = max(float(conf[i][1] if hasattr(conf[0], "__iter__") else conf[i] * 1.2), 0)
        results.append({"date": str(dt), "yhat": round(yhat, 2),
                        "yhat_lower": round(lo, 2), "yhat_upper": round(hi, 2)})

    return ForecastResponse(model="arima", horizon=horizon, forecast=results)
