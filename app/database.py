from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment - Railway uses DATABASE_PUBLIC_URL
DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback for local development
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/acme_products"

print(f"Using Database URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "No Database URL found")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Track if tables have been initialized
_tables_initialized = False

def ensure_tables_exist():
    """Ensure database tables exist, create if they don't"""
    global _tables_initialized
    if not _tables_initialized:
        try:
            Base.metadata.create_all(bind=engine)
            _tables_initialized = True
            print("Database tables initialized successfully")
        except Exception as e:
            print(f"Database table creation failed: {e}")
            # Don't set _tables_initialized = True so it will retry later
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db_async():
    """Initialize database tables asynchronously"""
    import threading
    thread = threading.Thread(target=ensure_tables_exist)
    thread.daemon = True
    thread.start()