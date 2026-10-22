import request, { sseClient } from '@/utils/request';
import { ApiResponse, PageResponse, Optimization } from '@/types';

export const optimizationsApi = {
  list: (params: { brand?: string; page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<Optimization>>>('/optimizations', { params })
      .then(r => r.data.data!),

  eeatStream: (
    body: { content: string; brand?: string; advantages?: string; platform?: string; temperature?: number; provider?: string; api_key?: string; use_knowledge?: boolean; article_id?: number },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/optimizations/eeat', body, handlers),

  factDensityStream: (
    body: { content: string; brand?: string; platform?: string; temperature?: number; provider?: string; api_key?: string; use_knowledge?: boolean; article_id?: number },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/optimizations/fact-density', body, handlers),

  generateSchema: (body: { content: string; schema_type: string; brand?: string }) =>
    request.post<ApiResponse<{ json_ld: string; schema_type: string }>>('/optimizations/schema', body)
      .then(r => r.data.data!),

  techConfig: (body: { brand?: string; website_url?: string; keywords?: string[]; platforms?: string[] }) =>
    request.post<ApiResponse<{ robots_txt: string; sitemap_xml: string; meta_tags: string; structured_data: string }>>('/optimizations/tech-config', body)
      .then(r => r.data.data!),

  checkUniqueness: (body: { content: string; reference_contents?: string[] }) =>
    request.post<ApiResponse<{ uniqueness_score: number; duplicate_segments: string[]; suggestions: string[] }>>('/optimizations/uniqueness', body)
      .then(r => r.data.data!),

  techniques: () =>
    request.get<ApiResponse<Array<{ name: string; category: string; description: string; example: string }>>>('/optimizations/techniques')
      .then(r => r.data.data!),

  // 获取文章原始内容（用于优化前展示）
  getOriginalContent: (articleId: number) =>
    request.get<ApiResponse<{ content: string; keyword?: string; platform?: string; brand?: string }>>(
      `/optimizations/articles/${articleId}/original-content`
    ).then(r => r.data.data!),
};
