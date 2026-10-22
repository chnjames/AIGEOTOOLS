import React, { useMemo, useState } from 'react';
import { Layout, Menu, Button, Switch, Badge, Tooltip, Drawer, Grid, Breadcrumb } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  KeyOutlined,
  EditOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  SwapOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MenuOutlined,
  DatabaseOutlined,
  LineChartOutlined,
  CodeOutlined,
  FileTextOutlined,
  BellOutlined,
  AimOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '@/stores';
import AppRoutes from './AppRoutes';

const { Header, Sider, Content } = Layout;
const { useBreakpoint } = Grid;

type MenuItem = Required<MenuProps>['items'];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar, darkMode, setDarkMode, config, mobileDrawerOpen, setMobileDrawerOpen } = useAppStore();
  const screens = useBreakpoint();

  // 移动端判定：lg 以下（< 992px）视为移动端，使用 Drawer 导航
  const isMobile = !screens.lg;

  // SubMenu 展开状态：根据当前路由自动展开所属分组
  const pathToGroup: Record<string, string> = {
    '/keywords': 'g-core', '/articles': 'g-core',
    '/optimize': 'g-core', '/dds': 'g-core', '/verify': 'g-core',
    '/monitor': 'g-monitor', '/analytics': 'g-monitor',
    '/reports': 'g-monitor', '/marketing-reports': 'g-monitor',
    '/workflows': 'g-tools', '/schema': 'g-tools',
    '/platforms': 'g-tools', '/knowledge': 'g-tools',
    '/resources': 'g-tools',
    '/config-optimizer': 'g-system', '/history': 'g-system',
    '/settings': 'g-system',
  };

  const getDefaultOpenKeys = (pathname: string): string[] => {
    const group = pathToGroup[pathname];
    return group ? [group] : ['g-core'];
  };

  const [openKeys, setOpenKeys] = useState<string[]>(getDefaultOpenKeys(location.pathname));

  // 面包屑路由映射
  const groupLabels: Record<string, string> = {
    'g-core': '核心流程',
    'g-monitor': '分析与监测',
    'g-tools': '工具与资源',
    'g-system': '系统',
  };
  const pathLabels: Record<string, string> = {
    '/': '工作台',
    '/keywords': '关键词蒸馏',
    '/articles': '自动创作',
    '/optimize': '文章优化',
    '/dds': 'DDS评分',
    '/verify': '多模型验证',
    '/monitor': '持续监测',
    '/analytics': 'ROI归因',
    '/reports': '数据报表',
    '/marketing-reports': '营销报告',
    '/workflows': '工作流',
    '/schema': 'Schema工具',
    '/platforms': '平台同步',
    '/knowledge': '知识库',
    '/resources': 'GEO资源库',
    '/config-optimizer': '配置助手',
    '/history': '历史记录',
    '/settings': '系统设置',
  };

  const breadcrumbItems = useMemo(() => {
    const path = location.pathname;
    const currentPageLabel = pathLabels[path];
    if (!currentPageLabel || path === '/') {
      return [{ title: <><HomeOutlined /> 工作台</> }];
    }
    const groupId = pathToGroup[path];
    const groupLabel = groupId ? groupLabels[groupId] : null;
    const items: Array<{ title: React.ReactNode; onClick?: () => void }> = [
      { title: <><HomeOutlined /> 工作台</>, onClick: () => navigate('/') },
    ];
    if (groupLabel) {
      items.push({ title: groupLabel });
    }
    items.push({ title: currentPageLabel });
    return items;
  }, [location.pathname]);

  const menuItems: MenuItem = useMemo(() => [
    // 工作台：独立顶级项，始终可见
    { key: '/', icon: <DashboardOutlined />, label: '工作台' },
    // 核心流程（可折叠 SubMenu）
    {
      key: 'g-core',
      icon: <ThunderboltOutlined />,
      label: '核心流程',
      children: [
        { key: '/keywords', icon: <KeyOutlined />, label: '关键词蒸馏' },
        { key: '/articles', icon: <EditOutlined />, label: '自动创作' },
        { key: '/optimize', icon: <ToolOutlined />, label: '文章优化' },
        { key: '/dds', icon: <AimOutlined />, label: 'DDS评分' },
        { key: '/verify', icon: <CheckCircleOutlined />, label: '多模型验证' },
      ],
    },
    // 分析与监测（可折叠 + 徽标）
    {
      key: 'g-monitor',
      icon: <BarChartOutlined />,
      label: '分析与监测',
      children: [
        { key: '/monitor', icon: <BellOutlined />, label: '持续监测' },
        { key: '/analytics', icon: <LineChartOutlined />, label: 'ROI归因' },
        { key: '/reports', icon: <BarChartOutlined />, label: '数据报表' },
        { key: '/marketing-reports', icon: <FileTextOutlined />, label: '营销报告' },
      ],
    },
    // 工具与资源（合并原"工具"和"系统"中的资源项）
    {
      key: 'g-tools',
      icon: <ToolOutlined />,
      label: '工具与资源',
      children: [
        { key: '/workflows', icon: <ThunderboltOutlined />, label: '工作流' },
        { key: '/schema', icon: <CodeOutlined />, label: 'Schema工具' },
        { key: '/platforms', icon: <SwapOutlined />, label: '平台同步' },
        { key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库' },
        { key: '/resources', icon: <BulbOutlined />, label: 'GEO资源库' },
      ],
    },
    // 系统
    {
      key: 'g-system',
      icon: <SettingOutlined />,
      label: '系统',
      children: [
        { key: '/config-optimizer', icon: <SettingOutlined />, label: '配置助手' },
        { key: '/history', icon: <HistoryOutlined />, label: '历史记录' },
        { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
      ],
    },
  ], []);

  const configOk = config?.gen_api_key_configured && (config?.verify_providers?.length ?? 0) > 0;

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key);
    // 移动端点击菜单项后自动关闭 Drawer
    if (isMobile) {
      setMobileDrawerOpen(false);
    }
  };

  // 抽屉内容：Logo + Menu
  const drawerContent = (
    <>
      <div className="app-sider-logo">
        <div className="logo-icon">G</div>
        <span className="logo-text">GEO 优化平台</span>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        openKeys={sidebarCollapsed ? [] : openKeys}
        onOpenChange={(keys) => setOpenKeys(keys as string[])}
        items={menuItems}
        onClick={handleMenuClick}
        className="app-menu"
        inlineIndent={12}
      />
    </>
  );

  return (
    <Layout className="app-layout">
      {/* 桌面端侧边栏 */}
      {!isMobile && (
        <Sider
          trigger={null}
          collapsible
          collapsed={sidebarCollapsed}
          width={200}
          collapsedWidth={56}
          className="app-sider"
        >
          {drawerContent}
        </Sider>
      )}

      {/* 移动端抽屉导航 */}
      {isMobile && (
        <Drawer
          placement="left"
          open={mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
          width={240}
          className="app-mobile-drawer"
          closable={false}
          styles={{ body: { padding: 0, background: 'var(--sidebar-bg)' } }}
        >
          {drawerContent}
        </Drawer>
      )}

      <Layout className={`app-main${sidebarCollapsed && !isMobile ? ' collapsed' : ''}${isMobile ? ' mobile' : ''}`}>
        <Header className="app-header">
          <div className="app-header-left">
            {isMobile ? (
              <Button
                type="text"
                size="small"
                icon={<MenuOutlined />}
                onClick={() => setMobileDrawerOpen(true)}
                aria-label="打开导航菜单"
              />
            ) : (
              <Button
                type="text"
                size="small"
                icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={toggleSidebar}
              />
            )}
            {!isMobile && (
              <Breadcrumb
                items={breadcrumbItems}
                className="app-breadcrumb"
              />
            )}
            {config ? (
              configOk ? (
                <Badge status="success" text={<span className="text-xs text-text-tertiary">配置就绪</span>} />
              ) : (
                <Badge status="warning" text={<span className="text-xs text-text-tertiary">待配置</span>} />
              )
            ) : null}
          </div>

          <div className="app-header-right">
            <Tooltip title={darkMode ? '切换浅色模式' : '切换深色模式'}>
              <Switch
                size="small"
                checked={darkMode}
                onChange={setDarkMode}
                checkedChildren="深"
                unCheckedChildren="浅"
              />
            </Tooltip>
            <Button type="text" size="small" icon={<SettingOutlined />} onClick={() => navigate('/settings')} />
          </div>
        </Header>

        <Content>
          <div className="app-content">
            <AppRoutes />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
