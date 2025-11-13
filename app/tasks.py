"""
Celery tasks for CSV processing
"""
from celery import current_task
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Product
from app.redis_client import RedisCache
from sqlalchemy import text
import csv
import io
from datetime import datetime

@celery_app.task(bind=True)
def process_csv_task(self, csv_content: str):
    """
    Celery task for processing CSV files asynchronously
    """
    task_id = self.request.id
    db = SessionLocal()
    
    try:
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        total_rows = len(rows)
        
        # Initialize progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": total_rows,
                "status": "Starting CSV processing...",
                "progress_percent": 0
            }
        )
        
        # Process in chunks
        chunk_size = 1000
        imported_count = 0
        
        for chunk_start in range(0, total_rows, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_rows)
            chunk = rows[chunk_start:chunk_end]
            
            # Prepare bulk data with deduplication
            valid_products = []
            seen_skus = set()
            
            for row in chunk:
                name = row.get('name', '').strip()
                sku = row.get('sku', '').strip()
                description = row.get('description', '').strip()
                
                if name and sku:
                    sku_upper = sku.upper()
                    if sku_upper not in seen_skus:
                        valid_products.append({
                            'name': name,
                            'sku': sku_upper,
                            'description': description
                        })
                        seen_skus.add(sku_upper)
            
            # Bulk insert with UPSERT
            if valid_products:
                values = []
                for p in valid_products:
                    name_escaped = p['name'].replace("'", "''")
                    desc_escaped = p['description'].replace("'", "''")
                    values.append(f"('{name_escaped}', '{p['sku']}', '{desc_escaped}', true, NOW(), NOW())")
                
                if values:
                    sql = f"""
                    INSERT INTO products (name, sku, description, active, created_at, updated_at) 
                    VALUES {','.join(values)}
                    ON CONFLICT (sku) DO UPDATE SET 
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        updated_at = NOW()
                    """
                    db.execute(text(sql))
                    db.commit()
            
            imported_count += len(valid_products)
            progress_percent = int(chunk_end / total_rows * 100)
            
            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": chunk_end,
                    "total": total_rows,
                    "progress_percent": progress_percent,
                    "status": f"Processed {chunk_end} of {total_rows} records ({progress_percent}%)",
                    "imported_count": imported_count
                }
            )
        
        # Mark as completed
        return {
            "current": total_rows,
            "total": total_rows,
            "progress_percent": 100,
            "status": f"Import completed! Processed {imported_count} products.",
            "imported_count": imported_count
        }
        
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Import failed: {str(e)}",
                "error": str(e)
            }
        )
        raise
    finally:
        db.close()