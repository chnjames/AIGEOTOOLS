import request, { sseClient } from '@/utils/request';
import { ApiResponse, PageResponse, Keyword, KeywordQuality, IndustryPreset } from '@/types';

export interface KeywordCreateResponse {
  saved: Keyword[];
  duplicates_skipped: number;
  errors: Array<{ keyword: string; reason: string }>;
}

export const keywordsApi = {
  list: (params: { brand?: string; page?: number; page_size?: number; is_favorite?: boolean; tag?: string; search?: string } = {}) =>
    request.get<ApiResponse<PageResponse<Keyword>>>('/keywords', { params })
      .then(r => r.data.data!),

  create: (keywords: string[], brand: string = '') =>
    request.post<ApiResponse<KeywordCreateResponse>>('/keywords', { keywords, brand })
      .then(r => r.data.data!),

  delete: (id: number) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/keywords/${id}`).then(r => r.data.data!),

  deleteAll: (brand: string = '') =>
    request.delete<ApiResponse<{ deleted: number }>>('/keywords', { params: { brand } })
      .then(r => r.data.data!),

  combinations: (core_keyword: string, max_results: number = 50) =>
    request.post<ApiResponse<string[]>>('/keywords/combinations', null, {
      params: { core_keyword, max_results }
    }).then(r => r.data.data!),

  // SSE streaming endpoints
  generateStream: (
    body: { core_keyword: string; brand?: string; advantages?: string; max_results?: number; polish?: boolean; temperature?: number; provider?: string; api_key?: string },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/keywords/generate', body, handlers),

  mineStream: (
    body: { keyword: string; brand?: string; temperature?: number },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/keywords/mine', body, handlers),

  expandStream: (
    body: { keywords: string[]; brand?: string; temperature?: number },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/keywords/expand', body, handlers),

  cluster: (body: { keywords: string[]; brand?: string; temperature?: number }) =>
    request.post<ApiResponse<{ clusters: unknown[]; summary: string }>>('/keywords/cluster', body)
      .then(r => r.data.data!),

  // 新功能
  industryPresets: () =>
    request.get<ApiResponse<IndustryPreset[]>>('/keywords/meta/industry-presets').then(r => r.data.data!),

  analyzeQuality: (keywords: string[]) =>
    request.post<ApiResponse<KeywordQuality>>('/keywords/analyze-quality', keywords).then(r => r.data.data!),

  // 搜索关键词
  searchKeywords: (q: string, brand?: string, limit?: number) =>
    request.get<ApiResponse<Keyword[]>>('/keywords/search', { params: { q, brand, limit } })
      .then(r => r.data.data!),

  // 收藏/取消收藏
  toggleFavorite: (id: number) =>
    request.post<ApiResponse<{ is_favorite: boolean }>>(`/keywords/${id}/favorite`)
      .then(r => r.data.data!),

  // 设置标签
  setTags: (id: number, tags: string[]) =>
    request.put<ApiResponse<Keyword>>(`/keywords/${id}/tags`, { tags })
      .then(r => r.data.data!),

  // 导入关键词到目标品牌
  importKeywords: (keyword_ids: number[], target_brand: string) =>
    request.post<ApiResponse<{ imported: number; skipped: number }>>('/keywords/import', { keyword_ids, target_brand })
      .then(r => r.data.data!),
};
