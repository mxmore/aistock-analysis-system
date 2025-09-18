#!/usr/bin/env python3
"""
直接使用数据库的测试API
"""
import sys
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db import SessionLocal
from app.models import Report, Watchlist
from sqlalchemy import select, and_, text

def create_real_api():
    """创建使用真实数据的API应用"""
    app = FastAPI(title="Real Stock API", version="1.0")
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {"message": "Real Stock API is running", "status": "ok"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "message": "All systems operational"}
    
    @app.get("/api/dashboard/reports")
    async def get_dashboard_reports():
        """获取真实的dashboard数据"""
        try:
            with SessionLocal() as session:
                # 获取所有启用的股票和最新报告
                query = """
                SELECT 
                    w.symbol,
                    w.name,
                    w.sector,
                    r.version,
                    r.created_at,
                    r.data_quality_score,
                    r.prediction_confidence,
                    r.analysis_summary,
                    r.latest_price_data,
                    r.signal_data,
                    r.forecast_data
                FROM watchlist w
                LEFT JOIN reports r ON w.symbol = r.symbol AND r.is_latest = true
                WHERE w.enabled = true
                ORDER BY w.symbol
                """
                
                result = session.execute(text(query)).fetchall()
                
                stocks = []
                for row in result:
                    # 解析JSON数据
                    latest_price_data = None
                    signal_data = None
                    forecast_data = None
                    
                    if row.latest_price_data:
                        try:
                            latest_price_data = json.loads(row.latest_price_data)
                        except:
                            pass
                    
                    if row.signal_data:
                        try:
                            signal_data = json.loads(row.signal_data)
                        except:
                            pass
                    
                    if row.forecast_data:
                        try:
                            forecast_data = json.loads(row.forecast_data)
                        except:
                            pass
                    
                    stock_data = {
                        "symbol": row.symbol,
                        "name": row.name,
                        "sector": row.sector or "",
                        "latest_report": None
                    }
                    
                    if row.version:
                        stock_data["latest_report"] = {
                            "version": row.version,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "data_quality_score": float(row.data_quality_score) if row.data_quality_score else 0.0,
                            "prediction_confidence": float(row.prediction_confidence) if row.prediction_confidence else 0.0,
                            "analysis_summary": row.analysis_summary,
                            "latest_price_data": latest_price_data,
                            "signal_data": signal_data,
                            "forecast_data": forecast_data
                        }
                    
                    stocks.append(stock_data)
                
                return {
                    "stocks": stocks,
                    "summary": {
                        "total_stocks": len(stocks),
                        "with_reports": len([s for s in stocks if s["latest_report"]]),
                        "without_reports": len([s for s in stocks if not s["latest_report"]])
                    }
                }
                
        except Exception as e:
            print(f"数据库错误: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    @app.get("/api/report/{symbol}/latest")
    async def get_latest_report(symbol: str):
        """获取特定股票的最新报告"""
        try:
            with SessionLocal() as session:
                report = session.execute(
                    select(Report).where(
                        and_(Report.symbol == symbol.upper(), Report.is_latest == True)
                    ).order_by(Report.created_at.desc())
                ).scalar_one_or_none()
                
                if not report:
                    raise HTTPException(status_code=404, detail=f"No report found for {symbol}")
                
                # 解析JSON数据
                latest_price_data = None
                signal_data = None
                forecast_data = None
                
                if report.latest_price_data:
                    try:
                        latest_price_data = json.loads(report.latest_price_data)
                    except:
                        pass
                
                if report.signal_data:
                    try:
                        signal_data = json.loads(report.signal_data)
                    except:
                        pass
                
                if report.forecast_data:
                    try:
                        forecast_data = json.loads(report.forecast_data)
                    except:
                        pass
                
                return {
                    "symbol": report.symbol,
                    "version": report.version,
                    "created_at": report.created_at.isoformat(),
                    "is_latest": report.is_latest,
                    "data_quality_score": float(report.data_quality_score) if report.data_quality_score else 0.0,
                    "prediction_confidence": float(report.prediction_confidence) if report.prediction_confidence else 0.0,
                    "analysis_summary": report.analysis_summary,
                    "latest_price_data": latest_price_data,
                    "signal_data": signal_data,
                    "forecast_data": forecast_data
                }
                
        except HTTPException:
            raise
        except Exception as e:
            print(f"数据库错误: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return app

if __name__ == "__main__":
    app = create_real_api()
    print("🚀 启动真实数据API服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="info")