import { create } from 'zustand';
import type { Schedule, ScheduleCreate, ScheduleUpdate } from '@/types';
import { scheduleService } from '@/services/scheduleService';

interface ScheduleState {
  schedules: Schedule[];
  upcomingSchedules: Schedule[];
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchSchedules: (params?: {
    page?: number;
    status?: string;
    start_date?: string;
    end_date?: string;
  }) => Promise<void>;
  fetchUpcomingSchedules: (limit?: number) => Promise<void>;
  createSchedule: (data: ScheduleCreate) => Promise<Schedule>;
  updateSchedule: (id: number, data: ScheduleUpdate) => Promise<Schedule>;
  updateScheduleStatus: (id: number, status: string) => Promise<Schedule>;
  deleteSchedule: (id: number) => Promise<void>;
  clearError: () => void;
}

export const useScheduleStore = create<ScheduleState>((set, get) => ({
  schedules: [],
  upcomingSchedules: [],
  total: 0,
  page: 1,
  pageSize: 50,
  isLoading: false,
  error: null,

  fetchSchedules: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await scheduleService.getSchedules({
        page: params?.page || get().page,
        page_size: get().pageSize,
        status: params?.status,
        start_date: params?.start_date,
        end_date: params?.end_date,
      });
      set({
        schedules: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: 'Failed to fetch schedules',
        isLoading: false,
      });
    }
  },

  fetchUpcomingSchedules: async (limit = 10) => {
    set({ isLoading: true, error: null });
    try {
      const schedules = await scheduleService.getUpcomingSchedules(limit);
      set({
        upcomingSchedules: schedules,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: 'Failed to fetch upcoming schedules',
        isLoading: false,
      });
    }
  },

  createSchedule: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const schedule = await scheduleService.createSchedule(data);
      await get().fetchSchedules();
      set({ isLoading: false });
      return schedule;
    } catch (error) {
      set({
        error: 'Failed to create schedule',
        isLoading: false,
      });
      throw error;
    }
  },

  updateSchedule: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const schedule = await scheduleService.updateSchedule(id, data);
      await get().fetchSchedules();
      set({ isLoading: false });
      return schedule;
    } catch (error) {
      set({
        error: 'Failed to update schedule',
        isLoading: false,
      });
      throw error;
    }
  },

  updateScheduleStatus: async (id, status) => {
    try {
      const schedule = await scheduleService.updateScheduleStatus(id, { status });
      // Update local state immediately
      set((state) => ({
        schedules: state.schedules.map((s) =>
          s.id === id ? { ...s, status } : s
        ),
        upcomingSchedules: state.upcomingSchedules.map((s) =>
          s.id === id ? { ...s, status } : s
        ),
      }));
      return schedule;
    } catch (error) {
      set({ error: 'Failed to update schedule status' });
      throw error;
    }
  },

  deleteSchedule: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await scheduleService.deleteSchedule(id);
      await get().fetchSchedules();
      set({ isLoading: false });
    } catch (error) {
      set({
        error: 'Failed to delete schedule',
        isLoading: false,
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
