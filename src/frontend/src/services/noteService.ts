import api from './api';
import type {
  Note,
  NoteDetail,
  NoteListResponse,
  NoteCreate,
  NoteUpdate,
  NoteGroupedResponse,
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

  async getNotesGrouped(params?: {
    page?: number;
    page_size?: number;
    category?: string;
  }): Promise<NoteGroupedResponse> {
    const response = await api.get<NoteGroupedResponse>('/notes/grouped', { params });
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

  async deleteAllNotes(hardDelete: boolean = false): Promise<{ message: string; count: number }> {
    const response = await api.delete<{ message: string; count: number }>('/notes', {
      params: { hard_delete: hardDelete },
    });
    return response.data;
  },

  async deleteRelation(noteId: number, relatedNoteId: number): Promise<void> {
    await api.delete(`/notes/${noteId}/relations/${relatedNoteId}`);
  },

  async recalculateRelations(): Promise<{ message: string; relations_created: number }> {
    const response = await api.post<{ message: string; relations_created: number }>('/notes/recalculate-relations');
    return response.data;
  },

  async getSuggestedRelations(noteId: number, minSimilarity: number = 0.2): Promise<{
    note_id: number;
    suggestions: Array<{
      note_id: number;
      title: string;
      category: string | null;
      summary: string | null;
      created_at: string;
      similarity: number;
      is_linked: boolean;
    }>;
  }> {
    const response = await api.get(`/notes/${noteId}/suggestions`, {
      params: { min_similarity: minSimilarity }
    });
    return response.data;
  },

  async createManualRelation(noteId: number, targetNoteId: number): Promise<{ message: string }> {
    const response = await api.post<{ message: string }>(`/notes/${noteId}/relations/${targetNoteId}`);
    return response.data;
  },
};
