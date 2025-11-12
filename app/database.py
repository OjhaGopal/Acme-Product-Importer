from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment (Railway sets this automatically)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback for local development
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/acme_products"

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
        except Exception as e:
            print(f"Database table creation failed: {e}")
            pass  # Continue without failing

def get_db():
    # Ensure tables exist on first database access
    ensure_tables_exist()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()