import React, { useEffect } from 'react';
import { ConfigProvider, theme as antdTheme, App as AntApp } from 'antd';
import { BrowserRouter, useLocation } from 'react-router-dom';
import zhCN from 'antd/locale/zh_CN';
import { useAppStore } from '@/stores';
import AppLayout from '@/layouts/AppLayout';
import AppRoutes from '@/layouts/AppRoutes';
import { ErrorBoundary } from '@/components';

/**
 * 根据当前路径决定是否包裹 AppLayout。
 * 分享报告页（/marketing-reports/share/:token）面向外部访问者，
 * 不应展示侧边栏/顶栏等内部布局，因此直接渲染路由内容。
 */
const LayoutSwitch: React.FC = () => {
  const location = useLocation();
  const isShareRoute = location.pathname.includes('/marketing-reports/share/');

  if (isShareRoute) {
    // 外部分享场景：不渲染 AppLayout，仅渲染路由内容
    return <AppRoutes />;
  }
  return <AppLayout />;
};

const App: React.FC = () => {
  const { darkMode, fetchConfig } = useAppStore();

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: darkMode ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          // 品牌色 - 与 global.css --brand-500 保持一致
          colorPrimary: '#3b82f6',
          // 语义色 - 与 global.css CSS 变量保持一致
          colorSuccess: '#10b981',
          colorWarning: '#f59e0b',
          colorError: '#ef4444',
          colorInfo: '#3b82f6',
          // 基础
          borderRadius: 6,
          fontSize: 14,
          controlHeight: 34,
          // 链接色
          colorLink: '#2563eb',
          colorLinkHover: '#1d4ed8',
          // 文本色（让 antd 组件文本跟随主题）
          colorText: darkMode ? '#e2e4e9' : '#111827',
          colorTextSecondary: darkMode ? '#9ca0b0' : '#4b5563',
          colorTextTertiary: darkMode ? '#6b6f82' : '#9ca3af',
          colorTextDescription: darkMode ? '#6b6f82' : '#9ca3af',
          // 边框色
          colorBorder: darkMode ? '#2a2d3e' : '#e5e7eb',
          colorBorderSecondary: darkMode ? '#1e2130' : '#f0f0f0',
          // 背景色
          colorBgContainer: darkMode ? '#161922' : '#ffffff',
          colorBgElevated: darkMode ? '#1e2130' : '#ffffff',
          colorBgLayout: darkMode ? '#0f1117' : '#fafafa',
          colorBgSpotlight: darkMode ? '#252838' : '#f4f5f7',
        },
        components: {
          Card: {
            borderRadiusLG: 8,
            paddingLG: 16,
            headerHeight: 44,
            headerFontSize: 13,
            headerFontSizeSM: 13,
          },
          Button: {
            controlHeight: 32,
            borderRadius: 6,
            controlHeightSM: 28,
            controlHeightLG: 40,
            paddingInline: 14,
            paddingInlineSM: 10,
            paddingInlineLG: 20,
          },
          Input: {
            controlHeight: 34,
            borderRadius: 6,
            paddingInline: 11,
          },
          Select: {
            controlHeight: 34,
            borderRadius: 6,
          },
          Table: {
            cellPaddingBlock: 10,
            headerBg: 'transparent',
            headerColor: darkMode ? '#9ca0b0' : '#4b5563',
            headerSplitColor: 'transparent',
            rowHoverBg: darkMode ? '#252838' : '#f0f1f3',
            borderColor: darkMode ? '#1e2130' : '#f0f0f0',
          },
          Tag: {
            borderRadiusSM: 4,
            defaultBg: darkMode ? '#1e2130' : '#f4f5f7',
          },
          Menu: {
            itemHeight: 38,
            itemMarginInline: 4,
            itemBorderRadius: 6,
            itemSelectedBg: darkMode ? '#1a2744' : '#eff6ff',
            itemSelectedColor: darkMode ? '#60a5fa' : '#2563eb',
            itemHoverBg: darkMode ? '#252838' : '#f0f1f3',
            itemHoverColor: darkMode ? '#e2e4e9' : '#111827',
            iconSize: 16,
            groupTitleFontSize: 11,
          },
          Modal: {
            borderRadiusLG: 8,
          },
          Tabs: {
            horizontalItemPadding: '8px 0',
            horizontalMargin: '0 0 0 0',
            itemColor: darkMode ? '#9ca0b0' : '#4b5563',
            itemSelectedColor: '#2563eb',
            inkBarColor: '#2563eb',
          },
          Form: {
            itemMarginBottom: 16,
            labelColor: darkMode ? '#9ca0b0' : '#4b5563',
            labelFontSize: 13,
          },
          Divider: {
            colorSplit: darkMode ? '#1e2130' : '#f0f0f0',
            marginLG: 16,
          },
          Alert: {
            borderRadiusLG: 6,
          },
          Progress: {
            defaultColor: '#3b82f6',
            remainingColor: darkMode ? '#1e2130' : '#f4f5f7',
          },
          Skeleton: {
            gradientFromColor: darkMode ? '#2a2d3e' : '#e5e7eb',
            gradientToColor: darkMode ? '#1e2130' : '#f4f5f7',
          },
          Empty: {
            colorTextDescription: darkMode ? '#6b6f82' : '#9ca3af',
          },
        },
      }}
    >
      <AntApp>
        <ErrorBoundary>
          <BrowserRouter>
            <LayoutSwitch />
          </BrowserRouter>
        </ErrorBoundary>
      </AntApp>
    </ConfigProvider>
  );
};

export default App;
