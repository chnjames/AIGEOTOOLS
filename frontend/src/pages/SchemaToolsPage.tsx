import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Select, Slider, Button, Typography, Alert, Tag, Space, Spin, message, Progress } from 'antd';
import { CodeOutlined, CheckCircleOutlined, BulbOutlined, CopyOutlined } from '@ant-design/icons';
import { schemaApi, SchemaType, SchemaRecommend, SchemaValidateResult, SchemaGenerateResult } from '@/api/schema';

const { TextArea } = Input;
const { Paragraph, Text } = Typography;

const SchemaToolsPage: React.FC = () => {
  // ── Shared state ─────────────────────────────────────────────────────────
  const [types, setTypes] = useState<SchemaType[]>([]);
  const [typesLoading, setTypesLoading] = useState(false);

  useEffect(() => {
    setTypesLoading(true);
    schemaApi
      .listTypes()
      .then((data) => setTypes(data))
      .catch(() => message.error('加载 Schema 类型列表失败'))
      .finally(() => setTypesLoading(false));
  }, []);

  // ── Tab 1: Generate ─────────────────────────────────────────────────────
  const [genContent, setGenContent] = useState('');
  const [genType, setGenType] = useState<string | undefined>(undefined);
  const [genBrand, setGenBrand] = useState('');
  const [genTemp, setGenTemp] = useState(0.3);
  const [genLoading, setGenLoading] = useState(false);
  const [genResult, setGenResult] = useState<SchemaGenerateResult | null>(null);

  const handleGenerate = async () => {
    if (!genContent.trim()) {
      message.warning('请输入内容');
      return;
    }
    if (!genType) {
      message.warning('请选择 Schema 类型');
      return;
    }
    setGenLoading(true);
    setGenResult(null);
    try {
      const result = await schemaApi.generate({
        content: genContent,
        schema_type: genType,
        brand: genBrand || undefined,
        temperature: genTemp,
      });
      setGenResult(result);
      message.success('Schema 生成成功');
    } catch (err) {
      console.error('[SchemaToolsPage] handleGenerate failed:', err);
      message.error('Schema 生成失败，请重试');
    } finally {
      setGenLoading(false);
    }
  };

  const handleCopyJson = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => message.success('已复制到剪贴板'),
      () => message.error('复制失败')
    );
  };

  const formatJsonLd = (raw: Record<string, unknown> | string): string => {
    if (typeof raw === 'string') {
      try {
        return JSON.stringify(JSON.parse(raw), null, 2);
      } catch (err) {
        console.warn('[SchemaToolsPage] formatJsonLd JSON.parse failed, returning raw:', err);
        return raw;
      }
    }
    return JSON.stringify(raw, null, 2);
  };

  // ── Tab 2: Validate ─────────────────────────────────────────────────────
  const [valInput, setValInput] = useState('');
  const [valType, setValType] = useState<string | undefined>(undefined);
  const [valLoading, setValLoading] = useState(false);
  const [valResult, setValResult] = useState<SchemaValidateResult | null>(null);

  const handleValidate = async () => {
    if (!valInput.trim()) {
      message.warning('请输入 JSON-LD 代码');
      return;
    }
    setValLoading(true);
    setValResult(null);
    try {
      const result = await schemaApi.validate(valInput, valType || '');
      setValResult(result);
      if (result.valid) {
        message.success('验证通过');
      } else {
        message.warning(`发现 ${result.errors.length} 个错误`);
      }
    } catch (err) {
      console.error('[SchemaToolsPage] handleValidate failed:', err);
      message.error('验证失败，请检查 JSON-LD 格式是否正确');
    } finally {
      setValLoading(false);
    }
  };

  // ── Tab 3: Recommend ────────────────────────────────────────────────────
  const [recContent, setRecContent] = useState('');
  const [recLoading, setRecLoading] = useState(false);
  const [recResult, setRecResult] = useState<SchemaRecommend[] | null>(null);

  const handleRecommend = async () => {
    if (!recContent.trim()) {
      message.warning('请输入内容');
      return;
    }
    setRecLoading(true);
    setRecResult(null);
    try {
      const result = await schemaApi.recommend(recContent);
      setRecResult(result);
      message.success(`推荐了 ${result.length} 个 Schema 类型`);
    } catch (err) {
      console.error('[SchemaToolsPage] handleRecommend failed:', err);
      message.error('推荐失败，请重试');
    } finally {
      setRecLoading(false);
    }
  };

  // ── Styles ──────────────────────────────────────────────────────────────
  const codeBlockStyle: React.CSSProperties = {
    background: 'var(--bg-code)',
    color: 'var(--text-code)',
    padding: '16px',
    borderRadius: '6px',
    fontFamily: "'Fira Code', 'Consolas', 'Monaco', monospace",
    fontSize: '13px',
    lineHeight: '1.6',
    overflowX: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    maxHeight: '480px',
    overflowY: 'auto',
    margin: 0,
  };

  const tabItems = [
    // ── Tab 1 ───────────────────────────────────────────────────────────
    {
      key: 'generate',
      label: (
        <span>
          <CodeOutlined /> Schema 生成
        </span>
      ),
      children: (
        <Card bordered={false}>
          <Form layout="vertical">
            <Form.Item label="内容描述" required>
              <TextArea
                rows={8}
                placeholder="输入网页内容、产品描述、文章正文等，AI 将据此生成结构化数据..."
                value={genContent}
                onChange={(e) => setGenContent(e.target.value)}
              />
            </Form.Item>

            <Space style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }} align="start">
              <Form.Item label="Schema 类型" required style={{ minWidth: 280, marginBottom: 0 }}>
                <Select
                  placeholder="选择 Schema 类型"
                  value={genType}
                  onChange={setGenType}
                  loading={typesLoading}
                  showSearch
                  optionFilterProp="label"
                  options={types.map((t) => ({
                    value: t.type,
                    label: t.type,
                    desc: t.description,
                  }))}
                  optionRender={(opt) => (
                    <div>
                      <Text strong>{opt.data.value as string}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {opt.data.desc as string}
                      </Text>
                    </div>
                  )}
                />
              </Form.Item>

              <Form.Item label="品牌（可选）" style={{ minWidth: 200, marginBottom: 0 }}>
                <Input
                  placeholder="如：MyBrand"
                  value={genBrand}
                  onChange={(e) => setGenBrand(e.target.value)}
                />
              </Form.Item>
            </Space>

            <Form.Item label="温度（创造性）" style={{ marginTop: 16 }}>
              <div style={{ paddingRight: 16 }}>
                <Slider
                  min={0}
                  max={1}
                  step={0.1}
                  value={genTemp}
                  onChange={setGenTemp}
                  marks={{
                    0: '精准',
                    0.3: '0.3',
                    0.5: '平衡',
                    0.7: '0.7',
                    1: '创意',
                  }}
                />
              </div>
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                size="large"
                loading={genLoading}
                onClick={handleGenerate}
                icon={<CodeOutlined />}
              >
                生成 Schema
              </Button>
            </Form.Item>
          </Form>

          {genLoading && (
            <div style={{ textAlign: 'center', padding: 32 }}>
              <Spin tip="正在生成 Schema..." size="large" />
            </div>
          )}

          {genResult && !genLoading && (
            <div style={{ marginTop: 8 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 12,
                }}
              >
                <Space>
                  <Tag color="blue">{genResult.schema_type}</Tag>
                  <Text type="secondary">JSON-LD 结构化数据</Text>
                </Space>
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() =>
                    handleCopyJson(formatJsonLd(genResult.json_ld_raw ?? genResult.json_ld))
                  }
                >
                  复制
                </Button>
              </div>
              <pre style={codeBlockStyle}>
                {formatJsonLd(genResult.json_ld_raw ?? genResult.json_ld)}
              </pre>
            </div>
          )}
        </Card>
      ),
    },

    // ── Tab 2 ───────────────────────────────────────────────────────────
    {
      key: 'validate',
      label: (
        <span>
          <CheckCircleOutlined /> Schema 验证
        </span>
      ),
      children: (
        <Card bordered={false}>
          <Form layout="vertical">
            <Form.Item label="JSON-LD 代码" required>
              <TextArea
                rows={10}
                placeholder="粘贴 JSON-LD 代码..."
                value={valInput}
                onChange={(e) => setValInput(e.target.value)}
                style={{
                  fontFamily: "'Fira Code', 'Consolas', 'Monaco', monospace",
                  fontSize: 13,
                }}
              />
            </Form.Item>

            <Space style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }} align="start">
              <Form.Item label="Schema 类型提示（可选）" style={{ minWidth: 280, marginBottom: 0 }}>
                <Select
                  placeholder="可指定 Schema 类型以获得更精确的验证"
                  value={valType}
                  onChange={setValType}
                  allowClear
                  loading={typesLoading}
                  showSearch
                  optionFilterProp="label"
                  options={types.map((t) => ({
                    value: t.type,
                    label: t.type,
                  }))}
                />
              </Form.Item>
            </Space>

            <Form.Item style={{ marginTop: 16 }}>
              <Button
                type="primary"
                size="large"
                loading={valLoading}
                onClick={handleValidate}
                icon={<CheckCircleOutlined />}
              >
                验证
              </Button>
            </Form.Item>
          </Form>

          {valLoading && (
            <div style={{ textAlign: 'center', padding: 32 }}>
              <Spin tip="正在验证..." size="large" />
            </div>
          )}

          {valResult && !valLoading && (
            <div style={{ marginTop: 8 }}>
              {valResult.valid ? (
                <Alert
                  type="success"
                  message="Schema 验证通过"
                  showIcon
                  icon={<CheckCircleOutlined />}
                  style={{ marginBottom: 16 }}
                />
              ) : (
                <Alert
                  type="error"
                  message="Schema 存在问题"
                  description={`共发现 ${valResult.errors.length} 个错误，${valResult.warnings.length} 个警告`}
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              {valResult.detected_type && (
                <Paragraph style={{ marginBottom: 12 }}>
                  <Text strong>检测到类型：</Text>
                  <Tag color="blue">{valResult.detected_type}</Tag>
                </Paragraph>
              )}

              <div style={{ marginBottom: 20 }}>
                <Text strong>
                  评分：{valResult.score} 分
                </Text>
                <Progress
                  percent={valResult.score}
                  status={
                    valResult.score >= 90
                      ? 'success'
                      : valResult.score >= 60
                      ? 'active'
                      : 'exception'
                  }
                  style={{ marginTop: 8 }}
                />
              </div>

              {valResult.errors.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ color: 'var(--error)' }}>
                    错误（{valResult.errors.length}）
                  </Text>
                  <ul style={{ paddingLeft: 20, marginTop: 8 }}>
                    {valResult.errors.map((err, idx) => (
                      <li key={idx} style={{ color: 'var(--error)', marginBottom: 4 }}>
                        {err}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {valResult.warnings.length > 0 && (
                <div>
                  <Text strong style={{ color: 'var(--warning)' }}>
                    警告（{valResult.warnings.length}）
                  </Text>
                  <ul style={{ paddingLeft: 20, marginTop: 8 }}>
                    {valResult.warnings.map((warn, idx) => (
                      <li key={idx} style={{ color: 'var(--warning)', marginBottom: 4 }}>
                        {warn}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>
      ),
    },

    // ── Tab 3 ───────────────────────────────────────────────────────────
    {
      key: 'recommend',
      label: (
        <span>
          <BulbOutlined /> 类型推荐
        </span>
      ),
      children: (
        <Card bordered={false}>
          <Form layout="vertical">
            <Form.Item label="内容描述" required>
              <TextArea
                rows={6}
                placeholder="输入网页内容或业务描述，AI 将推荐最适合的 Schema.org 类型..."
                value={recContent}
                onChange={(e) => setRecContent(e.target.value)}
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                size="large"
                loading={recLoading}
                onClick={handleRecommend}
                icon={<BulbOutlined />}
              >
                推荐 Schema 类型
              </Button>
            </Form.Item>
          </Form>

          {recLoading && (
            <div style={{ textAlign: 'center', padding: 32 }}>
              <Spin tip="正在分析内容并推荐类型..." size="large" />
            </div>
          )}

          {recResult && !recLoading && (
            <div style={{ marginTop: 8 }}>
              {recResult.length === 0 ? (
                <Alert type="info" message="未找到匹配的 Schema 类型，请尝试补充更多内容描述。" showIcon />
              ) : (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  {recResult.map((rec, idx) => {
                    const pct = Math.round(rec.confidence * 100);
                    return (
                      <Card
                        key={idx}
                        size="small"
                        style={{ borderLeft: '3px solid var(--brand-500)' }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12,
                            marginBottom: 8,
                            flexWrap: 'wrap',
                          }}
                        >
                          <Tag color="blue" style={{ fontSize: 14, padding: '2px 10px' }}>
                            {rec.type}
                          </Tag>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            置信度 {pct}%
                          </Text>
                          <div style={{ flex: 1, minWidth: 120 }}>
                            <Progress
                              percent={pct}
                              size="small"
                              status={pct >= 70 ? 'success' : pct >= 40 ? 'active' : 'normal'}
                              showInfo={false}
                            />
                          </div>
                        </div>
                        <Paragraph style={{ marginBottom: 0 }} type="secondary">
                          {rec.reason}
                        </Paragraph>
                      </Card>
                    );
                  })}
                </Space>
              )}
            </div>
          )}
        </Card>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">结构化数据 Schema 工具</h2>
        <p className="page-desc">生成、验证和推荐 Schema.org 结构化数据，提升搜索展示效果</p>
      </div>

      <Card bordered={false}>
        <Tabs
          defaultActiveKey="generate"
          items={tabItems}
          size="large"
          tabBarStyle={{ marginBottom: 24 }}
        />
      </Card>
    </div>
  );
};

export default SchemaToolsPage;
