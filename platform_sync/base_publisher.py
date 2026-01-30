"""
平台发布器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BasePublisher(ABC):
    """发布器基类"""
    
    def __init__(self, platform: str, account_config: Dict[str, Any]):
        self.platform = platform
        self.account_config = account_config
    
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
    def validate_account(self) -> bool:
        """验证账号是否有效"""
        pass
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """上传图片，返回图片URL（可选实现）"""
        return None
    
    def refresh_token_if_needed(self) -> bool:
        """刷新token（如果需要，可选实现）"""
        return True
