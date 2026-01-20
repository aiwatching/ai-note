import api from './api';
import type {
  Todo,
  TodoListResponse,
  TodoCreate,
  TodoUpdate,
  TodoStatusUpdate,
} from '@/types';

export const todoService = {
  async getTodos(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    priority?: string;
    due_date_from?: string;
    due_date_to?: string;
  }): Promise<TodoListResponse> {
    const response = await api.get<TodoListResponse>('/todos', { params });
    return response.data;
  },

  async getTodo(id: number): Promise<Todo> {
    const response = await api.get<Todo>(`/todos/${id}`);
    return response.data;
  },

  async createTodo(data: TodoCreate): Promise<Todo> {
    const response = await api.post<Todo>('/todos', data);
    return response.data;
  },

  async updateTodo(id: number, data: TodoUpdate): Promise<Todo> {
    const response = await api.put<Todo>(`/todos/${id}`, data);
    return response.data;
  },

  async updateTodoStatus(id: number, data: TodoStatusUpdate): Promise<Todo> {
    const response = await api.patch<Todo>(`/todos/${id}/status`, data);
    return response.data;
  },

  async deleteTodo(id: number): Promise<void> {
    await api.delete(`/todos/${id}`);
  },

  async createTodosFromNote(noteId: number, autoExtract: boolean = true): Promise<Todo[]> {
    const response = await api.post<Todo[]>('/todos/from-note', {
      note_id: noteId,
      auto_extract: autoExtract,
    });
    return response.data;
  },
};
