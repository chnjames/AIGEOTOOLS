import request, { sseClient } from '@/utils/request';
import { ApiResponse, PageResponse, Workflow, WorkflowExecution, WorkflowStep } from '@/types';

export const workflowsApi = {
  list: (brand: string = '') =>
    request.get<ApiResponse<Workflow[]>>('/workflows', { params: { brand } })
      .then(r => r.data.data!),

  create: (data: { name: string; steps: WorkflowStep[]; brand?: string; schedule?: string; conditions?: Record<string, unknown> }) =>
    request.post<ApiResponse<Workflow>>('/workflows', data).then(r => r.data.data!),

  update: (id: string, data: Partial<{ name: string; steps: WorkflowStep[]; enabled: boolean; schedule: string; conditions: Record<string, unknown> }>) =>
    request.put<ApiResponse<Workflow>>(`/workflows/${id}`, data).then(r => r.data.data!),

  delete: (id: string) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/workflows/${id}`).then(r => r.data.data!),

  toggle: (id: string, enabled: boolean) =>
    request.post<ApiResponse<Workflow>>(`/workflows/${id}/toggle`, { enabled }).then(r => r.data.data!),

  executeStream: (
    id: string,
    body: { brand?: string; advantages?: string; keywords?: string[]; platforms?: string[]; temperature?: number; provider?: string; api_key?: string },
    handlers: Parameters<typeof sseClient.connectPOST>[2]
  ) => sseClient.connectPOST(`/workflows/${id}/execute`, body, handlers),

  executions: (workflowId: string, params: { page?: number; page_size?: number } = {}) =>
    request.get<ApiResponse<PageResponse<WorkflowExecution>>>(`/workflows/${workflowId}/executions`, { params })
      .then(r => r.data.data!),

  templates: () =>
    request.get<ApiResponse<unknown[]>>('/workflows/templates/list').then(r => r.data.data!),
};
