import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Row, Col, Statistic, Typography, Spin, Empty, Table, Tag, Space, Button, Alert, Tabs, Progress, List, message } from 'antd';
import {
  LineChartOutlined, CheckCircleOutlined, CloseCircleOutlined,
  DollarOutlined, RiseOutlined, BulbOutlined, ReloadOutlined,
  WarningOutlined, SafetyOutlined, ThunderboltOutlined,
  KeyOutlined, FileTextOutlined, ToolOutlined, SearchOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { reportsApi } from '@/api/reports';
import { useAppStore } from '@/stores';
import { getEChartsThemeColors } from '@/utils/echartsTheme';
import { KpiCard } from '@/components';
import type { KPIData, CostReport, MentionReport } from '@/types';

const { Text } = Typography;

/**
 * 后端 negative / suggestions 接口返回的元素结构较松散（可能是字符串或对象），
 * 这里给出明确字段定义，避免在渲染处使用 any。
 */
interface NegativeItem {
  query?: string;
  content?: string;
  keyword?: string;
  diagnosis?: string;
  reason?: string;
}

interface SuggestionItem {
  message?: string;
  suggestion?: string;
  text?: string;
}

/** 品牌提及趋势的单条数据，兼容多种后端字段命名 */
interface MentionTrendItem {
  date?: string;
  day?: string;
  time?: string;
  created_at?: string;
  rate?: number;
  mention_rate?: number;
  mentioned?: number;
  total?: number;
  count?: number;
  mentions?: number;
}

type CostEntry = { cost_usd: number; cost_cny: number; calls: number; tokens: number };
type ModelMentionEntry = { total: number; mentioned: number; rate: number };

/**
 * Highlight text matching 【⚠️待验证来源：...】 pattern with an orange warning tag
 */
function highlightPlaceholders(text: string): React.ReactNode {
  if (!text) return text;
  const regex = /【⚠️待验证来源：([^】]*)】/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let keyIdx = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <Tag key={`ph-${keyIdx++}`} color="orange" icon={<WarningOutlined />} style={{ margin: '0 2px', fontSize: 12 }}>
        ⚠️待验证来源：{match[1]}
      </Tag>
    );
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length > 0 ? <>{parts}</> : text;
}

/**
 * Highlight placeholders in any string value within an object (recursively, for display)
 */
function highlightText(text: string | undefined | null): React.ReactNode {
  if (!text) return text;
  return highlightPlaceholders(text);
}

const ReportsPage: React.FC = () => {
  const { config, darkMode } = useAppStore();
  const [kpi, setKpi] = useState<KPIData | null>(null);
  const [costs, setCosts] = useState<CostReport | null>(null);
  const [mentions, setMentions] = useState<MentionReport | null>(null);
  const [negative, setNegative] = useState<NegativeItem[] | string[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestionItem[] | string[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [kpiData, costsData, mentionsData, negData, sugData] = await Promise.all([
        reportsApi.kpi(config?.brand),
        reportsApi.costs(config?.brand),
        reportsApi.mentions(config?.brand),
        reportsApi.negative(config?.brand).catch(() => []),
        reportsApi.suggestions(config?.brand).catch(() => []),
      ]);
      setKpi(kpiData);
      setCosts(costsData);
      setMentions(mentionsData);
      setNegative((negData || []) as NegativeItem[] | string[]);
      setSuggestions((sugData || []) as SuggestionItem[] | string[]);
    } catch (err) {
      console.error('[ReportsPage] 加载报表数据失败:', err);
      message.error('加载报表数据失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [config?.brand]);

  useEffect(() => { loadData(); }, [loadData]);

  // ─── ROI Calculation ───────────────────────────────────────────────
  // ROI 估算基于用户在设置页配置的 roi_value_per_mention 和 platform_value_coefficients。
  // 若用户未配置 ROI 参数，则不展示估算卡片，避免展示虚构数据。
  const roiEstimate = useMemo(() => {
    if (!mentions || !config) return null;
    const roiValue = config.roi_value_per_mention || 0;
    // 未配置单次提及价值时，不进行估算
    if (roiValue <= 0) return null;

    const coefficients = config.platform_value_coefficients || {};
    const totalMentioned = mentions.total_mentioned || 0;

    // 基础估算（不含平台系数）
    const baseValue = totalMentioned * roiValue;

    // 计算平均系数（若配置了平台系数）
    const coeffValues = Object.values(coefficients);
    const avgCoeff = coeffValues.length > 0
      ? coeffValues.reduce((a, b) => a + b, 0) / coeffValues.length
      : 1;

    const estimatedValue = baseValue * avgCoeff;

    // 按平台拆分估算（基于配置的平台系数）
    const platformBreakdown = Object.entries(coefficients).map(([platform, coeff]) => {
      const estMentions = coeffValues.length > 0 ? Math.round(totalMentioned / coeffValues.length) : 0;
      return {
        platform,
        coefficient: coeff,
        estimated_mentions: estMentions,
        estimated_value: Math.round(estMentions * roiValue * coeff * 100) / 100,
      };
    });

    return {
      total_mentioned: totalMentioned,
      roi_value_per_mention: roiValue,
      avg_coefficient: Math.round(avgCoeff * 100) / 100,
      estimated_value: Math.round(estimatedValue * 100) / 100,
      platform_breakdown: platformBreakdown,
      is_configured: roiValue > 0,
    };
  }, [mentions, config]);

  // ─── Chart Options ─────────────────────────────────────────────────
  const dailyCostOption = useMemo(() => {
    if (!costs?.daily_costs?.length) return null;
    const c = getEChartsThemeColors(darkMode);
    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: c.tooltipBg,
        borderColor: c.tooltipBorderColor,
        textStyle: { color: c.tooltipTextColor },
      },
      xAxis: {
        type: 'category',
        data: costs.daily_costs.map(d => d.date),
        axisLabel: { fontSize: 11, color: c.axisLabelColor },
        axisLine: { lineStyle: { color: c.axisLineColor } },
      },
      yAxis: [
        {
          type: 'value', name: '费用(¥)', position: 'left',
          nameTextStyle: { color: c.axisLabelColor },
          axisLabel: { color: c.axisLabelColor },
          axisLine: { lineStyle: { color: c.axisLineColor } },
          splitLine: { lineStyle: { color: c.splitLineColor } },
        },
        {
          type: 'value', name: '调用次数', position: 'right',
          nameTextStyle: { color: c.axisLabelColor },
          axisLabel: { color: c.axisLabelColor },
          axisLine: { lineStyle: { color: c.axisLineColor } },
          splitLine: { lineStyle: { color: c.splitLineColor } },
        },
      ],
      legend: { data: ['费用', '调用次数'], textStyle: { color: c.legendTextColor } },
      series: [
        {
          name: '费用', type: 'line', smooth: true,
          data: costs.daily_costs.map(d => Number(d.cost_cny.toFixed(4))),
          itemStyle: { color: '#3b82f6' },
          areaStyle: { color: 'rgba(59,130,246,0.1)' },
        },
        {
          name: '调用次数', type: 'bar', yAxisIndex: 1,
          data: costs.daily_costs.map(d => d.calls),
          itemStyle: { color: '#93c5fd' },
        },
      ],
    };
  }, [costs, darkMode]);

  const providerCostOption = useMemo(() => {
    if (!costs?.cost_by_provider) return null;
    const c = getEChartsThemeColors(darkMode);
    const entries = Object.entries(costs.cost_by_provider);
    return {
      tooltip: {
        trigger: 'item', formatter: '{b}: ¥{c} ({d}%)',
        backgroundColor: c.tooltipBg,
        borderColor: c.tooltipBorderColor,
        textStyle: { color: c.tooltipTextColor },
      },
      series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: entries.map(([name, v]) => ({ name, value: Number((v as CostEntry).cost_cny.toFixed(4)) })),
        label: { fontSize: 11, color: c.axisLabelColor },
      }],
    };
  }, [costs, darkMode]);

  const operationCostOption = useMemo(() => {
    if (!costs?.cost_by_operation) return null;
    const c = getEChartsThemeColors(darkMode);
    const entries = Object.entries(costs.cost_by_operation);
    return {
      tooltip: {
        backgroundColor: c.tooltipBg,
        borderColor: c.tooltipBorderColor,
        textStyle: { color: c.tooltipTextColor },
      },
      xAxis: {
        type: 'category', data: entries.map(([k]) => k),
        axisLabel: { fontSize: 10, rotate: 20, color: c.axisLabelColor },
        axisLine: { lineStyle: { color: c.axisLineColor } },
      },
      yAxis: {
        type: 'value', name: '费用(¥)',
        nameTextStyle: { color: c.axisLabelColor },
        axisLabel: { color: c.axisLabelColor },
        axisLine: { lineStyle: { color: c.axisLineColor } },
        splitLine: { lineStyle: { color: c.splitLineColor } },
      },
      series: [{ type: 'bar', data: entries.map(([, v]) => Number((v as CostEntry).cost_cny.toFixed(4))), itemStyle: { color: '#10b981' } }],
      grid: { bottom: 60 },
    };
  }, [costs, darkMode]);

  const mentionRateOption = useMemo(() => {
    if (!mentions?.mention_rate_by_model) return null;
    const c = getEChartsThemeColors(darkMode);
    const entries = Object.entries(mentions.mention_rate_by_model);
    return {
      tooltip: {
        backgroundColor: c.tooltipBg,
        borderColor: c.tooltipBorderColor,
        textStyle: { color: c.tooltipTextColor },
      },
      xAxis: {
        type: 'category', data: entries.map(([k]) => k),
        axisLabel: { color: c.axisLabelColor },
        axisLine: { lineStyle: { color: c.axisLineColor } },
      },
      yAxis: {
        type: 'value', max: 100, name: '提及率(%)',
        nameTextStyle: { color: c.axisLabelColor },
        axisLabel: { color: c.axisLabelColor },
        axisLine: { lineStyle: { color: c.axisLineColor } },
        splitLine: { lineStyle: { color: c.splitLineColor } },
      },
      series: [{
        type: 'bar',
        data: entries.map(([, v]) => Math.round((v as ModelMentionEntry).rate * 100)),
        itemStyle: { color: '#8b5cf6' },
        label: { show: true, position: 'top', formatter: '{c}%', fontSize: 11, color: c.axisLabelColor },
      }],
    };
  }, [mentions, darkMode]);

  // Mention trend over time
  const mentionTrendOption = useMemo(() => {
    if (!mentions?.mention_trend || !Array.isArray(mentions.mention_trend) || mentions.mention_trend.length === 0) {
      return null;
    }
    const trend = mentions.mention_trend as MentionTrendItem[];
    // Try to detect the data format
    // Format 1: [{date, count, rate}]
    // Format 2: [{date, mentioned, total}]
    const dates: string[] = [];
    const rates: number[] = [];
    const counts: number[] = [];

    trend.forEach((item) => {
      const date = item.date || item.day || item.time || item.created_at || '';
      dates.push(String(date).slice(0, 10));
      const rate = item.rate !== undefined ? Math.round(Number(item.rate) * 100)
        : item.mention_rate !== undefined ? Math.round(Number(item.mention_rate) * 100)
        : (item.mentioned !== undefined && item.total) ? Math.round((item.mentioned / item.total) * 100)
        : null;
      const count = item.mentioned !== undefined ? item.mentioned
        : item.count !== undefined ? item.count
        : item.mentions !== undefined ? item.mentions
        : null;
      rates.push(rate ?? 0);
      counts.push(count ?? 0);
    });

    const c = getEChartsThemeColors(darkMode);
    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: c.tooltipBg,
        borderColor: c.tooltipBorderColor,
        textStyle: { color: c.tooltipTextColor },
      },
      xAxis: {
        type: 'category', data: dates,
        axisLabel: { color: c.axisLabelColor },
        axisLine: { lineStyle: { color: c.axisLineColor } },
      },
      yAxis: [
        {
          type: 'value', name: '提及率(%)', max: 100, position: 'left',
          nameTextStyle: { color: c.axisLabelColor },
          axisLabel: { color: c.axisLabelColor },
          axisLine: { lineStyle: { color: c.axisLineColor } },
          splitLine: { lineStyle: { color: c.splitLineColor } },
        },
        {
          type: 'value', name: '提及次数', position: 'right',
          nameTextStyle: { color: c.axisLabelColor },
          axisLabel: { color: c.axisLabelColor },
          axisLine: { lineStyle: { color: c.axisLineColor } },
          splitLine: { lineStyle: { color: c.splitLineColor } },
        },
      ],
      legend: { data: ['提及率', '提及次数'], textStyle: { color: c.legendTextColor } },
      series: [
        {
          name: '提及率', type: 'line', smooth: true,
          data: rates,
          itemStyle: { color: '#8b5cf6' },
          areaStyle: { color: 'rgba(139,92,246,0.1)' },
        },
        {
          name: '提及次数', type: 'bar', yAxisIndex: 1,
          data: counts,
          itemStyle: { color: '#c4b5fd' },
        },
      ],
    };
  }, [mentions, darkMode]);

  // ─── Table Columns ─────────────────────────────────────────────────
  const opColumns = [
    { title: '操作类型', dataIndex: '0', key: 'op', render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: '调用次数', dataIndex: ['1', 'calls'], key: 'calls', render: (v: number) => v ?? 0 },
    { title: 'Token数', dataIndex: ['1', 'tokens'], key: 'tokens', render: (v: number) => v?.toLocaleString() ?? 0 },
    { title: '费用(¥)', dataIndex: ['1', 'cost_cny'], key: 'cny', render: (v: number) => v?.toFixed(4) ?? '0.0000' },
    { title: '费用($)', dataIndex: ['1', 'cost_usd'], key: 'usd', render: (v: number) => v?.toFixed(6) ?? '0.000000' },
  ];

  const providerColumns = [
    { title: '提供商', dataIndex: '0', key: 'provider' },
    { title: '调用次数', dataIndex: ['1', 'calls'], key: 'calls' },
    { title: 'Token数', dataIndex: ['1', 'tokens'], key: 'tokens', render: (v: number) => v?.toLocaleString() ?? 0 },
    { title: '费用(¥)', dataIndex: ['1', 'cost_cny'], key: 'cny', render: (v: number) => v?.toFixed(4) ?? '0.0000' },
  ];

  const roiColumns = [
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag color="purple">{v}</Tag> },
    { title: '价值系数', dataIndex: 'coefficient', key: 'coefficient', render: (v: number) => v.toFixed(2) },
    { title: '估算提及数', dataIndex: 'estimated_mentions', key: 'est' },
    {
      title: '估算价值(¥)', dataIndex: 'estimated_value', key: 'value',
      render: (v: number) => <Text strong style={{ color: 'var(--success)' }}>¥{v.toFixed(2)}</Text>,
    },
  ];

  // ─── Tab Items ─────────────────────────────────────────────────────
  const tabItems = [
    // ── 概览 Tab ──
    {
      key: 'overview',
      label: '概览',
      children: (
        <div>
          {/* KPI Cards */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8} lg={4}>
              <KpiCard label="关键词总数" value={kpi?.total_keywords || 0} icon={<KeyOutlined />} color="var(--brand-500)" iconBg="var(--bg-brand)" />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <KpiCard label="文章总数" value={kpi?.total_articles || 0} icon={<FileTextOutlined />} color="var(--brand-600)" iconBg="var(--bg-brand)" />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <KpiCard label="优化次数" value={kpi?.total_optimizations || 0} icon={<ToolOutlined />} color="var(--warning)" iconBg="var(--bg-warning)" />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <KpiCard label="验证次数" value={kpi?.total_verifications || 0} icon={<SearchOutlined />} color="var(--accent)" iconBg="var(--bg-accent)" />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <KpiCard label="总费用(¥)" value={kpi?.total_cost_cny?.toFixed(2) || '0.00'} icon={<DollarOutlined />} color="var(--error)" iconBg="var(--bg-error)" prefix="¥" precision={2} />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <KpiCard
                label="品牌提及率"
                value={Math.round((kpi?.mention_rate || 0) * 100)}
                suffix="%"
                icon={<RiseOutlined />}
                color={(kpi?.mention_rate || 0) >= 0.7 ? 'var(--success)' : 'var(--error)'}
                iconBg={(kpi?.mention_rate || 0) >= 0.7 ? 'var(--bg-success)' : 'var(--bg-error)'}
              />
            </Col>
          </Row>

          {/* ROI Estimate Card — 仅在用户配置了 ROI 参数时展示 */}
          {roiEstimate && roiEstimate.is_configured && (
            <Card
              title={<Space><ThunderboltOutlined style={{ color: 'var(--warning)' }} /><Text strong>ROI 估算</Text></Space>}
              size="small"
              style={{ marginBottom: 16 }}
              extra={<Text type="secondary" style={{ fontSize: 12 }}>基于设置页配置参数估算</Text>}
            >
              <Alert
                type="info" showIcon style={{ marginBottom: 12 }}
                message="本估算基于您在设置页配置的单次提及价值和平台系数，提及次数按平台均分计算，仅供参考。实际 ROI 请以真实业务数据为准。"
              />
              <Row gutter={16}>
                <Col xs={24} sm={8}>
                  <Card size="small" style={{ background: 'var(--bg-success)', border: '1px solid var(--bg-success-border)', textAlign: 'center' }}>
                    <Statistic
                      title="估算品牌价值"
                      value={roiEstimate.estimated_value}
                      prefix="¥"
                      precision={2}
                      valueStyle={{ color: 'var(--success)', fontSize: 28 }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Statistic
                      title="总提及次数"
                      value={roiEstimate.total_mentioned}
                      prefix={<CheckCircleOutlined style={{ color: 'var(--success)' }} />}
                    />
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
                      单次提及价值 ¥{roiEstimate.roi_value_per_mention.toFixed(2)} × 平均系数 {roiEstimate.avg_coefficient}
                    </div>
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Statistic
                      title="投入产出比"
                      value={kpi?.total_cost_cny && kpi.total_cost_cny > 0
                        ? (roiEstimate.estimated_value / kpi.total_cost_cny).toFixed(1)
                        : '-'}
                      suffix="x"
                      valueStyle={{ color: 'var(--brand-500)' }}
                    />
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
                      总投入 ¥{kpi?.total_cost_cny?.toFixed(2) || '0.00'}
                    </div>
                  </Card>
                </Col>
              </Row>
              {roiEstimate.platform_breakdown.length > 0 && (
                <Table
                  dataSource={roiEstimate.platform_breakdown}
                  columns={roiColumns}
                  size="small"
                  pagination={false}
                  rowKey="platform"
                  style={{ marginTop: 12 }}
                />
              )}
            </Card>
          )}

          {/* Mention Rate Overview */}
          {mentions && (
            <Row gutter={16}>
              <Col xs={24} lg={12}>
                <Card title="品牌提及概览" size="small">
                  <Row gutter={16} style={{ marginBottom: 12 }}>
                    <Col span={8}><Statistic title="总验证次数" value={mentions.total_verifications} /></Col>
                    <Col span={8}><Statistic title="提及次数" value={mentions.total_mentioned} valueStyle={{ color: 'var(--success)' }} /></Col>
                    <Col span={8}>
                      <Statistic
                        title="整体提及率"
                        value={Math.round(mentions.mention_rate * 100)}
                        suffix="%"
                        valueStyle={{ color: mentions.mention_rate >= 0.7 ? 'var(--success)' : 'var(--warning)' }}
                      />
                    </Col>
                  </Row>
                  {mentionRateOption && <ReactECharts option={mentionRateOption} style={{ height: 240 }} />}
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="质量健康度" size="small">
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text>关键词覆盖</Text>
                      <Text strong>{Math.min(100, Math.round(((kpi?.total_keywords || 0) / 50) * 100))}%</Text>
                    </div>
                    <Progress percent={Math.min(100, Math.round(((kpi?.total_keywords || 0) / 50) * 100))} strokeColor="var(--brand-500)" size="small" />
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text>内容产出</Text>
                      <Text strong>{Math.min(100, Math.round(((kpi?.total_articles || 0) / 30) * 100))}%</Text>
                    </div>
                    <Progress percent={Math.min(100, Math.round(((kpi?.total_articles || 0) / 30) * 100))} strokeColor="var(--success)" size="small" />
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text>品牌提及率</Text>
                      <Text strong>{Math.round((kpi?.mention_rate || 0) * 100)}%</Text>
                    </div>
                    <Progress
                      percent={Math.round((kpi?.mention_rate || 0) * 100)}
                      strokeColor={(kpi?.mention_rate || 0) >= 0.7 ? 'var(--success)' : 'var(--warning)'}
                      size="small"
                    />
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text>内容优化度</Text>
                      <Text strong>{Math.min(100, Math.round(((kpi?.total_optimizations || 0) / Math.max(kpi?.total_articles || 1, 1)) * 100))}%</Text>
                    </div>
                    <Progress
                      percent={Math.min(100, Math.round(((kpi?.total_optimizations || 0) / Math.max(kpi?.total_articles || 1, 1)) * 100))}
                      strokeColor="var(--brand-600)"
                      size="small"
                    />
                  </div>
                </Card>
              </Col>
            </Row>
          )}

          {/* Negative cases preview */}
          {negative.length > 0 && (
            <Card title="未被提及查询（最近）" size="small" style={{ marginTop: 16 }} extra={<Tag color="red">{negative.length} 条</Tag>}>
              <List
                size="small"
                dataSource={negative.slice(0, 5)}
                renderItem={(item: NegativeItem | string) => {
                  const text = typeof item === 'string' ? item : (item.query || item.content || JSON.stringify(item));
                  return (
                  <List.Item>
                    <Space>
                      <CloseCircleOutlined style={{ color: 'var(--error)' }} />
                      <Text>{highlightText(text)}</Text>
                    </Space>
                  </List.Item>
                  );
                }}
              />
            </Card>
          )}
        </div>
      ),
    },

    // ── 趋势 Tab ──
    {
      key: 'trend',
      label: <span><LineChartOutlined /> 趋势</span>,
      children: (
        <div>
          <Row gutter={16}>
            <Col span={24}>
              <Card title="品牌提及趋势" size="small" extra={<Text type="secondary" style={{ fontSize: 12 }}>按时间维度展示品牌提及率变化</Text>}>
                {mentionTrendOption ? (
                  <ReactECharts option={mentionTrendOption} style={{ height: 340 }} />
                ) : (
                  <Empty description="暂无趋势数据，多次执行验证后将展示趋势图" style={{ padding: '40px 0' }}>
                    <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => window.location.hash = '#/verify'}>
                      前往验证
                    </Button>
                  </Empty>
                )}
              </Card>
            </Col>
          </Row>
          {costs?.daily_costs?.length && (
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={24}>
                <Card title="调用量趋势（每日）" size="small">
                  {dailyCostOption && <ReactECharts option={dailyCostOption} style={{ height: 300 }} />}
                </Card>
              </Col>
            </Row>
          )}
        </div>
      ),
    },

    // ── 成本 Tab ──
    {
      key: 'cost',
      label: <span><DollarOutlined /> 成本</span>,
      children: (
        <div>
          {costs && (
            <>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}><KpiCard label="总费用($)" value={costs.total_cost_usd.toFixed(4)} prefix="$" precision={4} /></Col>
                <Col span={6}><KpiCard label="总费用(¥)" value={costs.total_cost_cny.toFixed(2)} prefix="¥" precision={2} /></Col>
                <Col span={6}><KpiCard label="总Token数" value={costs.total_tokens.toLocaleString()} /></Col>
                <Col span={6}><KpiCard label="总调用次数" value={costs.total_calls} /></Col>
              </Row>
              <Row gutter={16}>
                <Col span={16}>
                  <Card title="每日费用趋势" size="small">
                    {dailyCostOption ? <ReactECharts option={dailyCostOption} style={{ height: 280 }} /> : <Empty description="暂无数据，使用系统功能后将自动生成" />}
                  </Card>
                </Col>
                <Col span={8}>
                  <Card title="提供商费用占比" size="small">
                    {providerCostOption ? <ReactECharts option={providerCostOption} style={{ height: 280 }} /> : <Empty description="暂无数据，使用系统功能后将自动生成" />}
                  </Card>
                </Col>
              </Row>
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col span={12}>
                  <Card title="按操作类型费用" size="small">
                    {operationCostOption ? <ReactECharts option={operationCostOption} style={{ height: 260 }} /> : <Empty description="暂无数据，使用系统功能后将自动生成" />}
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="提供商费用明细" size="small">
                    <Table
                      dataSource={Object.entries(costs.cost_by_provider || {})}
                      columns={providerColumns}
                      size="small"
                      pagination={false}
                      rowKey="0"
                    />
                  </Card>
                </Col>
              </Row>
              <Card title="操作类型费用明细" size="small" style={{ marginTop: 16 }}>
                <Table
                  dataSource={Object.entries(costs.cost_by_operation || {})}
                  columns={opColumns}
                  size="small"
                  pagination={false}
                  rowKey="0"
                />
              </Card>
            </>
          )}
          {!costs && (
            <Empty description="暂无成本数据，使用系统功能后将自动生成" style={{ padding: '40px 0' }}>
              <Button type="primary" icon={<KeyOutlined />} onClick={() => window.location.hash = '#/keywords'}>
                开始生成关键词
              </Button>
            </Empty>
          )}
        </div>
      ),
    },

    // ── 质量 Tab ──
    {
      key: 'quality',
      label: <span><SafetyOutlined /> 质量</span>,
      children: (
        <div>
          {/* Quality metrics */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="品牌提及率"
                  value={Math.round((mentions?.mention_rate || 0) * 100)}
                  suffix="%"
                  prefix={<RiseOutlined />}
                  valueStyle={{ color: (mentions?.mention_rate || 0) >= 0.7 ? 'var(--success)' : 'var(--error)' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="优化覆盖率"
                  value={kpi?.total_articles ? Math.round(((kpi.total_optimizations || 0) / kpi.total_articles) * 100) : 0}
                  suffix="%"
                  valueStyle={{ color: 'var(--brand-600)' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="未提及查询"
                  value={negative.length}
                  prefix={<CloseCircleOutlined />}
                  valueStyle={{ color: negative.length > 0 ? 'var(--error)' : 'var(--success)' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="优化建议数"
                  value={suggestions.length}
                  prefix={<BulbOutlined />}
                  valueStyle={{ color: 'var(--warning)' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Optimization suggestions with placeholder highlighting */}
          <Card
            title={<Space><BulbOutlined /><Text strong>优化建议</Text></Space>}
            size="small"
            style={{ marginBottom: 16 }}
          >
            {suggestions.length > 0 ? (
              <List
                dataSource={suggestions as Array<SuggestionItem | string>}
                renderItem={(item: SuggestionItem | string, _idx) => {
                  const message = typeof item === 'string' ? item : item.message || item.suggestion || item.text || JSON.stringify(item);
                  return (
                    <List.Item>
                      <Alert
                        type="info"
                        showIcon
                        message={highlightText(message)}
                        style={{ width: '100%' }}
                      />
                    </List.Item>
                  );
                }}
              />
            ) : (
              <Empty description="暂无建议，继续优化内容后将生成改进建议" style={{ padding: '20px 0' }}>
                <Button type="primary" icon={<ToolOutlined />} onClick={() => window.location.hash = '#/optimize'}>
                  前往优化
                </Button>
              </Empty>
            )}
          </Card>

          {/* Negative cases */}
          {negative.length > 0 && (
            <Card
              title={<Space><CloseCircleOutlined style={{ color: 'var(--error)' }} /><Text strong>未被提及的查询（待改进）</Text></Space>}
              size="small"
            >
              <List
                dataSource={negative}
                renderItem={(item: NegativeItem | string) => {
                  const query = typeof item === 'string' ? item : (item.query || item.content || item.keyword || JSON.stringify(item));
                  const diagnosis = typeof item === 'string' ? '' : (item.diagnosis || item.reason || '');
                  return (
                    <List.Item>
                      <div style={{ width: '100%' }}>
                        <Space>
                          <CloseCircleOutlined style={{ color: 'var(--error)' }} />
                          <Text>{highlightText(query)}</Text>
                        </Space>
                        {diagnosis && (
                          <div style={{ marginTop: 4, paddingLeft: 22, fontSize: 12, color: 'var(--text-tertiary)' }}>
                            {highlightText(diagnosis)}
                          </div>
                        )}
                      </div>
                    </List.Item>
                  );
                }}
              />
            </Card>
          )}

          {/* Model mention rates as quality indicators */}
          {mentions?.mention_rate_by_model && (
            <Card title="各模型验证质量" size="small" style={{ marginTop: 16 }}>
              {Object.entries(mentions.mention_rate_by_model).map(([model, data]: [string, ModelMentionEntry]) => {
                const rate = Math.round((data?.rate || 0) * 100);
                return (
                  <div key={model} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Space>
                        <Tag color={rate >= 70 ? 'green' : rate >= 40 ? 'orange' : 'red'}>{model}</Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>{data?.mentioned || 0}/{data?.total || 0} 次提及</Text>
                      </Space>
                      <Text strong style={{ color: rate >= 70 ? 'var(--success)' : rate >= 40 ? 'var(--warning)' : 'var(--error)' }}>{rate}%</Text>
                    </div>
                    <Progress
                      percent={rate}
                      strokeColor={rate >= 70 ? 'var(--success)' : rate >= 40 ? 'var(--warning)' : 'var(--error)'}
                      size="small"
                    />
                  </div>
                );
              })}
            </Card>
          )}
        </div>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="page-container text-center p-20">
        <Spin size="large" tip="加载报表数据..." />
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">数据报表</h2>
        <p className="page-desc">内容产出、品牌提及率、费用统计与 ROI 分析</p>
        <Button size="small" icon={<ReloadOutlined />} onClick={loadData} className="mt-2">刷新数据</Button>
      </div>

      <Tabs defaultActiveKey="overview" items={tabItems} />
    </div>
  );
};

export default ReportsPage;
