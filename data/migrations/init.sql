-- ============================================================
-- Real-Time Sales Dashboard — PostgreSQL Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Raw sales transactions ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sales (
    id              BIGSERIAL PRIMARY KEY,
    order_id        VARCHAR(30)     NOT NULL UNIQUE,
    order_date      TIMESTAMPTZ     NOT NULL,
    ship_date       TIMESTAMPTZ,
    ship_mode       VARCHAR(30),
    customer_id     VARCHAR(20),
    customer_name   VARCHAR(100),
    segment         VARCHAR(30),
    country         VARCHAR(60),
    city            VARCHAR(80),
    state           VARCHAR(80),
    region          VARCHAR(30),
    product_id      VARCHAR(20),
    category        VARCHAR(50),
    sub_category    VARCHAR(50),
    product_name    VARCHAR(150),
    sales           NUMERIC(12, 2)  NOT NULL DEFAULT 0,
    quantity        INTEGER         NOT NULL DEFAULT 1,
    discount        NUMERIC(5, 2)   NOT NULL DEFAULT 0,
    profit          NUMERIC(12, 2)  NOT NULL DEFAULT 0,
    returned        BOOLEAN         NOT NULL DEFAULT FALSE,
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ─── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sales_order_date   ON sales (order_date DESC);
CREATE INDEX IF NOT EXISTS idx_sales_region       ON sales (region);
CREATE INDEX IF NOT EXISTS idx_sales_category     ON sales (category);
CREATE INDEX IF NOT EXISTS idx_sales_product_name ON sales (product_name);
CREATE INDEX IF NOT EXISTS idx_sales_ingested_at  ON sales (ingested_at DESC);

-- ─── Materialised view: daily KPIs (refreshed every minute via backend) ────────
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_kpis AS
SELECT
    DATE_TRUNC('day', order_date)::DATE                         AS sale_date,
    region,
    category,
    SUM(sales)                                                   AS total_revenue,
    SUM(profit)                                                   AS total_profit,
    COUNT(*)                                                      AS order_count,
    SUM(quantity)                                                 AS units_sold,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 2)         AS profit_margin_pct,
    COUNT(DISTINCT customer_id)                                   AS unique_customers
FROM sales
GROUP BY 1, 2, 3
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_kpis_pk
    ON daily_kpis (sale_date, region, category);

-- ─── Refresh helper function (called from FastAPI background task) ─────────────
CREATE OR REPLACE FUNCTION refresh_daily_kpis()
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_kpis;
END;
$$;
