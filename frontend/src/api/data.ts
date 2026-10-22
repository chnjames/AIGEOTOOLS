import request, { downloadWithAuth } from '@/utils/request';
import { ApiResponse, PageResponse, StorageStats, AuditLog, CleanupResult, ImportResult } from '@/types';

export const dataApi = {
  // 获取存储统计
  getStorageStats: () =>
    request.get<ApiResponse<StorageStats>>('/data/storage')
      .then(r => r.data.data!),

  // 全量导出并触发下载
  // 通过 X-API-Key 请求头传递凭证，避免将 API Key 暴露在 URL 查询参数中
  exportAll: (filename?: string) =>
    downloadWithAuth('/data/export/all', filename),

  // 指定模块 CSV 导出并触发下载
  exportCsv: (module: string, filename?: string) =>
    downloadWithAuth(`/data/export/csv/${encodeURIComponent(module)}`, filename),

  // 导入数据
  importData: (data: object, strategy: string) =>
    request.post<ApiResponse<ImportResult>>('/data/import', { data, strategy })
      .then(r => r.data.data!),

  // 清理旧数据
  cleanupOldData: (days: number, tables: string[]) =>
    request.post<ApiResponse<CleanupResult>>('/data/cleanup', { days, tables })
      .then(r => r.data.data!),

  // 获取审计日志
  getAuditLogs: (page: number = 1, page_size: number = 20, action?: string, resource_type?: string) =>
    request.get<ApiResponse<PageResponse<AuditLog>>>('/data/audit-logs', {
      params: { page, page_size, action, resource_type }
    }).then(r => r.data.data!),
};
