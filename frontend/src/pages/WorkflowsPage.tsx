import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Button, Space, Table, Tag, message, Row, Col, Typography,
  Modal, Form, Input, Select, Empty, Popconfirm, Divider, List, Progress, Collapse, Alert, InputNumber, Statistic
} from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined, DeleteOutlined, PlusOutlined,
  ReloadOutlined, HistoryOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, LoadingOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { workflowsApi } from '@/api/workflows';
import { articlesApi } from '@/api/articles';
import { StreamingText, PlatformSelector, ProgressBar } from '@/components';
import { useAppStore } from '@/stores';
import { CONTENT_PLATFORMS, KNOWN_CONTENT_PLATFORM_NAMES, DEFAULT_VERIFY_MODELS } from '@/constants';
import type { Workflow, WorkflowExecution, WorkflowStep, PlatformInfo, PlatformGroup } from '@/types';
import { formatDateTime } from '@/utils/dateFormat';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

/** 工作流模板（来自后端 /workflows/templates/list） */
interface WorkflowTemplate {
  name: string;
  steps: WorkflowStep[];
  description?: string;
}

/** 创建工作流表单值 */
interface CreateWorkflowFormValues {
  name: string;
  kw_count?: number;
  word_count?: number;
}

interface ExecSummary {
  keywords_generated?: number;
  articles_generated?: number;
  optimization_applied?: boolean;
  verification_passed?: number;
  verification_total?: number;
  verification_rate?: number;
  platforms?: string[];
}

interface FailedStep {
  step: string;
  error: string;
  error_type?: string;
}

interface StepStatus {
  name: string;
  status: 'pending' | 'running' | 'done' | 'error';
}

function parseExecResult(text: string): ExecSummary {
  const summary: ExecSummary = {};
  if (!text) return summary;

  // Try to extract keywords count
  const kwMatch = text.match(/(?:生成|产出|获取|共)\s*(\d+)\s*(?:个|条|项)?\s*关键词/);
  if (kwMatch) summary.keywords_generated = parseInt(kwMatch[1], 10);
  const kwMatch2 = text.match(/关键词[^\n]*?(\d+)\s*个/);
  if (!summary.keywords_generated && kwMatch2) summary.keywords_generated = parseInt(kwMatch2[1], 10);

  // Extract articles count
  const artMatch = text.match(/(?:生成|产出|撰写|创建|完成)\s*(\d+)\s*(?:篇|篇文章|篇内容|个文章)/);
  if (artMatch) summary.articles_generated = parseInt(artMatch[1], 10);
  const artMatch2 = text.match(/文章[^\n]*?(\d+)\s*篇/);
  if (!summary.articles_generated && artMatch2) summary.articles_generated = parseInt(artMatch2[1], 10);

  // Check optimization applied
  if (/优化(?:完成|成功|已应用|已完成|增强完成)|EEAT|eeat/.test(text)) {
    summary.optimization_applied = true;
  }

  // Extract verification results
  const verifyPassed = text.match(/(?:提及|通过|成功验证|positive|mentioned)\D{0,20}(\d+)\s*(?:次|个|条|篇|次提及)/);
  const verifyTotal = text.match(/(?:验证|查询|检测)\D{0,20}(\d+)\s*(?:次|个|条|个查询|篇)/);
  const rateMatch = text.match(/提及率[：:\s]*(\d+(?:\.\d+)?)\s*%/);

  if (verifyPassed) summary.verification_passed = parseInt(verifyPassed[1], 10);
  if (verifyTotal) summary.verification_total = parseInt(verifyTotal[1], 10);
  if (rateMatch) summary.verification_rate = parseFloat(rateMatch[1]);
  if (summary.verification_passed !== undefined && summary.verification_total && !summary.verification_rate) {
    summary.verification_rate = Math.round((summary.verification_passed / summary.verification_total) * 1000) / 10;
  }

  // Extract platforms mentioned
  const platformSet = new Set<string>();
  const knownPlatforms = KNOWN_CONTENT_PLATFORM_NAMES;
  knownPlatforms.forEach(p => {
    if (text.includes(p)) platformSet.add(p);
  });
  if (platformSet.size > 0) summary.platforms = Array.from(platformSet);

  // Fallback: if we couldn't parse anything, check for "完成" patterns
  if (summary.keywords_generated === undefined && summary.articles_generated === undefined) {
    const allNums = text.match(/(\d+)\s*(?:个|篇|条|次)/g);
    if (allNums) {
      // Look for context clues
      const kwSection = text.match(/关键词[\s\S]{0,200}/);
      const artSection = text.match(/(?:内容|文章|创作)[\s\S]{0,200}/);
      if (kwSection) {
        const n = kwSection[0].match(/(\d+)/);
        if (n) summary.keywords_generated = parseInt(n[1], 10);
      }
      if (artSection) {
        const n = artSection[0].match(/(\d+)/);
        if (n) summary.articles_generated = parseInt(n[1], 10);
      }
    }
  }

  return summary;
}

const WorkflowsPage: React.FC = () => {
  const { config } = useAppStore();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [execStreamKey, setExecStreamKey] = useState(0);
  const [execProgress, setExecProgress] = useState<{ percent: number; msg: string; logs: string[] }>({ percent: 0, msg: '', logs: [] });
  const [execResult, setExecResult] = useState('');
  const [execSummary, setExecSummary] = useState<ExecSummary | null>(null);
  const [failedSteps, setFailedSteps] = useState<FailedStep[]>([]);
  const [stepStatuses, setStepStatuses] = useState<StepStatus[]>([]);
  const [currentStepName, setCurrentStepName] = useState<string>('');
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [executionDetail, setExecutionDetail] = useState<WorkflowExecution | null>(null);

  // Platform selector state for create form
  const [availablePlatforms, setAvailablePlatforms] = useState<PlatformInfo[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [selectedVerifyModels, setSelectedVerifyModels] = useState<string[]>([]);

  const [createForm] = Form.useForm();

  const loadPlatforms = useCallback(async () => {
    try {
      const groups = await articlesApi.platformGroups();
      const flat: PlatformInfo[] = [];
      groups.forEach((g: PlatformGroup) => {
        if (g.platforms) {
          g.platforms.forEach((p: PlatformInfo) => flat.push(p));
        }
      });
      setAvailablePlatforms(flat);
    } catch (err) {
      console.warn('[WorkflowsPage] loadPlatforms failed, falling back to constants:', err);
      // Fallback platforms from constants
      setAvailablePlatforms(
        CONTENT_PLATFORMS.map(p => ({ ...p, publish_methods: [], icon: '' }))
      );
    }
  }, []);

  const loadWorkflows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await workflowsApi.list(config?.brand);
      setWorkflows(data);
    } catch (err) {
      console.error('[WorkflowsPage] loadWorkflows failed:', err);
      message.error('加载工作流失败');
    } finally {
      setLoading(false);
    }
  }, [config?.brand]);

  const loadTemplates = useCallback(async () => {
    try {
      const data = await workflowsApi.templates();
      setTemplates((data || []) as WorkflowTemplate[]);
    } catch (err) {
      console.error('[WorkflowsPage] 加载模板失败:', err);
    }
  }, []);

  useEffect(() => {
    loadWorkflows();
    loadTemplates();
    loadPlatforms();
  }, [loadWorkflows, loadTemplates, loadPlatforms]);

  useEffect(() => {
    if (config?.verify_providers) {
      setSelectedVerifyModels(config.verify_providers);
    }
  }, [config?.verify_providers]);

  const loadExecutions = async (workflowId: string) => {
    try {
      const data = await workflowsApi.executions(workflowId, { page_size: 20 });
      setExecutions(data.items);
    } catch (err) {
      console.error('[WorkflowsPage] 加载执行记录失败:', err);
    }
  };

  const handleToggle = async (wf: Workflow) => {
    await workflowsApi.toggle(wf.id, !wf.enabled);
    loadWorkflows();
    message.success(wf.enabled ? '已暂停' : '已启用');
  };

  const handleDelete = async (id: string) => {
    await workflowsApi.delete(id);
    message.success('已删除');
    loadWorkflows();
  };

  const handleCreate = async (values: CreateWorkflowFormValues) => {
    if (selectedPlatforms.length === 0) {
      message.warning('请选择至少一个目标平台');
      return;
    }
    const steps: WorkflowStep[] = [
      { step_type: 'generate_keywords', name: '关键词生成', config: { count: values.kw_count || 10 } },
      { step_type: 'generate_content', name: '内容创作', config: { platforms: selectedPlatforms, word_count: values.word_count || 800 } },
      { step_type: 'optimize', name: 'EEAT增强', config: { type: 'eeat' } },
      { step_type: 'verify', name: '多模型验证', config: { models: selectedVerifyModels.length > 0 ? selectedVerifyModels : (config?.verify_providers || []) } },
    ];
    try {
      await workflowsApi.create({ name: values.name, steps, brand: config?.brand });
      message.success('创建成功');
      setCreateModalVisible(false);
      createForm.resetFields();
      setSelectedPlatforms([]);
      setSelectedVerifyModels(config?.verify_providers || []);
      loadWorkflows();
    } catch (err) {
      console.error('[WorkflowsPage] handleCreate failed:', err);
      message.error('创建失败');
    }
  };

  const handleExecute = (wf: Workflow) => {
    setSelectedWorkflow(wf);
    setExecuting(true);
    setExecProgress({ percent: 0, msg: '准备执行...', logs: [] });
    setExecResult('');
    setExecSummary(null);
    setFailedSteps([]);
    const wfSteps = parseSteps(wf.steps);
    setStepStatuses(wfSteps.map(s => ({ name: s.name, status: 'pending' as const })));
    setCurrentStepName('');
    setExecStreamKey(k => k + 1);
  };

  const ERROR_TYPE_LABELS: Record<string, string> = {
    network_error: '网络连接错误，请检查网络后重试',
    api_error: 'API调用错误，请检查凭证配置',
    rate_limit: '请求频率超限，请稍后重试',
    timeout: '请求超时，请稍后重试',
    auth_error: '认证失败，请检查凭证是否有效',
    validation_error: '数据验证错误',
    content_policy: '内容触发安全策略，请调整输入',
    model_error: '模型处理错误，请重试',
    unknown: '未知错误',
  };

  const getClassifiedErrorMessage = (errorType: string | undefined, errorMsg: string) => {
    if (errorType && ERROR_TYPE_LABELS[errorType]) {
      return ERROR_TYPE_LABELS[errorType];
    }
    return errorMsg;
  };

  const onExecEvent = (event: string, data: Record<string, unknown>) => {
    if (event === 'progress') {
      const stepName = (data.step as string) || '';
      const msg = (data.message as string) || stepName || '';
      setExecProgress(prev => ({
        percent: (data.progress as number) ?? prev.percent,
        msg,
        logs: prev.logs,
      }));
      if (stepName && stepName !== currentStepName) {
        setCurrentStepName(stepName);
        setStepStatuses(prev => {
          const updated = prev.map(s => {
            if (s.name === stepName) return { ...s, status: 'running' as const };
            // Mark previous running steps as done when a new step starts
            if (s.status === 'running') return { ...s, status: 'done' as const };
            return s;
          });
          return updated;
        });
      }
    } else if (event === 'log' || event === 'chunk') {
      const msg = (data.message as string) || (data.content as string) || '';
      if (msg) {
        setExecProgress(prev => ({ ...prev, logs: [...prev.logs.slice(-100), msg] }));
      }
    } else if (event === 'step_start') {
      const stepName = (data.step as string) || (data.step_name as string) || '';
      if (stepName) {
        setCurrentStepName(stepName);
        setStepStatuses(prev => prev.map(s => {
          if (s.name === stepName) return { ...s, status: 'running' as const };
          if (s.status === 'running') return { ...s, status: 'done' as const };
          return s;
        }));
      }
    } else if (event === 'step_complete' || event === 'step_done') {
      const stepName = (data.step as string) || (data.step_name as string) || '';
      if (stepName) {
        setStepStatuses(prev => prev.map(s =>
          s.name === stepName ? { ...s, status: 'done' as const } : s
        ));
      }
    } else if (event === 'step_error') {
      const step = (data.step as string) || '未知步骤';
      const rawMsg = data.error as string || data.message as string || '步骤错误';
      const errorType = data.error_type as string | undefined;
      const msg = getClassifiedErrorMessage(errorType, rawMsg);
      setFailedSteps(prev => [...prev, { step, error: msg, error_type: errorType }]);
      setStepStatuses(prev => prev.map(s =>
        s.name === step ? { ...s, status: 'error' as const } : s
      ));
      setExecProgress(prev => ({ ...prev, logs: [...prev.logs.slice(-100), `[错误] ${step}: ${msg}`] }));
    }
  };

  const onExecComplete = (text: string) => {
    setExecuting(false);
    setExecProgress(prev => ({ ...prev, percent: 100, msg: '执行完成' }));
    setStepStatuses(prev => prev.map(s => s.status === 'running' || s.status === 'pending' ? { ...s, status: 'done' as const } : s));
    setExecResult(text);
    const summary = parseExecResult(text);
    setExecSummary(summary);
    loadWorkflows();
    if (selectedWorkflow) loadExecutions(selectedWorkflow.id);
  };

  const handleRetryStep = () => {
    if (selectedWorkflow) {
      setFailedSteps([]);
      handleExecute(selectedWorkflow);
    }
  };

  const parseSteps = (stepsStr: string): WorkflowStep[] => {
    try { return JSON.parse(stepsStr); } catch { return []; /* intentional fallback */ }
  };

  const renderExecSummary = (summary: ExecSummary) => {
    const hasAnyData = summary.keywords_generated !== undefined ||
      summary.articles_generated !== undefined ||
      summary.optimization_applied ||
      summary.verification_passed !== undefined;

    if (!hasAnyData) {
      return (
        <Alert
          type="success"
          message="执行完成"
          description="工作流已执行完毕，请查看下方日志了解详情。"
          showIcon
          style={{ marginBottom: 12 }}
        />
      );
    }

    return (
      <Card
        size="small"
        title={<Space><CheckCircleOutlined style={{ color: 'var(--success)' }} /><Text strong>执行结果摘要</Text></Space>}
        style={{ marginBottom: 12 }}
      >
        <Row gutter={[12, 12]}>
          {summary.keywords_generated !== undefined && (
            <Col span={12}>
              <Card size="small" style={{ background: 'var(--bg-success)', border: '1px solid var(--bg-success-border)' }}>
                <Statistic
                  title="关键词生成"
                  value={summary.keywords_generated}
                  suffix="个"
                  prefix={<Tag color="green">关键词</Tag>}
                  valueStyle={{ fontSize: 20 }}
                />
              </Card>
            </Col>
          )}
          {summary.articles_generated !== undefined && (
            <Col span={12}>
              <Card size="small" style={{ background: 'var(--bg-info)', border: '1px solid var(--bg-info-border)' }}>
                <Statistic
                  title="文章生成"
                  value={summary.articles_generated}
                  suffix="篇"
                  prefix={<Tag color="blue">内容</Tag>}
                  valueStyle={{ fontSize: 20 }}
                />
              </Card>
            </Col>
          )}
          {summary.optimization_applied !== undefined && (
            <Col span={12}>
              <Card size="small" style={{ background: 'var(--bg-warning)', border: '1px solid var(--bg-warning-border)' }}>
                <Space>
                  <CheckCircleOutlined style={{ color: 'var(--warning)', fontSize: 18 }} />
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>内容优化</div>
                    <Text strong style={{ color: 'var(--warning)' }}>EEAT增强已应用</Text>
                  </div>
                </Space>
              </Card>
            </Col>
          )}
          {summary.verification_total !== undefined && (
            <Col span={12}>
              <Card size="small" style={{ background: summary.verification_rate && summary.verification_rate >= 70 ? 'var(--bg-success)' : 'var(--bg-error)', border: `1px solid ${summary.verification_rate && summary.verification_rate >= 70 ? 'var(--bg-success-border)' : 'var(--bg-error-border)'}` }}>
                <Statistic
                  title="品牌验证"
                  value={summary.verification_rate ?? Math.round((summary.verification_passed! / summary.verification_total) * 100)}
                  suffix="%"
                  prefix={<Tag color={summary.verification_rate && summary.verification_rate >= 70 ? 'green' : 'red'}>验证</Tag>}
                  valueStyle={{ fontSize: 20, color: summary.verification_rate && summary.verification_rate >= 70 ? 'var(--success)' : 'var(--error)' }}
                />
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                  {summary.verification_passed}/{summary.verification_total} 次提及
                </div>
              </Card>
            </Col>
          )}
          {summary.platforms && summary.platforms.length > 0 && (
            <Col span={24}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>涉及平台：</Text>
                <Space size={4} wrap style={{ marginTop: 4 }}>
                  {summary.platforms.map(p => <Tag key={p} color="blue">{p}</Tag>)}
                </Space>
              </div>
            </Col>
          )}
        </Row>
      </Card>
    );
  };

  const columns: ColumnsType<Workflow> = [
    { title: 'ID', dataIndex: 'id', width: 280, ellipsis: true },
    { title: '名称', dataIndex: 'name', width: 150 },
    {
      title: '步骤', width: 300,
      render: (_, r) => {
        const steps = parseSteps(r.steps);
        return (
          <Space size={4} wrap>
            {steps.map((s, i) => (
              <Tag key={i} color="blue" style={{ fontSize: 11 }}>{s.name}</Tag>
            ))}
          </Space>
        );
      }
    },
    {
      title: '状态', dataIndex: 'enabled', width: 80,
      render: (e: boolean) => e ? <Tag color="green">启用</Tag> : <Tag>已暂停</Tag>,
    },
    { title: '更新时间', dataIndex: 'updated_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
    {
      title: '操作', width: 240,
      render: (_, r) => (
        <Space>
          <Button type="link" size="small" icon={<PlayCircleOutlined />} onClick={() => handleExecute(r)}>执行</Button>
          <Button type="link" size="small" icon={r.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />} onClick={() => handleToggle(r)}>
            {r.enabled ? '暂停' : '启用'}
          </Button>
          <Button type="link" size="small" icon={<HistoryOutlined />} onClick={() => { setSelectedWorkflow(r); loadExecutions(r.id); }}>
            记录
          </Button>
          <Popconfirm
            title={`确定删除工作流「${r.name}」？`}
            description="此工作流的所有执行记录将保留，但工作流本身将被删除。"
            onConfirm={() => handleDelete(r.id)}
            okText="确定删除"
            cancelText="取消"
          >
            <Button type="link" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const execColumns: ColumnsType<WorkflowExecution> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (s: string) => {
        const map: Record<string, { color: string; text: string }> = {
          running: { color: 'processing', text: '运行中' },
          completed: { color: 'success', text: '已完成' },
          failed: { color: 'error', text: '失败' },
          pending: { color: 'default', text: '等待中' },
        };
        const m = map[s] || { color: 'default', text: s };
        return <Tag color={m.color}>{m.text}</Tag>;
      }
    },
    {
      title: '进度', dataIndex: 'progress', width: 120,
      render: (p: number) => <Progress percent={Math.round(p)} size="small" status={p === 100 ? 'success' : 'active'} />
    },
    { title: '开始时间', dataIndex: 'started_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
    { title: '结束时间', dataIndex: 'completed_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
    {
      title: '错误', dataIndex: 'error', width: 120, ellipsis: true,
      render: (e: string) => e ? <Text type="danger">{e}</Text> : '-',
    },
  ];

  // Parse execution detail result for summary display
  const detailSummary = executionDetail?.result ? parseExecResult(executionDetail.result) : null;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">自动化工作流</h2>
        <p className="page-desc">关键词→创作→优化→验证 全流程自动化执行</p>
      </div>

      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card
            title="工作流列表"
            extra={
              <Space>
                <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
                  创建工作流
                </Button>
                <Button size="small" icon={<ReloadOutlined />} onClick={loadWorkflows}>刷新</Button>
              </Space>
            }
          >
            <Table
              columns={columns}
              dataSource={workflows}
              rowKey="id"
              loading={loading}
              size="small"
              pagination={false}
              locale={{
                emptyText: (
                  <Empty description="还没有创建任何工作流">
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
                      创建工作流
                    </Button>
                  </Empty>
                )
              }}
              scroll={{ x: 900 }}
            />
          </Card>

          {selectedWorkflow && executions.length > 0 && (
            <Card
              title={`执行记录 - ${selectedWorkflow.name}`}
              size="small"
              style={{ marginTop: 16 }}
              extra={<Button size="small" onClick={() => setSelectedWorkflow(null)}>关闭</Button>}
            >
              <Table
                columns={execColumns}
                dataSource={executions}
                rowKey="id"
                size="small"
                pagination={false}
                onRow={(record) => ({
                  onClick: () => setExecutionDetail(record),
                  style: { cursor: 'pointer' },
                })}
              />
            </Card>
          )}
        </Col>

        <Col xs={24} lg={10}>
          {executing || execResult ? (
            <Card title={`执行工作流：${selectedWorkflow?.name || ''}`} extra={
              !executing ? (
                <Button size="small" icon={<PlayCircleOutlined />} onClick={() => selectedWorkflow && handleExecute(selectedWorkflow)}>
                  重新执行
                </Button>
              ) : null
            }>
              {executing && (
                <>
                  <ProgressBar percent={execProgress.percent} status="active" message={execProgress.msg} logs={execProgress.logs} />
                  {stepStatuses.length > 0 && (
                    <div style={{ marginTop: 12, padding: '8px 12px', background: 'var(--bg-hover)', borderRadius: 6 }}>
                      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>执行步骤：</div>
                      <Space size={8} wrap>
                        {stepStatuses.map((s, i) => (
                          <Tag
                            key={i}
                            icon={
                              s.status === 'running' ? <LoadingOutlined spin /> :
                              s.status === 'done' ? <CheckCircleOutlined /> :
                              s.status === 'error' ? <CloseCircleOutlined /> :
                              <ClockCircleOutlined />
                            }
                            color={
                              s.status === 'running' ? 'processing' :
                              s.status === 'done' ? 'success' :
                              s.status === 'error' ? 'error' :
                              'default'
                            }
                            style={{ margin: 0, fontSize: 12 }}
                          >
                            {s.name}
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  )}
                </>
              )}

              {/* Failed steps retry section - show classified errors */}
              {failedSteps.length > 0 && !executing && (
                <Alert
                  type="error"
                  message="步骤执行失败"
                  description={
                    <div>
                      {failedSteps.map((fs, i) => (
                        <div key={i} style={{ marginBottom: i < failedSteps.length - 1 ? 4 : 8 }}>
                          <Space size={4} wrap>
                            <Tag color="red">{fs.step}</Tag>
                            {fs.error_type && (
                              <Tag color="orange" style={{ fontSize: 11 }}>
                                {ERROR_TYPE_LABELS[fs.error_type] ? fs.error_type : fs.error_type}
                              </Tag>
                            )}
                          </Space>
                          <div>
                            <Text type="danger" style={{ fontSize: 12 }}>{fs.error}</Text>
                          </div>
                        </div>
                      ))}
                      <Button
                        type="primary"
                        danger
                        size="small"
                        icon={<ReloadOutlined />}
                        onClick={handleRetryStep}
                        style={{ marginTop: 4 }}
                      >
                        重试执行
                      </Button>
                    </div>
                  }
                  style={{ marginBottom: 12 }}
                  showIcon
                />
              )}

              {/* Step status summary after completion */}
              {!executing && stepStatuses.length > 0 && (
                <div style={{ marginBottom: 12, padding: '8px 12px', background: 'var(--bg-hover)', borderRadius: 6 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>执行步骤：</div>
                  <Space size={8} wrap>
                    {stepStatuses.map((s, i) => (
                      <Tag
                        key={i}
                        icon={
                          s.status === 'error' ? <CloseCircleOutlined /> :
                          <CheckCircleOutlined />
                        }
                        color={s.status === 'error' ? 'error' : 'success'}
                        style={{ margin: 0, fontSize: 12 }}
                      >
                        {s.name}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}

              {/* Human-readable result summary */}
              {!executing && execSummary && renderExecSummary(execSummary)}

              <div style={{ marginTop: 12 }}>
                <StreamingText
                  key={`exec-${execStreamKey}`}
                  autoStart={executing}
                  fetchStream={(handlers) => {
                    if (!selectedWorkflow) return;
                    workflowsApi.executeStream(selectedWorkflow.id, {
                      brand: config?.brand,
                      advantages: config?.advantages,
                    }, {
                      ...handlers,
                      onEvent: (event, data) => {
                        handlers.onEvent?.(event, data);
                        onExecEvent(event, data);
                      },
                    });
                  }}
                  onComplete={onExecComplete}
                  height={executing ? 200 : 400}
                  placeholder="点击工作流的「执行」按钮开始"
                />
              </div>
            </Card>
          ) : templates.length > 0 ? (
            <Card title="内置模板">
              <List
                dataSource={templates}
                renderItem={(tpl: WorkflowTemplate) => (
                  <List.Item
                    actions={[
                      <Button
                        type="link"
                        size="small"
                        key="create"
                        onClick={async () => {
                          try {
                            await workflowsApi.create({
                              name: tpl.name,
                              steps: tpl.steps,
                              brand: config?.brand,
                            });
                            message.success(`已从模板创建：${tpl.name}`);
                            loadWorkflows();
                          } catch (err) { console.error('[WorkflowsPage] createFromTemplate failed:', err); message.error('创建失败'); }
                        }}
                      >
                        使用模板
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      title={tpl.name}
                      description={
                        <Space size={4} wrap>
                          {(tpl.steps || []).map((s: WorkflowStep, i: number) => (
                            <Tag key={i}>{s.name}</Tag>
                          ))}
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          ) : (
            <Card title="快速开始">
              <Paragraph type="secondary" style={{ fontSize: 13 }}>
                工作流可以自动化执行关键词生成、内容创作、优化和验证的完整流程。
              </Paragraph>
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Button type="primary" icon={<PlusOutlined />} size="large" onClick={() => setCreateModalVisible(true)}>
                  创建第一个工作流
                </Button>
              </div>
              <Collapse ghost size="small">
                <Panel header="工作流步骤说明" key="help">
                  <ul style={{ fontSize: 12, paddingLeft: 16, color: 'var(--text-secondary)' }}>
                    <li><Text strong>关键词生成</Text>：基于品牌和核心词自动生成长尾关键词</li>
                    <li><Text strong>内容创作</Text>：针对选定平台批量生成 GEO 优化内容</li>
                    <li><Text strong>内容优化</Text>：对生成内容进行 EEAT 增强提升</li>
                    <li><Text strong>品牌验证</Text>：多模型验证 AI 搜索中品牌是否被提及</li>
                  </ul>
                </Panel>
              </Collapse>
            </Card>
          )}
        </Col>
      </Row>

      <Modal
        title="创建工作流"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={560}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate} initialValues={{ kw_count: 10, word_count: 800 }}>
          <Form.Item label="工作流名称" name="name" rules={[{ required: true, message: '请输入工作流名称' }]}>
            <Input placeholder="例如：知乎内容全流程" />
          </Form.Item>

          <Form.Item label="关键词数量" name="kw_count">
            <Select options={[5, 10, 20, 30, 50].map(n => ({ label: `${n}个`, value: n }))} />
          </Form.Item>

          <Form.Item label="目标平台" required>
            <PlatformSelector
              platforms={availablePlatforms}
              selected={selectedPlatforms}
              onChange={setSelectedPlatforms}
              columns={3}
            />
          </Form.Item>

          <Form.Item label="每篇字数" name="word_count" extra="目标生成文章的字数">
            <InputNumber min={200} max={5000} step={100} style={{ width: 200 }} addonAfter="字" />
          </Form.Item>

          <Form.Item label="验证模型" extra="选择用于品牌提及验证的 AI 模型">
            <Select
              mode="multiple"
              placeholder="选择验证模型"
              value={selectedVerifyModels}
              onChange={setSelectedVerifyModels}
              style={{ width: '100%' }}
              options={(config?.verify_providers || DEFAULT_VERIFY_MODELS).map(m => ({
                label: m,
                value: m,
              }))}
            />
          </Form.Item>

          <Paragraph type="secondary" style={{ fontSize: 12 }}>
            将自动创建包含「关键词生成 → 内容创作 → EEAT优化 → 多模型验证」4个步骤的工作流。
          </Paragraph>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
            <Button type="primary" htmlType="submit">创建</Button>
          </Space>
        </Form>
      </Modal>

      <Modal
        title={`执行详情 #${executionDetail?.id}`}
        open={!!executionDetail}
        onCancel={() => setExecutionDetail(null)}
        width={600}
        footer={null}
      >
        {executionDetail && (
          <div>
            <Row gutter={16}>
              <Col span={12}><Text type="secondary">状态：</Text><Tag color={executionDetail.status === 'completed' ? 'green' : executionDetail.status === 'failed' ? 'red' : 'blue'}>{executionDetail.status}</Tag></Col>
              <Col span={12}><Text type="secondary">进度：</Text>{executionDetail.progress}%</Col>
            </Row>
            <Divider />
            {executionDetail.error && (
              <Alert type="error" message={executionDetail.error} style={{ marginBottom: 12 }} />
            )}
            {/* Summary for execution detail */}
            {detailSummary && executionDetail.status === 'completed' && renderExecSummary(detailSummary)}
            {executionDetail.logs && (
              <div>
                <Text strong style={{ fontSize: 13 }}>执行日志：</Text>
                <div style={{ background: 'var(--bg-tertiary)', borderRadius: 4, padding: 8, marginTop: 8, maxHeight: 300, overflow: 'auto', fontSize: 12, fontFamily: 'monospace' }}>
                  {executionDetail.logs.split('\n').map((line, i) => <div key={i}>{line}</div>)}
                </div>
              </div>
            )}
            {executionDetail.result && (
              <div style={{ marginTop: 12 }}>
                <Text strong style={{ fontSize: 13 }}>执行结果：</Text>
                <div style={{ background: 'var(--bg-success)', borderRadius: 4, padding: 8, marginTop: 8, fontSize: 12, whiteSpace: 'pre-wrap' }}>
                  {executionDetail.result}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default WorkflowsPage;
