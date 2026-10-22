import request from '@/utils/request';
import { ApiResponse, PageResponse } from '@/types';

export interface ROIOverview {
  total_actions: number;
  actions_by_type: Record<string, number>;
  total_cost_cny: number;
  current_mention_rate: number;
  mention_rate_change: number;
  mention_rate_change_pct: number;
  avg_score_change: number;
  cost_per_action: number;
  trend_days: number;
}

export interface ActionRankingItem {
  id: number;
  action_type: string;
  description?: string;
  platform?: string;
  keyword?: string;
  score_before?: number;
  score_after?: number;
  score_delta?: number;
  created_at?: string;
}

export interface TimelineData {
  mention_trend: Array<{ date: string; total: number; mentioned: number; rate: number }>;
  annotations: Array<{ date: string; type: string; description: string }>;
}

export interface ABComparison {
  has_data: boolean;
  split_date?: string;
  mention_rate_before?: number;
  mention_rate_after?: number;
  mention_rate_lift?: number;
  avg_score_before?: number;
  avg_score_after?: number;
  score_lift?: number;
  message?: string;
}

export interface MarketingReport {
  id: number;
  title: string;
  report_type: string;
  brand?: string;
  date_from?: string;
  date_to?: string;
  summary?: string;
  share_token?: string;
  is_published: boolean;
  created_at?: string;
  kpi_data?: Record<string, unknown>;
  mention_trend?: unknown[];
  cost_data?: Record<string, unknown>;
  optimization_effect?: unknown[];
  recommendations?: string[];
  markdown_content?: string;
}

export const analyticsApi = {
  roiOverview: (params: { brand?: string; days?: number } = {}) =>
    request.get<ApiResponse<ROIOverview>>('/analytics/roi-overview', { params }).then(r => r.data.data!),

  actionRanking: (params: { brand?: string; days?: number; limit?: number } = {}) =>
    request.get<ApiResponse<ActionRankingItem[]>>('/analytics/action-ranking', { params }).then(r => r.data.data!),

  timeline: (params: { brand?: string; days?: number } = {}) =>
    request.get<ApiResponse<TimelineData>>('/analytics/timeline', { params }).then(r => r.data.data!),

  abComparison: (params: { brand?: string } = {}) =>
    request.get<ApiResponse<ABComparison>>('/analytics/ab-comparison', { params }).then(r => r.data.data!),

  // Marketing reports
  generateReport: (data: { report_type?: string; brand?: string; date_from?: string; date_to?: string; title?: string }) =>
    request.post<ApiResponse<{ id: number; title: string; share_token: string }>>('/analytics/reports2/generate', data).then(r => r.data.data!),

  listReports: (params: { brand?: string; page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<MarketingReport>>>('/analytics/reports2/list', { params }).then(r => r.data.data!),

  getReport: (id: number) =>
    request.get<ApiResponse<MarketingReport>>(`/analytics/reports2/${id}`).then(r => r.data.data!),

  deleteReport: (id: number) =>
    request.delete<ApiResponse<{ deleted: boolean }>>(`/analytics/reports2/${id}`).then(r => r.data.data!),

  getSharedReport: (token: string) =>
    request.get<ApiResponse<MarketingReport>>(`/analytics/reports2/share/${token}`).then(r => r.data.data!),
};
