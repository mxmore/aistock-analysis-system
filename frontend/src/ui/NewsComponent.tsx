import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "./card";
import { Button } from "./button";
import { Input } from "./input";
import { Badge } from "./badge";

const API_BASE = (window as any).API_BASE || 'http://localhost:8080';

interface NewsArticle {
  id: number;
  title: string;
  url: string;
  summary: string;
  published_at: string;
  source: string;
  sentiment_type: 'positive' | 'negative' | 'neutral';
  sentiment_score: number;
  relevance_score: number;
  related_stocks: string[];
  keywords: string[];
}

interface NewsComponentProps {
  symbol?: string;
  companyName?: string;
}

interface WatchlistItem {
  symbol: string;
  name: string;
  sector: string;
  enabled: boolean;
}

export default function NewsComponent({ symbol, companyName }: NewsComponentProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState<'all' | 'positive' | 'negative' | 'neutral'>('all');
  const [isCollecting, setIsCollecting] = useState(false);
  const [isIntelligentCollecting, setIsIntelligentCollecting] = useState(false);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [showStrategies, setShowStrategies] = useState(false);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [selectedStock, setSelectedStock] = useState<string>('');
  const [showStockSelector, setShowStockSelector] = useState(false);

  // Load news articles
  const loadNews = async () => {
    setLoading(true);
    try {
      let url = `${API_BASE}/api/news/articles`;
      if (selectedStock) {
        url = `${API_BASE}/api/news/stock/${selectedStock}`;
      }

      const response = await fetch(url);
      const data = await response.json();
      
      console.log('API Response:', data); // 调试日志
      
      // 处理不同的数据结构
      let articles = [];
      if (data.articles) {
        articles = data.articles;
      } else if (Array.isArray(data)) {
        articles = data;
      } else if (data.stocks && Array.isArray(data.stocks)) {
        // 如果返回的是stocks数据，转换为articles格式
        articles = [];
      }
      
      setArticles(articles || []);
    } catch (error) {
      console.error('Failed to load news:', error);
      setArticles([]);
    } finally {
      setLoading(false);
    }
  };

  // Manual news collection
  const collectNews = async () => {
    if (!selectedStock) return;
    
    setIsCollecting(true);
    try {
      const response = await fetch(`${API_BASE}/api/news/collect/${selectedStock}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Refresh news after collection
        setTimeout(loadNews, 2000);
      }
    } catch (error) {
      console.error('Failed to collect news:', error);
    } finally {
      setIsCollecting(false);
    }
  };

  // Intelligent news collection
  const runIntelligentCollection = async () => {
    setIsIntelligentCollecting(true);
    try {
      const response = await fetch(`${API_BASE}/api/news/intelligent-collect`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Refresh articles after collection
        setTimeout(() => {
          loadNews();
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to run intelligent collection:', error);
    } finally {
      setIsIntelligentCollecting(false);
    }
  };

  // Load available strategies
  const loadStrategies = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/news/strategies`);
      const data = await response.json();
      setStrategies(data.strategies);
    } catch (error) {
      console.error('Failed to load strategies:', error);
    }
  };

  // Load watchlist
  const loadWatchlist = async () => {
    try {
      console.log('Loading watchlist from:', `${API_BASE}/watchlist`);
      const response = await fetch(`${API_BASE}/watchlist`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Watchlist API response:', data);
      
      // API返回的是直接的数组，不是包含stocks字段的对象
      if (Array.isArray(data)) {
        setWatchlist(data);
        console.log('Watchlist loaded successfully:', data.length, 'items');
      } else {
        console.warn('Unexpected watchlist response format:', data);
        setWatchlist([]);
      }
    } catch (error) {
      console.error('Failed to load watchlist:', error);
      setWatchlist([]);
    }
  };

  useEffect(() => {
    loadNews();
    loadWatchlist();
  }, [selectedStock]);

  // Search news
  const searchNews = async () => {
    if (!searchQuery.trim()) {
      loadNews();
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/news/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: searchQuery,
          category: 'news',
          time_range: 'week',
          max_results: 20
        })
      });
      
      const data = await response.json();
      // Convert search results to our article format
      const searchArticles = (data.articles || []).map((item: any, index: number) => ({
        id: index,
        title: item.title || '',
        url: item.url || '',
        summary: item.content || '',
        published_at: item.publishedDate || new Date().toISOString(),
        source: item.engine || 'Unknown',
        sentiment_type: 'neutral' as const,
        sentiment_score: 0,
        relevance_score: 0.5,
        related_stocks: [],
        keywords: []
      }));
      
      setArticles(searchArticles || []);
    } catch (error) {
      console.error('Failed to search news:', error);
      setArticles([]);
    } finally {
      setLoading(false);
    }
  };

  // Handle symbol prop changes
  useEffect(() => {
    if (symbol && symbol !== selectedStock) {
      setSelectedStock(symbol);
    }
  }, [symbol]);

  // Handle stock selection
  const handleStockSelect = (stockSymbol: string) => {
    setSelectedStock(stockSymbol);
    setShowStockSelector(false);
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full text-white font-bold text-sm">
            ↗
          </div>
        );
      case 'negative':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-r from-red-400 to-rose-500 rounded-full text-white font-bold text-sm">
            ↘
          </div>
        );
      default:
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-r from-gray-400 to-slate-500 rounded-full text-white font-bold text-sm">
            →
          </div>
        );
    }
  };

  const getSentimentBgColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 border-green-200';
      case 'negative':
        return 'bg-gradient-to-r from-red-50 to-rose-50 text-red-700 border-red-200';
      default:
        return 'bg-gradient-to-r from-gray-50 to-slate-50 text-gray-700 border-gray-200';
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'bg-green-100 text-green-700 border border-green-200';
      case 'negative':
        return 'bg-red-100 text-red-700 border border-red-200';
      case 'neutral':
        return 'bg-gray-100 text-gray-700 border border-gray-200';
      default:
        return 'bg-gray-100 text-gray-700 border border-gray-200';
    }
  };

  const getSentimentText = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return '积极';
      case 'negative':
        return '消极';
      case 'neutral':
        return '中性';
      default:
        return '未知';
    }
  };

  const getSentimentEmoji = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return '😊';
      case 'negative':
        return '😔';
      case 'neutral':
        return '😐';
      default:
        return '📰';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="w-full h-full">
      {/* Compact Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white flex-shrink-0">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
              <path d="M14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"/>
            </svg>
          </div>
          <div className="min-w-0">
            <h2 className="text-xl font-bold text-gray-900 truncate">
              {selectedStock ? `${selectedStock} 财经新闻` : '财经新闻'}
            </h2>
            {selectedStock && watchlist.find(w => w.symbol === selectedStock) && (
              <p className="text-xs text-gray-500 mt-0.5 truncate">
                {watchlist.find(w => w.symbol === selectedStock)?.name}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Stock Selector and Search Layout */}
      <div className="flex flex-col lg:flex-row gap-6 mb-8">
        {/* Left: Stock Selector */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 lg:w-auto">
          <div className="relative">
            <button
              onClick={() => setShowStockSelector(!showStockSelector)}
              className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-medium rounded-xl transition-all duration-200 flex items-center gap-3 whitespace-nowrap shadow-lg hover:shadow-xl"
            >
              <span className="text-lg">📊</span>
              <span>{selectedStock || '选择股票'}</span>
              <span className={`ml-2 transition-transform duration-200 ${showStockSelector ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            
            {showStockSelector && (
              <div className="absolute top-full left-0 mt-3 w-72 bg-white border border-gray-200 rounded-xl shadow-2xl z-50 max-h-64 overflow-hidden backdrop-blur-sm">
                <div className="p-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-gray-100">
                  <div className="text-sm font-semibold text-gray-700">选择关注股票</div>
                </div>
                <div className="overflow-y-auto max-h-52 custom-scrollbar bg-white">
                  {watchlist.length === 0 ? (
                    <div className="p-6 text-center text-gray-500 text-sm bg-white">
                      <div className="text-3xl mb-3">📈</div>
                      <div className="font-medium">暂无关注股票</div>
                      <div className="text-xs text-gray-400 mt-1">请先添加关注的股票</div>
                    </div>
                  ) : (
                    <div className="p-2 bg-white">
                      {watchlist.map((stock) => (
                        <button
                          key={stock.symbol}
                          onClick={() => handleStockSelect(stock.symbol)}
                          className={`w-full text-left p-3 rounded-lg text-sm transition-all duration-200 mb-1 ${
                            selectedStock === stock.symbol 
                              ? 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-800 shadow-sm' 
                              : 'hover:bg-gray-50 hover:shadow-sm'
                          }`}
                        >
                          <div className="font-semibold">{stock.symbol}</div>
                          <div className="text-xs text-gray-500 truncate mt-1">{stock.name}</div>
                          {stock.sector && (
                            <div className="text-xs text-gray-400 mt-1">
                              <span className="px-2 py-1 bg-gray-100 rounded-full text-xs">{stock.sector}</span>
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            {selectedStock ? (
              <button
                onClick={collectNews}
                disabled={isCollecting}
                className="px-6 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 disabled:from-gray-400 disabled:to-gray-500 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none"
              >
                {isCollecting ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    收集中...
                  </span>
                ) : '收集新闻'}
              </button>
            ) : (
              <button
                onClick={runIntelligentCollection}
                disabled={isIntelligentCollecting}
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 disabled:from-gray-400 disabled:to-gray-500 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none"
              >
                {isIntelligentCollecting ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    智能收集中...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <span>🤖</span>
                    <span>智能收集</span>
                  </span>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Right: Search Section */}
        <div className="flex-1 max-w-2xl">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="搜索新闻、股票代码、关键词..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && searchNews()}
                className="w-full px-4 py-3 pl-12 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm hover:shadow-md transition-shadow duration-200"
              />
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={searchNews}
                disabled={loading}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-400 disabled:to-gray-500 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none flex-shrink-0"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    搜索中
                  </span>
                ) : '搜索'}
              </button>
              
              <select
                value={sentimentFilter}
                onChange={(e) => setSentimentFilter(e.target.value as any)}
                className="px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent flex-shrink-0 shadow-sm hover:shadow-md transition-shadow duration-200"
              >
                <option value="all">全部情感</option>
                <option value="positive">😊 积极</option>
                <option value="negative">😔 消极</option>
                <option value="neutral">😐 中性</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Strategy Panel */}
      {!selectedStock && (
        <div className="mb-4">
          <button
            onClick={() => {
              setShowStrategies(!showStrategies);
              if (!showStrategies) loadStrategies();
            }}
            className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>新闻收集策略</span>
            <span className={`transition-transform ${showStrategies ? 'rotate-180' : ''}`}>▼</span>
          </button>
          
          {showStrategies && (
            <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-blue-600 mb-2">可用策略：</div>
              <div className="flex flex-wrap gap-2">
                {strategies.map((strategy, index) => (
                  <span key={index} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                    {strategy.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* News List */}
      {loading ? (
        <div className="flex items-center justify-center py-16 bg-white rounded-2xl shadow-sm border border-gray-100">
          <div className="flex flex-col items-center gap-6">
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-600 text-base font-medium">正在加载新闻...</p>
            <p className="text-gray-400 text-sm">请稍候片刻</p>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {(articles || []).filter(article => 
            sentimentFilter === 'all' || article.sentiment_type === sentimentFilter
          ).length === 0 ? (
            <div className="text-center py-16 bg-white rounded-2xl shadow-sm border border-gray-100">
              <div className="text-6xl mb-6">📰</div>
              <div className="text-xl font-semibold text-gray-700 mb-3">暂无新闻数据</div>
              <div className="text-gray-500 max-w-md mx-auto leading-relaxed">
                {selectedStock 
                  ? `没有找到关于 ${selectedStock} 的相关新闻。请尝试收集最新新闻或切换其他股票。`
                  : '请选择股票进行新闻收集，或使用智能收集功能获取最新财经资讯。'
                }
              </div>
              <div className="mt-8 flex justify-center gap-4">
                {selectedStock ? (
                  <button
                    onClick={collectNews}
                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl"
                  >
                    <span className="flex items-center gap-2">
                      <span>📊</span>
                      <span>收集 {selectedStock} 新闻</span>
                    </span>
                  </button>
                ) : (
                  <button
                    onClick={runIntelligentCollection}
                    className="px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl"
                  >
                    <span className="flex items-center gap-2">
                      <span>🤖</span>
                      <span>开始智能收集</span>
                    </span>
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="grid gap-6">
              {(articles || []).filter(article => 
                sentimentFilter === 'all' || article.sentiment_type === sentimentFilter
              ).map((article) => (
                <div
                  key={article.id}
                  className={`bg-white rounded-2xl shadow-sm border border-gray-100 hover:shadow-lg transition-all duration-300 overflow-hidden group ${getSentimentBgColor(article.sentiment_type)}`}
                >
                  {/* Header Section */}
                  <div className="p-6 pb-4">
                    <div className="flex items-start justify-between gap-4 mb-4">
                      <h3 className="text-lg font-bold text-gray-900 line-clamp-2 group-hover:text-blue-700 transition-colors duration-200 leading-7">
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-blue-600 transition-colors"
                        >
                          {article.title}
                        </a>
                      </h3>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {getSentimentIcon(article.sentiment_type)}
                        <div className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap ${getSentimentColor(article.sentiment_type)}`}>
                          {getSentimentText(article.sentiment_type)}
                        </div>
                      </div>
                    </div>
                    
                    {article.summary && (
                      <p className="text-gray-600 text-sm leading-relaxed mb-4 line-clamp-3">
                        {article.summary}
                      </p>
                    )}
                  </div>

                  {/* Metadata Section */}
                  <div className="px-6 pb-6">
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 mb-4">
                      <span className="flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                        </svg>
                        {formatDate(article.published_at)}
                      </span>
                      {article.source && (
                        <span className="flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
                          </svg>
                          {article.source}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Footer Actions */}
                  <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 border-t border-gray-100">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        {article.related_stocks && article.related_stocks.length > 0 && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">相关股票:</span>
                            <div className="flex gap-1.5">
                              {article.related_stocks.slice(0, 3).map((stock, idx) => (
                                <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-md font-medium">
                                  {stock}
                                </span>
                              ))}
                              {article.related_stocks.length > 3 && (
                                <span className="px-2 py-1 bg-gray-200 text-gray-600 text-xs rounded-md">
                                  +{article.related_stocks.length - 3}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-3">
                        {article.url && (
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:text-blue-800 bg-white hover:bg-blue-50 border border-blue-200 hover:border-blue-300 rounded-lg text-sm transition-all duration-200 font-medium shadow-sm hover:shadow-md"
                          >
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                            </svg>
                            阅读原文
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}