import React, { useState, useEffect, useMemo } from 'react';
import { Card, Row, Col, Table, Input, Select, Button, Tag, Space, Spin, Empty, message } from 'antd';
import { ReloadOutlined, ArrowUpOutlined, ArrowDownOutlined, SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { analyticsApi, ROIOverview, ActionRankingItem, TimelineData, ABComparison } from '@/api/analytics';
import { useAppStore } from '@/stores';
import { getEChartsThemeColors } from '@/utils/echartsTheme';

const ACTION_TYPE_COLORS: Record<string, string> = {
  eeat: 'blue',
  fact_density: 'green',
  schema: 'orange',
  keyword: 'purple',
};

const ACTION_TYPE_LABELS: Record<string, string> = {
  eeat: 'E-E-A-T 优化',
  fact_density: '事实密度提升',
  schema: 'Schema 标注',
  keyword: '关键词布局',
};

const formatPercent = (val: number | undefined): string => {
  if (val === undefined || val === null) return '0.0%';
  return `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`;
};

const formatDelta = (val: number | undefined): string => {
  if (val === undefined || val === null) return '0.00';
  return `${val >= 0 ? '+' : ''}${val.toFixed(2)}`;
};

/** ECharts axis tooltip formatter 单个系列参数（仅声明用到的字段） */
interface EChartsAxisParam {
  axisValue?: string;
  seriesName?: string;
  marker?: string;
  value?: number;
}

/** ECharts label formatter 参数（仅声明用到的字段） */
interface EChartsLabelParam {
  dataIndex?: number;
}

const AnalyticsPage: React.FC = () => {
  const navigate = useNavigate();
  const { darkMode } = useAppStore();
  const [brand, setBrand] = useState<string>('');
  const [days, setDays] = useState<number>(30);
  const [loading, setLoading] = useState(false);

  const [overview, setOverview] = useState<ROIOverview | null>(null);
  const [ranking, setRanking] = useState<ActionRankingItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [abData, setAbData] = useState<ABComparison | null>(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const params = { brand: brand || undefined, days };
      const [ov, rk, tl, ab] = await Promise.all([
        analyticsApi.roiOverview(params),
        analyticsApi.actionRanking({ ...params, limit: 50 }),
        analyticsApi.timeline(params),
        analyticsApi.abComparison({ brand: brand || undefined }),
      ]);
      setOverview(ov);
      setRanking(rk);
      setTimeline(tl);
      setAbData(ab);
    } catch (err) {
      console.error('[AnalyticsPage] loadAll failed:', err);
      message.error('数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const mentionChangeColor = (overview?.mention_rate_change_pct ?? 0) >= 0 ? 'var(--success)' : 'var(--error)';
  const scoreChangeColor = (overview?.avg_score_change ?? 0) >= 0 ? 'var(--success)' : 'var(--error)';

  // Timeline chart option
  const timelineOption = useMemo<echarts.EChartsOption>(() => {
    if (!timeline) return {};
    const themeColors = getEChartsThemeColors(darkMode);
    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          const arr = params as EChartsAxisParam[];
          const date = arr[0]?.axisValue ?? '';
          let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`;
          arr.forEach((p: EChartsAxisParam) => {
            if (p.seriesName === '提及率') {
              const val = (p.value ?? 0) as number;
              html += `<div>${p.marker} ${p.seriesName}: <b>${(val * 100).toFixed(1)}%</b></div>`;
            }
          });
          const annotation = timeline.annotations.find(a => a.date === date);
          if (annotation) {
            html += `<div style="margin-top:4px;color:#3b82f6;border-top:1px solid ${themeColors.axisLineColor};padding-top:4px">
            ${ACTION_TYPE_LABELS[annotation.type] || annotation.type}<br/>
            <span style="font-size:12px;color:${themeColors.axisLabelColor}">${annotation.description}</span>
          </div>`;
          }
          return html;
        },
        backgroundColor: themeColors.tooltipBg,
        borderColor: themeColors.tooltipBorderColor,
        textStyle: { color: themeColors.tooltipTextColor },
      },
      grid: { left: 50, right: 30, top: 40, bottom: 40 },
      xAxis: {
        type: 'category',
        data: timeline.mention_trend.map(d => d.date),
        axisLabel: { fontSize: 11, color: themeColors.axisLabelColor },
        axisLine: { lineStyle: { color: themeColors.axisLineColor } },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          fontSize: 11,
          color: themeColors.axisLabelColor,
          formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: themeColors.splitLineColor } },
      },
      series: [
        {
          name: '提及率',
          type: 'line',
          data: timeline.mention_trend.map(d => d.rate),
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { color: '#3b82f6', width: 2 },
          itemStyle: { color: '#3b82f6' },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59,130,246,0.15)' },
                { offset: 1, color: 'rgba(59,130,246,0.01)' },
              ],
            },
          },
          markLine: {
            silent: false,
            symbol: ['none', 'none'],
            lineStyle: { color: '#f59e0b', type: 'dashed', width: 1.5 },
            label: {
              show: true,
              position: 'insideEndTop',
              fontSize: 10,
              color: '#f59e0b',
              formatter: (params: EChartsLabelParam) => {
                const annotation = timeline.annotations.find((_, i) => i === params.dataIndex);
                return annotation ? (ACTION_TYPE_LABELS[annotation.type] || annotation.type) : '';
              },
            },
            data: timeline.annotations.map(a => ({
              xAxis: a.date,
              tooltip: { show: true, formatter: () => `<b>${ACTION_TYPE_LABELS[a.type] || a.type}</b><br/>${a.description}` },
            })),
          },
        },
      ],
    };
  }, [timeline, darkMode]);

  // Table columns for action ranking
  const rankingColumns = [
    {
      title: '动作类型',
      dataIndex: 'action_type',
      key: 'action_type',
      width: 130,
      render: (type: string) => (
        <Tag color={ACTION_TYPE_COLORS[type] || 'default'}>
          {ACTION_TYPE_LABELS[type] || type}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      width: 100,
      render: (p: string) => p ? <Tag>{p}</Tag> : '-',
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      key: 'keyword',
      width: 140,
      ellipsis: true,
      render: (kw: string) => kw || '-',
    },
    {
      title: '优化前',
      dataIndex: 'score_before',
      key: 'score_before',
      width: 80,
      align: 'center' as const,
      render: (v: number) => v !== undefined && v !== null ? v.toFixed(2) : '-',
    },
    {
      title: '优化后',
      dataIndex: 'score_after',
      key: 'score_after',
      width: 80,
      align: 'center' as const,
      render: (v: number) => v !== undefined && v !== null ? v.toFixed(2) : '-',
    },
    {
      title: '变化',
      dataIndex: 'score_delta',
      key: 'score_delta',
      width: 90,
      align: 'center' as const,
      sorter: (a: ActionRankingItem, b: ActionRankingItem) => (a.score_delta ?? 0) - (b.score_delta ?? 0),
      defaultSortOrder: 'descend' as const,
      render: (delta: number) => {
        if (delta === undefined || delta === null) return '-';
        const color = delta > 0 ? 'var(--success)' : delta < 0 ? 'var(--error)' : 'var(--text-tertiary)';
        const icon = delta > 0 ? <ArrowUpOutlined /> : delta < 0 ? <ArrowDownOutlined /> : null;
        return (
          <span style={{ color, fontWeight: 600 }}>
            {icon} {formatDelta(delta)}
          </span>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (d: string) => d ? d.slice(0, 19).replace('T', ' ') : '-',
    },
  ];

  const sortedRanking = [...ranking].sort((a, b) => (b.score_delta ?? 0) - (a.score_delta ?? 0));

  return (
    <Spin spinning={loading}>
      <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">ROI 归因分析</h2>
        <p className="page-desc">追踪优化动作效果，量化品牌提及率提升归因</p>
      </div>

      {/* Filter Bar */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="输入品牌名称（可选）"
            value={brand}
            onChange={e => setBrand(e.target.value)}
            onPressEnter={loadAll}
            allowClear
            style={{ width: 220 }}
          />
          <Select
            value={days}
            onChange={setDays}
            style={{ width: 120 }}
            options={[
              { label: '近 7 天', value: 7 },
              { label: '近 30 天', value: 30 },
              { label: '近 90 天', value: 90 },
            ]}
          />
          <Button type="primary" icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>
            刷新
          </Button>
        </Space>
      </Card>

      {/* KPI Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <div className="kpi-stat">
              <div className="kpi-stat-label">总操作数</div>
              <div className="kpi-stat-value">{overview?.total_actions ?? 0}</div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <div className="kpi-stat">
              <div className="kpi-stat-label">提及率变化</div>
              <div className="kpi-stat-value" style={{ color: mentionChangeColor, display: 'flex', alignItems: 'center', gap: 6 }}>
                {(overview?.mention_rate_change_pct ?? 0) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                {formatPercent(overview?.mention_rate_change_pct)}
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <div className="kpi-stat">
              <div className="kpi-stat-label">均分变化</div>
              <div className="kpi-stat-value" style={{ color: scoreChangeColor, display: 'flex', alignItems: 'center', gap: 6 }}>
                {(overview?.avg_score_change ?? 0) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                {formatDelta(overview?.avg_score_change)}
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <div className="kpi-stat">
              <div className="kpi-stat-label">单次成本</div>
              <div className="kpi-stat-value">
                ¥{overview?.cost_per_action?.toFixed(2) ?? '0.00'}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Timeline Chart */}
      <Card
        title="提及率趋势与优化动作标注"
        style={{ marginBottom: 16 }}
      >
        {timeline && timeline.mention_trend.length > 0 ? (
          <ReactECharts
            option={timelineOption}
            style={{ height: 340 }}
            notMerge
            lazyUpdate
          />
        ) : (
          <Empty description="暂无趋势数据，执行验证后将生成趋势分析" style={{ padding: '40px 0' }}>
            <Button type="primary" icon={<SearchOutlined />} onClick={() => navigate('/verify')}>
              前往验证
            </Button>
          </Empty>
        )}
      </Card>

      {/* A/B Comparison */}
      <Card title="A/B 对比" style={{ marginBottom: 16 }}>
        {abData?.has_data ? (
          <Row gutter={[24, 16]}>
            <Col xs={24} md={12}>
              <div style={{
                background: 'var(--bg-tertiary)',
                borderRadius: 8,
                padding: 24,
                textAlign: 'center',
              }}>
                <div style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 8 }}>
                  优化前（{abData.split_date ? `截至 ${abData.split_date}` : '基准期'}）
                </div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>提及率</div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {((abData.mention_rate_before ?? 0) * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>平均分</div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {(abData.avg_score_before ?? 0).toFixed(2)}
                  </div>
                </div>
              </div>
            </Col>
            <Col xs={24} md={12}>
              <div style={{
                background: 'var(--brand-50)',
                border: '1px solid var(--brand-100)',
                borderRadius: 8,
                padding: 24,
                textAlign: 'center',
              }}>
                <div style={{ fontSize: 13, color: 'var(--brand-500)', marginBottom: 8 }}>
                  优化后（当前）
                </div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>提及率</div>
                  <Space align="center">
                    <span style={{ fontSize: 28, fontWeight: 700, color: 'var(--brand-500)' }}>
                      {((abData.mention_rate_after ?? 0) * 100).toFixed(1)}%
                    </span>
                    <Tag color={((abData.mention_rate_lift ?? 0)) >= 0 ? 'green' : 'red'} style={{ fontSize: 13 }}>
                      {(abData.mention_rate_lift ?? 0) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                      {formatPercent(abData.mention_rate_lift)}
                    </Tag>
                  </Space>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>平均分</div>
                  <Space align="center">
                    <span style={{ fontSize: 28, fontWeight: 700, color: 'var(--brand-500)' }}>
                      {(abData.avg_score_after ?? 0).toFixed(2)}
                    </span>
                    <Tag color={((abData.score_lift ?? 0)) >= 0 ? 'green' : 'red'} style={{ fontSize: 13 }}>
                      {(abData.score_lift ?? 0) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                      {formatDelta(abData.score_lift)}
                    </Tag>
                  </Space>
                </div>
              </div>
            </Col>
          </Row>
        ) : (
          <Empty
            description={abData?.message || '暂无足够数据进行A/B对比，优化更多内容后即可对比效果'}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button icon={<ThunderboltOutlined />} onClick={() => navigate('/optimize')}>
              前往优化
            </Button>
          </Empty>
        )}
      </Card>

      {/* Action Ranking Table */}
      <Card title="优化动作效果排名">
        <Table
          columns={rankingColumns}
          dataSource={sortedRanking}
          rowKey="id"
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: total => `共 ${total} 条` }}
          scroll={{ x: 900 }}
          locale={{ emptyText: <Empty description="暂无优化动作数据" /> }}
        />
      </Card>
      </div>
    </Spin>
  );
};

export default AnalyticsPage;
