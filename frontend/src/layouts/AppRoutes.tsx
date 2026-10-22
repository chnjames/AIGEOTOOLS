import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Spin } from 'antd';
import { ErrorBoundary } from '@/components';

const Dashboard = lazy(() => import('@/pages/Dashboard'));
const MonitorPage = lazy(() => import('@/pages/MonitorPage'));
const KeywordsPage = lazy(() => import('@/pages/KeywordsPage'));
const ArticlesPage = lazy(() => import('@/pages/ArticlesPage'));
const OptimizePage = lazy(() => import('@/pages/OptimizePage'));
const DDSScorePage = lazy(() => import('@/pages/DDSScorePage'));
const VerifyPage = lazy(() => import('@/pages/VerifyPage'));
const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage'));
const SchemaToolsPage = lazy(() => import('@/pages/SchemaToolsPage'));
const HistoryPage = lazy(() => import('@/pages/HistoryPage'));
const ReportsPage = lazy(() => import('@/pages/ReportsPage'));
const MarketingReportsPage = lazy(() => import('@/pages/MarketingReportsPage'));
const WorkflowsPage = lazy(() => import('@/pages/WorkflowsPage'));
const ResourcesPage = lazy(() => import('@/pages/ResourcesPage'));
const PlatformsPage = lazy(() => import('@/pages/PlatformsPage'));
const ConfigOptimizerPage = lazy(() => import('@/pages/ConfigOptimizerPage'));
const KnowledgePage = lazy(() => import('@/pages/KnowledgePage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));

const PageLoader: React.FC = () => (
  <div className="flex items-center justify-center p-20">
    <Spin size="large" tip="加载中..." />
  </div>
);

const AppRoutes: React.FC = () => (
  <Suspense fallback={<PageLoader />}>
    <Routes>
      <Route path="/" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
      <Route path="/monitor" element={<ErrorBoundary><MonitorPage /></ErrorBoundary>} />
      <Route path="/keywords" element={<ErrorBoundary><KeywordsPage /></ErrorBoundary>} />
      <Route path="/articles" element={<ErrorBoundary><ArticlesPage /></ErrorBoundary>} />
      <Route path="/optimize" element={<ErrorBoundary><OptimizePage /></ErrorBoundary>} />
      <Route path="/dds" element={<ErrorBoundary><DDSScorePage /></ErrorBoundary>} />
      <Route path="/verify" element={<ErrorBoundary><VerifyPage /></ErrorBoundary>} />
      <Route path="/analytics" element={<ErrorBoundary><AnalyticsPage /></ErrorBoundary>} />
      <Route path="/schema" element={<ErrorBoundary><SchemaToolsPage /></ErrorBoundary>} />
      <Route path="/history" element={<ErrorBoundary><HistoryPage /></ErrorBoundary>} />
      <Route path="/reports" element={<ErrorBoundary><ReportsPage /></ErrorBoundary>} />
      <Route path="/marketing-reports" element={<ErrorBoundary><MarketingReportsPage /></ErrorBoundary>} />
      <Route path="/marketing-reports/share/:token" element={<ErrorBoundary><MarketingReportsPage shareMode /></ErrorBoundary>} />
      <Route path="/workflows" element={<ErrorBoundary><WorkflowsPage /></ErrorBoundary>} />
      <Route path="/resources" element={<ErrorBoundary><ResourcesPage /></ErrorBoundary>} />
      <Route path="/platforms" element={<ErrorBoundary><PlatformsPage /></ErrorBoundary>} />
      <Route path="/config-optimizer" element={<ErrorBoundary><ConfigOptimizerPage /></ErrorBoundary>} />
      <Route path="/knowledge" element={<ErrorBoundary><KnowledgePage /></ErrorBoundary>} />
      <Route path="/settings" element={<ErrorBoundary><SettingsPage /></ErrorBoundary>} />
      {/* 404 兜底路由：所有未匹配的路径都渲染 NotFound */}
      <Route path="*" element={<ErrorBoundary><NotFoundPage /></ErrorBoundary>} />
    </Routes>
  </Suspense>
);

export default AppRoutes;
