"""
Pydantic schemas for request / response validation
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ─── Ingest ───────────────────────────────────────────────────────────────────

class SaleIn(BaseModel):
    order_id:      str
    order_date:    datetime
    ship_date:     Optional[datetime] = None
    ship_mode:     Optional[str] = None
    customer_id:   Optional[str] = None
    customer_name: Optional[str] = None
    segment:       Optional[str] = None
    country:       Optional[str] = None
    city:          Optional[str] = None
    state:         Optional[str] = None
    region:        Optional[str] = None
    product_id:    Optional[str] = None
    category:      Optional[str] = None
    sub_category:  Optional[str] = None
    product_name:  Optional[str] = None
    sales:         float = Field(ge=0)
    quantity:      int   = Field(ge=1)
    discount:      float = Field(ge=0, le=1)
    profit:        float
    returned:      bool  = False

    @field_validator("sales", "profit")
    @classmethod
    def round_currency(cls, v: float) -> float:
        return round(v, 2)


class SaleOut(SaleIn):
    id:          int
    ingested_at: datetime

    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    inserted: int
    skipped:  int


# ─── Analytics ────────────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date:    str
    revenue: float
    profit:  float
    orders:  int


class RegionKPI(BaseModel):
    region:         str
    total_revenue:  float
    total_profit:   float
    order_count:    int
    profit_margin:  float


class TopProduct(BaseModel):
    product_name:  str
    category:      str
    total_revenue: float
    units_sold:    int
    total_profit:  float


class KPICard(BaseModel):
    total_revenue:      float
    total_profit:       float
    total_orders:       int
    avg_order_value:    float
    profit_margin_pct:  float
    revenue_growth_pct: float   # vs previous period


# ─── Forecast ─────────────────────────────────────────────────────────────────

class ForecastPoint(BaseModel):
    date:       str
    yhat:       float
    yhat_lower: float
    yhat_upper: float


class ForecastResponse(BaseModel):
    model:     str
    horizon:   int
    forecast:  List[ForecastPoint]
