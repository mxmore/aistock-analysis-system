"""
News Search and Management Service
Integrates with SearXNG for multi-source news aggregation
"""

import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import (
    NewsArticle, NewsSource, NewsKeyword, SearchLog, 
    NewsCategory, SentimentType, Watchlist
)
from .db import get_session


class NewsSearchService:
    def __init__(self, searxng_url: str = None):
        self.searxng_url = searxng_url or os.getenv("SEARXNG_URL", "http://localhost:10000")
        self.timeout = int(os.getenv("SEARXNG_TIMEOUT", "30"))
        self.http_client = httpx.AsyncClient(timeout=self.timeout)
        
    async def search_news(
        self, 
        query: str, 
        category: str = "general",
        time_range: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search news using SearXNG
        """
        search_params = {
            "q": query,
            "categories": category,
            "format": "json",
            "language": "zh-CN",
            "time_range": time_range or "week",
            "engines": "bing news,google news,baidu news"
        }
        
        start_time = datetime.utcnow()
        success = True
        error_message = None
        results = []
        
        try:
            response = await self.http_client.post(
                f"{self.searxng_url}/search",
                data=search_params
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])[:max_results]
            
            # Log search
            await self._log_search(
                query=query,
                query_type="api",
                source_engine="searxng",
                results_count=len(results),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                success=True
            )
            
            return results
            
        except Exception as e:
            error_message = str(e)
            success = False
            
            # Log failed search
            await self._log_search(
                query=query,
                query_type="api",
                source_engine="searxng",
                results_count=0,
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                success=False,
                error_message=error_message
            )
            
            raise Exception(f"News search failed: {error_message}")
    
    async def search_stock_news(self, symbol: str, company_name: str = None) -> List[Dict[str, Any]]:
        """
        Search news for specific stock symbol
        """
        queries = [symbol]
        if company_name:
            queries.append(company_name)
            
        all_results = []
        for query in queries:
            try:
                results = await self.search_news(
                    query=f"{query} 股票 财经",
                    category="general",
                    time_range="week",
                    max_results=10
                )
                all_results.extend(results)
            except Exception as e:
                print(f"Failed to search news for {query}: {e}")
                
        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
                
        return unique_results[:20]
    
    async def search_industry_news(self, industry: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search news for industry and policy keywords
        """
        query_parts = [industry]
        if keywords:
            query_parts.extend(keywords)
            
        query = " ".join(query_parts) + " 行业 政策 新闻"
        
        return await self.search_news(
            query=query,
            category="general",
            time_range="week",
            max_results=15
        )
    
    async def _log_search(
        self,
        query: str,
        query_type: str,
        source_engine: str,
        results_count: int,
        processing_time: float,
        success: bool,
        error_message: str = None
    ):
        """Log search operation - safe fallback when database unavailable"""
        try:
            from .db import SessionLocal
            session = SessionLocal()
            try:
                search_log = SearchLog(
                    query=query,
                    query_type=query_type,
                    source_engine=source_engine,
                    results_count=results_count,
                    processing_time=processing_time,
                    success=success,
                    error_message=error_message
                )
                session.add(search_log)
                session.commit()
            finally:
                session.close()
        except Exception as db_error:
            # Database unavailable - log to console instead
            print(f"🔍 Search Log (DB unavailable): query='{query}', results={results_count}, success={success}")
            if error_message:
                print(f"   Error: {error_message}")
            # Don't raise exception - continue without database logging


class NewsProcessor:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def process_search_results(self, results: List[Dict[str, Any]], related_symbol: str = None) -> List[NewsArticle]:
        """
        Process search results and create NewsArticle objects
        """
        articles = []
        
        for result in results:
            try:
                article = await self._process_single_result(result, related_symbol)
                if article:
                    articles.append(article)
            except Exception as e:
                print(f"Failed to process article {result.get('url', '')}: {e}")
                
        return articles
    
    async def _process_single_result(self, result: Dict[str, Any], related_symbol: str = None) -> Optional[NewsArticle]:
        """
        Process a single search result
        """
        url = result.get("url", "")
        title = result.get("title", "")
        
        if not url or not title:
            return None
            
        # Check if article already exists
        from .db import SessionLocal
        session = SessionLocal()
        try:
            existing = session.execute(
                select(NewsArticle).where(NewsArticle.url == url)
            ).scalar_one_or_none()
            
            if existing:
                return existing
        finally:
            session.close()
        
        # Extract content
        content = await self._extract_content(url)
        
        # Get or create news source
        source = await self._get_or_create_source(url)
        
        # Analyze content
        analysis = await self._analyze_content(title, content)
        
        # Create article
        article = NewsArticle(
            title=title,
            url=url,
            content=content,
            summary=self._generate_summary(content),
            published_at=self._parse_published_date(result.get("publishedDate")),
            source_id=source.id,
            category=analysis.get("category", NewsCategory.FINANCE.value),
            keywords=analysis.get("keywords", []),
            entities=analysis.get("entities", []),
            sentiment_type=analysis.get("sentiment_type"),
            sentiment_score=analysis.get("sentiment_score"),
            sentiment_confidence=analysis.get("sentiment_confidence"),
            related_stocks=self._extract_related_stocks(title, content, related_symbol),
            relevance_score=analysis.get("relevance_score", 0.5),
            content_quality=analysis.get("content_quality", 0.5)
        )
        
        return article
    
    async def _extract_content(self, url: str) -> Optional[str]:
        """
        Extract article content from URL
        """
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Try to find main content
            content_selectors = [
                "article", 
                ".content", 
                ".article-content",
                ".post-content",
                "#content",
                "main"
            ]
            
            content = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(strip=True)
                    break
            
            if not content:
                # Fallback to body content
                content = soup.get_text(strip=True)
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content)
            return content[:5000]  # Limit content length
            
        except Exception as e:
            print(f"Failed to extract content from {url}: {e}")
            return None
    
    async def _get_or_create_source(self, url: str) -> NewsSource:
        """
        Get or create news source from URL
        """
        domain = urlparse(url).netloc
        
        from .db import SessionLocal
        session = SessionLocal()
        try:
            source = session.execute(
                select(NewsSource).where(NewsSource.domain == domain)
            ).scalar_one_or_none()
            
            if not source:
                # Create new source
                source = NewsSource(
                    name=domain,
                    domain=domain,
                    category=self._categorize_domain(domain),
                    reliability_score=self._assess_reliability(domain),
                    language="zh-CN" if any(x in domain for x in ["cn", "com.cn", "sina", "163", "qq", "sohu"]) else "en"
                )
                session.add(source)
                session.commit()
                session.refresh(source)
            
            return source
        finally:
            session.close()
    
    def _categorize_domain(self, domain: str) -> str:
        """
        Categorize domain based on known patterns
        """
        finance_domains = ["finance", "money", "economic", "stock", "投资", "财经"]
        if any(keyword in domain.lower() for keyword in finance_domains):
            return NewsCategory.FINANCE.value
        return NewsCategory.FINANCE.value  # Default to finance
    
    def _assess_reliability(self, domain: str) -> float:
        """
        Assess domain reliability score
        """
        reliable_domains = {
            "reuters.com": 0.9,
            "bloomberg.com": 0.9,
            "finance.sina.com.cn": 0.8,
            "eastmoney.com": 0.85,
            "cnbc.com": 0.85,
            "ft.com": 0.9
        }
        return reliable_domains.get(domain, 0.6)
    
    async def _analyze_content(self, title: str, content: str) -> Dict[str, Any]:
        """
        Analyze content for sentiment, keywords, etc.
        """
        # Simple keyword extraction
        finance_keywords = ["股票", "投资", "市场", "交易", "涨跌", "利润", "财报", "业绩"]
        
        text = f"{title} {content or ''}"
        found_keywords = [kw for kw in finance_keywords if kw in text]
        
        # Simple sentiment analysis
        positive_words = ["上涨", "增长", "利好", "盈利", "突破", "看好"]
        negative_words = ["下跌", "亏损", "利空", "风险", "暴跌", "看空"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            sentiment_type = SentimentType.POSITIVE.value
            sentiment_score = min(0.8, 0.1 + positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment_type = SentimentType.NEGATIVE.value
            sentiment_score = max(-0.8, -0.1 - negative_count * 0.1)
        else:
            sentiment_type = SentimentType.NEUTRAL.value
            sentiment_score = 0.0
        
        return {
            "category": NewsCategory.FINANCE.value,
            "keywords": found_keywords,
            "entities": [],  # TODO: Implement NER
            "sentiment_type": sentiment_type,
            "sentiment_score": sentiment_score,
            "sentiment_confidence": 0.7,
            "relevance_score": min(1.0, len(found_keywords) * 0.2),
            "content_quality": 0.8 if content and len(content) > 100 else 0.3
        }
    
    def _extract_related_stocks(self, title: str, content: str, hint_symbol: str = None) -> List[str]:
        """
        Extract related stock symbols from content
        """
        stocks = []
        text = f"{title} {content or ''}"
        
        # Pattern for Chinese stock codes
        stock_pattern = r'\b\d{6}\.(SH|SZ)\b'
        matches = re.findall(stock_pattern, text, re.IGNORECASE)
        stocks.extend([f"{match[0]}.{match[1]}" for match in matches])
        
        if hint_symbol:
            stocks.append(hint_symbol)
        
        return list(set(stocks))  # Remove duplicates
    
    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """
        Generate article summary
        """
        if not content:
            return ""
        
        sentences = content.split('。')
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + "。"
            else:
                break
        
        return summary.strip()
    
    def _parse_published_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse published date from various formats
        """
        if not date_str:
            return None
        
        try:
            # Try common date formats
            formats = [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
        except Exception:
            pass
        
        return None


class NewsScheduler:
    def __init__(self):
        self.search_service = NewsSearchService()
        self.processor = NewsProcessor()
    
    async def run_scheduled_news_collection(self):
        """
        Run scheduled news collection for all watchlist stocks
        """
        from .db import SessionLocal
        session = SessionLocal()
        try:
            # Get all enabled stocks
            stocks = session.execute(
                select(Watchlist).where(Watchlist.enabled == True)
            ).scalars().all()
            
            for stock in stocks:
                try:
                    await self._collect_news_for_stock(stock.symbol, stock.name)
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    print(f"Failed to collect news for {stock.symbol}: {e}")
        finally:
            session.close()
    
    async def _collect_news_for_stock(self, symbol: str, company_name: str = None):
        """
        Collect news for a specific stock
        """
        # Search for news
        results = await self.search_service.search_stock_news(symbol, company_name)
        
        # Process results
        articles = await self.processor.process_search_results(results, symbol)
        
        # Save to database
        from .db import SessionLocal
        session = SessionLocal()
        try:
            for article in articles:
                try:
                    # Check for duplicates
                    existing = session.execute(
                        select(NewsArticle).where(NewsArticle.url == article.url)
                    ).scalar_one_or_none()
                    
                    if not existing:
                        session.add(article)
                except Exception as e:
                    print(f"Failed to save article {article.url}: {e}")
            
            session.commit()
        finally:
            session.close()
