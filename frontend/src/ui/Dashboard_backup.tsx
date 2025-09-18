import React, { useState, useEffect } from 'react';
import { API_BASE, API_ENDPOINTS, buildApiUrl } from '../config/api';

// 简化图标组件 - 更小更统一
const RefreshIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const ChartIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const TaskIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
  </svg>
);

const PlayIcon = () => (
  <svg className="w-2 h-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H15M6 10a2 2 0 112-2h3a2 2 0 012 2m1 4a2 2 0 104 0m-5 4a2 2 0 01-2-2v-1a1 1 0 00-1-1H9a1 1 0 01-1-1v-1a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h10z" />
  </svg>
);

const LoadingSpinner = () => (
  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
);

interface ReportData {
  version: number;
  created_at: string;
  data_quality_score: number;
  prediction_confidence: number;
  analysis_summary: string;
}

interface TaskData {
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  priority: number;
}

interface StockDashboardItem {
  symbol: string;
  name: string;
  sector: string;
  latest_report: ReportData | null;
  current_task: TaskData | null;
}

interface DashboardSummary {
  total_stocks: number;
  with_reports: number;
  pending_tasks: number;
  running_tasks: number;
  failed_tasks: number;
}

interface TasksDashboard {
  status_statistics: Record<string, number>;
  type_statistics: Record<string, number>;
  recent_tasks: Array<{
    symbol: string;
    task_type: string;
    status: string;
    created_at: string;
    completed_at?: string;
    error_message?: string;
  }>;
}

const Dashboard: React.FC = () => {
  const [reportsDashboard, setReportsDashboard] = useState<{
    stocks: StockDashboardItem[];
    summary: DashboardSummary;
  } | null>(null);
  
  const [tasksDashboard, setTasksDashboard] = useState<TasksDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'reports' | 'tasks'>('reports');

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [reportsResponse, tasksResponse] = await Promise.all([
        fetch(buildApiUrl(API_ENDPOINTS.DASHBOARD.REPORTS)),
        fetch(buildApiUrl('/api/dashboard/tasks'))
      ]);

      if (!reportsResponse.ok || !tasksResponse.ok) {
        const errorText = !reportsResponse.ok ? await reportsResponse.text() : await tasksResponse.text();
        throw new Error(`API请求失败: ${errorText}`);
      }

      const reportsData = await reportsResponse.json();
      const tasksData = await tasksResponse.json();

      setReportsDashboard(reportsData);
      setTasksDashboard(tasksData);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    // 每30秒刷新一次数据
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-emerald-100 text-emerald-800 border border-emerald-200';
      case 'running': return 'bg-blue-100 text-blue-800 border border-blue-200 animate-pulse';
      case 'pending': return 'bg-amber-100 text-amber-800 border border-amber-200';
      case 'failed': return 'bg-red-100 text-red-800 border border-red-200';
      default: return 'bg-gray-100 text-gray-800 border border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>;
      case 'running':
        return <svg className="w-3 h-3 mr-1 animate-spin" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" /></svg>;
      case 'pending':
        return <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" /></svg>;
      case 'failed':
        return <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>;
      default:
        return null;
    }
  };

  const getQualityScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-emerald-600';
    if (score >= 0.6) return 'text-amber-600';
    return 'text-red-600';
  };

  const getQualityScoreBackground = (score: number) => {
    if (score >= 0.8) return 'bg-emerald-50 border-emerald-200';
    if (score >= 0.6) return 'bg-amber-50 border-amber-200';
    return 'bg-red-50 border-red-200';
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const createReportTask = async (symbol: string) => {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.TASKS.REPORT(symbol)), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ priority: 1 })
      });

      if (response.ok) {
        // 刷新数据
        fetchDashboardData();
      } else {
        const errorText = await response.text();
        throw new Error(`创建任务失败: ${errorText}`);
      }
    } catch (err) {
      console.error('Create task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to create task');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="text-center">
          <LoadingSpinner />
          <div className="text-lg text-gray-600 mt-4 animate-pulse">加载仪表板数据...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto mt-20">
        <div className="bg-white border border-red-200 rounded-xl shadow-lg p-6">
          <div className="flex items-center mb-4">
            <div className="bg-red-100 rounded-full p-2 mr-3">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-red-800">加载失败</h3>
          </div>
          <p className="text-red-600 mb-6">{error}</p>
          <button
            onClick={fetchDashboardData}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors duration-200 flex items-center justify-center"
          >
            <RefreshIcon />
            <span className="ml-2">重试</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 简化页头 */}
      <div className="flex justify-between items-center pb-2 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-900">任务监控仪表板</h1>
          <p className="text-xs text-gray-600">监控股票分析任务状态</p>
        </div>
        <button
          onClick={fetchDashboardData}
          className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors duration-200 flex items-center text-xs"
        >
          <RefreshIcon />
          <span className="ml-1">刷新</span>
        </button>
      </div>

      {/* 简化标签页导航 */}
      <div className="border border-gray-200 rounded-md overflow-hidden">
        <nav className="flex">
          <button
            onClick={() => setActiveTab('reports')}
            className={`flex-1 py-2 px-3 text-xs font-medium transition-colors duration-200 ${
              activeTab === 'reports'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:text-blue-600 hover:bg-blue-50'
            }`}
          >
            <div className="flex items-center justify-center">
              <ChartIcon />
              <span className="ml-1">报告监控</span>
            </div>
          </button>
          <div className="w-px bg-gray-200"></div>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`flex-1 py-2 px-3 text-xs font-medium transition-colors duration-200 ${
              activeTab === 'tasks'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:text-blue-600 hover:bg-blue-50'
            }`}
          >
            <div className="flex items-center justify-center">
              <TaskIcon />
              <span className="ml-1">任务统计</span>
            </div>
          </button>
        </nav>
      </div>

        {activeTab === 'reports' && reportsDashboard && (
          <div className="space-y-6">
            {/* 统计概览卡片 - 更紧凑的布局 */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-blue-600">{reportsDashboard.summary.total_stocks}</div>
                    <div className="text-gray-600 text-xs font-medium">总股票数</div>
                  </div>
                  <div className="bg-blue-100 rounded-full p-2">
                    <ChartIcon />
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-emerald-600">{reportsDashboard.summary.with_reports}</div>
                    <div className="text-gray-600 text-xs font-medium">有报告</div>
                  </div>
                  <div className="bg-emerald-100 rounded-full p-2">
                    <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2">
                  <div className="bg-emerald-100 rounded-full h-1.5">
                    <div 
                      className="bg-emerald-600 h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${(reportsDashboard.summary.with_reports / reportsDashboard.summary.total_stocks) * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-amber-600">{reportsDashboard.summary.pending_tasks}</div>
                    <div className="text-gray-600 text-xs font-medium">待处理任务</div>
                  </div>
                  <div className="bg-amber-100 rounded-full p-2">
                    <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-blue-600">{reportsDashboard.summary.running_tasks}</div>
                    <div className="text-gray-600 text-xs font-medium">运行中任务</div>
                  </div>
                  <div className="bg-blue-100 rounded-full p-2">
                    <svg className="w-4 h-4 text-blue-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-red-600">{reportsDashboard.summary.failed_tasks}</div>
                    <div className="text-gray-600 text-xs font-medium">失败任务</div>
                  </div>
                  <div className="bg-red-100 rounded-full p-2">
                    <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            {/* 股票报告表格 - 优化布局 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <ChartIcon />
                  <span className="ml-2">股票报告状态</span>
                </h3>
                <p className="text-gray-600 text-xs mt-1">监控各股票的最新报告和任务执行状态</p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        股票信息
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        最新报告
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        任务状态
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        质量评分
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {reportsDashboard.stocks.map((stock, index) => (
                      <tr key={stock.symbol} className={`hover:bg-blue-50 transition-colors duration-200 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="flex-shrink-0 h-8 w-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                              <span className="text-white font-bold text-xs">{stock.symbol.slice(-2)}</span>
                            </div>
                            <div className="ml-3">
                              <div className="text-sm font-bold text-gray-900">{stock.symbol}</div>
                              <div className="text-xs text-gray-600">{stock.name}</div>
                              <div className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full inline-block mt-0.5">{stock.sector}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {stock.latest_report ? (
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-2">
                              <div className="text-xs font-semibold text-blue-900 flex items-center">
                                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm0 2h12v8H4V6z" />
                                </svg>
                                版本 {stock.latest_report.version}
                              </div>
                              <div className="text-xs text-blue-600 mt-0.5">
                                {formatDateTime(stock.latest_report.created_at)}
                              </div>
                            </div>
                          ) : (
                            <div className="bg-gray-100 border border-gray-200 rounded-lg p-2 text-center">
                              <span className="text-xs text-gray-500">暂无报告</span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {stock.current_task ? (
                            <div className="space-y-1">
                              <span className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadgeClass(stock.current_task.status)}`}>
                                {getStatusIcon(stock.current_task.status)}
                                {stock.current_task.status}
                              </span>
                              <div className="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                                优先级: {stock.current_task.priority}
                              </div>
                              {stock.current_task.error_message && (
                                <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-1 max-w-xs" title={stock.current_task.error_message}>
                                  <svg className="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                  </svg>
                                  {stock.current_task.error_message.substring(0, 20)}...
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded-full">
                              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                              </svg>
                              无任务
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {stock.latest_report ? (
                            <div className="space-y-1">
                              <div className={`p-1.5 rounded-lg border ${getQualityScoreBackground(stock.latest_report.data_quality_score)}`}>
                                <div className={`text-xs font-semibold ${getQualityScoreColor(stock.latest_report.data_quality_score)}`}>
                                  数据质量: {(stock.latest_report.data_quality_score * 100).toFixed(0)}%
                                </div>
                                <div className="bg-gray-200 rounded-full h-1 mt-0.5">
                                  <div 
                                    className={`h-1 rounded-full transition-all duration-500 ${
                                      stock.latest_report.data_quality_score >= 0.8 ? 'bg-emerald-500' :
                                      stock.latest_report.data_quality_score >= 0.6 ? 'bg-amber-500' : 'bg-red-500'
                                    }`}
                                    style={{ width: `${stock.latest_report.data_quality_score * 100}%` }}
                                  ></div>
                                </div>
                              </div>
                              <div className={`p-1.5 rounded-lg border ${getQualityScoreBackground(stock.latest_report.prediction_confidence)}`}>
                                <div className={`text-xs font-semibold ${getQualityScoreColor(stock.latest_report.prediction_confidence)}`}>
                                  预测信心: {(stock.latest_report.prediction_confidence * 100).toFixed(0)}%
                                </div>
                                <div className="bg-gray-200 rounded-full h-1 mt-0.5">
                                  <div 
                                    className={`h-1 rounded-full transition-all duration-500 ${
                                      stock.latest_report.prediction_confidence >= 0.8 ? 'bg-emerald-500' :
                                      stock.latest_report.prediction_confidence >= 0.6 ? 'bg-amber-500' : 'bg-red-500'
                                    }`}
                                    style={{ width: `${stock.latest_report.prediction_confidence * 100}%` }}
                                  ></div>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <span className="text-xs text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">
                          <button
                            onClick={() => createReportTask(stock.symbol)}
                            disabled={stock.current_task?.status === 'running' || stock.current_task?.status === 'pending'}
                            className={`inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                              stock.current_task?.status === 'running' || stock.current_task?.status === 'pending'
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md'
                            }`}
                          >
                            <PlayIcon />
                            <span className="ml-1">生成报告</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'tasks' && tasksDashboard && (
          <div className="space-y-6">
            {/* 任务统计卡片 - 更紧凑的布局 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center mb-4">
                  <div className="bg-blue-100 rounded-full p-2 mr-3">
                    <TaskIcon />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">任务状态统计</h3>
                </div>
                <div className="space-y-3">
                  {Object.entries(tasksDashboard.status_statistics).map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200">
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadgeClass(status)}`}>
                        {getStatusIcon(status)}
                        {status}
                      </span>
                      <div className="flex items-center">
                        <span className="text-xl font-bold text-gray-900 mr-2">{count}</span>
                        <span className="text-xs text-gray-500">个任务</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center mb-4">
                  <div className="bg-purple-100 rounded-full p-2 mr-3">
                    <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">任务类型统计</h3>
                </div>
                <div className="space-y-3">
                  {Object.entries(tasksDashboard.type_statistics).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200">
                      <div className="flex items-center">
                        <div className="bg-purple-100 rounded-full p-1.5 mr-2">
                          <svg className="w-3 h-3 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                          </svg>
                        </div>
                        <span className="text-sm font-medium text-gray-900">{type}</span>
                      </div>
                      <div className="flex items-center">
                        <span className="text-xl font-bold text-gray-900 mr-2">{count}</span>
                        <span className="text-xs text-gray-500">个</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 最近任务表格 - 优化布局 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  最近24小时任务
                </h3>
                <p className="text-gray-600 text-xs mt-1">查看最近任务的执行详情和状态</p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        股票代码
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        任务类型
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        状态
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        创建时间
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        完成时间
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        错误信息
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {tasksDashboard.recent_tasks.map((task, index) => (
                      <tr key={index} className={`hover:bg-blue-50 transition-colors duration-200 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="flex-shrink-0 h-6 w-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                              <span className="text-white font-bold text-xs">{task.symbol.slice(-2)}</span>
                            </div>
                            <div className="ml-2">
                              <div className="text-sm font-bold text-gray-900">{task.symbol}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="bg-indigo-100 rounded-full p-1 mr-2">
                              <svg className="w-3 h-3 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                            </div>
                            <span className="text-xs font-medium text-gray-900">{task.task_type}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadgeClass(task.status)}`}>
                            {getStatusIcon(task.status)}
                            {task.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="text-xs text-gray-900 font-medium">{formatDateTime(task.created_at)}</div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="text-xs text-gray-900 font-medium">
                            {task.completed_at ? formatDateTime(task.completed_at) : (
                              <span className="text-gray-400 italic">进行中...</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {task.error_message ? (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-1.5 max-w-xs">
                              <div className="flex items-start">
                                <svg className="w-3 h-3 text-red-500 mr-1 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                                <span className="text-xs text-red-700">{task.error_message}</span>
                              </div>
                            </div>
                          ) : (
                            <span className="text-xs text-gray-400">无错误</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
    </div>
  );
};

export default Dashboard;
