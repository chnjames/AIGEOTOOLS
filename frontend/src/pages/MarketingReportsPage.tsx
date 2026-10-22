import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, DatePicker, Tag, Space, message, Spin, Typography, Drawer, Popconfirm, Empty, Alert } from 'antd';
import { PlusOutlined, EyeOutlined, DeleteOutlined, CopyOutlined, ShareAltOutlined, FileTextOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import dayjs from 'dayjs';
import { analyticsApi, MarketingReport } from '@/api/analytics';
import { useParams } from 'react-router-dom';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

interface MarketingReportsPageProps {
  shareMode?: boolean;
}

const REPORT_TYPE_LABELS: Record<string, string> = {
  daily: '日报',
  weekly: '周报',
  monthly: '月报',
  custom: '自定义',
};

const REPORT_TYPE_COLORS: Record<string, string> = {
  daily: 'blue',
  weekly: 'green',
  monthly: 'purple',
  custom: 'orange',
};

const MarketingReportsPage: React.FC<MarketingReportsPageProps> = ({ shareMode = false }) => {
  const params = useParams<{ token: string }>();

  // Shared report state
  const [sharedReport, setSharedReport] = useState<MarketingReport | null>(null);
  const [sharedLoading, setSharedLoading] = useState(false);
  const [sharedError, setSharedError] = useState(false);

  // Normal mode state
  const [reports, setReports] = useState<MarketingReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  // Generate modal
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateForm] = Form.useForm();

  // Detail drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<MarketingReport | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Fetch shared report (share mode)
  useEffect(() => {
    if (!shareMode) return;
    const token = params.token;
    if (!token) {
      setSharedError(true);
      return;
    }
    let cancelled = false;
    const fetchShared = async () => {
      setSharedLoading(true);
      setSharedError(false);
      try {
        const data = await analyticsApi.getSharedReport(token);
        if (!cancelled) setSharedReport(data);
      } catch (err) {
        console.error('[MarketingReportsPage] fetchShared failed:', err);
        if (!cancelled) setSharedError(true);
      } finally {
        if (!cancelled) setSharedLoading(false);
      }
    };
    fetchShared();
    return () => { cancelled = true; };
  }, [shareMode, params.token]);

  // Fetch reports list (normal mode)
  const fetchReports = async (p = page, ps = pageSize) => {
    setLoading(true);
    try {
      const res = await analyticsApi.listReports({ page: p, page_size: ps });
      setReports(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('[MarketingReportsPage] fetchReports failed:', err);
      message.error('加载报告列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (shareMode) return;
    fetchReports(1, pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shareMode]);

  const handleGenerate = async () => {
    try {
      const values = await generateForm.validateFields();
      setGenerating(true);
      const payload: Record<string, unknown> = {
        report_type: values.report_type,
        brand: values.brand || undefined,
        title: values.title || undefined,
      };
      if (values.report_type === 'custom' && values.date_range) {
        payload.date_from = values.date_range[0].format('YYYY-MM-DD');
        payload.date_to = values.date_range[1].format('YYYY-MM-DD');
      }
      await analyticsApi.generateReport(payload as Parameters<typeof analyticsApi.generateReport>[0]);
      message.success('报告生成任务已提交');
      setGenerateModalOpen(false);
      generateForm.resetFields();
      fetchReports(1, pageSize);
      setPage(1);
    } catch (err) {
      // validation error or api error - antd shows validation errors inline
      console.error('[MarketingReportsPage] handleGenerate failed:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleView = async (record: MarketingReport) => {
    setDrawerOpen(true);
    setDetailLoading(true);
    setSelectedReport(null);
    try {
      const data = await analyticsApi.getReport(record.id);
      setSelectedReport(data);
    } catch (err) {
      console.error('[MarketingReportsPage] handleView failed:', err);
      message.error('加载报告详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await analyticsApi.deleteReport(id);
      message.success('报告已删除');
      // If we're on a page beyond the last after deletion, go back
      const newTotal = total - 1;
      const maxPage = Math.max(1, Math.ceil(newTotal / pageSize));
      if (page > maxPage) {
        setPage(maxPage);
        fetchReports(maxPage, pageSize);
      } else {
        fetchReports(page, pageSize);
      }
    } catch (err) {
      console.error('[MarketingReportsPage] handleDelete failed:', err);
      message.error('删除报告失败');
    }
  };

  const copyShareLink = (shareToken?: string) => {
    if (!shareToken) {
      message.warning('该报告尚未发布，无法分享');
      return;
    }
    const link = `${window.location.origin}/marketing-reports/share/${shareToken}`;
    navigator.clipboard.writeText(link).then(
      () => message.success('分享链接已复制到剪贴板'),
      () => message.error('复制失败，请手动复制')
    );
  };

  const formatDateRange = (from?: string, to?: string) => {
    if (!from && !to) return '-';
    if (from && to) return `${dayjs(from).format('YYYY-MM-DD')} ~ ${dayjs(to).format('YYYY-MM-DD')}`;
    return from ? dayjs(from).format('YYYY-MM-DD') : dayjs(to!).format('YYYY-MM-DD');
  };

  // ─── Share Mode Render ───────────────────────────────────────────────────────

  if (shareMode) {
    if (sharedLoading) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <Spin size="large" tip="加载报告中..." />
        </div>
      );
    }

    if (sharedError || !sharedReport) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <Alert
            type="error"
            message="报告不存在或已失效"
            icon={<FileTextOutlined />}
            showIcon
            style={{ maxWidth: 480 }}
          />
        </div>
      );
    }

    return (
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
        <Card bordered={false} style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={3} style={{ marginBottom: 4 }}>{sharedReport.title}</Title>
              <Space split={<Text type="secondary">|</Text>}>
                <Tag color={REPORT_TYPE_COLORS[sharedReport.report_type] || 'default'}>
                  {REPORT_TYPE_LABELS[sharedReport.report_type] || sharedReport.report_type}
                </Tag>
                {sharedReport.brand && <Text type="secondary">品牌：{sharedReport.brand}</Text>}
                {(sharedReport.date_from || sharedReport.date_to) && (
                  <Text type="secondary">{formatDateRange(sharedReport.date_from, sharedReport.date_to)}</Text>
                )}
                {sharedReport.created_at && (
                  <Text type="secondary">生成于 {dayjs(sharedReport.created_at).format('YYYY-MM-DD HH:mm')}</Text>
                )}
              </Space>
            </div>
            {sharedReport.summary && (
              <Alert message={sharedReport.summary} type="info" showIcon style={{ borderRadius: 8 }} />
            )}
            <div className="markdown-preview">
              <ReactMarkdown>
                {sharedReport.markdown_content || '*暂无报告内容*'}
              </ReactMarkdown>
            </div>
            {sharedReport.recommendations && sharedReport.recommendations.length > 0 && (
              <div>
                <Title level={5} style={{ marginTop: 0 }}>
                  <ShareAltOutlined /> 优化建议
                </Title>
                <ul style={{ paddingLeft: 20, margin: 0 }}>
                  {sharedReport.recommendations.map((rec, idx) => (
                    <li key={idx} style={{ marginBottom: 6 }}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </Space>
        </Card>
      </div>
    );
  }

  // ─── Normal Mode Render ──────────────────────────────────────────────────────

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text: string) => (
        <Space>
          <FileTextOutlined style={{ color: 'var(--brand-500)' }} />
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'report_type',
      key: 'report_type',
      width: 100,
      render: (type: string) => (
        <Tag color={REPORT_TYPE_COLORS[type] || 'default'}>
          {REPORT_TYPE_LABELS[type] || type}
        </Tag>
      ),
    },
    {
      title: '品牌',
      dataIndex: 'brand',
      key: 'brand',
      width: 120,
      render: (b?: string) => b || '-',
    },
    {
      title: '日期范围',
      key: 'date_range',
      width: 220,
      render: (_: unknown, record: MarketingReport) =>
        formatDateRange(record.date_from, record.date_to),
    },
    {
      title: '生成时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (t?: string) => t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '状态',
      dataIndex: 'is_published',
      key: 'is_published',
      width: 90,
      render: (p: boolean) => p
        ? <Tag color="green">已发布</Tag>
        : <Tag>草稿</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: MarketingReport) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => copyShareLink(record.share_token)}
            disabled={!record.is_published}
          >
            复制链接
          </Button>
          <Popconfirm
            title="确定删除此报告？"
            description="删除后无法恢复。"
            okText="删除"
            okButtonProps={{ danger: true }}
            cancelText="取消"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const reportType = Form.useWatch('report_type', generateForm);

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <h2 className="page-title">营销报告</h2>
        <p className="page-desc">自动生成周期性营销报告，支持分享和导出</p>
      </div>

      {/* Actions bar */}
      <Card
        bordered={false}
        style={{ marginBottom: 16 }}
        styles={{ body: { padding: '16px 24px' } }}
      >
        <div className="flex justify-between items-center">
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                generateForm.resetFields();
                setGenerateModalOpen(true);
              }}
            >
              生成报告
            </Button>
          </Space>
          <Text type="secondary">共 {total} 份报告</Text>
        </div>
      </Card>

      {/* Reports Table */}
      <Card bordered={false} style={{ boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <Table
          columns={columns}
          dataSource={reports}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t, range) => `${range[0]}-${range[1]} / 共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
              fetchReports(p, ps);
            },
          }}
          locale={{
            emptyText: <Empty description="暂无报告，点击上方按钮生成第一份报告" />,
          }}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* Generate Report Modal */}
      <Modal
        title="生成营销报告"
        open={generateModalOpen}
        onOk={handleGenerate}
        onCancel={() => setGenerateModalOpen(false)}
        confirmLoading={generating}
        okText="生成"
        cancelText="取消"
        destroyOnClose
      >
        <Form
          form={generateForm}
          layout="vertical"
          initialValues={{ report_type: 'weekly' }}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label="报告类型"
            name="report_type"
            rules={[{ required: true, message: '请选择报告类型' }]}
          >
            <Select>
              <Select.Option value="daily">日报</Select.Option>
              <Select.Option value="weekly">周报</Select.Option>
              <Select.Option value="monthly">月报</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="品牌" name="brand">
            <Input placeholder="请输入品牌名称（可选）" allowClear />
          </Form.Item>
          {reportType === 'custom' && (
            <Form.Item
              label="日期范围"
              name="date_range"
              rules={[{ required: true, message: '请选择日期范围' }]}
            >
              <RangePicker style={{ width: '100%' }} />
            </Form.Item>
          )}
          <Form.Item label="报告标题" name="title">
            <Input placeholder="自定义标题（可选，留空自动生成）" allowClear />
          </Form.Item>
        </Form>
      </Modal>

      {/* Report Detail Drawer */}
      <Drawer
        title={selectedReport?.title || '报告详情'}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedReport(null);
        }}
        width={720}
        destroyOnClose
        extra={
          selectedReport && (
            <Space>
              <Button
                icon={<CopyOutlined />}
                onClick={() => copyShareLink(selectedReport.share_token)}
                disabled={!selectedReport.is_published}
              >
                复制分享链接
              </Button>
            </Space>
          )
        }
      >
        {detailLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
            <Spin tip="加载报告..." />
          </div>
        ) : selectedReport ? (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Space wrap split={<Text type="secondary">|</Text>}>
              <Tag color={REPORT_TYPE_COLORS[selectedReport.report_type] || 'default'}>
                {REPORT_TYPE_LABELS[selectedReport.report_type] || selectedReport.report_type}
              </Tag>
              {selectedReport.brand && <Text type="secondary">品牌：{selectedReport.brand}</Text>}
              {(selectedReport.date_from || selectedReport.date_to) && (
                <Text type="secondary">
                  {formatDateRange(selectedReport.date_from, selectedReport.date_to)}
                </Text>
              )}
              {selectedReport.created_at && (
                <Text type="secondary">
                  生成于 {dayjs(selectedReport.created_at).format('YYYY-MM-DD HH:mm')}
                </Text>
              )}
              {selectedReport.is_published
                ? <Tag color="green" icon={<ShareAltOutlined />}>已发布</Tag>
                : <Tag>草稿</Tag>}
            </Space>

            {selectedReport.is_published && selectedReport.share_token && (
              <Alert
                type="success"
                showIcon
                icon={<ShareAltOutlined />}
                message="分享链接"
                description={
                  <Text copyable style={{ wordBreak: 'break-all' }}>
                    {`${window.location.origin}/marketing-reports/share/${selectedReport.share_token}`}
                  </Text>
                }
              />
            )}

            {selectedReport.summary && (
              <Alert message={selectedReport.summary} type="info" showIcon />
            )}

            <div className="markdown-preview">
              <ReactMarkdown>
                {selectedReport.markdown_content || '*暂无报告内容*'}
              </ReactMarkdown>
            </div>

            {selectedReport.recommendations && selectedReport.recommendations.length > 0 && (
              <div>
                <Title level={5} style={{ marginTop: 0 }}>
                  <ShareAltOutlined /> 优化建议
                </Title>
                <ul style={{ paddingLeft: 20, margin: 0 }}>
                  {selectedReport.recommendations.map((rec, idx) => (
                    <li key={idx} style={{ marginBottom: 6 }}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </Space>
        ) : null}
      </Drawer>
    </div>
  );
};

export default MarketingReportsPage;
