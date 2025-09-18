#!/usr/bin/env python3
"""
诊断API问题的测试脚本
"""
import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def test_database_connection():
    """测试数据库连接"""
    try:
        from app.db import SessionLocal
        from app.models import Report, Watchlist
        from sqlalchemy import select, and_, text
        import json
        
        print("🔌 测试数据库连接...")
        
        with SessionLocal() as session:
            # 测试基本查询
            watchlist_count = session.execute(text("SELECT COUNT(*) FROM watchlist WHERE enabled = true")).scalar()
            print(f"✅ 启用的股票数量: {watchlist_count}")
            
            # 测试报告查询
            reports_count = session.execute(text("SELECT COUNT(*) FROM reports WHERE is_latest = true")).scalar()
            print(f"✅ 最新报告数量: {reports_count}")
            
            # 获取一个具体的报告示例
            result = session.execute(text("""
                SELECT 
                    w.symbol,
                    w.name,
                    r.version,
                    r.created_at,
                    r.analysis_summary,
                    r.latest_price_data,
                    r.signal_data,
                    r.forecast_data
                FROM watchlist w
                LEFT JOIN reports r ON w.symbol = r.symbol AND r.is_latest = true
                WHERE w.enabled = true
                LIMIT 1
            """)).fetchone()
            
            if result:
                print(f"✅ 示例股票: {result.symbol} - {result.name}")
                print(f"   报告版本: {result.version}")
                print(f"   分析摘要: {result.analysis_summary}")
                
                # 检查JSON数据
                if result.latest_price_data:
                    try:
                        price_data = json.loads(result.latest_price_data)
                        print(f"   ✅ 价格数据: {price_data.get('close', 'N/A')}")
                    except Exception as e:
                        print(f"   ❌ 价格数据解析失败: {e}")
                else:
                    print("   ❌ 无价格数据")
                
                if result.signal_data:
                    try:
                        signal_data = json.loads(result.signal_data)
                        print(f"   ✅ 信号数据: {signal_data.get('action', 'N/A')}")
                    except Exception as e:
                        print(f"   ❌ 信号数据解析失败: {e}")
                else:
                    print("   ❌ 无信号数据")
                
                if result.forecast_data:
                    try:
                        forecast_data = json.loads(result.forecast_data)
                        if isinstance(forecast_data, list):
                            print(f"   ✅ 预测数据: {len(forecast_data)} 个预测点")
                        else:
                            print(f"   ✅ 预测数据: {type(forecast_data)}")
                    except Exception as e:
                        print(f"   ❌ 预测数据解析失败: {e}")
                else:
                    print("   ❌ 无预测数据")
            else:
                print("❌ 没有找到任何股票数据")
                
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        import traceback
        traceback.print_exc()

def test_api_response():
    """测试API响应生成"""
    try:
        from app.db import SessionLocal
        from sqlalchemy import text
        import json
        
        print("\n🔧 测试API响应生成...")
        
        with SessionLocal() as session:
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
            LIMIT 3
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
                    except Exception as e:
                        print(f"价格数据解析错误: {e}")
                
                if row.signal_data:
                    try:
                        signal_data = json.loads(row.signal_data)
                    except Exception as e:
                        print(f"信号数据解析错误: {e}")
                
                if row.forecast_data:
                    try:
                        forecast_data = json.loads(row.forecast_data)
                    except Exception as e:
                        print(f"预测数据解析错误: {e}")
                
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
            
            response_data = {
                "stocks": stocks,
                "summary": {
                    "total_stocks": len(stocks),
                    "with_reports": len([s for s in stocks if s["latest_report"]]),
                    "without_reports": len([s for s in stocks if not s["latest_report"]])
                }
            }
            
            print(f"✅ 成功生成响应数据:")
            print(f"   总股票数: {response_data['summary']['total_stocks']}")
            print(f"   有报告的股票: {response_data['summary']['with_reports']}")
            print(f"   无报告的股票: {response_data['summary']['without_reports']}")
            
            # 显示第一个股票的详细信息
            if stocks and stocks[0]['latest_report']:
                report = stocks[0]['latest_report']
                print(f"\n   第一个股票 {stocks[0]['symbol']} 的报告数据:")
                print(f"   - 价格数据: {'有' if report['latest_price_data'] else '无'}")
                print(f"   - 信号数据: {'有' if report['signal_data'] else '无'}")
                print(f"   - 预测数据: {'有' if report['forecast_data'] else '无'}")
                
                if report['latest_price_data']:
                    print(f"   - 最新价格: {report['latest_price_data'].get('close', 'N/A')}")
                if report['signal_data']:
                    print(f"   - 交易信号: {report['signal_data'].get('action', 'N/A')}")
                if report['forecast_data'] and isinstance(report['forecast_data'], list):
                    print(f"   - 预测点数: {len(report['forecast_data'])}")
            
            return response_data
            
    except Exception as e:
        print(f"❌ API响应生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🧪 诊断API和数据库问题")
    print("=" * 50)
    
    test_database_connection()
    response = test_api_response()
    
    if response:
        print(f"\n✅ 诊断完成：数据库和API响应都正常")
    else:
        print(f"\n❌ 诊断失败：存在问题需要修复")