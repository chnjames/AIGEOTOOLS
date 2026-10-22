import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card, Button, Space, Table, Tag, message, Row, Col, Typography,
  Input, Empty, Spin, Popconfirm, Alert, List, Badge
} from 'antd';
import {
  UploadOutlined, DeleteOutlined, ReloadOutlined, FileTextOutlined,
  SearchOutlined, FileOutlined, FilePdfOutlined, FileWordOutlined, FileMarkdownOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { knowledgeApi } from '@/api/knowledge';
import { FileUpload } from '@/components';
import { useAppStore } from '@/stores';
import { formatDateTime } from '@/utils/dateFormat';
import type { KnowledgeDoc, KnowledgeChunk } from '@/types';

const { Text, Paragraph } = Typography;
const { Search: AntSearch } = Input;

const getFileIcon = (type?: string) => {
  if (!type) return <FileOutlined />;
  const t = type.toLowerCase();
  if (t.includes('pdf')) return <FilePdfOutlined style={{ color: 'var(--error)' }} />;
  if (t.includes('word') || t.includes('doc')) return <FileWordOutlined style={{ color: 'var(--brand-500)' }} />;
  if (t.includes('markdown') || t.includes('md')) return <FileMarkdownOutlined style={{ color: 'var(--success)' }} />;
  return <FileTextOutlined />;
};

const KnowledgePage: React.FC = () => {
  const { config } = useAppStore();
  const uploadCardRef = useRef<HTMLDivElement>(null);
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<KnowledgeChunk[]>([]);
  const [uploading, setUploading] = useState(false);

  const loadDocs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await knowledgeApi.list({ brand: config?.brand, page, page_size: 20 });
      setDocs(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('[KnowledgePage] loadDocs failed:', err);
      message.error('加载知识库失败');
    } finally {
      setLoading(false);
    }
  }, [config?.brand, page]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await knowledgeApi.upload(file, config?.brand);
      message.success(`${file.name} 上传成功，已分块索引`);
      loadDocs();
    } catch (e: unknown) {
      const err = e as Error;
      message.error('上传失败：' + (err?.message || ''));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    await knowledgeApi.delete(id);
    message.success('已删除');
    loadDocs();
  };

  const handleSearch = async (value: string) => {
    if (!value.trim()) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const results = await knowledgeApi.search(value, config?.brand, 5);
      setSearchResults(results);
    } catch (err) {
      console.error('[KnowledgePage] handleSearch failed:', err);
      message.error('搜索失败');
    } finally {
      setSearching(false);
    }
  };

  const columns: ColumnsType<KnowledgeDoc> = [
    {
      title: '文档',
      dataIndex: 'filename',
      render: (name: string, r) => (
        <Space>
          {getFileIcon(r.file_type)}
          <Text>{name}</Text>
        </Space>
      ),
    },
    { title: '类型', dataIndex: 'file_type', width: 80, render: (t) => t ? <Tag>{t.toUpperCase()}</Tag> : '-' },
    {
      title: '分块数', dataIndex: 'chunk_count', width: 80,
      render: (c: number) => <Badge count={c} showZero color="#3b82f6" />
    },
    { title: '上传时间', dataIndex: 'created_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
    {
      title: '操作', width: 80,
      render: (_, r) => (
        <Popconfirm
          title={`确定删除文档「${r.filename}」？`}
          description="此操作不可恢复，文档将从知识库中移除。"
          onConfirm={() => handleDelete(r.id)}
          okText="确定删除"
          cancelText="取消"
        >
          <Button type="link" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">知识库管理</h2>
        <p className="page-desc">上传品牌资料文档，内容生成时自动引用相关知识增强准确性</p>
      </div>

      <Alert
        type="info"
        showIcon
        message="知识库使用说明"
        description="上传品牌介绍、产品文档、案例资料等文件后，系统将自动进行文本分块索引。生成内容时会自动检索相关段落作为上下文，提升内容准确性和品牌一致性。支持 TXT、Markdown、PDF、Word 格式。"
        style={{ marginBottom: 16 }}
      />

      <Row gutter={16}>
        <Col xs={24} lg={10}>
          <div ref={uploadCardRef}>
          <Card title="上传文档">
            <FileUpload
              onUpload={handleUpload}
              accept=".txt,.md,.pdf,.docx,.doc"
              maxSizeMB={20}
              tip="支持 TXT/MD/PDF/DOC/DOCX 格式，单个文件不超过 20MB"
            />
            {uploading && (
              <div style={{ textAlign: 'center', marginTop: 12 }}>
                <Spin tip="正在解析文档..." />
              </div>
            )}
          </Card>

          <Card title="知识检索" style={{ marginTop: 16 }}>
            <AntSearch
              placeholder="输入关键词搜索知识库..."
              enterButton={<SearchOutlined />}
              size="large"
              loading={searching}
              onSearch={handleSearch}
              onChange={e => { if (!e.target.value) setSearchResults([]); }}
            />
            {searchResults.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
                  找到 {searchResults.length} 个相关片段
                </Paragraph>
                <List
                  dataSource={searchResults}
                  renderItem={(chunk, i) => (
                    <List.Item key={i}>
                      <div style={{ width: '100%' }}>
                        <Space style={{ marginBottom: 4 }}>
                          <Tag color="blue">{chunk.filename}</Tag>
                          <Text type="secondary" style={{ fontSize: 11 }}>相关度：{(chunk.score * 100).toFixed(1)}%</Text>
                        </Space>
                        <div style={{
                          fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7,
                          background: 'var(--bg-tertiary)', padding: 8, borderRadius: 4,
                          border: '1px solid var(--border-light)',
                        }}>
                          {chunk.content.length > 300 ? chunk.content.slice(0, 300) + '...' : chunk.content}
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              </div>
            )}
          </Card>
          </div>
        </Col>

        <Col xs={24} lg={14}>
          <Card
            title={`已上传文档 (${total})`}
            extra={
              <Space>
                <Tag color={total > 0 ? 'green' : 'default'}>{total} 个文档</Tag>
                <Button size="small" icon={<ReloadOutlined />} onClick={loadDocs}>刷新</Button>
              </Space>
            }
          >
            <Table
              columns={columns}
              dataSource={docs}
              rowKey="id"
              loading={loading}
              size="small"
              pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
              locale={{
                emptyText: loading ? (
                  <div style={{ textAlign: 'center', padding: '40px 0' }}>
                    <Spin tip="加载中..." />
                  </div>
                ) : (
                  <Empty
                    description={
                      <span>
                        还没有上传任何文档，上传文档后AI会自动学习其中的内容
                      </span>
                    }
                  >
                    <Button
                      type="primary"
                      icon={<UploadOutlined />}
                      onClick={() => uploadCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                    >
                      上传文档
                    </Button>
                  </Empty>
                )
              }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default KnowledgePage;
