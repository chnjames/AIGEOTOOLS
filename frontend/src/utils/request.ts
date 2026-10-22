import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';
import { ApiResponse } from '@/types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY || '';

const request: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：注入 API Key
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (API_KEY) {
      config.headers.set('X-API-Key', API_KEY);
    }
    const storedKey = localStorage.getItem('api_key');
    if (storedKey) {
      config.headers.set('X-API-Key', storedKey);
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse;
    if (data.code !== undefined && data.code !== 0) {
      message.error(data.message || '请求失败');
      return Promise.reject(new Error(data.message));
    }
    return response;
  },
  (error: AxiosError<{ message?: string; code?: string }>) => {
    if (error.response) {
      const status = error.response.status;
      const errData = error.response.data;
      const msg = errData?.message || `请求错误 (${status})`;
      if (status === 401) {
        message.error('认证失败，请检查 API Key');
      } else if (status === 404) {
        message.error('资源不存在');
      } else if (status >= 500) {
        message.error(`服务器错误: ${msg}`);
      } else {
        message.error(msg);
      }
    } else if (error.code === 'ECONNABORTED') {
      message.error('请求超时，请检查网络连接');
    } else {
      message.error('网络错误，请检查连接');
    }
    return Promise.reject(error);
  }
);

export default request;

/**
 * 通过 fetch 携带 X-API-Key 请求头下载文件，避免将 API Key 暴露在 URL 查询参数中。
 * 获取 Blob 后用 URL.createObjectURL 触发浏览器下载，并在结束后释放对象 URL。
 *
 * @param url 相对路径（如 /data/export/all）或完整 URL
 * @param filename 可选下载文件名；未提供时尝试从响应头 content-disposition 解析
 */
export async function downloadWithAuth(url: string, filename?: string): Promise<void> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  const headers: Record<string, string> = {};
  const storedKey = localStorage.getItem('api_key');
  if (storedKey) headers['X-API-Key'] = storedKey;
  if (API_KEY) headers['X-API-Key'] = API_KEY;

  const response = await fetch(fullUrl, { headers });
  if (!response.ok) {
    throw new Error(`下载失败: HTTP ${response.status}`);
  }
  const blob = await response.blob();

  // 尝试从 content-disposition 解析文件名
  let finalName = filename;
  if (!finalName) {
    const disposition = response.headers.get('content-disposition') || '';
    const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)["']?/i);
    if (match) {
      try {
        finalName = decodeURIComponent(match[1]);
      } catch (err) {
        console.warn('[request] decodeURIComponent failed for filename, using raw value:', err);
        finalName = match[1];
      }
    }
  }

  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = finalName || 'download';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // 释放对象 URL，避免内存泄漏
  setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}

// SSE 连接工具
export class SSEClient {
  private eventSource: EventSource | null = null;
  private abortController: AbortController | null = null;
  // 超时定时器：用于在没有数据流入时主动中断连接，避免长期挂起导致内存泄漏
  private timeoutId: ReturnType<typeof setTimeout> | null = null;
  // 默认单次流式请求最长存活时间（10 分钟），防止后端异常导致连接永久挂起
  private static readonly DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
  // 两次数据块之间的最大间隔（90s），超过视为连接异常
  private static readonly IDLE_TIMEOUT_MS = 90 * 1000;

  /**
   * （重新）设置空闲超时定时器。
   * 每收到一帧数据都会重置该定时器，若超过 IDLE_TIMEOUT_MS 仍无数据则主动中断。
   */
  private resetIdleTimer(onTimeout: () => void) {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }
    this.timeoutId = setTimeout(() => {
      onTimeout();
    }, SSEClient.IDLE_TIMEOUT_MS);
  }

  async connectPOST(
    url: string,
    body: Record<string, unknown>,
    handlers: {
      onStart?: (data: Record<string, unknown> & { warnings?: Array<{ field: string; warning: string }> }) => void;
      onProgress?: (data: Record<string, unknown>) => void;
      onChunk?: (data: { content: string }) => void;
      onComplete?: (data: Record<string, unknown>) => void;
      onError?: (data: Record<string, unknown> & { error_type?: string }) => void;
      onEvent?: (event: string, data: Record<string, unknown>) => void;
      onModelStart?: (data: Record<string, unknown> & { model?: string; provider?: string }) => void;
      onModelComplete?: (data: Record<string, unknown>) => void;
      onArticleDone?: (data: Record<string, unknown>) => void;
    },
    options: { timeoutMs?: number } = {}
  ): Promise<void> {
    // 创建新连接前先清理旧连接，防止旧 reader 持续占用内存与连接
    this.disconnect();
    this.abortController = new AbortController();

    const totalTimeoutMs = options.timeoutMs ?? SSEClient.DEFAULT_TIMEOUT_MS;
    // 整体超时兜底：即使持续有数据流入，也不允许超过 totalTimeoutMs
    const totalTimer = setTimeout(() => {
      this.abortController?.abort();
    }, totalTimeoutMs);

    try {
      const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      const storedKey = localStorage.getItem('api_key');
      if (storedKey) headers['X-API-Key'] = storedKey;
      if (API_KEY) headers['X-API-Key'] = API_KEY;

      const response = await fetch(fullUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: this.abortController.signal,
      });

      if (!response.ok || !response.body) {
        handlers.onError?.({ message: `HTTP ${response.status}` });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // 空闲超时回调：超过 IDLE_TIMEOUT_MS 无数据则主动中断并通知
      const idleHandler = () => {
        this.abortController?.abort();
        handlers.onError?.({ message: 'SSE 连接空闲超时，已自动断开', error_type: 'timeout' });
      };
      // 启动空闲超时监控
      this.resetIdleTimer(idleHandler);

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // 正常结束，清掉空闲定时器
          if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
          }
          break;
        }
        // 收到任意数据帧后重置空闲定时器
        this.resetIdleTimer(idleHandler);

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const eventBlock of events) {
          if (!eventBlock.trim() || eventBlock.startsWith(':')) continue;

          let eventType = 'message';
          let eventData = '';

          for (const line of eventBlock.split('\n')) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              eventData += line.slice(5).trim();
            }
          }

          let parsed: Record<string, unknown> = {};
          try {
            parsed = JSON.parse(eventData);
          } catch (err) {
            console.warn('[request] SSE event JSON.parse failed, storing as raw:', err);
            parsed = { raw: eventData };
          }

          handlers.onEvent?.(eventType, parsed);

          switch (eventType) {
            case 'start':
              handlers.onStart?.(parsed);
              break;
            case 'progress':
              handlers.onProgress?.(parsed);
              break;
            case 'chunk':
              handlers.onChunk?.(parsed as { content: string });
              break;
            case 'complete':
            case 'done':
              handlers.onComplete?.(parsed);
              break;
            case 'error':
              handlers.onError?.(parsed);
              break;
            case 'model_start':
              handlers.onModelStart?.(parsed);
              break;
            case 'model_complete':
              handlers.onModelComplete?.(parsed);
              break;
            case 'model_error':
              handlers.onError?.({ ...parsed, error_type: parsed.error_type as string || 'model_error' });
              break;
            case 'article_done':
              handlers.onArticleDone?.(parsed);
              break;
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error).name !== 'AbortError') {
        handlers.onError?.({ message: (err as Error).message });
      }
    } finally {
      // 无论正常结束、出错还是超时，都清理整体超时与空闲定时器，避免内存泄漏
      clearTimeout(totalTimer);
      if (this.timeoutId) {
        clearTimeout(this.timeoutId);
        this.timeoutId = null;
      }
    }
  }

  disconnect() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

export const sseClient = new SSEClient();
