import React, { useState, useEffect } from 'react';

interface Article {
  id: string;
  title: string;
  summary: string;
  url: string;
  source: string;
  published_at: string;
  sentiment_type?: 'positive' | 'negative' | 'neutral';
  related_stocks: string[];
}

interface WatchlistItem {
  symbol: string;
  name: string;
  sector?: string;
  enabled: boolean;
}

interface Strategy {
  name: string;
  description: string;
}

const API_BASE = 'http://localhost:8080';

export default function ModernNewsComponent() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStock, setSelectedStock] = useState<string>('');
  const [sentimentFilter, setSentimentFilter] = useState<'all' | 'positive' | 'negative' | 'neutral'>('all');
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [showStockSelector, setShowStockSelector] = useState(false);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [showStrategies, setShowStrategies] = useState(false);
  const [isCollecting, setIsCollecting] = useState(false);
  const [isIntelligentCollecting, setIsIntelligentCollecting] = useState(false);

  // Load news articles
  const loadNews = async () => {
    setLoading(true);
    try {
      let url = `${API_BASE}/api/news/articles`;
      if (selectedStock) {
        url = `${API_BASE}/api/news/stock/${selectedStock}`;
      }

      console.log('Loading news from:', url);
      const response = await fetch(url);
      const data = await response.json();
      
      console.log('News API Response:', data);
      
      // 处理不同的响应格式
      let newsData = [];
      if (data.articles && Array.isArray(data.articles)) {
        newsData = data.articles;
      } else if (Array.isArray(data)) {
        newsData = data;
      } else if (data.stocks && Array.isArray(data.stocks)) {
        newsData = data.stocks;
      } else {
        console.warn('Unexpected news response format:', data);
        newsData = [];
      }

      setArticles(newsData);
      console.log('News loaded successfully:', newsData.length, 'articles');
    } catch (error) {
      console.error('Failed to load news:', error);
      setArticles([]);
    } finally {
      setLoading(false);
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

  // Load strategies
  const loadStrategies = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/news/strategies`);
      const data = await response.json();
      setStrategies(data || []);
    } catch (error) {
      console.error('Failed to load strategies:', error);
      setStrategies([]);
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery })
      });
      const data = await response.json();
      setArticles(data.articles || []);
    } catch (error) {
      console.error('Search failed:', error);
      setArticles([]);
    } finally {
      setLoading(false);
    }
  };

  // Collect news for selected stock
  const collectNews = async () => {
    if (!selectedStock) return;
    
    setIsCollecting(true);
    try {
      const response = await fetch(`${API_BASE}/api/news/collect/${selectedStock}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        console.log('News collection successful for', selectedStock);
        await loadNews(); // Reload news after collection
      } else {
        console.error('News collection failed:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('News collection failed:', error);
    } finally {
      setIsCollecting(false);
    }
  };

  // Intelligent news collection
  const runIntelligentCollection = async () => {
    setIsIntelligentCollecting(true);
    try {
      const response = await fetch(`${API_BASE}/api/news/collect/intelligent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        console.log('Intelligent news collection successful');
        await loadNews(); // Reload news after collection
      } else {
        console.error('Intelligent news collection failed:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Intelligent collection failed:', error);
    } finally {
      setIsIntelligentCollecting(false);
    }
  };

  // Utility functions
  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full flex items-center justify-center text-white font-bold text-sm">↗</div>;
      case 'negative':
        return <div className="w-8 h-8 bg-gradient-to-r from-red-400 to-rose-500 rounded-full flex items-center justify-center text-white font-bold text-sm">↘</div>;
      default:
        return <div className="w-8 h-8 bg-gradient-to-r from-gray-400 to-slate-500 rounded-full flex items-center justify-center text-white font-bold text-sm">→</div>;
    }
  };

  const getSentimentBgColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'bg-gradient-to-r from-green-50/50 to-emerald-50/50 border-green-200/50';
      case 'negative':
        return 'bg-gradient-to-r from-red-50/50 to-rose-50/50 border-red-200/50';
      default:
        return 'bg-white/60 border-gray-200/50';
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredArticles = articles.filter(article => 
    sentimentFilter === 'all' || article.sentiment_type === sentimentFilter
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/30">
      {/* Modern Header */}
      <div className="bg-white/70 backdrop-blur-xl border-b border-white/20 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-600 via-purple-600 to-blue-700 rounded-2xl flex items-center justify-center shadow-lg">
                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/>
                  <path d="M14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"/>
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent">
                  {selectedStock ? `${selectedStock} 财经新闻` : '财经新闻中心'}
                </h1>
                {selectedStock && watchlist.find(w => w.symbol === selectedStock) && (
                  <p className="text-sm text-gray-600 mt-1">
                    {watchlist.find(w => w.symbol === selectedStock)?.name}
                  </p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="px-4 py-2 bg-green-50/80 backdrop-blur-sm border border-green-200/50 rounded-xl text-green-700 text-sm font-medium">
                <span className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  实时数据
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Control Panel */}
        <div className="bg-white/50 backdrop-blur-xl rounded-3xl border border-white/20 p-8 mb-8 shadow-xl">
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            
            {/* Stock Selector */}
            <div className="space-y-4">
              <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <span className="text-lg">📊</span>
                选择股票
              </label>
              <div className="relative">
                <button
                  onClick={() => setShowStockSelector(!showStockSelector)}
                  className="w-full px-6 py-4 bg-white/70 backdrop-blur-sm border border-white/30 rounded-2xl text-left transition-all duration-300 hover:shadow-lg hover:border-blue-300/50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 group"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">
                        {selectedStock || '请选择股票'}
                      </div>
                      {selectedStock && watchlist.find(w => w.symbol === selectedStock) && (
                        <div className="text-sm text-gray-500 mt-1">
                          {watchlist.find(w => w.symbol === selectedStock)?.name}
                        </div>
                      )}
                    </div>
                    <div className={`text-gray-400 transition-transform duration-200 group-hover:text-blue-500 ${showStockSelector ? 'rotate-180' : ''}`}>
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                </button>
                
                {showStockSelector && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-white/95 backdrop-blur-xl border border-white/30 rounded-2xl shadow-2xl z-50 max-h-80 overflow-hidden">
                    <div className="p-4 border-b border-gray-100/50">
                      <div className="text-sm font-semibold text-gray-700">关注列表</div>
                      <div className="text-xs text-gray-500 mt-1">共 {watchlist.length} 只股票</div>
                    </div>
                    <div className="overflow-y-auto max-h-64">
                      {watchlist.length === 0 ? (
                        <div className="p-8 text-center">
                          <div className="text-4xl mb-4">📈</div>
                          <div className="font-medium text-gray-700 mb-2">暂无关注股票</div>
                          <div className="text-sm text-gray-500">请先添加股票到关注列表</div>
                        </div>
                      ) : (
                        <div className="p-2">
                          {watchlist.map((stock) => (
                            <button
                              key={stock.symbol}
                              onClick={() => {
                                setSelectedStock(stock.symbol);
                                setShowStockSelector(false);
                              }}
                              className={`w-full text-left p-4 rounded-xl transition-all duration-200 mb-1 ${
                                selectedStock === stock.symbol 
                                  ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 shadow-sm' 
                                  : 'hover:bg-gray-50/80 hover:shadow-sm'
                              }`}
                            >
                              <div className="font-semibold text-gray-900">{stock.symbol}</div>
                              <div className="text-sm text-gray-600 truncate mt-1">{stock.name}</div>
                              {stock.sector && (
                                <div className="text-xs text-gray-500 mt-2">
                                  <span className="px-2 py-1 bg-gray-100 rounded-full">{stock.sector}</span>
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
            </div>

            {/* Search Section */}
            <div className="space-y-4">
              <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <span className="text-lg">🔍</span>
                搜索新闻
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="输入关键词、股票代码..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchNews()}
                  className="w-full px-6 py-4 pl-12 bg-white/70 backdrop-blur-sm border border-white/30 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300/50 transition-all duration-300 hover:shadow-lg"
                />
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Actions & Filters */}
            <div className="space-y-4">
              <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <span className="text-lg">⚡</span>
                快速操作
              </label>
              <div className="flex flex-col gap-3">
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={searchNews}
                    disabled={loading}
                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-400 disabled:to-gray-500 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none"
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        搜索中
                      </span>
                    ) : '搜索'}
                  </button>
                  
                  {selectedStock ? (
                    <button
                      onClick={collectNews}
                      disabled={isCollecting}
                      className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-700 hover:from-green-700 hover:to-emerald-800 disabled:from-gray-400 disabled:to-gray-500 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none"
                    >
                      {isCollecting ? (
                        <span className="flex items-center justify-center gap-2">
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          收集中
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
                        <span className="flex items-center justify-center gap-2">
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          智能收集中
                        </span>
                      ) : (
                        <span className="flex items-center justify-center gap-2">
                          <span>🤖</span>
                          <span>智能收集</span>
                        </span>
                      )}
                    </button>
                  )}
                </div>
                
                <select
                  value={sentimentFilter}
                  onChange={(e) => setSentimentFilter(e.target.value as any)}
                  className="px-4 py-3 bg-white/70 backdrop-blur-sm border border-white/30 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300/50 transition-all duration-300 hover:shadow-lg"
                >
                  <option value="all">📊 全部情感</option>
                  <option value="positive">😊 积极情感</option>
                  <option value="negative">😔 消极情感</option>
                  <option value="neutral">😐 中性情感</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Strategy Panel */}
        {!selectedStock && (
          <div className="mb-8">
            <button
              onClick={() => {
                setShowStrategies(!showStrategies);
                if (!showStrategies) loadStrategies();
              }}
              className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-2 font-medium"
            >
              <span>📋 新闻收集策略</span>
              <span className={`transition-transform ${showStrategies ? 'rotate-180' : ''}`}>▼</span>
            </button>
            
            {showStrategies && (
              <div className="mt-4 p-6 bg-blue-50/80 backdrop-blur-sm rounded-2xl border border-blue-200/50">
                <div className="text-sm text-blue-700 mb-4 font-medium">可用策略：</div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {strategies.map((strategy, index) => (
                    <div key={index} className="px-4 py-3 bg-white/80 border border-blue-200 text-blue-700 text-sm rounded-xl shadow-sm">
                      <div className="font-medium">{strategy.name}</div>
                      {strategy.description && (
                        <div className="text-xs text-blue-600 mt-1">{strategy.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* News List */}
        {loading ? (
          <div className="flex items-center justify-center py-16 bg-white/50 backdrop-blur-xl rounded-3xl border border-white/20 shadow-xl">
            <div className="flex flex-col items-center gap-6">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-gray-600 text-base font-medium">正在加载新闻...</p>
              <p className="text-gray-400 text-sm">请稍候片刻</p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {filteredArticles.length === 0 ? (
              <div className="text-center py-16 bg-white/50 backdrop-blur-xl rounded-3xl border border-white/20 shadow-xl">
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
                {filteredArticles.map((article) => (
                  <div
                    key={article.id}
                    className={`backdrop-blur-xl rounded-3xl border border-white/20 hover:shadow-2xl transition-all duration-300 overflow-hidden group ${getSentimentBgColor(article.sentiment_type)} shadow-xl`}
                  >
                    {/* Header Section */}
                    <div className="p-8 pb-6">
                      <div className="flex items-start justify-between gap-6 mb-6">
                        <h3 className="text-xl font-bold text-gray-900 line-clamp-2 group-hover:text-blue-700 transition-colors duration-200 leading-8">
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-blue-600 transition-colors"
                          >
                            {article.title}
                          </a>
                        </h3>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          {getSentimentIcon(article.sentiment_type)}
                          <div className={`px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap ${getSentimentColor(article.sentiment_type)}`}>
                            {getSentimentText(article.sentiment_type)}
                          </div>
                        </div>
                      </div>
                      
                      {article.summary && (
                        <p className="text-gray-700 text-base leading-relaxed mb-6 line-clamp-3">
                          {article.summary}
                        </p>
                      )}
                    </div>

                    {/* Metadata Section */}
                    <div className="px-8 pb-6">
                      <div className="flex flex-wrap items-center gap-6 text-sm text-gray-600 mb-6">
                        <span className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                          </svg>
                          {formatDate(article.published_at)}
                        </span>
                        {article.source && (
                          <span className="flex items-center gap-2">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
                            </svg>
                            {article.source}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="px-8 py-6 bg-gradient-to-r from-white/80 to-gray-50/80 backdrop-blur-sm border-t border-white/30">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          {article.related_stocks && article.related_stocks.length > 0 && (
                            <div className="flex items-center gap-3">
                              <span className="text-sm text-gray-600 font-medium">相关股票:</span>
                              <div className="flex gap-2">
                                {article.related_stocks.slice(0, 3).map((stock, idx) => (
                                  <span key={idx} className="px-3 py-1.5 bg-blue-100 text-blue-700 text-sm rounded-lg font-medium">
                                    {stock}
                                  </span>
                                ))}
                                {article.related_stocks.length > 3 && (
                                  <span className="px-3 py-1.5 bg-gray-200 text-gray-600 text-sm rounded-lg">
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
                              className="flex items-center gap-2 px-6 py-3 text-blue-600 hover:text-blue-800 bg-white/80 hover:bg-blue-50 border border-blue-200 hover:border-blue-300 rounded-xl text-sm transition-all duration-200 font-medium shadow-sm hover:shadow-md backdrop-blur-sm"
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
    </div>
  );
}