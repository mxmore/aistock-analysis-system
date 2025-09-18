#!/usr/bin/env python3
"""
简单的报告API测试脚本
"""
import sys
import os
import json

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db import SessionLocal
from app.models import Report
from sqlalchemy import select, and_

def test_report_api():
    """测试报告API数据"""
    print("🧪 测试个股报告API数据")
    print("=" * 60)
    
    with SessionLocal() as session:
        # 测试一个具体股票的报告
        symbol = "300251.SZ"
        
        print(f"📊 测试股票: {symbol}")
        
        # 查找最新报告
        report = session.execute(
            select(Report).where(
                and_(Report.symbol == symbol, Report.is_latest == True)
            ).order_by(Report.created_at.desc())
        ).scalar_one_or_none()
        
        if report:
            print(f"✅ 找到最新报告 v{report.version}")
            
            # 模拟API响应
            result = {
                "symbol": symbol,
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
                print(f"✅ 价格数据: {result['latest']}")
            
            if report.signal_data:
                result["signal"] = json.loads(report.signal_data)
                print(f"✅ 信号数据: {result['signal']}")
            
            if report.forecast_data:
                result["forecast"] = json.loads(report.forecast_data)
                forecast_count = len(result["forecast"]) if isinstance(result["forecast"], list) else "1项"
                print(f"✅ 预测数据: {forecast_count}")
            
            print(f"\n📋 完整API响应示例:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        else:
            print(f"❌ 未找到 {symbol} 的报告")

if __name__ == "__main__":
    test_report_api()