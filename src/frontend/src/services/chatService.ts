import api from './api';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  provider?: string;
  timestamp?: string;
}

export interface ProviderResponse {
  provider: string;
  content: string;
  error?: string | null;
}

export interface ChatResponse {
  responses: ProviderResponse[];
  note_context?: string | null;
  session_id?: number | null;
}

export interface ProvidersResponse {
  providers: string[];
  descriptions: Record<string, string>;
}

// Session types
export interface ChatSessionOut {
  id: number;
  title: string | null;
  summary: string | null;
  providers: string[];
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  linked_note_ids: number[];
}

export interface ChatMessageOut {
  id: number;
  role: string;
  content: string;
  provider: string | null;
  all_responses: ProviderResponse[];
  created_at: string;
}

export interface ChatSessionDetail {
  id: number;
  title: string | null;
  summary: string | null;
  providers: string[];
  status: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessageOut[];
  linked_note_ids: number[];
}

export interface ChatSessionList {
  items: ChatSessionOut[];
  total: number;
  page: number;
  page_size: number;
}

export const chatService = {
  async getProviders(): Promise<ProvidersResponse> {
    const response = await api.get<ProvidersResponse>('/chat/providers');
    return response.data;
  },

  async sendMessage(
    message: string,
    providers: string[],
    noteIds?: number[],
    conversationHistory?: ChatMessage[],
    sessionId?: number | null
  ): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/chat', {
      message,
      providers,
      note_ids: noteIds,
      conversation_history: conversationHistory?.map(msg => ({
        role: msg.role,
        content: msg.content,
        provider: msg.provider,
      })),
      session_id: sessionId,
    });
    return response.data;
  },

  // Session management
  async listSessions(page = 1, pageSize = 20, status?: string): Promise<ChatSessionList> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) params.append('status', status);
    const response = await api.get<ChatSessionList>(`/chat/sessions?${params}`);
    return response.data;
  },

  async getSession(sessionId: number): Promise<ChatSessionDetail> {
    const response = await api.get<ChatSessionDetail>(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  async createSession(providers: string[], title?: string, noteIds?: number[]): Promise<ChatSessionOut> {
    const response = await api.post<ChatSessionOut>('/chat/sessions', {
      providers,
      title,
      note_ids: noteIds,
    });
    return response.data;
  },

  async updateSession(sessionId: number, data: { title?: string; status?: string }): Promise<ChatSessionOut> {
    const response = await api.patch<ChatSessionOut>(`/chat/sessions/${sessionId}`, data);
    return response.data;
  },

  async deleteSession(sessionId: number): Promise<void> {
    await api.delete(`/chat/sessions/${sessionId}`);
  },

  async linkNotesToSession(sessionId: number, noteIds: number[]): Promise<{ linked_note_ids: number[] }> {
    const response = await api.post(`/chat/sessions/${sessionId}/link-notes`, noteIds);
    return response.data;
  },

  async exportToNote(sessionId: number, title?: string, includeAllProviders = true): Promise<{ note_id: number; note_title: string }> {
    const response = await api.post(`/chat/sessions/${sessionId}/export-to-note`, {
      title,
      include_all_providers: includeAllProviders,
    });
    return response.data;
  },

  async getSessionsByNote(noteId: number): Promise<ChatSessionOut[]> {
    const response = await api.get<ChatSessionOut[]>(`/chat/by-note/${noteId}`);
    return response.data;
  },
};
