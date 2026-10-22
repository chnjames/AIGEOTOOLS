import request, { sseClient } from '@/utils/request';
import { ApiResponse, ContentMetrics } from '@/types';

export const scoringApi = {
  scoreStream: (
    body: { content: string; brand?: string; advantages?: string; platform?: string; temperature?: number; provider?: string; api_key?: string },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/scoring/score', body, handlers),

  metrics: (content: string, brand: string = '') =>
    request.post<ApiResponse<ContentMetrics>>('/scoring/metrics', { content, brand })
      .then(r => r.data.data!),

  quick: (content: string, brand: string = '') =>
    request.post<ApiResponse<{ has_title: boolean; has_list: boolean; has_faq: boolean; brand_count: number; word_count: number; quick_score: number }>>('/scoring/quick', { content, brand })
      .then(r => r.data.data!),
};
