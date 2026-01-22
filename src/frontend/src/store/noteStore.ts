import { create } from 'zustand';
import type { Note, NoteDetail, NoteCreate, NoteUpdate, NoteGroup } from '@/types';
import { noteService } from '@/services/noteService';

interface NoteState {
  notes: Note[];
  noteGroups: NoteGroup[];
  currentNote: NoteDetail | null;
  total: number;
  totalGroups: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchNotes: (params?: {
    page?: number;
    category?: string;
    status?: string;
  }) => Promise<void>;
  fetchNotesGrouped: (params?: {
    page?: number;
    category?: string;
  }) => Promise<void>;
  fetchNote: (id: number) => Promise<void>;
  createNote: (data: NoteCreate) => Promise<Note>;
  updateNote: (id: number, data: NoteUpdate) => Promise<Note>;
  deleteNote: (id: number) => Promise<void>;
  deleteRelation: (noteId: number, relatedNoteId: number) => Promise<void>;
  setCurrentNote: (note: NoteDetail | null) => void;
  clearError: () => void;
}

export const useNoteStore = create<NoteState>((set, get) => ({
  notes: [],
  noteGroups: [],
  currentNote: null,
  total: 0,
  totalGroups: 0,
  page: 1,
  pageSize: 20,
  isLoading: false,
  error: null,

  fetchNotes: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await noteService.getNotes({
        page: params?.page || get().page,
        page_size: get().pageSize,
        category: params?.category,
        status: params?.status || 'active',
      });
      set({
        notes: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: 'Failed to fetch notes',
        isLoading: false,
      });
    }
  },

  fetchNotesGrouped: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await noteService.getNotesGrouped({
        page: params?.page || get().page,
        page_size: get().pageSize,
        category: params?.category,
      });
      set({
        noteGroups: response.groups,
        totalGroups: response.total_groups,
        page: response.page,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: 'Failed to fetch grouped notes',
        isLoading: false,
      });
    }
  },

  fetchNote: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const note = await noteService.getNote(id);
      set({ currentNote: note, isLoading: false });
    } catch (error) {
      set({
        error: 'Failed to fetch note',
        isLoading: false,
      });
    }
  },

  createNote: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const note = await noteService.createNote(data);
      // Refresh notes list
      await get().fetchNotes();
      set({ isLoading: false });
      return note;
    } catch (error) {
      set({
        error: 'Failed to create note',
        isLoading: false,
      });
      throw error;
    }
  },

  updateNote: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const note = await noteService.updateNote(id, data);
      // Refresh notes list
      await get().fetchNotes();
      set({ isLoading: false });
      return note;
    } catch (error) {
      set({
        error: 'Failed to update note',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteNote: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await noteService.deleteNote(id);
      // Refresh notes list
      await get().fetchNotes();
      set({ isLoading: false });
    } catch (error) {
      set({
        error: 'Failed to delete note',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteRelation: async (noteId, relatedNoteId) => {
    try {
      await noteService.deleteRelation(noteId, relatedNoteId);
    } catch (error) {
      set({ error: 'Failed to delete relation' });
      throw error;
    }
  },

  setCurrentNote: (note) => {
    set({ currentNote: note });
  },

  clearError: () => {
    set({ error: null });
  },
}));
