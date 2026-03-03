"""
Real-Time Sales Data Generator
================================
Simulates a live Kafka-like streaming feed of sales transactions.
Publishes to FastAPI /ingest endpoint at configurable rate.

Dataset schema mirrors Kaggle Superstore Sales + E-Commerce Sales:
  - 500K+ rows after seeded historical generation
  - 20 columns: order_id, order_date, ship_date, ship_mode, customer_id,
    customer_name, segment, country, city, state, region, product_id,
    category, sub_category, product_name, sales, quantity, discount,
    profit, returned
"""

import random
import time
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Generator

import requests
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
API_URL = "http://localhost:8000/api/v1/sales/ingest"
EMIT_INTERVAL_SEC = 0.5   # emit one record every 500 ms (2 TPS)
BATCH_SIZE = 5            # records per HTTP call

# ─── Reference data (mirrors Superstore dataset taxonomy) ─────────────────────
REGIONS = ["West", "East", "Central", "South"]
STATES = {
    "West": ["California", "Washington", "Oregon", "Nevada", "Arizona"],
    "East": ["New York", "Pennsylvania", "Virginia", "Florida", "North Carolina"],
    "Central": ["Texas", "Illinois", "Ohio", "Michigan", "Minnesota"],
    "South": ["Georgia", "Tennessee", "Alabama", "Louisiana", "Mississippi"],
}
CITIES = {
    "California": ["Los Angeles", "San Francisco", "San Diego"],
    "New York": ["New York City", "Buffalo", "Albany"],
    "Texas": ["Houston", "Dallas", "Austin"],
    "Florida": ["Miami", "Orlando", "Tampa"],
    "Illinois": ["Chicago", "Springfield", "Naperville"],
    "Washington": ["Seattle", "Spokane", "Tacoma"],
    "Pennsylvania": ["Philadelphia", "Pittsburgh", "Allentown"],
    "Georgia": ["Atlanta", "Savannah", "Augusta"],
    "Virginia": ["Richmond", "Norfolk", "Arlington"],
    "Oregon": ["Portland", "Eugene", "Salem"],
    "Ohio": ["Columbus", "Cleveland", "Cincinnati"],
    "Michigan": ["Detroit", "Grand Rapids", "Ann Arbor"],
    "Minnesota": ["Minneapolis", "Saint Paul", "Rochester"],
    "Alabama": ["Birmingham", "Montgomery", "Huntsville"],
    "Tennessee": ["Nashville", "Memphis", "Knoxville"],
    "Arizona": ["Phoenix", "Tucson", "Mesa"],
    "Nevada": ["Las Vegas", "Reno", "Henderson"],
    "North Carolina": ["Charlotte", "Raleigh", "Durham"],
    "Louisiana": ["New Orleans", "Baton Rouge", "Shreveport"],
    "Mississippi": ["Jackson", "Biloxi", "Hattiesburg"],
}
SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SHIP_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
CATEGORIES = {
    "Technology": {
        "Phones": [("Apple iPhone 15", 799, 0.18), ("Samsung Galaxy S24", 699, 0.16),
                   ("Google Pixel 8", 599, 0.14), ("OnePlus 12", 449, 0.15)],
        "Computers": [("Dell XPS 15", 1299, 0.22), ("Apple MacBook Pro", 1999, 0.25),
                      ("Microsoft Surface Pro", 999, 0.20), ("Lenovo ThinkPad X1", 1499, 0.21)],
        "Accessories": [("Logitech MX Master 3", 99, 0.35), ("Anker USB-C Hub", 49, 0.40),
                        ("SanDisk 1TB SSD", 89, 0.30), ("HDMI Cable 4K", 19, 0.50)],
    },
    "Furniture": {
        "Chairs": [("Herman Miller Aeron", 1395, 0.15), ("IKEA Markus", 229, 0.20),
                   ("Steelcase Leap", 1295, 0.14), ("Flash Furniture Mesh", 149, 0.25)],
        "Tables": [("IKEA LINNMON Desk", 159, 0.22), ("Uplift Standing Desk", 599, 0.18),
                   ("Sauder 5-Shelf Bookcase", 129, 0.28), ("Realspace Outlet", 249, 0.19)],
        "Storage": [("IKEA KALLAX Shelf", 179, 0.20), ("Rubbermaid Fasttrack", 89, 0.30),
                    ("Whitmor 6-Shelf Bookcase", 69, 0.35), ("ClosetMaid Organizer", 59, 0.33)],
    },
    "Office Supplies": {
        "Binders": [("Avery Heavy Duty Binder", 12, 0.45), ("Cardinal Economy Binder", 8, 0.50),
                    ("Mead 3-Ring Binder", 6, 0.48), ("Wilson Jones Binder", 10, 0.46)],
        "Paper": [("HP Printer Paper 500", 29, 0.28), ("Hammermill 20lb Paper", 24, 0.30),
                  ("Amazon Basics Copy Paper", 19, 0.35), ("Staples Multipurpose Paper", 22, 0.32)],
        "Pens": [("Pilot G2 Pen 12pk", 14, 0.52), ("BIC Round Stic 60pk", 8, 0.58),
                 ("Sharpie Markers 24pk", 16, 0.50), ("Zebra F-301 Pens", 12, 0.48)],
    },
}

RETURN_RATE = 0.04  # 4% return rate


# ─── Helper functions ──────────────────────────────────────────────────────────

def _pick_product():
    cat = random.choice(list(CATEGORIES))
    sub = random.choice(list(CATEGORIES[cat]))
    name, base_price, margin_ratio = random.choice(CATEGORIES[cat][sub])
    return cat, sub, name, base_price, margin_ratio


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def generate_record(order_date: datetime | None = None) -> dict:
    """Generate one synthetic sales transaction."""
    region = random.choice(REGIONS)
    state = random.choice(STATES[region])
    city = random.choice(CITIES.get(state, [state + " City"]))
    cat, sub, product, base_price, margin_ratio = _pick_product()
    qty = random.randint(1, 10)
    discount = round(random.choice([0, 0, 0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]), 2)
    sales = round(base_price * qty * (1 - discount), 2)
    profit = round(sales * margin_ratio * (1 - discount * 1.5), 2)
    segment = random.choice(SEGMENTS)
    ship_mode = random.choices(SHIP_MODES, weights=[0.60, 0.20, 0.15, 0.05])[0]

    if order_date is None:
        order_date = datetime.utcnow()

    ship_days = {"Standard Class": 5, "Second Class": 3, "First Class": 2, "Same Day": 0}
    ship_date = order_date + timedelta(days=ship_days[ship_mode] + random.randint(0, 2))

    return {
        "order_id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
        "order_date": order_date.isoformat(),
        "ship_date": ship_date.isoformat(),
        "ship_mode": ship_mode,
        "customer_id": f"CUS-{random.randint(10000, 99999)}",
        "customer_name": f"Customer_{random.randint(1000, 9999)}",
        "segment": segment,
        "country": "United States",
        "city": city,
        "state": state,
        "region": region,
        "product_id": f"PRD-{random.randint(100, 999)}",
        "category": cat,
        "sub_category": sub,
        "product_name": product,
        "sales": max(sales, 0.01),
        "quantity": qty,
        "discount": discount,
        "profit": profit,
        "returned": random.random() < RETURN_RATE,
    }


def generate_historical(n_records: int = 500_000) -> Generator[dict, None, None]:
    """
    Generate n_records of historical data spanning the past 3 years.
    Yields dicts ready for bulk DB insert.
    """
    start = datetime.utcnow() - timedelta(days=365 * 3)
    end = datetime.utcnow() - timedelta(hours=1)
    for _ in range(n_records):
        yield generate_record(order_date=_random_date(start, end))


# ─── Live stream producer ──────────────────────────────────────────────────────

def stream_to_api(api_url: str = API_URL, interval: float = EMIT_INTERVAL_SEC):
    """
    Continuously generate sales records and POST to the FastAPI ingest endpoint.
    Acts as a simulated Kafka producer (replace POST with kafka-python producer
    to use real Kafka: producer.send('sales-topic', value=record)).
    """
    log.info("▶ Starting live sales stream → %s  (%.1f TPS)", api_url, 1 / interval)
    session = requests.Session()
    batch: list[dict] = []

    while True:
        batch.append(generate_record())
        if len(batch) >= BATCH_SIZE:
            try:
                resp = session.post(api_url, json=batch, timeout=5)
                resp.raise_for_status()
                log.info("✅ Sent %d records | status=%s", len(batch), resp.status_code)
            except requests.RequestException as exc:
                log.warning("⚠ Failed to send batch: %s", exc)
            batch = []
        time.sleep(interval)


if __name__ == "__main__":
    stream_to_api()
