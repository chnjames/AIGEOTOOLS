import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card, Form, Input, InputNumber, Button, Space, Table, Tag, message,
  Select, Row, Col, Popconfirm, Typography, Modal, Spin, Empty, Alert, Tabs, Switch,
  Collapse, Checkbox, Badge, Divider, Pagination, Skeleton, Tooltip, Progress
} from 'antd';
import {
  EditOutlined, DeleteOutlined, ThunderboltOutlined, DownloadOutlined,
  CloudUploadOutlined, EyeOutlined, FileTextOutlined, AppstoreOutlined,
  SaveOutlined, RocketOutlined, CheckCircleOutlined, SwapOutlined,
  HistoryOutlined, CaretRightOutlined, RollbackOutlined, DiffOutlined,
  UndoOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { articlesApi } from '@/api/articles';
import { keywordsApi } from '@/api/keywords';
import { StreamingText, MarkdownEditor } from '@/components';
import { useAppStore } from '@/stores';
import { PLATFORM_ICONS } from '@/constants';
import type { Article, PlatformInfo, Keyword, ArticleVersion, DiffResult, PlatformGroup } from '@/types';
import { formatDateTime } from '@/utils/dateFormat';

const { Text } = Typography;
const { TextArea } = Input;

// ─── Error classification helper ────────────────────────────────────────────
const classifyError = (errorType?: string, rawMessage?: string): string => {
  switch (errorType) {
    case 'auth_error': return 'API Key 无效，请前往设置检查';
    case 'balance_error': return 'API 余额不足，请充值后重试';
    case 'timeout': return '请求超时，请稍后重试';
    case 'rate_limit': return '请求过于频繁，请稍后重试';
    case 'model_not_found': return '模型配置有误，请检查设置';
    case 'network_error': return '网络连接失败，请检查网络';
    default: return rawMessage || '生成失败，请稍后重试';
  }
};

// ─── Grouped Platform Selector (inline) ─────────────────────────────────────
interface GroupedPlatformSelectorProps {
  groups: PlatformGroup[];
  flatPlatforms: PlatformInfo[];
  selected: string[];
  onChange: (selected: string[]) => void;
  columns?: number;
}

const GROUP_LABELS: Record<string, string> = {
  recommended: '推荐',
  tech: '技术社区',
  social: '社交媒体',
  news: '资讯平台',
  '推荐': '推荐',
  '技术社区': '技术社区',
  '社交媒体': '社交媒体',
  '资讯平台': '资讯平台',
};

const GROUP_ICONS: Record<string, string> = {
  '推荐': '★', '技术社区': '◆', '社交媒体': '●', '资讯平台': '▲',
};

// Helper: normalize platform item (could be string or PlatformInfo object)
const normalizePlatformName = (p: unknown): string => {
  if (typeof p === 'string') return p;
  if (p && typeof p === 'object') {
    const obj = p as Record<string, unknown>;
    return (obj.name as string) || (obj.key as string) || '';
  }
  return '';
};

const GroupedPlatformSelector: React.FC<GroupedPlatformSelectorProps> = ({
  groups, flatPlatforms, selected, onChange, columns = 3,
}) => {
  const [activeKeys, setActiveKeys] = useState<string[]>(() => groups.map(g => g.group));

  const toggle = (name: string) => {
    if (selected.includes(name)) {
      onChange(selected.filter(p => p !== name));
    } else {
      onChange([...selected, name]);
    }
  };

  const toggleGroup = (group: PlatformGroup) => {
    const names = group.platforms.map(p => normalizePlatformName(p));
    const allInGroup = names.every(n => selected.includes(n));
    if (allInGroup) {
      onChange(selected.filter(p => !names.includes(p)));
    } else {
      onChange([...new Set([...selected, ...names])]);
    }
  };

  const allPlatformNames = flatPlatforms.map(p => p.name || p.key);
  const allSelected = selected.length === allPlatformNames.length && allPlatformNames.length > 0;
  const indeterminate = selected.length > 0 && selected.length < allPlatformNames.length;

  const handleSelectAll = () => {
    if (allSelected) {
      onChange([]);
    } else {
      onChange(allPlatformNames);
    }
  };

  return (
    <div>
      <div className="mb-2 flex items-center gap-3">
        <Checkbox checked={allSelected} indeterminate={indeterminate} onChange={handleSelectAll}>
          全选
        </Checkbox>
        <Text type="secondary" className="text-xs">
          已选 {selected.length} / {allPlatformNames.length}
        </Text>
      </div>
      {groups.length > 0 ? (
        <Collapse
          activeKey={activeKeys}
          onChange={(keys) => setActiveKeys(typeof keys === 'string' ? [keys] : keys)}
          expandIcon={({ isActive }) => <CaretRightOutlined rotate={isActive ? 90 : 0} />}
          ghost
          size="small"
          items={groups.map(g => {
            const names = g.platforms.map(p => normalizePlatformName(p));
            const groupSelected = names.filter(n => selected.includes(n));
            const groupAll = groupSelected.length === names.length && names.length > 0;
            const groupIndeterminate = groupSelected.length > 0 && groupSelected.length < names.length;
            const label = GROUP_LABELS[g.group] || g.group;
            const icon = GROUP_ICONS[label] || '•';
            return {
              key: g.group,
              label: (
                <Space size={8}>
                  <Checkbox
                    checked={groupAll}
                    indeterminate={groupIndeterminate}
                    onClick={(e) => { e.stopPropagation(); toggleGroup(g); }}
                    onChange={() => {}}
                  />
                  <span className="font-medium">{icon} {label}</span>
                  <Badge count={names.length} className="bg-[var(--border-light)] text-[var(--text-secondary)] text-[11px]" />
                  {groupSelected.length > 0 && (
                    <Tag color="blue" className="text-[11px] !m-0">{groupSelected.length} 已选</Tag>
                  )}
                </Space>
              ),
              children: (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: `repeat(${columns}, 1fr)`,
                  gap: 8,
                  padding: '4px 0',
                }}>
                  {g.platforms.map((p, idx) => {
                    const name = normalizePlatformName(p);
                    const isChecked = selected.includes(name);
                    return (
                      <div
                        key={name || idx}
                        onClick={() => toggle(name)}
                        style={{
                          padding: '8px 12px',
                          border: `2px solid ${isChecked ? 'var(--brand-500)' : 'var(--border-default)'}`,
                          borderRadius: 8,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          background: isChecked ? 'var(--brand-50)' : 'var(--bg-primary)',
                          transition: 'all 0.2s',
                          fontSize: 13,
                        }}
                      >
                        <Checkbox checked={isChecked} onChange={() => toggle(name)} />
                        <span style={{
                          width: 22, height: 22, borderRadius: 4,
                          background: isChecked ? 'var(--brand-500)' : 'var(--border-light)',
                          color: isChecked ? 'var(--bg-primary)' : 'var(--text-tertiary)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 11, fontWeight: 600, flexShrink: 0,
                        }}>
                          {PLATFORM_ICONS[name] || (name ? name[0] : '?')}
                        </span>
                        <span>{name}</span>
                      </div>
                    );
                  })}
                </div>
              ),
            };
          })}
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${columns}, 1fr)`, gap: 8 }}>
          {flatPlatforms.map(p => {
            const name = p.name || p.key;
            const isChecked = selected.includes(name);
            return (
              <div
                key={p.key}
                onClick={() => toggle(name)}
                style={{
                  padding: '8px 12px',
                  border: `2px solid ${isChecked ? 'var(--brand-500)' : 'var(--border-default)'}`,
                  borderRadius: 8, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                  background: isChecked ? 'var(--brand-50)' : 'var(--bg-primary)', transition: 'all 0.2s', fontSize: 13,
                }}
              >
                <Checkbox checked={isChecked} onChange={() => toggle(name)} />
                <span style={{
                  width: 22, height: 22, borderRadius: 4,
                  background: isChecked ? 'var(--brand-500)' : 'var(--border-light)', color: isChecked ? 'var(--bg-primary)' : 'var(--text-tertiary)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 600, flexShrink: 0,
                }}>
                  {PLATFORM_ICONS[name] || name[0]}
                </span>
                <span>{name}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ─── Batch error item type ──────────────────────────────────────────────────
interface BatchErrorItem {
  keyword: string;
  platform: string;
  error_type: string;
  message: string;
}

// ─── Main Page ──────────────────────────────────────────────────────────────
const ArticlesPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { config } = useAppStore();

  // ── List state ─────────────────────────────────────────────────────────
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [totalArticles, setTotalArticles] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [platformGroups, setPlatformGroups] = useState<PlatformGroup[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [savedKeywords, setSavedKeywords] = useState<Keyword[]>([]);
  const [activeTab, setActiveTab] = useState('single');
  const [selectedRows, setSelectedRows] = useState<Article[]>([]);

  // ── Single generation state ────────────────────────────────────────────
  const [streamKey, setStreamKey] = useState(0);
  const [streaming, setStreaming] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [generatedContent, setGeneratedContent] = useState('');
  const [generatedArticleId, setGeneratedArticleId] = useState<number | null>(null);
  const [savingGenerated, setSavingGenerated] = useState(false);
  const [generatedPlatform, setGeneratedPlatform] = useState('');

  // ── Batch generation state ─────────────────────────────────────────────
  const [batchStreamKey, setBatchStreamKey] = useState(0);
  const [batchStreaming, setBatchStreaming] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{
    current: number; total: number; currentKeyword: string; currentPlatform: string; logs: string[];
  } | null>(null);
  const [batchWarnings, setBatchWarnings] = useState<Array<{ field: string; warning: string }>>([]);
  const [batchErrors, setBatchErrors] = useState<BatchErrorItem[]>([]);
  const [batchResult, setBatchResult] = useState<{ success: number; failed: number; errors: BatchErrorItem[] } | null>(null);
  // batchSuccessCount 用于批量进度跟踪（通过 ref 同步），state 保留以备 UI 展示
  const [, setBatchSuccessCount] = useState(0);
  // hasNeverLoaded 标记首次加载状态，用于优化首次渲染体验
  const [, setHasNeverLoaded] = useState(true);
  const [useKeywordPlatforms, setUseKeywordPlatforms] = useState(false);
  const [keywordPlatformsMap, setKeywordPlatformsMap] = useState<Record<string, string[]>>({});

  // Refs for batch counts to avoid stale closures in SSE callbacks
  const batchErrorsRef = useRef<BatchErrorItem[]>([]);
  const batchSuccessRef = useRef(0);
  const batchTotalRef = useRef(0);

  // ── View modal state ──────────────────────────────────────────────────
  const [viewArticle, setViewArticle] = useState<Article | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [viewModalTab, setViewModalTab] = useState('content');
  const [editingView, setEditingView] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editNote, setEditNote] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const [restoringOriginal, setRestoringOriginal] = useState(false);

  // ── Version history state ─────────────────────────────────────────────
  const [versions, setVersions] = useState<ArticleVersion[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [previewVersion, setPreviewVersion] = useState<ArticleVersion | null>(null);
  const [versionPreviewContent, setVersionPreviewContent] = useState('');
  // loadingVersionContent 当前固定为 false（setLoadingVersionContent 未被调用），
  // 保留 state 以便后续接入版本内容加载态
  const [loadingVersionContent] = useState(false);
  const [diffModalVisible, setDiffModalVisible] = useState(false);
  const [diffHtml, setDiffHtml] = useState('');
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [diffVerA, setDiffVerA] = useState<number | null>(null);
  const [diffVerB, setDiffVerB] = useState<number | null>(null);

  // ── Publish modal ─────────────────────────────────────────────────────
  const [publishModal, setPublishModal] = useState<Article | null>(null);
  const [pendingNotice, setPendingNotice] = useState<string | null>(null);

  const [singleForm] = Form.useForm();
  const [batchForm] = Form.useForm();

  const knowledgeBaseEnabled = config?.use_knowledge_base === true;

  // ── Load articles ──────────────────────────────────────────────────────
  const loadArticles = useCallback(async (page: number = currentPage, size: number = pageSize, keyword: string = searchKeyword) => {
    setLoading(true);
    try {
      const data = await articlesApi.list({
        brand: config?.brand,
        page,
        page_size: size,
        ...(keyword ? { keyword } : {}),
      } as Parameters<typeof articlesApi.list>[0]);
      setArticles(data.items);
      setTotalArticles(data.total);
      setHasNeverLoaded(false);
      return data.items;
    } catch (err) {
      console.error('[ArticlesPage] loadArticles failed:', err);
      message.error('加载文章失败');
      return [];
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  }, [config?.brand, currentPage, pageSize, searchKeyword]);

  // Reset to page 1 when search changes
  const handleSearch = (value: string) => {
    setSearchKeyword(value);
    setCurrentPage(1);
    loadArticles(1, pageSize, value);
  };

  const handlePageChange = (page: number, size?: number) => {
    if (size && size !== pageSize) {
      setPageSize(size);
      setCurrentPage(1);
      loadArticles(1, size, searchKeyword);
    } else {
      setCurrentPage(page);
      loadArticles(page, pageSize, searchKeyword);
    }
  };

  // Initial load: run once on mount
  useEffect(() => {
    loadArticles(1, 20, '');
    articlesApi.platforms().then(setPlatforms).catch(() => {});
    articlesApi.platformGroups().then(gs => {
      setPlatformGroups(gs);
    }).catch(() => {});
    keywordsApi.list({ brand: config?.brand, page: 1, page_size: 100 })
      .then(d => setSavedKeywords(d.items)).catch(() => {});
    // 读取从关键词页选择的待生成关键词
    // 优先读取 URL 查询参数 keyword_ids（新版跳转），再通过 API 获取关键词内容；
    // 兼容旧版 sessionStorage 跳转方式
    const keywordIdsParam = searchParams.get('keyword_ids');
    if (keywordIdsParam) {
      const ids = keywordIdsParam
        .split(',')
        .map(s => Number(s.trim()))
        .filter(n => !isNaN(n) && n > 0);
      if (ids.length > 0) {
        keywordsApi.list({ brand: config?.brand, page: 1, page_size: 1000 })
          .then(d => {
            const kws = d.items.filter(k => ids.includes(k.id)).map(k => k.keyword);
            if (kws.length > 0) {
              batchForm.setFieldsValue({ keywords: kws.join('\n') });
              setActiveTab('batch');
              setPendingNotice(`已选择 ${kws.length} 个关键词，请选择平台后点击批量生成`);
            }
          })
          .catch(err => console.warn('[ArticlesPage] 加载待生成关键词失败:', err));
      }
    } else {
      // 兼容旧版 sessionStorage 跳转
      const pendingKws = sessionStorage.getItem('pending_keywords');
      if (pendingKws) {
        try {
          const kws = JSON.parse(pendingKws) as string[];
          if (kws.length > 0) {
            batchForm.setFieldsValue({ keywords: kws.join('\n') });
            setActiveTab('batch');
            setPendingNotice(`已选择 ${kws.length} 个关键词，请选择平台后点击批量生成`);
          }
        } catch (err) {
          console.warn('[ArticlesPage] 解析 pending_keywords 失败:', err);
        }
        sessionStorage.removeItem('pending_keywords');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.brand]);

  // ── Single generation ──────────────────────────────────────────────────
  const startSingleGenerate = () => {
    const values = singleForm.getFieldsValue();
    if (!values.keyword) {
      message.warning('请输入关键词');
      return;
    }
    if (!selectedPlatforms.length) {
      message.warning('请至少选择一个平台');
      return;
    }
    const platform = selectedPlatforms[0];
    setStreaming(true);
    setStreamKey(k => k + 1);
    setWordCount(0);
    setGeneratedContent('');
    setGeneratedArticleId(null);
    setGeneratedPlatform(platform);
    singleForm.setFieldsValue({ _platform: platform });
  };

  const onSingleComplete = (text: string, data?: Record<string, unknown>) => {
    setStreaming(false);
    setWordCount(text.length);
    setGeneratedContent(text);
    // Try to get article ID from complete event data
    const aid = (data?.article_id as number) ?? (data?.id as number) ?? null;
    if (aid) {
      setGeneratedArticleId(aid);
    }
    loadArticles(currentPage, pageSize, searchKeyword).then((items) => {
      // If ID wasn't in event data, find from refreshed list
      if (!aid) {
        const kw = singleForm.getFieldValue('keyword') as string;
        const found = items.find(a => a.keyword === kw && a.platform === generatedPlatform);
        if (found) setGeneratedArticleId(found.id);
      }
    });
  };

  const handleSaveGenerated = async () => {
    if (!generatedArticleId) {
      message.warning('文章尚未保存，请等待生成完成');
      return;
    }
    setSavingGenerated(true);
    try {
      await articlesApi.update(generatedArticleId, { content: generatedContent, note: '编辑器手动修改' });
      message.success('已保存');
      loadArticles(currentPage, pageSize, searchKeyword);
      // Update the local article if it's being viewed
      if (viewArticle && viewArticle.id === generatedArticleId) {
        setViewArticle({ ...viewArticle, content: generatedContent });
      }
    } catch (err) {
      console.error('[ArticlesPage] saveGeneratedEdit failed:', err);
      message.error('保存失败');
    } finally {
      setSavingGenerated(false);
    }
  };

  // ── Batch generation ───────────────────────────────────────────────────
  const startBatchGenerate = () => {
    const values = batchForm.getFieldsValue();
    const kwsStr = values.keywords as string;
    if (!kwsStr || !kwsStr.trim()) {
      message.warning('请输入关键词列表');
      return;
    }
    const kws = kwsStr.split(/[,，\n\s]+/).map((s: string) => s.trim()).filter(Boolean);
    if (!kws.length) {
      message.warning('未解析到有效关键词');
      return;
    }
    if (useKeywordPlatforms) {
      const missingPlatforms = kws.filter(kw => !keywordPlatformsMap[kw] || keywordPlatformsMap[kw].length === 0);
      if (missingPlatforms.length) {
        message.warning(`以下关键词未选择平台: ${missingPlatforms.join(', ')}`);
        return;
      }
    } else {
      if (!selectedPlatforms.length) {
        message.warning('请至少选择一个平台');
        return;
      }
    }
    const totalTasks = useKeywordPlatforms
      ? Object.values(keywordPlatformsMap).reduce((s, arr) => s + arr.length, 0)
      : kws.length * selectedPlatforms.length;
    setBatchStreaming(true);
    setBatchProgress({ current: 0, total: totalTasks, currentKeyword: '', currentPlatform: '', logs: [] });
    setBatchWarnings([]);
    setBatchErrors([]);
    setBatchSuccessCount(0);
    setBatchResult(null);
    // Reset refs synchronously for SSE callbacks
    batchErrorsRef.current = [];
    batchSuccessRef.current = 0;
    batchTotalRef.current = totalTasks;
    setBatchStreamKey(k => k + 1);
  };

  const onBatchMessage = (event: string, data: Record<string, unknown>) => {
    if (event === 'start') {
      // Capture injection warnings from start event
      const warnings = data.warnings as Array<{ field: string; warning: string }> | undefined;
      if (warnings && warnings.length > 0) {
        setBatchWarnings(warnings);
      }
    } else if (event === 'progress') {
      const done = (data.done as number) ?? (data.current as number) ?? 0;
      const tot = (data.total as number) ?? batchTotalRef.current;
      batchTotalRef.current = tot;
      setBatchProgress(prev => ({
        current: done,
        total: tot,
        currentKeyword: (data.keyword as string) ?? prev?.currentKeyword ?? '',
        currentPlatform: (data.platform as string) ?? prev?.currentPlatform ?? '',
        logs: prev?.logs ?? [],
      }));
    } else if (event === 'article_done') {
      batchSuccessRef.current += 1;
      setBatchSuccessCount(batchSuccessRef.current);
      const kw = data.keyword as string;
      const plat = data.platform as string;
      const msg = `[${plat}] ${kw} 生成完成`;
      setBatchProgress(prev => prev ? { ...prev, logs: [...prev.logs.slice(-50), msg] } : prev);
    } else if (event === 'article_error') {
      const errItem: BatchErrorItem = {
        keyword: (data.keyword as string) || '未知关键词',
        platform: (data.platform as string) || '未知平台',
        error_type: (data.error_type as string) || 'other',
        message: (data.message as string) || '未知错误',
      };
      batchErrorsRef.current = [...batchErrorsRef.current, errItem];
      setBatchErrors([...batchErrorsRef.current]);
      const errMsg = `[${errItem.platform}] ${errItem.keyword} 失败: ${classifyError(errItem.error_type, errItem.message)}`;
      setBatchProgress(prev => prev ? { ...prev, logs: [...prev.logs.slice(-50), errMsg] } : prev);
    } else if (event === 'log') {
      const msg = (data.message as string) || '';
      if (msg) {
        setBatchProgress(prev => prev ? { ...prev, logs: [...prev.logs.slice(-50), msg] } : prev);
      }
    }
  };

  const onBatchComplete = () => {
    setBatchStreaming(false);
    const success = batchSuccessRef.current;
    const errors = [...batchErrorsRef.current];
    const failed = errors.length;
    const total = batchTotalRef.current || (success + failed);
    const resultFailed = total - success;
    setBatchResult({ success, failed: resultFailed, errors });
    setBatchProgress(null);
    setBatchSuccessCount(success);
    setBatchErrors(errors);
    loadArticles(currentPage, pageSize, searchKeyword);
    if (resultFailed === total && total > 0) {
      // All failed
      message.error(`批量生成全部失败，共 ${failed} 篇`);
    } else if (resultFailed > 0) {
      message.warning(`批量生成完成：成功 ${success} 篇，失败 ${resultFailed} 篇`);
    } else {
      message.success(`批量生成完成：成功 ${success} 篇`);
    }
  };

  // When batch keywords change, update the keywordPlatformsMap
  const handleBatchKeywordsChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    const kws = val.split(/[,，\n\s]+/).map(s => s.trim()).filter(Boolean);
    setKeywordPlatformsMap(prev => {
      const next: Record<string, string[]> = {};
      for (const kw of kws) {
        next[kw] = prev[kw] || [];
      }
      return next;
    });
  };

  // ── Article actions ────────────────────────────────────────────────────
  const handleDelete = async (id: number) => {
    try {
      await articlesApi.delete(id);
      message.success('已删除');
      // If current page becomes empty after deletion, go back a page
      const newArticles = articles.filter(a => a.id !== id);
      if (newArticles.length === 0 && currentPage > 1) {
        setCurrentPage(currentPage - 1);
      } else {
        loadArticles(currentPage, pageSize, searchKeyword);
      }
      setSelectedRows(prev => prev.filter(r => r.id !== id));
    } catch (err) {
      console.error('[ArticlesPage] handleDelete failed:', err);
      message.error('删除失败');
    }
  };

  const handleBatchDelete = async () => {
    if (!selectedRows.length) return;
    try {
      await Promise.all(selectedRows.map(r => articlesApi.delete(r.id)));
      message.success(`已删除 ${selectedRows.length} 篇文章`);
      setSelectedRows([]);
      // If current page may become empty, go back
      if (articles.length <= selectedRows.length && currentPage > 1) {
        setCurrentPage(currentPage - 1);
      } else {
        loadArticles(currentPage, pageSize, searchKeyword);
      }
    } catch (err) {
      console.error('[ArticlesPage] handleBatchDelete failed:', err);
      message.error('批量删除失败');
    }
  };

  const handleBatchDownload = () => {
    const ids = selectedRows.length ? selectedRows.map(r => r.id) : articles.map(a => a.id);
    if (!ids.length) { message.warning('没有可下载的文章'); return; }
    articlesApi.batchDownload(ids).catch((e: unknown) => {
      message.error('下载失败：' + (e as Error).message);
    });
  };

  const handleViewContent = (article: Article) => {
    setViewArticle(article);
    setModalVisible(true);
    setViewModalTab('content');
    setEditingView(false);
    setEditContent(article.content || '');
    setEditNote('');
    setVersions([]);
    setPreviewVersion(null);
    setVersionPreviewContent('');
  };

  // ── View modal: save edit ──────────────────────────────────────────────
  const handleSaveEdit = async () => {
    if (!viewArticle) return;
    setSavingEdit(true);
    try {
      const updated = await articlesApi.update(viewArticle.id, { content: editContent, note: editNote || '手动编辑' });
      setViewArticle(updated);
      setEditingView(false);
      message.success('已保存');
      loadArticles(currentPage, pageSize, searchKeyword);
    } catch (err) {
      console.error('[ArticlesPage] handleSaveEdit failed:', err);
      message.error('保存失败');
    } finally {
      setSavingEdit(false);
    }
  };

  // ── Restore original content ───────────────────────────────────────────
  const handleRestoreOriginal = async () => {
    if (!viewArticle) return;
    setRestoringOriginal(true);
    try {
      const result = await articlesApi.getOriginalContent(viewArticle.id);
      setEditContent(result.content);
      message.warning('还原后记得点击「保存修改」才能生效');
    } catch (err) {
      console.error('[ArticlesPage] handleRestoreOriginal failed:', err);
      message.error('获取原文失败');
    } finally {
      setRestoringOriginal(false);
    }
  };

  // ── Navigate to optimize / verify ──────────────────────────────────────
  const handleSendToOptimize = () => {
    if (!viewArticle) return;
    // 通过 URL 查询参数传递 article_id（与平台），优化页再调用 API 获取文章内容
    const params = new URLSearchParams();
    if (viewArticle.id) params.set('article_id', String(viewArticle.id));
    if (viewArticle.platform) params.set('platform', viewArticle.platform);
    navigate(`/optimize?${params.toString()}`);
  };

  const handleSendToVerify = () => {
    if (!viewArticle) return;
    // 通过 URL 查询参数传递 article_id（与平台），验证页再调用 API 获取文章内容
    const params = new URLSearchParams();
    if (viewArticle.id) params.set('article_id', String(viewArticle.id));
    if (viewArticle.platform) params.set('platform', viewArticle.platform);
    navigate(`/verify?${params.toString()}`);
  };

  // ── Version history ────────────────────────────────────────────────────
  const loadVersions = async () => {
    if (!viewArticle) return;
    setLoadingVersions(true);
    try {
      const vers = await articlesApi.versions(viewArticle.id);
      setVersions(vers);
    } catch (err) {
      console.error('[ArticlesPage] loadVersions failed:', err);
      message.error('加载版本失败');
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleViewVersion = async (ver: ArticleVersion) => {
    setPreviewVersion(ver);
    setVersionPreviewContent(ver.content);
  };

  const handleRollback = async (verNum: number) => {
    if (!viewArticle) return;
    try {
      const updated = await articlesApi.rollback(viewArticle.id, verNum);
      setViewArticle(updated);
      setEditContent(updated.content || '');
      message.success(`已回滚到版本 ${verNum}`);
      loadVersions();
      loadArticles(currentPage, pageSize, searchKeyword);
    } catch (err) {
      console.error('[ArticlesPage] handleRollback failed:', err);
      message.error('回滚失败');
    }
  };

  const handleShowDiff = async (verA: number, verB?: number) => {
    if (!viewArticle) return;
    setDiffVerA(verA);
    setDiffVerB(verB ?? null);
    setDiffModalVisible(true);
    setLoadingDiff(true);
    setDiffHtml('');
    try {
      const result: DiffResult = await articlesApi.diff(viewArticle.id, verA, verB);
      setDiffHtml(result.diff_html);
    } catch (err) {
      console.error('[ArticlesPage] handleShowDiff failed:', err);
      message.error('加载Diff失败');
    } finally {
      setLoadingDiff(false);
    }
  };

  // Load versions when switching to versions tab
  useEffect(() => {
    if (modalVisible && viewModalTab === 'versions' && viewArticle && versions.length === 0) {
      loadVersions();
    }
  }, [modalVisible, viewModalTab, viewArticle]);

  // ── Table columns ──────────────────────────────────────────────────────
  const columns: ColumnsType<Article> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '关键词', dataIndex: 'keyword', width: 150, ellipsis: true },
    { title: '平台', dataIndex: 'platform', width: 100, render: (p) => p ? <Tag color="blue">{p}</Tag> : '-' },
    {
      title: '状态', dataIndex: 'publish_status', width: 100,
      render: (s: string) => {
        const colorMap: Record<string, string> = { draft: 'default', published: 'green', failed: 'red' };
        const textMap: Record<string, string> = { draft: '草稿', published: '已发布', failed: '失败' };
        return <Tag color={colorMap[s] || 'default'}>{textMap[s] || s}</Tag>;
      }
    },
    { title: '创建时间', dataIndex: 'created_at', width: 160, render: (t) => t ? formatDateTime(t) : '-' },
    {
      title: '操作', width: 200,
      render: (_, r) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewContent(r)}>查看</Button>
          <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => articlesApi.batchDownload([r.id]).catch((e: unknown) => message.error('下载失败：' + (e as Error).message))}>下载</Button>
          <Button type="link" size="small" icon={<CloudUploadOutlined />} onClick={() => setPublishModal(r)}>发布</Button>
          <Popconfirm
            title={`确定删除文章「${r.keyword || '未命名'} - ${r.platform || '未知平台'}」？此操作不可恢复，版本历史也会被删除。`}
            onConfirm={() => handleDelete(r.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const hasConfig = config?.gen_api_key_configured;

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">自动创作</h2>
        <p className="page-desc">基于关键词一键生成各平台 GEO 优化内容</p>
      </div>

      {!hasConfig && (
        <Alert type="warning" showIcon message="请先在系统设置中配置 LLM API Key" className="mb-4" />
      )}

      {pendingNotice && (
        <Alert type="success" showIcon closable message={pendingNotice}
          onClose={() => setPendingNotice(null)} className="mb-4" />
      )}

      <Row gutter={16}>
        {/* ── Left column: Forms ─────────────────────────────────────── */}
        <Col xs={24} lg={10}>
          <Card>
            <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
              // ── Single generation tab ──────────────────────────────
              {
                key: 'single',
                label: <span><EditOutlined />单篇生成</span>,
                children: (
                  <Form form={singleForm} layout="vertical" initialValues={{ word_count: 2000, temperature: 0.7, style: '专业' }}>
                    <Form.Item label="关键词" name="keyword" rules={[{ required: true }]}>
                      <Select
                        showSearch
                        placeholder="输入或选择关键词"
                        options={savedKeywords.map(k => ({ label: k.keyword, value: k.keyword }))}
                        mode="tags"
                        maxCount={1}
                        className="w-full"
                      />
                    </Form.Item>
                    <Form.Item label="目标字数" name="word_count">
                      <InputNumber min={500} max={10000} step={100} className="w-full" />
                    </Form.Item>
                    <Form.Item label="写作风格" name="style">
                      <Select options={[
                        { label: '专业', value: '专业' },
                        { label: '通俗', value: '通俗' },
                        { label: '学术', value: '学术' },
                        { label: '营销', value: '营销' },
                      ]} />
                    </Form.Item>
                    <Form.Item label="温度" name="temperature">
                      <InputNumber min={0} max={1} step={0.05} className="w-full" />
                    </Form.Item>
                    <Form.Item label="选择平台" required>
                      <GroupedPlatformSelector
                        groups={platformGroups}
                        flatPlatforms={platforms}
                        selected={selectedPlatforms}
                        onChange={setSelectedPlatforms}
                        columns={3}
                      />
                    </Form.Item>
                    {knowledgeBaseEnabled && (
                      <Form.Item name="use_knowledge" label="知识库增强" valuePropName="checked" initialValue={false}>
                        <Switch checkedChildren="启用" unCheckedChildren="关闭" />
                      </Form.Item>
                    )}
                    <Button
                      type="primary"
                      icon={<ThunderboltOutlined />}
                      block
                      onClick={startSingleGenerate}
                      disabled={!hasConfig}
                      loading={streaming}
                    >
                      {streaming ? '生成中...' : '开始生成'}
                    </Button>
                  </Form>
                ),
              },
              // ── Batch generation tab ───────────────────────────────
              {
                key: 'batch',
                label: <span><AppstoreOutlined />批量生成</span>,
                children: (
                  <Form form={batchForm} layout="vertical" initialValues={{ word_count: 1500, temperature: 0.7 }}>
                    <Form.Item label="关键词列表（换行/逗号分隔）" name="keywords" rules={[{ required: true }]}>
                      <TextArea rows={4} placeholder="每行一个关键词，或用逗号分隔" onChange={handleBatchKeywordsChange} />
                    </Form.Item>
                    <Form.Item label="目标字数" name="word_count">
                      <InputNumber min={500} max={5000} step={100} className="w-full" />
                    </Form.Item>
                    <Form.Item label="温度" name="temperature">
                      <InputNumber min={0} max={1} step={0.05} className="w-full" />
                    </Form.Item>

                    {knowledgeBaseEnabled && (
                      <Form.Item name="use_knowledge" label="知识库增强" valuePropName="checked" initialValue={false}>
                        <Switch checkedChildren="启用" unCheckedChildren="关闭" />
                      </Form.Item>
                    )}

                    <Form.Item label="选择平台" required={!useKeywordPlatforms}>
                      <GroupedPlatformSelector
                        groups={platformGroups}
                        flatPlatforms={platforms}
                        selected={selectedPlatforms}
                        onChange={setSelectedPlatforms}
                        columns={3}
                      />
                    </Form.Item>

                    <Divider className="my-2" />

                    <Form.Item label="高级：各关键词选择平台" valuePropName="checked">
                      <Switch
                        checked={useKeywordPlatforms}
                        onChange={(val) => {
                          setUseKeywordPlatforms(val);
                          if (!val) {
                            setKeywordPlatformsMap({});
                          } else {
                            // Initialize from textarea
                            const kwsStr = batchForm.getFieldValue('keywords') as string;
                            if (kwsStr) {
                              const kws = kwsStr.split(/[,，\n\s]+/).map((s: string) => s.trim()).filter(Boolean);
                              const map: Record<string, string[]> = {};
                              for (const kw of kws) map[kw] = [];
                              setKeywordPlatformsMap(map);
                            }
                          }
                        }}
                        checkedChildren="开启"
                        unCheckedChildren="关闭"
                      />
                    </Form.Item>

                    {useKeywordPlatforms && (
                      <div className="mb-4 border border-[var(--border-light)] rounded-md overflow-auto max-h-[250px]">
                        <table className="w-full border-collapse text-sm">
                          <thead className="bg-[var(--bg-tertiary)] sticky top-0">
                            <tr>
                              <th className="py-2 px-3 text-left border-b border-[var(--border-light)] w-2/5">关键词</th>
                              <th className="py-2 px-3 text-left border-b border-[var(--border-light)]">选择平台</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(keywordPlatformsMap).map(([kw, plats]) => {
                              const availablePlatforms = platforms.length ? platforms : [];
                              return (
                                <tr key={kw}>
                                  <td className="py-2 px-3 border-b border-[var(--border-light)] font-medium">{kw}</td>
                                  <td className="py-2 px-3 border-b border-[var(--border-light)]">
                                    <Select
                                      mode="multiple"
                                      className="w-full"
                                      placeholder="选择平台"
                                      size="small"
                                      value={plats}
                                      onChange={(vals) => setKeywordPlatformsMap(prev => ({ ...prev, [kw]: vals }))}
                                      options={availablePlatforms.map(p => ({ label: p.name || p.key, value: p.name || p.key }))}
                                      maxTagCount="responsive"
                                    />
                                  </td>
                                </tr>
                              );
                            })}
                            {Object.keys(keywordPlatformsMap).length === 0 && (
                              <tr>
                                <td colSpan={2} className="p-4 text-center text-[var(--text-tertiary)]">
                                  请先输入关键词
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    )}

                    <Button
                      type="primary"
                      icon={<ThunderboltOutlined />}
                      block
                      onClick={startBatchGenerate}
                      disabled={!hasConfig}
                      loading={batchStreaming}
                    >
                      {batchStreaming ? '批量生成中...' : '批量生成'}
                    </Button>
                  </Form>
                ),
              },
            ]} />
          </Card>

          {/* Batch injection warnings */}
          {batchWarnings.length > 0 && (
            <Alert
              type="warning"
              showIcon
              className="mt-4"
              message="参数警告"
              description={
                <ul className="!m-0 pl-5">
                  {batchWarnings.map((w, i) => (
                    <li key={i}><strong>{w.field}:</strong> {w.warning}</li>
                  ))}
                </ul>
              }
              closable
              onClose={() => setBatchWarnings([])}
            />
          )}

          {/* Batch progress */}
          {batchProgress && (
            <Card title="批量生成进度" style={{ marginTop: 16 }} size="small">
              <div className="text-center mb-3">
                <Spin tip={`AI 正在生成第 ${batchProgress.current + 1}/${batchProgress.total} 篇...`}>
                  <div className="min-h-[20px]" />
                </Spin>
              </div>
              <Progress
                percent={batchProgress.total > 0 ? Math.round((batchProgress.current / batchProgress.total) * 100) : 0}
                size="small"
                className="mb-2"
              />
              <div className="mb-2 text-sm">
                <Text strong>正在生成第 {batchProgress.current}/{batchProgress.total} 篇：</Text>
                {batchProgress.currentKeyword && (
                  <Tag color="blue" className="ml-2">{batchProgress.currentKeyword}</Tag>
                )}
                {batchProgress.currentPlatform && (
                  <span>
                    <Text type="secondary" className="mx-1">@</Text>
                    <Tag color="green">{batchProgress.currentPlatform}</Tag>
                  </span>
                )}
              </div>
              <div className="bg-[var(--bg-secondary)] rounded p-2 max-h-[150px] overflow-auto text-xs font-mono">
                {batchProgress.logs.map((log, i) => <div key={i}>{log}</div>)}
              </div>
            </Card>
          )}

          {/* Batch per-article errors during streaming */}
          {batchErrors.length > 0 && batchStreaming && (
            <Alert
              type="error"
              showIcon
              className="mt-4"
              message={`${batchErrors.length} 篇生成失败`}
              description={
                <ul className="!m-0 pl-5 max-h-[120px] overflow-auto">
                  {batchErrors.map((e, i) => (
                    <li key={i} className="text-xs">
                      <Tag color="blue" className="text-[11px]">{e.keyword}</Tag>
                      <Tag color="green" className="text-[11px]">{e.platform}</Tag>
                      <Text type="danger" className="text-xs">{classifyError(e.error_type, e.message)}</Text>
                    </li>
                  ))}
                </ul>
              }
            />
          )}

          {/* Batch result summary */}
          {batchResult && (
            <Alert
              type={batchResult.failed === 0 ? 'success' : batchResult.success === 0 ? 'error' : 'warning'}
              showIcon
              className="mt-4"
              closable
              onClose={() => setBatchResult(null)}
              message={`批量生成完成：成功 ${batchResult.success} 篇，失败 ${batchResult.failed} 篇`}
              description={batchResult.errors.length > 0 ? (
                <div>
                  <div className="mb-1">失败详情：</div>
                  <ul className="!m-0 pl-5 max-h-[150px] overflow-auto">
                    {batchResult.errors.map((e, i) => (
                      <li key={i} className="text-xs mb-[2px]">
                        <Tag color="blue" className="text-[11px]">{e.keyword}</Tag>
                        <Tag color="green" className="text-[11px]">{e.platform}</Tag>
                        <Text type="danger" className="text-xs">
                          {classifyError(e.error_type, e.message)}
                        </Text>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            />
          )}
        </Col>

        {/* ── Right column: Output & Table ─────────────────────────── */}
        <Col xs={24} lg={14}>
          {/* Single generation result */}
          {(streaming || generatedContent || activeTab === 'single') && activeTab === 'single' && (
            <Card
              title="生成结果"
              extra={
                generatedContent && !streaming ? (
                  <Space>
                    <span className="text-xs text-[var(--text-tertiary)]">约 {wordCount} 字</span>
                    <Button size="small" icon={<SaveOutlined />} onClick={handleSaveGenerated} loading={savingGenerated}>
                      保存修改
                    </Button>
                    <Button size="small" icon={<ThunderboltOutlined />} onClick={startSingleGenerate}>重新生成</Button>
                  </Space>
                ) : null
              }
              style={{ marginBottom: 16 }}
            >
              {streaming && (
                <div className="text-center mb-3">
                  <Spin tip="AI 正在创作中..." />
                </div>
              )}
              {streaming || !generatedContent ? (
                <StreamingText
                  key={`article-${streamKey}`}
                  autoStart={streaming}
                  fetchStream={(handlers) => {
                    const values = singleForm.getFieldsValue();
                    articlesApi.generateStream({
                      keyword: values.keyword,
                      platform: values._platform || selectedPlatforms[0],
                      brand: config?.brand,
                      advantages: config?.advantages,
                      word_count: values.word_count,
                      style: values.style,
                      temperature: values.temperature,
                      use_knowledge: values.use_knowledge,
                    }, {
                      ...handlers,
                      onError: (errorData) => {
                        // Reset outer streaming state
                        setStreaming(false);
                        // Classify the error and pass friendly message to StreamingText's internal handler
                        const friendlyMessage = classifyError(
                          errorData.error_type as string | undefined,
                          errorData.message as string | undefined
                        );
                        handlers.onError?.({ ...errorData, message: friendlyMessage });
                      },
                    });
                  }}
                  onComplete={(text, data) => onSingleComplete(text, data)}
                  height={500}
                  placeholder="填写左侧表单并点击「开始生成」"
                />
              ) : (
                <MarkdownEditor
                  value={generatedContent}
                  onChange={setGeneratedContent}
                  height={500}
                  placeholder="生成内容后可在此编辑..."
                />
              )}
            </Card>
          )}

          {/* Batch generation output */}
          {activeTab === 'batch' && (
            <Card title="批量生成输出" style={{ marginBottom: 16 }}>
              {batchStreaming && (
                <div className="text-center mb-3">
                  <Spin tip={batchProgress ? `AI 正在生成第 ${batchProgress.current + 1}/${batchProgress.total} 篇...` : 'AI 正在初始化...'} />
                </div>
              )}
              <StreamingText
                key={`batch-${batchStreamKey}`}
                autoStart={batchStreaming}
                fetchStream={(handlers) => {
                  const values = batchForm.getFieldsValue();
                  const kws = (values.keywords as string).split(/[,，\n\s]+/).map((s: string) => s.trim()).filter(Boolean);
                  const body: Record<string, unknown> = {
                    keywords: kws,
                    brand: config?.brand,
                    advantages: config?.advantages,
                    word_count: values.word_count,
                    temperature: values.temperature,
                    use_knowledge: values.use_knowledge,
                  };
                  if (useKeywordPlatforms) {
                    body.keyword_platforms = keywordPlatformsMap;
                  } else {
                    body.platforms = selectedPlatforms;
                  }
                  articlesApi.batchGenerateStream(body as Parameters<typeof articlesApi.batchGenerateStream>[0], {
                    ...handlers,
                    onEvent: (event, data) => {
                      handlers.onEvent?.(event, data);
                      onBatchMessage(event, data);
                    },
                    onError: (errorData) => {
                      // Handle fatal batch-level errors
                      setBatchStreaming(false);
                      setBatchProgress(null);
                      const friendlyMessage = classifyError(
                        errorData.error_type as string | undefined,
                        errorData.message as string | undefined
                      );
                      handlers.onError?.({ ...errorData, message: friendlyMessage });
                      message.error(friendlyMessage);
                    },
                  });
                }}
                onComplete={onBatchComplete}
                height={300}
                placeholder="填写左侧表单并点击「批量生成」"
              />
            </Card>
          )}

          {/* Articles table */}
          <Card
            title={`已生成文章 (${totalArticles})`}
            extra={
              <Space wrap>
                <Input.Search
                  placeholder="搜索关键词/平台"
                  allowClear
                  size="small"
                  className="w-[180px]"
                  onSearch={handleSearch}
                  onChange={(e) => {
                    if (!e.target.value) handleSearch('');
                  }}
                />
                {selectedRows.length > 0 && (
                  <>
                    <span className="text-xs text-[var(--text-tertiary)]">已选 {selectedRows.length} 篇</span>
                    <Popconfirm
                      title={`确定删除选中的 ${selectedRows.length} 篇文章？此操作不可恢复。`}
                      onConfirm={handleBatchDelete}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button size="small" danger icon={<DeleteOutlined />}>
                        删除选中
                      </Button>
                    </Popconfirm>
                  </>
                )}
                <Button size="small" icon={<DownloadOutlined />} onClick={handleBatchDownload}>
                  {selectedRows.length ? `下载选中(${selectedRows.length})` : '批量下载'}
                </Button>
                <Button size="small" onClick={() => loadArticles(currentPage, pageSize, searchKeyword)}>刷新</Button>
              </Space>
            }
          >
            {initialLoading ? (
              <Skeleton active paragraph={{ rows: 8 }} />
            ) : totalArticles === 0 && !searchKeyword ? (
              <Empty
                description="还没有生成任何文章，去关键词页面选一些词来生成吧"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => navigate('/keywords')}>
                  前往关键词页面
                </Button>
              </Empty>
            ) : (
              <>
                <Table
                  columns={columns}
                  dataSource={articles}
                  rowKey="id"
                  loading={loading}
                  size="small"
                  rowSelection={{
                    selectedRowKeys: selectedRows.map(r => r.id),
                    onChange: (_, rows) => setSelectedRows(rows),
                  }}
                  pagination={false}
                  locale={{
                    emptyText: searchKeyword ? (
                      <Empty description="没有找到匹配的文章" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : (
                      <Empty description="暂无文章数据，请前往「关键词」页面生成内容" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )
                  }}
                  scroll={{ x: 600 }}
                />
                {totalArticles > 0 && (
                  <div className="mt-4 text-right">
                    <Pagination
                      current={currentPage}
                      pageSize={pageSize}
                      total={totalArticles}
                      showSizeChanger
                      showQuickJumper
                      showTotal={(total) => `共 ${total} 篇`}
                      pageSizeOptions={['10', '20', '50', '100']}
                      onChange={handlePageChange}
                    />
                  </div>
                )}
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* ── Article View / Edit Modal ──────────────────────────────────── */}
      <Modal
        title={viewArticle?.filename || `文章 #${viewArticle?.id}`}
        open={modalVisible}
        onCancel={() => { setModalVisible(false); setEditingView(false); setPreviewVersion(null); }}
        width={860}
        footer={null}
      >
        {viewArticle && (
          <Tabs
            activeKey={viewModalTab}
            onChange={setViewModalTab}
            tabBarExtraContent={
              viewModalTab === 'content' ? (
                <Space>
                  {!editingView ? (
                    <Button size="small" icon={<EditOutlined />} onClick={() => { setEditContent(viewArticle.content || ''); setEditingView(true); }}>
                      编辑
                    </Button>
                  ) : (
                    <>
                      <Button size="small" onClick={() => { setEditingView(false); setEditContent(viewArticle.content || ''); }}>
                        取消
                      </Button>
                      <Tooltip title="还原到版本1的原始内容，覆盖当前编辑区">
                        <Button
                          size="small"
                          icon={<UndoOutlined />}
                          onClick={handleRestoreOriginal}
                          loading={restoringOriginal}
                        >
                          还原原文
                        </Button>
                      </Tooltip>
                      <Button size="small" type="primary" icon={<SaveOutlined />} onClick={handleSaveEdit} loading={savingEdit}>
                        保存修改
                      </Button>
                    </>
                  )}
                </Space>
              ) : null
            }
            items={[
              // Content tab
              {
                key: 'content',
                label: <span><FileTextOutlined />内容</span>,
                children: (
                  <div>
                    {!editingView ? (
                      <div>
                        {/* Action buttons */}
                        <div className="mb-3 flex gap-2 flex-wrap">
                          <Button size="small" type="primary" icon={<RocketOutlined />} onClick={handleSendToOptimize}>
                            发送到优化
                          </Button>
                          <Button size="small" icon={<CheckCircleOutlined />} onClick={handleSendToVerify}>
                            发送到验证
                          </Button>
                          <Button size="small" icon={<DownloadOutlined />} onClick={() => articlesApi.batchDownload([viewArticle.id]).catch((e: unknown) => message.error('下载失败：' + (e as Error).message))}>
                            下载
                          </Button>
                        </div>
                        {/* Article metadata */}
                        <Space className="mb-3" split={<Divider type="vertical" />}>
                          {viewArticle.keyword && <Tag color="blue">关键词: {viewArticle.keyword}</Tag>}
                          {viewArticle.platform && <Tag color="green">平台: {viewArticle.platform}</Tag>}
                          {viewArticle.created_at && <Text type="secondary" className="text-xs">{formatDateTime(viewArticle.created_at)}</Text>}
                        </Space>
                        <Divider className="my-2" />
                        {/* Content */}
                        <div className="markdown-preview max-h-[500px] overflow-auto">
                          {viewArticle.content ? <ReactMarkdown>{viewArticle.content}</ReactMarkdown> : <Empty description="无内容" />}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <Form layout="vertical" className="mb-2">
                          <Form.Item label="编辑备注（可选）" className="mb-2">
                            <Input
                              size="small"
                              placeholder="描述本次修改的内容"
                              value={editNote}
                              onChange={(e) => setEditNote(e.target.value)}
                            />
                          </Form.Item>
                        </Form>
                        <Alert
                          type="info"
                          showIcon
                          message="提示：点击「还原原文」可恢复版本1原始内容，点击「保存修改」后生效"
                          className="mb-2"
                          closable
                        />
                        <MarkdownEditor
                          value={editContent}
                          onChange={setEditContent}
                          height={450}
                          placeholder="编辑文章内容..."
                        />
                      </div>
                    )}
                  </div>
                ),
              },
              // Version history tab
              {
                key: 'versions',
                label: <span><HistoryOutlined />历史版本</span>,
                children: (
                  <div>
                    {loadingVersions ? (
                      <div className="text-center p-10"><Spin /></div>
                    ) : versions.length === 0 ? (
                      <Empty description="暂无历史版本" />
                    ) : (
                      <Row gutter={16}>
                        {/* Version list */}
                        <Col span={previewVersion ? 10 : 24}>
                          <div className="max-h-[520px] overflow-auto border border-[var(--border-light)] rounded-md">
                            {versions.map(ver => {
                              const sourceMap: Record<string, { label: string; color: string }> = {
                                generate: { label: '生成', color: 'blue' },
                                edit: { label: '编辑', color: 'orange' },
                                rollback: { label: '回滚', color: 'purple' },
                                optimize: { label: '优化', color: 'green' },
                              };
                              const src = sourceMap[ver.source] || { label: ver.source, color: 'default' };
                              const isCurrent = ver === previewVersion;
                              return (
                                <div
                                  key={ver.id}
                                  onClick={() => handleViewVersion(ver)}
                                  style={{
                                    padding: '10px 12px',
                                    borderBottom: '1px solid var(--border-light)',
                                    cursor: 'pointer',
                                    background: isCurrent ? 'var(--brand-50)' : 'var(--bg-primary)',
                                    transition: 'background 0.2s',
                                  }}
                                >
                                  <div className="flex justify-between items-center mb-1">
                                    <Space>
                                      <Text strong>版本 {ver.version_number}</Text>
                                      <Tag color={src.color} className="!m-0">{src.label}</Tag>
                                    </Space>
                                    <Text type="secondary" className="text-xs">
                                      {ver.created_at ? formatDateTime(ver.created_at) : ''}
                                    </Text>
                                  </div>
                                  {ver.note && (
                                    <div className="text-xs text-[var(--text-secondary)] mb-[6px]">{ver.note}</div>
                                  )}
                                  <div className="flex gap-1">
                                    <Button
                                      size="small"
                                      icon={<RollbackOutlined />}
                                      onClick={(e) => { e.stopPropagation(); handleRollback(ver.version_number); }}
                                    >
                                      回滚
                                    </Button>
                                    <Button
                                      size="small"
                                      icon={<DiffOutlined />}
                                      onClick={(e) => { e.stopPropagation(); handleShowDiff(ver.version_number); }}
                                    >
                                      与当前Diff
                                    </Button>
                                    {ver.version_number > 1 && (
                                      <Button
                                        size="small"
                                        icon={<SwapOutlined />}
                                        onClick={(e) => { e.stopPropagation(); handleShowDiff(ver.version_number - 1, ver.version_number); }}
                                      >
                                        查看Diff
                                      </Button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </Col>
                        {/* Version preview */}
                        {previewVersion && (
                          <Col span={14}>
                            <Card
                              size="small"
                              title={`版本 ${previewVersion.version_number} 预览`}
                              extra={
                                <Button size="small" onClick={() => setPreviewVersion(null)}>关闭</Button>
                              }
                              className="max-h-[520px] overflow-auto"
                            >
                              {loadingVersionContent ? (
                                <div className="text-center p-5"><Spin /></div>
                              ) : (
                                <div className="markdown-preview max-h-[450px] overflow-auto">
                                  <ReactMarkdown>{versionPreviewContent}</ReactMarkdown>
                                </div>
                              )}
                            </Card>
                          </Col>
                        )}
                      </Row>
                    )}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Modal>

      {/* ── Diff Modal ─────────────────────────────────────────────────── */}
      <Modal
        title={`版本对比: ${diffVerB ? `v${diffVerA} vs v${diffVerB}` : `v${diffVerA} vs 当前`}`}
        open={diffModalVisible}
        onCancel={() => setDiffModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDiffModalVisible(false)}>关闭</Button>,
        ]}
      >
        {loadingDiff ? (
          <div className="text-center p-10"><Spin tip="加载Diff..." /></div>
        ) : diffHtml ? (
          <div
            className="max-h-[500px] overflow-auto p-4 border border-[var(--border-light)] rounded-md bg-white"
            // 后端返回的 diff HTML 必须先经过 DOMPurify 清洗，防止 XSS 注入
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(diffHtml, { USE_PROFILES: { html: true } }) }}
          />
        ) : (
          <Empty description="无差异内容" />
        )}
      </Modal>

      {/* ── Publish Modal ──────────────────────────────────────────────── */}
      <Modal
        title={`发布文章 #${publishModal?.id}`}
        open={!!publishModal}
        onCancel={() => setPublishModal(null)}
        footer={null}
      >
        <PublishForm
          article={publishModal}
          platforms={platforms}
          onComplete={() => { setPublishModal(null); loadArticles(currentPage, pageSize, searchKeyword); }}
        />
      </Modal>
    </div>
  );
};

// ─── Publish Form Sub-component ───────────────────────────────────────────
const PublishForm: React.FC<{ article: Article | null; platforms: PlatformInfo[]; onComplete: () => void }> = ({ article, platforms, onComplete }) => {
  const [platform, setPlatform] = useState(article?.platform || '');
  const [method, setMethod] = useState('copy');
  const [publishing, setPublishing] = useState(false);
  const [result, setResult] = useState<{ content?: string; message?: string; publish_url?: string } | null>(null);

  const platformInfo = platforms.find(p => p.name === platform || p.key === platform);

  const handlePublish = async () => {
    if (!article) return;
    setPublishing(true);
    setResult(null);
    try {
      const res = await (await import('@/api/platforms')).platformsApi.publish(article.id, {
        platform,
        publish_method: method,
      });
      setResult(res);
      message.success(res.message || '发布操作完成');
      // 发布成功后通知父组件关闭弹窗并刷新列表
      onComplete();
    } catch (e: unknown) {
      const err = e as Error;
      message.error('发布失败: ' + (err?.message || ''));
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div>
      <Form layout="vertical">
        <Form.Item label="平台">
          <Select value={platform} onChange={setPlatform} placeholder="选择发布平台">
            {platforms.map(p => (
              <Select.Option key={p.key} value={p.name}>{p.name}</Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item label="发布方式">
          <Select value={method} onChange={setMethod}>
            <Select.Option value="copy">复制到剪贴板</Select.Option>
            {platformInfo?.publish_methods.map(m => (
              <Select.Option key={m} value={m}>{m === 'github' ? 'GitHub Issue' : m === 'api' ? 'API 发布' : m}</Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Button type="primary" block onClick={handlePublish} loading={publishing} disabled={!platform}>
          {publishing ? '发布中...' : '确认发布'}
        </Button>
      </Form>
      {result?.content && (
        <div className="mt-4">
          <Alert type="success" message={result.message || '发布内容已准备好，请手动复制：'} className="mb-2" />
          <TextArea value={result.content} rows={8} readOnly />
        </div>
      )}
      {result?.publish_url && (
        <Alert type="success" message={`发布成功：${result.publish_url}`} className="mt-2" />
      )}
    </div>
  );
};

export default ArticlesPage;
