/**
 * Tasks Management Page
 *
 * Full-featured task management interface with:
 * - Task list with filtering
 * - Task creation form
 * - Task detail view
 * - Execution history
 */
import { useState, useEffect, useCallback } from 'react';
import {
  CalendarClock,
  RefreshCw,
  Play,
  Pause,
  Trash2,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  Activity,
  TrendingUp,
  Bell,
  Newspaper,
  Briefcase,
  Search,
  ArrowLeft,
  X,
  Settings,
  History,
  Info,
} from 'lucide-react';
import {
  getTasks,
  getTaskStats,
  getTask,
  triggerTask,
  pauseTask,
  cancelTask,
  resumeTask,
  deleteTask,
  getTaskExecutions,
  searchTaskResults,
  TaskSummary,
  TaskStats,
  TaskExecution,
} from '../services/api';

// Action type configuration
const actionTypeConfig: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  stock_alert: { icon: <Bell size={16} />, label: '价格警报', color: 'text-yellow-400' },
  stock_analysis: { icon: <TrendingUp size={16} />, label: '股票分析', color: 'text-green-400' },
  portfolio_monitor: { icon: <Briefcase size={16} />, label: '组合监控', color: 'text-blue-400' },
  news_watch: { icon: <Newspaper size={16} />, label: '新闻监控', color: 'text-purple-400' },
  custom: { icon: <Settings size={16} />, label: '自定义', color: 'text-gray-400' },
};

// Status configuration
const statusConfig: Record<string, { icon: React.ReactNode; label: string; color: string; bgColor: string }> = {
  pending: { icon: <Clock size={14} />, label: '等待中', color: 'text-gray-400', bgColor: 'bg-gray-500/20' },
  scheduled: { icon: <CalendarClock size={14} />, label: '已调度', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  running: { icon: <Activity size={14} />, label: '运行中', color: 'text-green-400', bgColor: 'bg-green-500/20' },
  completed: { icon: <CheckCircle size={14} />, label: '已完成', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
  paused: { icon: <Pause size={14} />, label: '已暂停', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' },
  cancelled: { icon: <XCircle size={14} />, label: '已取消', color: 'text-gray-500', bgColor: 'bg-gray-600/20' },
  failed: { icon: <AlertCircle size={14} />, label: '失败', color: 'text-red-400', bgColor: 'bg-red-500/20' },
};

interface TasksPageProps {
  onBack: () => void;
}

export default function TasksPage({ onBack }: TasksPageProps) {
  // State
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected task
  const [selectedTask, setSelectedTask] = useState<TaskSummary | null>(null);
  const [taskExecutions, setTaskExecutions] = useState<TaskExecution[]>([]);
  const [loadingExecutions, setLoadingExecutions] = useState(false);

  // Search results
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);

  // Fetch tasks
  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [tasksData, statsData] = await Promise.all([
        getTasks(statusFilter || undefined, typeFilter || undefined),
        getTaskStats(),
      ]);
      setTasks(tasksData.tasks);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, typeFilter]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Fetch task details
  const fetchTaskDetail = async (taskId: string) => {
    setLoadingExecutions(true);
    try {
      const [taskData, execData] = await Promise.all([
        getTask(taskId),
        getTaskExecutions(taskId, 20),
      ]);
      setSelectedTask(taskData);
      setTaskExecutions(execData.executions);
    } catch (err) {
      console.error('Failed to fetch task details:', err);
    } finally {
      setLoadingExecutions(false);
    }
  };

  // Search
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const results = await searchTaskResults(searchQuery);
      setSearchResults(results.results);
      setShowSearchResults(true);
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  // Task actions
  const handleTrigger = async (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await triggerTask(taskId);
      await fetchTasks();
      if (selectedTask?.id === taskId) {
        await fetchTaskDetail(taskId);
      }
    } catch (err) {
      console.error('Failed to trigger task:', err);
    }
  };

  const handlePause = async (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await pauseTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to pause task:', err);
    }
  };

  const handleCancel = async (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await cancelTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to cancel task:', err);
    }
  };

  const handleResume = async (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await resumeTask(taskId);
      await fetchTasks();
      if (selectedTask?.id === taskId) {
        await fetchTaskDetail(taskId);
      }
    } catch (err) {
      console.error('Failed to resume task:', err);
    }
  };

  const handleDelete = async (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!confirm('确定要删除这个任务吗？')) return;
    try {
      await deleteTask(taskId);
      if (selectedTask?.id === taskId) {
        setSelectedTask(null);
      }
      await fetchTasks();
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
  };

  // Format helpers
  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const formatFullTime = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleString('zh-CN');
    } catch {
      return dateStr;
    }
  };

  // Render execution result
  const renderExecutionResult = (exec: TaskExecution) => {
    const data = exec.result;
    if (!data || Object.keys(data).length === 0) return null;

    // Stock alert
    if ('triggered' in data) {
      return (
        <div className="mt-2 p-2 bg-gray-800 rounded text-xs">
          <div className="flex items-center gap-2 mb-1">
            {data.triggered ? (
              <span className="text-yellow-400 font-medium">🔔 已触发</span>
            ) : (
              <span className="text-gray-400">⏳ 未触发</span>
            )}
          </div>
          {data.symbol && <div>股票: <span className="text-white">{data.symbol}</span></div>}
          {data.current_price && <div>价格: <span className="text-white">${data.current_price.toFixed(2)}</span></div>}
          {data.change_percent !== undefined && (
            <div>涨跌: <span className={data.change_percent >= 0 ? 'text-green-400' : 'text-red-400'}>
              {data.change_percent >= 0 ? '+' : ''}{data.change_percent.toFixed(2)}%
            </span></div>
          )}
        </div>
      );
    }

    // Stock analysis
    if ('analyses' in data) {
      const analyses = data.analyses || {};
      return (
        <div className="mt-2 p-2 bg-gray-800 rounded text-xs">
          {data.symbol && <div className="font-medium text-white mb-1">{data.symbol}</div>}
          {data.current_price && <div>价格: ${data.current_price.toFixed(2)}</div>}
          <div className="grid grid-cols-3 gap-2 mt-1">
            {analyses.technical?.trend && (
              <div>
                <span className="text-gray-500">技术:</span>{' '}
                <span className={analyses.technical.trend === 'bullish' ? 'text-green-400' : analyses.technical.trend === 'bearish' ? 'text-red-400' : 'text-gray-400'}>
                  {analyses.technical.trend}
                </span>
              </div>
            )}
            {analyses.fundamental?.rating && (
              <div>
                <span className="text-gray-500">基本面:</span>{' '}
                <span className="text-blue-400">{analyses.fundamental.rating}</span>
              </div>
            )}
            {analyses.sentiment?.overall_sentiment && (
              <div>
                <span className="text-gray-500">情绪:</span>{' '}
                <span className="text-purple-400">{analyses.sentiment.overall_sentiment}</span>
              </div>
            )}
          </div>
        </div>
      );
    }

    // Portfolio
    if ('total_value' in data) {
      return (
        <div className="mt-2 p-2 bg-gray-800 rounded text-xs">
          <div>组合价值: <span className="text-white">${data.total_value.toLocaleString()}</span></div>
          {data.change_pct !== undefined && (
            <div>变化: <span className={data.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
              {data.change_pct >= 0 ? '+' : ''}{data.change_pct.toFixed(2)}%
            </span></div>
          )}
        </div>
      );
    }

    // News
    if ('news_count' in data) {
      return (
        <div className="mt-2 p-2 bg-gray-800 rounded text-xs">
          <div>新闻数量: <span className="text-white">{data.news_count}</span></div>
          {data.news && data.news.length > 0 && (
            <div className="mt-1">
              {data.news.slice(0, 2).map((n: any, i: number) => (
                <div key={i} className="truncate text-gray-400">• {n.title}</div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // Generic
    return (
      <div className="mt-2 p-2 bg-gray-800 rounded text-xs">
        <pre className="text-gray-400 overflow-x-auto">
          {JSON.stringify(data, null, 2).slice(0, 200)}
        </pre>
      </div>
    );
  };

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="h-14 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-700 rounded-lg transition"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-2">
            <CalendarClock size={20} className="text-blue-400" />
            <span className="font-medium">任务管理</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Stats */}
          {stats && (
            <div className="flex items-center gap-4 text-sm mr-4">
              <span className="text-gray-400">
                总计 <span className="text-white font-medium">{stats.total_tasks}</span>
              </span>
              <span className="text-blue-400">
                调度中 {stats.scheduled_tasks}
              </span>
              <span className="text-green-400">
                运行中 {stats.running_tasks}
              </span>
              {stats.failed_tasks > 0 && (
                <span className="text-red-400">
                  失败 {stats.failed_tasks}
                </span>
              )}
            </div>
          )}

          <button
            onClick={fetchTasks}
            disabled={isLoading}
            className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition disabled:opacity-50"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel - Task list */}
        <div className="w-96 border-r border-gray-700 flex flex-col">
          {/* Filters */}
          <div className="p-3 border-b border-gray-700 space-y-2">
            {/* Search */}
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="搜索执行结果..."
                  className="w-full pl-9 pr-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <button
                onClick={handleSearch}
                className="px-3 py-1.5 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 transition"
              >
                搜索
              </button>
            </div>

            {/* Filter dropdowns */}
            <div className="flex gap-2">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none"
              >
                <option value="">全部状态</option>
                {Object.entries(statusConfig).map(([key, cfg]) => (
                  <option key={key} value={key}>{cfg.label}</option>
                ))}
              </select>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none"
              >
                <option value="">全部类型</option>
                {Object.entries(actionTypeConfig).map(([key, cfg]) => (
                  <option key={key} value={key}>{cfg.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Task list */}
          <div className="flex-1 overflow-y-auto">
            {error && (
              <div className="p-4 bg-red-900/20 border-b border-red-800">
                <div className="flex items-center gap-2 text-red-400 text-sm">
                  <AlertCircle size={16} />
                  {error}
                </div>
              </div>
            )}

            {isLoading && tasks.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <RefreshCw size={24} className="mx-auto mb-2 animate-spin opacity-50" />
                <p className="text-sm">加载中...</p>
              </div>
            ) : tasks.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <CalendarClock size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">暂无任务</p>
                <p className="text-xs mt-1">通过对话创建任务来监控股票</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-800">
                {tasks.map((task) => {
                  const actionCfg = actionTypeConfig[task.action_type] || actionTypeConfig.custom;
                  const statusCfg = statusConfig[task.status] || statusConfig.pending;
                  const isSelected = selectedTask?.id === task.id;

                  return (
                    <div
                      key={task.id}
                      onClick={() => fetchTaskDetail(task.id)}
                      className={`p-3 cursor-pointer transition ${
                        isSelected ? 'bg-blue-900/30 border-l-2 border-l-blue-500' : 'hover:bg-gray-800/50'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Icon */}
                        <div className={`mt-0.5 ${actionCfg.color}`}>
                          {actionCfg.icon}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm truncate">{task.name}</span>
                            <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs ${statusCfg.bgColor} ${statusCfg.color}`}>
                              {statusCfg.icon}
                              {statusCfg.label}
                            </span>
                          </div>

                          <div className="text-xs text-gray-500 mt-1">
                            {actionCfg.label} · 执行 {task.execution_count} 次
                          </div>

                          {/* Last execution result */}
                          {task.last_execution ? (
                            <div className={`text-xs mt-1 flex items-center gap-1 ${task.last_execution.success ? 'text-green-400' : 'text-red-400'}`}>
                              {task.last_execution.success ? (
                                <CheckCircle size={12} />
                              ) : (
                                <XCircle size={12} />
                              )}
                              <span>
                                {task.last_execution.result_summary || (task.last_execution.success ? '执行成功' : '执行失败')}
                              </span>
                              <span className="text-gray-600">
                                · {formatTime(task.last_execution.executed_at)}
                              </span>
                            </div>
                          ) : (
                            <div className="text-xs text-gray-600 mt-1">
                              尚未执行
                            </div>
                          )}

                          <div className="text-xs text-gray-500 mt-0.5">
                            下次: {formatTime(task.next_execution_at)}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1">
                          {task.status === 'scheduled' && (
                            <>
                              <button
                                onClick={(e) => handleTrigger(task.id, e)}
                                className="p-1.5 hover:bg-gray-700 rounded"
                                title="立即执行"
                              >
                                <Play size={14} className="text-green-400" />
                              </button>
                              <button
                                onClick={(e) => handlePause(task.id, e)}
                                className="p-1.5 hover:bg-gray-700 rounded"
                                title="暂停"
                              >
                                <Pause size={14} className="text-yellow-400" />
                              </button>
                            </>
                          )}
                          {task.status === 'paused' && (
                            <button
                              onClick={(e) => handleResume(task.id, e)}
                              className="p-1.5 hover:bg-gray-700 rounded"
                              title="恢复"
                            >
                              <Play size={14} className="text-green-400" />
                            </button>
                          )}
                          {(task.status === 'cancelled' || task.status === 'completed' || task.status === 'failed') && (
                            <button
                              onClick={(e) => handleResume(task.id, e)}
                              className="p-1.5 hover:bg-gray-700 rounded"
                              title="重新启动"
                            >
                              <RefreshCw size={14} className="text-blue-400" />
                            </button>
                          )}
                          <button
                            onClick={(e) => handleDelete(task.id, e)}
                            className="p-1.5 hover:bg-gray-700 rounded"
                            title="删除"
                          >
                            <Trash2 size={14} className="text-red-400" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right panel - Task detail */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {showSearchResults ? (
            // Search results view
            <div className="flex-1 overflow-y-auto p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium">搜索结果: "{searchQuery}"</h2>
                <button
                  onClick={() => setShowSearchResults(false)}
                  className="p-1 hover:bg-gray-700 rounded"
                >
                  <X size={18} />
                </button>
              </div>

              {searchResults.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  未找到匹配的结果
                </div>
              ) : (
                <div className="space-y-3">
                  {searchResults.map((result, i) => (
                    <div key={i} className="p-3 bg-gray-800 rounded-lg">
                      <div className="flex items-center gap-2 text-sm">
                        {result.success ? (
                          <CheckCircle size={14} className="text-green-400" />
                        ) : (
                          <XCircle size={14} className="text-red-400" />
                        )}
                        <span className="text-gray-400">{formatFullTime(result.started_at)}</span>
                      </div>
                      {result.result && (
                        <pre className="mt-2 text-xs text-gray-400 overflow-x-auto">
                          {JSON.stringify(result.result, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : selectedTask ? (
            // Task detail view
            <>
              {/* Task header */}
              <div className="p-4 border-b border-gray-700">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={actionTypeConfig[selectedTask.action_type]?.color || 'text-gray-400'}>
                        {actionTypeConfig[selectedTask.action_type]?.icon}
                      </span>
                      <h2 className="text-lg font-medium">{selectedTask.name}</h2>
                    </div>
                    {selectedTask.description && (
                      <p className="text-sm text-gray-400 mt-1">{selectedTask.description}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {selectedTask.status === 'scheduled' && (
                      <>
                        <button
                          onClick={() => handleTrigger(selectedTask.id)}
                          className="px-3 py-1.5 bg-green-600 rounded-lg text-sm hover:bg-green-500 transition flex items-center gap-1"
                        >
                          <Play size={14} />
                          执行
                        </button>
                        <button
                          onClick={() => handlePause(selectedTask.id)}
                          className="px-3 py-1.5 bg-yellow-600 rounded-lg text-sm hover:bg-yellow-500 transition flex items-center gap-1"
                        >
                          <Pause size={14} />
                          暂停
                        </button>
                      </>
                    )}
                    {selectedTask.status === 'paused' && (
                      <button
                        onClick={() => handleResume(selectedTask.id)}
                        className="px-3 py-1.5 bg-green-600 rounded-lg text-sm hover:bg-green-500 transition flex items-center gap-1"
                      >
                        <Play size={14} />
                        恢复
                      </button>
                    )}
                    {(selectedTask.status === 'cancelled' || selectedTask.status === 'completed' || selectedTask.status === 'failed') && (
                      <button
                        onClick={() => handleResume(selectedTask.id)}
                        className="px-3 py-1.5 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 transition flex items-center gap-1"
                      >
                        <RefreshCw size={14} />
                        重新启动
                      </button>
                    )}
                    {selectedTask.status !== 'cancelled' && selectedTask.status !== 'completed' && selectedTask.status !== 'failed' && (
                      <button
                        onClick={() => handleCancel(selectedTask.id)}
                        className="px-3 py-1.5 bg-gray-700 rounded-lg text-sm hover:bg-gray-600 transition flex items-center gap-1"
                      >
                        <XCircle size={14} />
                        取消
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(selectedTask.id)}
                      className="px-3 py-1.5 bg-red-600 rounded-lg text-sm hover:bg-red-500 transition flex items-center gap-1"
                    >
                      <Trash2 size={14} />
                      删除
                    </button>
                  </div>
                </div>

                {/* Status and schedule info */}
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-800 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-1">状态</div>
                    <div className={`flex items-center gap-1 ${statusConfig[selectedTask.status]?.color}`}>
                      {statusConfig[selectedTask.status]?.icon}
                      <span className="font-medium">{statusConfig[selectedTask.status]?.label}</span>
                    </div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-1">调度类型</div>
                    <div className="font-medium">{selectedTask.schedule.type}</div>
                    {selectedTask.schedule.interval_value && (
                      <div className="text-xs text-gray-400">
                        每 {selectedTask.schedule.interval_value} {selectedTask.schedule.interval_unit}
                      </div>
                    )}
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-1">执行次数</div>
                    <div className="font-medium">{selectedTask.execution_count}</div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-1">下次执行</div>
                    <div className="font-medium text-sm">{formatTime(selectedTask.next_execution_at)}</div>
                  </div>
                </div>

                {/* Configuration */}
                <div className="mt-4">
                  <div className="text-sm text-gray-400 mb-2 flex items-center gap-1">
                    <Settings size={14} />
                    任务配置
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3">
                    <pre className="text-xs text-gray-300 overflow-x-auto">
                      {JSON.stringify(selectedTask.action_config, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>

              {/* Execution history */}
              <div className="flex-1 overflow-y-auto p-4">
                <div className="flex items-center gap-2 mb-3">
                  <History size={16} className="text-gray-400" />
                  <span className="font-medium">执行历史</span>
                  {loadingExecutions && (
                    <RefreshCw size={14} className="animate-spin text-gray-500" />
                  )}
                </div>

                {taskExecutions.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    暂无执行记录
                  </div>
                ) : (
                  <div className="space-y-3">
                    {taskExecutions.map((exec) => (
                      <div
                        key={exec.id}
                        className={`p-3 rounded-lg border ${
                          exec.success
                            ? 'bg-gray-800/50 border-gray-700'
                            : 'bg-red-900/20 border-red-800/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {exec.success ? (
                              <CheckCircle size={16} className="text-green-400" />
                            ) : (
                              <XCircle size={16} className="text-red-400" />
                            )}
                            <span className="text-sm font-medium">
                              {exec.success ? '执行成功' : '执行失败'}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            {formatFullTime(exec.started_at)}
                            {exec.duration_ms && (
                              <span className="ml-2">({exec.duration_ms}ms)</span>
                            )}
                          </div>
                        </div>

                        {exec.error && (
                          <div className="mt-2 p-2 bg-red-900/30 rounded text-xs text-red-400">
                            {exec.error}
                          </div>
                        )}

                        {renderExecutionResult(exec)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            // Empty state
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <Info size={48} className="mx-auto mb-3 opacity-50" />
                <p>选择一个任务查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
