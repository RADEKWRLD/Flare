# Todo模型层，处理Todo相关的数据操作和业务逻辑
import uuid
from typing import List, Dict, Optional, Tuple
from bson import ObjectId
from .base import BaseModel
from config.database import db_client

class TodoModel(BaseModel):
    """Todo标题模型"""
    
    def __init__(self):
        """初始化Todo模型"""
        super().__init__(db_client.todos)
    
    def create_todo(self, user_id: str, title: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        创建Todo
        
        Args:
            user_id: 用户ID
            title: Todo标题
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 消息, Todo数据)
        """
        if not title or not title.strip():
            return False, "Title is required", None
        
        if len(title.strip()) > 200:
            return False, "标题长度不能超过200个字符", None
        
        try:
            todo_data = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'title': title.strip()
            }
            result = self.create(todo_data)
            return True, "Todo created successfully", result
        except Exception as e:
            return False, f"Failed to create todo: {str(e)}", None
    
    def get_user_todos(self, user_id: str) -> List[Dict]:
        """获取用户的所有Todo，按创建时间倒序"""
        todos = list(self.collection.find({"user_id": user_id}).sort('created_at', -1))
        return self.convert_objectid(todos)
    
    def update_todo(self, todo_id: str, user_id: str, title: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        更新Todo
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            title: 新标题
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 消息, 更新后的Todo数据)
        """
        if not title or not title.strip():
            return False, "Title is required", None
        
        if len(title.strip()) > 200:
            return False, "标题长度不能超过200个字符", None
        
        # 检查Todo是否存在
        existing_todo = self.find_todo(todo_id, user_id)
        if not existing_todo:
            return False, "Todo not found or not authorized", None
        
        try:
            # 更新Todo
            result = self.collection.update_one(
                {'id': todo_id, 'user_id': user_id},
                {'$set': {'title': title.strip()}}
            )
            
            if result.modified_count == 0:
                return False, "Failed to update todo", None
            
            # 返回更新后的Todo
            updated_todo = self.find_todo(todo_id, user_id)
            return True, "Todo updated successfully", updated_todo
        except Exception as e:
            return False, f"Failed to update todo: {str(e)}", None
    
    def delete_todo(self, todo_id: str, user_id: str) -> Tuple[bool, str]:
        """
        删除Todo及其所有相关内容
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        # 检查Todo是否存在
        existing_todo = self.find_todo(todo_id, user_id)
        if not existing_todo:
            return False, "Todo not found or not authorized"
        
        try:
            # 删除Todo内容 (需要TodoContentModel实例)
            content_model = TodoContentModel()
            content_model.delete_contents_by_todo(todo_id, user_id)
            
            # 删除Todo
            result = self.collection.delete_one({'id': todo_id, 'user_id': user_id})
            if result.deleted_count > 0:
                return True, "Todo deleted successfully"
            else:
                return False, "Failed to delete todo"
                
        except Exception as e:
            return False, f"Failed to delete todo: {str(e)}"
    
    def find_todo(self, todo_id: str, user_id: str) -> Optional[Dict]:
        """查找特定的Todo"""
        todo = self.collection.find_one({'id': todo_id, 'user_id': user_id})
        return self.convert_objectid(todo) if todo else None


class TodoContentModel(BaseModel):
    """Todo内容模型"""
    
    def __init__(self):
        """初始化Todo内容模型"""
        super().__init__(db_client.todosContent)
    
    def create_content(self, todo_id: str, user_id: str, content: str, 
                      images: List[str] = None, files: List[str] = None,
                      ocr_texts: List[str] = None, file_texts: List[str] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        创建Todo内容
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            content: 用户输入的内容文本
            images: 图片列表
            files: 文件列表
            ocr_texts: OCR提取的文本列表（新增）
            file_texts: 从文档提取的文本列表（新增）
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 消息, 内容数据)
        """
        # 检查Todo是否存在
        todo_model = TodoModel()
        existing_todo = todo_model.find_todo(todo_id, user_id)
        if not existing_todo:
            return False, "Todo not found or not authorized", None
        
        # 验证输入
        if not content and not images and not files:
            return False, "至少需要文字或文件", None
        
        try:
            # 🔥 构建提取内容结构
            extracted_content = None
            ocr_list = ocr_texts or []
            file_list = file_texts or []
            
            if len(ocr_list) > 0 or len(file_list) > 0:
                # 合并所有提取的文本
                extracted_content = {
                    "ocr_texts": ocr_list,
                    "file_texts": file_list,
                }
            
            # 🔥 新的数据结构
            content_data = {
                "todo_id": todo_id,
                "user_id": user_id,
                "content": content or "",  # 只存用户输入
                "extracted_content": extracted_content,  # 自动提取的内容
                "images": images or [],
                "files": files or [],
                "complete": False
            }
            
            result = self.collection.insert_one(content_data)
            content_data["_id"] = str(result.inserted_id)
            return True, "内容添加成功", content_data
        except Exception as e:
            return False, f"Failed to add content: {str(e)}", None
    
    def get_todo_contents(self, todo_id: str, user_id: str) -> Tuple[bool, str, List[Dict]]:
        """
        获取Todo的所有内容
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            
        Returns:
            Tuple[bool, str, List[Dict]]: (是否成功, 消息, 内容列表)
        """
        # 检查Todo是否存在
        todo_model = TodoModel()
        existing_todo = todo_model.find_todo(todo_id, user_id)
        if not existing_todo:
            return False, "Todo not found or not authorized", []
        
        try:
            contents = list(self.collection.find({
                "todo_id": todo_id,
                "user_id": user_id
            }).sort("created_at", 1))
            
            # 转换ObjectId和时间格式
            for content in contents:
                content["_id"] = str(content["_id"])
                if 'created_at' in content:
                    content["created_at"] = content["created_at"].isoformat()
            
            return True, "Contents retrieved successfully", contents
        except Exception as e:
            return False, f"Failed to get contents: {str(e)}", []
    
    def update_content(self, content_id: str, user_id: str, update_fields: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        更新Todo内容
        
        Args:
            content_id: 内容ID
            user_id: 用户ID
            update_fields: 更新数据
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 消息, 更新后的内容)
        """
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(content_id), "user_id": user_id},
                {"$set": update_fields}
            )
            
            if result.matched_count == 0:
                return False, "找不到Todo内容", None
            
            # 返回更新后的内容
            updated = self.collection.find_one({"_id": ObjectId(content_id)})
            if updated:
                updated["_id"] = str(updated["_id"])
                if 'created_at' in updated:
                    updated["created_at"] = updated["created_at"].isoformat()
                return True, "Content updated successfully", updated
            else:
                return False, "Failed to retrieve updated content", None
        except Exception as e:
            return False, f"Failed to update content: {str(e)}", None
    
    def delete_content(self, content_id: str, user_id: str) -> Tuple[bool, str]:
        """
        删除Todo内容
        
        Args:
            content_id: 内容ID
            user_id: 用户ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(content_id),
                "user_id": user_id
            })
            if result.deleted_count > 0:
                return True, "内容已删除"
            else:
                return False, "找不到内容"
        except Exception as e:
            return False, f"Failed to delete content: {str(e)}"
    
    def find_content_by_id(self, content_id: str, user_id: str) -> Optional[Dict]:
        """根据内容ID查找内容"""
        content = self.collection.find_one({
            "_id": ObjectId(content_id),
            "user_id": user_id
        })
        if content:
            content["_id"] = str(content["_id"])
            if 'created_at' in content:
                content["created_at"] = content["created_at"].isoformat()
        return content
    
    def delete_contents_by_todo(self, todo_id: str, user_id: str) -> int:
        """删除指定Todo的所有内容"""
        result = self.collection.delete_many({
            "todo_id": todo_id,
            "user_id": user_id
        })
        return result.deleted_count