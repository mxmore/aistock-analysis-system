#!/usr/bin/env python3
"""
开发服务器启动脚本
整合了原来的多个启动脚本，提供统一的开发服务器管理
"""
import sys
import os
import argparse
import uvicorn

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def start_main_server(port=8080, reload=True):
    """启动主API服务器"""
    print(f"🚀 启动主API服务器在端口 {port}...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)

def start_simple_server(port=8083):
    """启动简化测试API服务器"""
    from fastapi import FastAPI
    
    # Import after path setup
    from app.data_source import get_stock_info
    
    app = FastAPI(title="简化测试API", description="用于快速测试股票信息功能")
    
    @app.get("/")
    async def root():
        return {"message": "简化测试API运行中", "port": port}
    
    @app.get("/api/stock/{symbol}")
    async def get_stock_info_simple(symbol: str):
        """简化的股票信息API"""
        try:
            stock_info = get_stock_info(symbol)
            if not stock_info:
                return {"error": "Stock not found", "symbol": symbol}
            
            return {
                "symbol": symbol,
                "name": stock_info.get('name'),
                "code": stock_info.get('code'),
                "status": "success"
            }
            
        except Exception as e:
            return {"error": str(e), "symbol": symbol}
    
    print(f"🚀 启动简化API服务器在端口 {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

def start_news_test_server(port=8082):
    """启动新闻搜索测试服务器"""
    import asyncio
    from fastapi import FastAPI
    
    app = FastAPI(title="新闻搜索测试API", description="用于测试新闻搜索功能")
    
    @app.get("/")
    async def root():
        return {"message": "新闻搜索测试API运行中", "port": port}
    
    @app.get("/api/news/stock/{symbol}")
    async def get_stock_news_test(symbol: str):
        """新闻搜索测试API"""
        try:
            print(f"🔍 测试股票新闻搜索: {symbol}")
            
            # 仅支持测试股票
            if symbol != "300251.SZ":
                return {
                    "symbol": symbol,
                    "error": "只支持 300251.SZ 进行测试",
                    "supported_symbol": "300251.SZ"
                }
            
            company_name = "光线传媒"
            
            # 导入新闻服务模块
            from app.news_service import NewsSearchService
            from app.news_strategy import NewsProcessor
            
            news_search_service = NewsSearchService()
            news_processor = NewsProcessor()
            
            # 执行搜索
            search_results = await news_search_service.search_stock_news(
                symbol=symbol,
                company_name=company_name
            )
            
            # 处理结果（不保存到数据库）
            articles = await news_processor.process_search_results(search_results, symbol)
            
            # 格式化响应
            response_articles = []
            for i, article in enumerate(articles[:5]):  # 限制5篇文章
                article_data = {
                    "title": article.title,
                    "url": article.url,
                    "summary": article.summary or "",
                    "sentiment_type": article.sentiment_type,
                    "relevance_score": article.relevance_score
                }
                response_articles.append(article_data)
            
            return {
                "symbol": symbol,
                "company_name": company_name,
                "articles": response_articles,
                "total_count": len(response_articles),
                "note": "测试模式 - 数据不保存到数据库"
            }
            
        except Exception as e:
            print(f"❌ 新闻搜索测试错误: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "status": "测试失败"
            }
    
    print(f"🚀 启动新闻搜索测试服务器在端口 {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票系统开发服务器')
    parser.add_argument('--mode', choices=['main', 'simple', 'news'], default='main',
                       help='服务器模式: main(主服务器), simple(简化测试), news(新闻测试)')
    parser.add_argument('--port', type=int, 
                       help='端口号 (默认: main=8080, simple=8083, news=8082)')
    parser.add_argument('--no-reload', action='store_true',
                       help='禁用自动重载 (仅主服务器)')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'main':
            port = args.port or 8080
            reload = not args.no_reload
            start_main_server(port, reload)
        elif args.mode == 'simple':
            port = args.port or 8083
            start_simple_server(port)
        elif args.mode == 'news':
            port = args.port or 8082
            start_news_test_server(port)
            
    except KeyboardInterrupt:
        print("\n⏸ 服务器被用户停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()