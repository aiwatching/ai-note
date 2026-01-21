// Note types
export interface Note {
  id: number;
  title: string | null;
  category: string | null;
  subcategory: string | null;
  tags: string[];
  summary: string | null;
  is_todo: boolean;
  is_schedule: boolean;
  priority: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface NoteDetail extends Note {
  raw_content: string;
  related_persons: string[];
  related_dates: string[];
  ai_analysis?: AIAnalysisResult;
}

export interface AIAnalysisResult {
  title: string | null;
  category: string | null;
  subcategory: string | null;
  tags: string[];
  summary: string | null;
  is_todo: boolean;
  is_schedule: boolean;
  priority: string | null;
  entities?: {
    persons?: string[];
    dates?: string[];
    locations?: string[];
    companies?: string[];
  };
  suggested_actions?: SuggestedAction[];
}

export interface SuggestedAction {
  type: string;
  title: string;
  due_date?: string;
  priority?: string;
  start_time?: string;
  participants?: string[];
}

export interface NoteListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Note[];
}

export interface NoteCreate {
  content: string;
  custom_prompt?: string;  // 自定义分析提示词
}

export interface NoteUpdate {
  content?: string;
  reanalyze?: boolean;
  custom_prompt?: string;  // 自定义分析提示词
}

// Todo types
export interface Todo {
  id: number;
  title: string;
  description: string | null;
  due_date: string | null;
  priority: string;
  status: string;
  note_id: number | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TodoListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Todo[];
}

export interface TodoCreate {
  title: string;
  description?: string;
  due_date?: string;
  priority?: string;
  note_id?: number;
}

export interface TodoUpdate {
  title?: string;
  description?: string;
  due_date?: string;
  priority?: string;
}

export interface TodoStatusUpdate {
  status: string;
}

// Search types
export interface SearchQuery {
  query: string;
  context?: Record<string, unknown>;
}

export interface SearchResult {
  note_id: number;
  title: string | null;
  summary: string | null;
  category: string | null;
  tags: string[];
  relevance_score: number;
  highlight: string | null;
  created_at: string;
}

export interface SearchSuggestion {
  action: string;
  description: string;
  data?: Record<string, unknown>;
}

export interface SearchResponse {
  intent: string;
  results: SearchResult[];
  suggestions: SearchSuggestion[];
  total: number;
}

// Common types
export type Priority = 'high' | 'medium' | 'low';
export type TodoStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';
export type NoteStatus = 'active' | 'archived' | 'deleted';

export const CATEGORIES = [
  '学习笔记',
  '工作记录',
  '客户问题',
  '需求记录',
  'Bug记录',
  '会议记录',
  '想法灵感',
  '个人杂记',
] as const;

export type Category = typeof CATEGORIES[number];

// Schedule types
export interface Schedule {
  id: number;
  user_id: number;
  note_id: number | null;
  title: string;
  description: string | null;
  location: string | null;
  participants: string[];
  start_time: string;
  end_time: string | null;
  is_all_day: boolean;
  recurrence: string | null;
  reminder_minutes: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ScheduleListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Schedule[];
}

export interface ScheduleCreate {
  title: string;
  description?: string;
  location?: string;
  participants?: string[];
  start_time: string;
  end_time?: string;
  is_all_day?: boolean;
  recurrence?: string;
  reminder_minutes?: number;
  note_id?: number;
}

export interface ScheduleUpdate {
  title?: string;
  description?: string;
  location?: string;
  participants?: string[];
  start_time?: string;
  end_time?: string;
  is_all_day?: boolean;
  recurrence?: string;
  reminder_minutes?: number;
}

export interface ScheduleStatusUpdate {
  status: string;
}

export type ScheduleStatus = 'scheduled' | 'completed' | 'cancelled';
