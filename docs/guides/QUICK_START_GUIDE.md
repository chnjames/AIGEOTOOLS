# 快速开始指南：实现GitHub发布功能

> 这是最简单的实现示例，可以作为其他平台的基础模板

## 🎯 目标

实现GitHub平台的文章自动发布功能，验证整体架构可行性。

## 📦 步骤1：安装依赖

```bash
pip install httpx pyperclip
```

## 📝 步骤2：扩展数据库

在 `modules/data_storage.py` 的 `_init_sqlite` 方法中添加：

```python
# 平台账号表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS platform_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        account_type TEXT NOT NULL,
        account_name TEXT,
        api_key TEXT,
        config_json TEXT,
        is_active INTEGER DEFAULT 1,
        brand TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 发布记录表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS publish_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        platform TEXT NOT NULL,
        publish_method TEXT NOT NULL,
        publish_status TEXT NOT NULL,
        publish_url TEXT,
        publish_id TEXT,
        error_message TEXT,
        published_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

## 💻 步骤3：创建GitHub发布器

创建文件 `platform_sync/github_publisher.py`：

```python
"""
GitHub发布器 - 最简单的实现示例
"""
import base64
import httpx
from typing import Dict, Any, Optional


class GitHubPublisher:
    """GitHub发布器"""
    
    def __init__(self, api_key: str, repo_owner: str, repo_name: str):
        self.api_key = api_key
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {api_key}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def publish(self, content: str, title: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        发布内容到GitHub
        
        Args:
            content: Markdown内容
            title: 文章标题
            file_path: 文件路径（可选）
        
        Returns:
            {
                'success': bool,
                'publish_url': str,
                'publish_id': str,
                'error': str
            }
        """
        try:
            # 生成文件路径
            if not file_path:
                safe_title = title.replace(' ', '_').replace('/', '_')
                file_path = f"content/{safe_title}.md"
            
            # 编码内容
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')
            
            # API URL
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
            
            # 检查文件是否存在
            response = httpx.get(url, headers=self.headers)
            sha = None
            if response.status_code == 200:
                sha = response.json().get('sha')
            
            # 准备数据
            data = {
                "message": f"Publish: {title}",
                "content": content_base64,
                "branch": "main"
            }
            if sha:
                data["sha"] = sha
            
            # 创建或更新文件
            response = httpx.put(url, json=data, headers=self.headers)
            
            if response.status_code in [200, 201]:
                result = response.json()
                html_url = result.get('content', {}).get('html_url', '')
                return {
                    'success': True,
                    'publish_url': html_url,
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
    
    def validate_account(self) -> bool:
        """验证GitHub账号"""
        try:
            response = httpx.get(f"{self.base_url}/user", headers=self.headers)
            return response.status_code == 200
        except:
            return False
```

## 🔧 步骤4：扩展DataStorage

在 `modules/data_storage.py` 的 `DataStorage` 类中添加：

```python
def save_platform_account(self, platform: str, account_config: Dict[str, Any], brand: str):
    """保存平台账号"""
    if self.storage_type == "sqlite":
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO platform_accounts 
            (platform, account_type, account_name, api_key, config_json, brand, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            platform,
            account_config.get('account_type', 'api'),
            account_config.get('account_name', ''),
            account_config.get('api_key', ''),
            json.dumps(account_config.get('config', {}), ensure_ascii=False),
            brand,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

def get_platform_account(self, platform: str, brand: str) -> Optional[Dict[str, Any]]:
    """获取平台账号"""
    if self.storage_type == "sqlite":
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM platform_accounts 
            WHERE platform = ? AND brand = ? AND is_active = 1
        """, (platform, brand))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'api_key': row[4],
                'config': json.loads(row[5] or '{}')
            }
    return None

def save_publish_record(self, article_id: int, platform: str, publish_method: str,
                       publish_status: str, publish_url: str = '', publish_id: str = '',
                       error_message: str = ''):
    """保存发布记录"""
    if self.storage_type == "sqlite":
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO publish_records 
            (article_id, platform, publish_method, publish_status, publish_url, 
             publish_id, error_message, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article_id, platform, publish_method, publish_status,
            publish_url, publish_id, error_message, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
```

## 🎨 步骤5：添加UI（在geo_tool.py中）

在 `modules/geo_tool.py` 中添加新的Tab或功能：

```python
# 在Tab定义中添加
tabs = st.tabs([
    "1 关键词蒸馏",
    "2 内容生成",
    "3 内容优化",
    "4 AI验证",
    "5 历史记录",
    "6 平台同步"  # 新增
])

with tabs[5]:  # 平台同步Tab
    st.header("📤 平台文章同步")
    
    # GitHub账号配置
    with st.expander("🔐 GitHub账号配置", expanded=True):
        github_api_key = st.text_input("GitHub Personal Access Token", type="password")
        github_repo_owner = st.text_input("仓库所有者（用户名）")
        github_repo_name = st.text_input("仓库名称")
        
        if st.button("保存GitHub配置"):
            if github_api_key and github_repo_owner and github_repo_name:
                storage.save_platform_account(
                    platform="GitHub",
                    account_config={
                        'account_type': 'api',
                        'api_key': github_api_key,
                        'config': {
                            'repo_owner': github_repo_owner,
                            'repo_name': github_repo_name
                        }
                    },
                    brand=brand
                )
                st.success("GitHub配置已保存！")
            else:
                st.error("请填写完整信息")
    
    # 发布功能
    st.subheader("📝 发布到GitHub")
    
    # 选择文章
    articles = storage.get_articles(brand=brand)
    if articles:
        article_options = {f"{a['keyword']} - {a['platform']}": a['id'] for a in articles}
        selected_article_key = st.selectbox("选择要发布的文章", list(article_options.keys()))
        selected_article_id = article_options[selected_article_key]
        
        if st.button("🚀 发布到GitHub", type="primary"):
            # 获取账号配置
            account_config = storage.get_platform_account("GitHub", brand)
            if not account_config:
                st.error("请先配置GitHub账号")
            else:
                # 获取文章
                article = next((a for a in articles if a['id'] == selected_article_id), None)
                if article:
                    # 创建发布器
                    from platform_sync.github_publisher import GitHubPublisher
                    publisher = GitHubPublisher(
                        api_key=account_config['api_key'],
                        repo_owner=account_config['config']['repo_owner'],
                        repo_name=account_config['config']['repo_name']
                    )
                    
                    # 发布
                    with st.spinner("正在发布到GitHub..."):
                        result = publisher.publish(
                            content=article['content'],
                            title=article['keyword']
                        )
                    
                    # 保存发布记录
                    storage.save_publish_record(
                        article_id=selected_article_id,
                        platform="GitHub",
                        publish_method="api",
                        publish_status="success" if result['success'] else "failed",
                        publish_url=result.get('publish_url', ''),
                        publish_id=result.get('publish_id', ''),
                        error_message=result.get('error', '')
                    )
                    
                    # 显示结果
                    if result['success']:
                        st.success(f"✅ 发布成功！")
                        st.markdown(f"**发布链接**: {result['publish_url']}")
                    else:
                        st.error(f"❌ 发布失败: {result.get('error', '未知错误')}")
    else:
        st.info("请先生成文章")
    
    # 发布记录
    st.subheader("📊 发布记录")
    # 这里可以显示发布历史记录
```

## ✅ 步骤6：测试

1. **获取GitHub Token**：
   - 访问 https://github.com/settings/tokens
   - 创建新的 Personal Access Token
   - 选择 `repo` 权限

2. **运行测试**：
   ```bash
   streamlit run geo_tool.py
   ```

3. **测试流程**：
   - 配置GitHub账号
   - 生成一篇文章
   - 发布到GitHub
   - 检查GitHub仓库是否成功创建文件

## 🎉 完成！

如果GitHub发布功能正常工作，说明架构是正确的。接下来可以：

1. 按照相同模式实现其他7个API平台
2. 实现一键复制功能
3. 添加批量发布功能

## 📚 参考

- [GitHub API文档](https://docs.github.com/en/rest)
- [完整实现指南](./PLATFORM_SYNC_IMPLEMENTATION.md)
