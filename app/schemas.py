"""
Pydantic schemas for request/response validation

This module defines the data models used for API request validation
and response serialization. All schemas include proper documentation
and validation rules.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductResponse(BaseModel):
    """
    Product response schema for API endpoints
    
    Used for serializing product data in API responses
    """
    id: int = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Product SKU (Stock Keeping Unit)")
    description: Optional[str] = Field(None, description="Product description")
    active: bool = Field(True, description="Product active status")
    created_at: Optional[str] = Field(None, description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Wireless Headphones",
                "sku": "WH-001",
                "description": "High-quality wireless headphones",
                "active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": None
            }
        }


class WebhookResponse(BaseModel):
    """
    Webhook response schema for API endpoints
    
    Used for serializing webhook data in API responses
    """
    id: int = Field(..., description="Unique webhook identifier")
    url: str = Field(..., description="Webhook URL endpoint")
    event_type: str = Field(..., description="Event type that triggers the webhook")
    enabled: bool = Field(True, description="Webhook enabled status")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "url": "https://api.example.com/webhook",
                "event_type": "product_created",
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class TaskStatusResponse(BaseModel):
    """
    Task status response for CSV import progress tracking
    
    Used for real-time progress updates during CSV processing
    """
    state: str = Field(..., description="Task state (PROGRESS, SUCCESS, FAILURE)")
    current: int = Field(0, description="Current number of processed records")
    total: int = Field(0, description="Total number of records to process")
    progress_percent: Optional[int] = Field(None, description="Progress percentage (0-100)")
    status: str = Field(..., description="Human-readable status message")
    imported_count: Optional[int] = Field(None, description="Number of successfully imported products")
    error: Optional[str] = Field(None, description="Error message if task failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "state": "PROGRESS",
                "current": 1500,
                "total": 10000,
                "progress_percent": 15,
                "status": "Processing 1500 of 10000 records (15%)",
                "imported_count": None,
                "error": None
            }
        }