import React, { useState, useEffect } from 'react';

// 统一的图标组件 - 模块化设计
const RefreshIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const ChartIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
  </svg>
);

const TaskIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
  </svg>
);

const StatsIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
  </svg>
);

const ActionIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const LoadingSpinner = () => (
  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4}></circle>
    <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

// 数据类型定义
interface DashboardData {
  totalStocks: number;
  completedReports: number;
  pendingReports: number;
  failedReports: number;
  reports: Array<{
    stockCode: string;
    latestVersion: string;
    status: string;
    lastUpdate: string;
  }>;
}

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData>({
    totalStocks: 0,
    completedReports: 0,
    pendingReports: 0,
    failedReports: 0,
    reports: []
  });
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'reports' | 'tasks'>('reports');

  const fetchDashboardData = async (isRefresh: boolean = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const API_BASE = (window as any).API_BASE || 'http://localhost:8083';
      const response = await fetch(`${API_BASE}/api/dashboard/reports`);

      if (!response.ok) {
        throw new Error(`API请求失败: ${response.statusText}`);
      }

      const data = await response.json();
      
      // 转换数据格式 - 修复数据映射
      const transformedData: DashboardData = {
        totalStocks: data.summary?.total_stocks || 0,
        completedReports: data.summary?.with_reports || 0,
        pendingReports: data.summary?.pending_tasks || 0,
        failedReports: data.summary?.failed_tasks || 0,
        reports: data.stocks?.map((stock: any) => ({
          stockCode: stock.symbol,
          latestVersion: stock.latest_report?.version || '未生成',
          status: stock.current_task?.status || (stock.latest_report ? 'completed' : 'unknown'),
          lastUpdate: stock.latest_report?.created_at ? 
            new Date(stock.latest_report.created_at).toLocaleString('zh-CN') : 
            stock.current_task?.completed_at ? 
              new Date(stock.current_task.completed_at).toLocaleString('zh-CN') : '未更新'
        })) || []
      };

      setDashboardData(transformedData);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      if (isRefresh) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  };

  const handleRefresh = () => {
    fetchDashboardData(true);
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'running': return 'bg-blue-100 text-blue-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return '已完成';
      case 'running': return '执行中';
      case 'pending': return '等待中';
      case 'failed': return '失败';
      default: return '未知';
    }
  };

  const retryReport = async (stockCode: string) => {
    try {
      const API_BASE = (window as any).API_BASE || 'http://localhost:8083';
      const response = await fetch(`${API_BASE}/api/tasks/report/${stockCode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority: 1 })
      });

      if (response.ok) {
        fetchDashboardData();
      }
    } catch (err) {
      console.error('Retry error:', err);
    }
  };

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        backgroundColor: '#f9fafb', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        padding: '20px'
      }}>
        <div style={{ 
          backgroundColor: 'white', 
          borderRadius: '12px', 
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)', 
          border: '1px solid #e5e7eb', 
          padding: '40px', 
          textAlign: 'center',
          maxWidth: '400px',
          width: '100%'
        }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            marginBottom: '20px' 
          }}>
            <LoadingSpinner />
          </div>
          <div style={{ 
            fontSize: '18px', 
            color: '#4b5563', 
            fontWeight: '500',
            marginBottom: '8px' 
          }}>
            加载仪表板数据...
          </div>
          <div style={{ 
            fontSize: '14px', 
            color: '#6b7280' 
          }}>
            请稍候，正在获取最新信息
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        backgroundColor: '#f9fafb', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        padding: '20px'
      }}>
        <div style={{ 
          backgroundColor: 'white', 
          borderRadius: '12px', 
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)', 
          border: '1px solid #fca5a5', 
          padding: '40px', 
          maxWidth: '400px',
          width: '100%',
          textAlign: 'center'
        }}>
          <div style={{ 
            backgroundColor: '#fee2e2', 
            borderRadius: '50%', 
            padding: '12px', 
            width: '48px', 
            height: '48px', 
            margin: '0 auto 16px auto', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center'
          }}>
            <svg style={{ width: '24px', height: '24px', color: '#dc2626' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 style={{ 
            fontSize: '18px', 
            fontWeight: '600', 
            color: '#991b1b', 
            marginBottom: '8px' 
          }}>
            加载失败
          </h3>
          <p style={{ 
            color: '#dc2626', 
            marginBottom: '24px',
            fontSize: '14px'
          }}>
            {error}
          </p>
          <button
            onClick={() => fetchDashboardData(false)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto',
              padding: '8px 16px',
              backgroundColor: '#dc2626',
              color: 'white',
              borderRadius: '8px',
              border: 'none',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => {
              (e.target as HTMLButtonElement).style.backgroundColor = '#b91c1c';
            }}
            onMouseOut={(e) => {
              (e.target as HTMLButtonElement).style.backgroundColor = '#dc2626';
            }}
          >
            <RefreshIcon />
            <span style={{ marginLeft: '8px' }}>重试</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '16px', 
      backgroundColor: '#f9fafb', 
      minHeight: '100vh' 
    }}>
      <div style={{ 
        maxWidth: '1200px', 
        margin: '0 auto' 
      }}>
        {/* 页头区域 */}
        <div style={{ 
          backgroundColor: 'white', 
          borderRadius: '8px', 
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)', 
          border: '1px solid #e5e7eb', 
          padding: '16px', 
          marginBottom: '16px'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px'
          }}>
            <h1 style={{ 
              fontSize: '20px', 
              fontWeight: 'bold', 
              color: '#111827',
              margin: 0
            }}>
              任务监控
            </h1>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              flexWrap: 'wrap'
            }}>
              <button
                onClick={handleRefresh}
                disabled={loading || refreshing}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '6px 12px',
                  backgroundColor: (loading || refreshing) ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: (loading || refreshing) ? 'not-allowed' : 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => {
                  if (!loading && !refreshing) {
                    (e.target as HTMLButtonElement).style.backgroundColor = '#1d4ed8';
                  }
                }}
                onMouseOut={(e) => {
                  if (!loading && !refreshing) {
                    (e.target as HTMLButtonElement).style.backgroundColor = '#2563eb';
                  }
                }}
              >
                {refreshing ? (
                  <LoadingSpinner />
                ) : (
                  <RefreshIcon />
                )}
                <span style={{ marginLeft: '4px' }}>
                  {refreshing ? '刷新中...' : loading ? '加载中...' : '刷新'}
                </span>
              </button>
              <button
                onClick={() => setActiveTab('reports')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '6px 12px',
                  fontSize: '14px',
                  fontWeight: '500',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  backgroundColor: activeTab === 'reports' ? '#2563eb' : '#f3f4f6',
                  color: activeTab === 'reports' ? 'white' : '#4b5563'
                }}
                onMouseOver={(e) => {
                  if (activeTab !== 'reports') {
                    (e.target as HTMLButtonElement).style.backgroundColor = '#e5e7eb';
                  }
                }}
                onMouseOut={(e) => {
                  if (activeTab !== 'reports') {
                    (e.target as HTMLButtonElement).style.backgroundColor = '#f3f4f6';
                  }
                }}
              >
                <ChartIcon />
                <span style={{ marginLeft: '4px' }}>报告</span>
              </button>
              <button
                onClick={() => setActiveTab('tasks')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '6px 12px',
                  fontSize: '14px',
                  fontWeight: '500',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  backgroundColor: activeTab === 'tasks' ? '#2563eb' : '#f3f4f6',
                  color: activeTab === 'tasks' ? 'white' : '#4b5563'
                }}
                onMouseOver={(e) => {
                  if (activeTab !== 'tasks') {
                    (e.target as HTMLButtonElement).style.backgroundColor = '#e5e7eb';
                  }
                }}
                onMouseOut={(e) => {
                  if (activeTab !== 'tasks') {
                    (e.target as HTMLButtonElement).style.backgroundColor = '#f3f4f6';
                  }
                }}
              >
                <TaskIcon />
                <span style={{ marginLeft: '4px' }}>统计</span>
              </button>
            </div>
          </div>
        </div>

        {/* 内容区域 */}
        <div style={{ 
          backgroundColor: 'white', 
          borderRadius: '8px', 
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)', 
          border: '1px solid #e5e7eb',
          position: 'relative'
        }}>
          {/* 刷新遮罩层 */}
          {refreshing && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
              backdropFilter: 'blur(2px)'
            }}>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px'
              }}>
                <LoadingSpinner />
                <div style={{
                  fontSize: '14px',
                  color: '#6b7280',
                  fontWeight: '500'
                }}>
                  正在刷新数据...
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'reports' && (
            <div style={{ padding: '16px' }}>
              {/* 统计数据区域 */}
              <div style={{ marginBottom: '24px' }}>
                <h3 style={{ 
                  fontSize: '18px', 
                  fontWeight: '500', 
                  color: '#111827', 
                  marginBottom: '16px' 
                }}>
                  股票分析状态
                </h3>
                
                {/* 统计卡片 - 强制横向布局 */}
                <div style={{ 
                  display: 'flex', 
                  gap: '16px', 
                  flexWrap: 'wrap',
                  justifyContent: 'space-between',
                  opacity: refreshing ? 0.6 : 1,
                  transition: 'opacity 0.3s ease'
                }}>
                  <div style={{ 
                    flex: '1',
                    minWidth: '200px',
                    backgroundColor: '#f9fafb', 
                    borderRadius: '8px', 
                    padding: '24px 16px', 
                    border: '1px solid #e5e7eb',
                    textAlign: 'center',
                    transform: refreshing ? 'scale(0.98)' : 'scale(1)',
                    transition: 'transform 0.3s ease'
                  }}>
                    <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#374151', marginBottom: '8px' }}>
                      {dashboardData.totalStocks}
                    </div>
                    <div style={{ fontSize: '14px', color: '#6b7280', fontWeight: '500' }}>总数</div>
                  </div>
                  
                  <div style={{ 
                    flex: '1',
                    minWidth: '200px',
                    backgroundColor: '#f0fdf4', 
                    borderRadius: '8px', 
                    padding: '24px 16px', 
                    border: '1px solid #bbf7d0',
                    textAlign: 'center',
                    transform: refreshing ? 'scale(0.98)' : 'scale(1)',
                    transition: 'transform 0.3s ease'
                  }}>
                    <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#047857', marginBottom: '8px' }}>
                      {dashboardData.completedReports}
                    </div>
                    <div style={{ fontSize: '14px', color: '#059669', fontWeight: '500' }}>完成</div>
                  </div>
                  
                  <div style={{ 
                    flex: '1',
                    minWidth: '200px',
                    backgroundColor: '#eff6ff', 
                    borderRadius: '8px', 
                    padding: '24px 16px', 
                    border: '1px solid #93c5fd',
                    textAlign: 'center',
                    transform: refreshing ? 'scale(0.98)' : 'scale(1)',
                    transition: 'transform 0.3s ease'
                  }}>
                    <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#1d4ed8', marginBottom: '8px' }}>
                      {dashboardData.pendingReports}
                    </div>
                    <div style={{ fontSize: '14px', color: '#2563eb', fontWeight: '500' }}>进行</div>
                  </div>
                  
                  <div style={{ 
                    flex: '1',
                    minWidth: '200px',
                    backgroundColor: '#fef2f2', 
                    borderRadius: '8px', 
                    padding: '24px 16px', 
                    border: '1px solid #fecaca',
                    textAlign: 'center',
                    transform: refreshing ? 'scale(0.98)' : 'scale(1)',
                    transition: 'transform 0.3s ease'
                  }}>
                    <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#dc2626', marginBottom: '8px' }}>
                      {dashboardData.failedReports}
                    </div>
                    <div style={{ fontSize: '14px', color: '#dc2626', fontWeight: '500' }}>失败</div>
                  </div>
                </div>
              </div>

              {/* 数据表格 - 优化样式 */}
              <div style={{ 
                border: '1px solid #e5e7eb', 
                borderRadius: '8px', 
                overflow: 'hidden',
                backgroundColor: 'white',
                opacity: refreshing ? 0.6 : 1,
                transform: refreshing ? 'scale(0.99)' : 'scale(1)',
                transition: 'opacity 0.3s ease, transform 0.3s ease'
              }}>
                <div style={{ 
                  backgroundColor: '#f9fafb', 
                  padding: '16px', 
                  borderBottom: '1px solid #e5e7eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <h4 style={{ fontSize: '16px', fontWeight: '600', color: '#111827', margin: 0 }}>
                    股票分析详情
                  </h4>
                  <span style={{ fontSize: '14px', color: '#6b7280' }}>
                    共 {dashboardData.reports.length} 条记录
                  </span>
                </div>
                
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead style={{ backgroundColor: '#f9fafb' }}>
                    <tr>
                      <th style={{ 
                        padding: '12px 16px', 
                        textAlign: 'left', 
                        fontSize: '12px', 
                        fontWeight: '500', 
                        color: '#6b7280',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        股票代码
                      </th>
                      <th style={{ 
                        padding: '12px 16px', 
                        textAlign: 'left', 
                        fontSize: '12px', 
                        fontWeight: '500', 
                        color: '#6b7280',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        最新版本
                      </th>
                      <th style={{ 
                        padding: '12px 16px', 
                        textAlign: 'left', 
                        fontSize: '12px', 
                        fontWeight: '500', 
                        color: '#6b7280',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        执行状态
                      </th>
                      <th style={{ 
                        padding: '12px 16px', 
                        textAlign: 'left', 
                        fontSize: '12px', 
                        fontWeight: '500', 
                        color: '#6b7280',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        更新时间
                      </th>
                      <th style={{ 
                        padding: '12px 16px', 
                        textAlign: 'center', 
                        fontSize: '12px', 
                        fontWeight: '500', 
                        color: '#6b7280',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardData.reports.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ 
                          padding: '48px 16px', 
                          textAlign: 'center', 
                          fontSize: '14px', 
                          color: '#6b7280' 
                        }}>
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <div style={{ 
                              backgroundColor: '#f3f4f6', 
                              borderRadius: '50%', 
                              padding: '12px', 
                              marginBottom: '16px' 
                            }}>
                              <ChartIcon className="w-6 h-6 text-gray-400" />
                            </div>
                            <div style={{ fontSize: '16px', fontWeight: '500', color: '#111827', marginBottom: '8px' }}>
                              暂无数据
                            </div>
                            <div style={{ fontSize: '14px', color: '#6b7280' }}>
                              当前没有股票报告数据
                            </div>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      dashboardData.reports.map((report, index) => (
                        <tr key={report.stockCode} style={{ 
                          backgroundColor: index % 2 === 0 ? 'white' : '#fafafa',
                          borderTop: '1px solid #f3f4f6'
                        }}>
                          <td style={{ 
                            padding: '16px', 
                            fontSize: '14px', 
                            fontWeight: '600', 
                            color: '#111827' 
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                              <div style={{ 
                                backgroundColor: '#dbeafe', 
                                borderRadius: '6px', 
                                padding: '6px 8px', 
                                marginRight: '12px',
                                fontSize: '12px',
                                fontWeight: 'bold',
                                color: '#1d4ed8'
                              }}>
                                {report.stockCode.slice(-2)}
                              </div>
                              {report.stockCode}
                            </div>
                          </td>
                          <td style={{ 
                            padding: '16px', 
                            fontSize: '14px', 
                            color: '#6b7280',
                            fontFamily: 'monospace'
                          }}>
                            {report.latestVersion || '未生成'}
                          </td>
                          <td style={{ padding: '16px' }}>
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '4px 12px',
                              borderRadius: '9999px',
                              fontSize: '12px',
                              fontWeight: '500',
                              backgroundColor: report.status === 'completed' ? '#dcfce7' :
                                             report.status === 'running' ? '#dbeafe' :
                                             report.status === 'pending' ? '#fef3c7' :
                                             report.status === 'failed' ? '#fee2e2' : '#f3f4f6',
                              color: report.status === 'completed' ? '#166534' :
                                    report.status === 'running' ? '#1e40af' :
                                    report.status === 'pending' ? '#92400e' :
                                    report.status === 'failed' ? '#991b1b' : '#374151'
                            }}>
                              <span style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                marginRight: '8px',
                                backgroundColor: report.status === 'completed' ? '#10b981' :
                                               report.status === 'running' ? '#3b82f6' :
                                               report.status === 'pending' ? '#f59e0b' : '#ef4444'
                              }}></span>
                              {getStatusText(report.status)}
                            </span>
                          </td>
                          <td style={{ 
                            padding: '16px', 
                            fontSize: '14px', 
                            color: '#6b7280' 
                          }}>
                            {report.lastUpdate || '未更新'}
                          </td>
                          <td style={{ padding: '16px', textAlign: 'center' }}>
                            <button
                              onClick={() => retryReport(report.stockCode)}
                              disabled={report.status === 'running'}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '6px 12px',
                                fontSize: '12px',
                                fontWeight: '500',
                                borderRadius: '6px',
                                border: '1px solid #3b82f6',
                                backgroundColor: report.status === 'running' ? '#f3f4f6' : '#eff6ff',
                                color: report.status === 'running' ? '#9ca3af' : '#1d4ed8',
                                cursor: report.status === 'running' ? 'not-allowed' : 'pointer',
                                transition: 'all 0.2s'
                              }}
                              onMouseOver={(e) => {
                                if (report.status !== 'running') {
                                  (e.target as HTMLButtonElement).style.backgroundColor = '#dbeafe';
                                }
                              }}
                              onMouseOut={(e) => {
                                if (report.status !== 'running') {
                                  (e.target as HTMLButtonElement).style.backgroundColor = '#eff6ff';
                                }
                              }}
                            >
                              <ActionIcon className="w-3 h-3 mr-1" />
                              重新执行
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'tasks' && (
            <div style={{ padding: '24px' }}>
              {/* 统计概览区域 */}
              <div style={{ marginBottom: '32px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', marginBottom: '16px' }}>
                  任务执行统计
                </h3>
                
                {/* 统计图表区域 */}
                <div style={{ 
                  display: 'flex', 
                  gap: '24px', 
                  flexWrap: 'wrap',
                  marginBottom: '32px'
                }}>
                  {/* 成功率统计 */}
                  <div style={{ 
                    flex: '1',
                    minWidth: '300px',
                    backgroundColor: '#f8fafc', 
                    borderRadius: '12px', 
                    padding: '24px', 
                    border: '1px solid #e2e8f0'
                  }}>
                    <h4 style={{ fontSize: '16px', fontWeight: '600', color: '#1e293b', marginBottom: '16px' }}>
                      总体成功率
                    </h4>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
                      <div style={{ 
                        fontSize: '36px', 
                        fontWeight: 'bold', 
                        color: '#059669',
                        marginRight: '12px'
                      }}>
                        {dashboardData.totalStocks > 0 ? 
                          Math.round((dashboardData.completedReports / dashboardData.totalStocks) * 100) : 0}%
                      </div>
                      <div style={{ fontSize: '14px', color: '#64748b' }}>
                        {dashboardData.completedReports} / {dashboardData.totalStocks} 任务完成
                      </div>
                    </div>
                    <div style={{ 
                      width: '100%', 
                      height: '8px', 
                      backgroundColor: '#e2e8f0', 
                      borderRadius: '4px',
                      overflow: 'hidden'
                    }}>
                      <div style={{ 
                        height: '100%', 
                        backgroundColor: '#10b981',
                        width: `${dashboardData.totalStocks > 0 ? (dashboardData.completedReports / dashboardData.totalStocks) * 100 : 0}%`,
                        transition: 'width 0.3s ease'
                      }}></div>
                    </div>
                  </div>
                  
                  {/* 任务分布统计 */}
                  <div style={{ 
                    flex: '1',
                    minWidth: '300px',
                    backgroundColor: '#f8fafc', 
                    borderRadius: '12px', 
                    padding: '24px', 
                    border: '1px solid #e2e8f0'
                  }}>
                    <h4 style={{ fontSize: '16px', fontWeight: '600', color: '#1e293b', marginBottom: '16px' }}>
                      任务状态分布
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <div style={{ 
                            width: '12px', 
                            height: '12px', 
                            backgroundColor: '#10b981', 
                            borderRadius: '50%', 
                            marginRight: '8px' 
                          }}></div>
                          <span style={{ fontSize: '14px', color: '#374151' }}>已完成</span>
                        </div>
                        <span style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>
                          {dashboardData.completedReports}
                        </span>
                      </div>
                      
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <div style={{ 
                            width: '12px', 
                            height: '12px', 
                            backgroundColor: '#3b82f6', 
                            borderRadius: '50%', 
                            marginRight: '8px' 
                          }}></div>
                          <span style={{ fontSize: '14px', color: '#374151' }}>进行中</span>
                        </div>
                        <span style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>
                          {dashboardData.pendingReports}
                        </span>
                      </div>
                      
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <div style={{ 
                            width: '12px', 
                            height: '12px', 
                            backgroundColor: '#ef4444', 
                            borderRadius: '50%', 
                            marginRight: '8px' 
                          }}></div>
                          <span style={{ fontSize: '14px', color: '#374151' }}>失败</span>
                        </div>
                        <span style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>
                          {dashboardData.failedReports}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* 详细统计表格 */}
                <div style={{ 
                  backgroundColor: 'white', 
                  borderRadius: '12px', 
                  border: '1px solid #e2e8f0',
                  overflow: 'hidden'
                }}>
                  <div style={{ 
                    backgroundColor: '#f8fafc', 
                    padding: '16px 24px', 
                    borderBottom: '1px solid #e2e8f0'
                  }}>
                    <h4 style={{ fontSize: '16px', fontWeight: '600', color: '#1e293b', margin: 0 }}>
                      任务执行详情统计
                    </h4>
                  </div>
                  
                  <div style={{ padding: '24px' }}>
                    <div style={{ 
                      display: 'grid', 
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                      gap: '16px'
                    }}>
                      <div style={{ 
                        padding: '16px', 
                        backgroundColor: '#f0f9ff', 
                        borderRadius: '8px',
                        border: '1px solid #bae6fd'
                      }}>
                        <div style={{ fontSize: '14px', color: '#0369a1', marginBottom: '4px' }}>
                          平均执行时间
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#0c4a6e' }}>
                          ~ 2.5分钟
                        </div>
                      </div>
                      
                      <div style={{ 
                        padding: '16px', 
                        backgroundColor: '#ecfdf5', 
                        borderRadius: '8px',
                        border: '1px solid #a7f3d0'
                      }}>
                        <div style={{ fontSize: '14px', color: '#047857', marginBottom: '4px' }}>
                          今日完成任务
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#064e3b' }}>
                          {dashboardData.completedReports}
                        </div>
                      </div>
                      
                      <div style={{ 
                        padding: '16px', 
                        backgroundColor: '#fefce8', 
                        borderRadius: '8px',
                        border: '1px solid #fde047'
                      }}>
                        <div style={{ fontSize: '14px', color: '#a16207', marginBottom: '4px' }}>
                          待处理任务
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#713f12' }}>
                          {dashboardData.pendingReports}
                        </div>
                      </div>
                      
                      <div style={{ 
                        padding: '16px', 
                        backgroundColor: '#fef2f2', 
                        borderRadius: '8px',
                        border: '1px solid #fca5a5'
                      }}>
                        <div style={{ fontSize: '14px', color: '#dc2626', marginBottom: '4px' }}>
                          失败重试次数
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#991b1b' }}>
                          {dashboardData.failedReports}
                        </div>
                      </div>
                    </div>
                    
                    {/* 系统状态指示 */}
                    <div style={{ 
                      marginTop: '24px', 
                      padding: '16px', 
                      backgroundColor: '#f8fafc',
                      borderRadius: '8px',
                      border: '1px solid #e2e8f0'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: '600', color: '#1e293b', marginBottom: '4px' }}>
                            系统运行状态
                          </div>
                          <div style={{ fontSize: '12px', color: '#64748b' }}>
                            最后更新: {new Date().toLocaleString('zh-CN')}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <div style={{ 
                            width: '8px', 
                            height: '8px', 
                            backgroundColor: '#10b981', 
                            borderRadius: '50%', 
                            marginRight: '8px',
                            animation: 'pulse 2s infinite'
                          }}></div>
                          <span style={{ fontSize: '14px', color: '#059669', fontWeight: '500' }}>
                            正常运行
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
