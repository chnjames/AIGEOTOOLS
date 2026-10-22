import React, { useState } from 'react';
import { Tabs } from 'antd';
import ReactMarkdown from 'react-markdown';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: number;
  placeholder?: string;
}

/**
 * Markdown 编辑+预览组件
 */
const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  height = 400,
  placeholder = '在此输入 Markdown 内容...',
}) => {
  const [activeTab, setActiveTab] = useState('edit');

  return (
    <Tabs
      activeKey={activeTab}
      onChange={setActiveTab}
      size="small"
      items={[
        {
          key: 'edit',
          label: '编辑',
          children: (
            <textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder={placeholder}
              style={{
                width: '100%',
                height,
                padding: 12,
                border: '1px solid var(--border-default)',
                borderRadius: 6,
                fontFamily: 'monospace',
                fontSize: 13,
                resize: 'vertical',
                outline: 'none',
                boxSizing: 'border-box',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
              }}
            />
          ),
        },
        {
          key: 'preview',
          label: '预览',
          children: (
            <div
              style={{
                minHeight: height,
                maxHeight: height + 100,
                overflow: 'auto',
                padding: 12,
                border: '1px solid var(--border-default)',
                borderRadius: 6,
                background: 'var(--bg-tertiary)',
              }}
              className="markdown-preview"
            >
              {value ? <ReactMarkdown>{value}</ReactMarkdown> : <span style={{ color: 'var(--text-tertiary)' }}>预览区域</span>}
            </div>
          ),
        },
      ]}
    />
  );
};

export default MarkdownEditor;
