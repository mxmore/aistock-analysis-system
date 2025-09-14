
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, Date, BigInteger, Numeric, TIMESTAMP, Text, Index
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
