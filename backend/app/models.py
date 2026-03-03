"""
SQLAlchemy ORM models
"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Numeric,
    Integer, String, func,
)
from .database import Base


class Sale(Base):
    __tablename__ = "sales"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id      = Column(String(30), nullable=False, unique=True, index=True)
    order_date    = Column(DateTime(timezone=True), nullable=False, index=True)
    ship_date     = Column(DateTime(timezone=True))
    ship_mode     = Column(String(30))
    customer_id   = Column(String(20))
    customer_name = Column(String(100))
    segment       = Column(String(30))
    country       = Column(String(60))
    city          = Column(String(80))
    state         = Column(String(80))
    region        = Column(String(30), index=True)
    product_id    = Column(String(20))
    category      = Column(String(50), index=True)
    sub_category  = Column(String(50))
    product_name  = Column(String(150))
    sales         = Column(Numeric(12, 2), nullable=False, default=0)
    quantity      = Column(Integer, nullable=False, default=1)
    discount      = Column(Numeric(5, 2), nullable=False, default=0)
    profit        = Column(Numeric(12, 2), nullable=False, default=0)
    returned      = Column(Boolean, nullable=False, default=False)
    ingested_at   = Column(DateTime(timezone=True), server_default=func.now())
