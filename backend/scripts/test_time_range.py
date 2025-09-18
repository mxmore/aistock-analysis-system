#!/usr/bin/env python3
"""
测试时间区间查询逻辑
"""
import sys
sys.path.append('.')
from app.db import SessionLocal
from sqlalchemy import text

def test_time_range_query(symbol, timeRange):
    print(f"\n=== 测试 {symbol} 的 {timeRange} 时间区间 ===")
    
    with SessionLocal() as session:
        if timeRange == 'all':
            # 获取所有可用数据
            result = session.execute(
                text(
                    "SELECT trade_date, close "
                    "FROM prices_daily WHERE symbol=:sym "
                    "ORDER BY trade_date DESC"
                ),
                {"sym": symbol}
            ).fetchall()
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
            
            result = session.execute(
                text(
                    "SELECT trade_date, close "
                    "FROM prices_daily WHERE symbol=:sym "
                    "AND trade_date >= CURRENT_DATE - INTERVAL '{} days' "
                    "ORDER BY trade_date DESC".format(days_back)
                ),
                {"sym": symbol}
            ).fetchall()
        
        print(f"返回 {len(result)} 条记录")
        if result:
            print(f"最新日期: {result[0][0]}")
            print(f"最早日期: {result[-1][0]}")
            print("前5条记录:")
            for i, row in enumerate(result[:5]):
                print(f"  {row[0]}: {row[1]}")

if __name__ == "__main__":
    symbol = "300251.SZ"
    for timeRange in ['5d', '1m', '3m', '6m', '1y', 'all']:
        test_time_range_query(symbol, timeRange)