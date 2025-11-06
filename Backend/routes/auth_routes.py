# 认证路由模块，处理用户注册、登录等认证相关的路由
from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from utils.decorators import token_required, validate_json, handle_exceptions
from utils.validators import validate_email, validate_password, validate_username

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# 初始化认证服务
auth_service = AuthService()


@auth_bp.route('/register', methods=['POST'])
@handle_exceptions
@validate_json(['username', 'email', 'password'])
def register():
    """
    用户注册路由
    
    请求体:
        {
            "username": "用户名",
            "email": "邮箱",
            "password": "密码"
        }
    
    返回:
        成功: {"message": "User registered successfully"}, 201
        失败: {"message": "错误信息"}, 400
    """
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    # 基础验证
    if not validate_username(username):
        return jsonify({"message": "用户名格式无效，长度应为3-20个字符，只允许字母、数字、下划线"}), 400
    
    if not validate_email(email):
        return jsonify({"message": "邮箱格式无效"}), 400
    
    if not validate_password(password):
        return jsonify({"message": "密码长度至少8个字符"}), 400
    
    # 调用认证服务进行注册
    success, message, user_data = auth_service.register(username, email, password)
    
    if success:
        return jsonify({"message": message}), 201
    else:
        return jsonify({"message": message}), 400


@auth_bp.route('/login', methods=['POST'])
@handle_exceptions
@validate_json(['email', 'password'])
def login():
    """
    用户登录路由
    
    请求体:
        {
            "email": "邮箱",
            "password": "密码"
        }
    
    返回:
        成功: {
            "message": "Login successful",
            "token": "JWT令牌",
            "username": "用户名",
            "email": "邮箱"
        }, 200
        失败: {"message": "错误信息"}, 401
    """
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    # 基础验证
    if not validate_email(email):
        return jsonify({"message": "邮箱格式无效"}), 400
    
    if not password:
        return jsonify({"message": "密码不能为空"}), 400
    
    # 调用认证服务进行登录
    success, message, result = auth_service.login(email, password)
    
    if success:
        return jsonify({
            "message": message,
            "token": result["token"],
            "username": result["username"],
            "email": result["email"]
        }), 200
    else:
        return jsonify({"message": message}), 401


@auth_bp.route('/me', methods=['GET'])
@handle_exceptions
@token_required
def get_me(current_user):
    """
    获取当前用户信息路由
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        成功: {
            "username": "用户名",
            "email": "邮箱"
        }, 200
        失败: {"message": "错误信息"}, 401
    """
    return jsonify({
        "username": current_user["username"],
        "email": current_user["email"]
    }), 200


@auth_bp.route('/verify-token', methods=['POST'])
@handle_exceptions
def verify_token():
    """
    验证Token路由
    
    请求体:
        {
            "token": "JWT令牌"
        }
    
    返回:
        成功: {
            "valid": true,
            "user": {
                "username": "用户名",
                "email": "邮箱"
            }
        }, 200
        失败: {"valid": false, "message": "错误信息"}, 401
    """
    data = request.get_json()
    if not data or 'token' not in data:
        return jsonify({"valid": False, "message": "Token is required"}), 400
    
    token = data['token']
    
    try:
        user = auth_service.verify_token(token)
        if user:
            return jsonify({
                "valid": True,
                "user": {
                    "username": user["username"],
                    "email": user["email"]
                }
            }), 200
        else:
            return jsonify({"valid": False, "message": "User not found"}), 401
    except Exception as e:
        return jsonify({"valid": False, "message": str(e)}), 401


@auth_bp.route('/logout', methods=['POST'])
@handle_exceptions
@token_required
def logout(current_user):
    """
    用户登出路由（当前实现为简单确认，实际应用中可以加入Token黑名单机制）
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        成功: {"message": "Logout successful"}, 200
    """
    # 注意：在实际应用中，这里应该将token加入黑名单
    # 或者使用Redis等缓存来管理token状态
    return jsonify({"message": "Logout successful"}), 200