import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Card, Input, Button, Progress, Row, Col, Tag, Space, Table, Alert,
  Typography, Spin, message, Divider
} from 'antd';
import {
  PlayCircleOutlined, StopOutlined, ReloadOutlined,
  CheckCircleOutlined, BulbOutlined, RiseOutlined, HistoryOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { ddsApi } from '@/api/dds';
import type { DDSScoreResult, DDSHistoryItem } from '@/api/dds';
import { SSEClient } from '@/utils/request';
import { getScoreColor, getScoreLevel } from '@/constants';
import { useAppStore } from '@/stores';
import { getEChartsThemeColors } from '@/utils/echartsTheme';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

// Sub-score label maps
const SUB_SCORE_LABELS: Record<string, Record<string, string>> = {
  semantic_depth: {
    logic: '逻辑层次',
    reasoning: '推理论证',
    insight: '观点洞察',
    richness: '内容丰富度',
  },
  data_support: {
    data_points: '数据点',
    citations: '引用来源',
    examples: '案例说明',
    statistics: '统计数据',
  },
  authoritative_source: {
    credentials: '资质认证',
    expert_quotes: '专家引用',
    references: '参考文献',
    venue_quality: '发布渠道质量',
  },
};

const DIMENSION_LABELS: Record<string, string> = {
  semantic_depth: '语义深度',
  data_support: '数据支撑',
  authoritative_source: '权威来源',
};

// ---- Gauge Chart Option ----

const getGaugeOption = (score: number, darkMode: boolean) => {
  const themeColors = getEChartsThemeColors(darkMode);
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        radius: '90%',
        center: ['50%', '55%'],
        progress: {
          show: true,
          width: 14,
          itemStyle: { color: getScoreColor(score) },
        },
        axisLine: {
          lineStyle: {
            width: 14,
            color: [[1, themeColors.axisLineColor]],
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: {
          offsetCenter: [0, '30%'],
          fontSize: 14,
          color: themeColors.textColor,
          fontWeight: 400,
        },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '-5%'],
          fontSize: 42,
          fontWeight: 700,
          color: getScoreColor(score),
          formatter: `{value}`,
        },
        data: [
          {
            value: score,
            name: getScoreLevel(score),
          },
        ],
      },
    ],
  };
};

// ---- Radar Chart Option ----

const getRadarOption = (result: DDSScoreResult, darkMode: boolean) => {
  const themeColors = getEChartsThemeColors(darkMode);
  return {
    radar: {
      indicator: [
        { name: '语义深度', max: 100 },
        { name: '数据支撑', max: 100 },
        { name: '权威来源', max: 100 },
      ],
      radius: '65%',
      center: ['50%', '52%'],
      splitNumber: 4,
      axisName: {
        color: themeColors.textColor,
        fontSize: 13,
        fontWeight: 500,
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(59,130,246,0.02)', 'rgba(59,130,246,0.04)', 'rgba(59,130,246,0.06)', 'rgba(59,130,246,0.08)'],
        },
      },
      splitLine: {
        lineStyle: { color: themeColors.splitLineColor },
      },
      axisLine: {
        lineStyle: { color: themeColors.axisLineColor },
      },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 6,
        data: [
          {
            value: [
              result.semantic_depth.score,
              result.data_support.score,
              result.authoritative_source.score,
            ],
            name: 'DDS 评分',
            areaStyle: {
              color: {
                type: 'radial',
                x: 0.5,
                y: 0.5,
                r: 0.5,
                colorStops: [
                  { offset: 0, color: 'rgba(59,130,246,0.35)' },
                  { offset: 1, color: 'rgba(59,130,246,0.08)' },
                ],
              },
            },
            lineStyle: { color: '#3B82F6', width: 2 },
            itemStyle: { color: '#3B82F6' },
          },
        ],
      },
    ],
  };
};

// ---- Dimension Card ----

interface DimensionCardProps {
  dimensionKey: string;
  data: { score: number; sub_scores: Record<string, number>; details: string };
}

const DimensionCard: React.FC<DimensionCardProps> = ({ dimensionKey, data }) => {
  const labels = SUB_SCORE_LABELS[dimensionKey] || {};
  const color = getScoreColor(data.score);

  return (
    <Card
      style={{ borderRadius: 8, border: '1px solid var(--border-default)' }}
      styles={{ body: { padding: 20 } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 15 }}>{DIMENSION_LABELS[dimensionKey]}</Text>
        <Tag
          style={{ fontSize: 16, fontWeight: 700, padding: '2px 10px', borderRadius: 6 }}
          color={color}
        >
          {data.score}
        </Tag>
      </div>
      <div style={{ marginBottom: 12 }}>
        {Object.entries(data.sub_scores).map(([key, val]) => (
          <div key={key} style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
              <Text type="secondary">{labels[key] || key}</Text>
              <Text style={{ fontWeight: 500, color: getScoreColor(val) }}>{val}</Text>
            </div>
            <Progress
              percent={val}
              showInfo={false}
              strokeColor={getScoreColor(val)}
              strokeWidth={5}
              size="small"
              style={{ marginBottom: 0 }}
            />
          </div>
        ))}
      </div>
      <Divider style={{ margin: '12px 0' }} />
      <Paragraph
        style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 0, lineHeight: 1.7 }}
      >
        {data.details}
      </Paragraph>
    </Card>
  );
};

// ---- Main Component ----

const DDSScorePage: React.FC = () => {
  const [content, setContent] = useState('');
  const [brand, setBrand] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [chunks, setChunks] = useState('');
  const [result, setResult] = useState<DDSScoreResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<DDSHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const clientRef = useRef<SSEClient | null>(null);
  const { darkMode } = useAppStore();

  // 图表配置随暗色模式变化重算
  const gaugeOption = useMemo(
    () => (result ? getGaugeOption(result.total_score, darkMode) : {}),
    [result, darkMode]
  );
  const radarOption = useMemo(
    () => (result ? getRadarOption(result, darkMode) : {}),
    [result, darkMode]
  );

  // Load history on mount
  useEffect(() => {
    loadHistory();
    return () => {
      clientRef.current?.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await ddsApi.history({ limit: 20 });
      setHistory(data || []);
    } catch (err) {
      console.error('[DDSScorePage] 加载历史失败:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleScore = () => {
    if (!content || content.trim().length < 20) {
      message.warning('请输入要评分的内容（至少20字）');
      return;
    }
    setError(null);
    setResult(null);
    setChunks('');

    const body: Record<string, unknown> = { content };
    if (brand.trim()) body.brand = brand.trim();

    // 使用 SSEClient 而非 StreamingText 组件：
    // DDS 评分需要同时收集流式 chunk（实时展示）和最终结构化结果（DDSScoreResult），
    // StreamingText 仅支持文本流式 + onComplete 回调，无法满足此场景的双通道需求。
    const client = new SSEClient();
    clientRef.current = client;

    client.connectPOST('/dds/score', body, {
      onStart: () => {
        setStreaming(true);
      },
      onChunk: (data) => {
        setChunks(prev => prev + (data.content || ''));
      },
      onProgress: (_data) => {
        // progress data might have a percent field
        // no-op: chunks themselves show streaming activity
      },
      onComplete: (data) => {
        setStreaming(false);
        const r = data.result as DDSScoreResult | undefined;
        if (r) {
          setResult(r);
          loadHistory();
        } else {
          // If result is at top level
          setResult(data as unknown as DDSScoreResult);
          loadHistory();
        }
      },
      onError: (data) => {
        setStreaming(false);
        const msg = String(data.error || data.message || '评分失败');
        setError(msg);
        message.error(msg);
      },
    });
  };

  const handleStop = () => {
    clientRef.current?.disconnect();
    setStreaming(false);
  };

  const handleReset = () => {
    setContent('');
    setBrand('');
    setResult(null);
    setChunks('');
    setError(null);
  };

  // --- History table columns ---
  const historyColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '语义深度',
      dataIndex: 'semantic_depth',
      key: 'semantic_depth',
      width: 90,
      render: (v: number) => <Text style={{ color: getScoreColor(v), fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: '数据支撑',
      dataIndex: 'data_support',
      key: 'data_support',
      width: 90,
      render: (v: number) => <Text style={{ color: getScoreColor(v), fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: '权威来源',
      dataIndex: 'authoritative_source',
      key: 'authoritative_source',
      width: 90,
      render: (v: number) => <Text style={{ color: getScoreColor(v), fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: '总分',
      dataIndex: 'total_score',
      key: 'total_score',
      width: 90,
      render: (v: number) => (
        <Tag color={getScoreColor(v)} style={{ fontWeight: 600, borderRadius: 4 }}>
          {v}
        </Tag>
      ),
    },
    {
      title: '品牌',
      dataIndex: 'brand',
      key: 'brand',
      width: 120,
      render: (v?: string) => v || <Text type="secondary">-</Text>,
    },
    {
      title: '评分时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v?: string) => {
        if (!v) return <Text type="secondary">-</Text>;
        try {
          return dayjs(v).format('MM-DD HH:mm');
        } catch (err) {
          console.warn('[DDSScorePage] date formatting failed, returning raw value:', err);
          return v;
        }
      },
    },
  ];

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <h2 className="page-title">DDS 三维评分</h2>
        <p className="page-desc">深度语义 · 数据支撑 · 权威来源 — 全方位评估内容质量</p>
      </div>

      <Row gutter={[16, 16]}>
        {/* Left column: Input + Results */}
        <Col xs={24} lg={15}>
          <Card
            title={
              <Space>
                <RiseOutlined style={{ color: 'var(--brand-500)' }} />
                <span>内容输入</span>
              </Space>
            }
            extra={
              result && !streaming ? (
                <Button icon={<ReloadOutlined />} size="small" onClick={handleReset}>
                  重新评分
                </Button>
              ) : null
            }
            style={{ borderRadius: 8, border: '1px solid var(--border-default)' }}
            styles={{ body: { padding: 20 } }}
          >
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>
                文章内容 <Text type="danger">*</Text>
              </Text>
              <TextArea
                rows={8}
                placeholder="粘贴要评分的文章内容..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                disabled={streaming}
                style={{ borderRadius: 6, resize: 'vertical', fontSize: 14, lineHeight: 1.7 }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>
                品牌（可选）
              </Text>
              <Input
                placeholder="输入品牌名称，用于品牌提及检测"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                disabled={streaming}
                style={{ borderRadius: 6 }}
                allowClear
              />
            </div>

            <Space>
              {!streaming ? (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={handleScore}
                  size="large"
                  style={{ borderRadius: 6, fontWeight: 500 }}
                >
                  开始评分
                </Button>
              ) : (
                <Button
                  danger
                  icon={<StopOutlined />}
                  onClick={handleStop}
                  size="large"
                  style={{ borderRadius: 6, fontWeight: 500 }}
                >
                  停止
                </Button>
              )}
            </Space>
          </Card>

          {/* Streaming Progress */}
          {streaming && (
            <Card
              style={{
                borderRadius: 8,
                border: '1px solid var(--border-default)',
                marginTop: 16,
              }}
            >
              <div style={{ marginBottom: 12 }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    <Spin size="small" style={{ marginRight: 8 }} />
                    AI 分析中...
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {chunks.length} 字符
                  </Text>
                </Space>
              </div>
              <Progress
                percent={Math.min(95, Math.round((chunks.length / 500) * 100))}
                strokeColor={{ from: '#3B82F6', to: '#10B981' }}
                showInfo={false}
                strokeWidth={6}
                style={{ marginBottom: 16 }}
              />
              <div
                style={{
                  background: 'var(--bg-tertiary)',
                  borderRadius: 6,
                  padding: 12,
                  maxHeight: 200,
                  overflowY: 'auto',
                  fontSize: 13,
                  lineHeight: 1.8,
                  color: 'var(--text-secondary)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {chunks || '等待模型响应...'}
              </div>
            </Card>
          )}

          {/* Error display */}
          {error && (
            <Alert
              type="error"
              message="评分失败"
              description={error}
              closable
              onClose={() => setError(null)}
              style={{ marginTop: 16, borderRadius: 6 }}
            />
          )}

          {/* Score Results — inline below input */}
          {result && !streaming && (
            <>
              {/* Summary: Gauge + Radar */}
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col xs={24} sm={10}>
                  <Card
                    style={{
                      borderRadius: 8,
                      border: '1px solid var(--border-default)',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                    styles={{ body: { padding: 20, width: '100%' } }}
                  >
                    <ReactECharts
                      option={gaugeOption}
                      style={{ height: 220, width: '100%' }}
                      opts={{ renderer: 'svg' }}
                    />
                    <div style={{ textAlign: 'center', marginTop: -8 }}>
                      {result.level && (
                        <Tag
                          color={result.level_color || getScoreColor(result.total_score)}
                          style={{ fontSize: 13, padding: '2px 12px', borderRadius: 4, fontWeight: 500 }}
                        >
                          {result.level}
                        </Tag>
                      )}
                    </div>
                  </Card>
                </Col>
                <Col xs={24} sm={14}>
                  <Card
                    style={{
                      borderRadius: 8,
                      border: '1px solid var(--border-default)',
                      height: '100%',
                    }}
                    styles={{ body: { padding: 20 } }}
                  >
                    <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>
                      三维度雷达图
                    </Text>
                    <ReactECharts
                      option={radarOption}
                      style={{ height: 210 }}
                      opts={{ renderer: 'svg' }}
                    />
                  </Card>
                </Col>
              </Row>

              {/* 3 Dimension Cards */}
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col xs={24} md={8} style={{ marginBottom: 16 }}>
                  <DimensionCard dimensionKey="semantic_depth" data={result.semantic_depth} />
                </Col>
                <Col xs={24} md={8} style={{ marginBottom: 16 }}>
                  <DimensionCard dimensionKey="data_support" data={result.data_support} />
                </Col>
                <Col xs={24} md={8} style={{ marginBottom: 16 }}>
                  <DimensionCard dimensionKey="authoritative_source" data={result.authoritative_source} />
                </Col>
              </Row>

              {/* Improvements & Strengths */}
              <Row gutter={16}>
                <Col xs={24} md={12} style={{ marginBottom: 16 }}>
                  <Card
                    title={
                      <Space>
                        <BulbOutlined style={{ color: 'var(--warning)' }} />
                        <span>改进建议</span>
                      </Space>
                    }
                    style={{ borderRadius: 8, border: '1px solid var(--border-default)', height: '100%' }}
                    styles={{ body: { padding: '12px 20px 20px' } }}
                  >
                    {result.improvements?.length > 0 ? (
                      <ul style={{ paddingLeft: 20, margin: 0 }}>
                        {result.improvements.map((item, idx) => (
                          <li
                            key={idx}
                            style={{
                              fontSize: 13,
                              lineHeight: 1.8,
                              color: 'var(--text-secondary)',
                              marginBottom: 6,
                            }}
                          >
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <Text type="secondary" style={{ fontSize: 13 }}>暂无改进建议</Text>
                    )}
                  </Card>
                </Col>
                <Col xs={24} md={12} style={{ marginBottom: 16 }}>
                  <Card
                    title={
                      <Space>
                        <CheckCircleOutlined style={{ color: 'var(--success)' }} />
                        <span>亮点</span>
                      </Space>
                    }
                    style={{ borderRadius: 8, border: '1px solid var(--border-default)', height: '100%' }}
                    styles={{ body: { padding: '12px 20px 20px' } }}
                  >
                    {result.strengths?.length > 0 ? (
                      <ul style={{ paddingLeft: 20, margin: 0 }}>
                        {result.strengths.map((item, idx) => (
                          <li
                            key={idx}
                            style={{
                              fontSize: 13,
                              lineHeight: 1.8,
                              color: 'var(--text-secondary)',
                              marginBottom: 6,
                            }}
                          >
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <Text type="secondary" style={{ fontSize: 13 }}>暂无亮点识别</Text>
                    )}
                  </Card>
                </Col>
              </Row>
            </>
          )}
        </Col>

        {/* Right column: History — always visible, sticky */}
        <Col xs={24} lg={9}>
          <div style={{ position: 'sticky', top: 80 }}>
            <Card
              title={
                <Space>
                  <HistoryOutlined style={{ color: 'var(--brand-500)' }} />
                  <span>评分历史</span>
                </Space>
              }
              extra={
                <Button icon={<ReloadOutlined />} size="small" onClick={loadHistory} loading={loadingHistory}>
                  刷新
                </Button>
              }
              style={{ borderRadius: 8, border: '1px solid var(--border-default)' }}
            >
              <Table
                dataSource={history}
                columns={historyColumns}
                rowKey="id"
                loading={loadingHistory}
                pagination={{ pageSize: 8, size: 'small' }}
                size="small"
                scroll={{ x: 500, y: 500 }}
                locale={{ emptyText: '暂无评分记录' }}
              />
            </Card>
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default DDSScorePage;
