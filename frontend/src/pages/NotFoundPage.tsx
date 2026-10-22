import React from 'react';
import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';

/**
 * 404 兜底页面
 * 当用户访问不存在的路由时展示，提供返回首页入口
 */
const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Result
      status="404"
      title="404"
      subTitle="抱歉，您访问的页面不存在。"
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          返回首页
        </Button>
      }
    />
  );
};

export default NotFoundPage;
