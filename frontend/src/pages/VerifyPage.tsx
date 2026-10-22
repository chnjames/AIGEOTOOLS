import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card, Form, Input, Button, Space, Table, Tag, message,
  Row, Col, Popconfirm, Typography, Spin, Empty, Alert, Badge, Select, Divider, Radio, Tooltip, List, Collapse, Pagination
} from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, ThunderboltOutlined,
  ReloadOutlined, DeleteOutlined, QuestionCircleOutlined, BulbOutlined,
  ClockCircleOutlined, LoadingOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useSearchParams } from 'react-router-dom';
import { verificationApi } from '@/api/verification';
import { articlesApi } from '@/api/articles';
import { StreamingText } from '@/components';
import { useAppStore } from '@/stores';
import { PROVIDER_LABELS, VERIFY_PROVIDER_KEYS, getErrorMessage } from '@/constants';
import type { VerifyResult } from '@/types';
import { formatDateTime } from '@/utils/dateFormat';

const { Text } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

interface DiagnosisData {
  competing_brands?: string[];
  root_cause?: string;
  suggestions?: Array<{ text: string; difficulty?: string }>;
}

type ModelStatus = 'pending' | 'running' | 'complete' | 'error';

interface ModelResultItem {
  model: string;        // provider key, e.g. 'deepseek'
  model_name?: string;  // actual model ID from model_start, e.g. 'deepseek-chat'
  provider_label?: string;
  status: ModelStatus;
  isMentioned: boolean;
  content: string;
  done: boolean;
  error?: string;
  error_type?: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  positive_mentions?: number;
  negative_mentions?: number;
  verification_mode?: string;
  diagnosis?: string | null;
  recommended_brands?: string | null;
  full_response?: string;
}

const getDifficultyColor = (difficulty?: string): string => {
  switch (difficulty) {
    case 'easy': return 'green';
    case 'medium': return 'orange';
    case 'hard': return 'red';
    default: return 'blue';
  }
};

const getDifficultyLabel = (difficulty?: string): string => {
  switch (difficulty) {
    case 'easy': return '简单';
    case 'medium': return '中等';
    case 'hard': return '困难';
    default: return '未知';
  }
};

const parseDiagnosis = (diagnosisStr?: string | null): DiagnosisData | null => {
  if (!diagnosisStr) return null;
  try {
    return JSON.parse(diagnosisStr) as DiagnosisData;
  } catch (err) {
    console.warn('[VerifyPage] parseDiagnosis JSON.parse failed, returning null:', err);
    return null;
  }
};

const SentimentTag: React.FC<{ sentiment?: string; positiveMentions?: number; negativeMentions?: number }> = ({
  sentiment, positiveMentions, negativeMentions,
}) => {
  if (!sentiment) return null;
  const tagProps = (() => {
    switch (sentiment) {
      case 'positive':
        return { color: 'green', label: '正面' };
      case 'negative':
        return { color: 'red', label: '负面' };
      case 'neutral':
      default:
        return { color: 'blue', label: '中性' };
    }
  })();
  const counts: string[] = [];
  if (typeof positiveMentions === 'number' && positiveMentions > 0) counts.push(`正${positiveMentions}`);
  if (typeof negativeMentions === 'number' && negativeMentions > 0) counts.push(`负${negativeMentions}`);
  return (
    <Space size={4}>
      <Tag color={tagProps.color}>{tagProps.label}</Tag>
      {counts.length > 0 && <Text type="secondary" style={{ fontSize: 12 }}>({counts.join(' / ')})</Text>}
    </Space>
  );
};

const DiagnosisAlert: React.FC<{ diagnosisStr?: string | null }> = ({ diagnosisStr }) => {
  const diagnosis = useMemo(() => parseDiagnosis(diagnosisStr), [diagnosisStr]);
  if (!diagnosis) return null;
  return (
    <Alert
      type="warning"
      showIcon
      message="未提及品牌 - 原因诊断"
      style={{ marginTop: 8 }}
      description={
        <div style={{ marginTop: 4 }}>
          {diagnosis.competing_brands && diagnosis.competing_brands.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <Text strong style={{ fontSize: 12 }}>竞品品牌：</Text>
              <Space size={4} wrap style={{ marginTop: 4 }}>
                {diagnosis.competing_brands.map((brand, i) => (
                  <Tag key={i} color="volcano">{brand}</Tag>
                ))}
              </Space>
            </div>
          )}
          {diagnosis.root_cause && (
            <div style={{ marginBottom: 8 }}>
              <Text strong style={{ fontSize: 12 }}>根本原因：</Text>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{diagnosis.root_cause}</div>
            </div>
          )}
          {diagnosis.suggestions && diagnosis.suggestions.length > 0 && (
            <div>
              <Text strong style={{ fontSize: 12 }}><BulbOutlined /> 优化建议：</Text>
              <List
                size="small"
                dataSource={diagnosis.suggestions}
                renderItem={(item, idx) => (
                  <List.Item style={{ padding: '4px 0', border: 'none' }}>
                    <Space size={6} align="start">
                      <Text type="secondary" style={{ fontSize: 12 }}>{idx + 1}.</Text>
                      <Tag color={getDifficultyColor(item.difficulty)} style={{ fontSize: 11, marginRight: 0 }}>
                        {getDifficultyLabel(item.difficulty)}
                      </Tag>
                      <Text style={{ fontSize: 12 }}>{item.text}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </div>
          )}
        </div>
      }
    />
  );
};

const ModelStatusIcon: React.FC<{ status: ModelStatus; isMentioned?: boolean }> = ({ status, isMentioned }) => {
  switch (status) {
    case 'complete':
      return isMentioned
        ? <CheckCircleOutlined style={{ color: 'var(--success)', fontSize: 16 }} />
        : <CheckCircleOutlined style={{ color: 'var(--warning)', fontSize: 16 }} />;
    case 'running':
      return <LoadingOutlined style={{ color: 'var(--brand-500)', fontSize: 16 }} />;
    case 'error':
      return <CloseCircleOutlined style={{ color: 'var(--error)', fontSize: 16 }} />;
    case 'pending':
    default:
      return <ClockCircleOutlined style={{ color: 'var(--border-strong)', fontSize: 16 }} />;
  }
};

function getModelStatusText(r: ModelResultItem): string {
  switch (r.status) {
    case 'running':
      return '验证中...';
    case 'error':
      return getErrorMessage(r.error_type, r.error);
    case 'pending':
      return '等待中';
    case 'complete':
      if (r.isMentioned) {
        const sent = r.sentiment === 'positive' ? '正面' : r.sentiment === 'negative' ? '负面' : r.sentiment === 'neutral' ? '中性' : '';
        return `已提及${sent ? '，' + sent : ''}`;
      }
      return '未提及';
    default:
      return '';
  }
}

const VerifyPage: React.FC = () => {
  const { config } = useAppStore();
  const [searchParams] = useSearchParams();
  const defaultMode = config?.default_verify_mode === 'prompted' ? 'prompted' : 'natural';
  const [results, setResults] = useState<VerifyResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [activeTab, setActiveTab] = useState<'brand' | 'competitor'>('brand');
  const [streamKey, setStreamKey] = useState(0);
  const [streaming, setStreaming] = useState(false);
  const [modelResults, setModelResults] = useState<ModelResultItem[]>([]);
  const [detailResult, setDetailResult] = useState<VerifyResult | null>(null);
  const [verifyMode, setVerifyMode] = useState<'natural' | 'prompted'>(defaultMode as 'natural' | 'prompted');
  const [pendingNotice, setPendingNotice] = useState<string | null>(null);

  const [form] = Form.useForm();

  useEffect(() => {
    if (config?.default_verify_mode) {
      setVerifyMode(config.default_verify_mode === 'prompted' ? 'prompted' : 'natural');
    }
    // 读取从优化/文章页跳转过来的待验证内容（自动生成查询语句）
    // 优先读取 URL 查询参数 article_id（新版跳转），再通过 API 获取文章内容；
    // 兼容旧版 sessionStorage 跳转（未保存的优化内容）
    const articleIdParam = searchParams.get('article_id');
    if (articleIdParam) {
      const aid = Number(articleIdParam);
      if (!isNaN(aid) && aid > 0) {
        articlesApi.get(aid).then(article => {
          const brand = article.brand || config?.brand || '该品牌';
          form.setFieldsValue({ query: `请推荐一个合适的${brand}，并说明理由。` });
          setPendingNotice('已从优化页面跳转，查询语句已自动填充，点击「开始验证」即可');
        }).catch(err => {
          console.warn('[VerifyPage] 加载文章失败:', err);
        });
      }
    } else {
      // 兼容旧版 sessionStorage 跳转（未保存的优化内容）
      const pendingContent = sessionStorage.getItem('pending_content');
      if (pendingContent) {
        const brand = config?.brand || '该品牌';
        form.setFieldsValue({ query: `请推荐一个合适的${brand ? brand : '品牌'}，并说明理由。` });
        setPendingNotice('已从优化页面跳转，查询语句已自动填充，点击「开始验证」即可');
        sessionStorage.removeItem('pending_content');
      }
    }
  }, [config?.default_verify_mode, form]);

  const loadResults = useCallback(async () => {
    setLoading(true);
    try {
      const data = await verificationApi.results({ brand: config?.brand, page, page_size: pageSize });
      setResults(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('[VerifyPage] loadResults failed:', err);
      message.error('加载验证结果失败');
    } finally {
      setLoading(false);
    }
  }, [config?.brand, page, pageSize]);

  useEffect(() => { loadResults(); }, [loadResults]);

  const hasVerifyConfig = config?.verify_keys_configured && Object.values(config.verify_keys_configured).some(Boolean);

  const startVerify = () => {
    const values = form.getFieldsValue();
    if (!values.query) { message.warning('请输入查询语句'); return; }
    const verifyKeys = (config?.verify_keys_configured || {}) as Record<string, boolean>;
    const selectedProviders: string[] = values.providers || Object.entries(verifyKeys)
      .filter(([, configured]) => configured)
      .map(([p]: [string, boolean]) => p);
    if (!selectedProviders.length) { message.warning('请先在设置中配置验证模型 API Key'); return; }

    setStreaming(true);
    setStreamKey(k => k + 1);
    setModelResults(selectedProviders.map((p: string) => ({
      model: p,
      provider_label: PROVIDER_LABELS[p] || p,
      status: 'pending' as ModelStatus,
      isMentioned: false,
      content: '',
      done: false,
    })));
  };

  const onSSEEvent = (event: string, data: Record<string, unknown>) => {
    if (event === 'model_start') {
      const provider = data.provider as string | undefined;
      const modelName = data.model as string | undefined;
      const key = provider || modelName;
      if (key) {
        setModelResults(prev => prev.map(r =>
          r.model === key
            ? { ...r, status: 'running' as ModelStatus, model_name: modelName, provider_label: PROVIDER_LABELS[r.model] || r.model }
            : r
        ));
      }
    } else if (event === 'model_complete' || event === 'model_error') {
      const model = data.model as string;
      const isError = event === 'model_error';
      setModelResults(prev => prev.map(r =>
        r.model === model
          ? {
              ...r,
              done: true,
              status: isError ? 'error' as ModelStatus : 'complete' as ModelStatus,
              isMentioned: isError ? false : ((data.is_mentioned as boolean) ?? false),
              content: (data.content as string) || '',
              full_response: (data.full_response as string) || (data.content as string) || '',
              error: isError ? (data.message as string | undefined) || (data.error as string | undefined) : undefined,
              error_type: isError ? (data.error_type as string | undefined) : undefined,
              sentiment: data.sentiment as ModelResultItem['sentiment'],
              positive_mentions: typeof data.positive_mentions === 'number' ? data.positive_mentions as number : undefined,
              negative_mentions: typeof data.negative_mentions === 'number' ? data.negative_mentions as number : undefined,
              verification_mode: data.verification_mode as string | undefined,
              diagnosis: data.diagnosis as string | null | undefined,
              recommended_brands: data.recommended_brands as string | null | undefined,
            }
          : r
      ));
    }
  };

  const onComplete = () => {
    setStreaming(false);
    loadResults();
  };

  const handleDelete = async (id: number) => {
    await verificationApi.delete(id);
    message.success('已删除');
    loadResults();
  };

  const renderSentimentInTable = (sentiment?: string, positiveMentions?: number, negativeMentions?: number) => {
    if (!sentiment) return '-';
    return <SentimentTag sentiment={sentiment} positiveMentions={positiveMentions} negativeMentions={negativeMentions} />;
  };

  const columns: ColumnsType<VerifyResult> = [
    { title: 'ID', dataIndex: 'id', width: 50 },
    { title: '查询语句', dataIndex: 'query', ellipsis: true, width: 180 },
    { title: '品牌', dataIndex: 'brand', width: 70, render: (b) => b ? <Tag>{b}</Tag> : '-' },
    { title: '验证模型', dataIndex: 'verify_model', width: 90, render: (m) => m ? <Tag color="purple">{PROVIDER_LABELS[m] || m}</Tag> : '-' },
    {
      title: '模式', dataIndex: 'verification_mode', width: 70,
      render: (mode: string) => mode === 'natural'
        ? <Tag color="cyan">自然</Tag>
        : mode === 'prompted'
          ? <Tag color="geekblue">提示</Tag>
          : '-',
    },
    {
      title: '情感', dataIndex: 'sentiment', width: 110,
      render: (s: string, r) => renderSentimentInTable(s, r.positive_mentions, r.negative_mentions),
    },
    {
      title: '提及次数', dataIndex: 'mention_count', width: 70,
      render: (c: number) => <Text strong style={{ color: c > 0 ? 'var(--success)' : 'var(--error)' }}>{c}</Text>,
    },
    {
      title: '是否提及', dataIndex: 'is_mentioned', width: 80,
      render: (m: boolean) => m
        ? <Tag icon={<CheckCircleOutlined />} color="success">已提及</Tag>
        : <Tag icon={<CloseCircleOutlined />} color="error">未提及</Tag>,
    },
    { title: '提及位置', dataIndex: 'mention_position', width: 90, render: (p) => p || '-' },
    { title: '创建时间', dataIndex: 'created_at', width: 140, render: (t) => t ? formatDateTime(t) : '-' },
    {
      title: '操作', width: 60,
      render: (_, r) => (
        <Popconfirm title="确定删除这条验证记录？" onConfirm={() => handleDelete(r.id)} okText="确定" cancelText="取消">
          <Button type="link" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const mentionCount = modelResults.filter(r => r.isMentioned).length;
  const totalModels = modelResults.length;
  const completedModels = modelResults.filter(r => r.done).length;
  const runningModel = modelResults.find(r => r.status === 'running');

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">品牌可见性验证</h2>
        <p className="page-desc">多模型验证 AI 搜索结果中品牌是否被提及及排名位置</p>
      </div>

      {!hasVerifyConfig && (
        <Alert type="warning" showIcon message="请先在系统设置中配置至少一个验证模型的 API Key" style={{ marginBottom: 16 }} />
      )}

      {pendingNotice && (
        <Alert type="info" showIcon closable message={pendingNotice}
          onClose={() => setPendingNotice(null)} style={{ marginBottom: 16 }} />
      )}

      <Row gutter={16}>
        <Col xs={24} lg={10}>
          <Card title="验证配置">
            <Form form={form} layout="vertical" initialValues={{ providers: [] }}>
              <Form.Item label="验证类型">
                <div style={{ display: 'flex', gap: 8 }}>
                  <Button
                    type={activeTab === 'brand' ? 'primary' : 'default'}
                    onClick={() => setActiveTab('brand')}
                  >
                    品牌验证
                  </Button>
                  <Button
                    type={activeTab === 'competitor' ? 'primary' : 'default'}
                    onClick={() => setActiveTab('competitor')}
                  >
                    竞品对比
                  </Button>
                </div>
              </Form.Item>

              {activeTab === 'brand' && (
                <Form.Item
                  label={
                    <Space>
                      <span>验证模式</span>
                      <Tooltip title="自然模式：不提示品牌，模拟真实用户提问，更准确反映品牌在AI搜索中的实际表现">
                        <QuestionCircleOutlined style={{ color: 'var(--text-tertiary)' }} />
                      </Tooltip>
                    </Space>
                  }
                >
                  <Radio.Group
                    value={verifyMode}
                    onChange={(e) => setVerifyMode(e.target.value)}
                    optionType="button"
                    buttonStyle="solid"
                  >
                    <Radio.Button value="natural">自然模式</Radio.Button>
                    <Radio.Button value="prompted">提示模式</Radio.Button>
                  </Radio.Group>
                </Form.Item>
              )}

              <Form.Item label={activeTab === 'brand' ? '查询语句/问题' : '对比查询'} name="query" rules={[{ required: true }]}>
                <TextArea rows={3} placeholder={
                  activeTab === 'brand'
                    ? '例如：项目管理软件哪个好用？'
                    : '例如：有哪些优秀的项目管理工具？'
                } />
              </Form.Item>

              {activeTab === 'competitor' && (
                <Form.Item label="竞品列表（逗号分隔）" name="competitors">
                  <Input placeholder="竞品A,竞品B,竞品C" />
                </Form.Item>
              )}

              <Form.Item label="选择验证模型" name="providers">
                <Select
                  mode="multiple"
                  placeholder="选择验证模型"
                  options={VERIFY_PROVIDER_KEYS.map(p => ({
                    label: (
                      <span>
                        {PROVIDER_LABELS[p]}
                        {config?.verify_keys_configured?.[p]
                          ? <Badge status="success" style={{ marginLeft: 6 }} />
                          : <Tag color="red" style={{ marginLeft: 6, fontSize: 10 }}>未配置</Tag>}
                      </span>
                    ),
                    value: p,
                    disabled: !config?.verify_keys_configured?.[p],
                  }))}
                />
              </Form.Item>

              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                block
                onClick={startVerify}
                disabled={!hasVerifyConfig}
                loading={streaming}
              >
                {streaming ? `验证中 (${completedModels}/${totalModels})` : '开始验证'}
              </Button>
            </Form>
          </Card>

          {modelResults.length > 0 && (
            <Card title="模型验证结果" size="small" style={{ marginTop: 16 }}>
              {/* Overall mention rate */}
              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <Text style={{ fontSize: 14 }}>品牌提及率：</Text>
                <Text strong style={{ fontSize: 24, color: mentionCount === totalModels ? 'var(--success)' : mentionCount > 0 ? 'var(--warning)' : 'var(--error)' }}>
                  {totalModels ? Math.round(mentionCount / totalModels * 100) : 0}%
                </Text>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{mentionCount}/{totalModels} 个模型提及了品牌</div>
              </div>

              {/* Per-model progress list */}
              <div style={{ marginBottom: 12 }}>
                <Text strong style={{ fontSize: 13 }}>验证进度：</Text>
                <div style={{ marginTop: 8 }}>
                  {modelResults.map((r, i) => {
                    const providerLabel = r.provider_label || PROVIDER_LABELS[r.model] || r.model;
                    const modelDisplay = r.model_name ? `${providerLabel} (${r.model_name})` : providerLabel;
                    return (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '6px 0', fontSize: 13,
                        borderBottom: i < modelResults.length - 1 ? '1px solid var(--border-light)' : 'none',
                      }}>
                        <ModelStatusIcon status={r.status} isMentioned={r.isMentioned} />
                        <Text strong style={{ minWidth: 160 }}>{modelDisplay}</Text>
                        <Text type={r.status === 'error' ? 'danger' : r.status === 'complete' && !r.isMentioned ? 'warning' : 'secondary'}
                          style={{ fontSize: 12 }}>
                          {getModelStatusText(r)}
                        </Text>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Running model indicator */}
              {runningModel && (
                <Alert
                  type="info"
                  showIcon
                  icon={<Spin size="small" />}
                  message={`正在使用 ${runningModel.provider_label || PROVIDER_LABELS[runningModel.model] || runningModel.model}${runningModel.model_name ? ` (${runningModel.model_name})` : ''} 验证...`}
                  style={{ marginBottom: 12 }}
                />
              )}

              {/* Detailed result cards */}
              {modelResults.map((r, i) => {
                const providerLabel = r.provider_label || PROVIDER_LABELS[r.model] || r.model;
                const modelDisplay = r.model_name ? `${providerLabel} (${r.model_name})` : providerLabel;
                const cardBg = r.status === 'complete'
                  ? (r.isMentioned ? 'var(--bg-success)' : 'var(--bg-warning)')
                  : r.status === 'error' ? 'var(--bg-error)' : 'var(--bg-tertiary)';
                return (
                  <div key={i} style={{
                    padding: 10, marginBottom: 8, borderRadius: 6,
                    border: '1px solid var(--border-light)',
                    background: cardBg,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
                      <Space size={6} wrap>
                        <Tag color="purple">{modelDisplay}</Tag>
                        {r.status === 'running' && <Spin size="small" />}
                        {r.status === 'error' && (
                          <Tag color="red">{getErrorMessage(r.error_type, r.error)}</Tag>
                        )}
                        {r.status === 'complete' && r.isMentioned && (
                          <>
                            <Tag icon={<CheckCircleOutlined />} color="success">已提及</Tag>
                            <SentimentTag
                              sentiment={r.sentiment}
                              positiveMentions={r.positive_mentions}
                              negativeMentions={r.negative_mentions}
                            />
                          </>
                        )}
                        {r.status === 'complete' && !r.isMentioned && (
                          <Tag icon={<CloseCircleOutlined />} color="warning">未提及</Tag>
                        )}
                      </Space>
                    </div>
                    {r.content && (
                      <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-secondary)', maxHeight: 120, overflow: 'auto' }}>
                        {r.content}
                      </div>
                    )}
                    {r.status === 'complete' && r.full_response && r.full_response !== r.content && (
                      <Collapse ghost size="small" style={{ marginTop: 4 }}>
                        <Panel header="查看完整AI回复" key="full">
                          <div style={{
                            fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap',
                            maxHeight: 300, overflow: 'auto', padding: 8, background: 'var(--bg-hover)', borderRadius: 4,
                          }}>
                            {r.full_response}
                          </div>
                        </Panel>
                      </Collapse>
                    )}
                    {r.status === 'complete' && !r.isMentioned && r.diagnosis && (
                      <DiagnosisAlert diagnosisStr={r.diagnosis} />
                    )}
                  </div>
                );
              })}
            </Card>
          )}
        </Col>

        <Col xs={24} lg={14}>
          {(streaming || modelResults.length > 0) && (
            <Card title="实时验证流" size="small" style={{ marginBottom: 16 }}>
              <StreamingText
                key={`verify-${activeTab}-${streamKey}`}
                autoStart={streaming}
                fetchStream={(handlers) => {
                  const values = form.getFieldsValue();
                  const selectedProviders = values.providers || Object.entries(config?.verify_keys_configured || {})
                    .filter(([, c]) => c)
                    .map(([p]) => p);
                  const apiCall = activeTab === 'brand' ? verificationApi.verifyStream : verificationApi.competitorStream;
                  const body: Record<string, unknown> = {
                    query: values.query,
                    brand: config?.brand,
                    providers: selectedProviders,
                    temperature: 0.3,
                  };
                  if (activeTab === 'brand') {
                    body.mode = verifyMode;
                  }
                  if (activeTab === 'competitor' && values.competitors) {
                    body.competitors = (values.competitors as string).split(/[,，]/).map((s: string) => s.trim()).filter(Boolean);
                  }
                  apiCall(body as any, {
                    ...handlers,
                    onEvent: (event, data) => {
                      handlers.onEvent?.(event, data);
                      onSSEEvent(event, data);
                    },
                  });
                }}
                onComplete={onComplete}
                height={250}
                placeholder="点击「开始验证」查看各模型实时验证过程"
              />
            </Card>
          )}

          <Card
            title={`历史验证记录 (${total})`}
            extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadResults}>刷新</Button>}
          >
            <Table
              columns={columns}
              dataSource={results}
              rowKey="id"
              loading={loading}
              size="small"
              pagination={false}
              locale={{
                emptyText: (
                  <Empty description="还没有验证任何内容，先去优化页面优化一篇文章再来验证吧">
                    <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => window.location.hash = '#/optimize'}>
                      前往优化
                    </Button>
                  </Empty>
                )
              }}
              scroll={{ x: 1000 }}
              onRow={(record) => ({
                onClick: () => setDetailResult(record),
                style: { cursor: 'pointer' },
              })}
            />
            {total > 0 && (
              <div style={{ marginTop: 12, textAlign: 'right' }}>
                <Pagination
                  current={page}
                  pageSize={pageSize}
                  total={total}
                  onChange={(p) => setPage(p)}
                  showSizeChanger={false}
                  showTotal={(t) => `共 ${t} 条记录`}
                />
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {detailResult && (
        <Card
          title={`验证详情 #${detailResult.id}`}
          style={{ marginTop: 16 }}
          extra={<Button size="small" onClick={() => setDetailResult(null)}>关闭</Button>}
        >
          <Row gutter={[16, 8]}>
            <Col span={12}>
              <Text type="secondary">查询：</Text><Text strong>{detailResult.query}</Text>
            </Col>
            <Col span={6}>
              <Text type="secondary">模型：</Text><Tag color="purple">{PROVIDER_LABELS[detailResult.verify_model || ''] || detailResult.verify_model}</Tag>
            </Col>
            <Col span={6}>
              <Text type="secondary">模式：</Text>
              {detailResult.verification_mode === 'natural'
                ? <Tag color="cyan">自然模式</Tag>
                : detailResult.verification_mode === 'prompted'
                  ? <Tag color="geekblue">提示模式</Tag>
                  : '-'}
            </Col>
            <Col span={6}>
              <Text type="secondary">结果：</Text>
              {detailResult.is_mentioned
                ? <Tag color="success">已提及 ({detailResult.mention_count}次)</Tag>
                : <Tag color="error">未提及</Tag>}
            </Col>
            <Col span={6}>
              <Text type="secondary">情感：</Text>
              <SentimentTag
                sentiment={detailResult.sentiment}
                positiveMentions={detailResult.positive_mentions}
                negativeMentions={detailResult.negative_mentions}
              />
            </Col>
          </Row>
          <Divider />
          <div style={{ fontSize: 13, lineHeight: 1.8 }}>
            <Text type="secondary">提及位置：{detailResult.mention_position || '无'}</Text>
          </div>
          {detailResult.content_snippet && (
            <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-tertiary)', borderRadius: 6, fontSize: 13 }}>
              <Text type="secondary">内容摘要：</Text>
              <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{detailResult.content_snippet}</div>
            </div>
          )}
          {detailResult.full_response && (
            <Collapse style={{ marginTop: 12 }} ghost>
              <Panel header="查看完整AI回复" key="full-detail">
                <div style={{
                  fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap',
                  maxHeight: 400, overflow: 'auto', padding: 12, background: 'var(--bg-tertiary)', borderRadius: 6,
                }}>
                  {detailResult.full_response}
                </div>
              </Panel>
            </Collapse>
          )}
          {!detailResult.is_mentioned && detailResult.diagnosis && (
            <div style={{ marginTop: 12 }}>
              <DiagnosisAlert diagnosisStr={detailResult.diagnosis} />
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default VerifyPage;
