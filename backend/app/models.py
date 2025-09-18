
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Date, BigInteger, Numeric, TIMESTAMP, Text, Index, Float, ForeignKey, JSON
import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(str, Enum):
    GENERATE_REPORT = "generate_report"
    FETCH_DATA = "fetch_data"
    TRAIN_MODEL = "train_model"
    FETCH_NEWS = "fetch_news"
    ANALYZE_NEWS = "analyze_news"

class NewsCategory(str, Enum):
    FINANCE = "finance"
    POLICY = "policy"
    INDUSTRY = "industry"
    COMPANY = "company"
    MARKET = "market"
    ECONOMIC = "economic"

class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class Base(DeclarativeBase):
    pass

class Watchlist(Base):
    __tablename__ = "watchlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Stock(Base):
    __tablename__ = "stocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, default=datetime.datetime.utcnow)

class PriceDaily(Base):
    __tablename__ = "prices_daily"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    trade_date: Mapped[datetime.date] = mapped_column(Date)
    open: Mapped[float | None] = mapped_column(Numeric)
    high: Mapped[float | None] = mapped_column(Numeric)
    low: Mapped[float | None] = mapped_column(Numeric)
    close: Mapped[float | None] = mapped_column(Numeric)
    pre_close: Mapped[float | None] = mapped_column(Numeric)
    change: Mapped[float | None] = mapped_column(Numeric)
    pct_chg: Mapped[float | None] = mapped_column(Numeric)
    vol: Mapped[int | None]
    amount: Mapped[float | None] = mapped_column(Numeric)

class Forecast(Base):
    __tablename__ = "forecasts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    run_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP)
    target_date: Mapped[datetime.date] = mapped_column(Date)
    model: Mapped[str] = mapped_column(String(32))
    yhat: Mapped[float | None] = mapped_column(Numeric)
    yhat_lower: Mapped[float | None] = mapped_column(Numeric)
    yhat_upper: Mapped[float | None] = mapped_column(Numeric)

class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    trade_date: Mapped[datetime.date] = mapped_column(Date)
    ma_short: Mapped[float | None] = mapped_column(Numeric)
    ma_long: Mapped[float | None] = mapped_column(Numeric)
    rsi: Mapped[float | None] = mapped_column(Numeric)
    macd: Mapped[float | None] = mapped_column(Numeric)
    signal_score: Mapped[float | None] = mapped_column(Numeric)
    action: Mapped[str] = mapped_column(String(100))

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_type: Mapped[str] = mapped_column(String(32))  # TaskType
    symbol: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default=TaskStatus.PENDING)  # TaskStatus
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, default=datetime.datetime.utcnow)
    started_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, 1 is highest priority
    task_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string for additional params

    __table_args__ = (
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_symbol_type', 'symbol', 'task_type'),
    )

class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, default=datetime.datetime.utcnow)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Report content
    latest_price_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    signal_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    forecast_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    analysis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metrics
    data_quality_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    prediction_confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    
    __table_args__ = (
        Index('idx_report_symbol_latest', 'symbol', 'is_latest'),
        Index('idx_report_symbol_version', 'symbol', 'version'),
    )

class NewsSource(Base):
    __tablename__ = "news_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    category: Mapped[str] = mapped_column(String(50))  # NewsCategory
    reliability_score: Mapped[float] = mapped_column(Float, default=0.5)
    language: Mapped[str] = mapped_column(String(10), default="zh-CN")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    # Relationships
    articles = relationship("NewsArticle", back_populates="source")

class NewsArticle(Base):
    __tablename__ = "news_articles"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # News metadata
    published_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    crawled_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, default=datetime.datetime.utcnow)
    source_id: Mapped[int] = mapped_column(ForeignKey("news_sources.id"))
    
    # Content analysis
    category: Mapped[str] = mapped_column(String(50))  # NewsCategory
    keywords: Mapped[str | None] = mapped_column(JSON, nullable=True)  # List of keywords
    entities: Mapped[str | None] = mapped_column(JSON, nullable=True)  # Named entities
    
    # Sentiment analysis
    sentiment_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # SentimentType
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1 to 1
    sentiment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Stock relevance
    from sqlalchemy.dialects.postgresql import JSONB
    related_stocks: Mapped[str | None] = mapped_column(JSONB, nullable=True)  # List of stock symbols
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0 to 1
    
    # Quality metrics
    content_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[int | None] = mapped_column(ForeignKey("news_articles.id"), nullable=True)
    
    # Relationships
    source = relationship("NewsSource", back_populates="articles")
    
    __table_args__ = (
        Index('idx_news_published_at', 'published_at'),
        Index('idx_news_category', 'category'),
        Index('idx_news_sentiment', 'sentiment_type', 'sentiment_score'),
    Index('idx_news_stocks', 'related_stocks', postgresql_using='gin', postgresql_ops={"related_stocks": "jsonb_path_ops"}),
        Index('idx_news_source_published', 'source_id', 'published_at'),
        Index('idx_news_quality', 'content_quality', 'is_duplicate'),
    )

class NewsKeyword(Base):
    __tablename__ = "news_keywords"
    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(100), unique=True)
    keyword_type: Mapped[str] = mapped_column(String(50))  # stock_symbol, company_name, industry, policy
    related_symbol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    search_priority: Mapped[int] = mapped_column(Integer, default=5)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_searched: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    search_frequency: Mapped[int] = mapped_column(Integer, default=24)  # hours
    
    __table_args__ = (
        Index('idx_keyword_type_symbol', 'keyword_type', 'related_symbol'),
        Index('idx_keyword_priority', 'search_priority', 'enabled'),
    )

class SearchLog(Base):
    __tablename__ = "search_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    query: Mapped[str] = mapped_column(String(500))
    query_type: Mapped[str] = mapped_column(String(50))  # manual, auto, scheduled
    source_engine: Mapped[str] = mapped_column(String(50))  # searxng, manual
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    processing_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        Index('idx_search_query_type', 'query_type', 'created_at'),
        Index('idx_search_success', 'success', 'created_at'),
    )
