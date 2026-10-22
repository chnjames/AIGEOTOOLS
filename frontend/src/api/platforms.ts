import request from '@/utils/request';
import { ApiResponse, PlatformInfo, PlatformAccount, PublishResponse, PublishRecord } from '@/types';

export const platformsApi = {
  supported: () =>
    request.get<ApiResponse<PlatformInfo[]>>('/platforms/supported').then(r => r.data.data!),

  accounts: (brand: string = '') =>
    request.get<ApiResponse<PlatformAccount[]>>('/platforms/accounts', { params: { brand } })
      .then(r => r.data.data!),

  createAccount: (data: { platform: string; account_type: string; account_name?: string; api_key?: string; api_secret?: string; access_token?: string; config_json?: Record<string, unknown>; brand?: string }) =>
    request.post<ApiResponse<PlatformAccount>>('/platforms/accounts', data).then(r => r.data.data!),

  updateAccount: (id: number, data: Record<string, unknown>) =>
    request.put<ApiResponse<PlatformAccount>>(`/platforms/accounts/${id}`, data).then(r => r.data.data!),

  deleteAccount: (id: number) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/platforms/accounts/${id}`).then(r => r.data.data!),

  publish: (articleId: number, data: { platform: string; publish_method: string; config?: Record<string, unknown> }) =>
    request.post<ApiResponse<PublishResponse>>(`/platforms/publish/${articleId}`, data)
      .then(r => r.data.data!),

  publishRecords: (articleId?: number) =>
    request.get<ApiResponse<PublishRecord[]>>('/platforms/publish-records', {
      params: articleId ? { article_id: articleId } : {}
    }).then(r => r.data.data!),

  // 重试发布
  retryPublish: (recordId: number, config?: Record<string, unknown>) =>
    request.post<ApiResponse<PublishResponse>>(`/platforms/publish/${recordId}/retry`, config || {})
      .then(r => r.data.data!),
};
