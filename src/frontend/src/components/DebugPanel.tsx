/**
 * Debug Panel Component
 *
 * Displays agent activity logs, tool calls, and sub-agent delegation events.
 * Enhanced with better visualization and filtering.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Bug,
  RefreshCw,
  ChevronUp,
  ChevronDown,
  Activity,
  Wrench,
  Users,
  AlertCircle,
  MessageSquare,
  Zap,
  Clock,
  X,
  Filter,
  CheckCircle,
  XCircle,
  ArrowRight,
  Database,
  Search,
  BarChart3,
  Play,
  Square,
} from 'lucide-react';
import { getAgents, getAllAgentLogs, AgentEvent, AgentInfo } from '../services/api';

// Event type colors and icons - more distinctive
const eventTypeConfig: Record<string, {
  color: string;
  bgColor: string;
  icon: React.ReactNode;
  label: string;
  category: 'lifecycle' | 'chat' | 'tool' | 'agent' | 'memory' | 'error';
}> = {
  // Lifecycle
  init: { color: 'text-cyan-400', bgColor: 'bg-cyan-500/20', icon: <Play size={12} />, label: '初始化', category: 'lifecycle' },
  ready: { color: 'text-green-400', bgColor: 'bg-green-500/20', icon: <CheckCircle size={12} />, label: '就绪', category: 'lifecycle' },
  // Chat
  chat_start: { color: 'text-blue-400', bgColor: 'bg-blue-500/20', icon: <MessageSquare size={12} />, label: '对话开始', category: 'chat' },
  chat_end: { color: 'text-blue-300', bgColor: 'bg-blue-500/10', icon: <Square size={12} />, label: '对话结束', category: 'chat' },
  // Tools
  tool_call: { color: 'text-purple-400', bgColor: 'bg-purple-500/20', icon: <Wrench size={12} />, label: '工具调用', category: 'tool' },
  tool_result: { color: 'text-purple-300', bgColor: 'bg-purple-500/10', icon: <Zap size={12} />, label: '工具结果', category: 'tool' },
  tool_register: { color: 'text-purple-300', bgColor: 'bg-purple-500/10', icon: <Wrench size={12} />, label: '工具注册', category: 'tool' },
  // Agents
  agent_delegate: { color: 'text-orange-400', bgColor: 'bg-orange-500/20', icon: <ArrowRight size={12} />, label: 'Agent委托', category: 'agent' },
  agent_response: { color: 'text-orange-300', bgColor: 'bg-orange-500/10', icon: <MessageSquare size={12} />, label: 'Agent响应', category: 'agent' },
  agent_register: { color: 'text-orange-300', bgColor: 'bg-orange-500/10', icon: <Users size={12} />, label: 'Agent注册', category: 'agent' },
  // Context
  model_select: { color: 'text-gray-400', bgColor: 'bg-gray-500/20', icon: <Activity size={12} />, label: '模型选择', category: 'lifecycle' },
  context_load: { color: 'text-gray-400', bgColor: 'bg-gray-500/20', icon: <Database size={12} />, label: '上下文加载', category: 'lifecycle' },
  // Memory
  memory_search: { color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', icon: <Search size={12} />, label: '记忆搜索', category: 'memory' },
  memory_add: { color: 'text-yellow-300', bgColor: 'bg-yellow-500/10', icon: <Database size={12} />, label: '记忆添加', category: 'memory' },
  // Error
  error: { color: 'text-red-400', bgColor: 'bg-red-500/20', icon: <XCircle size={12} />, label: '错误', category: 'error' },
};

const categoryLabels: Record<string, string> = {
  lifecycle: '生命周期',
  chat: '对话',
  tool: '工具',
  agent: 'Agent',
  memory: '记忆',
  error: '错误',
};

interface DebugPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

export default function DebugPanel({ isOpen, onToggle }: DebugPanelProps) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'logs' | 'agents' | 'stats'>('logs');
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());
  const [filterCategory, setFilterCategory] = useState<string | null>(null);
  const [filterAgent, setFilterAgent] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const allLogs = await getAllAgentLogs(100);
      const combinedEvents: AgentEvent[] = [];
      for (const [agentId, agentEvents] of Object.entries(allLogs)) {
        for (const event of agentEvents) {
          combinedEvents.push({ ...event, agent_id: agentId });
        }
      }
      combinedEvents.sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      setEvents(combinedEvents);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch logs');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const data = await getAgents();
      setAgents(data);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
      fetchAgents();
    }
  }, [isOpen, fetchLogs, fetchAgents]);

  useEffect(() => {
    if (autoRefresh && isOpen) {
      const interval = setInterval(fetchLogs, 2000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, isOpen, fetchLogs]);

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      const config = eventTypeConfig[event.event_type];
      if (filterCategory && config?.category !== filterCategory) return false;
      if (filterAgent && event.agent_id !== filterAgent) return false;
      return true;
    });
  }, [events, filterCategory, filterAgent]);

  // Calculate statistics
  const stats = useMemo(() => {
    const categoryCount: Record<string, number> = {};
    const agentCount: Record<string, number> = {};
    let totalToolCalls = 0;
    let totalDelegations = 0;
    let totalDuration = 0;
    let errorCount = 0;

    events.forEach(event => {
      const config = eventTypeConfig[event.event_type];
      if (config) {
        categoryCount[config.category] = (categoryCount[config.category] || 0) + 1;
      }
      agentCount[event.agent_id] = (agentCount[event.agent_id] || 0) + 1;

      if (event.event_type === 'tool_call') totalToolCalls++;
      if (event.event_type === 'agent_delegate') totalDelegations++;
      if (event.event_type === 'error') errorCount++;
      if (event.duration_ms) totalDuration += event.duration_ms;
    });

    return { categoryCount, agentCount, totalToolCalls, totalDelegations, totalDuration, errorCount };
  }, [events]);

  // Get unique agents from events
  const uniqueAgents = useMemo(() => {
    return [...new Set(events.map(e => e.agent_id))];
  }, [events]);

  const toggleEventExpand = (index: number) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedEvents(newExpanded);
  };

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const time = date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      const ms = date.getMilliseconds().toString().padStart(3, '0').slice(0, 1);
      return `${time}.${ms}`;
    } catch {
      return timestamp;
    }
  };

  const renderEventContent = (event: AgentEvent) => {
    switch (event.event_type) {
      case 'init':
        return <span>Agent <span className="text-cyan-400">{event.name}</span> 初始化</span>;
      case 'ready':
        return <span>就绪 - 工具: <span className="text-green-400">{event.tools_count}</span>, 子Agent: <span className="text-green-400">{event.sub_agents_count}</span></span>;
      case 'chat_start':
        return <span className="text-gray-300">"{event.message_preview}"</span>;
      case 'chat_end':
        return (
          <span className="flex items-center gap-2">
            <span className="text-gray-400">工具调用: {event.tool_calls || 0}</span>
            {event.agents_called?.length > 0 && (
              <span className="text-orange-400">Agent: {event.agents_called.join(', ')}</span>
            )}
            {event.duration_ms && (
              <span className="text-gray-500">{event.duration_ms.toFixed(0)}ms</span>
            )}
          </span>
        );
      case 'tool_call':
        return (
          <span className="font-mono">
            <span className="text-purple-400">{event.tool_name}</span>
            <span className="text-gray-500">(</span>
            <span className="text-gray-400 text-xs">{JSON.stringify(event.arguments)}</span>
            <span className="text-gray-500">)</span>
          </span>
        );
      case 'tool_result':
        return (
          <span className="flex items-center gap-2">
            {event.success ? (
              <CheckCircle size={12} className="text-green-400" />
            ) : (
              <XCircle size={12} className="text-red-400" />
            )}
            <span className="text-purple-300">{event.tool_name}</span>
            <span className="text-gray-500">→</span>
            <span className="text-gray-400 truncate max-w-md">{event.result_preview}</span>
          </span>
        );
      case 'agent_delegate':
        return (
          <span className="flex items-center gap-2">
            <span className="text-gray-400">{event.agent_id}</span>
            <ArrowRight size={12} className="text-orange-400" />
            <span className="text-orange-400 font-medium">{event.target_agent_id}</span>
            <span className="text-gray-500">:</span>
            <span className="text-gray-300 truncate max-w-md">"{event.message_preview}"</span>
          </span>
        );
      case 'agent_response':
        return (
          <span className="flex items-center gap-2">
            <span className="text-orange-300">{event.source_agent_id}</span>
            <span className="text-gray-500">返回:</span>
            <span className="text-gray-400 truncate max-w-md">{event.response_preview}</span>
          </span>
        );
      case 'agent_register':
        return (
          <span>注册 <span className="text-orange-400">{event.registered_agent_name}</span> ({event.registered_agent_id})</span>
        );
      case 'memory_search':
        return (
          <span className="flex items-center gap-2">
            <Search size={12} className="text-yellow-400" />
            <span className="text-gray-300">"{event.query}"</span>
            <span className="text-gray-500">→</span>
            <span className="text-yellow-400">{event.results_count} 条结果</span>
            {event.duration_ms && <span className="text-gray-500">{event.duration_ms.toFixed(0)}ms</span>}
          </span>
        );
      case 'memory_add':
        return (
          <span>添加到 <span className="text-yellow-400">{event.source}</span> ({event.chunks_count} chunks)</span>
        );
      case 'error':
        return (
          <span className="text-red-400">
            [{event.error_type}] {event.message}
          </span>
        );
      case 'model_select':
        return (
          <span>
            使用 <span className="text-blue-400">{event.provider}</span>
            <span className="text-gray-500"> ({event.reason})</span>
          </span>
        );
      default:
        return <span className="text-gray-400">{JSON.stringify(event)}</span>;
    }
  };

  const renderExpandedDetails = (event: AgentEvent) => {
    const details: Array<{ label: string; value: string | number | boolean }> = [];

    // Common fields
    if (event.conversation_id) details.push({ label: '对话ID', value: event.conversation_id });
    if (event.provider) details.push({ label: '模型', value: event.provider });
    if (event.model_used) details.push({ label: '使用模型', value: event.model_used });
    if (event.duration_ms) details.push({ label: '耗时', value: `${event.duration_ms.toFixed(0)}ms` });

    // Tool specific
    if (event.arguments && Object.keys(event.arguments).length > 0) {
      details.push({ label: '参数', value: JSON.stringify(event.arguments, null, 2) });
    }
    if (event.result_preview && event.result_preview.length > 100) {
      details.push({ label: '完整结果', value: event.result_preview });
    }

    // Chat specific
    if (event.context_messages !== undefined) details.push({ label: '上下文消息数', value: event.context_messages });
    if (event.tool_calls !== undefined) details.push({ label: '工具调用次数', value: event.tool_calls });

    // Error specific
    if (event.details) details.push({ label: '错误详情', value: JSON.stringify(event.details, null, 2) });

    return details;
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-4 right-4 bg-gray-800 text-white p-3 rounded-full shadow-lg hover:bg-gray-700 transition z-50 group"
        title="打开调试面板"
      >
        <Bug size={20} />
        {events.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {events.length > 99 ? '99+' : events.length}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-900 text-gray-100 shadow-2xl z-50 border-t border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Bug size={16} className="text-green-400" />
            <span className="font-medium text-sm">调试面板</span>
            <span className="text-xs text-gray-500">({filteredEvents.length} 条记录)</span>
          </div>

          {/* Tabs */}
          <div className="flex gap-1">
            <button
              onClick={() => setSelectedTab('logs')}
              className={`px-3 py-1 text-xs rounded transition ${
                selectedTab === 'logs'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <Activity size={12} className="inline mr-1" />
              活动日志
            </button>
            <button
              onClick={() => setSelectedTab('stats')}
              className={`px-3 py-1 text-xs rounded transition ${
                selectedTab === 'stats'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <BarChart3 size={12} className="inline mr-1" />
              统计
            </button>
            <button
              onClick={() => setSelectedTab('agents')}
              className={`px-3 py-1 text-xs rounded transition ${
                selectedTab === 'agents'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <Users size={12} className="inline mr-1" />
              Agents ({agents.length})
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedTab === 'logs' && (
            <>
              {/* Category filter */}
              <div className="flex items-center gap-1">
                <Filter size={12} className="text-gray-500" />
                <select
                  value={filterCategory || ''}
                  onChange={(e) => setFilterCategory(e.target.value || null)}
                  className="bg-gray-700 text-xs rounded px-2 py-1 border-none outline-none"
                >
                  <option value="">全部类型</option>
                  {Object.entries(categoryLabels).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
              </div>

              {/* Agent filter */}
              <select
                value={filterAgent || ''}
                onChange={(e) => setFilterAgent(e.target.value || null)}
                className="bg-gray-700 text-xs rounded px-2 py-1 border-none outline-none"
              >
                <option value="">全部Agent</option>
                {uniqueAgents.map(agent => (
                  <option key={agent} value={agent}>{agent}</option>
                ))}
              </select>

              <div className="w-px h-4 bg-gray-700" />

              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`p-1.5 rounded text-xs flex items-center gap-1 transition ${
                  autoRefresh
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                title={autoRefresh ? '关闭自动刷新' : '开启自动刷新'}
              >
                <RefreshCw size={12} className={autoRefresh ? 'animate-spin' : ''} />
              </button>

              <button
                onClick={fetchLogs}
                disabled={isLoading}
                className="p-1.5 bg-gray-700 rounded hover:bg-gray-600 transition disabled:opacity-50"
                title="刷新日志"
              >
                <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              </button>
            </>
          )}

          <button
            onClick={onToggle}
            className="p-1.5 bg-gray-700 rounded hover:bg-gray-600 transition"
            title="关闭面板"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="h-72 overflow-y-auto">
        {selectedTab === 'logs' ? (
          <div className="divide-y divide-gray-800">
            {error && (
              <div className="p-4 bg-red-900/20 border-b border-red-800">
                <div className="flex items-center gap-2 text-red-400">
                  <AlertCircle size={16} />
                  <span className="text-sm">加载失败: {error}</span>
                </div>
              </div>
            )}

            {isLoading && events.length === 0 && !error && (
              <div className="p-8 text-center text-gray-500">
                <RefreshCw size={24} className="mx-auto mb-2 animate-spin opacity-50" />
                <p className="text-sm">加载中...</p>
              </div>
            )}

            {!isLoading && filteredEvents.length === 0 && !error ? (
              <div className="p-8 text-center text-gray-500">
                <Activity size={24} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">暂无活动日志</p>
                <p className="text-xs mt-1">发送消息后，这里会显示Agent的活动记录</p>
              </div>
            ) : (
              filteredEvents.map((event, index) => {
                const config = eventTypeConfig[event.event_type] || {
                  color: 'text-gray-400',
                  bgColor: 'bg-gray-500/20',
                  icon: <Activity size={12} />,
                  label: event.event_type,
                  category: 'lifecycle',
                };
                const isExpanded = expandedEvents.has(index);
                const details = renderExpandedDetails(event);

                return (
                  <div
                    key={index}
                    className={`px-4 py-2 hover:bg-gray-800/50 cursor-pointer transition border-l-2 ${
                      event.event_type === 'error' ? 'border-l-red-500' :
                      event.event_type === 'agent_delegate' ? 'border-l-orange-500' :
                      event.event_type === 'tool_call' ? 'border-l-purple-500' :
                      'border-l-transparent'
                    }`}
                    onClick={() => details.length > 0 && toggleEventExpand(index)}
                  >
                    <div className="flex items-center gap-3">
                      {/* Time */}
                      <span className="text-xs text-gray-500 font-mono w-20 flex-shrink-0">
                        {formatTime(event.timestamp)}
                      </span>

                      {/* Agent badge */}
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                        event.agent_id === 'main' ? 'bg-blue-500/20 text-blue-400' :
                        event.agent_id === 'stock' ? 'bg-green-500/20 text-green-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {event.agent_id}
                      </span>

                      {/* Event type badge */}
                      <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs ${config.bgColor} ${config.color}`}>
                        {config.icon}
                        {config.label}
                      </span>

                      {/* Event content */}
                      <div className="text-xs flex-1 truncate">
                        {renderEventContent(event)}
                      </div>

                      {/* Expand indicator */}
                      {details.length > 0 && (
                        <span className="text-gray-500">
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </span>
                      )}
                    </div>

                    {/* Expanded details */}
                    {isExpanded && details.length > 0 && (
                      <div className="mt-2 ml-24 p-3 bg-gray-800/50 rounded border border-gray-700">
                        <div className="grid grid-cols-2 gap-2">
                          {details.map((detail, i) => (
                            <div key={i} className="text-xs">
                              <span className="text-gray-500">{detail.label}: </span>
                              <span className="text-gray-300 font-mono break-all">
                                {typeof detail.value === 'string' && detail.value.length > 200
                                  ? detail.value.substring(0, 200) + '...'
                                  : String(detail.value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        ) : selectedTab === 'stats' ? (
          <div className="p-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Summary cards */}
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <Activity size={16} className="text-blue-400" />
                <span className="text-sm text-gray-400">总事件数</span>
              </div>
              <div className="text-2xl font-bold text-white">{events.length}</div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <Wrench size={16} className="text-purple-400" />
                <span className="text-sm text-gray-400">工具调用</span>
              </div>
              <div className="text-2xl font-bold text-purple-400">{stats.totalToolCalls}</div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <Users size={16} className="text-orange-400" />
                <span className="text-sm text-gray-400">Agent委托</span>
              </div>
              <div className="text-2xl font-bold text-orange-400">{stats.totalDelegations}</div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <Clock size={16} className="text-green-400" />
                <span className="text-sm text-gray-400">总耗时</span>
              </div>
              <div className="text-2xl font-bold text-green-400">{(stats.totalDuration / 1000).toFixed(1)}s</div>
            </div>

            {/* Category breakdown */}
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 md:col-span-2">
              <div className="text-sm text-gray-400 mb-3">事件类型分布</div>
              <div className="space-y-2">
                {Object.entries(stats.categoryCount).map(([category, count]) => (
                  <div key={category} className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-20">{categoryLabels[category] || category}</span>
                    <div className="flex-1 bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          category === 'tool' ? 'bg-purple-500' :
                          category === 'agent' ? 'bg-orange-500' :
                          category === 'chat' ? 'bg-blue-500' :
                          category === 'memory' ? 'bg-yellow-500' :
                          category === 'error' ? 'bg-red-500' :
                          'bg-gray-500'
                        }`}
                        style={{ width: `${(count / events.length) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-8">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Agent breakdown */}
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 md:col-span-2">
              <div className="text-sm text-gray-400 mb-3">Agent活动分布</div>
              <div className="space-y-2">
                {Object.entries(stats.agentCount).map(([agent, count]) => (
                  <div key={agent} className="flex items-center gap-2">
                    <span className={`text-xs w-20 ${
                      agent === 'main' ? 'text-blue-400' :
                      agent === 'stock' ? 'text-green-400' :
                      'text-gray-400'
                    }`}>{agent}</span>
                    <div className="flex-1 bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          agent === 'main' ? 'bg-blue-500' :
                          agent === 'stock' ? 'bg-green-500' :
                          'bg-gray-500'
                        }`}
                        style={{ width: `${(count / events.length) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-8">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Error count */}
            {stats.errorCount > 0 && (
              <div className="bg-red-900/20 rounded-lg p-4 border border-red-800 md:col-span-4">
                <div className="flex items-center gap-2">
                  <AlertCircle size={16} className="text-red-400" />
                  <span className="text-sm text-red-400">错误数量: {stats.errorCount}</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className={`rounded-lg p-4 border ${
                  agent.id === 'main'
                    ? 'bg-blue-900/20 border-blue-800'
                    : 'bg-gray-800 border-gray-700'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Users size={16} className={agent.id === 'main' ? 'text-blue-400' : 'text-gray-400'} />
                  <span className="font-medium">{agent.name}</span>
                  {agent.id === 'main' && (
                    <span className="text-xs bg-blue-500/30 text-blue-300 px-1.5 py-0.5 rounded">主</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mb-3 line-clamp-2">{agent.description}</p>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">模型:</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      agent.provider === 'claude' ? 'bg-orange-500/20 text-orange-400' :
                      agent.provider === 'deepseek' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{agent.provider}</span>
                  </div>

                  {agent.tools.length > 0 && (
                    <div>
                      <span className="text-xs text-gray-500">工具 ({agent.tools.length}):</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {agent.tools.slice(0, 6).map((tool) => (
                          <span
                            key={tool}
                            className="text-xs bg-purple-900/50 text-purple-300 px-1.5 py-0.5 rounded"
                          >
                            {tool}
                          </span>
                        ))}
                        {agent.tools.length > 6 && (
                          <span className="text-xs text-gray-500">+{agent.tools.length - 6}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
