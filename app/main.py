"""
Acme Product Importer - Main Application

A scalable web application for importing products from CSV files into a SQL database.
Built with FastAPI, PostgreSQL, and Redis for optimal performance.

Author: Backend Engineer Assessment
Date: 2024
"""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import os
import csv
import io
import uuid
import asyncio
from datetime import datetime

from app.database import get_db, engine
from app.models import Product, Webhook, Base
from app.schemas import ProductResponse, WebhookResponse
from app.redis_client import RedisCache
from app.utils import get_health_status, get_metrics

# Database tables will be initialized on first request

# FastAPI application instance
app = FastAPI(
    title="Acme Product Importer",
    description="A scalable web application for importing products from CSV files",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    print("Acme Product Importer starting up...")
    print("Database tables will be initialized on first access")


# ============================================================================
# WEB ROUTES - User Interface
# ============================================================================

@app.get("/", response_class=HTMLResponse, tags=["Web Interface"])
async def home(request: Request):
    """Home page with CSV upload interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/products", response_class=HTMLResponse, tags=["Web Interface"])
async def products_page(request: Request):
    """Product management interface"""
    return templates.TemplateResponse("products.html", {"request": request})


@app.get("/webhooks", response_class=HTMLResponse, tags=["Web Interface"])
async def webhooks_page(request: Request):
    """Webhook configuration interface"""
    return templates.TemplateResponse("webhooks.html", {"request": request})


# ============================================================================
# HEALTH & MONITORING ENDPOINTS
# ============================================================================

@app.get("/ping", tags=["Monitoring"])
def ping():
    """Simple ping endpoint for basic health check"""
    return {"status": "ok", "message": "Acme Product Importer is running"}


@app.get("/health", tags=["Monitoring"])
def health_check():
    """
    Health check endpoint for monitoring system status
    Returns database and Redis connectivity status
    """
    return get_health_status()


@app.get("/metrics", tags=["Monitoring"])
def metrics(db: Session = Depends(get_db)):
    """
    Application metrics endpoint
    Returns product counts and system statistics
    """
    return get_metrics(db)


# ============================================================================
# PRODUCT API ENDPOINTS - STORY 2: Product Management
# ============================================================================

@app.get("/api/products", response_model=List[ProductResponse], tags=["Products"])
def get_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve products with filtering and pagination
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Search term for name, SKU, or description
    - **active**: Filter by active status (true/false)
    """
    # Create cache key for Redis
    cache_key = f"products:{skip}:{limit}:{search}:{active}"
    
    # Try to get from Redis cache first
    cached_result = RedisCache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Build database query
    query = db.query(Product)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) |
            (Product.sku.ilike(search_term)) |
            (Product.description.ilike(search_term))
        )
    
    if active is not None:
        query = query.filter(Product.active == active)
    
    products = query.offset(skip).limit(limit).all()
    
    # Convert to response format
    products_data = [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "description": p.description,
            "active": p.active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }
        for p in products
    ]
    
    # Cache for 5 minutes
    RedisCache.set(cache_key, products_data, 300)
    
    return products_data


@app.get("/api/products/count", tags=["Products"])
def get_products_count(
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get total count of products matching filters"""
    query = db.query(func.count(Product.id))
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) |
            (Product.sku.ilike(search_term)) |
            (Product.description.ilike(search_term))
        )
    
    if active is not None:
        query = query.filter(Product.active == active)
    
    count = query.scalar()
    return {"count": count}


@app.post("/api/products", response_model=ProductResponse, tags=["Products"])
def create_product(
    name: str = Form(..., description="Product name"),
    sku: str = Form(..., description="Product SKU (must be unique)"),
    description: str = Form("", description="Product description"),
    active: bool = Form(True, description="Product active status"),
    db: Session = Depends(get_db)
):
    """Create a new product"""
    # Check for duplicate SKU (case-insensitive)
    existing = db.query(Product).filter(Product.sku.ilike(sku)).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    # Create new product
    product = Product(name=name, sku=sku, description=description, active=active)
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Clear products cache
    _clear_products_cache()
    
    return product


@app.put("/api/products/{product_id}", response_model=ProductResponse, tags=["Products"])
def update_product(
    product_id: int,
    name: str = Form(...),
    sku: str = Form(...),
    description: str = Form(""),
    active: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Update an existing product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check SKU uniqueness if changed
    if sku.lower() != product.sku.lower():
        existing = db.query(Product).filter(Product.sku.ilike(sku)).first()
        if existing:
            raise HTTPException(status_code=400, detail="SKU already exists")
    
    # Update product
    product.name = name
    product.sku = sku
    product.description = description
    product.active = active
    product.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(product)
    
    # Clear products cache
    _clear_products_cache()
    
    return product


@app.delete("/api/products/{product_id}", tags=["Products"])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a specific product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    
    # Clear products cache
    _clear_products_cache()
    
    return {"message": "Product deleted successfully"}


@app.delete("/api/products", tags=["Products"])
def delete_all_products(db: Session = Depends(get_db)):
    """STORY 3: Bulk delete all products"""
    count = db.query(Product).count()
    db.query(Product).delete()
    db.commit()
    
    # Clear products cache
    _clear_products_cache()
    
    return {"message": f"Successfully deleted {count} products"}


# ============================================================================
# CSV UPLOAD ENDPOINTS - STORY 1 & 1A: File Upload with Progress
# ============================================================================

@app.post("/api/upload", tags=["CSV Import"])
async def upload_csv(file: UploadFile = File(...)):
    """
    STORY 1: Upload and process CSV file asynchronously
    Returns task ID for progress tracking
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Read file content
    content = await file.read()
    csv_content = content.decode('utf-8')
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Start async processing
    asyncio.create_task(_process_csv_async(task_id, csv_content))
    
    return {
        "task_id": task_id,
        "message": "CSV upload started. Use task_id to track progress."
    }


@app.get("/api/task-status/{task_id}", tags=["CSV Import"])
def get_task_status(task_id: str):
    """
    STORY 1A: Get real-time progress of CSV processing
    Returns current status, progress, and completion percentage
    """
    status = RedisCache.get(f"task:{task_id}")
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


# ============================================================================
# WEBHOOK ENDPOINTS - STORY 4: Webhook Management
# ============================================================================

@app.get("/api/webhooks", response_model=List[WebhookResponse], tags=["Webhooks"])
def get_webhooks(db: Session = Depends(get_db)):
    """Get all configured webhooks"""
    return db.query(Webhook).all()


@app.post("/api/webhooks", response_model=WebhookResponse, tags=["Webhooks"])
def create_webhook(
    url: str = Form(..., description="Webhook URL"),
    event_type: str = Form(..., description="Event type to trigger webhook"),
    enabled: bool = Form(True, description="Enable/disable webhook"),
    db: Session = Depends(get_db)
):
    """Create a new webhook"""
    webhook = Webhook(url=url, event_type=event_type, enabled=enabled)
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@app.delete("/api/webhooks/{webhook_id}", tags=["Webhooks"])
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Delete a webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
    return {"message": "Webhook deleted successfully"}


@app.post("/api/webhooks/{webhook_id}/test", tags=["Webhooks"])
def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Test a webhook by sending a test payload"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # In a real implementation, this would send an HTTP request to the webhook URL
    return {
        "message": "Test webhook triggered successfully",
        "webhook_url": webhook.url,
        "status": "simulated_success"
    }


# ============================================================================
# INTERNAL HELPER FUNCTIONS
# ============================================================================

async def _process_csv_async(task_id: str, csv_content: str):
    """
    Asynchronously process CSV content with progress tracking
    Handles large files efficiently with batch processing
    """
    db = next(get_db())
    
    try:
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        total_rows = len(rows)
        
        # Initialize progress tracking
        RedisCache.set(f"task:{task_id}", {
            "state": "PROGRESS",
            "current": 0,
            "total": total_rows,
            "status": "Starting CSV processing..."
        }, 3600)
        
        imported_count = 0
        batch_size = 100  # Process in batches for better performance
        
        for i, row in enumerate(rows):
            name = row.get('name', '').strip()
            sku = row.get('sku', '').strip()
            description = row.get('description', '').strip()
            
            # Skip invalid rows
            if not name or not sku:
                continue
            
            # Check for existing product (case-insensitive SKU)
            existing_product = db.query(Product).filter(Product.sku.ilike(sku)).first()
            
            if existing_product:
                # Update existing product (SKU-based deduplication)
                existing_product.name = name
                existing_product.description = description
                existing_product.updated_at = datetime.utcnow()
            else:
                # Create new product
                product = Product(
                    name=name,
                    sku=sku,
                    description=description,
                    active=True  # Default to active
                )
                db.add(product)
            
            imported_count += 1
            
            # Batch commit and progress update
            if i % batch_size == 0 or i == total_rows - 1:
                db.commit()
                
                # Update progress in Redis
                progress_percent = int((i + 1) / total_rows * 100)
                RedisCache.set(f"task:{task_id}", {
                    "state": "PROGRESS",
                    "current": i + 1,
                    "total": total_rows,
                    "progress_percent": progress_percent,
                    "status": f"Processing {i + 1} of {total_rows} records ({progress_percent}%)"
                }, 3600)
                
                # Clear products cache
                _clear_products_cache()
                
                # Allow other tasks to run
                await asyncio.sleep(0.01)
        
        # Mark as completed
        RedisCache.set(f"task:{task_id}", {
            "state": "SUCCESS",
            "current": total_rows,
            "total": total_rows,
            "progress_percent": 100,
            "status": f"Import completed successfully! Processed {imported_count} products.",
            "imported_count": imported_count
        }, 3600)
        
    except Exception as e:
        # Handle errors gracefully
        RedisCache.set(f"task:{task_id}", {
            "state": "FAILURE",
            "status": f"Import failed: {str(e)}",
            "error": str(e)
        }, 3600)
    
    finally:
        db.close()


def _clear_products_cache():
    """Clear all products-related cache entries"""
    try:
        from app.redis_client import redis_client
        # Clear all cache keys matching products pattern
        for key in redis_client.scan_iter(match="products:*"):
            redis_client.delete(key)
    except Exception:
        # Fail silently if Redis is unavailable
        pass


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )