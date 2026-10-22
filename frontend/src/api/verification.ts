import request, { sseClient } from '@/utils/request';
import { ApiResponse, PageResponse, VerifyResult } from '@/types';

export const verificationApi = {
  results: (params: { brand?: string; page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<VerifyResult>>>('/verification/results', { params })
      .then(r => r.data.data!),

  delete: (id: number) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/verification/results/${id}`)
      .then(r => r.data.data!),

  verifyStream: (
    body: {
      query: string;
      brand?: string;
      providers?: string[];
      verify_keys?: Record<string, string>;
      temperature?: number;
      mode?: string;
    },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/verification/verify', body, handlers),

  competitorStream: (
    body: { query: string; brand?: string; competitors?: string[]; providers?: string[]; verify_keys?: Record<string, string>; temperature?: number },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST('/verification/competitor', body, handlers),
};
