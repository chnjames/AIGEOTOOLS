import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Progress } from 'antd';
import { getScoreColor, getScoreLevel } from '@/constants';
import { useAppStore } from '@/stores';
import { getEChartsThemeColors } from '@/utils/echartsTheme';

interface ScoreData {
  structure: number;
  brand_mention: number;
  authority: number;
  citations: number;
  total: number;
}

/**
 * 评分雷达图组件
 */
export const ScoreRadarChart: React.FC<{ scores: ScoreData }> = ({ scores }) => {
  const { darkMode } = useAppStore();
  const option = useMemo(() => {
    const themeColors = getEChartsThemeColors(darkMode);
    return {
      radar: {
        indicator: [
          { name: '结构化', max: 25 },
          { name: '品牌提及', max: 25 },
          { name: '权威性', max: 25 },
          { name: '可引用性', max: 25 },
        ],
        radius: '70%',
        axisName: {
          color: themeColors.textColor,
        },
        splitArea: {
          areaStyle: { color: ['rgba(22,119,255,0.02)', 'rgba(22,119,255,0.05)'] }
        },
        splitLine: {
          lineStyle: { color: themeColors.splitLineColor },
        },
        axisLine: {
          lineStyle: { color: themeColors.axisLineColor },
        },
      },
      series: [{
        type: 'radar',
        data: [{
          value: [scores.structure, scores.brand_mention, scores.authority, scores.citations],
          name: '评分',
          areaStyle: { color: 'rgba(22,119,255,0.2)' },
          lineStyle: { color: '#1677ff' },
          itemStyle: { color: '#1677ff' },
        }],
      }],
    };
  }, [scores, darkMode]);

  return <ReactECharts option={option} style={{ height: 300 }} />;
};

/**
 * 总分显示组件（环形进度条）
 */
export const TotalScoreGauge: React.FC<{ score: number; label?: string }> = ({ score, label = '总分' }) => {
  return (
    <div style={{ textAlign: 'center', padding: 16 }}>
      <Progress
        type="circle"
        percent={score}
        strokeColor={getScoreColor(score)}
        format={(p) => <span style={{ fontSize: 24, fontWeight: 'bold', color: getScoreColor(score) }}>{p}</span>}
        size={140}
      />
      <div style={{ marginTop: 8, fontSize: 16, fontWeight: 500, color: getScoreColor(score) }}>
        {label}: {getScoreLevel(score)}
      </div>
    </div>
  );
};

/**
 * 单维度进度条
 */
export const ScoreBar: React.FC<{ label: string; score: number; max: number }> = ({ label, score, max }) => (
  <div style={{ marginBottom: 8 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 2 }}>
      <span>{label}</span>
      <span style={{ fontWeight: 500 }}>{score}/{max}</span>
    </div>
    <Progress percent={Math.round((score / max) * 100)} showInfo={false} strokeWidth={6} size="small" />
  </div>
);
