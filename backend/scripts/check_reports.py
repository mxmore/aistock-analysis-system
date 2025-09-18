#!/usr/bin/env python3
"""
检查报告内容详情
"""
import sys
import os
import json

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db import SessionLocal
from app.models import Report
from sqlalchemy import select

def check_report_details():
    """检查报告详细内容"""
    print("🔍 检查报告详细内容")
    print("=" * 60)
    
    with SessionLocal() as session:
        reports = session.execute(
            select(Report)
            .where(Report.is_latest == True)
            .order_by(Report.symbol)
        ).scalars().all()
        
        for report in reports:
            print(f"\n📋 {report.symbol} 报告详情:")
            print(f"   版本: v{report.version}")
            print(f"   创建时间: {report.created_at}")
            print(f"   摘要: '{report.analysis_summary}'")
            print(f"   摘要长度: {len(report.analysis_summary) if report.analysis_summary else 0}")
            
            # 检查JSON数据
            if report.latest_price_data:
                try:
                    price_data = json.loads(report.latest_price_data)
                    print(f"   价格数据: ✅ (字段: {list(price_data.keys()) if isinstance(price_data, dict) else 'non-dict'})")
                except:
                    print(f"   价格数据: ❌ 无效JSON")
            else:
                print(f"   价格数据: ❌ 为空")
                
            if report.signal_data:
                try:
                    signal_data = json.loads(report.signal_data)
                    print(f"   信号数据: ✅ (字段: {list(signal_data.keys()) if isinstance(signal_data, dict) else 'non-dict'})")
                except:
                    print(f"   信号数据: ❌ 无效JSON")
            else:
                print(f"   信号数据: ❌ 为空")
                
            if report.forecast_data:
                try:
                    forecast_data = json.loads(report.forecast_data)
                    if isinstance(forecast_data, list):
                        print(f"   预测数据: ✅ (条目数: {len(forecast_data)})")
                    else:
                        print(f"   预测数据: ✅ (类型: {type(forecast_data)})")
                except:
                    print(f"   预测数据: ❌ 无效JSON")
            else:
                print(f"   预测数据: ❌ 为空")
            
            print(f"   数据质量分数: {report.data_quality_score}")
            print(f"   预测信心度: {report.prediction_confidence}")

if __name__ == "__main__":
    check_report_details()