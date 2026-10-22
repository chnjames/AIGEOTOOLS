import React, { useEffect, useState } from 'react';
import {
  Card, Form, Input, Select, Button, Slider, Space, message, Divider, Alert, Tabs,
  Steps, Modal, InputNumber, Switch, Collapse, Typography,
} from 'antd';
import {
  SaveOutlined, ApiOutlined, CheckCircleOutlined, CloseCircleOutlined,
  RocketOutlined, SettingOutlined, BulbOutlined, DatabaseOutlined,
  AppstoreOutlined, BarChartOutlined,
} from '@ant-design/icons';
import { configApi } from '@/api/config';
import { useAppStore } from '@/stores';
import { PROVIDER_OPTIONS } from '@/constants';
import type { ProviderTestRequest } from '@/types';
import DataManagementTab from './settings/DataManagementTab';
import PlatformTemplatesTab from './settings/PlatformTemplatesTab';

const { TextArea } = Input;
const { Panel } = Collapse;
const { Text } = Typography;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VERIFY_MODES = [
  { label: '自然模式（推荐）', value: 'natural' },
  { label: '提示模式', value: 'prompted' },
];

const PLATFORM_COEFF_DEFAULTS: Record<string, number> = {
  '知乎': 1.5, '微信公众号': 1.3, '小红书': 1.2, 'B站': 1.1,
  'CSDN': 0.8, '掘金': 0.7, 'GitHub': 0.9,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const SettingsPage: React.FC = () => {
  const { config, updateConfig, fetchConfig } = useAppStore();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const temperatureValue = Form.useWatch('temperature', form);

  // Active tab key
  const [activeTab, setActiveTab] = useState('llm');

  // ---- First-run wizard ----
  const [wizardVisible, setWizardVisible] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [wizardLoading, setWizardLoading] = useState(false);
  const [wizardForm] = Form.useForm();

  // -----------------------------------------------------------------
  // Effects
  // -----------------------------------------------------------------

  useEffect(() => {
    if (config) {
      form.setFieldsValue({
        gen_provider: config.gen_provider,
        brand: config.brand,
        advantages: config.advantages,
        competitors: config.competitors,
        temperature: config.temperature,
        use_knowledge_base: config.use_knowledge_base,
        roi_value_per_mention: config.roi_value_per_mention,
        platform_value_coefficients: { ...PLATFORM_COEFF_DEFAULTS, ...config.platform_value_coefficients },
        default_verify_mode: config.default_verify_mode,
      });
      if (!config.first_run_completed && !config.gen_api_key_configured) {
        setTimeout(() => setWizardVisible(true), 500);
      }
    }
  }, [config, form]);

  // -----------------------------------------------------------------
  // Config form handlers
  // -----------------------------------------------------------------

  const handleSave = async (values: Record<string, unknown>) => {
    setSaving(true);
    try {
      const genKey = form.getFieldValue('gen_api_key') || '';
      await updateConfig({
        ...values,
        gen_api_key: genKey || undefined,
      } as Parameters<typeof updateConfig>[0]);
      message.success('配置已保存');
      await fetchConfig();
    } catch (e: unknown) {
      message.error('保存失败：' + (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    const provider = form.getFieldValue('gen_provider');
    const apiKey = form.getFieldValue('gen_api_key');
    if (!apiKey) { message.warning('请先输入 API Key'); return; }
    setTesting(true);
    setTestResult(null);
    try {
      const req: ProviderTestRequest = { provider, api_key: apiKey };
      const result = await configApi.testProvider(req);
      setTestResult(result);
      if (result.success) message.success('连接成功！');
      else message.error(result.message);
    } catch (e: unknown) {
      setTestResult({ success: false, message: (e as Error).message });
    } finally {
      setTesting(false);
    }
  };

  // -----------------------------------------------------------------
  // Wizard handlers
  // -----------------------------------------------------------------

  const handleWizardNext = async () => {
    if (wizardStep === 0) {
      try { await wizardForm.validateFields(['gen_provider', 'gen_api_key']); } catch { return; }
      setWizardLoading(true);
      try {
        const { gen_provider, gen_api_key } = wizardForm.getFieldsValue();
        const res = await configApi.testProvider({ provider: gen_provider, api_key: gen_api_key });
        if (!res.success) { message.error('连接测试失败：' + res.message); setWizardLoading(false); return; }
      } catch (e: unknown) { message.error('测试失败：' + (e as Error).message); setWizardLoading(false); return; }
      setWizardLoading(false);
      setWizardStep(1);
    } else if (wizardStep === 1) {
      try { await wizardForm.validateFields(['brand']); } catch { return; }
      setWizardStep(2);
    }
  };

  const handleWizardFinish = async () => {
    setWizardLoading(true);
    try {
      const values = wizardForm.getFieldsValue();
      await updateConfig({
        gen_provider: values.gen_provider,
        gen_api_key: values.gen_api_key,
        brand: values.brand,
        advantages: values.advantages || '',
        first_run_completed: true,
      });
      await fetchConfig();
      form.setFieldsValue(values);
      message.success('初始化完成！');
      setWizardVisible(false);
    } catch (e: unknown) {
      message.error('保存失败：' + (e as Error).message);
    } finally {
      setWizardLoading(false);
    }
  };

  // -----------------------------------------------------------------
  // Tab items
  // -----------------------------------------------------------------

  const tabItems = [
    // ---- 1. LLM 配置 ----
    {
      key: 'llm',
      label: <span><ApiOutlined /> LLM配置</span>,
      children: (
        <>
          <Form.Item label="生成&优化 LLM 提供商" name="gen_provider">
            <Select options={PROVIDER_OPTIONS.map(p => ({ label: p, value: p }))} />
          </Form.Item>
          <Form.Item label="API Key" name="gen_api_key" extra={
            config?.gen_api_key_configured
              ? <span style={{ color: 'var(--success)' }}><CheckCircleOutlined /> 已配置（{config.gen_api_key_masked}）</span>
              : <span style={{ color: 'var(--error)' }}>未配置</span>
          }>
            <Input.Password placeholder="输入 API Key" autoComplete="new-password" />
          </Form.Item>
          <Form.Item label="API 连接测试">
            <Space>
              <Button icon={<ApiOutlined />} onClick={handleTest} loading={testing}>测试连接</Button>
              {testResult && (
                <Text style={{
                  color: testResult.success ? 'var(--success)' : 'var(--error)',
                  fontSize: 13,
                }}>
                  {testResult.success
                    ? <><CheckCircleOutlined /> {testResult.message}</>
                    : <><CloseCircleOutlined /> {testResult.message}</>}
                </Text>
              )}
            </Space>
          </Form.Item>
          <Divider />
          <Form.Item name="temperature" label={
            <span>生成温度 <Text type="secondary" style={{ fontSize: 13 }}>
              当前: {(temperatureValue ?? 0.7).toFixed(2)}
            </Text></span>
          }>
            <Slider
              min={0} max={1} step={0.05}
              marks={{ 0: '稳定', 0.5: '平衡', 1: '创意' }}
              tooltip={{ formatter: (v) => v?.toFixed(2) }}
            />
          </Form.Item>
          <Collapse ghost style={{ marginLeft: -16 }}>
            <Panel header={<span><SettingOutlined /> 高级：验证设置</span>} key="verify">
              <Alert type="info" showIcon message="验证模型默认使用与生成模型相同的 Key" style={{ marginBottom: 8 }} />
              <Form.Item name="default_verify_mode" label="默认验证模式">
                <Select options={VERIFY_MODES} />
              </Form.Item>
            </Panel>
          </Collapse>
        </>
      ),
    },
    // ---- 2. 品牌信息 ----
    {
      key: 'brand',
      label: <span><BulbOutlined /> 品牌信息</span>,
      children: (
        <>
          <Form.Item label="主品牌名称" name="brand" rules={[{ required: true, message: '请输入品牌名称' }]}>
            <Input placeholder="例如：您的品牌名" />
          </Form.Item>
          <Form.Item label="核心优势/卖点" name="advantages">
            <TextArea rows={4} placeholder="描述品牌的核心优势和卖点，用于内容生成和优化" />
          </Form.Item>
          <Form.Item label="竞品品牌（每行一个）" name="competitors">
            <TextArea rows={3} placeholder="竞品1&#10;竞品2&#10;竞品3" />
          </Form.Item>
        </>
      ),
    },
    // ---- 3. 功能开关 ----
    {
      key: 'features',
      label: <span><SettingOutlined /> 功能开关</span>,
      children: (
        <>
          <Form.Item
            name="use_knowledge_base"
            label="知识库增强"
            valuePropName="checked"
            extra="启用后，内容生成和优化时会自动检索知识库相关内容（消耗额外 token）"
          >
            <Switch checkedChildren="开启" unCheckedChildren="关闭" />
          </Form.Item>
          <Alert
            type="info" showIcon icon={<BulbOutlined />}
            message="知识库功能"
            description="在「知识库」页面上传品牌资料（PDF/Word/TXT）后，开启此选项可让生成的内容更准确。"
          />
        </>
      ),
    },
    // ---- 4. ROI 设置 ----
    {
      key: 'roi',
      label: <span><BarChartOutlined /> ROI设置</span>,
      children: (
        <>
          <Form.Item
            name="roi_value_per_mention"
            label="单次品牌提及估算价值（元）"
            extra="用于计算 AI 搜索中品牌被提及时带来的估算价值"
          >
            <InputNumber min={0} step={10} addonAfter="元/次" style={{ width: 250 }} />
          </Form.Item>
          <Alert
            type="info" showIcon style={{ marginBottom: 12 }}
            message="平台价值系数 = 该平台单次提及相对基础价值的倍数（1.5 = 价值是基础的1.5倍）"
          />
          {Object.entries(PLATFORM_COEFF_DEFAULTS).map(([key, def]) => (
            <div key={key} style={{ marginBottom: 8 }}>
              <Form.Item name={['platform_value_coefficients', key]} noStyle initialValue={def}>
                <InputNumber min={0} step={0.1} style={{ width: 100 }} />
              </Form.Item>
              <span style={{ marginLeft: 8 }}>{key}</span>
            </div>
          ))}
        </>
      ),
    },
    // ---- 5. 数据管理 ----
    {
      key: 'data',
      label: <span><DatabaseOutlined /> 数据管理</span>,
      children: activeTab === 'data' ? <DataManagementTab brand={config?.brand} /> : null,
    },
    // ---- 6. 平台模板 ----
    {
      key: 'templates',
      label: <span><AppstoreOutlined /> 平台模板</span>,
      children: activeTab === 'templates' ? <PlatformTemplatesTab brand={config?.brand} /> : null,
    },
  ];

  // -----------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">系统设置</h2>
        <p className="page-desc">配置 LLM 提供商、API Key、品牌信息、ROI 参数，以及管理数据和平台模板</p>
      </div>

      {config && !config.first_run_completed && (
        <Alert
          type="info" showIcon icon={<RocketOutlined />}
          message="欢迎使用 GEO 智能内容优化平台"
          description="建议先完成首次配置向导，快速开始使用。"
          action={
            <Button type="primary" size="small" onClick={() => { setWizardStep(0); setWizardVisible(true); }}>
              打开配置向导
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <Card>
        <Form
          form={form} layout="vertical" onFinish={handleSave}
          initialValues={{
            gen_provider: 'DeepSeek', temperature: 0.7,
            use_knowledge_base: false, roi_value_per_mention: 50,
            default_verify_mode: 'natural',
          }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
          />
          {activeTab !== 'data' && activeTab !== 'templates' && (
            <>
              <Divider />
              <Space>
                <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving} size="large">保存配置</Button>
                {!config?.first_run_completed && (
                  <Button icon={<RocketOutlined />} onClick={() => { setWizardStep(0); setWizardVisible(true); }}>重新运行配置向导</Button>
                )}
              </Space>
            </>
          )}
        </Form>
      </Card>

      {/* ---- 首次配置向导 Modal ---- */}
      <Modal
        title={<span><RocketOutlined /> 快速配置向导</span>}
        open={wizardVisible}
        onCancel={() => { setWizardVisible(false); wizardForm.resetFields(); }}
        width={520} footer={null} maskClosable={false}
        closable={wizardStep === 2}
      >
        <Steps current={wizardStep} style={{ marginBottom: 24 }} size="small" items={[
          { title: '配置 LLM' }, { title: '品牌信息' }, { title: '完成' },
        ]} />
        <Form form={wizardForm} layout="vertical" initialValues={{ gen_provider: 'DeepSeek' }}>
          {wizardStep === 0 && (
            <>
              <Alert type="info" showIcon style={{ marginBottom: 16 }}
                message="第一步：选择 LLM 提供商并填入 API Key"
                description="推荐使用 DeepSeek（性价比高，中文效果好）。API Key 仅保存在本地数据库中。" />
              <Form.Item label="LLM 提供商" name="gen_provider" rules={[{ required: true }]}>
                <Select options={PROVIDER_OPTIONS.map(p => ({ label: p, value: p }))} />
              </Form.Item>
              <Form.Item label="API Key" name="gen_api_key" rules={[{ required: true, message: '请输入 API Key' }]}>
                <Input.Password placeholder="输入 API Key" autoComplete="new-password" />
              </Form.Item>
            </>
          )}
          {wizardStep === 1 && (
            <>
              <Alert type="info" showIcon style={{ marginBottom: 16 }}
                message="第二步：填写品牌信息"
                description="品牌名称是必需的，核心优势将帮助生成更精准的推荐内容。" />
              <Form.Item label="品牌名称" name="brand" rules={[{ required: true, message: '请输入品牌名称' }]}>
                <Input placeholder="您要优化的品牌名称" />
              </Form.Item>
              <Form.Item label="核心优势（可选）" name="advantages">
                <TextArea rows={3} placeholder="简要描述品牌的核心卖点和优势" />
              </Form.Item>
            </>
          )}
          {wizardStep === 2 && (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <CheckCircleOutlined style={{ fontSize: 48, color: 'var(--success)' }} />
              <h3>配置完成！</h3>
              <p style={{ color: 'var(--text-secondary)' }}>您可以开始使用了，建议先前往「关键词蒸馏」生成目标关键词。</p>
            </div>
          )}
        </Form>
        <Space style={{ marginTop: 16, width: '100%', justifyContent: 'flex-end' }}>
          {wizardStep > 0 && wizardStep < 2 && <Button onClick={() => setWizardStep(s => s - 1)}>上一步</Button>}
          {wizardStep < 2 ? (
            <Button type="primary" onClick={handleWizardNext} loading={wizardLoading}>
              {wizardStep === 0 ? '测试连接并下一步' : '下一步'}
            </Button>
          ) : (
            <Button type="primary" onClick={handleWizardFinish} loading={wizardLoading} icon={<CheckCircleOutlined />}>开始使用</Button>
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default SettingsPage;
