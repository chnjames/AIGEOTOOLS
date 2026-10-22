import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, Tag, Button, Space, Typography, Row, Col, Empty, Select } from 'antd';
import { ReloadOutlined, DollarOutlined, ApiOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { reportsApi, ApiCallRecord } from '@/api/reports';
import { useAppStore } from '@/stores';
import { getEChartsThemeColors } from '@/utils/echartsTheme';
import { KpiCard } from '@/components';
import ReactECharts from 'echarts-for-react';
import { formatDateTime } from '@/utils/dateFormat';

const { Text } = Typography;

const OPERATION_LABELS: Record<string, string> = {
  keyword_generate: '关键词生成',
  keyword_mine: '竞品挖掘',
  article_generate: '文章生成',
  article_batch: '批量生成',
  optimize_eeat: 'EEAT优化',
  optimize_fact: '事实密度优化',
  score: '内容评分',
  verify: '品牌验证',
  config_optimize: '配置优化',
};

const HistoryPage: React.FC = () => {
  const { config, darkMode } = useAppStore();
  const [records, setRecords] = useState<ApiCallRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filterOp, setFilterOp] = useState<string | undefined>();
  const [summary, setSummary] = useState({ total_calls: 0, total_tokens: 0, total_cost_cny: 0, total_cost_usd: 0 });

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      // 筛选和汇总都由后端处理，前端直接传递参数
      const data = await reportsApi.apiCalls({
        brand: config?.brand,
        operation_type: filterOp,
        page,
        page_size: 20,
      });
      setRecords(data?.items ?? []);
      setTotal(data?.total ?? 0);
      // 使用后端返回的全量汇总（非仅当前页），防御性处理 undefined
      setSummary(data?.summary ?? { total_calls: 0, total_tokens: 0, total_cost_cny: 0, total_cost_usd: 0 });
    } catch (err) {
      console.error('[HistoryPage] 加载记录失败:', err);
    } finally {
      setLoading(false);
    }
  }, [config?.brand, page, filterOp]);

  useEffect(() => { loadRecords(); }, [loadRecords]);

  const columns: ColumnsType<ApiCallRecord> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '操作类型', dataIndex: 'operation_type', width: 120,
      render: (op: string) => <Tag color="blue">{OPERATION_LABELS[op] || op}</Tag>,
    },
    { title: '提供商', dataIndex: 'provider', width: 100, render: (p) => p ? <Tag>{p}</Tag> : '-' },
    { title: '模型', dataIndex: 'model', width: 150, ellipsis: true },
    {
      title: 'Token消耗', width: 140,
      render: (_, r) => (
        <span style={{ fontSize: 'var(--font-size-xs)' }}>
          <Text type="secondary">入:</Text>{r.input_tokens || 0}
          {' / '}
          <Text type="secondary">出:</Text>{r.output_tokens || 0}
        </span>
      ),
    },
    {
      title: '费用', width: 100,
      render: (_, r) => (
        <span style={{ fontSize: 'var(--font-size-xs)' }}>
          ¥{(r.cost_cny || 0).toFixed(4)}
        </span>
      ),
    },
    { title: '关键词', dataIndex: 'keyword', width: 150, ellipsis: true, render: (k) => k || '-' },
    { title: '平台', dataIndex: 'platform', width: 80, render: (p) => p ? <Tag color="green">{p}</Tag> : '-' },
    { title: '时间', dataIndex: 'created_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
  ];

  const providerChartOption = React.useMemo(() => {
    const byProvider: Record<string, number> = {};
    records.forEach(r => {
      const p = r.provider || 'unknown';
      byProvider[p] = (byProvider[p] || 0) + (r.cost_cny || 0);
    });
    return {
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: Object.entries(byProvider).map(([name, value]) => ({ name, value: Number(value.toFixed(4)) })),
        label: { fontSize: 11 },
      }],
    };
  }, [records]);

  const opChartOption = React.useMemo(() => {
    const byOp: Record<string, number> = {};
    records.forEach(r => {
      const op = OPERATION_LABELS[r.operation_type] || r.operation_type;
      byOp[op] = (byOp[op] || 0) + 1;
    });
    const entries = Object.entries(byOp);
    const themeColors = getEChartsThemeColors(darkMode);
    return {
      tooltip: {},
      xAxis: {
        type: 'category',
        data: entries.map(([k]) => k),
        axisLabel: { fontSize: 10, rotate: 30, color: themeColors.axisLabelColor },
        axisLine: { lineStyle: { color: themeColors.axisLineColor } },
      },
      yAxis: {
        type: 'value',
        name: '调用次数',
        axisLabel: { color: themeColors.axisLabelColor },
        axisLine: { lineStyle: { color: themeColors.axisLineColor } },
        splitLine: { lineStyle: { color: themeColors.splitLineColor } },
        nameTextStyle: { color: themeColors.textColor },
      },
      series: [{ type: 'bar', data: entries.map(([, v]) => v), itemStyle: { color: '#3b82f6' } }],
      grid: { bottom: 60 },
    };
  }, [records, darkMode]);

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">调用历史</h2>
        <p className="page-desc">LLM API 调用记录、Token 消耗和费用统计</p>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <KpiCard
            label="总调用次数"
            value={summary?.total_calls ?? 0}
            icon={<ApiOutlined />}
            color="var(--brand-500)"
            iconBg="var(--bg-brand)"
          />
        </Col>
        <Col span={6}>
          <KpiCard
            label="Token 消耗"
            value={summary?.total_tokens ?? 0}
            icon={<ThunderboltOutlined />}
            color="var(--warning)"
            iconBg="var(--bg-warning)"
          />
        </Col>
        <Col span={6}>
          <KpiCard
            label="费用 (¥)"
            value={summary?.total_cost_cny ?? 0}
            precision={2}
            icon={<DollarOutlined />}
            color="var(--success)"
            iconBg="var(--bg-success)"
          />
        </Col>
        <Col span={6}>
          <KpiCard
            label="费用 ($)"
            value={summary?.total_cost_usd ?? 0}
            precision={4}
            prefix="$"
            color="var(--accent-500)"
            iconBg="var(--bg-hover)"
          />
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="按提供商费用分布" size="small">
            {records.length > 0 ? (
              <ReactECharts option={providerChartOption} style={{ height: 220 }} />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="按操作类型调用次数" size="small">
            {records.length > 0 ? (
              <ReactECharts option={opChartOption} style={{ height: 220 }} />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>

      <Card
        title="API 调用明细"
        extra={
          <Space>
            <Select
              placeholder="筛选操作类型"
              allowClear
              style={{ width: 150 }}
              value={filterOp}
              onChange={setFilterOp}
              options={Object.entries(OPERATION_LABELS).map(([v, l]) => ({ label: l, value: v }))}
            />
            <Button size="small" icon={<ReloadOutlined />} onClick={loadRecords}>刷新</Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
          locale={{ emptyText: (
            <Empty description="暂无调用记录，使用系统功能后将自动记录">
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => window.location.hash = '#/workbench'}>
                前往工作台
              </Button>
            </Empty>
          ) }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  );
};

export default HistoryPage;
