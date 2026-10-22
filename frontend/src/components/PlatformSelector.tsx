import React from 'react';
import { Checkbox } from 'antd';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';

interface PlatformInfo {
  key: string;
  name: string;
}

interface PlatformSelectorProps {
  platforms: PlatformInfo[];
  selected: string[];
  onChange: (selected: string[]) => void;
  columns?: number;
}

const ALL_PLATFORM_ICONS: Record<string, string> = {
  '知乎': '知', '小红书': '红', 'CSDN': 'C', '微信公众号': '微', 'B站': 'B',
  'GitHub': 'G', '掘金': '掘', '头条号': '头', '百家号': '百', '搜狐号': '搜',
};

/**
 * 平台多选组件
 */
const PlatformSelector: React.FC<PlatformSelectorProps> = ({ platforms, selected, onChange, columns = 4 }) => {
  const handleToggle = (name: string) => (e: CheckboxChangeEvent) => {
    if (e.target.checked) {
      onChange([...selected, name]);
    } else {
      onChange(selected.filter(p => p !== name));
    }
  };

  const handleSelectAll = () => {
    if (selected.length === platforms.length) {
      onChange([]);
    } else {
      onChange(platforms.map(p => p.name || p.key));
    }
  };

  const allSelected = selected.length === platforms.length && platforms.length > 0;
  const indeterminate = selected.length > 0 && selected.length < platforms.length;

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <Checkbox
          checked={allSelected}
          indeterminate={indeterminate}
          onChange={handleSelectAll}
        >
          全选
        </Checkbox>
        <span style={{ marginLeft: 12, color: '#999', fontSize: 12 }}>
          已选 {selected.length} / {platforms.length}
        </span>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: 8,
      }}>
        {platforms.map(p => {
          const name = p.name || p.key;
          const isChecked = selected.includes(name);
          return (
            <div
              key={p.key}
              onClick={() => {
                if (isChecked) onChange(selected.filter(x => x !== name));
                else onChange([...selected, name]);
              }}
              style={{
                padding: '8px 12px',
                border: `2px solid ${isChecked ? 'var(--brand-500)' : 'var(--border-default)'}`,
                borderRadius: 8,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: isChecked ? 'var(--brand-50)' : 'var(--bg-secondary)',
                transition: 'all 0.2s',
                fontSize: 13,
              }}
            >
              <Checkbox checked={isChecked} onChange={handleToggle(name)} />
              <span style={{
                width: 22, height: 22, borderRadius: 4,
                background: isChecked ? 'var(--brand-500)' : 'var(--bg-tertiary)',
                color: isChecked ? 'var(--text-inverse)' : 'var(--text-tertiary)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 600, flexShrink: 0,
              }}>
                {ALL_PLATFORM_ICONS[name] || name[0]}
              </span>
              <span>{name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PlatformSelector;
