/**
 * 聊天状态管理
 */
import { create } from 'zustand';
import * as api from '../services/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface ChatState {
  // 状态
  messages: ChatMessage[];
  conversationId: string | null;
  isLoading: boolean;
  error: string | null;
  selectedModel: string;
  availableModels: string[];

  // 历史对话
  conversations: api.ConversationSummary[];

  // 动作
  sendMessage: (content: string) => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  newConversation: () => void;
  loadConversations: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  setModel: (model: string) => void;
  loadModels: () => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // 初始状态
  messages: [],
  conversationId: null,
  isLoading: false,
  error: null,
  selectedModel: 'claude',
  availableModels: [],
  conversations: [],

  // 发送消息
  sendMessage: async (content: string) => {
    const { conversationId, selectedModel, messages } = get();

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // 添加助手消息占位
    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };

    set({
      messages: [...messages, userMessage, assistantMessage],
      isLoading: true,
      error: null,
    });

    try {
      // 流式请求
      let fullContent = '';
      for await (const chunk of api.sendMessageStream({
        message: content,
        conversation_id: conversationId || undefined,
        provider: selectedModel,
      })) {
        fullContent += chunk;
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === assistantMessage.id
              ? { ...msg, content: fullContent }
              : msg
          ),
        }));
      }

      // 完成
      set((state) => ({
        messages: state.messages.map((msg) =>
          msg.id === assistantMessage.id
            ? { ...msg, isStreaming: false }
            : msg
        ),
        isLoading: false,
      }));

      // 刷新对话列表
      get().loadConversations();
    } catch (error: any) {
      set({
        error: error.message || '发送失败',
        isLoading: false,
      });
    }
  },

  // 加载对话
  loadConversation: async (id: string) => {
    set({ isLoading: true, error: null });

    try {
      const conversation = await api.getConversation(id);
      const messages: ChatMessage[] = conversation.messages.map((msg) => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.timestamp),
      }));

      set({
        messages,
        conversationId: id,
        isLoading: false,
      });
    } catch (error: any) {
      set({
        error: error.message || '加载失败',
        isLoading: false,
      });
    }
  },

  // 新对话
  newConversation: () => {
    set({
      messages: [],
      conversationId: null,
      error: null,
    });
  },

  // 加载对话列表
  loadConversations: async () => {
    try {
      const conversations = await api.getConversations();
      set({ conversations });
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  },

  // 删除对话
  deleteConversation: async (id: string) => {
    try {
      await api.deleteConversation(id);
      const { conversationId } = get();
      if (conversationId === id) {
        get().newConversation();
      }
      get().loadConversations();
    } catch (error: any) {
      set({ error: error.message || '删除失败' });
    }
  },

  // 设置模型
  setModel: (model: string) => {
    set({ selectedModel: model });
  },

  // 加载可用模型
  loadModels: async () => {
    try {
      const { models, default: defaultModel } = await api.getModels();
      set({
        availableModels: models,
        selectedModel: defaultModel,
      });
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  },
}));
