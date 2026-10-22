import request, { downloadWithAuth, sseClient } from '@/utils/request';
import { ApiResponse, PageResponse, Article, PlatformInfo, ArticleVersion, DiffResult, PlatformGroup } from '@/types';

export const articlesApi = {
  list: (params: { brand?: string; platform?: string; page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<Article>>>('/articles', { params })
      .then(r => r.data.data!),

  get: (id: number) =>
    request.get<ApiResponse<Article>>(`/articles/${id}`).then(r => r.data.data!),

  create: (data: { keyword: string; platform: string; content: string; filename?: string; brand?: string }) =>
    request.post<ApiResponse<Article>>('/articles', data).then(r => r.data.data!),

  update: (id: number, data: { content?: string; note?: string; filename?: string }) =>
    request.put<ApiResponse<Article>>(`/articles/${id}`, data).then(r => r.data.data!),

  delete: (id: number) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/articles/${id}`).then(r => r.data.data!),

  generateStream: (
    body: { keyword: string; platform: string; brand?: string; advantages?: string; word_count?: number; style?: string; temperature?: number; provider?: string; api_key?: string; use_knowledge?: boolean },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/articles/generate', body, handlers),

  batchGenerateStream: (
    body: { keywords: string[]; platforms: string[]; brand?: string; advantages?: string; word_count?: number; temperature?: number; provider?: string; api_key?: string; use_knowledge?: boolean; keyword_platforms?: Record<string, string[]> },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/articles/batch-generate', body, handlers),

  multimodalStream: (
    id: number,
    body: { generate_image_desc?: boolean; generate_video_script?: boolean; temperature?: number },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST(`/articles/${id}/multimodal`, body, handlers),

  // 批量下载文章：通过 X-API-Key 请求头鉴权获取 Blob 后触发下载，
  // 避免将 API Key 拼到 URL 查询参数中
  batchDownload: (ids: number[], filename: string = 'articles.zip') =>
    downloadWithAuth(`/articles/batch-download?ids=${ids.join(',')}`, filename),

  platforms: () =>
    request.get<ApiResponse<PlatformInfo[]>>('/articles/meta/platforms').then(r => r.data.data!),

  platformGroups: () =>
    request.get<ApiResponse<PlatformGroup[]>>('/articles/meta/platform-groups').then(r => r.data.data!),

  // 版本管理
  versions: (id: number) =>
    request.get<ApiResponse<ArticleVersion[]>>(`/articles/${id}/versions`).then(r => r.data.data!),

  version: (id: number, versionNumber: number) =>
    request.get<ApiResponse<ArticleVersion>>(`/articles/${id}/versions/${versionNumber}`).then(r => r.data.data!),

  rollback: (id: number, versionNumber: number) =>
    request.post<ApiResponse<Article>>(`/articles/${id}/rollback/${versionNumber}`).then(r => r.data.data!),

  diff: (id: number, version_a?: number, version_b?: number) =>
    request.get<ApiResponse<DiffResult>>(`/articles/${id}/diff`, { params: { version_a, version_b } })
      .then(r => r.data.data!),

  // 搜索文章
  searchArticles: (q: string, brand?: string, limit?: number) =>
    request.get<ApiResponse<Article[]>>('/articles/search', { params: { q, brand, limit } })
      .then(r => r.data.data!),

  // 获取原始内容
  getOriginalContent: (id: number) =>
    request.get<ApiResponse<{ content: string; keyword?: string; platform?: string }>>(`/articles/${id}/original`)
      .then(r => r.data.data!),
};
