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

# 数据模型
class StockSearchResult(BaseModel):
    symbol: str
    name: str
    code: str

class WatchlistItem(BaseModel):
    symbol: str
    name: str = None
    sector: str = None

class ReportResponse(BaseModel):
    symbol: str
    version: int
    created_at: str
    latest_price_data: dict = None
    signal_data: dict = None
    forecast_data: dict = None
    analysis_summary: str = None
    data_quality_score: float = None
    prediction_confidence: float = None

class TaskResponse(BaseModel):
    id: int
    task_type: str
    symbol: str
    status: str
    created_at: str
    priority: int

# API 路由
@app.get("/")
def read_root():
    return {"message": "AI Stock API is running", "version": "1.1"}

@app.get("/api/search", response_model=List[StockSearchResult])
def search_stock_endpoint(q: str = Query(..., min_length=1)):
    """搜索股票"""
    try:
        results = search_stocks(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/api/stock/{symbol}")
def get_stock_info_endpoint(symbol: str):
    """获取股票信息"""
    try:
        stock_info = get_stock_info(symbol)
        if not stock_info:
            raise HTTPException(status_code=404, detail="Stock not found")
        return stock_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/realtime/{symbol}")
def get_realtime_stock_endpoint(symbol: str):
    """获取实时股票数据"""
    try:
        realtime_data = get_realtime_stock(symbol)
        if not realtime_data:
            raise HTTPException(status_code=404, detail="Realtime data not found")
        return realtime_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/watchlist")
def add_to_watchlist(item: WatchlistItem, db: Session = Depends(get_db)):
    """添加股票到监控列表"""
    try:
        # 检查是否已存在
        existing = db.execute(
            select(Watchlist).where(Watchlist.symbol == item.symbol)
        ).scalar_one_or_none()
        
        if existing:
            return {"message": "Stock already in watchlist", "symbol": item.symbol}
        
        # 添加到数据库
        watchlist_item = Watchlist(
            symbol=item.symbol,
            name=item.name,
            sector=item.sector
        )
        db.add(watchlist_item)
        db.commit()
        
        # 创建报告生成任务
        task_manager.create_task(
            task_type=TaskType.GENERATE_REPORT,
            symbol=item.symbol,
            priority=3
        )
        
        return {"message": "Stock added to watchlist", "symbol": item.symbol}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/watchlist", response_model=List[WatchlistItem])
def get_watchlist(db: Session = Depends(get_db)):
    """获取监控列表"""
    try:
        watchlist = db.execute(
            select(Watchlist).where(Watchlist.enabled == True)
        ).scalars().all()
        
        return [
            WatchlistItem(
                symbol=item.symbol,
                name=item.name,
                sector=item.sector
            )
            for item in watchlist
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/api/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    """从监控列表移除股票"""
    try:
        item = db.execute(
            select(Watchlist).where(Watchlist.symbol == symbol)
        ).scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=404, detail="Stock not found in watchlist")
        
        db.delete(item)
        db.commit()
        
        return {"message": "Stock removed from watchlist", "symbol": symbol}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/report/{symbol}")
def get_report(symbol: str, version: Optional[int] = None, db: Session = Depends(get_db)):
    """获取股票报告"""
    try:
        if version:
            # 获取指定版本
            report = db.execute(
                select(Report).where(
                    and_(Report.symbol == symbol, Report.version == version)
                )
            ).scalar_one_or_none()
        else:
            # 获取最新版本
            report = db.execute(
                select(Report).where(
                    and_(Report.symbol == symbol, Report.is_latest == True)
                )
            ).scalar_one_or_none()
        
        if not report:
            # 如果没有报告，创建生成任务
            task_manager.create_task(
                task_type=TaskType.GENERATE_REPORT,
                symbol=symbol,
                priority=1  # 高优先级
            )
            raise HTTPException(status_code=404, detail="Report not found, generation task created")
        
        return ReportResponse(
            symbol=report.symbol,
            version=report.version,
            created_at=report.created_at.isoformat(),
            latest_price_data=json.loads(report.latest_price_data) if report.latest_price_data else None,
            signal_data=json.loads(report.signal_data) if report.signal_data else None,
            forecast_data=json.loads(report.forecast_data) if report.forecast_data else None,
            analysis_summary=report.analysis_summary,
            data_quality_score=float(report.data_quality_score) if report.data_quality_score else None,
            prediction_confidence=float(report.prediction_confidence) if report.prediction_confidence else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/reports/{symbol}")
def list_reports(symbol: str, db: Session = Depends(get_db)):
    """列出股票的所有报告版本"""
    try:
        reports = db.execute(
            select(Report).where(Report.symbol == symbol).order_by(Report.version.desc())
        ).scalars().all()
        
        return [
            {
                "version": report.version,
                "created_at": report.created_at.isoformat(),
                "is_latest": report.is_latest,
                "data_quality_score": float(report.data_quality_score) if report.data_quality_score else None,
                "prediction_confidence": float(report.prediction_confidence) if report.prediction_confidence else None
            }
            for report in reports
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# 任务管理 API
@app.get("/api/tasks", response_model=List[TaskResponse])
def list_tasks(status: Optional[str] = None, symbol: Optional[str] = None, db: Session = Depends(get_db)):
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
            TaskResponse(
                id=task.id,
                task_type=task.task_type,
                symbol=task.symbol,
                status=task.status,
                created_at=task.created_at.isoformat(),
                priority=task.priority
            )
            for task in tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/tasks/report/{symbol}")
def create_report_task(symbol: str, priority: int = 5):
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

@app.get("/api/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情"""
    try:
        task = db.execute(
            select(Task).where(Task.id == task_id)
        ).scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "id": task.id,
            "task_type": task.task_type,
            "symbol": task.symbol,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "priority": task.priority,
            "task_metadata": json.loads(task.task_metadata) if task.task_metadata else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/api/tasks/{task_id}")
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """取消任务"""
    try:
        task = db.execute(
            select(Task).where(Task.id == task_id)
        ).scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed or failed task")
        
        task.status = TaskStatus.FAILED
        task.error_message = "Task cancelled by user"
        db.commit()
        
        return {"message": "Task cancelled", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/system/status")
def get_system_status():
    """获取系统状态"""
    return {
        "status": "running",
        "version": "1.1",
        "task_manager_running": not task_manager.is_stopped(),
        "database_connected": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
