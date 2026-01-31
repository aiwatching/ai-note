/**
 * 类型定义
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  result?: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}
