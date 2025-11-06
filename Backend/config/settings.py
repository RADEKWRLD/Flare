#配置层，方便后续的配置管理，设置全局的配置信息
import os
from dataclasses import dataclass,field
from typing import List
from dotenv import load_dotenv
import redis

load_dotenv()

#数据库配置
@dataclass
class DatabaseConfig:
    #MongoDB的配置
    mongodb_uri: str = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    database_name: str = os.getenv('DATABASE_NAME', 'todo_app')
    #Redis的配置
    redis_host: str = os.getenv('REDIS_HOST', '127.0.0.1')
    redis_port: str = os.getenv('REDIS_PORT','6379')
    # redis_password: str = os.getenv('REDIS_PASSWORD')
    redis_vector_ttl: int = os.getenv('REDIS_VECTOR_TTL', 3*24*60*60)#3天
    redis_content_ttl: int = os.getenv('REDIS_CONTENT_TTL', 3600)#一小时
    redis_db: int = os.getenv('REDIS_DB', 0)

    
#大模型配置
@dataclass
class AIconfig:
    deepseek_api_key: str = os.getenv('DEEPSEEK_API_KEY') or ""
    #向量嵌入模型
    # model_name:str = os.getenv('MODEL_NAME', 'BAAI/bge-m3')
    model_name:str = os.getenv('MODEL_NAME', './bge-m3')
    #HuggingFace镜像地址
    hf_endpoint: str = os.getenv('HF_ENDPOINT', 'https://hf-mirror.com')

#应用层配置
@dataclass
class AppConfig:
    #JWT密钥
    secret_key: str = os.getenv('SECRET_KEY') or ""
    #上传文件夹
    upload_folder: str = os.getenv('UPLOAD_FOLDER', './uploads')
    #最大文件大小
    max_file_size: int = int(os.getenv('MAX_FILE_SIZE', 200 * 1024 * 1024))
    #允许的文件类型
    allowed_file_extensions: List[str] = field(
        default_factory=lambda: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'md']
    )
    #允许的图片类型
    allowed_image_extensions: List[str] = field(
        default_factory=lambda: ['png', 'jpg', 'jpeg', 'gif']
    )
    #最大文件数量
    max_file_count: int = int(os.getenv('MAX_FILE_COUNT', 10))

#RAG配置
@dataclass
class RAGConfig:
    #检索结果数量
    top_k: int = int(os.getenv('TOP_K', 5))
    #检索结果相似度阈值
    similarity_threshold: float = float(os.getenv('SIMILARITY_THRESHOLD', 0.5))


#创建全局配置
db_config=DatabaseConfig()
ai_config=AIconfig()
app_config=AppConfig()
rag_config=RAGConfig()