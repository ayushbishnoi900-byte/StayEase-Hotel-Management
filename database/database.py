# Import required libraries

import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env

load_dotenv()

# Get database connection URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Normalize legacy postgres:// URI schema if provided
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Safe fallback for local/offline development and Vercel build inspection
if not DATABASE_URL:
    # On Vercel Serverless (AWS Lambda), only /tmp is writable; ./ is read-only
    db_path = "/tmp/stayease_local.db" if os.path.exists("/tmp") else "./stayease_local.db"
    DATABASE_URL = f"sqlite:///{db_path}"
    print(f"[StayEase] Notice: DATABASE_URL environment variable is missing. Falling back to SQLite database: {db_path}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

# Create database session

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for database models

Base = declarative_base()


# Function to connect database with API requests

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()