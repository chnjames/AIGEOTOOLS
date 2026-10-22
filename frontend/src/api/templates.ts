import request, { downloadWithAuth } from '@/utils/request';
import { ApiResponse, PlatformTemplate, PlatformGroup } from '@/types';

export interface TemplateCreateData {
  name?: string;
  style_instruction?: string;
  filename_suffix?: string;
  group_name?: string;
  word_count_default?: number;
  is_active?: boolean;
  [key: string]: unknown;
}

export interface TemplateImportResult {
  imported: number;
  updated: number;
  skipped: number;
  errors?: Array<{ name: string; reason: string }>;
}

export const templatesApi = {
  // 获取模板列表
  listTemplates: (active_only?: boolean) =>
    request.get<ApiResponse<PlatformTemplate[]>>('/templates', { params: { active_only } })
      .then(r => r.data.data!),

  // 获取平台分组（替代 articlesApi.platformGroups）
  getPlatformGroups: () =>
    request.get<ApiResponse<PlatformGroup[]>>('/templates/groups')
      .then(r => r.data.data!),

  // 获取平台配置
  getPlatformConfig: () =>
    request.get<ApiResponse<Record<string, unknown>>>('/templates/config')
      .then(r => r.data.data!),

  // 创建模板
  createTemplate: (data: TemplateCreateData) =>
    request.post<ApiResponse<PlatformTemplate>>('/templates', data)
      .then(r => r.data.data!),

  // 更新模板
  updateTemplate: (id: number, data: Partial<TemplateCreateData>) =>
    request.put<ApiResponse<PlatformTemplate>>(`/templates/${id}`, data)
      .then(r => r.data.data!),

  // 删除模板
  deleteTemplate: (id: number) =>
    request.delete<ApiResponse<{ ok: boolean }>>(`/templates/${id}`)
      .then(r => r.data.data!),

  // 重置模板为默认
  resetTemplate: (id: number) =>
    request.post<ApiResponse<PlatformTemplate>>(`/templates/${id}/reset`)
      .then(r => r.data.data!),

  // 导出模板（触发下载）
  // 通过 X-API-Key 请求头传递凭证，避免将 API Key 暴露在 URL 查询参数中
  exportTemplates: (filename: string = 'templates.json') =>
    downloadWithAuth('/templates/export', filename),

  // 导入模板
  importTemplates: (templates: object[], strategy: string = 'skip') =>
    request.post<ApiResponse<TemplateImportResult>>('/templates/import', { templates, strategy })
      .then(r => r.data.data!),
};
