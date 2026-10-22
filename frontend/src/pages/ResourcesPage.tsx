import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Tabs, Tag, Button, Empty, Space, List, Spin } from 'antd';
import { BookOutlined, LinkOutlined, ToolOutlined, BulbOutlined } from '@ant-design/icons';
import { resourcesApi } from '@/api/resources';
import type { Resource, Technique } from '@/types';

const { Text, Paragraph } = Typography;

const ResourcesPage: React.FC = () => {
  const [resources, setResources] = useState<Resource[]>([]);
  const [techniques, setTechniques] = useState<Technique[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      resourcesApi.list(),
      resourcesApi.categories(),
      resourcesApi.techniques(),
    ]).then(([res, cats, techs]) => {
      setResources(res);
      setCategories(cats);
      setTechniques(techs);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const filteredResources = activeCategory
    ? resources.filter(r => r.category === activeCategory)
    : resources;

  const techniqueCategories = Array.from(new Set(techniques.map(t => t.category)));

  if (loading) {
    return (
      <div className="page-container text-center p-20">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">GEO 资源库</h2>
        <p className="page-desc">GEO 优化技巧、学习资源和最佳实践参考</p>
      </div>

      <Tabs items={[
        {
          key: 'techniques',
          label: <span><ToolOutlined />GEO 优化技巧</span>,
          children: (
            <div>
              <Paragraph type="secondary">
                以下是 GEO（Generative Engine Optimization，生成引擎优化）的核心优化技巧，
                应用这些技巧可以提升品牌在 AI 搜索结果中的被提及率和排名位置。
              </Paragraph>
              {techniqueCategories.map(cat => (
                <Card
                  key={cat}
                  title={
                    <Space>
                      <BulbOutlined />
                      <span>{cat}</span>
                      <Tag color="blue">{techniques.filter(t => t.category === cat).length} 项</Tag>
                    </Space>
                  }
                  size="small"
                  style={{ marginBottom: 12 }}
                >
                  <List
                    dataSource={techniques.filter(t => t.category === cat)}
                    renderItem={(t, i) => (
                      <List.Item key={i}>
                        <div style={{ width: '100%' }}>
                          <Text strong>{t.name}</Text>
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0' }}>{t.description}</div>
                          <div style={{ fontSize: 12, color: 'var(--brand-500)', fontStyle: 'italic', background: 'var(--bg-info)', padding: '6px 8px', borderRadius: 4 }}>
                            <BulbOutlined /> {t.example}
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                </Card>
              ))}
            </div>
          ),
        },
        {
          key: 'resources',
          label: <span><BookOutlined />学习资源</span>,
          children: (
            <div>
              <Space wrap style={{ marginBottom: 16 }}>
                <Button type={!activeCategory ? 'primary' : 'default'} size="small" onClick={() => setActiveCategory('')}>
                  全部 ({resources.length})
                </Button>
                {categories.map(cat => (
                  <Button
                    key={cat}
                    type={activeCategory === cat ? 'primary' : 'default'}
                    size="small"
                    onClick={() => setActiveCategory(cat)}
                  >
                    {cat} ({resources.filter(r => r.category === cat).length})
                  </Button>
                ))}
              </Space>
              <Row gutter={[16, 16]}>
                {filteredResources.length > 0 ? filteredResources.map((r, i) => (
                  <Col xs={24} md={12} lg={8} key={i}>
                    <Card
                      size="small"
                      title={
                        <Space>
                          <LinkOutlined />
                          <span>{r.title}</span>
                        </Space>
                      }
                      extra={<Tag>{r.category}</Tag>}
                      hoverable
                    >
                      <Paragraph
                        ellipsis={{ rows: 3 }}
                        style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8, minHeight: 60 }}
                      >
                        {r.description}
                      </Paragraph>
                      <Button
                        type="link"
                        size="small"
                        icon={<LinkOutlined />}
                        onClick={() => window.open(r.url, '_blank', 'noopener,noreferrer')}
                        style={{ padding: 0 }}
                      >
                        查看原文
                      </Button>
                    </Card>
                  </Col>
                )) : (
                  <Col span={24}><Empty description="暂无 GEO 资源，请尝试切换上方分类或刷新页面" /></Col>
                )}
              </Row>
            </div>
          ),
        },
      ]} />
    </div>
  );
};

export default ResourcesPage;
