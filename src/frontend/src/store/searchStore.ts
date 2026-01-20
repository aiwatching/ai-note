import { create } from 'zustand';
import type { SearchResult, SearchSuggestion } from '@/types';
import { searchService } from '@/services/searchService';

interface SearchState {
  query: string;
  intent: string;
  results: SearchResult[];
  suggestions: SearchSuggestion[];
  isLoading: boolean;
  error: string | null;

  // Actions
  search: (query: string) => Promise<void>;
  setQuery: (query: string) => void;
  clearResults: () => void;
  clearError: () => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  query: '',
  intent: '',
  results: [],
  suggestions: [],
  isLoading: false,
  error: null,

  search: async (query) => {
    set({ isLoading: true, error: null, query });
    try {
      const response = await searchService.search({ query });
      set({
        intent: response.intent,
        results: response.results,
        suggestions: response.suggestions,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: 'Failed to search',
        isLoading: false,
      });
    }
  },

  setQuery: (query) => {
    set({ query });
  },

  clearResults: () => {
    set({
      query: '',
      intent: '',
      results: [],
      suggestions: [],
    });
  },

  clearError: () => {
    set({ error: null });
  },
}));
