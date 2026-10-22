import React from 'react';
import { Card, Statistic } from 'antd';

interface KpiCardProps {
  /** 卡片标题/标签 */
  label: string;
  /** 数值 */
  value: number | string;
  /** 前缀图标 */
  icon?: React.ReactNode;
  /** 主题色（CSS 变量，如 'var(--brand-500)'） */
  color?: string;
  /** 数值前缀（如 '$'、'¥'） */
  prefix?: string;
  /** 数值后缀（如 '%'） */
  suffix?: string;
  /** 小数位数 */
  precision?: number;
  /** 点击跳转路径（可选） */
  onClick?: () => void;
  /** 是否可悬浮（有 onClick 时默认 true） */
  hoverable?: boolean;
  /** 数值样式覆盖 */
  valueStyle?: React.CSSProperties;
  /** 图标背景色（可选，默认透明） */
  iconBg?: string;
}

/**
 * 统一 KPI 卡片组件
 * - 用于 Dashboard、ReportsPage 等需要展示统计指标的页面
 * - 支持点击跳转、自定义图标和颜色
 * - 所有颜色使用 CSS 变量，支持主题切换
 */
const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  icon,
  color = 'var(--text-primary)',
  prefix,
  suffix,
  precision,
  onClick,
  hoverable,
  valueStyle,
  iconBg,
}) => {
  const isClickable = !!onClick;
  const isHoverable = hoverable ?? isClickable;

  return (
    <Card
      hoverable={isHoverable}
      onClick={onClick}
      styles={{ body: { padding: 20 } }}
    >
      {icon ? (
        <div className="flex items-center gap-3 mb-1">
          <span
            className="flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0"
            style={{
              background: iconBg || 'transparent',
              color,
              fontSize: 18,
            }}
          >
            {icon}
          </span>
          <span className="text-xs text-text-tertiary">{label}</span>
        </div>
      ) : null}
      <Statistic
        title={icon ? undefined : label}
        value={value}
        prefix={prefix}
        suffix={suffix}
        precision={precision}
        valueStyle={{
          color,
          fontSize: icon ? 24 : undefined,
          fontWeight: 600,
          ...valueStyle,
        }}
      />
    </Card>
  );
};

export default KpiCard;
