#数据库连接模块
from pydoc import doc
from pymongo import MongoClient
from pymongo.server_api import ServerApi
#导入redis
import redis
from redis import Redis
#导入redis的搜索模块
from redis.commands.search.query import Query
#导入redis的搜索字段模块
from redis.commands.search.field import (
    NumericField,
    TagField,
    TextField,
    VectorField,
)
#开发环境
# from redis.commands.search.index_definition import IndexDefinition, IndexType
#部署环境
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from utils.decorators import singleton
#导入配置
from config.settings import db_config

@singleton
class MongoDBClient:
    _client=None
    _db=None

    def __init__(self):
        if self._client is not None:
            return
        self._client=MongoClient(db_config.mongodb_uri, server_api=ServerApi('1'))
        self._db=self._client[db_config.database_name]
        self.setup_indexes()
        print('MongoDB连接成功')

    #设置索引
    def setup_indexes(self):
        self._db['users'].create_index("username", unique=True)
        self._db['users'].create_index("email", unique=True)
        self._db['todos'].create_index([("user_id", 1), ("created_at", -1)])
        self._db['todosContent'].create_index([("user_id", 1), ("created_at", -1)])
        # self._db['vector'].create_index([("user_id", 1)])

    #数据库配置
    @property
    def db(self):
        return self._db
    
    #获取user信息
    @property
    def users(self):
        return self._db['users']
    
    #获取todo信息
    @property
    def todos(self):
        return self._db['todos']
    
    #获取todo内容信息
    @property
    def todosContent(self):
        return self._db['todosContent']
    
    # #获取向量信息
    # @property
    # def vector(self):
    #     return self._db['vector']

#创建全局数据库实例
db_client=MongoDBClient()

#Redis客户端
@singleton
class RedisClient:
    _client=None

    #规定vector索引
    vector_schema=[
        TextField('content'),
        TagField('user_id'),
        TextField('raw'),
        TextField('text'),
        VectorField(
                        "vector",                   # 向量字段
                        # "FLAT",                     # 使用FLAT算法适应小中数据
                        # {
                        #     "TYPE": "FLOAT32",
                        #     "DIM": 1024,#1024是向量维度
                        #     "DISTANCE_METRIC": "COSINE"
                        # }
                        "HNSW",                     # 使用HNSW算法适应大中数据
                        {
                            "TYPE": "FLOAT32",
                            "DIM": 1024,#512是向量维度
                            "DISTANCE_METRIC": "COSINE",
                            "INITIAL_CAP": 1000,
                            "M": 16,  # HNSW 参数：连接数
                            "EF_CONSTRUCTION": 200,  # 构建时的搜索深度
                            "EF_RUNTIME": 10  # 查询时的搜索深度
                        }
                    )
    ]

    content_schema = [
        TextField('content'),          
        TagField('user_id'),          
        TagField('todo_id'),           
        TagField('content_id'),      
        TextField('images'),          
        TextField('files'),           
        TagField('complete'),          
        NumericField('created_at', sortable=True) 
    ]

    #连接
    def __init__(self):
        if self._client is not None:
            return 
        
        #数据库配置
        self._client=Redis(
        host=db_config.redis_host, 
        port=db_config.redis_port, 
        db=db_config.redis_db,
        decode_responses=False#向量数据不需要解码成字符串
        )
        
        self._client.ping()
        print('Redis连接成功')

        self.init_index()
        print('索引创建成功')


    #初始化操作，如果没有就创建索引
    def init_index(self):
        try:
            self._client.ft('vector').info()
            self._client.ft('content').info()
        except Exception as e:
            try:
                vector_definition=IndexDefinition(
                    prefix=[
                    "vector:"
                    ],
                    index_type=IndexType.HASH
                )
                self._client.ft('vector').create_index(self.vector_schema,vector_definition)
                content_definition=IndexDefinition(
                    prefix=[
                    "content:"
                    ],
                    index_type=IndexType.HASH
                )
                self._client.ft('content').create_index(self.content_schema,content_definition)
            except Exception as e:
                print(f'创建索引失败: {e}')

    
    
    @property
    #返回客户端
    def client(self):
        return self._client

    @property
    def vector(self):
        return self._client['vector']

    @property
    def todosContent(self):
        return self._client['todosContent']

#缓存客户端
cache_client=RedisClient()
    
    


    
    
