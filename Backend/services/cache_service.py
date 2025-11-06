# 缓存服务层，处理Redis缓存相关的业务逻辑
import json
from typing import List, Dict, Optional
from config.database import cache_client
from config.settings import db_config


class CacheService:
    """缓存服务类"""
    
    def __init__(self):
        """初始化缓存服务"""
        self.redis_client = cache_client.client
        self.content_ttl = db_config.redis_content_ttl
    
    def get_todo_contents_cache(self, todo_id: str, user_id: str) -> Optional[List[Dict]]:
        """
        从Redis获取Todo内容缓存
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            
        Returns:
            Optional[List[Dict]]: 缓存的内容列表，如果不存在返回None
        """
        cache_key = f"content:{user_id}:{todo_id}"
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"获取缓存失败: {e}")
            return None
    
    def set_todo_contents_cache(self, todo_id: str, user_id: str, contents: List[Dict]) -> bool:
        """
        设置Todo内容到Redis缓存
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            contents: 内容列表
            
        Returns:
            bool: 是否设置成功
        """
        cache_key = f"content:{user_id}:{todo_id}"
        try:
            # 序列化数据
            cache_data = json.dumps(contents, ensure_ascii=False)
            # 设置缓存，带过期时间
            self.redis_client.setex(cache_key, self.content_ttl, cache_data)
            return True
        except Exception as e:
            print(f"设置缓存失败: {e}")
            return False
    
    def delete_todo_contents_cache(self, todo_id: str, user_id: str) -> bool:
        """
        删除Todo内容缓存
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        cache_key = f"content:{user_id}:{todo_id}"
        try:
            result = self.redis_client.delete(cache_key)
            return result > 0
        except Exception as e:
            print(f"删除缓存失败: {e}")
            return False
    
    def invalidate_todo_cache(self, todo_id: str, user_id: str) -> bool:
        """
        使Todo缓存失效（用于内容更新、删除、添加时）
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        return self.delete_todo_contents_cache(todo_id, user_id)

