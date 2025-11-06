#指定接口层，定义所有模型所需的通用方法和属性
from abc import ABC, abstractmethod
from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List, Optional


class BaseModel(ABC):
    def __init__(self,collection):
        self.collection=collection

    @staticmethod
    def convert_objectid(data):
        if isinstance(data,list):
            return [BaseModel.convert_objectid(item) for item in data]
        if isinstance(data,dict):
            return {k: BaseModel.convert_objectid(v) for k,v in data.items()}
        if isinstance(data,ObjectId):
            return str(data)
        return data
    
    def find_by_id(self, doc_id: str) -> Optional[Dict]:
        """根据ID查找文档"""
        doc = self.collection.find_one({"id": doc_id})
        return self.convert_objectid(doc) if doc else None
    
    def find_by_user_id(self, user_id: str) -> List[Dict]:
        """根据用户ID查找文档"""
        docs = list(self.collection.find({"user_id": user_id}))
        return self.convert_objectid(docs)
    
    def create(self, data: Dict) -> Dict:
        """创建文档"""
        data['created_at'] = datetime.utcnow()
        result = self.collection.insert_one(data)
        data['_id'] = str(result.inserted_id)
        return self.convert_objectid(data)
    
    def update(self, doc_id: str, data: Dict) -> bool:
        """更新文档"""
        result = self.collection.update_one({"id": doc_id}, {"$set": data})
        return result.modified_count > 0
    
    def delete(self, doc_id: str) -> bool:
        """删除文档"""
        result = self.collection.delete_one({"id": doc_id})
        return result.deleted_count > 0

    