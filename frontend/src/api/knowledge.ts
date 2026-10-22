import request from '@/utils/request';
import { ApiResponse, PageResponse, KnowledgeDoc, KnowledgeChunk } from '@/types';

export const knowledgeApi = {
  list: (params: { brand?: string; page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<KnowledgeDoc>>>('/knowledge', { params })
      .then(r => r.data.data!),

  // 上传知识库文档：使用项目封装的 axios 实例，统一走请求拦截器注入 X-API-Key，
  // 避免 bypass 鉴权与错误处理。axios 会自动处理 FormData 的 multipart 边界。
  upload: async (file: File, brand: string = '') => {
    const formData = new FormData();
    formData.append('file', file);
    if (brand) formData.append('brand', brand);
    const response = await request.post<ApiResponse<KnowledgeDoc>>('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data.data!;
  },

  search: (query: string, brand: string = '', top_k: number = 5) =>
    request.post<ApiResponse<KnowledgeChunk[]>>('/knowledge/search', { query, brand, top_k })
      .then(r => r.data.data!),

  delete: (id: number) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/knowledge/${id}`).then(r => r.data.data!),
};
