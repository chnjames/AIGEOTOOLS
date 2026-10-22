/**
 * 全局常量与工具函数
 * 
 * 提取自各页面中重复定义的常量映射和辅助函数，
 * 统一维护，避免多处重复。
 */

// ─── 模型供应商标签 ──────────────────────────────────────────────────────────
export const PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  openai: 'OpenAI (GPT)',
  tongyi: '通义千问',
  groq: 'Groq',
  moonshot: 'Kimi',
  doubao: '豆包',
  wenxin: '文心一言',
  yuanbao: '腾讯元宝',
};

// ─── 供应商选项列表（用于 Select 下拉） ──────────────────────────────────────
export const PROVIDER_OPTIONS = [
  'DeepSeek', 'OpenAI (GPT)', 'Tongyi (通义千问)', 'Groq',
  'Moonshot (Kimi)', '豆包（字节跳动）', '文心一言（百度）',
] as const;

// ─── 验证/配置用供应商 key 列表（用于多模型验证、配置优化器等） ────────────────
export const VERIFY_PROVIDER_KEYS = ['deepseek', 'openai', 'tongyi', 'groq', 'moonshot', 'doubao', 'wenxin'] as const;

// ─── AI 监测平台列表 ──────────────────────────────────────────────────────────
export const MONITOR_PLATFORMS = ['wenxin', 'doubao', 'yuanbao', 'deepseek', 'kimi', 'tongyi'] as const;

// ─── AI 监测平台标签（复用 PROVIDER_LABELS） ──────────────────────────────────
export const MONITOR_PLATFORM_LABELS: Record<string, string> = {
  wenxin: '文心一言',
  doubao: '豆包',
  yuanbao: '腾讯元宝',
  deepseek: 'DeepSeek',
  kimi: 'Kimi',
  tongyi: '通义千问',
};

// ─── 内容发布平台（回退列表） ────────────────────────────────────────────────
export const CONTENT_PLATFORMS: Array<{ key: string; name: string }> = [
  { key: 'zhihu', name: '知乎' },
  { key: 'xiaohongshu', name: '小红书' },
  { key: 'csdn', name: 'CSDN' },
  { key: 'wechat', name: '微信公众号' },
  { key: 'bilibili', name: 'B站' },
  { key: 'juejin', name: '掘金' },
  { key: 'toutiao', name: '头条号' },
  { key: 'baijiahao', name: '百家号' },
  { key: 'sohu', name: '搜狐号' },
  { key: 'github', name: 'GitHub' },
];

// ─── 已知内容平台名称（用于文本解析匹配） ────────────────────────────────────
export const KNOWN_CONTENT_PLATFORM_NAMES = [
  '知乎', '小红书', 'CSDN', '微信公众号', 'B站', '掘金', '头条号', '百家号', '搜狐号', 'GitHub',
];

// ─── 默认验证模型列表 ────────────────────────────────────────────────────────
export const DEFAULT_VERIFY_MODELS = ['gpt-4o', 'claude', 'doubao', 'qwen', 'deepseek'];

// ─── 错误类型映射 ─────────────────────────────────────────────────────────────
export const ERROR_TYPE_MAP: Record<string, string> = {
  auth_error: 'API Key 无效',
  balance_error: '余额不足',
  timeout: '请求超时',
  rate_limit: '请求频率超限',
  model_not_found: '模型名称无效',
  network_error: '网络连接失败',
};

/** 根据错误类型返回友好的中文提示 */
export function getErrorMessage(errorType?: string, errorMsg?: string): string {
  if (errorType && ERROR_TYPE_MAP[errorType]) return ERROR_TYPE_MAP[errorType];
  return errorMsg || '操作失败，请重试';
}

// ─── 平台图标映射（中文首字） ────────────────────────────────────────────────
export const PLATFORM_ICONS: Record<string, string> = {
  '知乎': '知', '小红书': '红', 'CSDN': 'C', '微信公众号': '微', 'B站': 'B',
  'GitHub': 'G', '掘金': '掘', '头条号': '头', '百家号': '百', '搜狐号': '搜',
  '微博': '微', '抖音': '抖', '快手': '快', '简书': '简', '知乎专栏': '知',
};

// ─── 平台颜色映射（用于图表） ────────────────────────────────────────────────
export const PLATFORM_COLORS: Record<string, string> = {
  wenxin: '#3370ff',
  doubao: '#0066ff',
  yuanbao: '#07c160',
  deepseek: '#4d6bfe',
  kimi: '#000000',
  tongyi: '#ff6a00',
};

// ─── 评分工具函数 ─────────────────────────────────────────────────────────────

/** 根据分数返回对应颜色（优秀=绿、良好=蓝、中等=黄、需改进=红） */
export function getScoreColor(score: number): string {
  if (score >= 90) return '#10B981';
  if (score >= 75) return '#3B82F6';
  if (score >= 60) return '#F59E0B';
  return '#EF4444';
}

/** 根据分数返回对应等级文本 */
export function getScoreLevel(score: number): string {
  if (score >= 90) return '优秀';
  if (score >= 75) return '良好';
  if (score >= 60) return '中等';
  return '需改进';
}
