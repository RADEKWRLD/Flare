# 向量服务层，处理向量嵌入和搜索相关的业务逻辑
import os
import numpy as np
from typing import List, Tuple, Dict, Optional
from FlagEmbedding import BGEM3FlagModel
from models.base import BaseModel
from config.database import cache_client, db_client
from config.settings import ai_config,db_config
import json
from utils.decorators import singleton

@singleton
class VectorService(BaseModel):
    """向量服务类"""
    _model = None
    
    def __init__(self):
        """初始化向量服务"""
        if self._model is None:
            # super().__init__(db_client.vector)
            #导入实例
            self.redis_client = cache_client.client
            self.vector_ttl = db_config.redis_vector_ttl

            # 设置HuggingFace镜像
            os.environ['HF_ENDPOINT'] = ai_config.hf_endpoint
            
            # 加载向量模型
            self._model = BGEM3FlagModel(ai_config.model_name, use_fp16=True)
            print('向量模型加载成功')
    
    def encode_dense(self, texts: List[str], batch_size: int = 8, max_length: int = 2048) -> np.ndarray:
        """
        稠密向量编码，用于语义搜索
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
            max_length: 最大文本长度
            
        Returns:
            np.ndarray: 稠密向量数组
        """
        if not texts:
            return np.zeros((0, 1))
        
        out = self._model.encode(
            texts,
            batch_size=batch_size,
            max_length=max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )
        return np.array(out["dense_vecs"])
    
    # def encode_sparse(self, texts: List[str]) -> List[Dict]:
    #     """
    #     稀疏向量编码，输出字典格式
        
    #     Args:
    #         texts: 文本列表
            
    #     Returns:
    #         List[Dict]: 稀疏向量字典列表
    #     """
    #     out = self._model.encode(
    #         texts,
    #         return_dense=False,
    #         return_sparse=True,
    #         return_colbert_vecs=False
    #     )
    #     return out["lexical_weights"]
    
    # def encode_colbert(self, texts: List[str]) -> List[np.ndarray]:
    #     """
    #     ColBERT多向量编码，用于精细匹配
        
    #     Args:
    #         texts: 文本列表
            
    #     Returns:
    #         List[np.ndarray]: ColBERT向量列表
    #     """
    #     out = self._model.encode(
    #         texts,
    #         return_dense=False,
    #         return_sparse=False,
    #         return_colbert_vecs=True
    #     )
    #     return out["colbert_vecs"]
    
    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            a: 向量a
            b: 向量b
            
        Returns:
            float: 余弦相似度值
        """
        a, b = np.array(a), np.array(b)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def save_embedding(self, doc_id: str, user_id: str, text: str, raw_data: Dict = None) -> Dict:
        """
        保存向量嵌入到数据库
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            text: 文本内容
            raw_data: 原始数据（如图片、文件路径等）
            
        Returns:
            Dict: 保存的文档数据
            
        Raises:
            ValueError: 当user_id为空时抛出
        """
        if not user_id:
            raise ValueError("User ID is required")
        
        # 生成向量嵌入
        vector = self.encode_dense([text])[0]

        #Redis索引
        redis_key = f'vector:{doc_id}'
        
        # # 构建文档数据 for MongoDB
        # doc = {
        #     "doc_id": doc_id,
        #     "user_id": user_id,
        #     "raw": raw_data or {},
        #     "text": text,
        #     "vector": vector.tolist()
        # }
        
        # # 保存到数据库
        # result = self.collection.insert_one(doc)
        # doc['_id'] = str(result.inserted_id)
        # return doc

        #构建vector for Redis
        doc = {
            "doc_id": doc_id,
            "user_id": user_id,
            "raw": json.dumps(raw_data or {}, ensure_ascii=False),
            "text": text,
            "vector": vector.astype(np.float32).tobytes()
        }

        self.redis_client.hset(redis_key,mapping=doc)
        self.redis_client.expire(redis_key,self.vector_ttl)
        return {
            "doc_id": doc_id,
            "user_id": user_id,
            "text": text,
            "raw": raw_data or {}
        }
    
    def search_embedding(self, query: str, user_id: str, top_k: int = 5) -> List[Tuple[float, str]]:
        """
        向量搜索
        
        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 返回前k个结果
            
        Returns:
            List[Tuple[float, str]]: (相似度分数, 文档ID) 列表
            
        Raises:
            ValueError: 当user_id为空时抛出
        """
        if not user_id:
            raise ValueError("User ID is required")


        # 生成查询向量
        query_vec = self.encode_dense([query])[0]

        try:
            #查询向量转为字节向量
            query_vec_bytes = query_vec.astype(np.float32).tobytes()

            #报错向量搜索异常: 向量搜索异常: Syntax error at offset 28 near -4339
            #原因是UUID中有-符号,所以需要转义

            #构建RedisSearch查询
            # query_str = f"@user_id:{{{user_id}}} => [KNN {top_k} @vector $vec AS score]"
            query_str = f"* => [KNN {top_k * 3} @vector $vec AS score]"

            from redis.commands.search.query import Query
            q=(
                Query(query_str).sort_by("score").paging(0,top_k).return_fields("user_id","doc_id","score").dialect(2)
            )
            # 执行搜索，返回结果 包含doc_id和score
            results = self.redis_client.ft("vector").search(
            q,
            query_params={"vec": query_vec_bytes}
            )
             # 格式化结果
            scores = []
            for doc in results.docs:
                # 获取 user_id
                doc_user_id = getattr(doc, 'user_id', None)
                if isinstance(doc_user_id, bytes):
                    doc_user_id = doc_user_id.decode('utf-8')
                
                # 只保留当前用户的结果
                if doc_user_id != user_id:
                    continue
                
                # 提取 doc_id
                doc_id = doc.id.replace("vector:", "") if hasattr(doc, 'id') else ""
                
                # 计算相似度
                distance = float(getattr(doc, 'score', 0.0))
                similarity = 1 - (distance / 2)
                
                scores.append((similarity, doc_id))
                
                # 获取足够结果后停止
                if len(scores) >= top_k:
                    break
            return scores[:top_k]

        except Exception as e:
            raise ValueError(f"向量搜索异常: {e}")




        # scores=[]
        # cursor = 0 

        # while True:
        #     cursor,keys = self.redis_client.scan(cursor,match="vector:*",count=100)
        #     for key in keys:
        #         if isinstance(key,bytes):
        #             #解码key
        #             key = key.decode("utf-8")
                
        #         #得到向量数据
        #         doc_user_id = self.redis_client.hget(key,"user_id")
        #         if isinstance(doc_user_id,bytes):
        #             doc_user_id = doc_user_id.decode("utf-8")
        #             #当不是用户id时跳出循环
        #         if doc_user_id!=user_id:
        #             continue
                
        #         #获取向量
        #         vector_bytes = self.redis_client.hget(key,"vector")
        #         if not vector_bytes:
        #             continue
        #         doc_vector = np.frombuffer(vector_bytes,dtype=np.float32)

        #         #计算相似度
        #         score= self.cosine_similarity(query_vec,doc_vector)

        #         # 提取 doc_id (移除 "vector:" 前缀)
        #         doc_id = key.replace("vector:", "")
        #         scores.append((score, doc_id))
        #     if cursor==0:
        #         break
        # #排序损失
        # scores.sort(key=lambda x:x[0],reverse=True)
        # return scores[:top_k]

    def delete_by_doc_id(self, doc_id: str, user_id: str) -> bool:
        """
        根据文档ID删除向量
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        # result = self.collection.delete_one({
        #     "doc_id": doc_id,
        #     "user_id": user_id
        # })
        # return result.deleted_count > 0

        redis_key = f"vector:{doc_id}"

        #验证是不是属于该用户
        doc_user_id=self.redis_client.hget(redis_key,"user_id")
        if doc_user_id:
            if isinstance(doc_user_id,bytes):
                doc_user_id=doc_user_id.decode("utf-8")
            if doc_user_id == user_id:
                result = self.redis_client.delete(redis_key)
                return result > 0
        return False
    
    def delete_by_todo_id(self, todo_id: str, user_id: str) -> int:
        """
        删除指定Todo的所有向量
        
        Args:
            todo_id: Todo ID
            user_id: 用户ID
            
        Returns:
            int: 删除的文档数量
        """
        # 从 MongoDB 中查找该 Todo 的所有内容
        contents = db_client.todosContent.find({"todo_id": todo_id, "user_id": user_id})
        
        # 收集需要删除的 Redis key
        keys_to_delete = []
        for content in contents:
            content_id = str(content["_id"])
            redis_key = f"vector:{content_id}"
            
            # 验证是否属于该用户
            doc_user_id = self.redis_client.hget(redis_key, "user_id")
            if doc_user_id:
                if isinstance(doc_user_id, bytes):
                    doc_user_id = doc_user_id.decode("utf-8")
                if doc_user_id == user_id:
                    keys_to_delete.append(redis_key)
        
        # 批量删除
        if keys_to_delete:
            deleted_count = self.redis_client.delete(*keys_to_delete)
            return deleted_count
        
        return 0
    
    def update_embedding(self, doc_id: str, user_id: str, text: str, raw_data: Dict = None) -> bool:
        """
        更新向量嵌入
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            text: 新的文本内容
            raw_data: 新的原始数据
            
        Returns:
            bool: 是否更新成功
        """
        if not user_id:
            raise ValueError("User ID is required")
        #设置索引
        redis_key = f"vector:{doc_id}"

        # 验证是否属于该用户
        doc_user_id = self.redis_client.hget(redis_key, "user_id")
        if not doc_user_id:
            return False
        
        if isinstance(doc_user_id, bytes):
            doc_user_id = doc_user_id.decode('utf-8')
        
        if doc_user_id != user_id:
            return False
        
        # 生成新的向量嵌入
        vector = self.encode_dense([text])[0]
        
        # 更新数据
        update_data = {
            "text": text,
            # "vector": vector.tolist()
            "vector":vector.astype(np.float32).tobytes()
        }

        if raw_data is not None:
            # update_data["raw"] = raw_data
            update_data["raw"] = json.dumps(raw_data, ensure_ascii=False)

        
        # result = self.collection.update_one(
        #     {"doc_id": doc_id, "user_id": user_id},
        #     {"$set": update_data}
        # )
        #更新哈希
        self.redis_client.hset(redis_key, mapping=update_data)

        #重置过期时间
        self.redis_client.expire(redis_key,self.vector_ttl)

        return True


        # return result.modified_count > 0
    
    def get_embedding_by_doc_id(self, doc_id: str, user_id: str) -> Optional[Dict]:
        """
        根据文档ID获取向量嵌入
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 向量文档数据
        """
        # doc = self.collection.find_one({
        #     "doc_id": doc_id,
        #     "user_id": user_id
        # })
        # return self.convert_objectid(doc) if doc else None
        redis_key = f"vector:{doc_id}"
        
        # 获取所有字段
        doc_data = self.redis_client.hgetall(redis_key)
        
        if not doc_data:
            return None
        
        # 解码数据
        doc_user_id = doc_data.get(b"user_id", b"").decode('utf-8')
        
        if doc_user_id != user_id:
            return None
        
        # 反序列化向量
        vector_bytes = doc_data.get(b"vector")
        vector = np.frombuffer(vector_bytes, dtype=np.float32).tolist() if vector_bytes else []
        
        return {
            "doc_id": doc_data.get(b"doc_id", b"").decode('utf-8'),
            "user_id": doc_user_id,
            "text": doc_data.get(b"text", b"").decode('utf-8'),
            "raw": json.loads(doc_data.get(b"raw", b"{}").decode('utf-8')),
            "vector": vector
        }