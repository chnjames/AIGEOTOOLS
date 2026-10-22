import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Button, Space, message, Alert, Table, Tag, Tooltip, Popconfirm,
  Empty, Modal, Form, Input, InputNumber, Switch, Row, Col, Radio,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined, ExportOutlined, ImportOutlined, ReloadOutlined,
  EditOutlined, DeleteOutlined, UndoOutlined,
} from '@ant-design/icons';
import { templatesApi } from '@/api/templates';
import type { TemplateCreateData, TemplateImportResult } from '@/api/templates';
import type { PlatformTemplate } from '@/types';

const { Text } = Typography;
const { TextArea } = Input;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PlatformTemplatesTabProps {
  /** Current brand name from app config (reserved for brand-scoped actions). */
  brand?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PlatformTemplatesTab: React.FC<PlatformTemplatesTabProps> = ({ brand: _brand }) => {
  // ---- Templates ----
  const [templates, setTemplates] = useState<PlatformTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);

  // Template edit modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PlatformTemplate | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editForm] = Form.useForm();

  // Template create modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createSaving, setCreateSaving] = useState(false);
  const [createForm] = Form.useForm();

  // Template import
  const [templateImportStrategy, setTemplateImportStrategy] = useState<'skip' | 'overwrite'>('skip');
  const [templateImportResult, setTemplateImportResult] = useState<TemplateImportResult | null>(null);
  const [templateImportLoading, setTemplateImportLoading] = useState(false);
  const templateFileInputRef = useRef<HTMLInputElement>(null);

  // -----------------------------------------------------------------
  // Data loaders
  // -----------------------------------------------------------------

  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    try {
      const list = await templatesApi.listTemplates();
      setTemplates(list);
    } catch (e: unknown) {
      message.error('加载模板失败：' + (e as Error).message);
    } finally {
      setTemplatesLoading(false);
    }
  }, []);

  // Load data on mount
  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  // -----------------------------------------------------------------
  // Templates: Toggle / Reset / Delete
  // -----------------------------------------------------------------

  const handleToggleTemplateActive = async (id: number, is_active: boolean) => {
    try {
      await templatesApi.updateTemplate(id, { is_active });
      setTemplates(prev => prev.map(t => t.id === id ? { ...t, is_active } : t));
      message.success(is_active ? '模板已启用' : '模板已禁用');
    } catch (e: unknown) {
      message.error('操作失败：' + (e as Error).message);
      loadTemplates();
    }
  };

  const handleResetTemplate = async (id: number) => {
    try {
      await templatesApi.resetTemplate(id);
      message.success('模板已重置为默认配置');
      loadTemplates();
    } catch (e: unknown) {
      message.error('重置失败：' + (e as Error).message);
    }
  };

  const handleDeleteTemplate = async (id: number) => {
    try {
      await templatesApi.deleteTemplate(id);
      message.success('模板已删除');
      loadTemplates();
    } catch (e: unknown) {
      message.error('删除失败：' + (e as Error).message);
    }
  };

  // -----------------------------------------------------------------
  // Templates: Edit
  // -----------------------------------------------------------------

  const handleOpenEdit = (tmpl: PlatformTemplate) => {
    setEditingTemplate(tmpl);
    editForm.setFieldsValue({
      style_instruction: tmpl.style,
      filename_suffix: tmpl.filename_suffix,
      group_name: tmpl.group,
      word_count_default: tmpl.word_count_default,
      is_active: tmpl.is_active,
    });
    setEditModalOpen(true);
  };

  const handleEditSave = async () => {
    if (!editingTemplate) return;
    try {
      const values = await editForm.validateFields();
      setEditSaving(true);
      await templatesApi.updateTemplate(editingTemplate.id, {
        style: values.style_instruction,
        filename_suffix: values.filename_suffix,
        group: values.group_name,
        word_count_default: values.word_count_default,
        is_active: values.is_active,
      });
      message.success('模板已更新');
      setEditModalOpen(false);
      setEditingTemplate(null);
      editForm.resetFields();
      loadTemplates();
    } catch (e: unknown) {
      if ((e as { errorFields?: unknown }).errorFields) return; // form validation error
      message.error('更新失败：' + (e as Error).message);
    } finally {
      setEditSaving(false);
    }
  };

  // -----------------------------------------------------------------
  // Templates: Create
  // -----------------------------------------------------------------

  const handleOpenCreate = () => {
    createForm.resetFields();
    createForm.setFieldsValue({ word_count_default: 1500, is_active: true });
    setCreateModalOpen(true);
  };

  const handleCreateSave = async () => {
    try {
      const values = await createForm.validateFields();
      setCreateSaving(true);
      const data: TemplateCreateData = {
        name: values.name,
        style_instruction: values.style_instruction,
        filename_suffix: values.filename_suffix,
        group_name: values.group_name,
        word_count_default: values.word_count_default,
        is_active: values.is_active ?? true,
      };
      await templatesApi.createTemplate(data);
      message.success('模板已创建');
      setCreateModalOpen(false);
      createForm.resetFields();
      loadTemplates();
    } catch (e: unknown) {
      if ((e as { errorFields?: unknown }).errorFields) return;
      message.error('创建失败：' + (e as Error).message);
    } finally {
      setCreateSaving(false);
    }
  };

  // -----------------------------------------------------------------
  // Templates: Export / Import
  // -----------------------------------------------------------------

  const handleExportTemplates = () => {
    templatesApi.exportTemplates()
      .then(() => message.success('开始导出模板'))
      .catch((e: unknown) => message.error('导出失败：' + (e as Error).message));
  };

  const handleTemplateFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setTemplateImportResult(null);
    setTemplateImportLoading(true);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const text = ev.target?.result as string;
        let templatesData: object[];
        try {
          const parsed = JSON.parse(text);
          templatesData = Array.isArray(parsed) ? parsed : (parsed.templates ?? parsed.data ?? []);
        } catch (err) {
          console.error('[PlatformTemplatesTab] JSON.parse failed:', err);
          throw new Error('JSON 解析失败，请检查文件格式');
        }
        if (!Array.isArray(templatesData)) {
          throw new Error('文件格式不正确，应为模板数组');
        }
        const result = await templatesApi.importTemplates(templatesData, templateImportStrategy);
        setTemplateImportResult(result);
        message.success(`导入完成：新增 ${result.imported}，更新 ${result.updated}，跳过 ${result.skipped}`);
        loadTemplates();
      } catch (err: unknown) {
        message.error('导入失败：' + (err as Error).message);
      } finally {
        setTemplateImportLoading(false);
        if (templateFileInputRef.current) templateFileInputRef.current.value = '';
      }
    };
    reader.onerror = () => {
      message.error('文件读取失败');
      setTemplateImportLoading(false);
    };
    reader.readAsText(file);
  };

  // -----------------------------------------------------------------
  // Table columns
  // -----------------------------------------------------------------

  const templateColumns: ColumnsType<PlatformTemplate> = [
    {
      title: '平台名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record) => (
        <Space>
          <Text strong>{name}</Text>
          {record.is_default && <Tag color="blue" style={{ fontSize: 11 }}>内置</Tag>}
        </Space>
      ),
    },
    {
      title: '分组',
      dataIndex: 'group',
      key: 'group',
      width: 110,
      render: (g: string) => <Tag>{g || '-'}</Tag>,
    },
    {
      title: '默认字数',
      dataIndex: 'word_count_default',
      key: 'word_count_default',
      width: 100,
      render: (n: number) => n != null ? `${n} 字` : '-',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean, record) => (
        <Switch
          checked={active}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          size="small"
          onChange={(checked) => handleToggleTemplateActive(record.id, checked)}
        />
      ),
    },
    {
      title: '是否内置',
      dataIndex: 'is_default',
      key: 'is_default',
      width: 90,
      render: (isDef: boolean) => isDef
        ? <Tag color="blue">内置</Tag>
        : <Tag color="default">自定义</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record) => (
        <Space size="small">
          <Button
            type="link" size="small" icon={<EditOutlined />}
            onClick={() => handleOpenEdit(record)}
          >
            编辑
          </Button>
          {record.is_default && (
            <Popconfirm
              title="重置模板"
              description="确定要将此内置模板重置为默认配置吗？自定义修改将丢失。"
              okText="确定重置"
              cancelText="取消"
              okButtonProps={{ danger: true }}
              onConfirm={() => handleResetTemplate(record.id)}
            >
              <Button type="link" size="small" icon={<UndoOutlined />} danger>
                重置
              </Button>
            </Popconfirm>
          )}
          {!record.is_default && (
            <Popconfirm
              title="删除模板"
              description={`确定要删除自定义模板"${record.name}"吗？此操作不可恢复。`}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
              onConfirm={() => handleDeleteTemplate(record.id)}
            >
              <Button type="link" size="small" icon={<DeleteOutlined />} danger>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // -----------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button
          type="primary" icon={<PlusOutlined />}
          onClick={handleOpenCreate}
        >
          新增模板
        </Button>
        <Button
          icon={<ExportOutlined />}
          onClick={handleExportTemplates}
        >
          导出模板
        </Button>
        <Popconfirm
          title="导入模板"
          description={(
            <div>
              <p>选择一个 JSON 文件导入模板</p>
              <Radio.Group
                value={templateImportStrategy}
                onChange={(e) => setTemplateImportStrategy(e.target.value)}
                optionType="button" buttonStyle="solid" size="small"
              >
                <Radio.Button value="skip">跳过重复</Radio.Button>
                <Radio.Button value="overwrite">覆盖同名</Radio.Button>
              </Radio.Group>
            </div>
          )}
          okText="选择文件"
          cancelText="取消"
          onConfirm={() => templateFileInputRef.current?.click()}
        >
          <Button icon={<ImportOutlined />} loading={templateImportLoading}>
            导入模板
          </Button>
        </Popconfirm>
        <input
          ref={templateFileInputRef}
          type="file"
          accept=".json"
          style={{ display: 'none' }}
          onChange={handleTemplateFileChange}
        />
        <Button
          icon={<ReloadOutlined />}
          onClick={loadTemplates}
          loading={templatesLoading}
        >
          刷新
        </Button>
      </Space>

      {templateImportResult && (
        <Alert
          type="success" showIcon closable
          style={{ marginBottom: 12 }}
          message="模板导入完成"
          description={
            <Space>
              <Tag color="green">新增：{templateImportResult.imported}</Tag>
              <Tag color="blue">更新：{templateImportResult.updated}</Tag>
              <Tag color="default">跳过：{templateImportResult.skipped}</Tag>
              {templateImportResult.errors && templateImportResult.errors.length > 0 && (
                <Tooltip title={templateImportResult.errors.map(e => `${e.name}: ${e.reason}`).join('\n')}>
                  <Tag color="orange">错误：{templateImportResult.errors.length}</Tag>
                </Tooltip>
              )}
            </Space>
          }
          onClose={() => setTemplateImportResult(null)}
        />
      )}

      <Table<PlatformTemplate>
        columns={templateColumns}
        dataSource={templates}
        rowKey="id"
        loading={templatesLoading}
        size="small"
        pagination={{ pageSize: 20, showTotal: (total) => `共 ${total} 个模板`, showSizeChanger: false }}
        locale={{ emptyText: <Empty description="暂无模板数据" /> }}
        scroll={{ x: 700 }}
      />

      {/* ---- 编辑模板 Modal ---- */}
      <Modal
        title={`编辑模板：${editingTemplate?.name ?? ''}`}
        open={editModalOpen}
        onCancel={() => { setEditModalOpen(false); setEditingTemplate(null); editForm.resetFields(); }}
        onOk={handleEditSave}
        confirmLoading={editSaving}
        okText="保存"
        cancelText="取消"
        width={640}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" preserve={false}>
          <Form.Item label="风格指令 (style_instruction)" name="style_instruction">
            <TextArea rows={5} placeholder="描述该平台的内容风格要求，如语言风格、格式偏好等" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="文件名后缀" name="filename_suffix">
                <Input placeholder="例如：zhihu, xiaohongshu" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="所属分组" name="group_name">
                <Input placeholder="例如：社区, 技术, 自媒体" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="默认字数" name="word_count_default">
                <InputNumber min={100} max={20000} step={100} style={{ width: '100%' }} addonAfter="字" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="启用状态" name="is_active" valuePropName="checked">
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* ---- 新建模板 Modal ---- */}
      <Modal
        title="新增平台模板"
        open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); createForm.resetFields(); }}
        onOk={handleCreateSave}
        confirmLoading={createSaving}
        okText="创建"
        cancelText="取消"
        width={640}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item
            label="平台名称" name="name"
            rules={[{ required: true, message: '请输入平台名称' }]}
          >
            <Input placeholder="例如：知乎专栏、小红书笔记" />
          </Form.Item>
          <Form.Item label="风格指令 (style_instruction)" name="style_instruction">
            <TextArea rows={5} placeholder="描述该平台的内容风格要求、格式规范、语气偏好等" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="文件名后缀" name="filename_suffix">
                <Input placeholder="例如：zhihu, xhs" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="所属分组" name="group_name">
                <Input placeholder="例如：社区, 技术, 自媒体" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="默认字数" name="word_count_default">
                <InputNumber min={100} max={20000} step={100} style={{ width: '100%' }} addonAfter="字" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="启用状态" name="is_active" valuePropName="checked">
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default PlatformTemplatesTab;
