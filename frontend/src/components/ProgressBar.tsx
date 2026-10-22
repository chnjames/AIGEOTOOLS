import React from 'react';
import { Progress as AntProgress, Typography } from 'antd';

const { Text } = Typography;

interface ProgressBarProps {
  percent: number;
  status?: 'active' | 'success' | 'exception' | 'normal';
  message?: string;
  logs?: string[];
}

/**
 * 实时进度条 + 日志流组件
 */
const ProgressBar: React.FC<ProgressBarProps> = ({ percent, status = 'active', message, logs }) => {
  return (
    <div>
      {message && (
        <div style={{ marginBottom: 4, fontSize: 13 }}>
          <Text>{message}</Text>
        </div>
      )}
      <AntProgress percent={Math.round(percent)} status={status} strokeWidth={8} />
      {logs && logs.length > 0 && (
        <div
          style={{
            maxHeight: 200,
            overflow: 'auto',
            background: 'var(--bg-tertiary)',
            borderRadius: 4,
            padding: 8,
            marginTop: 8,
            fontSize: 12,
            fontFamily: 'monospace',
          }}
        >
          {logs.map((log, i) => (
            <div key={i} style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {log}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
