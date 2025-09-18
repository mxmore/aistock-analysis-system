import requests
import json

def test_api_endpoints():
    """测试API端点"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/api/dashboard/reports",
        "/api/watchlist",
        "/api/search/stocks?q=平安",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            print(f"\n🔗 测试端点: {endpoint}")
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 响应正常")
                if isinstance(data, dict):
                    print(f"响应字段: {list(data.keys())}")
                    if 'stocks' in data:
                        print(f"股票数量: {len(data['stocks'])}")
                        if data['stocks']:
                            stock = data['stocks'][0]
                            print(f"第一个股票: {stock.get('symbol', 'N/A')} - {stock.get('name', 'N/A')}")
                            if 'latest_report' in stock:
                                report = stock['latest_report']
                                if report and isinstance(report, dict):
                                    print(f"报告版本: {report.get('version', 'N/A')}")
                                    print(f"报告创建时间: {report.get('created_at', 'N/A')}")
                                    # 检查数据完整性
                                    data_fields = ['latest_price_data', 'signal_data', 'forecast_data']
                                    for field in data_fields:
                                        if field in report:
                                            if report[field]:
                                                print(f"✅ {field}: 有数据")
                                            else:
                                                print(f"❌ {field}: 无数据")
                                        else:
                                            print(f"❌ {field}: 字段不存在")
                                else:
                                    print("❌ 报告为空或格式错误")
                elif isinstance(data, list):
                    print(f"响应列表长度: {len(data)}")
            else:
                print(f"❌ 错误: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ 异常: {e}")

def test_specific_report():
    """测试特定股票报告"""
    symbol = "300251.SZ"
    url = f"http://localhost:8000/reports/{symbol}/latest"
    
    try:
        response = requests.get(url)
        print(f"\n📊 测试股票报告: {symbol}")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 报告获取成功")
            print(f"报告版本: {data.get('version', 'N/A')}")
            print(f"数据质量分数: {data.get('data_quality_score', 'N/A')}")
            print(f"分析摘要: {data.get('analysis_summary', 'N/A')}")
            
            # 检查各个数据字段
            if 'latest_price_data' in data and data['latest_price_data']:
                price_data = data['latest_price_data']
                print(f"✅ 价格数据: {price_data.get('close', 'N/A')} ({price_data.get('trade_date', 'N/A')})")
            else:
                print("❌ 价格数据缺失")
                
            if 'signal_data' in data and data['signal_data']:
                signal_data = data['signal_data']
                print(f"✅ 信号数据: {signal_data.get('action', 'N/A')} (评分: {signal_data.get('signal_score', 'N/A')})")
            else:
                print("❌ 信号数据缺失")
                
            if 'forecast_data' in data and data['forecast_data']:
                print(f"✅ 预测数据: {len(data['forecast_data'])} 个预测点")
            else:
                print("❌ 预测数据缺失")
        else:
            print(f"❌ 错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    print("🧪 测试API端点连通性")
    print("=" * 50)
    test_api_endpoints()
    test_specific_report()