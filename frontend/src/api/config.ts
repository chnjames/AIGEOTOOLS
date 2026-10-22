import request from '@/utils/request';
import { ApiResponse, AppConfig, AppConfigUpdate, ProviderTestRequest } from '@/types';

export const configApi = {
  get: () => request.get<ApiResponse<AppConfig>>('/config').then(r => r.data.data!),
  update: (data: AppConfigUpdate) =>
    request.put<ApiResponse<AppConfig>>('/config', data).then(r => r.data.data!),
  testProvider: (data: ProviderTestRequest) =>
    request.post<ApiResponse<{ success: boolean; message: string }>>('/config/test', data)
      .then(r => r.data.data!),
};
