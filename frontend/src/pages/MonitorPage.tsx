import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Switch, Tag, Space, message, Spin, Tabs, Slider, Progress, Alert, Popconfirm, Drawer, Typography, Badge, Empty } from 'antd';
import { PlusOutlined, PlayCircleOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, BellOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { monitorApi, MonitorTask, MonitorResult, AlertItem, TrendPoint } from '@/api/monitor';
import { sseClient } from '@/utils/request';
import { useAppStore } from '@/stores';
import { PLATFORM_COLORS, MONITOR_PLATFORMS, MONITOR_PLATFORM_LABELS } from '@/constants';
import { getEChartsThemeColors } from '@/utils/echartsTheme';
import { formatDateTime } from '@/utils/dateFormat';

const { Text } = Typography;
const { TextArea } = Input;

const SCHEDULE_LABELS: Record<string, string> = {
  manual: '手动',
  daily: '每天',
  weekly: '每周',
};

const SENTIMENT_MAP: Record<string, { color: string; label: string }> = {
  positive: { color: 'green', label: '正面' },
  negative: { color: 'red', label: '负面' },
  neutral: { color: 'default', label: '中性' },
};

const ALERT_LEVEL_MAP: Record<string, { color: string; label: string }> = {
  critical: { color: 'red', label: '严重' },
  warning: { color: 'orange', label: '警告' },
  info: { color: 'blue', label: '信息' },
};

const ALERT_TYPE_LABELS: Record<string, string> = {
  not_mentioned: '未提及告警',
  negative_sentiment: '负面情感',
  competitor_rank: '竞品领先',
  threshold_breach: '阈值突破',
};

interface RunProgress {
  task_name: string;
  platform: string;
  query: string;
  status: string;
  is_mentioned?: boolean;
  sentiment?: string;
  mention_count?: number;
  content_snippet?: string;
  error?: string;
}

const MonitorPage: React.FC = () => {
  const { config, darkMode } = useAppStore();
  const [activeTab, setActiveTab] = useState('tasks');

  // Tasks state
  const [tasks, setTasks] = useState<MonitorTask[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [taskTotal, setTaskTotal] = useState(0);
  const [taskPage, setTaskPage] = useState(1);

  // Create/Edit task modal
  const [taskModalVisible, setTaskModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<MonitorTask | null>(null);
  const [taskForm] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  // Run drawer (SSE streaming)
  const [runDrawerVisible, setRunDrawerVisible] = useState(false);
  const [running, setRunning] = useState(false);
  const [runProgress, setRunProgress] = useState<RunProgress[]>([]);
  const [runTaskName, setRunTaskName] = useState('');
  const [runCompleted, setRunCompleted] = useState(0);
  const [runTotal, setRunTotal] = useState(0);
  const runAbortRef = useRef<boolean>(false);

  // Results state
  const [results, setResults] = useState<MonitorResult[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultTotal, setResultTotal] = useState(0);
  const [resultPage, setResultPage] = useState(1);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);

  // Trends state
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [trendsLoading, setTrendsLoading] = useState(false);
  const [trendPlatform, setTrendPlatform] = useState<string | undefined>(undefined);

  // Alerts state
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertTotal, setAlertTotal] = useState(0);
  const [alertPage, setAlertPage] = useState(1);
  const [unreadCount, setUnreadCount] = useState(0);

  // KPI stats
  const [kpiStats, setKpiStats] = useState({ activeTasks: 0, totalAlerts: 0, avgMentionRate: 0, lastRunTime: '' });

  const loadTasks = useCallback(async () => {
    setTasksLoading(true);
    try {
      const data = await monitorApi.listTasks({ page: taskPage, page_size: 20 });
      setTasks(data.items);
      setTaskTotal(data.total);
      const activeCount = data.items.filter(t => t.is_active).length;
      const lastRun = data.items
        .filter(t => t.last_run_at)
        .sort((a, b) => new Date(b.last_run_at!).getTime() - new Date(a.last_run_at!).getTime())[0];
      setKpiStats(prev => ({
        ...prev,
        activeTasks: activeCount,
        lastRunTime: lastRun?.last_run_at || '',
      }));
    } catch (err) {
      console.error('[MonitorPage] loadTasks failed:', err);
      message.error('加载监测任务失败');
    } finally {
      setTasksLoading(false);
    }
  }, [taskPage]);

  const loadResults = useCallback(async () => {
    if (!selectedTaskId) return;
    setResultsLoading(true);
    try {
      const data = await monitorApi.getResults(selectedTaskId, { page: resultPage, page_size: 20 });
      setResults(data.items);
      setResultTotal(data.total);
    } catch (err) {
      console.error('[MonitorPage] loadResults failed:', err);
      message.error('加载监测结果失败');
    } finally {
      setResultsLoading(false);
    }
  }, [selectedTaskId, resultPage]);

  const loadTrends = useCallback(async () => {
    setTrendsLoading(true);
    try {
      const data = await monitorApi.getTrends({ platform: trendPlatform, days: 30 });
      setTrends(data);
      if (data.length > 0) {
        const mentioned = data.reduce((sum, p) => sum + p.mentioned_count, 0);
        const total = data.reduce((sum, p) => sum + p.total_checks, 0);
        setKpiStats(prev => ({ ...prev, avgMentionRate: total > 0 ? Math.round((mentioned / total) * 100) : 0 }));
      }
    } catch (err) {
      console.error('[MonitorPage] loadTrends failed:', err);
      message.error('加载趋势数据失败');
    } finally {
      setTrendsLoading(false);
    }
  }, [trendPlatform]);

  const loadAlerts = useCallback(async () => {
    setAlertsLoading(true);
    try {
      const data = await monitorApi.listAlerts({ page: alertPage, page_size: 20 });
      setAlerts(data.items);
      setAlertTotal(data.total);
      const unread = data.items.filter(a => !a.is_read).length;
      setUnreadCount(prev => (alertPage === 1 ? unread : prev));
      setKpiStats(prev => ({ ...prev, totalAlerts: data.total }));
    } catch (err) {
      console.error('[MonitorPage] loadAlerts failed:', err);
      message.error('加载告警失败');
    } finally {
      setAlertsLoading(false);
    }
  }, [alertPage]);

  const loadUnreadCount = useCallback(async () => {
    try {
      const data = await monitorApi.listAlerts({ unread_only: true, page: 1, page_size: 1 });
      setUnreadCount(data.total);
      setKpiStats(prev => ({ ...prev, totalAlerts: data.total }));
    } catch (err) {
      console.error('[MonitorPage] 加载未读告警数失败:', err);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    loadUnreadCount();
  }, [loadTasks, loadUnreadCount]);

  useEffect(() => {
    if (activeTab === 'results' && selectedTaskId) {
      loadResults();
    }
  }, [activeTab, loadResults, selectedTaskId]);

  useEffect(() => {
    if (activeTab === 'trends') {
      loadTrends();
    }
  }, [activeTab, loadTrends]);

  useEffect(() => {
    if (activeTab === 'alerts') {
      loadAlerts();
    }
  }, [activeTab, loadAlerts]);

  // When tasks load, auto-select first task for results tab
  useEffect(() => {
    if (tasks.length > 0 && !selectedTaskId) {
      setSelectedTaskId(tasks[0].id);
    }
  }, [tasks, selectedTaskId]);

  const openCreateModal = () => {
    setEditingTask(null);
    taskForm.resetFields();
    taskForm.setFieldsValue({
      schedule_type: 'manual',
      alert_threshold: 30,
      MONITOR_PLATFORMS: ['wenxin', 'doubao', 'deepseek', 'kimi', 'tongyi'],
    });
    setTaskModalVisible(true);
  };

  const openEditModal = (task: MonitorTask) => {
    setEditingTask(task);
    taskForm.setFieldsValue({
      name: task.name,
      queries: task.queries,
      MONITOR_PLATFORMS: task.platforms ? task.platforms.split(',').map(s => s.trim()) : [],
      schedule_type: task.schedule_type,
      alert_threshold: task.alert_threshold,
      competitors: task.competitors || '',
    });
    setTaskModalVisible(true);
  };

  const handleSubmitTask = async () => {
    try {
      const values = await taskForm.validateFields();
      setSubmitting(true);
      const payload = {
        name: values.name,
        queries: values.queries,
        platforms: (values.MONITOR_PLATFORMS || []).join(','),
        schedule_type: values.schedule_type,
        alert_threshold: values.alert_threshold,
        competitors: values.competitors || '',
        brand: config?.brand,
      };
      if (editingTask) {
        await monitorApi.updateTask(editingTask.id, payload);
        message.success('任务更新成功');
      } else {
        await monitorApi.createTask(payload);
        message.success('任务创建成功');
      }
      setTaskModalVisible(false);
      loadTasks();
    } catch (err: unknown) {
      if ((err as { errorFields?: unknown[] }).errorFields) {
        // form validation error
        return;
      }
      message.error(editingTask ? '更新任务失败' : '创建任务失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTask = async (id: number) => {
    try {
      await monitorApi.deleteTask(id);
      message.success('任务已删除');
      loadTasks();
    } catch (err) {
      console.error('[MonitorPage] handleDeleteTask failed:', err);
      message.error('删除任务失败');
    }
  };

  const handleToggleTask = async (id: number, checked: boolean) => {
    try {
      await monitorApi.toggleTask(id);
      setTasks(prev => prev.map(t => t.id === id ? { ...t, is_active: checked } : t));
      message.success(checked ? '任务已启用' : '任务已暂停');
    } catch (err) {
      console.error('[MonitorPage] handleToggleTask failed:', err);
      message.error('操作失败');
    }
  };

  const handleRunTask = (task: MonitorTask) => {
    setRunTaskName(task.name);
    setRunProgress([]);
    setRunCompleted(0);
    setRunTotal(0);
    setRunning(true);
    setRunDrawerVisible(true);

    const queries = task.queries.split('\n').filter(q => q.trim());
    const taskPlatforms = task.platforms ? task.platforms.split(',').map(p => p.trim()) : [];
    const totalSteps = queries.length * taskPlatforms.length;
    setRunTotal(totalSteps);

    runAbortRef.current = true;

    monitorApi.runTaskStream(task.id, {
      onStart: (data) => {
        if (!runAbortRef.current) return;
        setRunTaskName((data.task_name as string) || task.name);
      },
      onProgress: (data) => {
        if (!runAbortRef.current) return;
        const platform = (data.platform as string) || '';
        const query = (data.query as string) || '';
        const status = (data.status as string) || 'running';
        const isMentioned = data.is_mentioned as boolean | undefined;
        const sentiment = data.sentiment as string | undefined;
        const mentionCount = data.mention_count as number | undefined;
        const contentSnippet = data.content_snippet as string | undefined;
        const error = data.error as string | undefined;

        setRunProgress(prev => {
          const existing = prev.findIndex(p => p.platform === platform && p.query === query);
          const entry: RunProgress = {
            task_name: task.name,
            platform,
            query,
            status,
            is_mentioned: isMentioned,
            sentiment,
            mention_count: mentionCount,
            content_snippet: contentSnippet,
            error,
          };
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = entry;
            return updated;
          }
          return [...prev, entry];
        });

        if (status === 'done' || status === 'error') {
          setRunCompleted(c => c + 1);
        }
      },
      onComplete: () => {
        if (!runAbortRef.current) return;
        runAbortRef.current = false;
        setRunning(false);
        message.success('监测任务执行完成');
        loadTasks();
        loadUnreadCount();
      },
      onError: (data) => {
        runAbortRef.current = false;
        setRunning(false);
        const errMsg = (data.message as string) || '任务执行出错';
        if (errMsg !== 'The user aborted a request.' && !errMsg.includes('abort')) {
          message.error(errMsg);
        }
      },
    }).catch(() => {
      // Connection error handled by onError or abort
    });
  };

  const handleBackgroundRun = () => {
    // 后台运行：关闭抽屉但不断开 SSE 连接，任务继续在后台执行
    setRunDrawerVisible(false);
    message.info({ content: '任务已在后台继续运行，完成后将自动刷新数据', duration: 3 });
  };

  const closeRunDrawer = () => {
    if (running) {
      Modal.confirm({
        title: '确认关闭',
        content: '任务正在执行中，关闭后将终止任务，是否继续？',
        okText: '终止并关闭',
        cancelText: '取消',
        okButtonProps: { danger: true },
        onOk: () => {
          runAbortRef.current = false;
          sseClient.disconnect();
          setRunning(false);
          setRunDrawerVisible(false);
        },
      });
    } else {
      setRunDrawerVisible(false);
    }
  };

  const handleMarkAlertRead = async (id: number) => {
    try {
      await monitorApi.markAlertRead(id);
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, is_read: true } : a));
      setUnreadCount(c => Math.max(0, c - 1));
      message.success('已标记为已读');
    } catch (err) {
      console.error('[MonitorPage] handleMarkAlertRead failed:', err);
      message.error('操作失败');
    }
  };

  const handleMarkAllRead = async () => {
    const unreadAlerts = alerts.filter(a => !a.is_read);
    try {
      await Promise.all(unreadAlerts.map(a => monitorApi.markAlertRead(a.id)));
      setAlerts(prev => prev.map(a => ({ ...a, is_read: true })));
      setUnreadCount(0);
      message.success('已全部标记为已读');
    } catch (err) {
      console.error('[MonitorPage] handleMarkAllRead failed:', err);
      message.error('操作失败');
    }
  };

  // Build ECharts option for trends
  const getTrendChartOption = useCallback(() => {
    const tc = getEChartsThemeColors(darkMode);
    if (!trends.length) {
      return {
        title: { text: '暂无趋势数据', left: 'center', top: 'center', textStyle: { color: tc.axisLabelColor, fontSize: 14 } },
      };
    }

    const MONITOR_PLATFORMS = [...new Set(trends.map(t => t.platform))];
    const dates = [...new Set(trends.map(t => t.date))].sort();

    const series = MONITOR_PLATFORMS.map(platform => {
      const platformData = trends.filter(t => t.platform === platform);
      const dataMap = new Map(platformData.map(t => [t.date, t.mention_rate]));
      return {
        name: MONITOR_PLATFORM_LABELS[platform] || platform,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: dates.map(d => {
          const point = dataMap.get(d);
          return point !== undefined ? Number((point * 100).toFixed(1)) : null;
        }),
        itemStyle: { color: PLATFORM_COLORS[platform] || '#3b82f6' },
        lineStyle: { width: 2 },
      };
    });

    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: tc.tooltipBg,
        borderColor: tc.tooltipBorderColor,
        textStyle: { color: tc.tooltipTextColor },
        formatter: (params: Array<{ seriesName: string; value: number | null; name: string }>) => {
          let html = `<div style="margin-bottom:4px;font-weight:500">${params[0]?.name || ''}</div>`;
          params.forEach(p => {
            if (p.value !== null && p.value !== undefined) {
              html += `<div>${p.seriesName}: <strong>${p.value}%</strong></div>`;
            }
          });
          return html;
        },
      },
      legend: {
        data: MONITOR_PLATFORMS.map(p => MONITOR_PLATFORM_LABELS[p] || p),
        bottom: 0,
        textStyle: { color: tc.legendTextColor },
      },
      grid: {
        left: 50,
        right: 24,
        top: 24,
        bottom: 48,
      },
      xAxis: {
        type: 'category',
        data: dates.map(d => d.slice(5)),
        boundaryGap: false,
        axisLine: { lineStyle: { color: tc.axisLineColor } },
        axisLabel: { color: tc.axisLabelColor },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%', color: tc.axisLabelColor },
        splitLine: { lineStyle: { color: tc.splitLineColor, type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series,
    };
  }, [trends, darkMode]);

  // Task table columns
  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      width: 160,
      ellipsis: true,
    },
    {
      title: '关键词',
      dataIndex: 'queries',
      key: 'queries',
      width: 200,
      ellipsis: true,
      render: (v: string) => {
        const lines = v.split('\n').filter(Boolean);
        return (
          <Space size={[4, 4]} wrap>
            {lines.slice(0, 3).map((q, i) => (
              <Tag key={i} style={{ margin: 0 }}>{q}</Tag>
            ))}
            {lines.length > 3 && <Tag style={{ margin: 0 }}>+{lines.length - 3}</Tag>}
          </Space>
        );
      },
    },
    {
      title: '监测平台',
      dataIndex: 'platforms',
      key: 'platforms',
      width: 200,
      render: (v: string) => {
        if (!v) return '-';
        const plats = v.split(',').map(s => s.trim());
        return (
          <Space size={[4, 4]} wrap>
            {plats.map(p => (
              <Tag key={p} color="blue" style={{ margin: 0 }}>{MONITOR_PLATFORM_LABELS[p] || p}</Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '调度',
      dataIndex: 'schedule_type',
      key: 'schedule_type',
      width: 80,
      render: (v: string) => <Tag>{SCHEDULE_LABELS[v] || v}</Tag>,
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 70,
      render: (v: boolean, record: MonitorTask) => (
        <Switch
          checked={v}
          size="small"
          onChange={(checked) => handleToggleTask(record.id, checked)}
        />
      ),
    },
    {
      title: '上次运行',
      dataIndex: 'last_run_at',
      key: 'last_run_at',
      width: 150,
      render: (v: string) => v ? formatDateTime(v) : <Text type="secondary">从未运行</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: MonitorTask) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRunTask(record)}
            loading={running && runTaskName === record.name}
          >
            运行
          </Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Popconfirm
            title={`确定删除监控任务「${record.name}」？`}
            description="此操作不可恢复，任务及其历史结果将被删除。"
            onConfirm={() => handleDeleteTask(record.id)}
            okText="确定删除"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Result table columns
  const resultColumns = [
    {
      title: '查询词',
      dataIndex: 'query',
      key: 'query',
      width: 160,
      ellipsis: true,
    },
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      width: 100,
      render: (v: string) => <Tag color="blue">{MONITOR_PLATFORM_LABELS[v] || v}</Tag>,
    },
    {
      title: '是否提及',
      dataIndex: 'is_mentioned',
      key: 'is_mentioned',
      width: 90,
      render: (v: boolean) => v
        ? <Tag color="green">已提及</Tag>
        : <Tag color="red">未提及</Tag>,
    },
    {
      title: '情感倾向',
      dataIndex: 'sentiment',
      key: 'sentiment',
      width: 90,
      render: (v: string) => {
        const s = SENTIMENT_MAP[v] || { color: 'default', label: v || '-' };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '提及次数',
      dataIndex: 'mention_count',
      key: 'mention_count',
      width: 80,
      render: (v: number) => <Text strong>{v}</Text>,
    },
    {
      title: '内容摘要',
      dataIndex: 'content_snippet',
      key: 'content_snippet',
      ellipsis: true,
      render: (v: string) => v ? (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {v.length > 80 ? v.slice(0, 80) + '...' : v}
        </Text>
      ) : '-',
    },
    {
      title: '检测时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (v: string) => v ? formatDateTime(v) : '-',
    },
  ];

  // Alert table columns
  const alertColumns = [
    {
      title: '类型',
      dataIndex: 'alert_type',
      key: 'alert_type',
      width: 110,
      render: (v: string) => <Tag>{ALERT_TYPE_LABELS[v] || v}</Tag>,
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (v: string) => {
        const l = ALERT_LEVEL_MAP[v] || { color: 'default', label: v || '-' };
        return <Tag color={l.color}>{l.label}</Tag>;
      },
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      ellipsis: true,
      render: (v: string, record: AlertItem) => (
        <Text strong={!record.is_read}>{v}</Text>
      ),
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (v: string) => <Text type="secondary">{v || '-'}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'is_read',
      key: 'is_read',
      width: 70,
      render: (v: boolean) => v
        ? <Tag color="default">已读</Tag>
        : <Badge status="processing" text="未读" />,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (v: string) => v ? formatDateTime(v) : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: AlertItem) =>
        !record.is_read ? (
          <Button type="link" size="small" onClick={() => handleMarkAlertRead(record.id)}>
            标记已读
          </Button>
        ) : null,
    },
  ];

  const taskPagination = { current: taskPage, pageSize: 20, total: taskTotal, onChange: setTaskPage };
  const resultPagination = { current: resultPage, pageSize: 20, total: resultTotal, onChange: setResultPage };
  const alertPagination = { current: alertPage, pageSize: 20, total: alertTotal, onChange: setAlertPage };

  const tabItems = [
    {
      key: 'tasks',
      label: '监测任务',
      children: (
        <>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <Text type="secondary">共 {taskTotal} 个任务，{kpiStats.activeTasks} 个启用中</Text>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={loadTasks} loading={tasksLoading}>刷新</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>新建任务</Button>
              </Space>
            </div>
            <Table
              columns={taskColumns as any}
              dataSource={tasks}
              rowKey="id"
              loading={tasksLoading}
              pagination={taskPagination}
              size="middle"
              scroll={{ x: 1000 }}
              locale={{
                emptyText: (
                  <Empty description="还没有创建监控任务">
                    <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
                      新建任务
                    </Button>
                  </Empty>
                )
              }}
            />
          </Card>
        </>
      ),
    },
    {
      key: 'results',
      label: '监测结果',
      children: (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12 }}>
            <Space>
              <Text>选择任务：</Text>
              <Select
                style={{ width: 280 }}
                value={selectedTaskId}
                onChange={setSelectedTaskId}
                placeholder="请选择监测任务"
                options={tasks.map(t => ({ label: t.name, value: t.id }))}
              />
            </Space>
            <Button icon={<ReloadOutlined />} onClick={loadResults} loading={resultsLoading}>刷新</Button>
          </div>
          {selectedTaskId ? (
            <Table
              columns={resultColumns as any}
              dataSource={results}
              rowKey="id"
              loading={resultsLoading}
              pagination={resultPagination}
              size="middle"
              scroll={{ x: 1000 }}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-tertiary)' }}>请先选择一个监测任务</div>
          )}
        </Card>
      ),
    },
    {
      key: 'trends',
      label: '趋势图表',
      children: (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Space>
              <Text>平台筛选：</Text>
              <Select
                style={{ width: 180 }}
                value={trendPlatform}
                onChange={setTrendPlatform}
                allowClear
                placeholder="全部平台"
                options={[
                  { label: '全部平台', value: undefined },
                  ...MONITOR_PLATFORMS.map(p => ({ label: MONITOR_PLATFORM_LABELS[p], value: p })),
                ]}
              />
            </Space>
            <Button icon={<ReloadOutlined />} onClick={loadTrends} loading={trendsLoading}>刷新</Button>
          </div>
          <Spin spinning={trendsLoading}>
            <div style={{ height: 400 }}>
              <ReactECharts
                option={getTrendChartOption()}
                style={{ height: '100%', width: '100%' }}
                notMerge
                lazyUpdate
              />
            </div>
          </Spin>
        </Card>
      ),
    },
    {
      key: 'alerts',
      label: (
        <Badge count={unreadCount} size="small" offset={[6, -2]}>
          <BellOutlined /> 告警中心
        </Badge>
      ),
      children: (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Space>
              {unreadCount > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  message={`有 ${unreadCount} 条未读告警`}
                  style={{ marginBottom: 0 }}
                />
              )}
            </Space>
            <Space>
              {unreadCount > 0 && (
                <Button onClick={handleMarkAllRead}>全部标记已读</Button>
              )}
              <Button icon={<ReloadOutlined />} onClick={loadAlerts} loading={alertsLoading}>刷新</Button>
            </Space>
          </div>
          <Table
            columns={alertColumns as any}
            dataSource={alerts}
            rowKey="id"
            loading={alertsLoading}
            pagination={alertPagination}
            size="middle"
            scroll={{ x: 900 }}
          />
        </Card>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">持续监测</h2>
        <p className="page-desc">自动巡检品牌在各大AI平台的提及情况，及时发现风险</p>
      </div>

      {/* KPI Stats Row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        <div className="kpi-stat" style={{ flex: '1 1 180px', minWidth: 150 }}>
          <div className="kpi-stat-label">活跃任务</div>
          <div className="kpi-stat-value">{kpiStats.activeTasks}</div>
        </div>
        <div className="kpi-stat" style={{ flex: '1 1 180px', minWidth: 150 }}>
          <div className="kpi-stat-label">平均提及率</div>
          <div className="kpi-stat-value">{kpiStats.avgMentionRate}%</div>
        </div>
        <div className="kpi-stat" style={{ flex: '1 1 180px', minWidth: 150 }}>
          <div className="kpi-stat-label">未读告警</div>
          <div className="kpi-stat-value">
            <Badge count={unreadCount} showZero style={{ backgroundColor: unreadCount > 0 ? 'var(--error)' : 'var(--border-strong)' }} />
          </div>
        </div>
        <div className="kpi-stat" style={{ flex: '1 1 180px', minWidth: 150 }}>
          <div className="kpi-stat-label">最近运行</div>
          <div className="kpi-stat-value" style={{ fontSize: 14 }}>
            {kpiStats.lastRunTime ? formatDateTime(kpiStats.lastRunTime) : '-'}
          </div>
        </div>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />

      {/* Create/Edit Task Modal */}
      <Modal
        title={editingTask ? '编辑监测任务' : '新建监测任务'}
        open={taskModalVisible}
        onOk={handleSubmitTask}
        onCancel={() => setTaskModalVisible(false)}
        okText={editingTask ? '保存' : '创建'}
        cancelText="取消"
        confirmLoading={submitting}
        width={600}
        destroyOnClose
      >
        <Form
          form={taskForm}
          layout="vertical"
          initialValues={{ schedule_type: 'manual', alert_threshold: 30, MONITOR_PLATFORMS: [] }}
        >
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：品牌关键词日常监测" maxLength={100} />
          </Form.Item>
          <Form.Item
            label="监测关键词（每行一个）"
            name="queries"
            rules={[{ required: true, message: '请输入至少一个关键词' }]}
          >
            <TextArea rows={4} placeholder="产品名称怎么样？&#10;XX软件好用吗&#10;XX品牌评价" />
          </Form.Item>
          <Form.Item
            label="监测平台"
            name="MONITOR_PLATFORMS"
            rules={[{ required: true, message: '请选择至少一个平台' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择要监测的AI平台"
              options={MONITOR_PLATFORMS.map(p => ({ label: MONITOR_PLATFORM_LABELS[p], value: p }))}
            />
          </Form.Item>
          <Form.Item label="调度方式" name="schedule_type">
            <Select
              options={[
                { label: '手动执行', value: 'manual' },
                { label: '每天执行', value: 'daily' },
                { label: '每周执行', value: 'weekly' },
              ]}
            />
          </Form.Item>
          <Form.Item label="告警阈值（提及率低于此值时告警）" name="alert_threshold">
            <Slider
              min={0}
              max={100}
              marks={{ 0: '0%', 30: '30%', 50: '50%', 70: '70%', 100: '100%' }}
              tooltip={{ formatter: (v?: number) => `${v}%` }}
            />
          </Form.Item>
          <Form.Item label="竞品关键词（每行一个，选填）" name="competitors">
            <TextArea rows={3} placeholder="竞品A&#10;竞品B" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Run Task Drawer (SSE streaming progress) */}
      <Drawer
        title={
          <Space>
            <PlayCircleOutlined spin={running} />
            <span>运行监测任务：{runTaskName}</span>
          </Space>
        }
        placement="right"
        width={520}
        open={runDrawerVisible}
        onClose={closeRunDrawer}
        extra={
          <Space>
            {running && (
              <Button onClick={handleBackgroundRun} type="default">
                后台运行
              </Button>
            )}
            <Button onClick={closeRunDrawer} danger={running}>
              {running ? '终止任务' : '关闭'}
            </Button>
          </Space>
        }
      >
        {runTotal > 0 && (
          <div style={{ marginBottom: 20 }}>
            <Progress
              percent={runTotal > 0 ? Math.round((runCompleted / runTotal) * 100) : 0}
              status={running ? 'active' : 'success'}
              format={() => `${runCompleted}/${runTotal}`}
            />
          </div>
        )}

        {runProgress.length === 0 && running && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: 'var(--text-tertiary)' }}>正在初始化监测任务...</div>
          </div>
        )}

        <Space direction="vertical" style={{ width: '100%' }} size={8}>
          {runProgress.map((item, idx) => (
            <div
              key={idx}
              style={{
                padding: '10px 12px',
                border: '1px solid var(--border-light)',
                borderRadius: 6,
                background: item.status === 'error'
                  ? 'var(--bg-error)'
                  : item.status === 'done'
                    ? (item.is_mentioned ? 'var(--bg-success)' : 'var(--bg-warning)')
                    : 'var(--bg-hover)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <Space size={6} wrap>
                  <Tag color="blue" style={{ margin: 0 }}>{MONITOR_PLATFORM_LABELS[item.platform] || item.platform}</Tag>
                  <Text strong style={{ fontSize: 13 }}>{item.query}</Text>
                </Space>
                {item.status === 'running' && <Spin size="small" />}
                {item.status === 'done' && item.is_mentioned && <Tag color="green" style={{ margin: 0 }}>已提及</Tag>}
                {item.status === 'done' && !item.is_mentioned && <Tag color="red" style={{ margin: 0 }}>未提及</Tag>}
                {item.status === 'error' && <Tag color="red" style={{ margin: 0 }}>错误</Tag>}
              </div>
              {item.status === 'done' && item.sentiment && (
                <div style={{ marginBottom: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    情感：
                    <Tag
                      color={(SENTIMENT_MAP[item.sentiment] || SENTIMENT_MAP.neutral).color}
                      style={{ marginLeft: 4, marginRight: 0 }}
                    >
                      {(SENTIMENT_MAP[item.sentiment] || SENTIMENT_MAP.neutral).label}
                    </Tag>
                    {'  '}提及次数：{item.mention_count ?? 0}
                  </Text>
                </div>
              )}
              {item.content_snippet && (
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4, maxHeight: 60, overflow: 'hidden' }}>
                  {item.content_snippet.length > 100 ? item.content_snippet.slice(0, 100) + '...' : item.content_snippet}
                </div>
              )}
              {item.error && (
                <div style={{ fontSize: 12, color: 'var(--error)', marginTop: 4 }}>{item.error}</div>
              )}
            </div>
          ))}
        </Space>

        {!running && runProgress.length > 0 && (
          <Alert
            type="success"
            showIcon
            message="监测任务执行完成"
            style={{ marginTop: 16 }}
            description={`共检测 ${runTotal} 个平台-查询组合，完成 ${runCompleted} 个。`}
          />
        )}
      </Drawer>

      {/* 后台运行浮动指示器：任务运行中且抽屉关闭时显示 */}
      {running && !runDrawerVisible && (
        <div
          className="bg-run-indicator"
          onClick={() => setRunDrawerVisible(true)}
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 16px',
            borderRadius: 8,
            background: 'var(--brand-500)',
            color: '#fff',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            transition: 'transform 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-2px)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
        >
          <Spin size="small" />
          <span style={{ fontSize: 13 }}>
            {runTaskName} · {runCompleted}/{runTotal}
          </span>
        </div>
      )}
    </div>
  );
};

export default MonitorPage;
