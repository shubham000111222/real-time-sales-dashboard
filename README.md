# Real-Time Sales Analytics Dashboard

A production-grade, end-to-end data engineering project featuring a live sales data
stream, a FastAPI analytics backend, a PostgreSQL data warehouse, and an interactive
Streamlit dashboard with Plotly, Matplotlib, Seaborn, Prophet, and ARIMA forecasting.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Compose Stack                         │
│                                                                       │
│  ┌──────────────┐    HTTP POST    ┌──────────────┐                   │
│  │   Producer   │ ─────────────▶ │   FastAPI    │                   │
│  │ (Simulated   │   /ingest       │   Backend    │                   │
│  │  Kafka feed) │                 │  (port 8000) │                   │
│  └──────────────┘                 └──────┬───────┘                   │
│                                          │ SQLAlchemy (asyncpg)      │
│                                          ▼                            │
│                                   ┌──────────────┐                   │
│                                   │  PostgreSQL  │                   │
│                                   │   sales_db   │                   │
│                                   │  (port 5432) │                   │
│                                   └──────┬───────┘                   │
│                                          │ REST API calls            │
│                                          ▼                            │
│                                   ┌──────────────┐                   │
│                                   │  Streamlit   │                   │
│                                   │  Dashboard   │                   │
│                                   │  (port 8501) │                   │
│                                   └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

To use real **Kafka**, replace the HTTP producer with `kafka-python` and uncomment the
Kafka services in `docker-compose.yml`.

---

## Dataset

| Property       | Details                                              |
|----------------|------------------------------------------------------|
| **Source**     | Synthetic (mirrors Kaggle Superstore + E-Commerce)   |
| **Size**       | 500K rows historical + continuous live stream        |
| **Columns**    | 20 (see table below)                                 |
| **Time span**  | 3 years historical + real-time                       |

### Schema (20 columns)

| Column          | Type     | Description                              |
|-----------------|----------|------------------------------------------|
| `order_id`      | VARCHAR  | Unique order identifier                  |
| `order_date`    | TIMESTAMPTZ | Time of purchase                      |
| `ship_date`     | TIMESTAMPTZ | Shipping date                         |
| `ship_mode`     | VARCHAR  | Standard / Second / First / Same Day     |
| `customer_id`   | VARCHAR  | Customer key                             |
| `customer_name` | VARCHAR  | Anonymised customer name                 |
| `segment`       | VARCHAR  | Consumer / Corporate / Home Office       |
| `country`       | VARCHAR  | Country (United States)                  |
| `city`          | VARCHAR  | City                                     |
| `state`         | VARCHAR  | US state                                 |
| `region`        | VARCHAR  | West / East / Central / South            |
| `product_id`    | VARCHAR  | Product key                              |
| `category`      | VARCHAR  | Technology / Furniture / Office Supplies |
| `sub_category`  | VARCHAR  | e.g. Phones, Chairs, Binders             |
| `product_name`  | VARCHAR  | Specific product                         |
| `sales`         | NUMERIC  | Gross revenue ($)                        |
| `quantity`      | INTEGER  | Units sold                               |
| `discount`      | NUMERIC  | Discount fraction (0–1)                  |
| `profit`        | NUMERIC  | Net profit ($)                           |
| `returned`      | BOOLEAN  | Whether order was returned               |

### Derived KPIs

- **Revenue Growth %** — current period vs prior period of equal length
- **Profit Margin %** — `profit / revenue × 100`
- **Average Order Value** — `total_revenue / order_count`

---

## Project Structure

```
real-time-sales-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, lifespan, CORS
│   │   ├── database.py           # Async SQLAlchemy engine
│   │   ├── models.py             # ORM model (Sale table)
│   │   ├── schemas.py            # Pydantic schemas
│   │   └── routers/
│   │       ├── sales.py          # Ingest, KPIs, trends, regions, products, CSV export
│   │       └── forecast.py       # Prophet & ARIMA forecast endpoints
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app.py                    # Main Streamlit entrypoint + sidebar nav
│   ├── pages/
│   │   ├── overview.py           # KPI cards + revenue/profit trend + histogram
│   │   ├── regional.py           # Region scorecard + bar + pie + Seaborn heatmap
│   │   ├── products.py           # Top products bar + scatter + category breakdown
│   │   └── forecast.py           # Prophet/ARIMA forecast ribbon chart + table
│   ├── utils/
│   │   ├── api.py                # HTTP client wrapper for FastAPI
│   │   └── charts.py             # Plotly, Matplotlib, Seaborn chart builders
│   ├── requirements.txt
│   └── Dockerfile
│
├── data/
│   ├── generator/
│   │   ├── sales_generator.py    # Simulated live data stream producer
│   │   └── Dockerfile
│   └── migrations/
│       └── init.sql              # DB schema + materialised view + indexes
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
# 1. Clone & enter the project
git clone https://github.com/shubham000111222/real-time-sales-dashboard
cd real-time-sales-dashboard

# 2. Copy env file
cp .env.example .env

# 3. Spin up the full stack
docker compose up --build

# 4. Open the dashboard
open http://localhost:8501

# 5. View the API docs
open http://localhost:8000/docs
```

All 4 services start together:
- **PostgreSQL** — port 5432 (schema applied automatically from `init.sql`)
- **FastAPI backend** — port 8000 (auto-creates tables on startup)
- **Streamlit dashboard** — port 8501
- **Producer** — begins streaming 2 transactions/second immediately

---

### Option B — Local Development

#### Prerequisites
- Python 3.11+
- PostgreSQL 15+

```bash
# 1. Create the database
psql -U postgres -c "CREATE USER sales_user WITH PASSWORD 'sales_pass';"
psql -U postgres -c "CREATE DATABASE sales_db OWNER sales_user;"
psql -U sales_user -d sales_db -f data/migrations/init.sql

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py

# 4. Producer (new terminal)
cd data/generator
python sales_generator.py
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint                  | Description                          |
|--------|---------------------------|--------------------------------------|
| POST   | `/sales/ingest`           | Bulk upsert sales records            |
| GET    | `/sales/kpis`             | KPI cards (revenue, profit, growth)  |
| GET    | `/sales/trends`           | Time-series trend data               |
| GET    | `/sales/regions`          | Region-wise revenue & profit         |
| GET    | `/sales/top-products`     | Top products by revenue              |
| GET    | `/sales/export`           | Download CSV (up to 100K rows)       |
| GET    | `/forecast/prophet`       | Prophet 30-day revenue forecast      |
| GET    | `/forecast/arima`         | ARIMA 30-day revenue forecast        |
| GET    | `/health`                 | Service health check                 |

Full interactive docs: `http://localhost:8000/docs`

---

## Dashboard Pages

| Page          | Charts & Features                                                    |
|---------------|----------------------------------------------------------------------|
| 📊 Overview   | 6 KPI metric cards, Revenue+Profit dual-axis chart (Plotly), Orders histogram (Matplotlib), CSV export button |
| 🗺 Regional   | Region scorecard table, Grouped bar chart, Donut chart, Seaborn revenue heatmap (Region × Category), Region drilldown |
| 🏆 Products   | Top-N horizontal bar chart, Profit vs Revenue scatter (bubble = units), Category bar chart, Detail table |
| 🔮 Forecast   | Forecast ribbon chart with 90% CI (Prophet or ARIMA), Summary KPI cards, Forecast data table, CSV download |

### Global sidebar controls
- **Lookback window**: 7 / 14 / 30 / 60 / 90 / 180 / 365 days
- **Region filter**: All / West / East / Central / South
- **Category filter**: All / Technology / Furniture / Office Supplies
- **Auto-refresh**: Page reloads every 30 seconds for live data

---

## Forecasting Models

### Facebook Prophet
- Decomposes trend + yearly + weekly seasonality
- `changepoint_prior_scale=0.1` (conservative)
- 90% uncertainty interval
- Gracefully falls back to ARIMA if not installed

### ARIMA(5,1,2)
- 5 autoregressive lags, 1 differencing step, 2 moving-average terms
- 90% confidence interval via `statsmodels`
- Falls back to linear extrapolation if convergence fails

---

## Deployment on Cloud

### AWS (EC2 + RDS)

```bash
# 1. Launch EC2 instance (t3.medium, Ubuntu 22.04)
# 2. Install Docker
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu

# 3. Create RDS PostgreSQL instance
#    Note the endpoint, e.g. sales-db.abc123.us-east-1.rds.amazonaws.com

# 4. Update .env with RDS endpoint
DATABASE_URL=postgresql+asyncpg://sales_user:sales_pass@<RDS_ENDPOINT>:5432/sales_db

# 5. Open Security Group: ports 8000, 8501 (and 5432 only from EC2)

# 6. Clone & run
git clone https://github.com/shubham000111222/real-time-sales-dashboard
cd real-time-sales-dashboard && cp .env.example .env   # edit with RDS creds
docker compose up -d --build

# Dashboard: http://<EC2_PUBLIC_IP>:8501
# API docs:  http://<EC2_PUBLIC_IP>:8000/docs
```

### Google Cloud Run (serverless)

```bash
# Build and push images
gcloud builds submit --tag gcr.io/$PROJECT_ID/sales-backend ./backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/sales-dashboard ./frontend

# Deploy backend
gcloud run deploy sales-backend \
  --image gcr.io/$PROJECT_ID/sales-backend \
  --platform managed --region us-central1 \
  --set-env-vars DATABASE_URL=$DATABASE_URL \
  --allow-unauthenticated

# Deploy frontend
gcloud run deploy sales-dashboard \
  --image gcr.io/$PROJECT_ID/sales-dashboard \
  --platform managed --region us-central1 \
  --set-env-vars API_BASE_URL=https://<backend-url>/api/v1 \
  --allow-unauthenticated
```

### Render (free tier)

1. Push repo to GitHub
2. Create a new **Web Service** for `backend/` — build command: `pip install -r requirements.txt`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Create a new **Web Service** for `frontend/` — start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Set `DATABASE_URL` and `API_BASE_URL` as environment variables in the Render dashboard
5. Use Render's managed PostgreSQL for the database

---

## Visualisation Libraries

| Library     | Used For                                                  |
|-------------|-----------------------------------------------------------|
| **Plotly**  | Revenue trends, region bars, donut charts, forecast ribbon, scatter |
| **Seaborn** | Region × Category heatmap                                 |
| **Matplotlib** | Orders-per-day histogram                               |

---

## Extending with Real Kafka

1. Uncomment the `zookeeper` and `kafka` services in `docker-compose.yml`
2. Replace the HTTP POST in `sales_generator.py` with:

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=["kafka:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)
producer.send("sales-topic", value=generate_record())
```

3. Add a Kafka consumer service that reads from `sales-topic` and calls the DB ingest logic

---

## Tech Stack

| Layer         | Technology                              |
|---------------|-----------------------------------------|
| Stream        | Python generator (Kafka-ready)          |
| Backend       | FastAPI + SQLAlchemy (async) + asyncpg  |
| Database      | PostgreSQL 16                           |
| Forecasting   | Prophet, ARIMA (statsmodels)            |
| Frontend      | Streamlit                               |
| Visualisation | Plotly, Matplotlib, Seaborn             |
| Container     | Docker + Docker Compose                 |
| Cloud         | AWS EC2/RDS · GCP Cloud Run · Render    |

---

## Author

**Shubham Kumar** — Data Scientist & ML Engineer  
📍 Delhi, India  
🔗 [LinkedIn](https://linkedin.com/in/shubham-kumar-288b7437b) · [GitHub](https://github.com/shubham000111222)
