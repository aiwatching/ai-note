import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Message {
  id: string;
  type: 'user' | 'result'; // user: 用户输入, result: 分析结果
  content: string;
  noteId?: number; // 关联的 note id
  timestamp: Date;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  logNoteId?: number;    // 对话日志 note id
  resultNoteId?: number; // 分析结果 note id
}

interface ConversationState {
  conversations: Conversation[];
  currentConversationId: string | null;

  // Actions
  createConversation: () => string;
  setCurrentConversation: (id: string | null) => void;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateConversationTitle: (id: string, title: string) => void;
  markLogSaved: (conversationId: string, noteId: number) => void;
  markResultSaved: (conversationId: string, noteId: number) => void;
  deleteConversation: (id: string) => void;
  clearCurrentConversation: () => void;
  getCurrentConversation: () => Conversation | null;
  getRecentConversations: (limit?: number) => Conversation[];
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,

      createConversation: () => {
        const { currentConversationId, conversations } = get();

        // 如果当前对话是空的，直接复用它，不创建新的
        if (currentConversationId) {
          const currentConv = conversations.find((c) => c.id === currentConversationId);
          if (currentConv && currentConv.messages.length === 0) {
            // 当前对话是空的，直接返回当前 id
            return currentConversationId;
          }
        }

        // 删除所有空对话（保持列表整洁）
        const nonEmptyConversations = conversations.filter((c) => c.messages.length > 0);

        const id = `conv_${Date.now()}`;
        const newConversation: Conversation = {
          id,
          title: '新对话',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        set({
          conversations: [newConversation, ...nonEmptyConversations],
          currentConversationId: id,
        });
        return id;
      },

      setCurrentConversation: (id) => {
        set({ currentConversationId: id });
      },

      addMessage: (message) => {
        const { currentConversationId, conversations } = get();
        if (!currentConversationId) return;

        const newMessage: Message = {
          ...message,
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
        };

        set({
          conversations: conversations.map((conv) =>
            conv.id === currentConversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, newMessage],
                  updatedAt: new Date(),
                  // 自动更新标题（使用第一条用户消息的前20个字符）
                  title:
                    conv.messages.length === 0 && message.type === 'user'
                      ? message.content.slice(0, 20) + (message.content.length > 20 ? '...' : '')
                      : conv.title,
                }
              : conv
          ),
        });
      },

      updateConversationTitle: (id, title) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, title, updatedAt: new Date() } : conv
          ),
        }));
      },

      markLogSaved: (conversationId, noteId) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? { ...conv, logNoteId: noteId, updatedAt: new Date() }
              : conv
          ),
        }));
      },

      markResultSaved: (conversationId, noteId) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? { ...conv, resultNoteId: noteId, updatedAt: new Date() }
              : conv
          ),
        }));
      },

      deleteConversation: (id) => {
        set((state) => ({
          conversations: state.conversations.filter((conv) => conv.id !== id),
          currentConversationId:
            state.currentConversationId === id ? null : state.currentConversationId,
        }));
      },

      clearCurrentConversation: () => {
        const { currentConversationId, conversations } = get();
        if (!currentConversationId) return;

        set({
          conversations: conversations.map((conv) =>
            conv.id === currentConversationId
              ? { ...conv, messages: [], title: '新对话', updatedAt: new Date() }
              : conv
          ),
        });
      },

      getCurrentConversation: () => {
        const { currentConversationId, conversations } = get();
        if (!currentConversationId) return null;
        return conversations.find((conv) => conv.id === currentConversationId) || null;
      },

      getRecentConversations: (limit = 10) => {
        return get()
          .conversations
          .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
          .slice(0, limit);
      },
    }),
    {
      name: 'ai-note-conversations',
      // 序列化日期
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
      }),
    }
  )
);
