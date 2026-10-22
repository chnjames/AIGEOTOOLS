import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Typography, Spin, Alert } from 'antd';
import ReactMarkdown from 'react-markdown';
import { SSEClient } from '@/utils/request';

const { Text } = Typography;

interface StreamingTextProps {
  // 触发流式请求的函数，接收 handlers 参数
  fetchStream: (handlers: Parameters<SSEClient['connectPOST']>[2]) => void;
  onComplete?: (fullText: string, data?: Record<string, unknown>) => void;
  autoStart?: boolean;
  showCursor?: boolean;
  height?: number | string;
  placeholder?: string;
}

/**
 * SSE 流式文本渲染组件
 * - 打字机效果逐字显示
 * - POST 请求发送 body
 * - 组件卸载时自动关闭连接
 * - 错误处理和重试
 */
const StreamingText: React.FC<StreamingTextProps> = ({
  fetchStream,
  onComplete,
  autoStart = true,
  showCursor = true,
  height,
  placeholder = '等待生成...',
}) => {
  const [text, setText] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState('');
  const clientRef = useRef<SSEClient | null>(null);
  const textRef = useRef('');
  const mountedRef = useRef(true);

  const startStream = useCallback(() => {
    setText('');
    setError(null);
    setProgress(0);
    setProgressMsg('');
    textRef.current = '';
    setStreaming(true);

    const client = new SSEClient();
    clientRef.current = client;

    fetchStream({
      onStart: () => {
        if (!mountedRef.current) return;
        setProgressMsg('正在连接...');
      },
      onProgress: (data) => {
        if (!mountedRef.current) return;
        const p = Number(data.progress) || 0;
        setProgress(p);
        if (data.message) setProgressMsg(String(data.message));
      },
      onChunk: (data) => {
        if (!mountedRef.current) return;
        const content = data.content || '';
        textRef.current += content;
        setText(textRef.current);
      },
      onComplete: (data) => {
        if (!mountedRef.current) return;
        setStreaming(false);
        setProgress(100);
        setProgressMsg('完成');
        const fullContent = (data.full_content as string) || textRef.current;
        onComplete?.(fullContent, data);
      },
      onError: (data) => {
        if (!mountedRef.current) return;
        setStreaming(false);
        setError(String(data.message || data.error || '生成失败'));
      },
    });
  }, [fetchStream, onComplete]);

  useEffect(() => {
    mountedRef.current = true;
    if (autoStart) {
      startStream();
    }
    return () => {
      mountedRef.current = false;
      clientRef.current?.disconnect();
    };
  }, [autoStart, startStream]);

  return (
    <div style={{ height, position: 'relative' }}>
      {error && (
        <Alert
          type="error"
          message={error}
          action={
            <a onClick={startStream}>重试</a>
          }
          style={{ marginBottom: 12 }}
        />
      )}

      {streaming && (
        <div style={{ marginBottom: 8 }}>
          {progressMsg && <Text type="secondary" style={{ fontSize: 12 }}>{progressMsg}</Text>}
          {progress > 0 && progress < 100 && (
            <div style={{
              height: 3, background: 'var(--border-light)', borderRadius: 2, marginTop: 4, overflow: 'hidden'
            }}>
              <div style={{
                height: '100%', background: 'var(--brand-500)', width: `${progress}%`,
                transition: 'width 0.3s', borderRadius: 2,
              }} />
            </div>
          )}
        </div>
      )}

      <div style={{ minHeight: 100 }}>
        {text ? (
          <div className="streaming-content">
            <ReactMarkdown>{text + (streaming && showCursor ? '▌' : '')}</ReactMarkdown>
          </div>
        ) : streaming ? (
          <div style={{ color: 'var(--text-tertiary)', padding: 20, textAlign: 'center' }}>
            <Spin size="small" style={{ marginRight: 8 }} />
            正在生成...
          </div>
        ) : error ? null : (
          <Text type="secondary">{placeholder}</Text>
        )}
      </div>
    </div>
  );
};

export default StreamingText;
