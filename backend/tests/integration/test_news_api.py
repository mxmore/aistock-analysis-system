import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, backend_root)

from app.news_service import NewsSearchService, NewsProcessor
from app.data_source import get_stock_info

async def test_news_search():
    """测试新闻搜索功能"""
    
    symbol = "300251.SZ"
    
    # 1. 测试股票信息获取
    print("1. 获取股票信息...")
    stock_info = get_stock_info(symbol)
    print(f"股票信息: {stock_info}")
    
    # 2. 测试新闻搜索
    print("\n2. 搜索新闻...")
    news_search_service = NewsSearchService()
    
    try:
        results = await news_search_service.search_stock_news(
            symbol=symbol,
            company_name=stock_info.get('name')
        )
        print(f"搜索结果数量: {len(results)}")
        
        for i, result in enumerate(results[:3]):
            print(f"\n结果 {i+1}:")
            print(f"  标题: {result.get('title', 'N/A')}")
            print(f"  URL: {result.get('url', 'N/A')}")
            print(f"  内容: {result.get('content', 'N/A')[:100]}...")
    
    except Exception as e:
        print(f"搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. 测试新闻处理
    if 'results' in locals() and results:
        print("\n3. 处理新闻...")
        try:
            news_processor = NewsProcessor()
            articles = await news_processor.process_search_results(results[:3], symbol)
            print(f"处理后的文章数量: {len(articles)}")
            
            for i, article in enumerate(articles):
                print(f"\n文章 {i+1}:")
                print(f"  标题: {article.title}")
                print(f"  URL: {article.url}")
                print(f"  摘要: {article.summary}")
                print(f"  情感类型: {article.sentiment_type}")
                print(f"  相关性评分: {article.relevance_score}")
        
        except Exception as e:
            print(f"处理失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_news_search())