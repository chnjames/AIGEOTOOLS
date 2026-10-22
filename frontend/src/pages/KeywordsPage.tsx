import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Card, Tabs, Form, Input, InputNumber, Button, Space, Table, Tag, message,
  Switch, Row, Col, Popconfirm, Typography, Spin, Empty, Alert, Select, Statistic, Divider,
  Modal, Pagination, Popover, Tooltip, Dropdown,
} from 'antd';
import {
  SearchOutlined, ReloadOutlined, DeleteOutlined, ThunderboltOutlined,
  ClusterOutlined, BranchesOutlined, UndoOutlined, FileTextOutlined,
  BarChartOutlined, StarFilled, StarOutlined, PlusOutlined, ImportOutlined,
  WarningOutlined, DownOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { keywordsApi } from '@/api/keywords';
import { StreamingText } from '@/components';
import { useAppStore } from '@/stores';
import { getEChartsThemeColors, getLegendBase } from '@/utils/echartsTheme';
import type { Keyword, KeywordQuality, IndustryPreset, InjectionWarning } from '@/types';
import { formatDateTime, formatDate } from '@/utils/dateFormat';

const { Paragraph, Text } = Typography;
const { TextArea } = Input;

/** Parse a markdown/yaml-style keyword list from streaming text into a string array */
function parseKeywordsFromText(text: string): string[] {
  if (!text) return [];
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const kws: string[] = [];
  for (const line of lines) {
    let cleaned = line
      .replace(/^[-*•·]\s*/, '')
      .replace(/^\d+[.)、]\s*/, '')
      .replace(/^>\s*/, '')
      .replace(/^\*\*|\*\*$/g, '')
      .replace(/^["'`]|["'`]$/g, '')
      .trim();
    const parts = cleaned.split(/[,，；;]/).map(p => p.trim()).filter(Boolean);
    for (const p of parts) {
      if (p && p.length <= 100 && !/^(#{1,6}\s|```)/.test(p)) {
        kws.push(p);
      }
    }
  }
  return [...new Set(kws)];
}

/** Parse tags field (JSON array string or comma-separated) into string[] */
function parseTags(tagsStr: string | undefined | null): string[] {
  if (!tagsStr) return [];
  try {
    const parsed = JSON.parse(tagsStr);
    if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
  } catch { /* not JSON - intentional fallback */ }
  return tagsStr.split(/[,，;；]/).map(t => t.trim()).filter(Boolean);
}

const KeywordsPage: React.FC = () => {
  const navigate = useNavigate();
  const { config, darkMode } = useAppStore();

  // ── Pagination & filtering ─────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalKeywords, setTotalKeywords] = useState(0);
  const [searchText, setSearchText] = useState('');
  const [filterTag, setFilterTag] = useState<string | undefined>();
  const [filterFavorite, setFilterFavorite] = useState(false);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>();

  // ── Core keyword list (saved) ──────────────────────────────────────────
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(false);
  const [allKnownTags, setAllKnownTags] = useState<string[]>([]);

  // ── Tabs & streaming ───────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('combo');
  const [streamKey, setStreamKey] = useState(0);
  const [streamResult, setStreamResult] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [comboKeywords, setComboKeywords] = useState<string[]>([]);

  // ── Streaming feedback (warnings / errors / progress) ──────────────────
  const [injectionWarnings, setInjectionWarnings] = useState<InjectionWarning[]>([]);
  const [streamError, setStreamError] = useState<{ error_type?: string; message: string } | null>(null);
  const [streamProgress, setStreamProgress] = useState<{ current?: number; total?: number; message?: string }>({});

  // ── Industry presets ───────────────────────────────────────────────────
  const [industryPresets, setIndustryPresets] = useState<IndustryPreset[]>([]);
  const [selectedIndustry, setSelectedIndustry] = useState<string | undefined>();
  const [seedTagKeywords, setSeedTagKeywords] = useState<string[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(false);

  // ── Quality analysis ───────────────────────────────────────────────────
  const [quality, setQuality] = useState<KeywordQuality | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  // ── Table row selection ────────────────────────────────────────────────
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  // ── Expand (语义扩展) tab ──────────────────────────────────────────────
  const [expandKeywords, setExpandKeywords] = useState<string[]>([]);
  const [undoStack, setUndoStack] = useState<string[][]>([]);
  const [expandStreamKey, setExpandStreamKey] = useState(0);
  const [expandStreamResult, setExpandStreamResult] = useState('');
  const [expandStreaming, setExpandStreaming] = useState(false);

  // ── Tag editing popover state ──────────────────────────────────────────
  const [tagEditId, setTagEditId] = useState<number | null>(null);
  const [tagInputValue, setTagInputValue] = useState('');

  // ── History import modal ───────────────────────────────────────────────
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [historyKeywords, setHistoryKeywords] = useState<Keyword[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  // historyPageSize 固定为 20（setHistoryPageSize 未被调用），保留 state 以便后续接入动态分页
  const [historyPageSize] = useState(20);
  const [historySearch, setHistorySearch] = useState('');
  const [historySearchVal, setHistorySearchVal] = useState('');
  const [historySelectedKeys, setHistorySelectedKeys] = useState<React.Key[]>([]);
  const historySearchTimer = useRef<ReturnType<typeof setTimeout>>();

  const [comboForm] = Form.useForm();
  const [llmForm] = Form.useForm();
  const [mineForm] = Form.useForm();
  const [expandForm] = Form.useForm();

  const hasConfig = config?.gen_api_key_configured;

  // ── Collect unique tags from keywords ──────────────────────────────────
  const collectTags = useCallback((items: Keyword[]) => {
    const tagSet = new Set<string>();
    for (const item of items) {
      for (const t of parseTags(item.tags)) {
        tagSet.add(t);
      }
    }
    setAllKnownTags(prev => {
      const merged = new Set(prev);
      tagSet.forEach(t => merged.add(t));
      return [...merged].sort();
    });
  }, []);

  // ── Load saved keywords ────────────────────────────────────────────────
  const loadKeywords = useCallback(async (page?: number, page_size?: number) => {
    const p = page ?? currentPage;
    const ps = page_size ?? pageSize;
    setLoading(true);
    try {
      const data = await keywordsApi.list({
        brand: config?.brand,
        page: p,
        page_size: ps,
        search: searchText || undefined,
        tag: filterTag || undefined,
        is_favorite: filterFavorite || undefined,
      });
      setKeywords(data.items);
      setTotalKeywords(data.total);
      collectTags(data.items);
      return data.items;
    } catch (err) {
      console.error('[KeywordsPage] loadKeywords failed:', err);
      message.error('加载关键词失败');
      return [];
    } finally {
      setLoading(false);
    }
  }, [config?.brand, currentPage, pageSize, searchText, filterTag, filterFavorite, collectTags]);

  // Reload when page/pageSize/filters change
  useEffect(() => {
    loadKeywords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, pageSize, filterTag, filterFavorite]);

  // Debounced search
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setCurrentPage(1);
      loadKeywords(1, pageSize);
    }, 400);
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText]);

  // ── Load industry presets on mount ─────────────────────────────────────
  useEffect(() => {
    let alive = true;
    async function load() {
      setPresetsLoading(true);
      try {
        const presets = await keywordsApi.industryPresets();
        if (alive) setIndustryPresets(presets);
      } catch (err) {
        console.error('[KeywordsPage] 加载行业预设失败:', err);
      } finally {
        if (alive) setPresetsLoading(false);
      }
    }
    load();
    return () => { alive = false; };
  }, []);

  // ── Run quality analysis helper ────────────────────────────────────────
  const runQualityAnalysis = useCallback(async (kwList: string[]) => {
    if (!kwList.length) { setQuality(null); return; }
    setQualityLoading(true);
    try {
      const result = await keywordsApi.analyzeQuality(kwList);
      setQuality(result);
    } catch (err) {
      console.error('[KeywordsPage] runQualityAnalysis failed:', err);
      message.error('质量分析失败');
    } finally {
      setQualityLoading(false);
    }
  }, []);

  // ── Industry preset selection ──────────────────────────────────────────
  const handleIndustryChange = useCallback((val: string) => {
    setSelectedIndustry(val);
    const preset = industryPresets.find(p => p.key === val);
    if (!preset) { setSeedTagKeywords([]); return; }
    setSeedTagKeywords(preset.seed_keywords);
    const firstKw = preset.seed_keywords[0];
    if (firstKw) {
      comboForm.setFieldsValue({ core_keyword: firstKw });
      llmForm.setFieldsValue({ core_keyword: firstKw });
      mineForm.setFieldsValue({ keyword: firstKw });
    }
  }, [industryPresets, comboForm, llmForm, mineForm]);

  const handleSeedTagClick = useCallback((kw: string) => {
    switch (activeTab) {
      case 'combo':  comboForm.setFieldsValue({ core_keyword: kw }); break;
      case 'llm':    llmForm.setFieldsValue({ core_keyword: kw }); break;
      case 'mine':   mineForm.setFieldsValue({ keyword: kw }); break;
      case 'expand': expandForm.setFieldsValue({ keywords: kw }); break;
    }
  }, [activeTab, comboForm, llmForm, mineForm, expandForm]);

  // ── Combo tab ──────────────────────────────────────────────────────────
  const handleCombo = useCallback((values: Record<string, unknown>) => {
    const core = values.core_keyword as string;
    const max = values.max_results as number || 50;
    keywordsApi.combinations(core, max).then(kws => {
      setComboKeywords(kws);
      message.success(`生成了 ${kws.length} 个组合关键词`);
    }).catch(() => message.error('生成失败'));
  }, []);

  const saveComboKeywords = useCallback(async () => {
    if (!comboKeywords.length) return;
    try {
      const res = await keywordsApi.create(comboKeywords, config?.brand || '');
      const dup = res.duplicates_skipped;
      if (dup > 0) {
        message.success(`成功保存 ${res.saved.length} 个关键词（跳过 ${dup} 个重复）`);
      } else {
        message.success(`成功保存 ${res.saved.length} 个关键词`);
      }
      const items = await loadKeywords(currentPage, pageSize);
      setComboKeywords([]);
      runQualityAnalysis(items.map(k => k.keyword));
    } catch (err) { console.error('[KeywordsPage] handleSaveCombo failed:', err); message.error('保存失败'); }
  }, [comboKeywords, config?.brand, loadKeywords, runQualityAnalysis, currentPage, pageSize]);

  // ── LLM generate tab ──────────────────────────────────────────────────
  const startLLMGenerate = useCallback(() => {
    const values = llmForm.getFieldsValue();
    if (!values.core_keyword) { message.warning('请输入核心关键词'); return; }
    setStreaming(true);
    setStreamResult('');
    setQuality(null);
    setInjectionWarnings([]);
    setStreamError(null);
    setStreamProgress({});
    setStreamKey(k => k + 1);
  }, []);

  const onLLMComplete = useCallback((text: string, data?: Record<string, unknown>) => {
    setStreaming(false);
    setStreamResult(text);
    // Show duplicate feedback if present in complete data
    if (data) {
      const saved = Number(data.saved_count ?? data.saved ?? 0);
      const dup = Number(data.duplicates_skipped ?? 0);
      if (saved > 0 || dup > 0) {
        if (dup > 0) {
          message.success(`成功保存 ${saved} 个关键词（跳过 ${dup} 个重复）`);
        } else {
          message.success(`成功保存 ${saved} 个关键词`);
        }
      }
    }
    loadKeywords(currentPage, pageSize).then(items => {
      runQualityAnalysis(items.map(k => k.keyword));
    });
  }, [loadKeywords, runQualityAnalysis, currentPage, pageSize]);

  // ── Save parsed LLM/mine streaming results ─────────────────────────────
  const saveStreamKeywords = useCallback(async () => {
    const kws = parseKeywordsFromText(streamResult);
    if (!kws.length) { message.warning('没有可保存的关键词'); return; }
    try {
      const res = await keywordsApi.create(kws, config?.brand || '');
      const dup = res.duplicates_skipped;
      if (dup > 0) {
        message.success(`成功保存 ${res.saved.length} 个关键词（跳过 ${dup} 个重复）`);
      } else {
        message.success(`成功保存 ${res.saved.length} 个关键词`);
      }
      const items = await loadKeywords(currentPage, pageSize);
      runQualityAnalysis(items.map(k => k.keyword));
    } catch (err) { console.error('[KeywordsPage] handleSaveLLM failed:', err); message.error('保存失败'); }
  }, [streamResult, config?.brand, loadKeywords, runQualityAnalysis, currentPage, pageSize]);

  // ── Mine tab ───────────────────────────────────────────────────────────
  const startMine = useCallback(() => {
    const values = mineForm.getFieldsValue();
    if (!values.keyword) { message.warning('请输入目标关键词'); return; }
    setStreaming(true);
    setStreamResult('');
    setQuality(null);
    setInjectionWarnings([]);
    setStreamError(null);
    setStreamProgress({});
    setStreamKey(k => k + 1);
  }, []);

  const onMineComplete = useCallback((text: string, data?: Record<string, unknown>) => {
    setStreaming(false);
    setStreamResult(text);
    if (data) {
      const saved = Number(data.saved_count ?? data.saved ?? 0);
      const dup = Number(data.duplicates_skipped ?? 0);
      if (saved > 0 || dup > 0) {
        if (dup > 0) {
          message.success(`成功保存 ${saved} 个关键词（跳过 ${dup} 个重复）`);
        } else {
          message.success(`成功保存 ${saved} 个关键词`);
        }
      }
    }
    const mined = parseKeywordsFromText(text);
    if (mined.length) runQualityAnalysis(mined);
  }, [runQualityAnalysis]);

  // ── Expand (语义扩展) tab ──────────────────────────────────────────────
  const MAX_UNDO = 10;

  const startExpand = useCallback(() => {
    const values = expandForm.getFieldsValue();
    const inputText = values.keywords as string || '';
    const inputKws = parseKeywordsFromText(inputText);
    const base = expandKeywords.length ? expandKeywords : inputKws;
    if (!base.length) { message.warning('请输入或已有要扩展的关键词'); return; }

    setUndoStack(prev => {
      const next = [...prev, [...expandKeywords]];
      return next.length > MAX_UNDO ? next.slice(-MAX_UNDO) : next;
    });

    setExpandStreaming(true);
    setExpandStreamResult('');
    setStreamError(null);
    setExpandStreamKey(k => k + 1);
  }, [expandForm, expandKeywords]);

  const onExpandComplete = useCallback((text: string) => {
    setExpandStreaming(false);
    setExpandStreamResult(text);
    const newKws = parseKeywordsFromText(text);
    const merged = [...new Set([...expandKeywords, ...newKws])];
    setExpandKeywords(merged);
    if (merged.length) runQualityAnalysis(merged);
  }, [expandKeywords, runQualityAnalysis]);

  const handleUndo = useCallback(() => {
    setUndoStack(prev => {
      if (!prev.length) { message.info('没有可撤销的操作'); return prev; }
      const last = prev[prev.length - 1];
      setExpandKeywords(last);
      setQuality(null);
      if (last.length) runQualityAnalysis(last);
      return prev.slice(0, -1);
    });
  }, [runQualityAnalysis]);

  const saveExpandKeywords = useCallback(async () => {
    if (!expandKeywords.length) return;
    try {
      const res = await keywordsApi.create(expandKeywords, config?.brand || '');
      const dup = res.duplicates_skipped;
      if (dup > 0) {
        message.success(`成功保存 ${res.saved.length} 个关键词（跳过 ${dup} 个重复）`);
      } else {
        message.success(`成功保存 ${res.saved.length} 个关键词`);
      }
      const items = await loadKeywords(currentPage, pageSize);
      runQualityAnalysis(items.map(k => k.keyword));
    } catch (err) { console.error('[KeywordsPage] handleSaveExpand failed:', err); message.error('保存失败'); }
  }, [expandKeywords, config?.brand, loadKeywords, runQualityAnalysis, currentPage, pageSize]);

  const addInputToExpandList = useCallback(() => {
    const values = expandForm.getFieldsValue();
    const inputKws = parseKeywordsFromText(values.keywords || '');
    if (!inputKws.length) { message.warning('请先输入关键词'); return; }
    setUndoStack(prev => {
      const next = [...prev, [...expandKeywords]];
      return next.length > MAX_UNDO ? next.slice(-MAX_UNDO) : next;
    });
    const merged = [...new Set([...expandKeywords, ...inputKws])];
    setExpandKeywords(merged);
    expandForm.setFieldsValue({ keywords: '' });
    runQualityAnalysis(merged);
  }, [expandForm, expandKeywords, runQualityAnalysis]);

  const clearExpandKeywords = useCallback(() => {
    setUndoStack(prev => {
      const next = [...prev, [...expandKeywords]];
      return next.length > MAX_UNDO ? next.slice(-MAX_UNDO) : next;
    });
    setExpandKeywords([]);
    setQuality(null);
  }, [expandKeywords]);

  // ── Favorites ──────────────────────────────────────────────────────────
  const handleToggleFavorite = useCallback(async (id: number) => {
    const kw = keywords.find(k => k.id === id);
    if (!kw) return;
    // Optimistic update
    setKeywords(prev => prev.map(k => k.id === id ? { ...k, is_favorite: !k.is_favorite } : k));
    try {
      await keywordsApi.toggleFavorite(id);
    } catch (err) {
      console.error('[KeywordsPage] handleToggleFavorite failed:', err);
      // Revert on failure
      setKeywords(prev => prev.map(k => k.id === id ? { ...k, is_favorite: !k.is_favorite } : k));
      message.error('操作失败');
    }
  }, [keywords]);

  // ── Tags: remove a single tag ──────────────────────────────────────────
  const handleRemoveTag = useCallback(async (id: number, tagToRemove: string) => {
    const kw = keywords.find(k => k.id === id);
    if (!kw) return;
    const currentTags = parseTags(kw.tags);
    const newTags = currentTags.filter(t => t !== tagToRemove);
    // Optimistic update
    setKeywords(prev => prev.map(k => k.id === id ? { ...k, tags: JSON.stringify(newTags) } : k));
    try {
      const updated = await keywordsApi.setTags(id, newTags);
      setKeywords(prev => prev.map(k => k.id === id ? updated : k));
      collectTags([updated]);
    } catch (err) {
      console.error('[KeywordsPage] handleRemoveTag failed:', err);
      // Revert
      setKeywords(prev => prev.map(k => k.id === id ? kw : k));
      message.error('标签删除失败');
    }
  }, [keywords, collectTags]);

  // ── Tags: add tags via popover ─────────────────────────────────────────
  const handleAddTagsSubmit = useCallback(async () => {
    if (tagEditId === null) return;
    const kw = keywords.find(k => k.id === tagEditId);
    if (!kw) return;
    const newTags = parseTags(tagInputValue);
    if (!newTags.length) { setTagEditId(null); setTagInputValue(''); return; }
    const currentTags = parseTags(kw.tags);
    const merged = [...new Set([...currentTags, ...newTags])];
    setKeywords(prev => prev.map(k => k.id === tagEditId ? { ...k, tags: JSON.stringify(merged) } : k));
    try {
      const updated = await keywordsApi.setTags(tagEditId, merged);
      setKeywords(prev => prev.map(k => k.id === tagEditId ? updated : k));
      collectTags([updated]);
      message.success('标签已添加');
    } catch (err) {
      console.error('[KeywordsPage] handleAddTags failed:', err);
      setKeywords(prev => prev.map(k => k.id === tagEditId ? kw : k));
      message.error('标签添加失败');
    }
    setTagEditId(null);
    setTagInputValue('');
  }, [tagEditId, tagInputValue, keywords, collectTags]);

  // ── Delete ─────────────────────────────────────────────────────────────
  const handleDelete = useCallback(async (id: number) => {
    await keywordsApi.delete(id);
    message.success('已删除');
    // If deleting last item on current page, go back one page
    const items = await loadKeywords(
      keywords.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage,
      pageSize
    );
    if (keywords.length === 1 && currentPage > 1) setCurrentPage(p => Math.max(1, p - 1));
    if (items.length) runQualityAnalysis(items.map(k => k.keyword));
    else setQuality(null);
    setSelectedRowKeys(prev => prev.filter(k => k !== id));
  }, [loadKeywords, runQualityAnalysis, keywords.length, currentPage, pageSize]);

  const handleDeleteAll = useCallback(async () => {
    await keywordsApi.deleteAll(config?.brand || '');
    message.success('已清空');
    setKeywords([]);
    setTotalKeywords(0);
    setCurrentPage(1);
    setSelectedRowKeys([]);
    setQuality(null);
  }, [config?.brand]);

  // ── Analyze saved keywords quality ────────────────────────────────────
  const analyzeSavedQuality = useCallback(async () => {
    // Load first page to get keywords, but for analysis load all
    try {
      const data = await keywordsApi.list({ brand: config?.brand, page: 1, page_size: 1000 });
      const kwStrings = data.items.map(k => k.keyword);
      if (!kwStrings.length) { message.warning('暂无已保存关键词'); return; }
      runQualityAnalysis(kwStrings);
    } catch (err) { console.error('[KeywordsPage] analyzeSavedQuality failed:', err); message.error('加载关键词失败'); }
  }, [config?.brand, runQualityAnalysis]);

  // ── Generate content from selected keywords ───────────────────────────
  const handleGenerateContent = useCallback(() => {
    const count = selectedRowKeys.length;
    if (!count) { message.warning('请先选择关键词'); return; }
    // 通过 URL 查询参数传递选中的关键词 ID，文章页再调用 API 获取关键词内容
    const selectedIds = keywords
      .filter(k => selectedRowKeys.includes(k.id))
      .map(k => k.id);
    message.success(`已选择 ${count} 个关键词，正在跳转...`);
    navigate(`/articles?keyword_ids=${selectedIds.join(',')}`);
  }, [selectedRowKeys, keywords, navigate]);

  // ── History import modal ──────────────────────────────────────────────
  const loadHistoryKeywords = useCallback(async (page: number, search: string) => {
    setImportLoading(true);
    try {
      // Pass no brand to get all brands' keywords
      const data = await keywordsApi.list({
        page,
        page_size: historyPageSize,
        search: search || undefined,
      });
      setHistoryKeywords(data.items);
      setHistoryTotal(data.total);
    } catch (err) {
      console.error('[KeywordsPage] loadHistoryKeywords failed:', err);
      message.error('加载历史关键词失败');
    } finally {
      setImportLoading(false);
    }
  }, [historyPageSize]);

  const openImportModal = useCallback(() => {
    setImportModalVisible(true);
    setHistoryPage(1);
    setHistorySearch('');
    setHistorySearchVal('');
    setHistorySelectedKeys([]);
    loadHistoryKeywords(1, '');
  }, [loadHistoryKeywords]);

  useEffect(() => {
    if (importModalVisible) {
      loadHistoryKeywords(historyPage, historySearch);
    }
  }, [historyPage, importModalVisible, loadHistoryKeywords, historySearch]);

  // Debounced history search
  useEffect(() => {
    if (!importModalVisible) return;
    if (historySearchTimer.current) clearTimeout(historySearchTimer.current);
    historySearchTimer.current = setTimeout(() => {
      setHistorySearch(historySearchVal);
      setHistoryPage(1);
    }, 400);
    return () => { if (historySearchTimer.current) clearTimeout(historySearchTimer.current); };
  }, [historySearchVal, importModalVisible]);

  const handleImportConfirm = useCallback(async () => {
    if (!historySelectedKeys.length) { message.warning('请先选择要导入的关键词'); return; }
    try {
      const ids = historySelectedKeys
        .map(k => Number(k))
        .filter(n => !isNaN(n) && n > 0);
      if (!ids.length) { message.warning('请先选择要导入的关键词'); return; }
      const res = await keywordsApi.importKeywords(ids, config?.brand || '');
      message.success(`成功导入 ${res.imported} 个关键词${res.skipped > 0 ? `（跳过 ${res.skipped} 个重复）` : ''}`);
      setImportModalVisible(false);
      setHistorySelectedKeys([]);
      loadKeywords(currentPage, pageSize);
    } catch (err) {
      console.error('[KeywordsPage] handleImportKeywords failed:', err);
      message.error('导入失败');
    }
  }, [historySelectedKeys, config?.brand, loadKeywords, currentPage, pageSize]);

  // ── Empty state: go to generate ───────────────────────────────────────
  const goToGenerate = useCallback(() => {
    setActiveTab('combo');
    const el = document.querySelector('.ant-tabs-tab-btn') as HTMLElement | null;
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, []);

  // ── Wrap SSE handlers to capture warnings/errors/progress ─────────────
  const wrapStreamHandlers = useCallback((handlers: Record<string, unknown>) => ({
    ...handlers,
    onStart: (data: Record<string, unknown> & { warnings?: InjectionWarning[] }) => {
      if (data.warnings && data.warnings.length > 0) {
        setInjectionWarnings(data.warnings);
      }
      (handlers as Record<string, (d: unknown) => void>).onStart?.(data);
    },
    onProgress: (data: Record<string, unknown> & { current?: number; total?: number; step?: number; message?: string }) => {
      setStreamProgress({
        current: data.current ?? data.step,
        total: data.total,
        message: data.message ? String(data.message) : undefined,
      });
      (handlers as Record<string, (d: unknown) => void>).onProgress?.(data);
    },
    onError: (data: Record<string, unknown> & { error_type?: string; message?: string; error?: string }) => {
      setStreaming(false);
      setStreamError({
        error_type: data.error_type ? String(data.error_type) : undefined,
        message: String(data.message || data.error || '生成失败'),
      });
      (handlers as Record<string, (d: unknown) => void>).onError?.(data);
    },
  }), []);

  // ── Reset stream feedback when starting a new stream ──────────────────
  const resetStreamFeedback = useCallback(() => {
    setInjectionWarnings([]);
    setStreamError(null);
    setStreamProgress({});
  }, []);

  // ── ECharts pie data ──────────────────────────────────────────────────
  const pieData = useMemo(() => {
    if (!quality?.intent_distribution) return [];
    return Object.entries(quality.intent_distribution).map(([name, value]) => ({ name, value }));
  }, [quality]);

  // ── ECharts pie option (theme-aware) ──────────────────────────────────
  const pieChartOption = useMemo(() => {
    const legendBase = getLegendBase(darkMode);
    const themeColors = getEChartsThemeColors(darkMode);
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, left: 'center', textStyle: { fontSize: 11, color: legendBase.textStyle.color } },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: pieData,
        label: { fontSize: 11, color: themeColors.textColor },
      }],
    };
  }, [pieData, darkMode]);

  // ── Table columns ─────────────────────────────────────────────────────
  const columns: ColumnsType<Keyword> = [
    {
      title: '',
      width: 40,
      render: (_, r) => (
        <Tooltip title={r.is_favorite ? '取消收藏' : '收藏'}>
          <Button
            type="text"
            size="small"
            icon={r.is_favorite
              ? <StarFilled className="text-warning" />
              : <StarOutlined />}
            onClick={() => handleToggleFavorite(r.id)}
          />
        </Tooltip>
      ),
    },
    { title: 'ID', dataIndex: 'id', width: 55 },
    {
      title: '关键词',
      dataIndex: 'keyword',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text} placement="topLeft">
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 240,
      render: (_: unknown, r) => {
        const tags = parseTags(r.tags);
        return (
          <Space size={[4, 4]} wrap className="max-w-[240px]">
            {tags.map(t => (
              <Tag
                key={t}
                closable
                onClose={(e) => { e.preventDefault(); handleRemoveTag(r.id, t); }}
                className="!m-0"
              >
                {t}
              </Tag>
            ))}
            <Popover
              trigger="click"
              open={tagEditId === r.id}
              onOpenChange={(visible) => {
                if (!visible) { setTagEditId(null); setTagInputValue(''); }
                else { setTagEditId(r.id); setTagInputValue(''); }
              }}
              content={(
                <div className="w-[220px]">
                  <Input
                    placeholder="输入标签，逗号分隔多个"
                    value={tagInputValue}
                    onChange={e => setTagInputValue(e.target.value)}
                    onPressEnter={handleAddTagsSubmit}
                    autoFocus
                    className="mb-2"
                  />
                  <Space>
                    <Button type="primary" size="small" onClick={handleAddTagsSubmit}>添加</Button>
                    <Button size="small" onClick={() => { setTagEditId(null); setTagInputValue(''); }}>取消</Button>
                  </Space>
                </div>
              )}
            >
              <Tag
                className="cursor-pointer border-dashed bg-[#fafafa] !m-0"
                onClick={() => { setTagEditId(r.id); setTagInputValue(''); }}
              >
                <PlusOutlined /> 添加标签
              </Tag>
            </Popover>
          </Space>
        );
      },
    },
    { title: '品牌', dataIndex: 'brand', width: 90, render: (b: string) => b ? <Tag>{b}</Tag> : '-' },
    { title: '创建时间', dataIndex: 'created_at', width: 155, render: (t: string) => t ? formatDateTime(t) : '-' },
    {
      title: '操作', width: 70,
      render: (_, r) => (
        <Popconfirm
          title={`确定删除关键词「${r.keyword}」？此操作不可恢复`}
          onConfirm={() => handleDelete(r.id)}
          okText="删除"
          okButtonProps={{ danger: true }}
          cancelText="取消"
        >
          <Button type="link" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ];

  const selectedCount = selectedRowKeys.length;

  // ── Determine table empty state ───────────────────────────────────────
  const isInitialLoad = loading && keywords.length === 0 && !searchText && !filterTag && !filterFavorite;
  const hasFilters = !!searchText || !!filterTag || filterFavorite;
  const isEmpty = !loading && totalKeywords === 0 && !hasFilters;
  const noSearchResults = !loading && keywords.length === 0 && totalKeywords === 0 && hasFilters;

  const tableLocale = isEmpty
    ? {
        emptyText: (
          <Empty
            description="还没有保存任何关键词，先生成一批吧"
            className="py-6"
          >
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={goToGenerate}>
              生成关键词
            </Button>
          </Empty>
        ),
      }
    : noSearchResults
    ? { emptyText: <Empty description="没有找到匹配的关键词" className="py-6" /> }
    : undefined;

  // ── History import table columns ──────────────────────────────────────
  const historyColumns: ColumnsType<Keyword> = [
    { title: '关键词', dataIndex: 'keyword', ellipsis: true },
    { title: '品牌', dataIndex: 'brand', width: 100, render: (b: string) => b ? <Tag>{b}</Tag> : '-' },
    { title: '收藏', dataIndex: 'is_favorite', width: 60, render: (f: boolean) => f ? <StarFilled className="text-warning" /> : '' },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 150,
      render: (tagsStr: string) => {
        const tags = parseTags(tagsStr);
        return tags.length > 0
          ? <Space size={2} wrap>{tags.slice(0, 3).map(t => <Tag key={t} className="!m-0">{t}</Tag>)}{tags.length > 3 && <Text type="secondary">+{tags.length - 3}</Text>}</Space>
          : '-';
      },
    },
    { title: '创建时间', dataIndex: 'created_at', width: 150, render: (t: string) => t ? formatDate(t) : '-' },
  ];

  // ── Build SSE fetch wrappers with feedback capture ────────────────────
  const makeLLMStreamFetcher = useCallback(() => {
    return (handlers: Parameters<typeof keywordsApi.generateStream>[1]) => {
      const values = llmForm.getFieldsValue();
      resetStreamFeedback();
      keywordsApi.generateStream({
        core_keyword: values.core_keyword,
        brand: config?.brand,
        advantages: config?.advantages,
        max_results: values.max_results,
        polish: values.polish,
        temperature: values.temperature,
      }, wrapStreamHandlers(handlers as unknown as Record<string, unknown>));
    };
  }, [llmForm, config?.brand, config?.advantages, wrapStreamHandlers, resetStreamFeedback]);

  const makeMineStreamFetcher = useCallback(() => {
    return (handlers: Parameters<typeof keywordsApi.mineStream>[1]) => {
      const values = mineForm.getFieldsValue();
      resetStreamFeedback();
      keywordsApi.mineStream({
        keyword: values.keyword,
        brand: config?.brand,
        temperature: values.temperature,
      }, wrapStreamHandlers(handlers as unknown as Record<string, unknown>));
    };
  }, [mineForm, config?.brand, wrapStreamHandlers, resetStreamFeedback]);

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">关键词蒸馏</h2>
        <p className="page-desc">生成针对 AI 搜索优化的口语化、长尾关键词</p>
      </div>

      {!hasConfig && (
        <Alert type="warning" showIcon message="请先在系统设置中配置 LLM API Key" className="mb-4" />
      )}

      <Row gutter={16}>
        {/* ── Left column: generation panel ─────────────────────────── */}
        <Col xs={24} lg={10}>
          <Card>
            {/* Industry preset dropdown */}
            <Form.Item label="行业预设词库" className="mb-3">
              <Select
                placeholder="选择行业以快速填充种子词"
                allowClear
                loading={presetsLoading}
                value={selectedIndustry}
                onChange={handleIndustryChange}
                options={industryPresets.map(p => ({ label: p.name, value: p.key }))}
              />
            </Form.Item>

            {/* Seed keyword tags */}
            {seedTagKeywords.length > 0 && (
              <div className="mb-3">
                <Text type="secondary" className="text-xs block mb-1">
                  种子关键词（点击使用）：
                </Text>
                <Space wrap>
                  {seedTagKeywords.map((kw, i) => (
                    <Tag
                      key={i}
                      color="blue"
                      className="cursor-pointer"
                      onClick={() => handleSeedTagClick(kw)}
                    >
                      {kw}
                    </Tag>
                  ))}
                </Space>
                {selectedIndustry && (() => {
                  const preset = industryPresets.find(p => p.key === selectedIndustry);
                  return preset?.description ? (
                    <Paragraph type="secondary" className="text-xs mt-[6px] mb-0">
                      {preset.description}
                    </Paragraph>
                  ) : null;
                })()}
              </div>
            )}

            <Divider className="my-3" />

            <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
              // ── 词库组合 ────────────────────────────────────────
              {
                key: 'combo',
                label: <span><BranchesOutlined />词库组合</span>,
                children: (
                  <Form form={comboForm} layout="vertical" onFinish={handleCombo} initialValues={{ max_results: 50 }}>
                    <Form.Item label="核心行业词" name="core_keyword" rules={[{ required: true, message: '请输入核心行业词' }]}>
                      <Input placeholder="例如：项目管理软件" />
                    </Form.Item>
                    <Form.Item label="最大生成数量" name="max_results">
                      <InputNumber min={10} max={500} className="w-full" />
                    </Form.Item>
                    <Button type="primary" htmlType="submit" icon={<ThunderboltOutlined />} block>
                      生成组合关键词
                    </Button>
                  </Form>
                ),
              },
              // ── AI蒸馏 ──────────────────────────────────────────
              {
                key: 'llm',
                label: <span><SearchOutlined />AI蒸馏</span>,
                children: (
                  <Form form={llmForm} layout="vertical" initialValues={{ max_results: 30, polish: true, temperature: 0.7 }}>
                    <Form.Item label="核心关键词" name="core_keyword" rules={[{ required: true, message: '请输入核心关键词' }]}>
                      <Input placeholder="输入目标关键词" />
                    </Form.Item>
                    <Form.Item label="生成数量" name="max_results">
                      <InputNumber min={5} max={100} className="w-full" />
                    </Form.Item>
                    <Form.Item label="使用LLM润色" name="polish" valuePropName="checked">
                      <Switch />
                    </Form.Item>
                    <Form.Item label="温度" name="temperature">
                      <InputNumber min={0} max={1} step={0.05} className="w-full" />
                    </Form.Item>
                    <Button
                      type="primary"
                      onClick={startLLMGenerate}
                      icon={<ThunderboltOutlined />}
                      block
                      disabled={!hasConfig}
                      loading={streaming && activeTab === 'llm'}
                    >
                      {streaming && activeTab === 'llm' ? '生成中...' : 'AI生成关键词'}
                    </Button>
                  </Form>
                ),
              },
              // ── 竞品挖掘 ────────────────────────────────────────
              {
                key: 'mine',
                label: <span><ClusterOutlined />竞品挖掘</span>,
                children: (
                  <Form form={mineForm} layout="vertical" initialValues={{ temperature: 0.7 }}>
                    <Form.Item label="目标关键词" name="keyword" rules={[{ required: true, message: '请输入要分析的关键词' }]}>
                      <Input placeholder="输入要分析的关键词" />
                    </Form.Item>
                    <Button
                      type="primary"
                      onClick={startMine}
                      block
                      disabled={!hasConfig}
                      loading={streaming && activeTab === 'mine'}
                      icon={<ClusterOutlined />}
                    >
                      {streaming && activeTab === 'mine' ? '挖掘中...' : '挖掘竞品关键词'}
                    </Button>
                  </Form>
                ),
              },
              // ── 语义扩展 ────────────────────────────────────────
              {
                key: 'expand',
                label: <span><BranchesOutlined />语义扩展</span>,
                children: (
                  <Form form={expandForm} layout="vertical" initialValues={{ temperature: 0.7 }}>
                    <Form.Item label="种子关键词（每行一个）" name="keywords">
                      <TextArea rows={3} placeholder="输入要扩展的关键词，每行一个，或从已有列表继续扩展" />
                    </Form.Item>
                    <Form.Item label="温度" name="temperature">
                      <InputNumber min={0} max={1} step={0.05} className="w-full" />
                    </Form.Item>
                    <Space.Compact block className="mb-2">
                      <Button
                        type="primary"
                        onClick={startExpand}
                        icon={<ThunderboltOutlined />}
                        disabled={!hasConfig}
                        loading={expandStreaming}
                        className="flex-1"
                      >
                        {expandStreaming ? '扩展中...' : '语义扩展'}
                      </Button>
                      <Button
                        onClick={addInputToExpandList}
                        disabled={expandStreaming}
                      >
                        添加到列表
                      </Button>
                      <Button
                        onClick={handleUndo}
                        icon={<UndoOutlined />}
                        disabled={undoStack.length === 0 || expandStreaming}
                      >
                        撤销 {undoStack.length > 0 && `(${undoStack.length})`}
                      </Button>
                    </Space.Compact>
                    <Button
                      block
                      danger
                      size="small"
                      onClick={clearExpandKeywords}
                      disabled={!expandKeywords.length || expandStreaming}
                      className="mb-2"
                    >
                      清空列表
                    </Button>

                    {/* Expand keyword tags */}
                    {expandKeywords.length > 0 && (
                      <Card size="small" title={`扩展关键词 (${expandKeywords.length}个)`} extra={
                        <Button size="small" type="primary" onClick={saveExpandKeywords}>保存</Button>
                      }>
                        <div className="max-h-[200px] overflow-auto">
                          <Space wrap>
                            {expandKeywords.map((kw, i) => (
                              <Tag
                                key={i}
                                color="geekblue"
                                closable
                                onClose={(e) => {
                                  e.preventDefault();
                                  setUndoStack(prev => {
                                    const next = [...prev, [...expandKeywords]];
                                    return next.length > MAX_UNDO ? next.slice(-MAX_UNDO) : next;
                                  });
                                  const next = expandKeywords.filter((_, idx) => idx !== i);
                                  setExpandKeywords(next);
                                  if (next.length) runQualityAnalysis(next);
                                  else setQuality(null);
                                }}
                              >
                                {kw}
                              </Tag>
                            ))}
                          </Space>
                        </div>
                      </Card>
                    )}

                    {/* Expand streaming result raw text */}
                    {expandStreaming || expandStreamResult ? (
                      <div className="mt-3">
                        {streamError && activeTab === 'expand' && (
                          <Alert
                            type="error"
                            message={streamError.error_type ? `[${streamError.error_type}]` : '生成错误'}
                            description={streamError.message}
                            showIcon
                            className="mb-2"
                            closable
                            onClose={() => setStreamError(null)}
                          />
                        )}
                        <StreamingText
                          key={`expand-${expandStreamKey}`}
                          autoStart={expandStreaming}
                          fetchStream={(handlers) => {
                            const values = expandForm.getFieldsValue();
                            const base = expandKeywords.length
                              ? expandKeywords
                              : parseKeywordsFromText(values.keywords || '');
                            setStreamError(null);
                            keywordsApi.expandStream({
                              keywords: base,
                              brand: config?.brand,
                              temperature: values.temperature,
                            }, wrapStreamHandlers(handlers as unknown as Record<string, unknown>));
                          }}
                          onComplete={onExpandComplete}
                          height={200}
                          placeholder="点击「语义扩展」开始"
                        />
                      </div>
                    ) : null}
                  </Form>
                ),
              },
            ]} />

            {/* Combo results */}
            {comboKeywords.length > 0 && activeTab === 'combo' && (
              <div className="mt-4">
                <Card size="small" title={`组合结果 (${comboKeywords.length}个)`} extra={
                  <Space>
                    <Button size="small" onClick={() => { setComboKeywords([]); setQuality(null); }}>清空</Button>
                    <Button size="small" type="primary" onClick={saveComboKeywords}>保存</Button>
                  </Space>
                }>
                  <div className="max-h-[200px] overflow-auto">
                    <Space wrap>
                      {comboKeywords.map((kw, i) => (
                        <Tag key={i} color="blue">{kw}</Tag>
                      ))}
                    </Space>
                  </div>
                </Card>
              </div>
            )}
          </Card>

          {/* ── AI streaming result card (llm/mine) ───────────────── */}
          {(streaming || streamResult || streamError) && (activeTab === 'llm' || activeTab === 'mine') && (
            <Card title="AI 生成结果" extra={
              <Space>
                {streamResult && !streaming && (
                  <Button size="small" type="primary" onClick={saveStreamKeywords}>
                    保存关键词
                  </Button>
                )}
                <Button size="small" icon={<ReloadOutlined />} onClick={() => {
                  setStreamResult('');
                  setQuality(null);
                  setStreamError(null);
                  setInjectionWarnings([]);
                  setStreamProgress({});
                  setStreamKey(k => k + 1);
                }}>
                  重新生成
                </Button>
              </Space>
            } style={{ marginTop: 16 }}>
              {/* Injection warnings */}
              {injectionWarnings.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  icon={<WarningOutlined />}
                  message="输入内容提示"
                  description={
                    <ul className="m-0 pl-5">
                      {injectionWarnings.map((w, i) => (
                        <li key={i}><strong>{w.field}</strong>：{w.warning}</li>
                      ))}
                    </ul>
                  }
                  className="mb-3"
                  closable
                  onClose={() => setInjectionWarnings([])}
                />
              )}

              {/* Error display */}
              {streamError && (
                <Alert
                  type="error"
                  showIcon
                  message={streamError.error_type ? `错误类型：${streamError.error_type}` : '生成失败'}
                  description={streamError.message}
                  className="mb-3"
                  action={
                    <Button size="small" type="primary" onClick={() => {
                      setStreamError(null);
                      setStreamKey(k => k + 1);
                      setStreaming(true);
                    }}>
                      重试
                    </Button>
                  }
                />
              )}

              {/* Progress indicator (current step / total) */}
              {streaming && streamProgress.current !== undefined && streamProgress.total !== undefined && (
                <div className="mb-2">
                  <Text type="secondary" className="text-xs">
                    进度：{streamProgress.current} / {streamProgress.total}
                    {streamProgress.message && ` - ${streamProgress.message}`}
                  </Text>
                </div>
              )}

              {!streamError && activeTab === 'llm' && (
                <StreamingText
                  key={`llm-${streamKey}`}
                  autoStart={streaming}
                  fetchStream={makeLLMStreamFetcher()}
                  onComplete={onLLMComplete}
                  height={400}
                  placeholder="点击「AI生成关键词」开始"
                />
              )}
              {!streamError && activeTab === 'mine' && (
                <StreamingText
                  key={`mine-${streamKey}`}
                  autoStart={streaming}
                  fetchStream={makeMineStreamFetcher()}
                  onComplete={onMineComplete}
                  height={400}
                  placeholder="点击「挖掘竞品关键词」开始"
                />
              )}
            </Card>
          )}
        </Col>

        {/* ── Right column: results & quality ──────────────────────── */}
        <Col xs={24} lg={14}>
          {/* Quality overview panel */}
          {qualityLoading && (
            <Card style={{ marginBottom: 16 }}>
              <div className="text-center p-6">
                <Spin tip="正在分析质量..." />
              </div>
            </Card>
          )}

          {quality && quality.total > 0 && !qualityLoading && (
            <Card title="质量概览" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={10}>
                  <ReactECharts
                    option={pieChartOption}
                    className="h-[220px]"
                    opts={{ renderer: 'svg' }}
                  />
                </Col>
                <Col xs={24} md={14}>
                  <Row gutter={12}>
                    <Col span={12}>
                      <Statistic title="品牌词占比" value={quality.brand_keyword_ratio} suffix="%" precision={1} valueStyle={{ fontSize: 20 }} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="疑问词占比" value={quality.question_ratio} suffix="%" precision={1} valueStyle={{ fontSize: 20 }} />
                    </Col>
                    <Col span={12} className="mt-3">
                      <Statistic title="长尾词占比" value={quality.long_tail_ratio} suffix="%" precision={1} valueStyle={{ fontSize: 20 }} />
                    </Col>
                    <Col span={12} className="mt-3">
                      <Statistic title="平均词长" value={quality.avg_length} precision={1} suffix="字" valueStyle={{ fontSize: 20 }} />
                    </Col>
                    <Col span={24} className="mt-3">
                      <Text type="secondary" className="text-xs">共 {quality.total} 个关键词</Text>
                    </Col>
                  </Row>
                </Col>
              </Row>

              {quality.suggestions && quality.suggestions.length > 0 && (
                <>
                  <Divider className="my-3" />
                  <div>
                    <Text strong className="text-sm block mb-2">优化建议</Text>
                    <Space direction="vertical" className="w-full">
                      {quality.suggestions.map((s, i) => (
                        <Alert key={i} message={s} type="info" showIcon className="text-xs" />
                      ))}
                    </Space>
                  </div>
                </>
              )}
            </Card>
          )}

          {/* Saved keywords table */}
          <Card
            title={`已保存关键词 (${totalKeywords})`}
            extra={
              <Space>
                {/* 主操作：选词生成内容 */}
                <Button
                  type="primary"
                  icon={<FileTextOutlined />}
                  onClick={handleGenerateContent}
                  disabled={selectedCount === 0}
                >
                  {selectedCount > 0 ? `用${selectedCount}个词生成内容` : '选词生成内容'}
                </Button>

                {/* 次操作：收纳到 Dropdown */}
                <Dropdown menu={{
                  items: [
                    { key: 'import', label: '从历史导入', icon: <ImportOutlined /> },
                    { key: 'analyze', label: '分析质量', icon: <BarChartOutlined /> },
                  ],
                  onClick: ({ key }) => {
                    if (key === 'import') openImportModal();
                    else if (key === 'analyze') analyzeSavedQuality();
                  },
                }}>
                  <Button icon={<DownOutlined />}>更多</Button>
                </Dropdown>

                {/* 工具操作 */}
                <Tooltip title="刷新">
                  <Button icon={<ReloadOutlined />} onClick={() => loadKeywords(currentPage, pageSize)} />
                </Tooltip>

                {/* 危险操作：隔离 + Popconfirm */}
                <Divider type="vertical" style={{ margin: '0 4px' }} />
                <Popconfirm title="确认清空所有关键词？此操作不可恢复" onConfirm={handleDeleteAll}>
                  <Button danger ghost icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            }
          >
            {/* Search and filter bar */}
            <div className="mb-3 flex gap-2 flex-wrap items-center">
              <Input.Search
                placeholder="搜索关键词"
                allowClear
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                className="w-[220px]"
                onSearch={v => { setSearchText(v); setCurrentPage(1); }}
              />
              <Select
                placeholder="按标签筛选"
                allowClear
                value={filterTag}
                onChange={v => { setFilterTag(v); setCurrentPage(1); }}
                className="w-[160px]"
                options={allKnownTags.map(t => ({ label: t, value: t }))}
              />
              <Space size={4}>
                <Text type="secondary" className="text-xs">仅看收藏</Text>
                <Switch
                  size="small"
                  checked={filterFavorite}
                  onChange={v => { setFilterFavorite(v); setCurrentPage(1); }}
                />
              </Space>
            </div>

            <Spin spinning={isInitialLoad} tip="加载中...">
              <Table
                rowSelection={{
                  selectedRowKeys,
                  onChange: setSelectedRowKeys,
                  preserveSelectedRowKeys: false,
                }}
                columns={columns}
                dataSource={keywords}
                rowKey="id"
                loading={!isInitialLoad && loading}
                size="small"
                pagination={false}
                locale={tableLocale}
                scroll={{ y: 400 }}
              />
            </Spin>

            {/* Pagination */}
            {totalKeywords > 0 && (
              <div className="mt-3 flex justify-end">
                <Pagination
                  current={currentPage}
                  pageSize={pageSize}
                  total={totalKeywords}
                  showSizeChanger
                  showQuickJumper
                  pageSizeOptions={['10', '20', '50', '100']}
                  showTotal={(t, range) => `第 ${range[0]}-${range[1]} 条，共 ${t} 条`}
                  onChange={(page, ps) => {
                    setCurrentPage(page);
                    setPageSize(ps);
                    setSelectedRowKeys([]);
                  }}
                />
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* ── History import modal ─────────────────────────────────────────── */}
      <Modal
        title="从历史导入关键词"
        open={importModalVisible}
        width={800}
        onCancel={() => setImportModalVisible(false)}
        onOk={handleImportConfirm}
        okText={`导入已选 (${historySelectedKeys.length})`}
        okButtonProps={{ disabled: historySelectedKeys.length === 0 }}
        destroyOnClose
      >
        <div className="mb-3">
          <Input.Search
            placeholder="搜索历史关键词"
            allowClear
            value={historySearchVal}
            onChange={e => setHistorySearchVal(e.target.value)}
            className="w-[300px]"
          />
          <Text type="secondary" className="ml-3 text-xs">
            共 {historyTotal} 个关键词，已选 {historySelectedKeys.length} 个
          </Text>
        </div>
        <Table
          rowSelection={{
            selectedRowKeys: historySelectedKeys,
            onChange: setHistorySelectedKeys,
            preserveSelectedRowKeys: true,
          }}
          columns={historyColumns}
          dataSource={historyKeywords}
          rowKey="id"
          loading={importLoading}
          size="small"
          pagination={{
            current: historyPage,
            pageSize: historyPageSize,
            total: historyTotal,
            showSizeChanger: false,
            onChange: (page) => setHistoryPage(page),
            size: 'small',
          }}
          scroll={{ y: 360 }}
          locale={{ emptyText: <Empty description="暂无历史关键词" /> }}
        />
      </Modal>
    </div>
  );
};

export default KeywordsPage;
