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

// 流式发送消息
export async function* sendMessageStream(
  request: ChatRequest
): AsyncGenerator<string> {
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
          const parsed = JSON.parse(data);
          if (parsed.type === 'content' && parsed.content) {
            yield parsed.content;
          }
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
