
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, text, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import json
import os
import random
import signal
import sys
import time
import tushare as ts
from dotenv import load_dotenv

load_dotenv()

from .db import SessionLocal, init_database
from .data_source import get_stock_info, search_stocks, get_realtime_stock, fetch_daily
from .models import Watchlist, PriceDaily, Forecast, Signal, Task, Report, TaskStatus, TaskType, Stock
from .forecast import predict_stock_price
from .report import generate_report_data
from .task_manager import TaskManager
from .scheduler import run_daily_pipeline

# 创建任务管理器实例
task_manager = TaskManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    print("🚀 Starting backend server...")
    init_database()
    
    # 启动后台任务处理器
    task = asyncio.create_task(background_task_processor())
    
    yield
    
    # 关闭时停止任务管理器
    print("🔄 Stopping backend server...")
    task_manager.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

async def background_task_processor():
    """后台任务处理器"""
    print("📋 Background task processor started")
    await task_manager.process_tasks()

app = FastAPI(title="AI Stock API", version="1.1", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio

from .db import SessionLocal, init_database
from .data_source import get_stock_info, search_stocks, get_realtime_stock
from .models import Stock, Report, Task
from .forecast import predict_stock_price
from .report import generate_report_data
from .task_manager import TaskManager

# 创建任务管理器实例
task_manager = TaskManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    print("🚀 Starting backend server...")
    init_database()
    
    # 启动后台任务处理器
    task = asyncio.create_task(background_task_processor())
    
    yield
    
    # 关闭时停止任务管理器
    print("🔄 Stopping backend server...")
    task_manager.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

async def background_task_processor():
    """后台任务处理器"""
    print("📋 Background task processor started")
    await task_manager.process_tasks()

app = FastAPI(title="AI Stock API", version="1.1", lifespan=lifespan)

app = FastAPI(
    title="AIStock A-Share Assistant", 
    version="1.1",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WatchItem(BaseModel):
    symbol: str
    name: str | None = None
    sector: str | None = None
    enabled: bool = True

# 全局缓存股票基础数据
_stock_basic_cache = None

def retry_with_backoff(max_retries=3, base_delay=1.0):
    """重试装饰器，支持指数退避"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:  # 不是最后一次重试
                        # 指数退避 + 随机抖动
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                    else:
                        print(f"All {max_retries} attempts failed. Last error: {str(e)}")
            raise last_exception
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3, base_delay=1.0)
def fetch_stock_basic_with_retry(data_source):
    """带重试机制的股票基础数据获取"""
    if data_source == "tushare":
        token = os.getenv("TUSHARE_TOKEN")
        if not token or token == "your_tushare_token_here":
            raise HTTPException(status_code=500, detail="TUSHARE_TOKEN not configured. Please set your token in .env file")
        
        ts.set_token(token)
        pro = ts.pro_api()
        return pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,market')
    else:
        # 使用 akshare 作为默认数据源
        import akshare as ak
        # 获取A股股票基本信息
        df = ak.stock_info_a_code_name()
        # 重命名列以匹配 tushare 格式
        df = df.rename(columns={'code': 'symbol', 'name': 'name'})
        # 为了兼容，添加 ts_code 和 market 列
        df['ts_code'] = df['symbol'].apply(lambda x: f"{x}.SH" if x.startswith('6') else f"{x}.SZ")
        df['market'] = df['symbol'].apply(lambda x: 'SH' if x.startswith('6') else 'SZ')
        return df

def get_stock_basic():
    global _stock_basic_cache
    if _stock_basic_cache is not None:
        return _stock_basic_cache
    
    data_source = os.getenv("DATA_SOURCE", "akshare")
    
    try:
        _stock_basic_cache = fetch_stock_basic_with_retry(data_source)
        print(f"✓ Stock basic data loaded successfully using {data_source}")
        return _stock_basic_cache
    except Exception as e:
        error_msg = f"{data_source.title()} API error: {str(e)}"
        if data_source == "tushare":
            error_msg += ". Try using akshare instead."
        raise HTTPException(status_code=500, detail=error_msg)

# 在线股票搜索接口
@app.get("/search_stock")
def search_stock(q: str = Query(..., description="股票代码或名称")):
    print(f"🔍 Search query: {q}")
    
    # 输入验证
    if not q or len(q.strip()) < 1:
        raise HTTPException(status_code=400, detail="查询参数不能为空")
    
    q = q.strip()
    
    try:
        # 尝试获取股票基础数据（已包含重试机制）
        df = get_stock_basic()
        
        # pandas contains 支持正则，特殊字符需转义，中文需 lower 兼容
        import re
        def safe_contains(s, pat):
            try:
                escaped_pat = re.escape(pat)
                return s.str.contains(escaped_pat, case=False, na=False)
            except Exception:
                try:
                    return s.str.contains(pat, case=False, na=False)
                except Exception:
                    return s == s  # 返回全 False 的布尔索引
        
        result = df[
            safe_contains(df['ts_code'], q)
            | safe_contains(df['symbol'], q)
            | safe_contains(df['name'], q)
        ]
        
        # 限制返回结果数量，避免过多结果
        result = result.head(20)

        print(f"✓ Found {len(result)} results for query: {q}")

        # 转换为列表字典格式，使用字典索引避免 iterrows 的问题
        new_result = []
        for _, row in result.iterrows():
            new_result.append({
                "ts_code": str(row['ts_code']),
                "symbol": str(row['symbol']),
                "name": str(row['name']),
                "market": str(row['market'])
            })

        return new_result
        
    except HTTPException:
        # 重新抛出 HTTPException，保持原有错误信息
        print("✗ Stock search failed with HTTPException")
        raise
    except Exception as e:
        error_msg = f"Stock search failed: {str(e)}"
        print(f"✗ {error_msg}")
        
        # 对于网络相关错误，提供更友好的错误信息
        if any(keyword in str(e).lower() for keyword in ['timeout', 'connection', 'network', 'dns']):
            error_msg = "网络连接超时，请稍后重试。如果问题持续存在，请检查网络连接。"
        elif 'read timed out' in str(e).lower():
            error_msg = "数据读取超时，请稍后重试。"
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
def health():
    return {"status":"ok"}

# 清除股票基础数据缓存并重新加载
@app.post("/cache/refresh")
def refresh_stock_cache():
    global _stock_basic_cache
    _stock_basic_cache = None
    try:
        # 重新获取数据
        data = get_stock_basic()
        return {
            "ok": True, 
            "message": f"Stock cache refreshed successfully. Loaded {len(data)} stocks.",
            "data_source": os.getenv("DATA_SOURCE", "akshare")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh cache: {str(e)}")

# 获取缓存状态
@app.get("/cache/status")
def cache_status():
    global _stock_basic_cache
    return {
        "cache_loaded": _stock_basic_cache is not None,
        "cache_size": len(_stock_basic_cache) if _stock_basic_cache is not None else 0,
        "data_source": os.getenv("DATA_SOURCE", "akshare")
    }

@app.get("/watchlist")
def get_watchlist():
    with SessionLocal() as session:
        res = session.execute(select(Watchlist).where(Watchlist.enabled==True)).scalars().all()
        return [
            {
                "symbol": r.symbol,
                "name": r.name,
                "sector": r.sector,
                "enabled": r.enabled,
            }
            for r in res
        ]


@app.post("/watchlist")
def add_watch(item: WatchItem):
    with SessionLocal() as session:
        stmt = pg_insert(Watchlist).values(
            symbol=item.symbol.upper(),
            name=item.name,
            sector=item.sector,
            enabled=item.enabled,
        ).on_conflict_do_update(
            index_elements=["symbol"],
            set_={"name": item.name, "sector": item.sector, "enabled": item.enabled},
        )
        session.execute(stmt)
        session.commit()
    return {"ok": True}

# 删除自选股接口
@app.delete("/watchlist/{symbol}")
def delete_watch(symbol: str):
    with SessionLocal() as session:
        affected = session.execute(
            text("DELETE FROM watchlist WHERE symbol=:sym"),
            {"sym": symbol.upper()}
        )
        session.commit()
    return {"ok": True}

@app.post("/run/daily")
async def run_daily_now():
    ok = await run_daily_pipeline()
    return {"ok": ok}

@app.get("/report/{symbol}")
async def get_report(symbol: str, version: int = Query(None, description="报告版本号，默认返回最新版本")):
    with SessionLocal() as session:
        sym = symbol.upper()
        
        # 查找报告
        if version:
            # 获取指定版本的报告
            report = session.execute(
                select(Report).where(
                    and_(Report.symbol == sym, Report.version == version)
                )
            ).scalar_one_or_none()
        else:
            # 获取最新版本的报告 - 按创建时间排序并取第一个
            result = session.execute(
                select(Report).where(
                    and_(Report.symbol == sym, Report.is_latest == True)
                ).order_by(Report.created_at.desc())
            ).first()
            
            report = result[0] if result else None
        
        if report:
            # 使用报告数据
            result = {
                "symbol": sym,
                "version": report.version,
                "created_at": report.created_at.isoformat(),
                "is_latest": report.is_latest,
                "data_quality_score": float(report.data_quality_score) if report.data_quality_score else None,
                "prediction_confidence": float(report.prediction_confidence) if report.prediction_confidence else None,
                "analysis_summary": report.analysis_summary
            }
            
            # 解析JSON数据
            if report.latest_price_data:
                result["latest"] = json.loads(report.latest_price_data)
            
            if report.signal_data:
                result["signal"] = json.loads(report.signal_data)
            
            if report.forecast_data:
                result["forecast"] = json.loads(report.forecast_data)
            
            return result
        
        # 如果没有报告，创建报告任务并返回传统数据
        await task_manager.create_report_task(sym, priority=1)
        
        # 返回传统方式查询的数据
        last = session.execute(
            text(
                "SELECT p.* FROM prices_daily p WHERE p.symbol=:sym ORDER BY p.trade_date DESC LIMIT 1"
            ),
            {"sym": sym},
        ).mappings().first()
        sig = session.execute(
            text(
                "SELECT * FROM signals WHERE symbol=:sym ORDER BY trade_date DESC LIMIT 1"
            ),
            {"sym": sym},
        ).mappings().first()
        fc = session.execute(
            text(
                "SELECT target_date, avg(yhat) yhat, avg(yhat_lower) yl, avg(yhat_upper) yu FROM forecasts WHERE symbol=:sym GROUP BY target_date ORDER BY target_date"
            ),
            {"sym": sym},
        ).mappings().all()
        
        if not last:
            raise HTTPException(status_code=404, detail="no data")
        
        return {
            "latest": dict(last),
            "signal": dict(sig) if sig else None,
            "forecast": [dict(r) for r in fc],
            "report_status": "generating",
            "message": "报告生成中，请稍后刷新"
        }

@app.get("/signals/today")
def signals_today():
    with SessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT * FROM signals WHERE trade_date=(SELECT max(trade_date) FROM signals) ORDER BY signal_score DESC"
            )
        ).mappings().all()
        return [dict(r) for r in rows]

@app.get("/prices/{symbol}")
def get_prices(symbol: str, limit: int = Query(180, ge=1, le=1000)):
    with SessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT trade_date, close, open, high, low, vol FROM prices_daily WHERE symbol=:sym ORDER BY trade_date DESC LIMIT :lim"
            ),
            {"sym": symbol.upper(), "lim": limit},
        ).mappings().all()
        out = [dict(r) for r in rows][::-1]
        return out

# 任务管理API端点
@app.get("/tasks/pending")
async def get_pending_tasks():
    """获取待处理任务列表"""
    tasks = await task_manager.get_pending_tasks()
    return {"tasks": tasks}

@app.post("/tasks/create_report/{symbol}")
async def create_report_task(symbol: str, priority: int = Query(5, ge=1, le=10)):
    """为指定股票创建报告任务"""
    task_id = await task_manager.create_report_task(symbol.upper(), priority)
    return {"task_id": task_id, "symbol": symbol.upper()}

@app.post("/tasks/check_missing")
async def check_missing_report_tasks():
    """检查并创建缺失的报告任务"""
    created_tasks = await task_manager.check_and_create_missing_report_tasks()
    return {"created_tasks": created_tasks, "count": len(created_tasks)}

@app.get("/api/report/{symbol}/full")
async def get_full_report(symbol: str):
    """
    获取完整的股票报告，包含历史价格走势和预测数据
    默认显示过去5个工作日和未来5个工作日
    """
    with SessionLocal() as session:
        sym = symbol.upper()
        
        try:
            # 获取最新报告
            report = session.execute(
                select(Report).where(
                    and_(Report.symbol == sym, Report.is_latest == True)
                ).order_by(Report.created_at.desc())
            ).scalar_one_or_none()
            
            # 获取过去10个工作日的价格数据（确保有5个工作日）
            historical_prices = session.execute(
                text(
                    "SELECT trade_date, open, high, low, close, vol, pct_chg "
                    "FROM prices_daily WHERE symbol=:sym "
                    "ORDER BY trade_date DESC LIMIT 10"
                ),
                {"sym": sym}
            ).mappings().all()
            
            if not historical_prices:
                raise HTTPException(status_code=404, detail=f"No data found for {sym}")
            
            # 转换历史价格数据
            price_data = []
            for i, price in enumerate(reversed(historical_prices)):
                price_data.append({
                    "date": price["trade_date"].isoformat(),
                    "open": float(price["open"]) if price["open"] else None,
                    "high": float(price["high"]) if price["high"] else None,
                    "low": float(price["low"]) if price["low"] else None,
                    "close": float(price["close"]) if price["close"] else None,
                    "volume": int(price["vol"]) if price["vol"] else 0,
                    "pct_change": float(price["pct_chg"]) if price["pct_chg"] else 0,
                    "type": "historical"
                })
            
            # 获取预测数据
            predictions = []
            prediction_dates = []
            prediction_mean = []
            prediction_upper = []
            prediction_lower = []
            
            if report and report.forecast_data:
                try:
                    forecast_data = json.loads(report.forecast_data)
                    if "predictions" in forecast_data:
                        from datetime import datetime, timedelta
                        last_date = historical_prices[0]["trade_date"]
                        
                        for pred in forecast_data["predictions"]:
                            # 计算预测日期（跳过周末）
                            target_date = last_date + timedelta(days=pred["day"])
                            while target_date.weekday() >= 5:  # 跳过周末
                                target_date += timedelta(days=1)
                            
                            prediction_dates.append(target_date.isoformat())
                            prediction_mean.append(pred["predicted_price"])
                            prediction_upper.append(pred["upper_bound"])
                            prediction_lower.append(pred["lower_bound"])
                            
                            predictions.append({
                                "date": target_date.isoformat(),
                                "predicted_price": pred["predicted_price"],
                                "upper_bound": pred["upper_bound"],
                                "lower_bound": pred["lower_bound"],
                                "type": "prediction"
                            })
                except Exception as e:
                    print(f"Error parsing forecast data: {e}")
            
            # 构建响应
            result = {
                "symbol": sym,
                "data_updated": report.created_at.isoformat() if report else None,
                "data_quality_score": float(report.data_quality_score) if report and report.data_quality_score else None,
                "prediction_confidence": float(report.prediction_confidence) if report and report.prediction_confidence else None,
                "analysis_summary": report.analysis_summary if report else None,
                
                # 价格数据（过去和预测）
                "price_data": price_data,
                "predictions": predictions,
                
                # 前端兼容的格式
                "dates": prediction_dates,
                "predictions_mean": prediction_mean,
                "predictions_upper": prediction_upper,
                "predictions_lower": prediction_lower,
                
                # 最新价格和信号
                "latest_price": price_data[-1] if price_data else None,
            }
            
            # 添加技术指标信号
            if report and report.signal_data:
                try:
                    signal_data = json.loads(report.signal_data)
                    result["signal"] = signal_data
                except Exception as e:
                    print(f"Error parsing signal data: {e}")
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error in get_full_report: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/reports/{symbol}/regenerate")
async def regenerate_report(symbol: str):
    """重新生成指定股票的报告"""
    try:
        sym = symbol.upper()
        # 创建高优先级任务来重新生成报告
        task_id = await task_manager.create_report_task(sym, priority=1)
        return {"message": f"Report regeneration task created for {sym}", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating regeneration task: {str(e)}")

@app.get("/reports/{symbol}/history")
def get_report_history(symbol: str, limit: int = Query(10, ge=1, le=50)):
    """获取股票报告历史版本"""
    with SessionLocal() as session:
        reports = session.execute(
            select(Report).where(Report.symbol == symbol.upper())
            .order_by(Report.version.desc())
            .limit(limit)
        ).scalars().all()
        
        return {
            "symbol": symbol.upper(),
            "reports": [
                {
                    "version": r.version,
                    "created_at": r.created_at.isoformat(),
                    "is_latest": r.is_latest,
                    "data_quality_score": float(r.data_quality_score) if r.data_quality_score else None,
                    "prediction_confidence": float(r.prediction_confidence) if r.prediction_confidence else None,
                    "analysis_summary": r.analysis_summary
                }
                for r in reports
            ]
        }

@app.get("/tasks/status")
async def get_task_status():
    """获取任务系统状态"""
    with SessionLocal() as session:
        # 统计各状态的任务数量
        pending_count = session.execute(
            select(Task).where(Task.status == TaskStatus.PENDING)
        ).scalars().all()
        
        running_count = session.execute(
            select(Task).where(Task.status == TaskStatus.RUNNING)
        ).scalars().all()
        
        completed_count = session.execute(
            select(Task).where(Task.status == TaskStatus.COMPLETED)
        ).scalars().all()
        
        failed_count = session.execute(
            select(Task).where(Task.status == TaskStatus.FAILED)
        ).scalars().all()
        
        # 统计报告数量
        total_reports = session.execute(select(Report)).scalars().all()
        latest_reports = session.execute(
            select(Report).where(Report.is_latest == True)
        ).scalars().all()
        
        return {
            "tasks": {
                "pending": len(pending_count),
                "running": len(running_count),
                "completed": len(completed_count),
                "failed": len(failed_count)
            },
            "reports": {
                "total": len(total_reports),
                "latest": len(latest_reports)
            },
            "task_manager": {
                "running_tasks": len(task_manager.running_tasks),
                "max_concurrent": task_manager.max_concurrent_tasks
            }
        }

@app.get("/api/dashboard/reports")
def get_reports_dashboard(db: Session = Depends(get_db)):
    """获取报告仪表板数据 - 按股票统计"""
    try:
        # 获取所有股票的最新报告和任务状态
        query = """
        WITH latest_reports AS (
            SELECT DISTINCT ON (symbol) 
                symbol, version, created_at, is_latest,
                data_quality_score, prediction_confidence, analysis_summary
            FROM reports 
            ORDER BY symbol, version DESC
        ),
        latest_tasks AS (
            SELECT DISTINCT ON (symbol, task_type) 
                symbol, task_type, status, created_at as task_created_at,
                started_at, completed_at, error_message, priority
            FROM tasks 
            WHERE task_type = 'generate_report'
            ORDER BY symbol, task_type, created_at DESC
        )
        SELECT 
            w.symbol,
            w.name,
            w.sector,
            lr.version as latest_report_version,
            lr.created_at as latest_report_date,
            lr.data_quality_score,
            lr.prediction_confidence,
            lr.analysis_summary,
            lt.status as task_status,
            lt.task_created_at,
            lt.started_at,
            lt.completed_at,
            lt.error_message,
            lt.priority
        FROM watchlist w
        LEFT JOIN latest_reports lr ON w.symbol = lr.symbol
        LEFT JOIN latest_tasks lt ON w.symbol = lt.symbol
        WHERE w.enabled = true
        ORDER BY w.symbol
        """
        
        result = db.execute(text(query)).fetchall()
        
        dashboard_data = []
        for row in result:
            dashboard_data.append({
                "symbol": row.symbol,
                "name": row.name,
                "sector": row.sector,
                "latest_report": {
                    "version": str(row.latest_report_version) if row.latest_report_version else None,
                    "created_at": row.latest_report_date.isoformat() if row.latest_report_date else None,
                    "data_quality_score": float(row.data_quality_score) if row.data_quality_score else 0.0,
                    "prediction_confidence": float(row.prediction_confidence) if row.prediction_confidence else 0.0,
                    "analysis_summary": row.analysis_summary
                } if row.latest_report_version else None,
                "current_task": {
                    "status": row.task_status,
                    "created_at": row.task_created_at.isoformat() if row.task_created_at else None,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "error_message": row.error_message,
                    "priority": row.priority
                } if row.task_status else None
            })
        
        return {
            "stocks": dashboard_data,
            "summary": {
                "total_stocks": len(dashboard_data),
                "with_reports": len([s for s in dashboard_data if s["latest_report"]]),
                "pending_tasks": len([s for s in dashboard_data if s["current_task"] and s["current_task"]["status"] == "pending"]),
                "running_tasks": len([s for s in dashboard_data if s["current_task"] and s["current_task"]["status"] == "running"]),
                "failed_tasks": len([s for s in dashboard_data if s["current_task"] and s["current_task"]["status"] == "failed"])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/dashboard/tasks")
def get_tasks_dashboard(db: Session = Depends(get_db)):
    """获取任务仪表板数据"""
    try:
        # 任务状态统计
        status_stats = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """)).fetchall()
        
        # 最近24小时任务
        recent_tasks = db.execute(text("""
            SELECT symbol, task_type, status, created_at, completed_at, error_message
            FROM tasks
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 50
        """)).fetchall()
        
        # 任务类型统计
        type_stats = db.execute(text("""
            SELECT task_type, COUNT(*) as count
            FROM tasks
            GROUP BY task_type
        """)).fetchall()
        
        return {
            "status_statistics": {row.status: row.count for row in status_stats},
            "type_statistics": {row.task_type: row.count for row in type_stats},
            "recent_tasks": [
                {
                    "symbol": row.symbol,
                    "task_type": row.task_type,
                    "status": row.status,
                    "created_at": row.created_at.isoformat(),
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "error_message": row.error_message
                }
                for row in recent_tasks
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/tasks/report/{symbol}")
def create_report_task_api(symbol: str, priority: int = 5):
    """手动创建报告生成任务"""
    try:
        task_id = task_manager.create_task(
            task_type=TaskType.GENERATE_REPORT,
            symbol=symbol,
            priority=priority
        )
        return {"message": "Task created", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/tasks", response_model=List[dict])
def list_tasks_api(status: Optional[str] = None, symbol: Optional[str] = None, db: Session = Depends(get_db)):
    """列出任务"""
    try:
        query = select(Task)
        
        if status:
            query = query.where(Task.status == status)
        if symbol:
            query = query.where(Task.symbol == symbol)
            
        query = query.order_by(Task.priority.asc(), Task.created_at.asc())
        
        tasks = db.execute(query).scalars().all()
        
        return [
            {
                "id": task.id,
                "task_type": task.task_type,
                "symbol": task.symbol,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "priority": task.priority
            }
            for task in tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
