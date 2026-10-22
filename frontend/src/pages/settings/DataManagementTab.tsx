import React, { useEffect, useState, useCallback } from 'react';
import {
  Card, Button, Space, message, Divider, Alert, Spin, Row, Col,
  Statistic, Radio, Upload, Checkbox, Empty, Typography, Table, Tag,
  Tooltip, Popconfirm, InputNumber,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { UploadProps } from 'antd/es/upload';
import {
  DatabaseOutlined, DownloadOutlined, UploadOutlined, DeleteOutlined,
  ReloadOutlined, FileTextOutlined, ExportOutlined, ImportOutlined,
  WarningOutlined, HistoryOutlined, EyeOutlined,
} from '@ant-design/icons';
import { dataApi } from '@/api/data';
import type {
  StorageStats, AuditLog, CleanupResult, ImportResult,
} from '@/types';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CLEANUP_TABLES = [
  { label: 'API 调用记录', value: 'api_calls' },
  { label: '验证记录', value: 'verify_results' },
  { label: '工作流执行记录', value: 'workflow_executions' },
  { label: '监控结果', value: 'monitor_results' },
];

const CSV_EXPORT_MODULES = [
  { label: '关键词', value: 'keywords' },
  { label: '文章', value: 'articles' },
  { label: '验证记录', value: 'verify_results' },
  { label: 'API 调用记录', value: 'api_calls' },
];

const TABLE_NAME_LABELS: Record<string, string> = {
  keywords: '关键词',
  articles: '文章',
  optimizations: '优化记录',
  verify_results: '验证记录',
  api_calls: 'API 调用记录',
  platform_accounts: '平台账号',
  workflows: '工作流',
  workflow_executions: '工作流执行记录',
  publish_records: '发布记录',
  knowledge_docs: '知识库文档',
  knowledge_chunks: '知识片段',
  audit_logs: '审计日志',
  article_versions: '文章版本',
  platform_templates: '平台模板',
  monitor_results: '监控结果',
};

const AUDIT_ACTION_COLORS: Record<string, string> = {
  create: 'green', update: 'blue', delete: 'red',
  import: 'purple', export: 'cyan', cleanup: 'orange',
  login: 'geekblue', config: 'gold', reset: 'volcano',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return '未知';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
}

function formatDateTime(iso?: string): string {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', { hour12: false });
  } catch (err) {
    console.warn('[DataManagementTab] formatDateTime failed, returning raw iso:', err);
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DataManagementTabProps {
  /** Current brand name from app config (reserved for brand-scoped actions). */
  brand?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const DataManagementTab: React.FC<DataManagementTabProps> = ({ brand: _brand }) => {
  // ---- Storage Stats ----
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [storageLoading, setStorageLoading] = useState(false);

  // ---- Import ----
  const [importStrategy, setImportStrategy] = useState<'skip' | 'overwrite' | 'append'>('skip');
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);

  // ---- Cleanup ----
  const [cleanupDays, setCleanupDays] = useState(90);
  const [cleanupTables, setCleanupTables] = useState<string[]>(['api_calls']);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const [cleanupLoading, setCleanupLoading] = useState(false);

  // ---- Audit Logs ----
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotal, setAuditTotal] = useState(0);
  const auditPageSize = 20;

  // -----------------------------------------------------------------
  // Data loaders
  // -----------------------------------------------------------------

  const loadStorageStats = useCallback(async () => {
    setStorageLoading(true);
    try {
      const stats = await dataApi.getStorageStats();
      setStorageStats(stats);
    } catch (e: unknown) {
      message.error('加载存储统计失败：' + (e as Error).message);
    } finally {
      setStorageLoading(false);
    }
  }, []);

  const loadAuditLogs = useCallback(async (page: number = 1) => {
    setAuditLoading(true);
    try {
      const result = await dataApi.getAuditLogs(page, auditPageSize);
      setAuditLogs(result.items);
      setAuditTotal(result.total);
      setAuditPage(page);
    } catch (e: unknown) {
      message.error('加载审计日志失败：' + (e as Error).message);
    } finally {
      setAuditLoading(false);
    }
  }, []);

  // Load data on mount
  useEffect(() => {
    loadStorageStats();
    loadAuditLogs(1);
  }, [loadStorageStats, loadAuditLogs]);

  // -----------------------------------------------------------------
  // Export handlers
  // -----------------------------------------------------------------

  const handleExportAll = () => {
    const filename = `backup_${new Date().toISOString().slice(0, 10)}.json`;
    dataApi.exportAll(filename)
      .then(() => message.success('开始下载全量备份文件'))
      .catch((e: unknown) => message.error('下载失败：' + (e as Error).message));
  };

  const handleExportCsv = (module: string, label: string) => {
    const filename = `${label}_${new Date().toISOString().slice(0, 10)}.csv`;
    dataApi.exportCsv(module, filename)
      .then(() => message.success(`开始下载${label} CSV`))
      .catch((e: unknown) => message.error('下载失败：' + (e as Error).message));
  };

  // -----------------------------------------------------------------
  // Import handlers
  // -----------------------------------------------------------------

  const handleImportFileChange: UploadProps['beforeUpload'] = (file) => {
    setImportFile(file);
    setImportResult(null);
    return false; // prevent auto upload
  };

  const handleImportRemove = () => {
    setImportFile(null);
    setImportResult(null);
  };

  const handleImport = async () => {
    if (!importFile) {
      message.warning('请先选择要导入的 JSON 文件');
      return;
    }
    setImportLoading(true);
    setImportResult(null);
    try {
      const text = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(new Error('文件读取失败'));
        reader.readAsText(importFile);
      });
      let data: object;
      try {
        data = JSON.parse(text);
      } catch (err) {
        console.error('[DataManagementTab] JSON.parse failed:', err);
        throw new Error('JSON 解析失败，请检查文件格式');
      }
      const result = await dataApi.importData(data, importStrategy);
      setImportResult(result);
      message.success('数据导入完成');
    } catch (e: unknown) {
      message.error('导入失败：' + (e as Error).message);
    } finally {
      setImportLoading(false);
    }
  };

  // -----------------------------------------------------------------
  // Cleanup handlers
  // -----------------------------------------------------------------

  const handleCleanup = async () => {
    if (cleanupTables.length === 0) {
      message.warning('请至少选择一个要清理的数据表');
      return;
    }
    setCleanupLoading(true);
    setCleanupResult(null);
    try {
      const result = await dataApi.cleanupOldData(cleanupDays, cleanupTables);
      setCleanupResult(result);
      message.success('数据清理完成');
      loadStorageStats(); // refresh stats after cleanup
    } catch (e: unknown) {
      message.error('清理失败：' + (e as Error).message);
    } finally {
      setCleanupLoading(false);
    }
  };

  // -----------------------------------------------------------------
  // Audit table change
  // -----------------------------------------------------------------

  const handleAuditTableChange = (pagination: TablePaginationConfig) => {
    loadAuditLogs(pagination.current ?? 1);
  };

  // -----------------------------------------------------------------
  // Table columns
  // -----------------------------------------------------------------

  const auditColumns: ColumnsType<AuditLog> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (v?: string) => <Text style={{ fontSize: 12 }}>{formatDateTime(v)}</Text>,
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 110,
      render: (action: string) => (
        <Tag color={AUDIT_ACTION_COLORS[action] || 'default'}>
          {action || '-'}
        </Tag>
      ),
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 130,
      render: (rt: string) => <Tag>{rt || '-'}</Tag>,
    },
    {
      title: '结果',
      dataIndex: 'result',
      key: 'result',
      width: 90,
      render: (result: string, record) => (
        result === 'success'
          ? <Tag color="success">成功</Tag>
          : (
            <Tooltip title={record.error_message}>
              <Tag color="error">失败</Tag>
            </Tooltip>
          )
      ),
    },
    {
      title: '详情',
      dataIndex: 'detail',
      key: 'detail',
      render: (detail?: Record<string, unknown>) => {
        if (!detail || Object.keys(detail).length === 0) return <Text type="secondary">-</Text>;
        const json = JSON.stringify(detail);
        return (
          <Tooltip title={<pre style={{ maxWidth: 400, maxHeight: 200, overflow: 'auto', margin: 0, fontSize: 12 }}>{json}</pre>}>
            <Button type="link" size="small" icon={<EyeOutlined />}>查看详情</Button>
          </Tooltip>
        );
      },
    },
  ];

  // -----------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------

  return (
    <div>
      {/* 存储概览 */}
      <Card
        title={<span><DatabaseOutlined /> 存储概览</span>}
        size="small"
        extra={
          <Button
            size="small" icon={<ReloadOutlined />}
            onClick={loadStorageStats} loading={storageLoading}
          >
            刷新
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Spin spinning={storageLoading}>
          {storageStats ? (
            <>
              {(storageStats.db_file_size_bytes != null && storageStats.db_file_size_bytes > 500 * 1024 * 1024) && (
                <Alert
                  type="warning" showIcon icon={<WarningOutlined />}
                  message="数据库体积较大"
                  description={`当前数据库大小为 ${formatBytes(storageStats.db_file_size_bytes)}，已超过 500MB，建议进行数据清理以提升性能。`}
                  style={{ marginBottom: 16 }}
                />
              )}
              <Row gutter={[16, 16]}>
                <Col xs={12} sm={8} md={6}>
                  <Statistic
                    title="数据库大小"
                    value={formatBytes(storageStats.db_file_size_bytes)}
                    valueStyle={{ fontSize: 20 }}
                  />
                </Col>
                <Col xs={12} sm={8} md={6}>
                  <Statistic
                    title="知识库大小"
                    value={formatBytes(storageStats.knowledge_dir_size_bytes)}
                    valueStyle={{ fontSize: 20 }}
                  />
                </Col>
                <Col xs={24} sm={24} md={12}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    数据库路径：{storageStats.db_file_path || '-'}<br />
                    知识库路径：{storageStats.knowledge_dir_path || '-'}
                  </Text>
                </Col>
              </Row>
              <Divider style={{ margin: '16px 0' }} />
              <Text strong>数据表行数</Text>
              <Row gutter={[8, 8]} style={{ marginTop: 12 }}>
                {Object.entries(storageStats.table_counts).map(([table, count]) => (
                  <Col xs={12} sm={8} md={6} key={table}>
                    <Card size="small" styles={{ body: { padding: '8px 12px' } }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {TABLE_NAME_LABELS[table] || table}
                      </Text>
                      <br />
                      <Text strong style={{ fontSize: 18 }}>
                        {count != null ? count.toLocaleString() : '-'}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}> 行</Text>
                    </Card>
                  </Col>
                ))}
                {Object.keys(storageStats.table_counts).length === 0 && (
                  <Col span={24}><Empty description="暂无表数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /></Col>
                )}
              </Row>
            </>
          ) : (
            <Empty description="点击刷新加载存储统计" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Spin>
      </Card>

      {/* 数据导出 */}
      <Card
        title={<span><DownloadOutlined /> 数据导出</span>}
        size="small"
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>全量备份导出</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>导出所有数据为 JSON 备份文件，可用于迁移或恢复</Text>
            <br />
            <Button
              type="primary" icon={<ExportOutlined />}
              onClick={handleExportAll}
              style={{ marginTop: 8 }}
            >
              全量导出 JSON
            </Button>
          </div>
          <Divider style={{ margin: '8px 0' }} />
          <div>
            <Text strong>按模块导出 CSV</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>选择单个模块导出为 CSV 格式，方便在 Excel 中查看</Text>
            <br />
            <Space wrap style={{ marginTop: 8 }}>
              {CSV_EXPORT_MODULES.map(({ label, value }) => (
                <Button
                  key={value}
                  icon={<FileTextOutlined />}
                  onClick={() => handleExportCsv(value, label)}
                >
                  导出{label} CSV
                </Button>
              ))}
            </Space>
          </div>
        </Space>
      </Card>

      {/* 数据导入 */}
      <Card
        title={<span><UploadOutlined /> 数据导入</span>}
        size="small"
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            type="warning" showIcon
            message="导入注意事项"
            description="导入操作将根据所选策略处理数据。建议先执行全量导出备份，再进行导入操作。"
            style={{ marginBottom: 12 }}
          />
          <Row gutter={16} align="middle">
            <Col>
              <Upload
                accept=".json"
                beforeUpload={handleImportFileChange}
                onRemove={handleImportRemove}
                maxCount={1}
                fileList={importFile ? [{ uid: '-1', name: importFile.name, status: 'done' }] : []}
              >
                <Button icon={<UploadOutlined />}>选择 JSON 文件</Button>
              </Upload>
            </Col>
            <Col>
              <Text>导入策略：</Text>
              <Radio.Group
                value={importStrategy}
                onChange={(e) => setImportStrategy(e.target.value)}
                optionType="button"
                buttonStyle="solid"
                size="middle"
              >
                <Radio.Button value="skip">跳过重复</Radio.Button>
                <Radio.Button value="overwrite">覆盖已有</Radio.Button>
                <Radio.Button value="append">追加（允许重复）</Radio.Button>
              </Radio.Group>
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<ImportOutlined />}
                onClick={handleImport}
                loading={importLoading}
                disabled={!importFile}
              >
                开始导入
              </Button>
            </Col>
          </Row>
          {importResult && (
            <div style={{ marginTop: 12 }}>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>导入结果</Text>
              <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                {Object.entries(importResult).map(([module, stats]) => (
                  <Col xs={24} sm={12} md={8} key={module}>
                    <Card size="small" title={TABLE_NAME_LABELS[module] || module}>
                      <Space>
                        <Tag color="green">新增：{stats.inserted}</Tag>
                        <Tag color="blue">更新：{stats.updated}</Tag>
                        <Tag color="default">跳过：{stats.skipped}</Tag>
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </div>
          )}
        </Space>
      </Card>

      {/* 数据清理 */}
      <Card
        title={<span><DeleteOutlined /> 数据清理</span>}
        size="small"
        style={{ marginBottom: 16 }}
      >
        <Alert
          type="error" showIcon icon={<WarningOutlined />}
          message="危险操作"
          description="数据清理将永久删除指定时间之前的历史记录，请谨慎操作。建议先导出备份。"
          style={{ marginBottom: 12 }}
        />
        <Space direction="vertical" style={{ width: '100%' }}>
          <Row gutter={16} align="top">
            <Col>
              <Text>保留最近</Text>
              <InputNumber
                min={1} max={3650}
                value={cleanupDays}
                onChange={(v) => setCleanupDays(v ?? 90)}
                addonAfter="天"
                style={{ width: 150, margin: '0 8px' }}
              />
              <Text type="secondary">（将删除此日期之前的数据）</Text>
            </Col>
          </Row>
          <div style={{ marginTop: 8 }}>
            <Text>选择要清理的数据表：</Text>
            <br />
            <Checkbox.Group
              options={CLEANUP_TABLES}
              value={cleanupTables}
              onChange={(v) => setCleanupTables(v as string[])}
              style={{ marginTop: 8 }}
            />
          </div>
          <div style={{ marginTop: 12 }}>
            <Popconfirm
              title="确认执行数据清理？"
              description={`将删除 ${cleanupTables.length} 个表中 ${cleanupDays} 天前的历史数据，此操作不可恢复！`}
              okText="确认清理"
              cancelText="取消"
              okButtonProps={{ danger: true, loading: cleanupLoading }}
              onConfirm={handleCleanup}
              disabled={cleanupTables.length === 0}
            >
              <Button
                danger
                type="primary"
                icon={<DeleteOutlined />}
                loading={cleanupLoading}
                disabled={cleanupTables.length === 0}
              >
                执行清理
              </Button>
            </Popconfirm>
          </div>
          {cleanupResult && (
            <div style={{ marginTop: 12 }}>
              <Divider style={{ margin: '8px 0' }} />
              <Text strong>清理结果</Text>
              <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                {Object.entries(cleanupResult).map(([table, deleted]) => (
                  <Col xs={12} sm={8} md={6} key={table}>
                    <Card size="small">
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {TABLE_NAME_LABELS[table] || table}
                      </Text>
                      <br />
                      <Text strong style={{ fontSize: 18, color: 'var(--error)' }}>
                        {deleted.toLocaleString()}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}> 行已删除</Text>
                    </Card>
                  </Col>
                ))}
                {Object.keys(cleanupResult).length === 0 && (
                  <Col span={24}><Text type="secondary">没有符合条件的数据需要清理</Text></Col>
                )}
              </Row>
            </div>
          )}
        </Space>
      </Card>

      {/* 审计日志 */}
      <Card
        title={<span><HistoryOutlined /> 审计日志</span>}
        size="small"
        extra={
          <Button
            size="small" icon={<ReloadOutlined />}
            onClick={() => loadAuditLogs(auditPage)}
            loading={auditLoading}
          >
            刷新
          </Button>
        }
      >
        <Table<AuditLog>
          columns={auditColumns}
          dataSource={auditLogs}
          rowKey="id"
          loading={auditLoading}
          size="small"
          pagination={{
            current: auditPage,
            pageSize: auditPageSize,
            total: auditTotal,
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`,
          }}
          onChange={handleAuditTableChange}
          locale={{ emptyText: <Empty description="暂无审计日志" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          scroll={{ x: 600 }}
        />
      </Card>
    </div>
  );
};

export default DataManagementTab;
