"""
SQLAlchemy database models

This module defines the database schema using SQLAlchemy ORM.
All models include proper indexing, constraints, and relationships
for optimal performance and data integrity.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from sqlalchemy.sql import func
from app.database import Base


class Product(Base):
    """
    Product model representing items in the catalog
    
    This model stores product information with unique SKU constraint
    and supports case-insensitive SKU lookups for deduplication.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, doc="Unique product identifier")
    name = Column(String(255), nullable=False, doc="Product name")
    sku = Column(String(100), unique=True, index=True, nullable=False, doc="Stock Keeping Unit (unique)")
    description = Column(Text, doc="Product description")
    active = Column(Boolean, default=True, nullable=False, doc="Product active status")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), doc="Last update timestamp")
    
    # Create case-insensitive index for SKU lookups
    __table_args__ = (
        Index('ix_products_sku_lower', func.lower(sku)),
    )
    
    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}')>"


class Webhook(Base):
    """
    Webhook model for event notifications
    
    This model stores webhook configurations that are triggered
    when specific events occur in the application.
    """
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True, doc="Unique webhook identifier")
    url = Column(String(500), nullable=False, doc="Webhook endpoint URL")
    event_type = Column(String(50), nullable=False, index=True, doc="Event type that triggers webhook")
    enabled = Column(Boolean, default=True, nullable=False, doc="Webhook enabled status")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Creation timestamp")
    
    def __repr__(self):
        return f"<Webhook(id={self.id}, url='{self.url}', event_type='{self.event_type}')>"