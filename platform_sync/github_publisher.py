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
                safe_title = title.replace(' ', '_').replace('/', '_').replace('\\', '_')
                safe_title = ''.join(c for c in safe_title if c.isalnum() or c in ('_', '-', '.'))[:50]
                file_path = f"content/{safe_title}.md"
            
            # 编码内容
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')
            
            # API URL
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
            
            # 检查文件是否存在
            response = httpx.get(url, headers=self.headers, timeout=30.0)
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
            response = httpx.put(url, json=data, headers=self.headers, timeout=30.0)
            
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
                error_text = response.text
                try:
                    error_json = response.json()
                    error_text = error_json.get('message', error_text)
                except:
                    pass
                return {
                    'success': False,
                    'publish_url': '',
                    'publish_id': '',
                    'error': f"GitHub API错误: {error_text}"
                }
        except httpx.TimeoutException:
            return {
                'success': False,
                'publish_url': '',
                'publish_id': '',
                'error': '请求超时，请稍后重试'
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
            response = httpx.get(f"{self.base_url}/user", headers=self.headers, timeout=10.0)
            return response.status_code == 200
        except:
            return False
