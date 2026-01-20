import api from './api';
import type {
  Note,
  NoteDetail,
  NoteListResponse,
  NoteCreate,
  NoteUpdate,
} from '@/types';

export const noteService = {
  async getNotes(params?: {
    page?: number;
    page_size?: number;
    category?: string;
    status?: string;
    sort_by?: string;
    order?: string;
  }): Promise<NoteListResponse> {
    const response = await api.get<NoteListResponse>('/notes', { params });
    return response.data;
  },

  async getNote(id: number): Promise<NoteDetail> {
    const response = await api.get<NoteDetail>(`/notes/${id}`);
    return response.data;
  },

  async createNote(data: NoteCreate): Promise<Note> {
    const response = await api.post<Note>('/notes', data);
    return response.data;
  },

  async updateNote(id: number, data: NoteUpdate): Promise<Note> {
    const response = await api.put<Note>(`/notes/${id}`, data);
    return response.data;
  },

  async deleteNote(id: number): Promise<void> {
    await api.delete(`/notes/${id}`);
  },
};
