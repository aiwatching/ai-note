/**
 * API 服务
 */

const API_BASE = '/api';

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  provider?: string;
  stream?: boolean;
}

export interface ChatResponse {
  content: string;
  conversation_id: string;
  model_used: string;
  tool_calls_made: Array<{
    name: string;
    arguments: Record<string, any>;
    result: string;
  }>;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  timestamp: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export interface AppInfo {
  name: string;
  version: string;
  available_models: string[];
  available_tools: string[];
  default_model: string;
}

// 发送聊天消息
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// 流式消息事件类型
export interface StreamEvent {
  type: 'content' | 'done';
  content?: string;
  conversation_id?: string;
  model_used?: string;
  agents_called?: string[];
}

// 流式发送消息 - 返回事件流
export async function* sendMessageStream(
  request: ChatRequest
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;

        try {
          const parsed = JSON.parse(data) as StreamEvent;
          yield parsed;
        } catch {
          // 忽略解析错误
        }
      }
    }
  }
}

// 获取对话列表
export async function getConversations(limit = 20): Promise<ConversationSummary[]> {
  const response = await fetch(`${API_BASE}/conversations?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 获取对话详情
export async function getConversation(id: string): Promise<ConversationDetail> {
  const response = await fetch(`${API_BASE}/conversations/${id}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 删除对话
export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/conversations/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
}

// 获取应用信息
export async function getAppInfo(): Promise<AppInfo> {
  const response = await fetch(`${API_BASE}/info`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 获取可用模型
export async function getModels(): Promise<{ models: string[]; default: string }> {
  const response = await fetch(`${API_BASE}/chat/models`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// ==================== Debug / Logging API ====================

export interface AgentEvent {
  timestamp: string;
  event_type: string;
  agent_id: string;
  [key: string]: any;
}

export interface AgentInfo {
  id: string;
  name: string;
  description: string;
  provider: string;
  skills: string[];
  tools: string[];
}

// 获取Agent日志
export async function getAgentLogs(agentId: string = 'main', count: number = 50): Promise<{
  agent_id: string;
  events: AgentEvent[];
}> {
  const response = await fetch(`${API_BASE}/chat/logs?agent_id=${agentId}&count=${count}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 获取Agent委托日志
export async function getAgentDelegationLogs(): Promise<{
  delegations: AgentEvent[];
}> {
  const response = await fetch(`${API_BASE}/chat/logs/agents`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 获取所有Agent日志
export async function getAllAgentLogs(count: number = 20): Promise<Record<string, AgentEvent[]>> {
  const response = await fetch(`${API_BASE}/chat/logs/all?count=${count}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 获取所有Agent信息
export async function getAgents(): Promise<AgentInfo[]> {
  const response = await fetch(`${API_BASE}/chat/agents`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// ==================== Task Management API ====================

export interface TaskSchedule {
  type: string;
  scheduled_at?: string;
  interval_value?: number;
  interval_unit?: string;
  cron_expression?: string;
  max_executions?: number;
  expires_at?: string;
}

export interface LastExecutionInfo {
  success: boolean;
  executed_at: string;
  duration_ms: number | null;
  error: string | null;
  result_summary: string | null;
}

export interface TaskSummary {
  id: string;
  name: string;
  description: string;
  action_type: string;
  action_config: Record<string, any>;
  schedule: TaskSchedule;
  status: string;
  execution_count: number;
  last_executed_at: string | null;
  next_execution_at: string | null;
  last_execution: LastExecutionInfo | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface TaskStats {
  total_tasks: number;
  pending_tasks: number;
  scheduled_tasks: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  total_executions: number;
  scheduler_running: boolean;
  action_types: string[];
}

export interface TaskExecution {
  id: string;
  task_id: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  success: boolean;
  result: Record<string, any>;
  error: string | null;
}

export interface TaskListResponse {
  tasks: TaskSummary[];
  total: number;
}

export interface ExecutionListResponse {
  executions: TaskExecution[];
  total: number;
}

// 获取任务列表
export async function getTasks(
  status?: string,
  actionType?: string,
  limit: number = 100
): Promise<TaskListResponse> {
  let url = `${API_BASE}/tasks?limit=${limit}`;
  if (status) url += `&status=${status}`;
  if (actionType) url += `&action_type=${actionType}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 获取任务统计
export async function getTaskStats(): Promise<TaskStats> {
  const response = await fetch(`${API_BASE}/tasks/stats`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 获取任务详情
export async function getTask(taskId: string): Promise<TaskSummary> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 触发任务
export async function triggerTask(taskId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/trigger`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 暂停任务
export async function pauseTask(taskId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/pause`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 取消任务
export async function cancelTask(taskId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 恢复任务（从暂停/取消/完成/失败状态恢复）
export async function resumeTask(taskId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/resume`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 删除任务
export async function deleteTask(taskId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
}

// 获取任务执行历史
export async function getTaskExecutions(
  taskId: string,
  limit: number = 50
): Promise<ExecutionListResponse> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/executions?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// 搜索任务结果
export async function searchTaskResults(
  query: string,
  taskId?: string,
  limit: number = 20
): Promise<{ query: string; results: any[] }> {
  let url = `${API_BASE}/tasks/search/results?q=${encodeURIComponent(query)}&limit=${limit}`;
  if (taskId) url += `&task_id=${taskId}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}
