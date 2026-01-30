# 平台文章同步功能实现指南

> 实现20个平台的文章同步功能：8个API平台 + 12个一键复制平台

## 📋 目录

1. [技术架构设计](#技术架构设计)
2. [数据库设计](#数据库设计)
3. [模块划分](#模块划分)
4. [核心代码实现](#核心代码实现)
5. [实施步骤](#实施步骤)
6. [测试方案](#测试方案)

---

## 🏗️ 技术架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                    │
│  (平台配置、发布管理、状态展示、一键复制)                  │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                  Platform Sync Manager                  │
│  (统一发布接口、任务队列、状态管理)                        │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────────────────┐              ┌──────────────────────┐
│  API Publishers   │              │  Copy-to-Clipboard   │
│  (8个平台)        │              │  (12个平台)          │
│                   │              │                      │
│ - GitHub          │              │ - 头条号             │
│ - 微信公众号       │              │ - 小红书             │
│ - B站             │              │ - 抖音               │
│ - 知乎            │              │ - 简书               │
│ - CSDN            │              │ - QQ空间             │
│ - 百家号          │              │ - 新浪博客/新闻       │
│ - 企鹅号          │              │ - 搜狐号             │
│ - 网易号          │              │ - 一点号             │
│                   │              │ - 东方财富           │
│                   │              │ - 邦阅网             │
│                   │              │ - 原创力文档         │
└───────────────────┘              └──────────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│              Data Storage Layer (SQLite)                │
│  (平台账号、发布记录、文章状态)                           │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

- **后端框架**：Streamlit（已有）
- **数据库**：SQLite（已有）
- **HTTP客户端**：`httpx` 或 `requests`
- **OAuth2.0**：`requests-oauthlib`
- **任务队列**：`asyncio`（异步发布）
- **内容转换**：`markdown`、`html2text`、`Pillow`（图片处理）

---

## 💾 数据库设计

### 新增表结构

#### 1. platform_accounts（平台账号表）

```sql
CREATE TABLE IF NOT EXISTS platform_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,              -- 平台名称
    account_type TEXT NOT NULL,          -- 'api' 或 'manual'
    account_name TEXT,                   -- 账号名称/标识
    access_token TEXT,                   -- OAuth token（加密存储）
    refresh_token TEXT,                  -- 刷新token（加密存储）
    token_expires_at TIMESTAMP,          -- token过期时间
    api_key TEXT,                        -- API Key（如GitHub）
    api_secret TEXT,                     -- API Secret
    config_json TEXT,                    -- 平台特定配置（JSON）
    is_active INTEGER DEFAULT 1,         -- 是否激活
    brand TEXT,                          -- 关联品牌
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, brand, account_name)
);
```

#### 2. publish_records（发布记录表）

```sql
CREATE TABLE IF NOT EXISTS publish_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER,                  -- 关联articles表
    platform TEXT NOT NULL,
    publish_method TEXT NOT NULL,        -- 'api' 或 'copy'
    publish_status TEXT NOT NULL,        -- 'pending', 'success', 'failed', 'copied'
    publish_url TEXT,                    -- 发布后的URL（API发布）
    publish_id TEXT,                     -- 平台返回的发布ID
    error_message TEXT,                   -- 错误信息
    retry_count INTEGER DEFAULT 0,       -- 重试次数
    published_at TIMESTAMP,              -- 发布时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

#### 3. platform_configs（平台配置表）

```sql
CREATE TABLE IF NOT EXISTS platform_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL UNIQUE,
    has_api INTEGER DEFAULT 0,          -- 是否有API
    api_docs_url TEXT,                   -- API文档链接
    content_format TEXT,                  -- 内容格式要求
    max_length INTEGER,                   -- 最大字数
    min_length INTEGER,                  -- 最小字数
    supports_images INTEGER DEFAULT 0,   -- 是否支持图片
    supports_tags INTEGER DEFAULT 0,     -- 是否支持标签
    publish_guide TEXT,                  -- 发布指南（一键复制平台）
    format_template TEXT,                 -- 格式模板（一键复制平台）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. publish_queue（发布队列表）

```sql
CREATE TABLE IF NOT EXISTS publish_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    priority INTEGER DEFAULT 0,          -- 优先级
    scheduled_at TIMESTAMP,              -- 计划发布时间
    status TEXT DEFAULT 'pending',       -- 'pending', 'processing', 'completed', 'failed'
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

### 扩展articles表

```sql
ALTER TABLE articles ADD COLUMN publish_status TEXT DEFAULT 'draft';
ALTER TABLE articles ADD COLUMN publish_urls TEXT;  -- JSON格式存储各平台发布URL
```

---

## 📦 模块划分

### 目录结构

```
geo_tool/
├── platform_sync/                    # 新增：平台同步模块
│   ├── __init__.py
│   ├── base_publisher.py             # 发布器基类
│   ├── api_publishers/               # API发布器
│   │   ├── __init__.py
│   │   ├── github_publisher.py
│   │   ├── wechat_publisher.py
│   │   ├── bilibili_publisher.py
│   │   ├── zhihu_publisher.py
│   │   ├── csdn_publisher.py
│   │   ├── baijiahao_publisher.py
│   │   ├── qq_publisher.py
│   │   └── netease_publisher.py
│   ├── copy_publishers/              # 一键复制发布器
│   │   ├── __init__.py
│   │   ├── copy_manager.py
│   │   └── format_templates.py
│   ├── content_converter.py          # 内容格式转换
│   ├── sync_manager.py               # 同步管理器
│   └── account_manager.py            # 账号管理
├── platform_templates/               # 新增：平台模板
│   ├── __init__.py
│   ├── new_platforms/               # 新增8个平台的Prompt模板
│   │   ├── sina_blog.py
│   │   ├── sina_news.py
│   │   ├── sohu.py
│   │   ├── qzone.py
│   │   ├── bangyue.py
│   │   ├── yidian.py
│   │   ├── eastmoney.py
│   │   └── yuanchuangli.py
│   └── existing_platforms/           # 原有平台模板（已有）
├── modules/data_storage.py                   # 扩展：添加发布相关方法
└── geo_tool.py                       # 扩展：添加发布UI
```

---

## 💻 核心代码实现

### 1. 发布器基类 (modules/base_publisher.py)

```python
"""
平台发布器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime


class BasePublisher(ABC):
    """发布器基类"""
    
    def __init__(self, platform: str, account_config: Dict[str, Any]):
        self.platform = platform
        self.account_config = account_config
        self.access_token = account_config.get('access_token')
        self.refresh_token = account_config.get('refresh_token')
    
    @abstractmethod
    def publish(self, content: str, title: str, **kwargs) -> Dict[str, Any]:
        """
        发布内容
        
        Args:
            content: 文章内容
            title: 文章标题
            **kwargs: 其他参数（标签、图片等）
        
        Returns:
            {
                'success': bool,
                'publish_url': str,
                'publish_id': str,
                'error': str
            }
        """
        pass
    
    @abstractmethod
    def upload_image(self, image_path: str) -> Optional[str]:
        """上传图片，返回图片URL"""
        pass
    
    def refresh_token_if_needed(self) -> bool:
        """刷新token（如果需要）"""
        # 子类实现
        return True
    
    def validate_account(self) -> bool:
        """验证账号是否有效"""
        # 子类实现
        return True
```

### 2. GitHub发布器示例 (api_publishers/github_publisher.py)

```python
"""
GitHub发布器
"""
import base64
import requests
from typing import Dict, Any, Optional
from .base_publisher import BasePublisher


class GitHubPublisher(BasePublisher):
    """GitHub发布器"""
    
    def __init__(self, account_config: Dict[str, Any]):
        super().__init__("GitHub", account_config)
        self.api_key = account_config.get('api_key')
        self.repo_owner = account_config.get('repo_owner')
        self.repo_name = account_config.get('repo_name')
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.api_key}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def publish(self, content: str, title: str, **kwargs) -> Dict[str, Any]:
        """发布到GitHub"""
        try:
            # 生成文件路径
            file_path = kwargs.get('file_path', f"content/{title.replace(' ', '_')}.md")
            
            # 编码内容
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')
            
            # 创建或更新文件
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
            
            # 检查文件是否存在
            response = requests.get(url, headers=self.headers)
            sha = None
            if response.status_code == 200:
                sha = response.json().get('sha')
            
            data = {
                "message": f"Publish: {title}",
                "content": content_base64,
                "branch": kwargs.get('branch', 'main')
            }
            if sha:
                data["sha"] = sha
            
            response = requests.put(url, json=data, headers=self.headers)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    'success': True,
                    'publish_url': result.get('content', {}).get('html_url', ''),
                    'publish_id': result.get('content', {}).get('sha', ''),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'publish_url': '',
                    'publish_id': '',
                    'error': f"GitHub API错误: {response.text}"
                }
        except Exception as e:
            return {
                'success': False,
                'publish_url': '',
                'publish_id': '',
                'error': str(e)
            }
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """GitHub不支持直接上传图片，需要先上传到仓库"""
        # 实现图片上传逻辑
        return None
    
    def validate_account(self) -> bool:
        """验证GitHub账号"""
        try:
            response = requests.get(f"{self.base_url}/user", headers=self.headers)
            return response.status_code == 200
        except:
            return False
```

### 3. 一键复制管理器 (copy_publishers/copy_manager.py)

```python
"""
一键复制管理器
"""
import pyperclip
from typing import Dict, Any
from .format_templates import FormatTemplates


class CopyManager:
    """一键复制管理器"""
    
    def __init__(self):
        self.templates = FormatTemplates()
    
    def format_for_platform(self, platform: str, content: str, title: str, **kwargs) -> str:
        """
        为平台格式化内容
        
        Args:
            platform: 平台名称
            content: 原始内容
            title: 标题
            **kwargs: 其他参数（标签、摘要等）
        
        Returns:
            格式化后的内容
        """
        template = self.templates.get_template(platform)
        if not template:
            # 默认格式
            return f"{title}\n\n{content}"
        
        return template.format(
            title=title,
            content=content,
            **kwargs
        )
    
    def copy_to_clipboard(self, text: str) -> bool:
        """复制到剪贴板"""
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"复制失败: {e}")
            return False
    
    def generate_publish_guide(self, platform: str) -> str:
        """生成发布指南"""
        guides = {
            "头条号": """
发布步骤：
1. 登录头条号后台
2. 点击"发布" -> "文章"
3. 粘贴标题和内容
4. 添加封面图和标签
5. 点击发布
            """,
            "小红书": """
发布步骤：
1. 打开小红书APP
2. 点击"+"号发布
3. 选择"图文"
4. 粘贴标题和内容
5. 添加图片和标签
6. 发布
            """,
            # ... 其他平台指南
        }
        return guides.get(platform, "请参考平台官方发布指南")
```

### 4. 同步管理器 (modules/sync_manager.py)

```python
"""
平台同步管理器
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from data_storage import DataStorage
from platform_sync.api_publishers import get_api_publisher
from platform_sync.copy_publishers import CopyManager


class SyncManager:
    """平台同步管理器"""
    
    def __init__(self, storage: DataStorage):
        self.storage = storage
        self.copy_manager = CopyManager()
    
    async def publish_article(
        self,
        article_id: int,
        platform: str,
        account_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发布文章到指定平台
        
        Args:
            article_id: 文章ID
            platform: 平台名称
            account_config: 账号配置
        
        Returns:
            发布结果
        """
        # 获取文章
        article = self.storage.get_article_by_id(article_id)
        if not article:
            return {'success': False, 'error': '文章不存在'}
        
        # 获取平台配置
        platform_config = self.storage.get_platform_config(platform)
        if not platform_config:
            return {'success': False, 'error': '平台配置不存在'}
        
        # 判断发布方式
        if platform_config.get('has_api'):
            # API发布
            if not account_config:
                account_config = self.storage.get_platform_account(platform)
            
            if not account_config:
                return {'success': False, 'error': '账号未配置'}
            
            publisher = get_api_publisher(platform, account_config)
            result = await self._publish_via_api(publisher, article, platform_config)
        else:
            # 一键复制
            result = await self._publish_via_copy(article, platform, platform_config)
        
        # 保存发布记录
        self.storage.save_publish_record(
            article_id=article_id,
            platform=platform,
            publish_method='api' if platform_config.get('has_api') else 'copy',
            publish_status='success' if result['success'] else 'failed',
            publish_url=result.get('publish_url', ''),
            publish_id=result.get('publish_id', ''),
            error_message=result.get('error')
        )
        
        return result
    
    async def _publish_via_api(
        self,
        publisher,
        article: Dict[str, Any],
        platform_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """通过API发布"""
        try:
            # 内容格式转换
            content = self._convert_content(article['content'], platform_config)
            
            # 发布
            result = publisher.publish(
                content=content,
                title=article.get('title', article['keyword']),
                keyword=article['keyword'],
                brand=article.get('brand', '')
            )
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _publish_via_copy(
        self,
        article: Dict[str, Any],
        platform: str,
        platform_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """通过一键复制发布"""
        try:
            # 格式化内容
            formatted_content = self.copy_manager.format_for_platform(
                platform=platform,
                content=article['content'],
                title=article.get('title', article['keyword']),
                keyword=article['keyword'],
                brand=article.get('brand', '')
            )
            
            # 复制到剪贴板
            success = self.copy_manager.copy_to_clipboard(formatted_content)
            
            if success:
                return {
                    'success': True,
                    'publish_url': '',
                    'publish_id': '',
                    'copied_content': formatted_content,
                    'guide': self.copy_manager.generate_publish_guide(platform)
                }
            else:
                return {'success': False, 'error': '复制到剪贴板失败'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _convert_content(self, content: str, platform_config: Dict[str, Any]) -> str:
        """内容格式转换"""
        # 根据平台要求转换格式
        # Markdown -> HTML / 纯文本等
        return content
    
    async def batch_publish(
        self,
        article_ids: List[int],
        platforms: List[str],
        delay_seconds: int = 5
    ) -> List[Dict[str, Any]]:
        """批量发布"""
        results = []
        for article_id in article_ids:
            for platform in platforms:
                result = await self.publish_article(article_id, platform)
                results.append({
                    'article_id': article_id,
                    'platform': platform,
                    'result': result
                })
                # 延迟，避免频率限制
                await asyncio.sleep(delay_seconds)
        return results
```

### 5. 扩展DataStorage (modules/data_storage.py扩展)

```python
# 在DataStorage类中添加以下方法

def save_platform_account(self, platform: str, account_config: Dict[str, Any], brand: str):
    """保存平台账号"""
    # 实现保存逻辑

def get_platform_account(self, platform: str, brand: str) -> Optional[Dict[str, Any]]:
    """获取平台账号"""
    # 实现获取逻辑

def save_publish_record(self, article_id: int, platform: str, publish_method: str,
                       publish_status: str, publish_url: str = '', publish_id: str = '',
                       error_message: str = ''):
    """保存发布记录"""
    # 实现保存逻辑

def get_publish_records(self, article_id: Optional[int] = None,
                       platform: Optional[str] = None) -> List[Dict]:
    """获取发布记录"""
    # 实现获取逻辑

def save_platform_config(self, platform: str, config: Dict[str, Any]):
    """保存平台配置"""
    # 实现保存逻辑

def get_platform_config(self, platform: str) -> Optional[Dict[str, Any]]:
    """获取平台配置"""
    # 实现获取逻辑
```

### 6. UI集成 (geo_tool.py扩展)

```python
# 在geo_tool.py中添加新的Tab

def show_platform_sync_tab():
    """平台同步Tab"""
    st.header("📤 平台文章同步")
    
    # 1. 平台账号配置
    with st.expander("🔐 平台账号配置", expanded=False):
        platform = st.selectbox("选择平台", ALL_PLATFORMS)
        account_type = "API" if platform in API_PLATFORMS else "手动"
        st.info(f"发布方式: {account_type}")
        
        if account_type == "API":
            # API账号配置
            api_key = st.text_input("API Key", type="password")
            api_secret = st.text_input("API Secret", type="password")
            # ... 其他配置
            
            if st.button("保存账号配置"):
                # 保存配置
                pass
        else:
            st.info("该平台使用一键复制功能，无需配置账号")
    
    # 2. 发布管理
    st.subheader("📝 发布管理")
    
    # 选择文章
    articles = storage.get_articles(brand=brand)
    selected_articles = st.multiselect("选择要发布的文章", articles, format_func=lambda x: x['keyword'])
    
    # 选择平台
    selected_platforms = st.multiselect("选择发布平台", ALL_PLATFORMS)
    
    # 发布选项
    col1, col2 = st.columns(2)
    with col1:
        publish_mode = st.radio("发布模式", ["立即发布", "定时发布"])
    with col2:
        delay_seconds = st.number_input("发布间隔（秒）", min_value=0, value=5)
    
    # 发布按钮
    if st.button("🚀 开始发布", type="primary"):
        sync_manager = SyncManager(storage)
        
        with st.spinner("正在发布..."):
            results = asyncio.run(sync_manager.batch_publish(
                article_ids=[a['id'] for a in selected_articles],
                platforms=selected_platforms,
                delay_seconds=delay_seconds
            ))
        
        # 显示结果
        for result in results:
            if result['result']['success']:
                st.success(f"✅ {result['platform']}: 发布成功")
            else:
                st.error(f"❌ {result['platform']}: {result['result']['error']}")
    
    # 3. 发布记录
    st.subheader("📊 发布记录")
    records = storage.get_publish_records()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df)
    else:
        st.info("暂无发布记录")
```

---

## 🚀 实施步骤

### 阶段一：基础架构（第1-2周）

1. **数据库扩展**
   ```bash
   # 运行数据库迁移脚本
   python scripts/migrate_database.py
   ```

2. **创建模块结构**
   ```bash
   mkdir -p platform_sync/api_publishers
   mkdir -p platform_sync/copy_publishers
   mkdir -p platform_templates/new_platforms
   ```

3. **实现基础类**
   - `BasePublisher` 基类
   - `SyncManager` 管理器
   - `CopyManager` 复制管理器

### 阶段二：API发布器（第3-6周）

1. **GitHub发布器**（1-2天）
2. **微信公众号发布器**（3-4天）
3. **B站发布器**（3-4天）
4. **知乎发布器**（3-4天）
5. **CSDN发布器**（3-4天）
6. **百家号发布器**（4-5天）
7. **企鹅号发布器**（4-5天）
8. **网易号发布器**（4-5天）

### 阶段三：新增平台内容生成（第4-5周）

为8个新增平台创建Prompt模板：

```python
# platform_templates/new_platforms/sina_blog.py
SINA_BLOG_TEMPLATE = """
你是GEO专家 + 新浪博客作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个吸引人的标题
2) 开头：故事化或热点引入
3) 正文：深度分析、案例丰富、观点鲜明
4) 自然提及品牌2-4次
5) 适合新浪博客：内容深度、可读性强
6) 字数：1500-3000字
7) 结尾：总结+延伸思考
【格式】标题-正文-总结
【开始】
"""
```

### 阶段四：一键复制功能（第7-8周）

1. **格式模板开发**（12个平台）
2. **剪贴板集成**
3. **发布指南生成**

### 阶段五：UI集成（第9周）

1. **平台账号配置界面**
2. **发布管理界面**
3. **发布记录展示**

### 阶段六：测试和优化（第10周）

1. **单元测试**
2. **集成测试**
3. **性能优化**

---

## 🧪 测试方案

### 单元测试

```python
# tests/test_github_publisher.py
import pytest
from platform_sync.api_publishers.github_publisher import GitHubPublisher

def test_github_publish():
    config = {
        'api_key': 'test_key',
        'repo_owner': 'test_owner',
        'repo_name': 'test_repo'
    }
    publisher = GitHubPublisher(config)
    result = publisher.publish("Test content", "Test Title")
    assert result['success'] == True
```

### 集成测试

```python
# tests/test_sync_manager.py
async def test_batch_publish():
    manager = SyncManager(storage)
    results = await manager.batch_publish([1, 2], ['GitHub', '知乎'])
    assert len(results) == 4
```

---

## 📝 依赖安装

```bash
pip install httpx requests-oauthlib pyperclip markdown html2text Pillow
```

更新 `requirements.txt`：

```
httpx>=0.24.0
requests-oauthlib>=1.3.1
pyperclip>=1.8.2
markdown>=3.4.0
html2text>=2020.1.16
Pillow>=10.0.0
```

---

## ⚠️ 注意事项

1. **Token安全**：所有token需要加密存储
2. **频率限制**：遵守各平台的API调用频率限制
3. **错误处理**：完善的错误处理和重试机制
4. **日志记录**：详细的发布日志
5. **用户体验**：清晰的发布状态反馈

---

**实施时间**：10周（2.5个月）  
**开发人员**：1-2人  
**优先级**：高
