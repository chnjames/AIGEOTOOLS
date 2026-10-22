import React, { useState } from 'react';
import {
  Card, Button, Form, Input, InputNumber, Select, Space,
  Row, Col, Alert, Typography, Collapse
} from 'antd';
import { ThunderboltOutlined, SettingOutlined, BulbOutlined } from '@ant-design/icons';
import { reportsApi } from '@/api/reports';
import { StreamingText } from '@/components';
import { useAppStore } from '@/stores';
import { PROVIDER_LABELS, VERIFY_PROVIDER_KEYS } from '@/constants';

const { Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

const ConfigOptimizerPage: React.FC = () => {
  const { config } = useAppStore();
  const [form] = Form.useForm();
  const [streamKey, setStreamKey] = useState(0);
  const [streaming, setStreaming] = useState(false);
  const [result, setResult] = useState('');

  const hasConfig = config?.gen_api_key_configured;

  const startOptimize = () => {
    setStreaming(true);
    setResult('');
    setStreamKey(k => k + 1);
  };

  const onComplete = (text: string) => {
    setStreaming(false);
    setResult(text);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">配置智能优化</h2>
        <p className="page-desc">AI 分析当前配置，提供参数调优建议，提升 GEO 效果</p>
      </div>

      {!hasConfig && (
        <Alert type="warning" showIcon message="请先在系统设置中配置 LLM API Key" style={{ marginBottom: 16 }} />
      )}

      <Row gutter={16}>
        <Col xs={24} lg={10}>
          <Card title="优化配置" extra={<SettingOutlined />}>
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message="将基于当前配置和竞品信息，由 AI 分析给出模型选择、温度设置、提示词优化等方面的建议。"
            />
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                provider: config?.gen_provider,
                temperature: config?.temperature || 0.7,
              }}
            >
              <Form.Item label="LLM 提供商" name="provider">
                <Select options={VERIFY_PROVIDER_KEYS.map(p => ({ label: PROVIDER_LABELS[p] || p, value: p }))} />
              </Form.Item>
              <Form.Item label="温度" name="temperature">
                <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="品牌" name="brand" initialValue={config?.brand}>
                <Input placeholder="品牌名称" />
              </Form.Item>
              <Form.Item label="品牌优势" name="advantages" initialValue={config?.advantages}>
                <TextArea rows={3} placeholder="描述品牌核心优势..." />
              </Form.Item>
              <Form.Item label="主要竞品（每行一个）" name="competitors">
                <TextArea rows={3} placeholder={config?.competitors || '竞品A\n竞品B'} />
              </Form.Item>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                block
                onClick={startOptimize}
                disabled={!hasConfig}
                loading={streaming}
                size="large"
              >
                {streaming ? 'AI 分析中...' : '开始智能分析'}
              </Button>
            </Form>
          </Card>

          <Card title="配置优化维度" size="small" style={{ marginTop: 16 }}>
            <Collapse ghost defaultActiveKey={['1']}>
              <Panel header="模型选择建议" key="1">
                <ul style={{ fontSize: 12, paddingLeft: 16, color: 'var(--text-secondary)', margin: 0 }}>
                  <li>不同任务适用不同模型（生成用创造力强的，验证用精确型的）</li>
                  <li>成本效益分析：低成本模型处理大量任务，高成本模型处理关键内容</li>
                  <li>速度优化：批量任务优先选择响应快的模型</li>
                </ul>
              </Panel>
              <Panel header="温度参数调优" key="2">
                <ul style={{ fontSize: 12, paddingLeft: 16, color: 'var(--text-secondary)', margin: 0 }}>
                  <li>内容生成：0.7-0.9（更有创意）</li>
                  <li>验证任务：0.1-0.3（更精确）</li>
                  <li>事实增强：0.4-0.6（平衡创意和准确）</li>
                </ul>
              </Panel>
              <Panel header="关键词策略" key="3">
                <ul style={{ fontSize: 12, paddingLeft: 16, color: 'var(--text-secondary)', margin: 0 }}>
                  <li>长尾关键词在 AI 搜索中更容易被引用</li>
                  <li>口语化、问句形式的关键词表现更好</li>
                  <li>结合品牌特色词组合生成差异化内容</li>
                </ul>
              </Panel>
              <Panel header="平台适配建议" key="4">
                <ul style={{ fontSize: 12, paddingLeft: 16, color: 'var(--text-secondary)', margin: 0 }}>
                  <li>知乎：深度、专业、长文（2000字以上）</li>
                  <li>小红书：图文结合、种草风格、800-1500字</li>
                  <li>CSDN：技术导向、代码示例、教程风格</li>
                </ul>
              </Panel>
            </Collapse>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card
            title="AI 优化建议"
            extra={
              result && !streaming ? (
                <Space>
                  <Button size="small" icon={<ThunderboltOutlined />} onClick={startOptimize}>重新分析</Button>
                </Space>
              ) : null
            }
          >
            {(streaming || result) ? (
              <StreamingText
                key={`opt-${streamKey}`}
                autoStart={streaming}
                fetchStream={(handlers) => {
                  const values = form.getFieldsValue();
                  const competitors = (values.competitors as string || '')
                    .split(/[\n,，]/).map((s: string) => s.trim()).filter(Boolean);
                  reportsApi.configOptimizerStream({
                    provider: values.provider || config?.gen_provider,
                    temperature: values.temperature ?? config?.temperature ?? 0.7,
                    brand: values.brand || config?.brand,
                    advantages: values.advantages || config?.advantages,
                    competitors,
                  }, handlers);
                }}
                onComplete={onComplete}
                height={600}
                placeholder="点击「开始智能分析」获取 AI 配置优化建议"
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <BulbOutlined style={{ fontSize: 48, color: 'var(--border-strong)', marginBottom: 16 }} />
                <Paragraph type="secondary">
                  填写左侧配置信息后，AI 将从模型选择、参数设置、关键词策略、平台适配等多个维度
                  给出个性化优化建议，帮助提升 GEO 效果。
                </Paragraph>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ConfigOptimizerPage;
