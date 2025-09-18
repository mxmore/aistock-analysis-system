
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, text, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from typing import List, Optional
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

app = FastAPI(title="AI Stock API", version="1.1")

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
async def get_full_report(symbol: str, timeRange: str = Query('5d', description="时间区间: 5d, 1m, 3m, 6m, 1y, all")):
    """
    获取完整的股票报告，包含历史价格走势和预测数据
    支持不同时间区间：5d, 1m, 3m, 6m, 1y, all
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
            
            # 根据时间区间获取历史价格数据
            if timeRange == 'all':
                # 获取所有可用数据
                historical_prices = session.execute(
                    text(
                        "SELECT trade_date, open, high, low, close, vol, pct_chg "
                        "FROM prices_daily WHERE symbol=:sym "
                        "ORDER BY trade_date DESC"
                    ),
                    {"sym": sym}
                ).mappings().all()
            else:
                # 根据时间区间过滤数据
                if timeRange == '5d':
                    days_back = 7  # 多取几天以确保有5个工作日
                elif timeRange == '1m':
                    days_back = 35  # 一个月加几天buffer
                elif timeRange == '3m':
                    days_back = 95  # 三个月加几天buffer
                elif timeRange == '6m':
                    days_back = 185  # 六个月加几天buffer
                elif timeRange == '1y':
                    days_back = 370  # 一年加几天buffer
                
                historical_prices = session.execute(
                    text(
                        "SELECT trade_date, open, high, low, close, vol, pct_chg "
                        "FROM prices_daily WHERE symbol=:sym "
                        "AND trade_date >= CURRENT_DATE - INTERVAL '{} days' "
                        "ORDER BY trade_date DESC".format(days_back)
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
                    "pct_chg": float(price["pct_chg"]) if price["pct_chg"] else 0,  # 前端兼容
                    "type": "historical"
                })
            
            # 获取预测数据
            predictions = []
            prediction_dates = []
            prediction_mean = []
            prediction_upper = []
            prediction_lower = []
            
            if report and report.forecast_data and historical_prices:
                try:
                    forecast_data = json.loads(report.forecast_data)
                    # forecast_data 是一个列表，直接处理
                    if isinstance(forecast_data, list) and len(forecast_data) > 0:
                        from datetime import datetime, timedelta
                        # 使用最新的历史价格日期作为基准（historical_prices是按日期降序排列的）
                        last_date = historical_prices[0]["trade_date"]
                        
                        # 取前10个预测点，重新计算日期
                        for i, pred in enumerate(forecast_data[:10]):
                            # 重新计算预测日期：从最新历史日期的下一个交易日开始
                            target_date = last_date + timedelta(days=i+1)
                            while target_date.weekday() >= 5:  # 跳过周末
                                target_date += timedelta(days=1)
                            
                            prediction_dates.append(target_date.isoformat())
                            prediction_mean.append(pred["yhat"])
                            prediction_upper.append(pred["yhat_upper"])
                            prediction_lower.append(pred["yhat_lower"])
                            
                            predictions.append({
                                "date": target_date.isoformat(),  # 使用重新计算的日期
                                "predicted_price": pred["yhat"],
                                "upper_bound": pred["yhat_upper"],
                                "lower_bound": pred["yhat_lower"],
                                "type": "prediction"
                            })
                    # 兼容旧格式（包含 "predictions" 键的格式）
                    elif isinstance(forecast_data, dict) and "predictions" in forecast_data:
                        from datetime import datetime, timedelta
                        # 使用最新的历史价格日期作为基准（historical_prices是按日期降序排列的）
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
                    # 即使预测数据解析失败，也要继续返回历史数据
            
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
                
                # 前端兼容字段
                "latest": price_data[-1] if price_data else None,  # 向后兼容
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

# ================ NEWS API ENDPOINTS ================

from .news_service import NewsSearchService, NewsProcessor, NewsScheduler
from .models import NewsArticle, NewsSource, SearchLog, NewsCategory, SentimentType

# Initialize news services
news_search_service = NewsSearchService()
news_processor = NewsProcessor()
news_scheduler = NewsScheduler()

class NewsSearchRequest(BaseModel):
    query: str
    category: Optional[str] = "news"
    time_range: Optional[str] = "week"
    max_results: Optional[int] = 20

class NewsResponse(BaseModel):
    articles: List[dict]
    total_count: int
    query: str
    processing_time: float

@app.post("/api/news/search")
async def search_news(request: NewsSearchRequest):
    """
    Search news using SearXNG
    """
    try:
        start_time = time.time()
        
        results = await news_search_service.search_news(
            query=request.query,
            category=request.category,
            time_range=request.time_range,
            max_results=request.max_results
        )
        
        processing_time = time.time() - start_time
        
        return NewsResponse(
            articles=results,
            total_count=len(results),
            query=request.query,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"News search failed: {str(e)}")

@app.get("/api/news/stock/{symbol}")
async def get_stock_news(symbol: str, limit: int = Query(20, ge=1, le=100)):
    """
    Get news for specific stock symbol
    """
    try:
        print(f"🔍 API called for stock: {symbol}")
        
        # Get stock info first
        stock_info = get_stock_info(symbol)
        if not stock_info:
            print(f"❌ Stock not found: {symbol}")
            raise HTTPException(status_code=404, detail="Stock not found")
        
        print(f"📊 Stock info: {stock_info.get('name')}")
        
        # Initialize services
        news_search_service = NewsSearchService()
        news_processor = NewsProcessor()
        
        # Search news for this stock
        print(f"🔎 Searching news...")
        results = await news_search_service.search_stock_news(
            symbol=symbol,
            company_name=stock_info.get('name')
        )
        
        print(f"🔎 Found {len(results)} search results")
        
        # Process and save articles
        print(f"📝 Processing articles...")
        articles = await news_processor.process_search_results(results, symbol)
        
        print(f"📝 Processed {len(articles)} articles")
        
        # Format response articles list
        response_articles = []
        
        # Save to database and build response
        session = SessionLocal()
        try:
            for i, article in enumerate(articles[:limit]):
                try:
                    print(f"💾 Processing article {i+1}: {article.title[:50]}...")
                    
                    # Check if article exists
                    existing = session.execute(
                        select(NewsArticle).where(NewsArticle.url == article.url)
                    ).scalar_one_or_none()
                    
                    current_article = None
                    if not existing:
                        print(f"  ✅ New article, saving...")
                        session.add(article)
                        session.commit()
                        session.refresh(article)
                        current_article = article
                    else:
                        print(f"  ♻️ Article exists, using existing...")
                        current_article = existing
                    
                    # Build article response data
                    source_name = "Unknown"
                    if current_article.source_id:
                        if hasattr(current_article, 'source') and current_article.source:
                            source_name = current_article.source.name
                        else:
                            # Load source if not loaded
                            session.refresh(current_article)
                            if hasattr(current_article, 'source') and current_article.source:
                                source_name = current_article.source.name
                    
                    article_data = {
                        "id": current_article.id,
                        "title": current_article.title,
                        "url": current_article.url,
                        "summary": current_article.summary or "",
                        "published_at": current_article.published_at.isoformat() if current_article.published_at else None,
                        "source": source_name,
                        "sentiment_type": current_article.sentiment_type,
                        "sentiment_score": current_article.sentiment_score,
                        "relevance_score": current_article.relevance_score,
                        "related_stocks": current_article.related_stocks or []
                    }
                    
                    response_articles.append(article_data)
                    print(f"  📄 Added to response")
                    
                except Exception as e:
                    print(f"❌ Error processing article: {e}")
                    session.rollback()
                    continue
                    
        finally:
            session.close()
        
        print(f"✅ Completed! Returning {len(response_articles)} articles")
        
        # Return response
        return {
            "symbol": symbol,
            "company_name": stock_info.get('name'),
            "articles": response_articles,
            "total_count": len(response_articles)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching stock news: {str(e)}")

@app.get("/api/news/articles")
async def get_news_articles(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Get news articles with filtering
    """
    try:
        query = select(NewsArticle).join(NewsSource)
        
        # Apply filters
        if category:
            query = query.where(NewsArticle.category == category)
        
        if sentiment:
            query = query.where(NewsArticle.sentiment_type == sentiment)
        
        if symbol:
            query = query.where(NewsArticle.related_stocks.contains([symbol]))
        
        # Order by published date, most recent first
        query = query.order_by(NewsArticle.published_at.desc().nullslast())
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        articles = db.execute(query).scalars().all()
        
        return {
            "articles": [
                {
                    "id": article.id,
                    "title": article.title,
                    "url": article.url,
                    "summary": article.summary,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "source": article.source.name,
                    "category": article.category,
                    "sentiment_type": article.sentiment_type,
                    "sentiment_score": article.sentiment_score,
                    "relevance_score": article.relevance_score,
                    "related_stocks": article.related_stocks,
                    "keywords": article.keywords
                }
                for article in articles
            ],
            "limit": limit,
            "offset": offset,
            "total_count": len(articles)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching articles: {str(e)}")

@app.get("/api/news/sources")
async def get_news_sources(db: Session = Depends(get_db)):
    """
    Get all news sources
    """
    try:
        sources = db.execute(select(NewsSource)).scalars().all()
        
        return {
            "sources": [
                {
                    "id": source.id,
                    "name": source.name,
                    "domain": source.domain,
                    "category": source.category,
                    "reliability_score": source.reliability_score,
                    "language": source.language,
                    "enabled": source.enabled
                }
                for source in sources
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sources: {str(e)}")

@app.post("/api/news/collect/{symbol}")
async def collect_news_for_stock(symbol: str, db: Session = Depends(get_db)):
    """
    Manually trigger news collection for a specific stock
    """
    try:
        # Get stock info
        stock_info = get_stock_info(symbol)
        if not stock_info:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Add news collection task
        task = Task(
            task_type=TaskType.FETCH_NEWS.value,
            symbol=symbol,
            status=TaskStatus.PENDING.value,
            priority=3,
            task_metadata=json.dumps({
                "company_name": stock_info.get('name'),
                "manual_trigger": True
            })
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        
        return {
            "message": f"News collection task created for {symbol}",
            "symbol": symbol,
            "company_name": stock_info.get('name'),
            "task_id": task_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating news collection task: {str(e)}")

@app.post("/api/news/collect/intelligent")
async def run_intelligent_news_collection():
    """
    Manually trigger intelligent news collection based on watchlist strategies
    """
    try:
        from .scheduler import run_manual_intelligent_collection
        
        result = await run_manual_intelligent_collection()
        
        return {
            "message": "Intelligent news collection completed",
            "status": result.get("status"),
            "strategies_executed": result.get("strategies_executed", 0),
            "strategies_skipped": result.get("strategies_skipped", 0),
            "strategies_failed": result.get("strategies_failed", 0),
            "total_articles": result.get("total_articles", 0),
            "strategy_results": result.get("strategy_results", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running intelligent news collection: {str(e)}")

@app.get("/api/news/strategies/test")
async def test_strategies():
    """
    Test endpoint for strategies generation
    """
    try:
        from .news_strategy import IntelligentNewsCollector
        
        collector = IntelligentNewsCollector()
        strategies = await collector.generate_strategies()
        
        return {
            "message": "Test successful",
            "strategies_count": len(strategies),
            "strategies": [s.name for s in strategies]
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/api/news/strategies")
async def get_news_strategies():
    """
    Get available news collection strategies
    """
    try:
        from .news_strategy import IntelligentNewsCollector
        
        collector = IntelligentNewsCollector()
        strategies = await collector.generate_strategies()
        
        return {
            "strategies": [
                {
                    "name": strategy.name,
                    "keywords": strategy.keywords,
                    "frequency_hours": strategy.search_frequency,
                    "priority": strategy.priority,
                    "category": strategy.category,
                    "search_params": strategy.search_params
                }
                for strategy in strategies
            ],
            "total_strategies": len(strategies)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching strategies: {str(e)}")

@app.post("/api/news/strategies/execute/{strategy_name}")
async def execute_news_strategy(strategy_name: str):
    """
    Execute a specific news strategy by name
    """
    try:
        from .news_strategy import IntelligentNewsCollector
        
        collector = IntelligentNewsCollector()
        strategies = await collector.generate_strategies()
        
        # Find the strategy
        target_strategy = None
        for strategy in strategies:
            if strategy.name == strategy_name:
                target_strategy = strategy
                break
        
        if not target_strategy:
            raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
        
        result = await collector.execute_strategy(target_strategy)
        
        return {
            "message": f"Strategy '{strategy_name}' executed",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing strategy: {str(e)}")

@app.get("/api/news/sentiment/{symbol}")
async def get_stock_sentiment(symbol: str, db: Session = Depends(get_db), days: int = Query(7, ge=1, le=30)):
    """
    Get sentiment analysis for a stock over time
    """
    try:
        from datetime import datetime, timedelta
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(NewsArticle).where(
            and_(
                NewsArticle.related_stocks.contains([symbol]),
                NewsArticle.published_at >= since_date,
                NewsArticle.sentiment_score.isnot(None)
            )
        ).order_by(NewsArticle.published_at.desc())
        
        articles = db.execute(query).scalars().all()
        
        if not articles:
            return {
                "symbol": symbol,
                "period_days": days,
                "sentiment_summary": {
                    "average_score": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "total_articles": 0
                },
                "daily_sentiment": []
            }
        
        # Calculate sentiment metrics
        positive_count = sum(1 for a in articles if a.sentiment_type == SentimentType.POSITIVE.value)
        negative_count = sum(1 for a in articles if a.sentiment_type == SentimentType.NEGATIVE.value)
        neutral_count = sum(1 for a in articles if a.sentiment_type == SentimentType.NEUTRAL.value)
        
        avg_score = sum(a.sentiment_score for a in articles if a.sentiment_score) / len(articles)
        
        # Group by day
        daily_sentiment = {}
        for article in articles:
            if article.published_at:
                day = article.published_at.date().isoformat()
                if day not in daily_sentiment:
                    daily_sentiment[day] = []
                daily_sentiment[day].append(article.sentiment_score)
        
        # Calculate daily averages
        daily_data = []
        for day, scores in daily_sentiment.items():
            avg_day_score = sum(score for score in scores if score is not None) / len(scores)
            daily_data.append({
                "date": day,
                "average_sentiment": avg_day_score,
                "article_count": len(scores)
            })
        
        daily_data.sort(key=lambda x: x["date"])
        
        return {
            "symbol": symbol,
            "period_days": days,
            "sentiment_summary": {
                "average_score": round(avg_score, 3),
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "total_articles": len(articles)
            },
            "daily_sentiment": daily_data,
            "recent_articles": [
                {
                    "title": article.title,
                    "sentiment_type": article.sentiment_type,
                    "sentiment_score": article.sentiment_score,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "url": article.url
                }
                for article in articles[:10]
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing sentiment: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
