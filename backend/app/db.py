
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def get_db_url():
    user = os.getenv("POSTGRES_USER")
    pwd = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

engine = create_engine(get_db_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_database():
    """初始化数据库表结构"""
    from .models import Base
    try:
        # 使用 SQLAlchemy 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created/updated successfully")
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        raise
