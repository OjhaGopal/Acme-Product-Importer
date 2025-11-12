"""
Utility functions for health checks, metrics, and common operations

This module provides helper functions for monitoring application health,
gathering metrics, and other shared functionality.
"""

import time
from sqlalchemy.orm import Session
from app.models import Product, Webhook
from app.redis_client import RedisCache


def check_database_health():
    """
    Check database connectivity and response time
    
    Returns:
        dict: Database health status with response time
    """
    try:
        from app.database import SessionLocal
        
        start_time = time.time()
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": "healthy",
            "response_time": f"{response_time}ms"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_redis_health():
    """
    Check Redis connectivity and response time
    
    Returns:
        dict: Redis health status with response time
    """
    try:
        start_time = time.time()
        RedisCache.set("health_check", "ok", 10)
        result = RedisCache.get("health_check")
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if result == "ok":
            return {
                "status": "healthy",
                "response_time": f"{response_time}ms"
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Redis test failed"
            }
    except Exception as e:
        return {
            "status": "degraded",
            "error": "Redis unavailable - running without cache",
            "details": str(e)
        }


def get_health_status():
    """
    Get overall application health status
    
    Returns:
        dict: Complete health status including all services
    """
    db_health = check_database_health()
    redis_health = check_redis_health()
    
    # Determine overall status
    if db_health["status"] == "healthy":
        if redis_health["status"] == "healthy":
            overall_status = "healthy"
        elif redis_health["status"] == "degraded":
            overall_status = "degraded"  # App works but without cache
        else:
            overall_status = "unhealthy"
    else:
        overall_status = "unhealthy"  # Database is critical
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "services": {
            "database": db_health,
            "redis": redis_health
        },
        "version": "1.0.0"
    }


def get_metrics(db: Session):
    """
    Get application metrics and statistics
    
    Args:
        db: Database session
        
    Returns:
        dict: Application metrics including product and webhook counts
    """
    try:
        # Get product statistics
        total_products = db.query(Product).count()
        active_products = db.query(Product).filter(Product.active == True).count()
        inactive_products = total_products - active_products
        
        # Get webhook statistics
        total_webhooks = db.query(Webhook).count()
        enabled_webhooks = db.query(Webhook).filter(Webhook.enabled == True).count()
        
        return {
            "products": {
                "total": total_products,
                "active": active_products,
                "inactive": inactive_products
            },
            "webhooks": {
                "total": total_webhooks,
                "enabled": enabled_webhooks,
                "disabled": total_webhooks - enabled_webhooks
            },
            "status": "operational",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
            "timestamp": time.time()
        }


def validate_csv_headers(csv_content: str):
    """
    Validate CSV file headers
    
    Args:
        csv_content: CSV file content as string
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    import csv
    import io
    
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        headers = csv_reader.fieldnames
        
        required_headers = {'name', 'sku'}
        optional_headers = {'description'}
        
        if not headers:
            return False, "CSV file appears to be empty"
        
        # Convert to lowercase for case-insensitive comparison
        headers_lower = {h.lower().strip() for h in headers}
        
        # Check required headers
        missing_headers = required_headers - headers_lower
        if missing_headers:
            return False, f"Missing required headers: {', '.join(missing_headers)}"
        
        return True, "CSV headers are valid"
        
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"


def format_file_size(size_bytes: int):
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        str: Formatted file size (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def sanitize_filename(filename: str):
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    import re
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    
    return filename.strip('-')