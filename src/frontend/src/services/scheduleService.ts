import api from './api';
import type {
  Schedule,
  ScheduleCreate,
  ScheduleListResponse,
  ScheduleUpdate,
  ScheduleStatusUpdate,
} from '@/types';

export const scheduleService = {
  async getSchedules(params?: {
    start_date?: string;
    end_date?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<ScheduleListResponse> {
    const response = await api.get('/schedules', { params });
    return response.data;
  },

  async getUpcomingSchedules(limit?: number): Promise<Schedule[]> {
    const response = await api.get('/schedules/upcoming', {
      params: { limit },
    });
    return response.data;
  },

  async getSchedule(id: number): Promise<Schedule> {
    const response = await api.get(`/schedules/${id}`);
    return response.data;
  },

  async createSchedule(data: ScheduleCreate): Promise<Schedule> {
    const response = await api.post('/schedules', data);
    return response.data;
  },

  async updateSchedule(id: number, data: ScheduleUpdate): Promise<Schedule> {
    const response = await api.put(`/schedules/${id}`, data);
    return response.data;
  },

  async updateScheduleStatus(
    id: number,
    data: ScheduleStatusUpdate
  ): Promise<Schedule> {
    const response = await api.patch(`/schedules/${id}/status`, data);
    return response.data;
  },

  async deleteSchedule(id: number): Promise<void> {
    await api.delete(`/schedules/${id}`);
  },
};
