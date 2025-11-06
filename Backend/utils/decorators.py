# 装饰器模块，提供认证和其他通用装饰器
import jwt
from functools import wraps
from flask import request, jsonify

def token_required(f):
    """
    Token认证装饰器，用于保护需要认证的路由
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from services.auth_service import AuthService
        auth_service = AuthService()
        token = None
        
        # 从请求头获取token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({"message": "Invalid authorization header format"}), 401
        
        # 从URL参数获取token（用于SSE等场景）
        if not token:
            token = request.args.get("token", None)
            
        if not token:
            return jsonify({"message": "Token is missing"}), 401
        
        try:
            # 验证token并获取用户信息
            current_user = auth_service.verify_token(token)
            if not current_user:
                return jsonify({"message": "User not found"}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token is invalid"}), 401
        except Exception as e:
            return jsonify({"message": f"Token verification failed: {str(e)}"}), 401
        
        # 将用户信息传递给被装饰的函数
        return f(current_user, *args, **kwargs)
    
    return decorated


def validate_json(required_fields=None):
    """
    JSON数据验证装饰器
    
    Args:
        required_fields: 必需的字段列表
        
    Returns:
        装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 检查是否有JSON数据
            if not request.is_json:
                return jsonify({"message": "Request must be JSON"}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({"message": "No JSON data provided"}), 400
            
            # 检查必需字段
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or not data[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        "message": f"Missing required fields: {', '.join(missing_fields)}"
                    }), 400
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def handle_exceptions(f):
    """
    异常处理装饰器，统一处理路由中的异常
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            import traceback
            print(f"路由异常: {traceback.format_exc()}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    return decorated


#单例模式
def singleton(cls):
    instances={}
    def get_instance(*args,**kwargs):
        if cls not in instances:
            instances[cls]=cls(*args,**kwargs)
        return instances[cls]
    return get_instance