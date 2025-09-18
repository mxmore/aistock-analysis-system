#!/usr/bin/env python3
"""
数据诊断脚本 - 检查个股数据报告相关的数据
"""
import sys
import os
from datetime import datetime, date, timedelta

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db import SessionLocal
from app.models import Watchlist, PriceDaily, Forecast, Signal, Report, Stock
from sqlalchemy import select, func, desc, and_

def check_database_data():
    """检查数据库中的数据情况"""
    print("🔍 诊断个股数据报告问题")
    print("=" * 60)
    
    with SessionLocal() as session:
        # 1. 检查监控列表
        print("\n1. 📋 监控列表检查")
        watchlist_count = session.scalar(select(func.count(Watchlist.symbol)))
        print(f"   监控股票数量: {watchlist_count}")
        
        if watchlist_count > 0:
            watchlist_symbols = session.execute(
                select(Watchlist.symbol, Watchlist.name)
                .limit(5)
            ).all()
            for symbol, name in watchlist_symbols:
                print(f"   - {symbol} ({name or '未知名称'})")
        
        # 2. 检查价格数据
        print("\n2. 💰 价格数据检查")
        price_count = session.scalar(select(func.count(PriceDaily.id)))
        print(f"   价格记录总数: {price_count}")
        
        if price_count > 0:
            # 获取最新价格数据
            latest_price = session.execute(
                select(PriceDaily.symbol, PriceDaily.trade_date, PriceDaily.close)
                .order_by(PriceDaily.trade_date.desc())
                .limit(5)
            ).all()
            print("   最新价格数据:")
            for symbol, trade_date, close in latest_price:
                print(f"   - {symbol}: {trade_date} 收盘价 {close}")
        
        # 3. 检查信号数据
        print("\n3. 📊 技术信号检查")
        signal_count = session.scalar(select(func.count(Signal.id)))
        print(f"   信号记录总数: {signal_count}")
        
        if signal_count > 0:
            latest_signals = session.execute(
                select(Signal.symbol, Signal.trade_date, Signal.action, Signal.signal_score)
                .order_by(Signal.trade_date.desc())
                .limit(5)
            ).all()
            print("   最新信号数据:")
            for symbol, trade_date, action, score in latest_signals:
                print(f"   - {symbol}: {trade_date} {action} 分数:{score}")
        
        # 4. 检查预测数据
        print("\n4. 🔮 预测数据检查")
        forecast_count = session.scalar(select(func.count(Forecast.id)))
        print(f"   预测记录总数: {forecast_count}")
        
        if forecast_count > 0:
            latest_forecasts = session.execute(
                select(Forecast.symbol, Forecast.target_date, Forecast.yhat)
                .order_by(Forecast.run_at.desc())
                .limit(5)
            ).all()
            print("   最新预测数据:")
            for symbol, target_date, yhat in latest_forecasts:
                print(f"   - {symbol}: {target_date} 预测价格 {yhat}")
        
        # 5. 检查报告数据
        print("\n5. 📋 报告数据检查")
        report_count = session.scalar(select(func.count(Report.id)))
        print(f"   报告记录总数: {report_count}")
        
        if report_count > 0:
            latest_reports = session.execute(
                select(Report.symbol, Report.version, Report.created_at, Report.is_latest)
                .order_by(Report.created_at.desc())
                .limit(5)
            ).all()
            print("   最新报告数据:")
            for symbol, version, created_at, is_latest in latest_reports:
                status = "最新" if is_latest else "历史"
                print(f"   - {symbol}: v{version} {created_at} ({status})")
        
        # 6. 按股票统计数据完整性
        print("\n6. 📈 按股票数据完整性统计")
        if watchlist_count > 0:
            for symbol, _ in watchlist_symbols:
                print(f"\n   📊 {symbol} 数据统计:")
                
                # 价格数据
                price_cnt = session.scalar(
                    select(func.count(PriceDaily.id))
                    .where(PriceDaily.symbol == symbol)
                )
                print(f"     价格记录: {price_cnt}")
                
                # 信号数据
                signal_cnt = session.scalar(
                    select(func.count(Signal.id))
                    .where(Signal.symbol == symbol)
                )
                print(f"     信号记录: {signal_cnt}")
                
                # 预测数据
                forecast_cnt = session.scalar(
                    select(func.count(Forecast.id))
                    .where(Forecast.symbol == symbol)
                )
                print(f"     预测记录: {forecast_cnt}")
                
                # 报告数据
                report_cnt = session.scalar(
                    select(func.count(Report.id))
                    .where(Report.symbol == symbol)
                )
                print(f"     报告记录: {report_cnt}")
                
                # 最新报告检查
                latest_report = session.execute(
                    select(Report)
                    .where(and_(Report.symbol == symbol, Report.is_latest == True))
                    .order_by(Report.created_at.desc())
                ).first()
                
                if latest_report:
                    report = latest_report[0]
                    print(f"     最新报告: v{report.version} ({report.created_at})")
                    if report.analysis_summary:
                        print(f"     摘要长度: {len(report.analysis_summary)} 字符")
                    else:
                        print(f"     ❌ 摘要为空")
                else:
                    print(f"     ❌ 无最新报告")
        
        print("\n" + "=" * 60)

def diagnose_report_issue():
    """诊断报告问题的具体原因"""
    print("\n🔧 诊断报告生成问题")
    print("=" * 60)
    
    with SessionLocal() as session:
        # 检查是否有数据但没有报告的股票
        watchlist_symbols = session.execute(
            select(Watchlist.symbol)
        ).scalars().all()
        
        for symbol in watchlist_symbols:
            print(f"\n🔍 检查 {symbol}:")
            
            # 检查各种数据是否存在
            has_price = session.scalar(
                select(func.count(PriceDaily.id))
                .where(PriceDaily.symbol == symbol)
            ) > 0
            
            has_signal = session.scalar(
                select(func.count(Signal.id))
                .where(Signal.symbol == symbol)
            ) > 0
            
            has_forecast = session.scalar(
                select(func.count(Forecast.id))
                .where(Forecast.symbol == symbol)
            ) > 0
            
            has_report = session.scalar(
                select(func.count(Report.id))
                .where(Report.symbol == symbol)
            ) > 0
            
            print(f"   价格数据: {'✅' if has_price else '❌'}")
            print(f"   信号数据: {'✅' if has_signal else '❌'}")
            print(f"   预测数据: {'✅' if has_forecast else '❌'}")
            print(f"   报告数据: {'✅' if has_report else '❌'}")
            
            # 如果有基础数据但没有报告，这可能是问题所在
            if (has_price or has_signal) and not has_report:
                print(f"   ⚠️  {symbol} 有基础数据但缺少报告")
            elif not (has_price or has_signal or has_forecast):
                print(f"   ❌ {symbol} 缺少所有基础数据")

def fix_reports():
    """修复缺失的报告"""
    print("\n🔧 开始修复缺失的报告")
    print("=" * 60)
    
    from app.report import generate_report_data
    
    with SessionLocal() as session:
        watchlist_symbols = session.execute(
            select(Watchlist.symbol)
        ).scalars().all()
        
        for symbol in watchlist_symbols:
            print(f"\n🔄 为 {symbol} 生成报告...")
            
            try:
                # 检查是否已有最新报告
                existing_report = session.execute(
                    select(Report)
                    .where(and_(Report.symbol == symbol, Report.is_latest == True))
                ).first()
                
                if existing_report:
                    print(f"   ✅ {symbol} 已有最新报告")
                    continue
                
                # 生成新报告
                import asyncio
                
                async def generate_report_async():
                    return await generate_report_data(symbol)
                
                try:
                    report_data = asyncio.run(generate_report_async())
                except Exception as gen_error:
                    print(f"   ❌ {symbol} 报告生成异常: {gen_error}")
                    continue
                
                if report_data:
                    print(f"   ✅ {symbol} 报告生成成功")
                else:
                    print(f"   ❌ {symbol} 报告生成失败")
                    
            except Exception as e:
                print(f"   ❌ {symbol} 报告生成异常: {e}")

def main():
    """主函数"""
    print("🩺 个股数据报告诊断工具")
    
    # 1. 检查数据库数据
    check_database_data()
    
    # 2. 诊断具体问题
    diagnose_report_issue()
    
    # 3. 提供修复建议
    print("\n💡 修复建议:")
    print("1. 如果缺少基础数据，请运行数据收集任务")
    print("2. 如果有基础数据但缺少报告，请运行报告生成任务")
    print("3. 检查数据源API是否正常工作")

if __name__ == "__main__":
    main()