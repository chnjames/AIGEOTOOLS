import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { Card, Row, Col, Button, Space, Empty, Spin, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  RiseOutlined, ThunderboltOutlined, BarChartOutlined, SettingOutlined,
  ArrowRightOutlined, RightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { reportsApi, ApiCallRecord } from '@/api/reports';
import { keywordsApi } from '@/api/keywords';
import { articlesApi } from '@/api/articles';
import { workflowsApi } from '@/api/workflows';
import { useAppStore } from '@/stores';
import type { KPIData, Keyword, Article } from '@/types';
import { formatDateTime } from '@/utils/dateFormat';

// ============ 类型定义 ============

type TaskPriority = 'high' | 'medium' | 'low' | 'done';

interface DashboardTask {
  id: string;
  priority: TaskPriority;
  title: string;
  desc?: string;
  actionLabel: string;
  path: string;
}

interface ActivityItem {
  id: string;
  text: string;
  time: string;
  rawTime?: string;
}

// ============ 辅助函数 ============

/** 品牌可见度语义标签 */
function getVisibilityBadge(rate: number): { label: string; color: string } {
  if (rate <= 0) return { label: '待启动', color: 'var(--text-tertiary)' };
  if (rate < 0.3) return { label: 'Poor', color: 'var(--error)' };
  if (rate < 0.6) return { label: 'Emerging', color: 'var(--warning)' };
  return { label: 'Good', color: 'var(--success)' };
}

/** 操作类型 → 中文标签 */
const OP_LABELS: Record<string, string> = {
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

/** 相对时间格式化 */
function relativeTime(dateStr?: string): string {
  if (!dateStr) return '';
  const now = Date.now();
  const t = new Date(dateStr).getTime();
  const diff = Math.max(0, now - t);
  const min = Math.floor(diff / 60000);
  if (min < 1) return '刚刚';
  if (min < 60) return `${min}分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}小时前`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}天前`;
  return formatDateTime(dateStr).split(' ')[0];
}

// ============ 主组件 ============

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { config } = useAppStore();
  const [kpi, setKpi] = useState<KPIData | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [tasks, setTasks] = useState<DashboardTask[]>([]);
  const [loading, setLoading] = useState(false);

  const configOk = config?.gen_api_key_configured && (config?.verify_providers?.length ?? 0) > 0;

  // 配置完成度
  const configProgress = useMemo(() => {
    if (!config) return 0;
    const checks = [
      config.gen_api_key_configured,
      (config.verify_providers?.length ?? 0) > 0,
      !!config.brand,
      config.verify_keys_configured ? Object.keys(config.verify_keys_configured).length > 0 : false,
    ];
    return Math.round((checks.filter(Boolean).length / checks.length) * 100);
  }, [config]);

  // 加载所有数据
  const loadAll = useCallback(async () => {
    setLoading(true);
    const brand = config?.brand || '';
    try {
      // 并行请求:KPI + 活动流
      const [kpiData, apiCallsResp] = await Promise.all([
        reportsApi.kpi(brand).catch(() => null),
        reportsApi.apiCalls({ brand, page: 1, page_size: 8 }).catch(() => null),
      ]);
      if (kpiData) setKpi(kpiData);

      // 活动流
      if (apiCallsResp?.items?.length) {
        setActivities(apiCallsResp.items.map((r: ApiCallRecord) => ({
          id: String(r.id),
          text: `${OP_LABELS[r.operation_type] || r.operation_type}${r.keyword ? ` · ${r.keyword}` : ''}`,
          time: relativeTime(r.created_at),
          rawTime: r.created_at,
        })));
      } else {
        setActivities([]);
      }

      // 任务清单(异步聚合,不阻塞主渲染)
      buildTasks(brand, kpiData).then(setTasks).catch(() => setTasks([]));
    } catch (err) {
      console.error('[Dashboard] 加载失败:', err);
    } finally {
      setLoading(false);
    }
  }, [config?.brand]);

  // 构建任务清单(前端聚合现有数据)
  const buildTasks = useCallback(async (brand: string, kpiData: KPIData | null): Promise<DashboardTask[]> => {
    const taskList: DashboardTask[] = [];

    // 高优先级:提及率低的关键词(从 mentions 报告的 top_mentioned_queries)
    try {
      const mention = await reportsApi.mentions(brand).catch(() => null);
      if (mention?.top_mentioned_queries?.length) {
        // top_mentioned_queries 结构未知,尝试提取低提及率项
        const queries = mention.top_mentioned_queries as Array<Record<string, unknown>>;
        const lowRateQueries = queries
          .filter(q => {
            const rate = typeof q.rate === 'number' ? q.rate : typeof q.mention_rate === 'number' ? q.mention_rate : null;
            return rate !== null && rate < 0.3;
          })
          .slice(0, 2);
        lowRateQueries.forEach((q, i) => {
          const kw = (q.keyword || q.query || q.term || '') as string;
          const rate = (typeof q.rate === 'number' ? q.rate : typeof q.mention_rate === 'number' ? q.mention_rate : 0) as number;
          taskList.push({
            id: `high-${i}`,
            priority: 'high',
            title: kw ? `“${kw}” 提及率仅 ${(rate * 100).toFixed(0)}%` : `关键词提及率偏低 (${(rate * 100).toFixed(0)}%)`,
            desc: 'AI 对话中品牌提及不足',
            actionLabel: '去优化',
            path: '/optimize',
          });
        });
      }
    } catch { /* ignore */ }

    // 中优先级:缺少 FAQ Schema 的文章
    try {
      // 用 KPI 数据判断未优化文章数(total_articles - total_optimizations)
      const noOptCount = kpiData && kpiData.total_articles > kpiData.total_optimizations
        ? kpiData.total_articles - kpiData.total_optimizations
        : 0;
      if (noOptCount > 0) {
        taskList.push({
          id: 'med-schema',
          priority: 'medium',
          title: `${noOptCount} 篇文章尚未优化`,
          desc: '缺少 E-E-A-T / Schema 结构化',
          actionLabel: '去修复',
          path: '/optimize',
        });
      }
    } catch { /* ignore */ }

    // 低优先级:未生成内容的关键词
    try {
      const kwResp = await keywordsApi.list({ brand, page: 1, page_size: 100 }).catch(() => null);
      const keywords = kwResp?.items || [];
      const artResp = await articlesApi.list({ brand, page: 1, page_size: 100 }).catch(() => null);
      const articleKeywords = new Set((artResp?.items || []).map((a: Article) => a.keyword).filter(Boolean));
      const noContentKws = keywords.filter((k: Keyword) => !articleKeywords.has(k.keyword)).slice(0, 3);
      if (noContentKws.length > 0) {
        taskList.push({
          id: 'low-nocontent',
          priority: 'low',
          title: `${noContentKws.length} 个关键词尚未生成内容`,
          desc: noContentKws.slice(0, 2).map(k => k.keyword).join('、') + (noContentKws.length > 2 ? '...' : ''),
          actionLabel: '去创建',
          path: '/articles',
        });
      }
    } catch { /* ignore */ }

    // 已完成:最近完成的工作流执行
    try {
      const wfResp = await workflowsApi.list(brand).catch(() => null);
      const workflows = wfResp || [];
      // 找最近启用的工作流作为"已完成"参考
      if (workflows.length > 0 && kpiData && kpiData.total_optimizations > 0) {
        const latest = workflows[0];
        taskList.push({
          id: 'done-wf',
          priority: 'done',
          title: `工作流“${latest.name}”已配置`,
          desc: latest.enabled ? '运行中' : '已就绪',
          actionLabel: '查看',
          path: '/workflows',
        });
      }
    } catch { /* ignore */ }

    return taskList;
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // ============ 派生数据 ============

  const mentionRate = kpi?.mention_rate ?? 0;
  const visibility = getVisibilityBadge(mentionRate);
  const isEmpty = !kpi || (kpi.total_keywords === 0 && kpi.total_articles === 0 && kpi.total_optimizations === 0 && mentionRate === 0);

  // 任务按优先级排序
  const sortedTasks = useMemo(() => {
    const order: Record<TaskPriority, number> = { high: 0, medium: 1, low: 2, done: 3 };
    return [...tasks].sort((a, b) => order[a.priority] - order[b.priority]);
  }, [tasks]);

  const priorityConfig: Record<TaskPriority, { dot: string; label: string; labelColor: string }> = {
    high: { dot: 'var(--error)', label: 'High', labelColor: 'var(--error)' },
    medium: { dot: 'var(--warning)', label: 'Med', labelColor: 'var(--warning)' },
    low: { dot: 'var(--text-tertiary)', label: 'Low', labelColor: 'var(--text-tertiary)' },
    done: { dot: 'var(--success)', label: 'Done', labelColor: 'var(--success)' },
  };

  // ============ 渲染 ============

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">GEO 智能内容优化平台</h2>
        <p className="page-desc">让您的品牌在 AI 对话中被提及 · 任务驱动的工作台</p>
      </div>

      {/* 配置引导条:仅在未就绪时显示 */}
      {!configOk && config && (
        <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '10px 16px' } }}>
          <Row align="middle" gutter={16}>
            <Col flex="auto">
              <Space>
                <SettingOutlined style={{ color: 'var(--warning)' }} />
                <span className="font-medium text-sm">配置完成度 {configProgress}%</span>
                <div style={{ width: 120, height: 6, background: 'var(--bg-hover)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${configProgress}%`, height: '100%', background: configProgress >= 75 ? 'var(--success)' : 'var(--warning)', borderRadius: 3 }} />
                </div>
              </Space>
            </Col>
            <Col>
              <Button type="primary" size="small" onClick={() => navigate('/settings')}>前往设置</Button>
            </Col>
          </Row>
        </Card>
      )}

      {loading && !kpi ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin tip="加载工作台数据..." />
        </div>
      ) : isEmpty ? (
        /* ========== 空状态:3 步引导 ========== */
        <EmptyStateGuide navigate={navigate} configOk={!!configOk} configProgress={configProgress} />
      ) : (
        <>
          {/* ========== 段 1:品牌 AI 可见度 Hero ========== */}
          <Card
            styles={{ body: { padding: '20px 24px' } }}
            style={{ marginBottom: 16, background: 'linear-gradient(135deg, var(--bg-info), var(--accent-50))' }}
          >
            <Row align="middle" gutter={[24, 16]}>
              <Col xs={24} sm={8} md={7}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                  <span style={{ fontSize: '2.5rem', fontWeight: 700, lineHeight: 1, color: visibility.color === 'var(--text-tertiary)' ? 'var(--text-tertiary)' : 'var(--text-primary)' }}>
                    {mentionRate > 0 ? (mentionRate * 100).toFixed(0) : '--'}
                  </span>
                  {mentionRate > 0 && <span style={{ fontSize: '1rem', color: 'var(--text-tertiary)' }}>%</span>}
                </div>
                <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>品牌 AI 可见度</span>
                  <span
                    style={{
                      fontSize: '0.7rem', fontWeight: 600, padding: '1px 8px', borderRadius: 4,
                      background: visibility.color === 'var(--text-tertiary)' ? 'var(--bg-hover)' : `${visibility.color}1a`,
                      color: visibility.color,
                    }}
                  >
                    {visibility.label}
                  </span>
                </div>
              </Col>
              <Col xs={24} sm={10} md={10}>
                <Row gutter={16}>
                  <Col span={8} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.4rem', fontWeight: 600 }}>{kpi?.total_keywords ?? 0}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>关键词</div>
                  </Col>
                  <Col span={8} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.4rem', fontWeight: 600 }}>{kpi?.total_articles ?? 0}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>内容包</div>
                  </Col>
                  <Col span={8} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.4rem', fontWeight: 600 }}>{kpi?.total_verifications ?? 0}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>验证次数</div>
                  </Col>
                </Row>
              </Col>
              <Col xs={24} sm={6} md={7} style={{ textAlign: 'right' }}>
                <Tooltip title="查看多模型验证详情">
                  <Button
                    type="text"
                    icon={<ArrowRightOutlined />}
                    onClick={() => navigate('/verify')}
                    style={{ color: 'var(--brand-500)' }}
                  >
                    查看验证详情
                  </Button>
                </Tooltip>
              </Col>
            </Row>
          </Card>

          {/* ========== 段 2:任务清单 + 活动流 ========== */}
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={16}>
              <Card
                title={<span className="font-medium">待优化任务</span>}
                extra={
                  <Button type="link" size="small" onClick={() => navigate('/workflows')}>
                    一键工作流
                  </Button>
                }
                styles={{ body: { padding: sortedTasks.length > 0 ? '8px 0' : '24px' } }}
              >
                {sortedTasks.length > 0 ? (
                  sortedTasks.map(task => {
                    const cfg = priorityConfig[task.priority];
                    return (
                      <div
                        key={task.id}
                        onClick={() => navigate(task.path)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px',
                          cursor: 'pointer', borderBottom: '1px solid var(--border-light)',
                          transition: 'background 0.2s',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                      >
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: cfg.dot, flexShrink: 0 }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="text-sm font-medium" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {task.priority === 'done' && <CheckCircleOutlined style={{ color: 'var(--success)', marginRight: 4 }} />}
                            {task.title}
                          </div>
                          {task.desc && (
                            <div className="text-xs" style={{ color: 'var(--text-tertiary)', marginTop: 2 }}>
                              {task.desc}
                            </div>
                          )}
                        </div>
                        <span
                          style={{
                            fontSize: '0.7rem', fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                            background: `${cfg.labelColor}1a`, color: cfg.labelColor, flexShrink: 0,
                          }}
                        >
                          {cfg.label}
                        </span>
                        <span className="text-xs" style={{ color: 'var(--brand-500)', flexShrink: 0 }}>
                          {task.actionLabel} <RightOutlined style={{ fontSize: 10 }} />
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无待办任务"
                    style={{ margin: '16px 0' }}
                  >
                    <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => navigate('/workflows')}>
                      运行工作流
                    </Button>
                  </Empty>
                )}
              </Card>
            </Col>

            <Col xs={24} lg={8}>
              <Card
                title={<span className="font-medium">最近活动</span>}
                styles={{ body: { padding: '8px 0', maxHeight: 360, overflow: 'auto' } }}
              >
                {activities.length > 0 ? (
                  activities.map((act, i) => (
                    <div
                      key={act.id}
                      style={{
                        display: 'flex', alignItems: 'flex-start', gap: 8, padding: '10px 20px',
                        borderBottom: i < activities.length - 1 ? '1px solid var(--border-light)' : 'none',
                      }}
                    >
                      <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--brand-500)', marginTop: 7, flexShrink: 0 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="text-sm" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {act.text}
                        </div>
                        <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          {act.time}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无活动记录"
                    style={{ margin: '16px 0' }}
                  />
                )}
              </Card>
            </Col>
          </Row>

          {/* ========== 段 3:快捷操作条 ========== */}
          <div className="mt-4" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span className="text-xs" style={{ color: 'var(--text-tertiary)', marginRight: 4 }}>快捷:</span>
            <QuickChip icon={<ThunderboltOutlined />} label="一键工作流" primary onClick={() => navigate('/workflows')} />
            <QuickChip icon={<BarChartOutlined />} label="查看报表" onClick={() => navigate('/reports')} />
            <QuickChip icon={<RiseOutlined />} label="ROI 归因" onClick={() => navigate('/analytics')} />
            <QuickChip icon={<SettingOutlined />} label="配置助手" onClick={() => navigate('/config-optimizer')} />
          </div>
        </>
      )}
    </div>
  );
};

// ============ 快捷 Chip 组件 ============

const QuickChip: React.FC<{
  icon: React.ReactNode;
  label: string;
  primary?: boolean;
  onClick: () => void;
}> = ({ icon, label, primary, onClick }) => (
  <button
    onClick={onClick}
    style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '4px 10px', borderRadius: 4, cursor: 'pointer',
      fontSize: '0.78rem', border: 'none', transition: 'all 0.2s',
      background: primary ? 'var(--brand-50)' : 'var(--bg-hover)',
      color: primary ? 'var(--brand-600)' : 'var(--text-secondary)',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.background = primary ? 'var(--brand-100)' : 'var(--border-light)';
    }}
    onMouseLeave={e => {
      e.currentTarget.style.background = primary ? 'var(--brand-50)' : 'var(--bg-hover)';
    }}
  >
    {icon} {label}
  </button>
);

// ============ 空状态引导组件 ==========

const EmptyStateGuide: React.FC<{
  navigate: (path: string) => void;
  configOk: boolean;
  configProgress: number;
}> = ({ navigate, configOk, configProgress }) => {
  const steps = [
    {
      n: 1,
      title: '配置 AI 密钥',
      desc: '连接 DeepSeek / OpenAI 等生成模型',
      done: configOk,
      action: '去配置',
      path: '/settings',
    },
    {
      n: 2,
      title: '蒸馏关键词',
      desc: 'AI 挖掘品牌相关搜索词',
      done: configOk && configProgress >= 75,
      action: configOk ? '去蒸馏' : '先完成步骤 1',
      path: '/keywords',
      locked: !configOk,
    },
    {
      n: 3,
      title: '一键工作流',
      desc: '自动创作 + 优化 + 验证',
      done: false,
      action: configOk ? '去执行' : '先完成步骤 2',
      path: '/workflows',
      locked: !configOk,
    },
  ];

  return (
    <Card styles={{ body: { padding: '40px 24px' } }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 8 }}>开始你的第一个 GEO 优化项目</h3>
        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>3 步完成配置,让品牌在 AI 对话中被提及</p>
      </div>
      <Row gutter={[16, 16]}>
        {steps.map(step => (
          <Col xs={24} sm={8} key={step.n}>
            <Card
              hoverable={!step.locked}
              onClick={() => !step.locked && navigate(step.path)}
              styles={{ body: { padding: 20, textAlign: 'center' } }}
              style={{
                opacity: step.locked ? 0.6 : 1,
                border: step.done ? '1px solid var(--success)' : '1px solid var(--border-light)',
                height: '100%',
              }}
            >
              <div style={{ marginBottom: 12 }}>
                {step.done ? (
                  <CheckCircleOutlined style={{ fontSize: 28, color: 'var(--success)' }} />
                ) : (
                  <div
                    style={{
                      width: 32, height: 32, borderRadius: '50%', margin: '0 auto',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: step.locked ? 'var(--bg-hover)' : 'var(--brand-50)',
                      color: step.locked ? 'var(--text-tertiary)' : 'var(--brand-500)',
                      fontSize: '0.9rem', fontWeight: 600,
                    }}
                  >
                    {step.n}
                  </div>
                )}
              </div>
              <div className="font-medium" style={{ marginBottom: 4 }}>{step.title}</div>
              <div className="text-xs" style={{ color: 'var(--text-tertiary)', marginBottom: 12 }}>{step.desc}</div>
              <Button
                type={step.done ? 'default' : 'primary'}
                size="small"
                disabled={step.locked}
                ghost={!step.done && !step.locked}
              >
                {step.done ? '已完成' : step.action}
              </Button>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
};

export default Dashboard;
