/**
 * ECharts 暗色主题适配工具
 *
 * 提供 dark/light 模式下的通用图表配置（文字颜色、轴线颜色、分割线颜色等），
 * 各图表页面调用 getEChartsTheme(darkMode) 获取基础配色，再合并到自己的 option 中。
 */

export interface EChartsThemeColors {
  /** 坐标轴文字颜色 */
  axisLabelColor: string;
  /** 坐标轴线颜色 */
  axisLineColor: string;
  /** 分割线颜色 */
  splitLineColor: string;
  /** 标题文字颜色 */
  textColor: string;
  /** 图例文字颜色 */
  legendTextColor: string;
  /** tooltip 背景色 */
  tooltipBg: string;
  /** tooltip 边框色 */
  tooltipBorderColor: string;
  /** tooltip 文字色 */
  tooltipTextColor: string;
}

/**
 * 根据暗色模式返回 ECharts 通用配色
 */
export function getEChartsThemeColors(darkMode: boolean): EChartsThemeColors {
  return darkMode
    ? {
        axisLabelColor: '#6b6f82',
        axisLineColor: '#2a2d3e',
        splitLineColor: '#1e2130',
        textColor: '#e2e4e9',
        legendTextColor: '#9ca0b0',
        tooltipBg: '#1e2130',
        tooltipBorderColor: '#2a2d3e',
        tooltipTextColor: '#e2e4e9',
      }
    : {
        axisLabelColor: '#9ca3af',
        axisLineColor: '#e5e7eb',
        splitLineColor: '#f4f5f7',
        textColor: '#111827',
        legendTextColor: '#4b5563',
        tooltipBg: '#ffffff',
        tooltipBorderColor: '#e5e7eb',
        tooltipTextColor: '#111827',
      };
}

/**
 * 生成通用的 xAxis 基础配置（不含 data/type，由调用方合并）
 */
export function getAxisBase(darkMode: boolean) {
  const c = getEChartsThemeColors(darkMode);
  return {
    axisLabel: { fontSize: 11, color: c.axisLabelColor },
    axisLine: { lineStyle: { color: c.axisLineColor } },
  };
}

/**
 * 生成通用的 yAxis 基础配置
 */
export function getYAxisBase(darkMode: boolean) {
  const c = getEChartsThemeColors(darkMode);
  return {
    axisLabel: { fontSize: 11, color: c.axisLabelColor },
    axisLine: { lineStyle: { color: c.axisLineColor } },
    splitLine: { lineStyle: { color: c.splitLineColor } },
  };
}

/**
 * 生成通用的 tooltip 配置
 */
export function getTooltipBase(darkMode: boolean) {
  const c = getEChartsThemeColors(darkMode);
  return {
    backgroundColor: c.tooltipBg,
    borderColor: c.tooltipBorderColor,
    textStyle: { color: c.tooltipTextColor },
  };
}

/**
 * 生成通用的 legend 配置
 */
export function getLegendBase(darkMode: boolean) {
  const c = getEChartsThemeColors(darkMode);
  return {
    textStyle: { color: c.legendTextColor },
  };
}
