import bcrypt
from typing import Optional, Dict
from .base import BaseModel
from config.database import db_client
#用户模型
class UserModel(BaseModel):
    def __init__(self):
        """初始化用户模型"""
        super().__init__(db_client.users)

    def find_by_email(self, email: str) -> Optional[Dict]:
        """根据邮箱查找用户"""
        user = self.collection.find_one({"email": email})
        return self.convert_objectid(user) if user else None
    
    def find_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名查找用户"""
        user = self.collection.find_one({"username": username})
        return self.convert_objectid(user) if user else None
    
    def create_user(self, username: str, email: str, password: str) -> Dict:
        """创建用户"""
        import uuid
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {
            'id': str(uuid.uuid4()),
            'username': username,
            'email': email,
            'password': hashed_password
        }
        return self.create(user_data)
    
    def verify_password(self, user: Dict, password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), user['password'])
        