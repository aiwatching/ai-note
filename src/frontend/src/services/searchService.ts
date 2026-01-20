import api from './api';
import type { SearchQuery, SearchResponse } from '@/types';

export const searchService = {
  async search(query: SearchQuery): Promise<SearchResponse> {
    const response = await api.post<SearchResponse>('/search', query);
    return response.data;
  },
};
