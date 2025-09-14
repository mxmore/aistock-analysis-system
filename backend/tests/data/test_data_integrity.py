#!/usr/bin/env python3
"""
数据验证测试 - 检查系统核心数据的完整性
用于验证价格数据、信号、预测和报告数据的正确性
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db import SessionLocal
from app.models import Report, Stock, Task, PriceDaily, Signal, Forecast, Watchlist
from sqlalchemy import select, func
import json
from datetime import datetime, timedelta

def check_prices_data():
    """检查价格数据完整性"""
    print("🔍 检查价格数据...")
    session = SessionLocal()
    try:
        # 检查总记录数
        total_prices = session.execute(select(func.count(PriceDaily.id))).scalar()
        print(f"  总价格记录数: {total_prices}")
        
        # 检查最新数据日期
        latest_date = session.execute(
            select(func.max(PriceDaily.trade_date))
        ).scalar()
        print(f"  最新数据日期: {latest_date}")
        
        # 检查各股票数据量
        symbols_count = session.execute(
            select(PriceDaily.symbol, func.count(PriceDaily.id).label('count'))
            .group_by(PriceDaily.symbol)
            .order_by(func.count(PriceDaily.id).desc())
        ).all()
        
        print(f"  覆盖股票数: {len(symbols_count)}")
        for symbol, count in symbols_count[:5]:  # 显示前5个
            print(f"    {symbol}: {count} 条记录")
            
        return total_prices > 0
    finally:
        session.close()

def check_signals_data():
    """检查信号数据"""
    print("\n📊 检查信号数据...")
    session = SessionLocal()
    try:
        total_signals = session.execute(select(func.count(Signal.id))).scalar()
        print(f"  总信号记录数: {total_signals}")
        
        # 检查最新信号
        latest_signals = session.execute(
            select(Signal.symbol, Signal.trade_date, Signal.action)
            .order_by(Signal.trade_date.desc())
            .limit(5)
        ).all()
        
        print("  最新信号:")
        for symbol, date, action in latest_signals:
            print(f"    {symbol} - {date} - {action}")
            
        return total_signals > 0
    finally:
        session.close()

def check_forecasts_data():
    """检查预测数据"""
    print("\n🔮 检查预测数据...")
    session = SessionLocal()
    try:
        total_forecasts = session.execute(select(func.count(Forecast.id))).scalar()
        print(f"  总预测记录数: {total_forecasts}")
        
        # 检查最新预测
        latest_forecasts = session.execute(
            select(Forecast.symbol, Forecast.target_date, Forecast.yhat)
            .order_by(Forecast.run_at.desc())
            .limit(5)
        ).all()
        
        print("  最新预测:")
        for symbol, target_date, yhat in latest_forecasts:
            print(f"    {symbol} - {target_date} - {yhat:.2f}")
            
        return total_forecasts > 0
    finally:
        session.close()

def check_reports_data():
    """检查报告数据"""
    print("\n📋 检查报告数据...")
    session = SessionLocal()
    try:
        total_reports = session.execute(select(func.count(Report.id))).scalar()
        print(f"  总报告记录数: {total_reports}")
        
        # 检查最新报告
        latest_reports = session.execute(
            select(Report.symbol, Report.created_at, Report.is_latest)
            .where(Report.is_latest == True)
            .order_by(Report.created_at.desc())
        ).all()
        
        print(f"  当前有效报告数: {len(latest_reports)}")
        for symbol, created_at, is_latest in latest_reports[:3]:
            print(f"    {symbol} - {created_at}")
            
        return total_reports > 0
    finally:
        session.close()

def check_watchlist():
    """检查监控列表"""
    print("\n👀 检查监控列表...")
    session = SessionLocal()
    try:
        watchlist = session.execute(
            select(Watchlist).where(Watchlist.enabled == True)
        ).scalars().all()
        
        print(f"  启用的监控股票数: {len(watchlist)}")
        for w in watchlist:
            print(f"    {w.symbol} - {w.name}")
            
        return len(watchlist) > 0
    finally:
        session.close()

def main():
    """主测试函数"""
    print("🧪 股票系统数据完整性检查")
    print("=" * 50)
    
    results = []
    
    # 依次执行各项检查
    results.append(("价格数据", check_prices_data()))
    results.append(("信号数据", check_signals_data()))
    results.append(("预测数据", check_forecasts_data()))
    results.append(("报告数据", check_reports_data()))
    results.append(("监控列表", check_watchlist()))
    
    # 总结结果
    print("\n" + "=" * 50)
    print("📊 检查结果总结:")
    
    all_passed = True
    for name, passed in results:
        status = "✅ 正常" if passed else "❌ 异常"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n🎯 系统数据状态: {'✅ 健康' if all_passed else '❌ 需要检查'}")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)
