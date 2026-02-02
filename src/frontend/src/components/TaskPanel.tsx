/**
 * Task Panel Component
 *
 * Displays and manages scheduled tasks.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  CalendarClock,
  RefreshCw,
  X,
  Play,
  Pause,
  Trash2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  Activity,
  TrendingUp,
  Bell,
  Newspaper,
  Briefcase,
} from 'lucide-react';
import {
  getTasks,
  getTaskStats,
  triggerTask,
  pauseTask,
  cancelTask,
  deleteTask,
  getTaskExecutions,
  TaskSummary,
  TaskStats,
  TaskExecution,
} from '../services/api';

// Action type icons
const actionTypeIcons: Record<string, React.ReactNode> = {
  stock_alert: <Bell size={14} className="text-yellow-400" />,
  stock_analysis: <TrendingUp size={14} className="text-green-400" />,
  portfolio_monitor: <Briefcase size={14} className="text-blue-400" />,
  news_watch: <Newspaper size={14} className="text-purple-400" />,
};

// Status badges
const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ReactNode }> = {
  pending: { color: 'text-gray-400', bgColor: 'bg-gray-500/20', icon: <Clock size={12} /> },
  scheduled: { color: 'text-blue-400', bgColor: 'bg-blue-500/20', icon: <CalendarClock size={12} /> },
  running: { color: 'text-green-400', bgColor: 'bg-green-500/20', icon: <Activity size={12} /> },
  completed: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/20', icon: <CheckCircle size={12} /> },
  paused: { color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', icon: <Pause size={12} /> },
  cancelled: { color: 'text-gray-500', bgColor: 'bg-gray-600/20', icon: <XCircle size={12} /> },
  failed: { color: 'text-red-400', bgColor: 'bg-red-500/20', icon: <AlertCircle size={12} /> },
};

interface TaskPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

export default function TaskPanel({ isOpen, onToggle }: TaskPanelProps) {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [executions, setExecutions] = useState<Record<string, TaskExecution[]>>({});
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [tasksData, statsData] = await Promise.all([
        getTasks(),
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
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchTasks();
    }
  }, [isOpen, fetchTasks]);

  useEffect(() => {
    if (autoRefresh && isOpen) {
      const interval = setInterval(fetchTasks, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, isOpen, fetchTasks]);

  const handleToggleExpand = async (taskId: string) => {
    if (expandedTask === taskId) {
      setExpandedTask(null);
    } else {
      setExpandedTask(taskId);
      // Fetch executions if not already loaded
      if (!executions[taskId]) {
        try {
          const data = await getTaskExecutions(taskId);
          setExecutions(prev => ({ ...prev, [taskId]: data.executions }));
        } catch (err) {
          console.error('Failed to fetch executions:', err);
        }
      }
    }
  };

  const handleTrigger = async (taskId: string) => {
    try {
      await triggerTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to trigger task:', err);
    }
  };

  const handlePause = async (taskId: string) => {
    try {
      await pauseTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to pause task:', err);
    }
  };

  const handleCancel = async (taskId: string) => {
    try {
      await cancelTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to cancel task:', err);
    }
  };

  const handleDelete = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      await deleteTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
  };

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-4 right-20 bg-gray-800 text-white p-3 rounded-full shadow-lg hover:bg-gray-700 transition z-50"
        title="Task Panel"
      >
        <CalendarClock size={20} />
        {stats && stats.scheduled_tasks > 0 && (
          <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {stats.scheduled_tasks}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 h-80 bg-gray-900 text-gray-100 shadow-2xl z-50 border-t border-gray-700 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <CalendarClock size={16} className="text-blue-400" />
            <span className="font-medium text-sm">Tasks</span>
          </div>

          {/* Stats */}
          {stats && (
            <div className="flex items-center gap-3 text-xs">
              <span className="text-gray-400">
                Total: <span className="text-white">{stats.total_tasks}</span>
              </span>
              <span className="text-blue-400">
                Scheduled: {stats.scheduled_tasks}
              </span>
              <span className="text-green-400">
                Running: {stats.running_tasks}
              </span>
              {stats.failed_tasks > 0 && (
                <span className="text-red-400">
                  Failed: {stats.failed_tasks}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`p-1.5 rounded text-xs flex items-center gap-1 transition ${
              autoRefresh
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
            title={autoRefresh ? 'Stop auto-refresh' : 'Auto-refresh'}
          >
            <RefreshCw size={12} className={autoRefresh ? 'animate-spin' : ''} />
          </button>

          <button
            onClick={fetchTasks}
            disabled={isLoading}
            className="p-1.5 bg-gray-700 rounded hover:bg-gray-600 transition disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>

          <button
            onClick={onToggle}
            className="p-1.5 bg-gray-700 rounded hover:bg-gray-600 transition"
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="p-4 bg-red-900/20 border-b border-red-800">
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle size={16} />
              <span className="text-sm">{error}</span>
            </div>
          </div>
        )}

        {isLoading && tasks.length === 0 && !error && (
          <div className="p-8 text-center text-gray-500">
            <RefreshCw size={24} className="mx-auto mb-2 animate-spin opacity-50" />
            <p className="text-sm">Loading...</p>
          </div>
        )}

        {!isLoading && tasks.length === 0 && !error ? (
          <div className="p-8 text-center text-gray-500">
            <CalendarClock size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">No tasks yet</p>
            <p className="text-xs mt-1">Create tasks through the chat to monitor stocks</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {tasks.map((task) => {
              const status = statusConfig[task.status] || statusConfig.pending;
              const isExpanded = expandedTask === task.id;
              const taskExecutions = executions[task.id] || [];

              return (
                <div key={task.id} className="hover:bg-gray-800/50">
                  {/* Task row */}
                  <div
                    className="px-4 py-3 cursor-pointer"
                    onClick={() => handleToggleExpand(task.id)}
                  >
                    <div className="flex items-center gap-3">
                      {/* Action type icon */}
                      <span className="flex-shrink-0">
                        {actionTypeIcons[task.action_type] || <Activity size={14} />}
                      </span>

                      {/* Name */}
                      <span className="font-medium text-sm flex-1 truncate">
                        {task.name}
                      </span>

                      {/* Status badge */}
                      <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs ${status.bgColor} ${status.color}`}>
                        {status.icon}
                        {task.status}
                      </span>

                      {/* Execution count */}
                      <span className="text-xs text-gray-500">
                        x{task.execution_count}
                      </span>

                      {/* Next execution */}
                      <span className="text-xs text-gray-400 w-28 text-right">
                        {formatTime(task.next_execution_at)}
                      </span>

                      {/* Actions */}
                      <div className="flex items-center gap-1">
                        {task.status === 'scheduled' && (
                          <>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleTrigger(task.id); }}
                              className="p-1 hover:bg-gray-700 rounded"
                              title="Run now"
                            >
                              <Play size={12} className="text-green-400" />
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handlePause(task.id); }}
                              className="p-1 hover:bg-gray-700 rounded"
                              title="Pause"
                            >
                              <Pause size={12} className="text-yellow-400" />
                            </button>
                          </>
                        )}
                        {task.status === 'paused' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleTrigger(task.id); }}
                            className="p-1 hover:bg-gray-700 rounded"
                            title="Resume"
                          >
                            <Play size={12} className="text-green-400" />
                          </button>
                        )}
                        {task.status !== 'cancelled' && task.status !== 'completed' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleCancel(task.id); }}
                            className="p-1 hover:bg-gray-700 rounded"
                            title="Cancel"
                          >
                            <XCircle size={12} className="text-gray-400" />
                          </button>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(task.id); }}
                          className="p-1 hover:bg-gray-700 rounded"
                          title="Delete"
                        >
                          <Trash2 size={12} className="text-red-400" />
                        </button>
                      </div>

                      {/* Expand indicator */}
                      <span className="text-gray-500">
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </span>
                    </div>
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="px-4 pb-3">
                      <div className="ml-7 p-3 bg-gray-800/50 rounded border border-gray-700">
                        {/* Task details */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mb-3">
                          <div>
                            <span className="text-gray-500">Type:</span>
                            <span className="ml-1 text-gray-300">{task.action_type}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Schedule:</span>
                            <span className="ml-1 text-gray-300">{task.schedule.type}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Last run:</span>
                            <span className="ml-1 text-gray-300">{formatTime(task.last_executed_at)}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Created:</span>
                            <span className="ml-1 text-gray-300">{formatTime(task.created_at)}</span>
                          </div>
                        </div>

                        {/* Recent executions */}
                        {taskExecutions.length > 0 && (
                          <div>
                            <div className="text-xs text-gray-500 mb-2">Recent Executions:</div>
                            <div className="space-y-2">
                              {taskExecutions.slice(0, 5).map((exec) => (
                                <div
                                  key={exec.id}
                                  className="bg-gray-900/50 rounded p-2"
                                >
                                  <div className="flex items-center gap-2 text-xs mb-1">
                                    {exec.success ? (
                                      <CheckCircle size={12} className="text-green-400" />
                                    ) : (
                                      <XCircle size={12} className="text-red-400" />
                                    )}
                                    <span className="text-gray-400">
                                      {formatTime(exec.started_at)}
                                    </span>
                                    {exec.duration_ms && (
                                      <span className="text-gray-500">
                                        ({exec.duration_ms}ms)
                                      </span>
                                    )}
                                  </div>
                                  {exec.error && (
                                    <div className="text-red-400 text-xs mt-1">
                                      Error: {exec.error}
                                    </div>
                                  )}
                                  {exec.result && Object.keys(exec.result).length > 0 && (
                                    <div className="text-xs mt-1 space-y-0.5">
                                      {Object.entries(exec.result).slice(0, 6).map(([key, value]) => {
                                        // Skip complex nested objects
                                        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                                          return null;
                                        }
                                        const displayValue = Array.isArray(value)
                                          ? `[${value.length} items]`
                                          : typeof value === 'boolean'
                                          ? value ? 'Yes' : 'No'
                                          : typeof value === 'number'
                                          ? value.toLocaleString()
                                          : String(value).slice(0, 50);
                                        return (
                                          <div key={key} className="flex gap-1">
                                            <span className="text-gray-500">{key}:</span>
                                            <span className={`text-gray-300 ${key === 'triggered' && value ? 'text-yellow-400 font-medium' : ''}`}>
                                              {displayValue}
                                            </span>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
