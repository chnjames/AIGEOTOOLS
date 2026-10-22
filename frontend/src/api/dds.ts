import request, { sseClient } from '@/utils/request';
import { ApiResponse } from '@/types';

export interface DDSScoreResult {
  semantic_depth: { score: number; sub_scores: Record<string, number>; details: string };
  data_support: { score: number; sub_scores: Record<string, number>; details: string };
  authoritative_source: { score: number; sub_scores: Record<string, number>; details: string };
  total_score: number;
  improvements: string[];
  strengths: string[];
  level?: string;
  level_color?: string;
}

export interface DDSHistoryItem {
  id: number;
  semantic_depth: number;
  data_support: number;
  authoritative_source: number;
  total_score: number;
  article_id?: number;
  brand?: string;
  created_at?: string;
}

export const ddsApi = {
  scoreStream: (
    body: { content: string; brand?: string; temperature?: number; provider?: string; api_key?: string },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/dds/score', body, handlers),

  history: (params: { article_id?: number; brand?: string; limit?: number } = {}) =>
    request.get<ApiResponse<DDSHistoryItem[]>>('/dds/history', { params }).then(r => r.data.data!),
};
