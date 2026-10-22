// 通用 API 响应类型
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 配置
export interface AppConfig {
  gen_provider: string;
  gen_api_key_masked: string;
  gen_api_key_configured: boolean;
  verify_providers: string[];
  verify_keys_configured: Record<string, boolean>;
  tongyi_wanxiang_configured: boolean;
  brand: string;
  advantages: string;
  competitors: string;
  temperature: number;
  use_knowledge_base: boolean;
  roi_value_per_mention: number;
  platform_value_coefficients: Record<string, number>;
  first_run_completed: boolean;
  default_verify_mode: string;
}

export interface AppConfigUpdate {
  gen_provider?: string;
  gen_api_key?: string;
  verify_providers?: string[];
  verify_keys?: Record<string, string>;
  tongyi_wanxiang_api_key?: string;
  brand?: string;
  advantages?: string;
  competitors?: string;
  temperature?: number;
  use_knowledge_base?: boolean;
  roi_value_per_mention?: number;
  platform_value_coefficients?: Record<string, number>;
  first_run_completed?: boolean;
  default_verify_mode?: string;
}

export interface ProviderTestRequest {
  provider: string;
  api_key: string;
  model?: string;
}

// 关键词
export interface Keyword {
  id: number;
  keyword: string;
  brand?: string;
  is_favorite: boolean;
  tags?: string;
  created_at?: string;
}

// 文章
export interface Article {
  id: number;
  keyword?: string;
  platform?: string;
  content?: string;
  filename?: string;
  brand?: string;
  publish_status: string;
  publish_urls?: string;
  multimodal?: string;
  created_at?: string;
}

export interface PlatformInfo {
  key: string;
  name: string;
  publish_methods: string[];
  icon: string;
  style?: string;
}

// 优化记录
export interface Optimization {
  id: number;
  original_content?: string;
  optimized_content?: string;
  changes?: string;
  platform?: string;
  brand?: string;
  optimization_type?: string;
  score_result?: string;
  created_at?: string;
}

// 验证结果（旧定义已移至文件末尾，含新字段）

// 内容评分
export interface ScoreResult {
  scores: {
    structure: number;
    brand_mention: number;
    authority: number;
    citations: number;
    total: number;
  };
  details: {
    structure: string;
    brand_mention: string;
    authority: string;
    citations: string;
  };
  improvements: string[];
  strengths: string[];
}

export interface ContentMetrics {
  word_count: number;
  paragraph_count: number;
  heading_count: number;
  list_count: number;
  brand_count: number;
  keyword_density: number;
  readability_score: number;
  has_faq: boolean;
  has_citations: boolean;
  avg_paragraph_length: number;
}

// KPI
export interface KPIData {
  total_keywords: number;
  total_articles: number;
  total_optimizations: number;
  total_verifications: number;
  total_cost_cny: number;
  mention_rate: number;
}

// 成本报表
export interface CostReport {
  total_cost_usd: number;
  total_cost_cny: number;
  total_tokens: number;
  total_calls: number;
  cost_by_operation: Record<string, { cost_usd: number; cost_cny: number; calls: number; tokens: number }>;
  cost_by_provider: Record<string, { cost_usd: number; cost_cny: number; calls: number; tokens: number }>;
  cost_by_keyword: Record<string, unknown>;
  cost_by_platform: Record<string, unknown>;
  daily_costs: Array<{ date: string; cost_usd: number; cost_cny: number; calls: number; tokens: number }>;
}

export interface MentionReport {
  total_verifications: number;
  total_mentioned: number;
  mention_rate: number;
  mention_rate_by_model: Record<string, { total: number; mentioned: number; rate: number }>;
  mention_trend: unknown[];
  top_mentioned_queries: unknown[];
}

// 工作流
export interface WorkflowStep {
  step_type: string;
  name: string;
  config: Record<string, unknown>;
}

export interface Workflow {
  id: string;
  name: string;
  steps: string; // JSON string
  schedule?: string;
  conditions?: string;
  enabled: boolean;
  brand?: string;
  created_at?: string;
  updated_at?: string;
}

export interface WorkflowExecution {
  id: number;
  workflow_id: string;
  status: string;
  result?: string;
  progress: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
  logs?: string;
}

// 平台账号
export interface PlatformAccount {
  id: number;
  platform: string;
  account_type: string;
  account_name?: string;
  is_active: boolean;
  brand?: string;
  has_api_key: boolean;
  has_token: boolean;
  created_at?: string;
}

// 知识库
export interface KnowledgeDoc {
  id: number;
  filename: string;
  file_type?: string;
  brand?: string;
  chunk_count: number;
  created_at?: string;
}

export interface KnowledgeChunk {
  doc_id: number;
  filename: string;
  content: string;
  score: number;
}

// 资源
export interface Resource {
  title: string;
  url: string;
  category: string;
  description: string;
}

export interface Technique {
  name: string;
  category: string;
  description: string;
  example: string;
}

// SSE 事件类型
export type SSEEventType = 'start' | 'progress' | 'chunk' | 'complete' | 'error' | 'done' |
  'model_start' | 'model_complete' | 'model_error' |
  'article_done' | 'article_error' | 'log' | 'step_error';

export interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
}

// 发布
export interface PublishRequest {
  platform: string;
  publish_method: string;
  config?: Record<string, unknown>;
}

export interface PublishResponse {
  success: boolean;
  platform: string;
  publish_url?: string;
  message: string;
  content?: string;
  filename?: string;
}

export interface PublishRecord {
  id: number;
  article_id?: number;
  platform: string;
  publish_method: string;
  publish_status: string;
  publish_url?: string;
  error_message?: string;
  retry_count: number;
  published_at?: string;
  created_at?: string;
}

// 文章版本
export interface ArticleVersion {
  id: number;
  article_id: number;
  version_number: number;
  content: string;
  source: string;
  note?: string;
  dds_score?: string;
  created_at?: string;
}

export interface DiffResult {
  diff_html: string;
  additions: number;
  deletions: number;
}

// 验证结果（含情感分析、诊断和完整响应）
export interface VerifyResult {
  id: number;
  query?: string;
  brand?: string;
  verify_model?: string;
  mention_count: number;
  positive_mentions?: number;
  negative_mentions?: number;
  sentiment?: string; // positive/neutral/negative
  verification_mode?: string; // natural/prompted
  diagnosis?: string;
  recommended_brands?: string;
  mention_position?: string;
  content_snippet?: string;
  full_response?: string;
  is_mentioned: boolean;
  created_at?: string;
}

// LLM 错误分类
export interface LLMErrorInfo {
  error_type: string;
  message: string;
  provider?: string;
  retriable: boolean;
}

// 注入警告
export interface InjectionWarning {
  field: string;
  warning: string;
}

// 关键词质量分析
export interface KeywordQuality {
  total: number;
  intent_distribution: Record<string, number>;
  brand_keyword_ratio: number;
  question_ratio: number;
  avg_length: number;
  long_tail_ratio: number;
  suggestions: string[];
}

export interface IndustryPreset {
  key: string;
  name: string;
  description: string;
  seed_keywords: string[];
}

// 平台分组
export interface PlatformGroup {
  group: string;
  platforms: PlatformInfo[];
}

// 平台模板
export interface PlatformTemplate {
  id: number;
  name: string;
  style: string;       // 后端返回映射: style_instruction → style
  style_instruction?: string;  // 创建/更新时使用
  filename_suffix: string;
  group: string;       // 后端返回映射: group_name → group
  group_name?: string; // 创建/更新时使用
  is_default: boolean;
  is_active: boolean;
  word_count_default: number;
}

// 数据管理
export interface StorageStats {
  db_file_size_bytes: number | null;
  db_file_path: string | null;
  knowledge_dir_size_bytes: number;
  knowledge_dir_path: string;
  table_counts: Record<string, number>;
}

export interface AuditLog {
  id: number;
  action: string;
  resource_type: string;
  resource_id?: string;
  detail?: Record<string, unknown>;
  result: string;
  error_message?: string;
  operator?: string;
  created_at?: string;
}

export interface CleanupResult {
  [table: string]: number;
}

export interface ImportResult {
  [module: string]: { inserted: number; updated: number; skipped: number };
}
