#!/usr/bin/env python3
"""
修复个股数据报告 - 重新生成所有报告
"""
import sys
import os
import asyncio

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db import SessionLocal
from app.models import Watchlist, Report
from app.task_manager import TaskManager
from sqlalchemy import select, and_

async def fix_all_reports():
    """修复所有股票的报告"""
    print("🔧 开始修复个股数据报告")
    print("=" * 60)
    
    # 创建任务管理器
    task_manager = TaskManager()
    
    with SessionLocal() as session:
        # 获取所有监控的股票
        watchlist_symbols = session.execute(
            select(Watchlist.symbol)
            .where(Watchlist.enabled == True)
        ).scalars().all()
        
        print(f"📋 发现 {len(watchlist_symbols)} 只股票需要修复报告")
        
        for symbol in watchlist_symbols:
            print(f"\n🔄 修复 {symbol} 的报告...")
            
            try:
                # 删除旧报告（可选）
                # print(f"   🗑️  删除旧报告...")
                # session.execute(
                #     delete(Report).where(Report.symbol == symbol)
                # )
                # session.commit()
                
                # 标记所有旧报告为非最新
                session.execute(
                    Report.__table__.update()
                    .where(and_(Report.symbol == symbol, Report.is_latest == True))
                    .values(is_latest=False)
                )
                session.commit()
                
                # 重新生成报告
                success = await task_manager._generate_report(symbol, session)
                
                if success:
                    print(f"   ✅ {symbol} 报告修复成功")
                else:
                    print(f"   ❌ {symbol} 报告修复失败")
                    
            except Exception as e:
                print(f"   ❌ {symbol} 报告修复异常: {e}")
                session.rollback()

async def verify_reports():
    """验证修复后的报告"""
    print("\n🔍 验证修复后的报告")
    print("=" * 60)
    
    with SessionLocal() as session:
        reports = session.execute(
            select(Report)
            .where(Report.is_latest == True)
            .order_by(Report.symbol)
        ).scalars().all()
        
        for report in reports:
            print(f"\n📋 {report.symbol} 验证结果:")
            
            # 检查价格数据
            if report.latest_price_data:
                print(f"   ✅ 价格数据: 有")
            else:
                print(f"   ❌ 价格数据: 无")
            
            # 检查信号数据  
            if report.signal_data:
                print(f"   ✅ 信号数据: 有")
            else:
                print(f"   ❌ 信号数据: 无")
            
            # 检查预测数据
            if report.forecast_data:
                print(f"   ✅ 预测数据: 有")
            else:
                print(f"   ❌ 预测数据: 无")
            
            # 检查摘要
            summary_len = len(report.analysis_summary) if report.analysis_summary else 0
            if summary_len > 30:
                print(f"   ✅ 分析摘要: {summary_len} 字符")
            else:
                print(f"   ⚠️  分析摘要: {summary_len} 字符 (太短)")
            
            print(f"   📊 数据质量: {report.data_quality_score}")
            print(f"   🎯 预测信心: {report.prediction_confidence}")

async def main():
    """主函数"""
    print("🩺 个股数据报告修复工具")
    
    # 1. 修复所有报告
    await fix_all_reports()
    
    # 2. 验证修复结果
    await verify_reports()
    
    print("\n✅ 报告修复完成！")

if __name__ == "__main__":
    asyncio.run(main())