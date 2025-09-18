#!/usr/bin/env python3
"""
简化的API测试脚本
"""
import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def create_test_app():
    """创建测试API应用"""
    app = FastAPI(title="Stock API Test", version="1.0")
    
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
        return {"message": "Stock API is running", "status": "ok"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "message": "All systems operational"}
    
    @app.get("/api/dashboard/reports")
    async def get_dashboard_reports():
        """返回模拟的dashboard数据"""
        return {
            "stocks": [
                {
                    "symbol": "300251.SZ",
                    "name": "光线传媒",
                    "latest_report": {
                        "version": 2,
                        "created_at": "2025-09-18T07:01:08.951361",
                        "data_quality_score": 11.0,
                        "prediction_confidence": 0.901,
                        "analysis_summary": "最新收盘价 18.83，下跌 1.31% | 技术信号：BUY | 信号评分：15.0 | 短期预测：18.48",
                        "latest_price_data": {
                            "trade_date": "2025-09-18",
                            "close": 18.83,
                            "open": 19.01,
                            "high": 19.07,
                            "low": 18.82,
                            "pct_chg": -1.31,
                            "vol": 385984
                        },
                        "signal_data": {
                            "trade_date": "2025-09-18",
                            "ma_short": 19.085,
                            "ma_long": 19.5297,
                            "rsi": 42.9272,
                            "macd": -0.2085,
                            "signal_score": 15.0,
                            "action": "BUY"
                        }
                    }
                },
                {
                    "symbol": "000829.SZ",
                    "name": "天音控股",
                    "latest_report": {
                        "version": 2,
                        "created_at": "2025-09-18T07:01:09.025128",
                        "analysis_summary": "数据已修复，包含完整信息"
                    }
                }
            ],
            "summary": {
                "total_stocks": 2,
                "with_reports": 2,
                "without_reports": 0
            }
        }
    
    return app

if __name__ == "__main__":
    app = create_test_app()
    print("🚀 启动测试API服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info")