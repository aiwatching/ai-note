import { create } from 'zustand';
import type { Todo, TodoCreate, TodoUpdate } from '@/types';
import { todoService } from '@/services/todoService';

interface TodoState {
  todos: Todo[];
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchTodos: (params?: {
    page?: number;
    status?: string;
    priority?: string;
  }) => Promise<void>;
  createTodo: (data: TodoCreate) => Promise<Todo>;
  updateTodo: (id: number, data: TodoUpdate) => Promise<Todo>;
  updateTodoStatus: (id: number, status: string) => Promise<Todo>;
  deleteTodo: (id: number) => Promise<void>;
  createTodosFromNote: (noteId: number) => Promise<Todo[]>;
  clearError: () => void;
}

export const useTodoStore = create<TodoState>((set, get) => ({
  todos: [],
  total: 0,
  page: 1,
  pageSize: 50,
  isLoading: false,
  error: null,

  fetchTodos: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await todoService.getTodos({
        page: params?.page || get().page,
        page_size: get().pageSize,
        status: params?.status,
        priority: params?.priority,
      });
      set({
        todos: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: 'Failed to fetch todos',
        isLoading: false,
      });
    }
  },

  createTodo: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const todo = await todoService.createTodo(data);
      await get().fetchTodos();
      set({ isLoading: false });
      return todo;
    } catch (error) {
      set({
        error: 'Failed to create todo',
        isLoading: false,
      });
      throw error;
    }
  },

  updateTodo: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const todo = await todoService.updateTodo(id, data);
      await get().fetchTodos();
      set({ isLoading: false });
      return todo;
    } catch (error) {
      set({
        error: 'Failed to update todo',
        isLoading: false,
      });
      throw error;
    }
  },

  updateTodoStatus: async (id, status) => {
    try {
      const todo = await todoService.updateTodoStatus(id, { status });
      // Update local state immediately
      set((state) => ({
        todos: state.todos.map((t) =>
          t.id === id ? { ...t, status, completed_at: status === 'completed' ? new Date().toISOString() : null } : t
        ),
      }));
      return todo;
    } catch (error) {
      set({ error: 'Failed to update todo status' });
      throw error;
    }
  },

  deleteTodo: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await todoService.deleteTodo(id);
      await get().fetchTodos();
      set({ isLoading: false });
    } catch (error) {
      set({
        error: 'Failed to delete todo',
        isLoading: false,
      });
      throw error;
    }
  },

  createTodosFromNote: async (noteId) => {
    set({ isLoading: true, error: null });
    try {
      const todos = await todoService.createTodosFromNote(noteId);
      await get().fetchTodos();
      set({ isLoading: false });
      return todos;
    } catch (error) {
      set({
        error: 'Failed to create todos from note',
        isLoading: false,
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
