import request, { sseClient } from '@/utils/request';
import { ApiResponse, PageResponse } from '@/types';

export interface MonitorTask {
  id: number;
  name: string;
  queries: string;
  platforms: string;
  schedule_type: string;
  schedule_time: string;
  is_active: boolean;
  brand?: string;
  competitors?: string;
  alert_threshold: number;
  last_run_at?: string;
  next_run_at?: string;
  created_at?: string;
}

export interface MonitorResult {
  id: number;
  task_id: number;
  query: string;
  platform: string;
  is_mentioned: boolean;
  mention_position?: string;
  mention_count: number;
  sentiment: string;
  content_snippet?: string;
  is_alert: boolean;
  run_batch: string;
  created_at?: string;
}

export interface AlertItem {
  id: number;
  alert_type: string;
  level: string;
  title: string;
  message?: string;
  is_read: boolean;
  task_id?: number;
  result_id?: number;
  created_at?: string;
}

export interface TrendPoint {
  date: string;
  platform: string;
  mention_rate: number;
  total_checks: number;
  mentioned_count: number;
}

export const monitorApi = {
  listTasks: (params: { page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<MonitorTask>>>('/monitor/tasks', { params }).then(r => r.data.data!),

  createTask: (data: { name: string; queries: string; platforms?: string; schedule_type?: string; schedule_time?: string; competitors?: string; alert_threshold?: number; brand?: string }) =>
    request.post<ApiResponse<MonitorTask>>('/monitor/tasks', data).then(r => r.data.data!),

  updateTask: (id: number, data: Partial<MonitorTask>) =>
    request.put<ApiResponse<MonitorTask>>(`/monitor/tasks/${id}`, data).then(r => r.data.data!),

  deleteTask: (id: number) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/monitor/tasks/${id}`).then(r => r.data.data!),

  toggleTask: (id: number) =>
    request.post<ApiResponse<MonitorTask>>(`/monitor/tasks/${id}/toggle`).then(r => r.data.data!),

  runTaskStream: (id: number, handlers: Parameters<typeof sseClient.connectPOST>[2]) =>
    sseClient.connectPOST(`/monitor/tasks/${id}/run`, {}, handlers),

  getResults: (taskId: number, params: { page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<MonitorResult>>>(`/monitor/tasks/${taskId}/results`, { params }).then(r => r.data.data!),

  getTrends: (params: { task_id?: number; platform?: string; days?: number } = {}) =>
    request.get<ApiResponse<TrendPoint[]>>('/monitor/trends', { params }).then(r => r.data.data!),

  listAlerts: (params: { unread_only?: boolean; page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<AlertItem>>>('/monitor/alerts', { params }).then(r => r.data.data!),

  markAlertRead: (id: number) =>
    request.put<ApiResponse<AlertItem>>(`/monitor/alerts/${id}/read`).then(r => r.data.data!),
};
