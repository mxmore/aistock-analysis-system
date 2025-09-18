// MongoDB initialization script for AI Stock News Database

// Switch to aistock_news database
use aistock_news

// Create collections and indexes
db.createCollection("news_articles")
db.createCollection("news_sources")
db.createCollection("search_cache")

// Create indexes for news_articles collection
db.news_articles.createIndex({"url": 1}, {"unique": true})
db.news_articles.createIndex({"published_at": -1})
db.news_articles.createIndex({"related_stocks": 1})
db.news_articles.createIndex({"sentiment_score": 1})
db.news_articles.createIndex({"keywords": 1})
db.news_articles.createIndex({"source": 1})
db.news_articles.createIndex({"title": "text", "content": "text", "summary": "text"})

// Create indexes for search_cache collection
db.search_cache.createIndex({"query_hash": 1}, {"unique": true})
db.search_cache.createIndex({"created_at": 1}, {"expireAfterSeconds": 3600})

// Insert sample news sources configuration
db.news_sources.insertMany([
  {
    "name": "新浪财经",
    "domain": "finance.sina.com.cn",
    "category": "finance",
    "reliability_score": 0.8,
    "language": "zh-CN",
    "enabled": true
  },
  {
    "name": "东方财富",
    "domain": "eastmoney.com",
    "category": "finance",
    "reliability_score": 0.85,
    "language": "zh-CN",
    "enabled": true
  },
  {
    "name": "雪球",
    "domain": "xueqiu.com",
    "category": "social_finance",
    "reliability_score": 0.7,
    "language": "zh-CN",
    "enabled": true
  },
  {
    "name": "Reuters",
    "domain": "reuters.com",
    "category": "international_finance",
    "reliability_score": 0.9,
    "language": "en",
    "enabled": true
  },
  {
    "name": "Bloomberg",
    "domain": "bloomberg.com",
    "category": "international_finance",
    "reliability_score": 0.9,
    "language": "en",
    "enabled": true
  }
])

print("AI Stock News Database initialized successfully!")
