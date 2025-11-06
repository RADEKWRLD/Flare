# 认证服务层，处理用户认证相关的业务逻辑
import jwt
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from models.user import UserModel
from config.settings import app_config

class AuthService:
    """认证服务类"""
    
    def __init__(self):
        """初始化认证服务"""
        self.user_model = UserModel()
        self.secret_key = app_config.secret_key
    
    def register(self, username: str, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        用户注册
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 消息, 用户数据)
        """
        # 验证输入参数
        if not username or not password or not email:
            return False, "Username, email, and password are required", None
        
        # 验证密码长度
        if len(password) < 8:
            return False, "Password must be at least 8 characters", None
        
        # 验证邮箱格式
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            return False, "Invalid email format", None
        
        # 检查用户是否已存在
        if self.user_model.find_by_username(username):
            return False, "Username already exists", None
        
        if self.user_model.find_by_email(email):
            return False, "Email already exists", None
        
        # 创建用户
        try:
            user = self.user_model.create_user(username, email, password)
            return True, "User registered successfully", user
        except Exception as e:
            return False, f"Registration failed: {str(e)}", None
    
    def login(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        用户登录
        
        Args:
            email: 邮箱
            password: 密码
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 消息, 登录结果)
        """
        # 验证输入参数
        if not email or not password:
            return False, "Email and password are required", None
        
        # 查找用户
        user = self.user_model.find_by_email(email)
        if not user:
            return False, "Invalid email or password", None
        
        # 验证密码
        if not self.user_model.verify_password(user, password):
            return False, "Invalid email or password", None
        
        # 生成JWT令牌
        token = self.generate_token(user['id'])
        
        return True, "Login successful", {
            "token": token,
            "username": user["username"],
            "email": user["email"]
        }
    
    def generate_token(self, user_id: str) -> str:
        """
        生成JWT令牌
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: JWT令牌
        """
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)  # 24小时过期
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            Optional[Dict]: 用户信息，如果令牌无效返回None
            
        Raises:
            jwt.ExpiredSignatureError: 令牌已过期
            jwt.InvalidTokenError: 令牌无效
        """
        try:
            # 解码JWT令牌
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # 查找用户
            user = self.user_model.find_by_id(payload['user_id'])
            return user
            
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError:
            raise jwt.InvalidTokenError("Token is invalid")
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 用户信息
        """
        user = self.user_model.find_by_id(user_id)
        if user:
            # 返回安全的用户信息，不包含密码
            return {
                "username": user["username"],
                "email": user["email"]
            }
        return None