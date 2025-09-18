/**
 * 统一的 API 配置
 * 所有前端组件都应该使用这个配置文件中的 API_BASE
 */

// 从全局变量获取 API_BASE，或使用默认后端地址
export const API_BASE = (window as any).API_BASE || 'http://localhost:8080';

// 导出一个函数，方便其他地方调用
export const getApiBase = (): string => {
  return API_BASE;
};

// 常用的 API 端点
export const API_ENDPOINTS = {
  // 新闻相关
  NEWS: {
    ARTICLES: '/api/news/articles',
    STOCK_NEWS: (symbol: string) => `/api/news/stock/${symbol}`,
    COLLECT: (symbol: string) => `/api/news/collect/${symbol}`,
    INTELLIGENT_COLLECT: '/api/news/intelligent-collect',
    SEARCH: '/api/news/search',
    STRATEGIES: '/api/news/strategies',
  },
  
  // 仪表板相关
  DASHBOARD: {
    REPORTS: '/api/dashboard/reports',
  },
  
  // 任务相关
  TASKS: {
    REPORT: (stockCode: string) => `/api/tasks/report/${stockCode}`,
  },
  
  // 观察列表
  WATCHLIST: '/watchlist',
} as const;

// 辅助函数：构建完整的 API URL
export const buildApiUrl = (endpoint: string): string => {
  return `${API_BASE}${endpoint}`;
};