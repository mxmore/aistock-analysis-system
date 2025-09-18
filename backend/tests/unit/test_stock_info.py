#!/usr/bin/env python3
"""
股票信息获取功能的单元测试
"""
import sys
import os
import unittest

# Add the backend directory to the path
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, backend_root)

from app.data_source import get_stock_info


class TestStockInfo(unittest.TestCase):
    """股票信息测试类"""
    
    def test_get_stock_info_valid_symbol(self):
        """测试获取有效股票代码的信息"""
        symbol = "300251.SZ"
        stock_info = get_stock_info(symbol)
        
        self.assertIsNotNone(stock_info, "股票信息不应该为空")
        self.assertIsInstance(stock_info, dict, "股票信息应该是字典类型")
        
        # 检查必要字段
        if stock_info:
            self.assertIn('name', stock_info, "股票信息应包含名称")
            self.assertIn('code', stock_info, "股票信息应包含代码")
            self.assertIn('symbol', stock_info, "股票信息应包含符号")
    
    def test_get_stock_info_invalid_symbol(self):
        """测试获取无效股票代码的信息"""
        symbol = "INVALID.XX"
        stock_info = get_stock_info(symbol)
        
        # 根据实际实现，可能返回None或空字典
        if stock_info is not None:
            self.assertIsInstance(stock_info, dict, "返回值应该是字典或None")
    
    def test_get_stock_info_empty_symbol(self):
        """测试空股票代码"""
        symbol = ""
        stock_info = get_stock_info(symbol)
        
        # 应该处理空输入
        if stock_info is not None:
            self.assertIsInstance(stock_info, dict, "返回值应该是字典或None")


def test_stock_info_manual():
    """手动测试函数，用于调试"""
    symbol = "300251.SZ"
    print(f"🔍 测试获取股票信息: {symbol}")
    
    try:
        stock_info = get_stock_info(symbol)
        print(f"📊 结果: {stock_info}")
        
        if stock_info:
            print(f"✅ 股票名称: {stock_info.get('name')}")
            print(f"✅ 股票代码: {stock_info.get('code')}")
            print(f"✅ 股票符号: {stock_info.get('symbol')}")
        else:
            print("❌ 未找到股票信息")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='股票信息测试')
    parser.add_argument('--manual', action='store_true', help='运行手动测试')
    args = parser.parse_args()
    
    if args.manual:
        test_stock_info_manual()
    else:
        unittest.main()