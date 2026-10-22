import request, { sseClient } from '@/utils/request';
import { ApiResponse, KPIData, CostReport, MentionReport } from '@/types';

export interface ApiCallRecord {
  id: number;
  operation_type: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  cost_cny: number;
  keyword?: string;
  platform?: string;
  brand?: string;
  created_at?: string;
}

export interface ApiCallSummary {
  total_calls: number;
  total_tokens: number;
  total_cost_cny: number;
  total_cost_usd: number;
}

export interface ApiCallResponse {
  items: ApiCallRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: ApiCallSummary;
}

export const reportsApi = {
  apiCalls: (params: { brand?: string; operation_type?: string; page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<ApiCallResponse>>('/reports/api-calls', { params })
      .then(r => r.data.data!),

  kpi: (brand: string = '') =>
    request.get<ApiResponse<KPIData>>('/reports/kpi', { params: { brand } })
      .then(r => r.data.data!),

  costs: (brand: string = '') =>
    request.get<ApiResponse<CostReport>>('/reports/costs', { params: { brand } })
      .then(r => r.data.data!),

  mentions: (brand: string = '') =>
    request.get<ApiResponse<MentionReport>>('/reports/mentions', { params: { brand } })
      .then(r => r.data.data!),

  roi: (brand: string = '') =>
    request.get<ApiResponse<Record<string, unknown>>>('/reports/roi', { params: { brand } })
      .then(r => r.data.data!),

  negative: (brand: string = '') =>
    request.get<ApiResponse<unknown[]>>('/reports/negative', { params: { brand } })
      .then(r => r.data.data!),

  suggestions: (brand: string = '') =>
    request.get<ApiResponse<unknown[]>>('/reports/optimization-suggestions', { params: { brand } })
      .then(r => r.data.data!),

  configOptimizerStream: (
    body: Record<string, unknown>,
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/reports/config-optimizer', body, handlers),
};
