import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Button, Space, Table, Tag, message, Typography,
  Modal, Form, Input, Select, Empty, Popconfirm, Badge, Alert, Tabs, Tooltip
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined, CloudServerOutlined,
  CloudUploadOutlined, CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { platformsApi } from '@/api/platforms';
import { useAppStore } from '@/stores';
import type { PlatformInfo, PlatformAccount, PublishRecord } from '@/types';
import { formatDateTime } from '@/utils/dateFormat';

const { Text } = Typography;

const ACCOUNT_TYPES = [
  { label: 'API Key', value: 'api_key' },
  { label: 'Access Token', value: 'token' },
  { label: 'OAuth', value: 'oauth' },
];

const PUBLISH_METHOD_LABELS: Record<string, string> = {
  copy: '复制到剪贴板',
  github: 'GitHub Issue',
  api: 'API 直接发布',
};

const PlatformsPage: React.FC = () => {
  const { config } = useAppStore();
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [records, setRecords] = useState<PublishRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAccount, setEditingAccount] = useState<PlatformAccount | null>(null);

  const [form] = Form.useForm();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [plats, accs, recs] = await Promise.all([
        platformsApi.supported(),
        platformsApi.accounts(config?.brand),
        platformsApi.publishRecords(),
      ]);
      setPlatforms(plats);
      setAccounts(accs);
      setRecords(recs);
    } catch (err) {
      console.error('[PlatformsPage] loadData failed:', err);
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  }, [config?.brand]);

  useEffect(() => { loadData(); }, [loadData]);

  const openCreate = () => {
    setEditingAccount(null);
    form.resetFields();
    setModalVisible(true);
  };

  const openEdit = (acc: PlatformAccount) => {
    setEditingAccount(acc);
    form.setFieldsValue({
      platform: acc.platform,
      account_type: acc.account_type,
      account_name: acc.account_name,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      if (editingAccount) {
        await platformsApi.updateAccount(editingAccount.id, values);
        message.success('更新成功');
      } else {
        await platformsApi.createAccount({ ...values, brand: config?.brand } as Parameters<typeof platformsApi.createAccount>[0]);
        message.success('添加成功');
      }
      setModalVisible(false);
      loadData();
    } catch (err) {
      console.error('[PlatformsPage] handleSave failed:', err);
      message.error('保存失败');
    }
  };

  const handleDelete = async (id: number) => {
    await platformsApi.deleteAccount(id);
    message.success('已删除');
    loadData();
  };

  const handleRetryPublish = async (recordId: number) => {
    try {
      await platformsApi.retryPublish(recordId);
      message.success('已重新发起发布');
      loadData();
    } catch (err) {
      console.error('[PlatformsPage] handleRetryPublish failed:', err);
      message.error('重试失败');
    }
  };

  const accountColumns: ColumnsType<PlatformAccount> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '平台', dataIndex: 'platform', width: 120, render: (p) => <Tag color="blue">{p}</Tag> },
    { title: '账号类型', dataIndex: 'account_type', width: 120, render: (t) => PUBLISH_METHOD_LABELS[t] || t },
    { title: '账号名称', dataIndex: 'account_name', ellipsis: true },
    {
      title: '凭证状态', width: 160,
      render: (_, r) => (
        <Space size={4}>
          {r.has_api_key ? <Badge status="success" text="API Key" /> : <Badge status="default" text="API Key" />}
          {r.has_token ? <Badge status="success" text="Token" /> : null}
        </Space>
      )
    },
    {
      title: '状态', dataIndex: 'is_active', width: 80,
      render: (a: boolean) => a ? <Tag color="green" icon={<CheckCircleOutlined />}>启用</Tag> : <Tag icon={<CloseCircleOutlined />}>停用</Tag>
    },
    { title: '添加时间', dataIndex: 'created_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
    {
      title: '操作', width: 120,
      render: (_, r) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm
            title={`确定删除账号「${r.account_name || r.platform}」？`}
            description="删除后将无法通过此账号发布内容。"
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

  const recordColumns: ColumnsType<PublishRecord> = [
    { title: 'ID', dataIndex: 'id', width: 50 },
    { title: '文章ID', dataIndex: 'article_id', width: 70 },
    { title: '平台', dataIndex: 'platform', width: 100, render: (p) => <Tag color="blue">{p}</Tag> },
    { title: '方式', dataIndex: 'publish_method', width: 100, render: (m) => PUBLISH_METHOD_LABELS[m] || m },
    {
      title: '状态', dataIndex: 'publish_status', width: 80,
      render: (s: string) => {
        const map: Record<string, { color: string; text: string }> = {
          success: { color: 'success', text: '成功' },
          pending: { color: 'processing', text: '待发布' },
          failed: { color: 'error', text: '失败' },
        };
        const m = map[s] || { color: 'default', text: s };
        return <Tag color={m.color}>{m.text}</Tag>;
      }
    },
    {
      title: '发布链接', dataIndex: 'publish_url', ellipsis: true,
      render: (url: string) => url ? <a href={url} target="_blank" rel="noreferrer">{url}</a> : '-',
    },
    {
      title: '重试次数', dataIndex: 'retry_count', width: 80,
      render: (c: number) => c != null && c > 0 ? <Tag color="orange">{c}</Tag> : <Tag>0</Tag>,
    },
    { title: '发布时间', dataIndex: 'published_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
    {
      title: '错误信息', dataIndex: 'error_message', width: 150, ellipsis: true,
      render: (e: string) => e ? (
        <Tooltip title={e} placement="topLeft">
          <Text type="danger" style={{ cursor: 'help' }}>{e.length > 20 ? e.slice(0, 20) + '...' : e}</Text>
        </Tooltip>
      ) : '-',
    },
    {
      title: '操作', width: 70,
      render: (_, r) => (
        r.publish_status === 'failed' ? (
          <Tooltip title="重试发布">
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetryPublish(r.id)}
            >
              重试
            </Button>
          </Tooltip>
        ) : null
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">平台管理</h2>
        <p className="page-desc">管理发布平台账号配置，支持多平台一键发布</p>
      </div>

      <Alert
        type="info"
        showIcon
        message="发布说明"
        description="大部分平台暂无开放 API，系统支持「复制到剪贴板」手动发布方式。配置 GitHub Token 可自动发布到 GitHub Issues。"
        style={{ marginBottom: 16 }}
      />

      <Card title="支持的平台" size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {platforms.map(p => {
            const hasAccount = accounts.some(a => a.platform === p.name || a.platform === p.key);
            return (
              <Tag
                key={p.key}
                color={hasAccount ? 'green' : 'default'}
                style={{ padding: '4px 12px', fontSize: 13, margin: 0 }}
                icon={hasAccount ? <CheckCircleOutlined /> : undefined}
              >
                {p.name}
                {hasAccount ? '（已配置）' : ''}
              </Tag>
            );
          })}
        </div>
      </Card>

      <Tabs items={[
        {
          key: 'accounts',
          label: <span><CloudServerOutlined />平台账号</span>,
          children: (
            <Card
              title="已配置账号"
              extra={
                <Space>
                  <Button size="small" type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加账号</Button>
                  <Button size="small" icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
                </Space>
              }
            >
              <Table
                columns={accountColumns}
                dataSource={accounts}
                rowKey="id"
                loading={loading}
                size="small"
                pagination={false}
                locale={{
                  emptyText: (
                    <Empty
                      description="还没有配置任何平台账号"
                    >
                      <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                        添加账号
                      </Button>
                    </Empty>
                  )
                }}
                scroll={{ x: 800 }}
              />
            </Card>
          ),
        },
        {
          key: 'records',
          label: <span><CloudUploadOutlined />发布记录</span>,
          children: (
            <Card title="发布历史记录" extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>}>
              <Table
                columns={recordColumns}
                dataSource={records}
                rowKey="id"
                loading={loading}
                size="small"
                pagination={{ pageSize: 20 }}
                locale={{ emptyText: <Empty description="暂无发布记录，请在文章管理中发布内容" /> }}
                scroll={{ x: 1000 }}
              />
            </Card>
          ),
        },
      ]} />

      <Modal
        title={editingAccount ? '编辑平台账号' : '添加平台账号'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item label="平台" name="platform" rules={[{ required: true }]}>
            <Select placeholder="选择平台" disabled={!!editingAccount}>
              {platforms.map(p => (
                <Select.Option key={p.key} value={p.name}>{p.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="账号名称" name="account_name">
            <Input placeholder="给账号起个备注名称" />
          </Form.Item>
          <Form.Item label="认证方式" name="account_type" rules={[{ required: true }]} initialValue="api_key">
            <Select options={ACCOUNT_TYPES} />
          </Form.Item>
          <Form.Item label="API Key" name="api_key">
            <Input.Password placeholder="输入 API Key" />
          </Form.Item>
          <Form.Item label="Access Token" name="access_token">
            <Input.Password placeholder="输入 Access Token（如需要）" />
          </Form.Item>
          <Form.Item label="API Secret" name="api_secret">
            <Input.Password placeholder="输入 API Secret（如需要）" />
          </Form.Item>
          <Alert
            type="warning"
            showIcon
            message="凭证仅存储在本地数据库中，请确保部署环境的安全性。"
            style={{ marginBottom: 12 }}
          />
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setModalVisible(false)}>取消</Button>
            <Button type="primary" htmlType="submit">{editingAccount ? '更新' : '添加'}</Button>
          </Space>
        </Form>
      </Modal>
    </div>
  );
};

export default PlatformsPage;
