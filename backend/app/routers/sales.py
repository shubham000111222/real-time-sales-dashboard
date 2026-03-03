"""
Sales router — ingest + analytics endpoints
"""
from __future__ import annotations

import io
import csv
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..database import get_db
from ..models import Sale
from ..schemas import (
    SaleIn, IngestResponse, TrendPoint, RegionKPI, TopProduct, KPICard,
)

router = APIRouter(prefix="/sales", tags=["Sales"])


# ─── Ingest ───────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest_sales(records: List[SaleIn], db: AsyncSession = Depends(get_db)):
    """
    Bulk-upsert sales records. Simulates Kafka consumer writing to PostgreSQL.
    Duplicate order_ids are silently skipped (ON CONFLICT DO NOTHING).
    """
    if not records:
        return IngestResponse(inserted=0, skipped=0)

    rows = [r.model_dump() for r in records]
    stmt = insert(Sale).values(rows).on_conflict_do_nothing(index_elements=["order_id"])
    result = await db.execute(stmt)
    await db.commit()

    inserted = result.rowcount
    skipped = len(records) - inserted
    return IngestResponse(inserted=inserted, skipped=skipped)


# ─── KPI Cards ────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=KPICard)
async def get_kpis(
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    prev  = since - timedelta(days=days)

    async def _period_totals(start: datetime, end: datetime):
        q = await db.execute(
            text("""
                SELECT
                    COALESCE(SUM(sales), 0)          AS revenue,
                    COALESCE(SUM(profit), 0)         AS profit,
                    COUNT(*)                          AS orders
                FROM sales
                WHERE order_date BETWEEN :start AND :end
                  AND returned = FALSE
            """),
            {"start": start, "end": end},
        )
        return q.one()

    cur  = await _period_totals(since, datetime.utcnow())
    prev_row = await _period_totals(prev, since)

    revenue = float(cur.revenue)
    profit  = float(cur.profit)
    orders  = int(cur.orders)
    prev_rev = float(prev_row.revenue)

    growth = ((revenue - prev_rev) / prev_rev * 100) if prev_rev else 0.0
    aov    = revenue / orders if orders else 0.0
    margin = (profit / revenue * 100) if revenue else 0.0

    return KPICard(
        total_revenue=round(revenue, 2),
        total_profit=round(profit, 2),
        total_orders=orders,
        avg_order_value=round(aov, 2),
        profit_margin_pct=round(margin, 2),
        revenue_growth_pct=round(growth, 2),
    )


# ─── Sales Trends ─────────────────────────────────────────────────────────────

@router.get("/trends", response_model=List[TrendPoint])
async def get_trends(
    days: int = Query(90, ge=7, le=730),
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    trunc = f"'{granularity}'"
    where_clauses = ["order_date >= :since", "returned = FALSE"]
    params: dict = {"since": since}

    if region:
        where_clauses.append("region = :region")
        params["region"] = region
    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    where = " AND ".join(where_clauses)
    q = await db.execute(
        text(f"""
            SELECT
                DATE_TRUNC({trunc}, order_date)::DATE::TEXT AS date,
                SUM(sales)                                   AS revenue,
                SUM(profit)                                  AS profit,
                COUNT(*)                                     AS orders
            FROM sales
            WHERE {where}
            GROUP BY 1
            ORDER BY 1
        """),
        params,
    )
    return [
        TrendPoint(date=r.date, revenue=round(float(r.revenue), 2),
                   profit=round(float(r.profit), 2), orders=int(r.orders))
        for r in q.fetchall()
    ]


# ─── Regional KPIs ────────────────────────────────────────────────────────────

@router.get("/regions", response_model=List[RegionKPI])
async def get_regions(
    days: int = Query(90, ge=7, le=730),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    q = await db.execute(
        text("""
            SELECT
                region,
                SUM(sales)   AS total_revenue,
                SUM(profit)  AS total_profit,
                COUNT(*)     AS order_count
            FROM sales
            WHERE order_date >= :since AND returned = FALSE
            GROUP BY region
            ORDER BY total_revenue DESC
        """),
        {"since": since},
    )
    return [
        RegionKPI(
            region=r.region,
            total_revenue=round(float(r.total_revenue), 2),
            total_profit=round(float(r.total_profit), 2),
            order_count=int(r.order_count),
            profit_margin=round(float(r.total_profit) / float(r.total_revenue) * 100, 2)
            if r.total_revenue else 0.0,
        )
        for r in q.fetchall()
    ]


# ─── Top Products ─────────────────────────────────────────────────────────────

@router.get("/top-products", response_model=List[TopProduct])
async def get_top_products(
    days: int = Query(90, ge=7, le=730),
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    extra = "AND category = :category" if category else ""
    params: dict = {"since": since, "limit": limit}
    if category:
        params["category"] = category

    q = await db.execute(
        text(f"""
            SELECT
                product_name,
                category,
                SUM(sales)    AS total_revenue,
                SUM(quantity) AS units_sold,
                SUM(profit)   AS total_profit
            FROM sales
            WHERE order_date >= :since AND returned = FALSE {extra}
            GROUP BY product_name, category
            ORDER BY total_revenue DESC
            LIMIT :limit
        """),
        params,
    )
    return [
        TopProduct(
            product_name=r.product_name,
            category=r.category,
            total_revenue=round(float(r.total_revenue), 2),
            units_sold=int(r.units_sold),
            total_profit=round(float(r.total_profit), 2),
        )
        for r in q.fetchall()
    ]


# ─── CSV Export ───────────────────────────────────────────────────────────────

@router.get("/export")
async def export_csv(
    days: int = Query(90, ge=1, le=730),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Download filtered sales data as CSV."""
    since = datetime.utcnow() - timedelta(days=days)
    where = ["order_date >= :since"]
    params: dict = {"since": since}
    if region:
        where.append("region = :region"); params["region"] = region
    if category:
        where.append("category = :category"); params["category"] = category

    q = await db.execute(
        text(f"SELECT * FROM sales WHERE {' AND '.join(where)} ORDER BY order_date DESC LIMIT 100000"),
        params,
    )
    rows = q.fetchall()
    cols = q.keys()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    writer.writerows(rows)
    output.seek(0)

    filename = f"sales_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
