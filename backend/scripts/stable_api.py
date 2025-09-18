#!/usr/bin/env python3
"""
稳定的API服务器 - 处理CORS和异常
"""
import sys
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import traceback
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db import SessionLocal
from app.models import Report, Watchlist
from sqlalchemy import select, and_, text

def create_stable_api():
    """创建稳定的API应用"""
    app = FastAPI(title="Stable Stock API", version="1.0")
    
    # CORS middleware - 更宽松的配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {"message": "Stable Stock API is running", "status": "ok", "timestamp": "2025-09-18T15:00:00Z"}
    
    @app.get("/health")
    async def health():
        try:
            # 测试数据库连接
            with SessionLocal() as session:
                count = session.execute(text("SELECT COUNT(*) FROM watchlist")).scalar()
            return {"status": "healthy", "database": "connected", "stocks": count}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    @app.get("/watchlist")
    async def get_watchlist():
        """获取监控列表 - 返回数组格式"""
        try:
            logger.info("获取监控列表...")
            
            with SessionLocal() as session:
                # 获取所有启用的股票
                watchlist = session.execute(
                    select(Watchlist).where(Watchlist.enabled == True)
                ).scalars().all()
                
                stocks = []
                for stock in watchlist:
                    stocks.append({
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "sector": stock.sector,
                        "enabled": stock.enabled
                    })
                
                logger.info(f"返回 {len(stocks)} 个监控股票")
                # 返回数组格式，不是对象格式
                return stocks
                
        except Exception as e:
            logger.error(f"获取监控列表错误: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    @app.get("/api/dashboard/reports")
    async def get_dashboard_reports():
        """获取dashboard数据 - 带完整异常处理"""
        try:
            logger.info("开始处理dashboard请求...")
            
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
                
                logger.info("执行数据库查询...")
                result = session.execute(text(query)).fetchall()
                logger.info(f"查询返回 {len(result)} 条记录")
                
                stocks = []
                for i, row in enumerate(result):
                    try:
                        logger.info(f"处理第 {i+1} 个股票: {row.symbol}")
                        
                        # 解析JSON数据
                        latest_price_data = None
                        signal_data = None
                        forecast_data = None
                        
                        if row.latest_price_data:
                            try:
                                latest_price_data = json.loads(row.latest_price_data)
                                logger.info(f"  价格数据解析成功: {latest_price_data.get('close', 'N/A')}")
                            except Exception as e:
                                logger.error(f"  价格数据解析失败: {e}")
                        
                        if row.signal_data:
                            try:
                                signal_data = json.loads(row.signal_data)
                                logger.info(f"  信号数据解析成功: {signal_data.get('action', 'N/A')}")
                            except Exception as e:
                                logger.error(f"  信号数据解析失败: {e}")
                        
                        if row.forecast_data:
                            try:
                                forecast_data = json.loads(row.forecast_data)
                                if isinstance(forecast_data, list):
                                    logger.info(f"  预测数据解析成功: {len(forecast_data)} 个预测点")
                                else:
                                    logger.info(f"  预测数据类型: {type(forecast_data)}")
                            except Exception as e:
                                logger.error(f"  预测数据解析失败: {e}")
                        
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
                        
                    except Exception as e:
                        logger.error(f"处理股票 {row.symbol} 时出错: {e}")
                        # 继续处理其他股票
                        continue
                
                response_data = {
                    "stocks": stocks,
                    "summary": {
                        "total_stocks": len(stocks),
                        "with_reports": len([s for s in stocks if s["latest_report"]]),
                        "without_reports": len([s for s in stocks if not s["latest_report"]])
                    }
                }
                
                logger.info(f"成功生成响应: {len(stocks)} 个股票")
                return response_data
                
        except Exception as e:
            logger.error(f"Dashboard API错误: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    @app.get("/api/report/{symbol}/latest")
    async def get_latest_report(symbol: str):
        """获取特定股票的最新报告"""
        try:
            logger.info(f"获取股票 {symbol} 的最新报告...")
            
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
                    except Exception as e:
                        logger.error(f"价格数据解析失败: {e}")
                
                if report.signal_data:
                    try:
                        signal_data = json.loads(report.signal_data)
                    except Exception as e:
                        logger.error(f"信号数据解析失败: {e}")
                
                if report.forecast_data:
                    try:
                        forecast_data = json.loads(report.forecast_data)
                    except Exception as e:
                        logger.error(f"预测数据解析失败: {e}")
                
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
            logger.error(f"获取报告错误: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    @app.get("/api/report/{symbol}/full")
    async def get_full_report(symbol: str, timeRange: str = Query('5d', description="时间区间: 5d, 1m, 3m, 6m, 1y, all")):
        """获取完整的股票报告 - 前端兼容格式"""
        try:
            logger.info(f"获取股票 {symbol} 的完整报告，时间区间: {timeRange}...")
            
            # 根据时间区间确定需要获取的数据天数
            if timeRange == '5d':
                limit_days = 5
            elif timeRange == '1m':
                limit_days = 30
            elif timeRange == '3m':
                limit_days = 90
            elif timeRange == '6m':
                limit_days = 180
            elif timeRange == '1y':
                limit_days = 365
            else:  # 'all'
                limit_days = 1000  # 获取所有可用数据
            
            with SessionLocal() as session:
                # 获取最新报告
                report = session.execute(
                    select(Report).where(
                        and_(Report.symbol == symbol.upper(), Report.is_latest == True)
                    ).order_by(Report.created_at.desc())
                ).scalar_one_or_none()
                
                if not report:
                    raise HTTPException(status_code=404, detail=f"No report found for {symbol}")
                
                # 根据时间区间获取历史价格数据
                if timeRange == 'all':
                    # 获取所有可用数据
                    historical_prices = session.execute(
                        text(
                            "SELECT trade_date, open, high, low, close, vol, pct_chg "
                            "FROM prices_daily WHERE symbol=:sym "
                            "ORDER BY trade_date DESC"
                        ),
                        {"sym": symbol.upper()}
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
                        {"sym": symbol.upper()}
                    ).mappings().all()
                
                # 解析JSON数据
                latest_price_data = None
                signal_data = None
                forecast_data = None
                
                if report.latest_price_data:
                    try:
                        latest_price_data = json.loads(report.latest_price_data)
                    except Exception as e:
                        logger.error(f"价格数据解析失败: {e}")
                
                if report.signal_data:
                    try:
                        signal_data = json.loads(report.signal_data)
                    except Exception as e:
                        logger.error(f"信号数据解析失败: {e}")
                
                if report.forecast_data:
                    try:
                        forecast_data = json.loads(report.forecast_data)
                    except Exception as e:
                        logger.error(f"预测数据解析失败: {e}")
                
                # 转换历史价格数据为前端期望的格式
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
                
                # 转换预测数据为前端期望的格式
                predictions = []
                if forecast_data and isinstance(forecast_data, list):
                    from datetime import datetime, timedelta
                    last_date = historical_prices[0]["trade_date"] if historical_prices else datetime.now().date()
                    
                    for i, pred in enumerate(forecast_data[:10]):  # 只取前10个预测点
                        # 计算预测日期（跳过周末）
                        target_date = last_date + timedelta(days=i+1)
                        while target_date.weekday() >= 5:  # 跳过周末
                            target_date += timedelta(days=1)
                        
                        predictions.append({
                            "date": target_date.isoformat(),
                            "predicted_price": pred.get("yhat", 0),
                            "upper_bound": pred.get("yhat_upper", 0),
                            "lower_bound": pred.get("yhat_lower", 0),
                            "type": "prediction"
                        })
                
                # 构建前端期望的响应格式
                response = {
                    "symbol": symbol.upper(),
                    "data_updated": report.created_at.isoformat() if report.created_at else None,
                    "data_quality_score": float(report.data_quality_score) if report.data_quality_score else 0.0,
                    "prediction_confidence": float(report.prediction_confidence) if report.prediction_confidence else 0.0,
                    "analysis_summary": report.analysis_summary,
                    
                    # 价格数据（过去和预测）
                    "price_data": price_data,
                    "predictions": predictions,
                    
                    # 前端兼容的格式
                    "dates": [p["date"] for p in predictions],
                    "predictions_mean": [p["predicted_price"] for p in predictions],
                    "predictions_upper": [p["upper_bound"] for p in predictions],
                    "predictions_lower": [p["lower_bound"] for p in predictions],
                    
                    # 最新价格和信号
                    "latest_price": price_data[-1] if price_data else latest_price_data,
                    "signal": signal_data,
                    
                    # 向后兼容
                    "latest": latest_price_data,
                    "forecast": forecast_data
                }
                
                logger.info(f"成功生成完整报告: {len(price_data)} 个历史价格, {len(predictions)} 个预测点")
                return response
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取完整报告错误: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return app

if __name__ == "__main__":
    app = create_stable_api()
    print("🚀 启动稳定的API服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8083, log_level="info", access_log=True)