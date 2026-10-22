import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card, Form, Input, InputNumber, Button, Space, Row, Col, message,
  Select, Tabs, Tag, Alert, Spin, Empty, Collapse, Typography, Divider, Switch, Popconfirm, Tooltip
} from 'antd';
import {
  ThunderboltOutlined, CheckCircleOutlined, SafetyOutlined,
  CodeOutlined, FileSearchOutlined, BarChartOutlined, ReloadOutlined,
  AimOutlined, UndoOutlined
} from '@ant-design/icons';
import type { SelectProps } from 'antd';
import { optimizationsApi } from '@/api/optimizations';
import { articlesApi } from '@/api/articles';
import { scoringApi } from '@/api/scoring';
import { StreamingText, TotalScoreGauge, ScoreBar } from '@/components';
import { useAppStore } from '@/stores';
import { getErrorMessage } from '@/constants';
import type { ScoreResult, ContentMetrics, Article } from '@/types';

const { Title: AntTitle, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

const OPTIMIZE_STEP_TIPS: Record<string, string> = {
  eeat: '正在优化内容（EEAT增强/权威性提升/可信度强化）...',
  fact: '正在优化内容（事实密度提升/数据补充/引用增强）...',
};

const OptimizePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { config } = useAppStore();
  const [activeTab, setActiveTab] = useState('eeat');
  const [content, setContent] = useState('');
  const [useKnowledge, setUseKnowledge] = useState(false);
  const [pendingNotice, setPendingNotice] = useState<string | null>(null);
  const [streamKey, setStreamKey] = useState(0);
  const [streaming, setStreaming] = useState(false);
  const [optimizedContent, setOptimizedContent] = useState('');
  const [scoring, setScoring] = useState(false);
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null);
  const [metrics, setMetrics] = useState<ContentMetrics | null>(null);
  const [quickScore, setQuickScore] = useState<{ has_title: boolean; has_list: boolean; has_faq: boolean; brand_count: number; word_count: number; quick_score: number } | null>(null);
  const [schemaResult, setSchemaResult] = useState<{ json_ld: string; schema_type: string } | null>(null);
  const [techConfig, setTechConfig] = useState<{ robots_txt: string; sitemap_xml: string; meta_tags: string; structured_data: string } | null>(null);
  const [uniquenessResult, setUniquenessResult] = useState<{ uniqueness_score: number; duplicate_segments: string[]; suggestions: string[] } | null>(null);
  const [techniques, setTechniques] = useState<Array<{ name: string; category: string; description: string; example: string }>>([]);
  const [analyzingMetrics, setAnalyzingMetrics] = useState(false);

  // Article search state
  const [articleOptions, setArticleOptions] = useState<SelectProps['options']>([]);
  const [searchingArticles, setSearchingArticles] = useState(false);
  const [selectedArticleId, setSelectedArticleId] = useState<number | null>(null);
  const [restoringOriginal, setRestoringOriginal] = useState(false);

  // Streaming state
  const [injectionWarnings, setInjectionWarnings] = useState<Array<{ field: string; warning: string }>>([]);
  const [optimizeError, setOptimizeError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);

  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [eeatForm] = Form.useForm();
  const [factForm] = Form.useForm();
  const [schemaForm] = Form.useForm();
  const [techForm] = Form.useForm();

  useEffect(() => {
    optimizationsApi.techniques().then(setTechniques).catch(() => {});
    // 读取从文章页跳转过来的待优化内容
    // 优先读取 URL 查询参数 article_id（新版跳转），再通过 API 获取文章内容；
    // 兼容旧版 sessionStorage 跳转方式
    const articleIdParam = searchParams.get('article_id');
    const platformParam = searchParams.get('platform');
    if (articleIdParam) {
      const aid = Number(articleIdParam);
      if (!isNaN(aid) && aid > 0) {
        setSelectedArticleId(aid);
        articlesApi.get(aid).then(article => {
          if (article.content) {
            setContent(article.content);
            setMetrics(null);
            setQuickScore(null);
            const plat = platformParam || article.platform;
            setPendingNotice(plat ? `已载入来自「${plat}」的文章内容` : '已载入待优化内容');
          }
        }).catch(err => {
          console.error('[OptimizePage] 加载文章失败:', err);
          message.error('加载文章内容失败');
        });
      }
    } else {
      // 兼容旧版 sessionStorage 跳转
      const pending = sessionStorage.getItem('pending_content');
      const pendingPlatform = sessionStorage.getItem('pending_platform');
      if (pending) {
        setContent(pending);
        setPendingNotice(pendingPlatform ? `已载入来自「${pendingPlatform}」的文章内容` : '已载入待优化内容');
        sessionStorage.removeItem('pending_content');
        sessionStorage.removeItem('pending_platform');
        sessionStorage.removeItem('pending_article_id');
      }
    }
    if (config?.use_knowledge_base) {
      setUseKnowledge(true);
    }
  }, []);

  const hasConfig = config?.gen_api_key_configured;

  const handleArticleSearch = useCallback((value: string) => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    if (!value || value.length < 1) {
      setArticleOptions([]);
      return;
    }
    searchTimeoutRef.current = setTimeout(async () => {
      setSearchingArticles(true);
      try {
        const articles = await articlesApi.searchArticles(value, config?.brand, 20);
        setArticleOptions(
          articles.map((a: Article) => ({
            label: `${a.keyword || '(无关键词)'} - ${a.platform || '未知平台'}`,
            value: a.id,
          }))
        );
      } catch (err) {
        console.error('[OptimizePage] searchArticles failed:', err);
      } finally {
        setSearchingArticles(false);
      }
    }, 300);
  }, [config?.brand]);

  const handleArticleSelect = useCallback(async (articleId: number) => {
    setSelectedArticleId(articleId);
    try {
      const result = await articlesApi.get(articleId);
      if (result.content) {
        setContent(result.content);
        setMetrics(null);
        setQuickScore(null);
        message.success(`已载入文章：${result.keyword || ''} - ${result.platform || ''}`);
      }
    } catch (err) {
      console.error('[OptimizePage] handleArticleSelect failed:', err);
      message.error('加载文章内容失败');
    }
  }, []);

  const handleRestoreOriginal = useCallback(async () => {
    if (!selectedArticleId) {
      message.warning('请先选择一篇文章');
      return;
    }
    setRestoringOriginal(true);
    try {
      const result = await articlesApi.getOriginalContent(selectedArticleId);
      setContent(result.content);
      setMetrics(null);
      setQuickScore(null);
      message.info('已还原为原文');
    } catch (err) {
      console.warn('[OptimizePage] articlesApi.getOriginalContent failed, falling back to optimizationsApi:', err);
      // fallback to optimizationsApi
      try {
        const result = await optimizationsApi.getOriginalContent(selectedArticleId);
        setContent(result.content);
        setMetrics(null);
        setQuickScore(null);
        message.info('已还原为原文');
      } catch (err2) {
        console.error('[OptimizePage] handleRestoreOriginal failed:', err2);
        message.error('还原原文失败');
      }
    } finally {
      setRestoringOriginal(false);
    }
  }, [selectedArticleId]);

  const startStream = (type: 'eeat' | 'fact' | 'score') => {
    if (!content || content.length < 50) {
      message.warning('请先输入需要优化的内容（至少50字）');
      return;
    }
    setStreaming(true);
    setOptimizedContent('');
    setOptimizeError(null);
    setInjectionWarnings([]);
    setCurrentStep(0);
    setTotalSteps(0);
    setStreamKey(k => k + 1);
    if (type === 'score') setScoreResult(null);
  };

  const onStreamComplete = (text: string) => {
    setStreaming(false);
    setOptimizedContent(text);
  };

  const handleAnalyzeMetrics = async () => {
    if (!content || content.length < 10) { message.warning('请输入内容'); return; }
    setAnalyzingMetrics(true);
    try {
      const [m, q] = await Promise.all([
        scoringApi.metrics(content, config?.brand),
        scoringApi.quick(content, config?.brand),
      ]);
      setMetrics(m);
      setQuickScore(q);
    } catch (err) {
      console.error('[OptimizePage] handleAnalyzeMetrics failed:', err);
      message.error('分析失败');
    } finally {
      setAnalyzingMetrics(false);
    }
  };

  const handleGenerateSchema = async () => {
    if (!content) { message.warning('请输入内容'); return; }
    const values = schemaForm.getFieldsValue();
    try {
      const res = await optimizationsApi.generateSchema({ content, schema_type: values.schema_type || 'Article', brand: config?.brand });
      setSchemaResult(res);
      message.success('Schema 生成成功');
    } catch (err) { console.error('[OptimizePage] handleGenerateSchema failed:', err); message.error('生成失败'); }
  };

  const handleTechConfig = async () => {
    const values = techForm.getFieldsValue();
    const keywords = (values.keywords as string || '').split(/[,，\n\s]+/).filter(Boolean);
    try {
      const res = await optimizationsApi.techConfig({
        brand: config?.brand,
        website_url: values.website_url,
        keywords,
        platforms: values.platforms ? [values.platforms] : undefined,
      });
      setTechConfig(res);
      message.success('技术配置生成成功');
    } catch (err) { console.error('[OptimizePage] handleTechConfig failed:', err); message.error('生成失败'); }
  };

  const handleCheckUniqueness = async () => {
    if (!content) { message.warning('请输入内容'); return; }
    try {
      const res = await optimizationsApi.checkUniqueness({ content });
      setUniquenessResult(res);
    } catch (err) { console.error('[OptimizePage] handleCheckUniqueness failed:', err); message.error('检测失败'); }
  };

  const handleScoreStream = (handlers: Parameters<typeof scoringApi.scoreStream>[1]) => {
    scoringApi.scoreStream({
      content,
      brand: config?.brand,
      advantages: config?.advantages,
    }, handlers);
  };

  const handleClear = () => {
    setContent('');
    setMetrics(null);
    setQuickScore(null);
    setSelectedArticleId(null);
    setOptimizedContent('');
    setSchemaResult(null);
    setUniquenessResult(null);
    setTechConfig(null);
    setInjectionWarnings([]);
    setOptimizeError(null);
  };

  const makeOptimizeStream = (type: 'eeat' | 'fact') => (handlers: Parameters<typeof optimizationsApi.eeatStream>[1]) => {
    const values = type === 'eeat' ? eeatForm.getFieldsValue() : factForm.getFieldsValue();
    const apiCall = type === 'eeat' ? optimizationsApi.eeatStream : optimizationsApi.factDensityStream;
    apiCall({
      content,
      brand: config?.brand,
      advantages: config?.advantages,
      temperature: values.temperature,
      use_knowledge: useKnowledge,
      article_id: selectedArticleId || undefined,
    }, {
      ...handlers,
      onStart: (data) => {
        handlers.onStart?.(data);
        if (data.warnings && Array.isArray(data.warnings) && data.warnings.length > 0) {
          setInjectionWarnings(data.warnings as Array<{ field: string; warning: string }>);
        }
        if (typeof data.total_steps === 'number') {
          setTotalSteps(data.total_steps as number);
        }
      },
      onProgress: (data) => {
        handlers.onProgress?.(data);
        if (typeof data.step === 'number') {
          setCurrentStep(data.step as number);
        }
        if (typeof data.total_steps === 'number') {
          setTotalSteps(data.total_steps as number);
        }
      },
      onError: (data) => {
        handlers.onError?.(data);
        setStreaming(false);
        const errMsg = getErrorMessage(
          data.error_type as string | undefined,
          (data.message as string) || (data.error as string)
        );
        setOptimizeError(errMsg);
      },
      onEvent: (event, data) => {
        handlers.onEvent?.(event, data);
      },
    });
  };

  const techniqueCategories = Array.from(new Set(techniques.map(t => t.category)));

  const showEmpty = !content && !streaming && !optimizedContent;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">内容优化</h2>
        <p className="page-desc">EEAT增强、事实密度提升、结构化数据生成、原创度检测</p>
      </div>

      {!hasConfig && (
        <Alert type="warning" showIcon message="请先在系统设置中配置 LLM API Key" style={{ marginBottom: 16 }} />
      )}

      {pendingNotice && (
        <Alert
          type="success" showIcon closable message={pendingNotice}
          onClose={() => setPendingNotice(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={16}>
        <Col xs={24} lg={10}>
          <Card title="输入内容" extra={
            <Space>
              <Button size="small" icon={<BarChartOutlined />} onClick={handleAnalyzeMetrics} loading={analyzingMetrics}>
                快速分析
              </Button>
              {selectedArticleId && (
                <Tooltip title="还原为文章原始内容">
                  <Button size="small" icon={<UndoOutlined />} onClick={handleRestoreOriginal} loading={restoringOriginal}>
                    还原原文
                  </Button>
                </Tooltip>
              )}
              <Popconfirm title="确定清空所有内容和结果？" onConfirm={handleClear} okText="确定" cancelText="取消">
                <Button size="small" icon={<ReloadOutlined />}>
                  清空
                </Button>
              </Popconfirm>
            </Space>
          }>
            {/* Article search selector */}
            <Form.Item label="从文章库选择" style={{ marginBottom: 12 }}>
              <Select
                showSearch
                placeholder="搜索关键词或平台以选择已有文章"
                filterOption={false}
                onSearch={handleArticleSearch}
                onSelect={handleArticleSelect}
                loading={searchingArticles}
                options={articleOptions}
                value={selectedArticleId || undefined}
                allowClear
                onClear={() => { setSelectedArticleId(null); setArticleOptions([]); }}
                style={{ width: '100%' }}
                notFoundContent={searchingArticles ? <Spin size="small" /> : '输入关键词搜索文章'}
              />
            </Form.Item>

            <TextArea
              value={content}
              onChange={e => setContent(e.target.value)}
              placeholder="粘贴需要优化的文章内容，或从上方文章库选择已有文章..."
              rows={16}
              style={{ fontSize: 13 }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'right' }}>
              {content.length} 字
            </div>

            {metrics && (
              <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-tertiary)', borderRadius: 6 }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>内容指标分析</div>
                <Row gutter={[8, 8]}>
                  <Col span={8}><Text type="secondary">字数：</Text><Text strong>{metrics.word_count}</Text></Col>
                  <Col span={8}><Text type="secondary">段落：</Text><Text strong>{metrics.paragraph_count}</Text></Col>
                  <Col span={8}><Text type="secondary">标题：</Text><Text strong>{metrics.heading_count}</Text></Col>
                  <Col span={8}><Text type="secondary">列表：</Text><Text strong>{metrics.list_count}</Text></Col>
                  <Col span={8}><Text type="secondary">品牌提及：</Text><Text strong>{metrics.brand_count}次</Text></Col>
                  <Col span={8}><Text type="secondary">可读性：</Text><Text strong>{metrics.readability_score.toFixed(1)}</Text></Col>
                  <Col span={8}><Text type="secondary">FAQ：</Text>{metrics.has_faq ? <Tag color="green">有</Tag> : <Tag>无</Tag>}</Col>
                  <Col span={8}><Text type="secondary">引用：</Text>{metrics.has_citations ? <Tag color="green">有</Tag> : <Tag>无</Tag>}</Col>
                  <Col span={8}><Text type="secondary">段落均长：</Text><Text strong>{Math.round(metrics.avg_paragraph_length)}字</Text></Col>
                </Row>
                {quickScore && (
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border-default)' }}>
                    <Text type="secondary">快速评分：</Text>
                    <Text strong style={{ color: quickScore.quick_score >= 70 ? 'var(--success)' : 'var(--warning)', fontSize: 16 }}>
                      {quickScore.quick_score}分
                    </Text>
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card title="优化操作" style={{ marginTop: 16 }}>
            <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
              {
                key: 'eeat',
                label: <span><SafetyOutlined />EEAT增强</span>,
                children: (
                  <Form form={eeatForm} layout="vertical" initialValues={{ temperature: 0.5 }}>
                    <Paragraph type="secondary" style={{ fontSize: 12 }}>
                      提升内容的经验性、专业性、权威性和可信度（Experience, Expertise, Authoritativeness, Trustworthiness）
                    </Paragraph>
                    {config?.use_knowledge_base && (
                      <Form.Item label="知识库增强" extra="启用后将检索知识库相关内容注入优化过程">
                        <Switch checked={useKnowledge} onChange={setUseKnowledge} checkedChildren="开启" unCheckedChildren="关闭" />
                      </Form.Item>
                    )}
                    <Form.Item label="温度" name="temperature">
                      <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
                    </Form.Item>
                    <Button type="primary" icon={<ThunderboltOutlined />} block disabled={!hasConfig || !content} loading={streaming && activeTab === 'eeat'} onClick={() => startStream('eeat')}>
                      EEAT增强优化
                    </Button>
                  </Form>
                ),
              },
              {
                key: 'fact',
                label: <span><CheckCircleOutlined />事实密度</span>,
                children: (
                  <Form form={factForm} layout="vertical" initialValues={{ temperature: 0.5 }}>
                    <Paragraph type="secondary" style={{ fontSize: 12 }}>
                      在内容中补充数据、案例、研究引用等事实性信息，提升可引用性。未经验证的数据将标记为【⚠️待验证来源】
                    </Paragraph>
                    {config?.use_knowledge_base && (
                      <Form.Item label="知识库增强" extra="启用后将优先使用知识库中的数据">
                        <Switch checked={useKnowledge} onChange={setUseKnowledge} checkedChildren="开启" unCheckedChildren="关闭" />
                      </Form.Item>
                    )}
                    <Form.Item label="温度" name="temperature">
                      <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
                    </Form.Item>
                    <Button type="primary" icon={<ThunderboltOutlined />} block disabled={!hasConfig || !content} loading={streaming && activeTab === 'fact'} onClick={() => startStream('fact')}>
                      提升事实密度
                    </Button>
                  </Form>
                ),
              },
              {
                key: 'schema',
                label: <span><CodeOutlined />结构化数据</span>,
                children: (
                  <Form form={schemaForm} layout="vertical" initialValues={{ schema_type: 'Article' }}>
                    <Form.Item label="Schema类型" name="schema_type">
                      <Select options={[
                        { label: 'Article（文章）', value: 'Article' },
                        { label: 'FAQPage（常见问题）', value: 'FAQPage' },
                        { label: 'HowTo（教程）', value: 'HowTo' },
                        { label: 'Product（产品）', value: 'Product' },
                        { label: 'Review（评价）', value: 'Review' },
                        { label: 'Organization（组织）', value: 'Organization' },
                      ]} />
                    </Form.Item>
                    <Button type="primary" icon={<CodeOutlined />} block disabled={!content} onClick={handleGenerateSchema}>
                      生成 JSON-LD
                    </Button>
                    {schemaResult && (
                      <div style={{ marginTop: 12 }}>
                        <div style={{ marginBottom: 4, fontSize: 12, color: 'var(--text-secondary)' }}>Schema类型: {schemaResult.schema_type}</div>
                        <Input.TextArea value={schemaResult.json_ld} rows={8} readOnly style={{ fontFamily: 'monospace', fontSize: 12 }} />
                        <Button size="small" style={{ marginTop: 8 }} onClick={() => { navigator.clipboard.writeText(schemaResult.json_ld); message.success('已复制'); }}>复制代码</Button>
                      </div>
                    )}
                  </Form>
                ),
              },
              {
                key: 'tech',
                label: <span><FileSearchOutlined />技术配置</span>,
                children: (
                  <Form form={techForm} layout="vertical">
                    <Paragraph type="secondary" style={{ fontSize: 12 }}>
                      生成 robots.txt、sitemap.xml、meta标签等 GEO 技术 SEO 配置
                    </Paragraph>
                    <Form.Item label="网站URL" name="website_url">
                      <Input placeholder="https://example.com" />
                    </Form.Item>
                    <Form.Item label="核心关键词（逗号分隔）" name="keywords">
                      <Input placeholder="关键词1,关键词2" />
                    </Form.Item>
                    <Button type="primary" icon={<FileSearchOutlined />} block onClick={handleTechConfig}>
                      生成技术配置
                    </Button>
                    {techConfig && (
                      <Collapse style={{ marginTop: 12 }}>
                        <Panel header="robots.txt" key="robots"><pre style={{ fontSize: 11, margin: 0 }}>{techConfig.robots_txt}</pre></Panel>
                        <Panel header="sitemap.xml" key="sitemap"><pre style={{ fontSize: 11, margin: 0 }}>{techConfig.sitemap_xml}</pre></Panel>
                        <Panel header="Meta 标签" key="meta"><pre style={{ fontSize: 11, margin: 0 }}>{techConfig.meta_tags}</pre></Panel>
                        <Panel header="结构化数据" key="sd"><pre style={{ fontSize: 11, margin: 0, whiteSpace: 'pre-wrap' }}>{techConfig.structured_data}</pre></Panel>
                      </Collapse>
                    )}
                  </Form>
                ),
              },
              {
                key: 'uniqueness',
                label: <span><BarChartOutlined />原创度检测</span>,
                children: (
                  <div>
                    <Paragraph type="secondary" style={{ fontSize: 12 }}>
                      检测内容中的重复段落，给出改进建议
                    </Paragraph>
                    <Button type="primary" icon={<BarChartOutlined />} block disabled={!content} onClick={handleCheckUniqueness}>
                      开始检测
                    </Button>
                    {uniquenessResult && (
                      <div style={{ marginTop: 12 }}>
                        <div style={{ textAlign: 'center', marginBottom: 12 }}>
                          <Text style={{ fontSize: 13 }}>原创度评分：</Text>
                          <Text strong style={{ fontSize: 24, color: uniquenessResult.uniqueness_score >= 80 ? 'var(--success)' : uniquenessResult.uniqueness_score >= 60 ? 'var(--warning)' : 'var(--error)' }}>
                            {uniquenessResult.uniqueness_score}%
                          </Text>
                        </div>
                        {uniquenessResult.duplicate_segments.length > 0 && (
                          <div>
                            <Text type="warning" style={{ fontSize: 12 }}>疑似重复片段：</Text>
                            {uniquenessResult.duplicate_segments.map((seg, i) => (
                              <div key={i} style={{ padding: 8, background: 'var(--bg-warning)', borderRadius: 4, margin: '4px 0', fontSize: 12 }}>
                                {seg}
                              </div>
                            ))}
                          </div>
                        )}
                        {uniquenessResult.suggestions.length > 0 && (
                          <div style={{ marginTop: 8 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>改进建议：</Text>
                            <ul style={{ paddingLeft: 20, fontSize: 12, margin: '4px 0' }}>
                              {uniquenessResult.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ),
              },
            ]} />
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          {/* Optimization result area for EEAT / fact-density */}
          {(activeTab === 'eeat' || activeTab === 'fact') && (
            <Card
              title={activeTab === 'eeat' ? 'EEAT增强结果' : '事实密度增强结果'}
              extra={
                optimizedContent && !streaming ? (
                  <Button size="small" icon={<ThunderboltOutlined />} onClick={() => startStream(activeTab as 'eeat' | 'fact')}>重新优化</Button>
                ) : null
              }
              style={{ marginBottom: 16 }}
            >
              {/* Injection warnings */}
              {injectionWarnings.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  message="内容注入提示"
                  style={{ marginBottom: 12 }}
                  description={
                    <ul style={{ margin: '4px 0', paddingLeft: 20, fontSize: 12 }}>
                      {injectionWarnings.map((w, i) => (
                        <li key={i}><Text strong>{w.field}：</Text>{w.warning}</li>
                      ))}
                    </ul>
                  }
                />
              )}

              {/* Optimization error */}
              {optimizeError && (
                <Alert
                  type="error"
                  showIcon
                  message="优化失败"
                  description={optimizeError}
                  closable
                  onClose={() => setOptimizeError(null)}
                  style={{ marginBottom: 12 }}
                />
              )}

              {/* Loading state with Spin and tip */}
              {streaming && (
                <div style={{ textAlign: 'center', padding: '12px 0', marginBottom: 12 }}>
                  <Spin tip={OPTIMIZE_STEP_TIPS[activeTab] || '正在优化内容...'}>
                    <div style={{ minHeight: 40 }} />
                  </Spin>
                  {totalSteps > 0 && (
                    <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                      进度：{currentStep} / {totalSteps} 步
                    </div>
                  )}
                </div>
              )}

              {/* Streaming text */}
              {(streaming || optimizedContent) ? (
                <>
                  <StreamingText
                    key={`opt-${activeTab}-${streamKey}`}
                    autoStart={streaming}
                    fetchStream={makeOptimizeStream(activeTab as 'eeat' | 'fact')}
                    onComplete={onStreamComplete}
                    height={400}
                    placeholder="点击左侧优化按钮开始"
                  />
                  {optimizedContent && !streaming && (
                    <div style={{ marginTop: 12 }}>
                      <Space>
                        <Button onClick={() => { navigator.clipboard.writeText(optimizedContent); message.success('已复制优化后内容'); }}>复制结果</Button>
                        <Button
                          type="primary"
                          icon={<AimOutlined />}
                          onClick={() => {
                            // 优先通过 article_id 传递（来自文章库的已保存文章）；
                            // 否则回退到 sessionStorage 传递未保存的优化内容
                            if (selectedArticleId) {
                              navigate(`/verify?article_id=${selectedArticleId}`);
                            } else {
                              sessionStorage.setItem('pending_content', optimizedContent);
                              navigate('/verify');
                            }
                            message.success('已跳转到验证页面');
                          }}
                        >
                          发送到验证
                        </Button>
                      </Space>
                    </div>
                  )}
                </>
              ) : showEmpty ? (
                <Empty
                  description="输入内容或从文章生成页面选择文章进行优化"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  style={{ padding: '40px 0' }}
                >
                  <Button type="primary" icon={<FileSearchOutlined />} onClick={() => navigate('/articles')}>
                    选择文章
                  </Button>
                </Empty>
              ) : (
                <Text type="secondary">点击左侧优化按钮开始优化</Text>
              )}
            </Card>
          )}

          {/* Empty state for non-eeat/fact tabs when no content */}
          {(activeTab !== 'eeat' && activeTab !== 'fact') && !content && (
            <Card style={{ marginBottom: 16 }}>
              <Empty
                description="输入内容或从文章生成页面选择文章进行优化"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button type="primary" icon={<FileSearchOutlined />} onClick={() => navigate('/articles')}>
                  选择文章
                </Button>
              </Empty>
            </Card>
          )}

          <Card title="AI 综合评分" extra={
            <Button size="small" icon={<ThunderboltOutlined />} disabled={!hasConfig || !content} loading={scoring} onClick={() => { setScoring(true); setScoreResult(null); setStreamKey(k => k + 1); }}>
              {scoring ? '评分中...' : '开始AI评分'}
            </Button>
          } style={{ marginBottom: 16 }}>
            {scoreResult ? (
              <div>
                <Row gutter={16}>
                  <Col span={8}>
                    <TotalScoreGauge score={scoreResult.scores.total} label="综合得分" />
                  </Col>
                  <Col span={16}>
                    <div style={{ paddingTop: 16 }}>
                      <ScoreBar label="结构化" score={scoreResult.scores.structure} max={25} />
                      <ScoreBar label="品牌提及" score={scoreResult.scores.brand_mention} max={25} />
                      <ScoreBar label="权威性" score={scoreResult.scores.authority} max={25} />
                      <ScoreBar label="可引用性" score={scoreResult.scores.citations} max={25} />
                    </div>
                  </Col>
                </Row>
                <Divider />
                <Row gutter={16}>
                  <Col span={12}>
                    <AntTitle level={5} style={{ color: 'var(--success)' }}>优势</AntTitle>
                    <ul style={{ paddingLeft: 20, fontSize: 13 }}>
                      {scoreResult.strengths.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </Col>
                  <Col span={12}>
                    <AntTitle level={5} style={{ color: 'var(--warning)' }}>改进建议</AntTitle>
                    <ul style={{ paddingLeft: 20, fontSize: 13 }}>
                      {scoreResult.improvements.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </Col>
                </Row>
              </div>
            ) : (
              <StreamingText
                key={`score-${streamKey}`}
                autoStart={scoring}
                fetchStream={handleScoreStream}
                onComplete={(text) => {
                  setScoring(false);
                  try {
                    const jsonMatch = text.match(/\{[\s\S]*\}/);
                    if (jsonMatch) {
                      const parsed = JSON.parse(jsonMatch[0]);
                      setScoreResult(parsed);
                    }
                  } catch (err) {
                    console.warn('[OptimizePage] 解析评分结果失败:', err);
                  }
                }}
                height={200}
                placeholder="点击「开始AI评分」对内容进行四维度综合评估"
              />
            )}
          </Card>

          <Card title="GEO优化技术手册" size="small">
            {techniques.length ? (
              <Collapse>
                {techniqueCategories.map(cat => (
                  <Panel header={`${cat}（${techniques.filter(t => t.category === cat).length}项）`} key={cat}>
                    {techniques.filter(t => t.category === cat).map((t, i) => (
                      <div key={i} style={{ marginBottom: 12, padding: 8, background: 'var(--bg-hover)', borderRadius: 4 }}>
                        <Text strong style={{ fontSize: 13 }}>{t.name}</Text>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '4px 0' }}>{t.description}</div>
                        <div style={{ fontSize: 12, color: 'var(--brand-500)', fontStyle: 'italic' }}>示例：{t.example}</div>
                      </div>
                    ))}
                  </Panel>
                ))}
              </Collapse>
            ) : (
              <Empty description="加载中..." />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default OptimizePage;
