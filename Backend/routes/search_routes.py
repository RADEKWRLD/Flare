# 搜索路由模块，处理RAG搜索和问答相关的路由
import time
import jwt
from flask import Blueprint, request, jsonify, Response
from services.vector_service import VectorService
from services.auth_service import AuthService
from utils.decorators import handle_exceptions
from utils.validators import validate_search_query
from config.settings import app_config

# 创建搜索蓝图
search_bp = Blueprint('search', __name__)

# 初始化服务
vector_service = VectorService()
auth_service = AuthService()

# 导入RAG服务
from services.rag_service import RAGService

# 初始化RAG服务
try:
    rag_service = RAGService()
    print("RAG服务初始化成功")
except Exception as e:
    print(f"RAG服务初始化失败: {e}")
    rag_service = None


def verify_token_for_sse(token):
    """
    为SSE连接验证Token的辅助函数
    
    Args:
        token: JWT令牌
        
    Returns:
        tuple: (是否有效, 用户信息或错误消息)
    """
    if not token:
        return False, "Token is missing"
    
    try:
        user = auth_service.verify_token(token)
        return True, user
    except jwt.ExpiredSignatureError:
        return False, "Token has expired"
    except jwt.InvalidTokenError:
        return False, "Token is invalid"
    except Exception as e:
        return False, f"Token verification failed: {str(e)}"


@search_bp.route('/search', methods=['GET', 'POST'])
@handle_exceptions
def chat():
    """
    RAG搜索和问答路由（支持GET和POST，返回SSE流）
    
    POST请求体:
        {
            "question": "问题",
            "user_id": "用户ID",
            "token": "JWT令牌",
            "continue": false  # 是否继续对话
        }
    
    GET请求参数:
        question: 问题
        user_id: 用户ID
        token: JWT令牌
        continue: 是否继续对话 (true/false)
    
    返回:
        SSE流式响应
    """
    # 检查RAG服务是否可用
    if not rag_service:
        return jsonify({"error": "RAG service is not available"}), 503
    
    # 解析请求参数
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"message": "请求体不能为空"}), 400
        
        question = data.get("question", "").strip()
        user_id = data.get('user_id', '')
        token = data.get('token', '')
        continue_chat = data.get('continue', False)
    else:  # GET方法
        question = request.args.get("question", "").strip()
        user_id = request.args.get('user_id', '')
        token = request.args.get('token', '')
        continue_chat = request.args.get('continue', 'false').lower() == 'true'
    
    # 验证输入参数
    if not validate_search_query(question):
        error_msg = "问题不能为空且长度不能超过500个字符"
        if request.method == "POST":
            return jsonify({"message": error_msg}), 400
        else:
            def generate_error():
                yield f"event: error\ndata: {error_msg}\n\n"
            return Response(generate_error(), mimetype="text/event-stream")
    
    if not user_id:
        error_msg = "用户ID不能为空"
        if request.method == "POST":
            return jsonify({"message": error_msg}), 400
        else:
            def generate_error():
                yield f"event: error\ndata: {error_msg}\n\n"
            return Response(generate_error(), mimetype="text/event-stream")
    
    # 验证Token
    token_valid, user_or_error = verify_token_for_sse(token)
    if not token_valid:
        if request.method == "POST":
            return jsonify({"message": user_or_error}), 401
        else:
            def generate_error():
                yield f"event: error\ndata: {user_or_error}\n\n"
            return Response(generate_error(), mimetype="text/event-stream")
    
    # 检查用户ID是否匹配
    if user_or_error['id'] != user_id:
        error_msg = "用户ID不匹配"
        if request.method == "POST":
            return jsonify({"message": error_msg}), 403
        else:
            def generate_error():
                yield f"event: error\ndata: {error_msg}\n\n"
            return Response(generate_error(), mimetype="text/event-stream")
    
    # 如果是继续对话，添加标记
    if continue_chat:
        print(f"继续之前的对话: {question}")
    
    # 调用RAG服务
    try:
        result = rag_service.process_question(question, user_id, continue_chat)
        
        # 返回SSE流式响应
        def generate():
            try:
                # 如果是继续对话，先发送一个通知
                if continue_chat:
                    yield f"data: [继续上次对话...]\n\n"
                    time.sleep(0.5)  # 添加短暂延迟
                
                # 流式输出答案
                for token_text in result["answer"]():
                    yield f"data: {token_text}\n\n"
                    time.sleep(0.01)  # 确保数据立即发送
                
                # 结束标记
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                print(f"RAG生成异常: {e}")
                yield f"event: error\ndata: 生成回答时发生错误: {str(e)}\n\n"
        
        return Response(generate(), mimetype="text/event-stream")
        
    except Exception as e:
        print(f"RAG调用异常: {e}")
        error_msg = f"搜索服务异常: {str(e)}"
        
        if request.method == "POST":
            return jsonify({"error": error_msg}), 500
        else:
            def generate_error():
                yield f"event: error\ndata: {error_msg}\n\n"
            return Response(generate_error(), mimetype="text/event-stream")


@search_bp.route('/search/vector', methods=['POST'])
@handle_exceptions
def vector_search():
    """
    纯向量搜索路由（不使用RAG，直接返回相似文档）
    
    请求体:
        {
            "query": "搜索查询",
            "user_id": "用户ID",
            "token": "JWT令牌",
            "top_k": 5  # 可选，返回结果数量
        }
    
    返回:
        成功: {
            "results": [
                {
                    "score": 0.95,
                    "doc_id": "文档ID",
                    "content": "文档内容"
                }
            ]
        }, 200
        失败: {"message": "错误信息"}, 400/401/500
    """
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求体不能为空"}), 400
    
    query = data.get("query", "").strip()
    user_id = data.get("user_id", "")
    token = data.get("token", "")
    top_k = data.get("top_k", 5)
    
    # 验证输入
    if not validate_search_query(query):
        return jsonify({"message": "查询不能为空且长度不能超过500个字符"}), 400
    
    if not user_id:
        return jsonify({"message": "用户ID不能为空"}), 400
    
    # 验证Token
    token_valid, user_or_error = verify_token_for_sse(token)
    if not token_valid:
        return jsonify({"message": user_or_error}), 401
    
    # 检查用户ID是否匹配
    if user_or_error['id'] != user_id:
        return jsonify({"message": "用户ID不匹配"}), 403
    
    # 验证top_k参数
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        top_k = 5
    
    try:
        # 执行向量搜索
        search_results = vector_service.search_embedding(query, user_id, top_k)
        
        # 格式化结果
        results = []
        for score, doc_id in search_results:
            # 获取文档详细信息
            embedding_doc = vector_service.get_embedding_by_doc_id(doc_id, user_id)
            if embedding_doc:
                results.append({
                    "score": score,
                    "doc_id": doc_id,
                    "content": embedding_doc.get("text", ""),
                    "raw_data": embedding_doc.get("raw", {})
                })
        
        return jsonify({"results": results}), 200
        
    except Exception as e:
        print(f"向量搜索异常: {e}")
        return jsonify({"error": f"搜索失败: {str(e)}"}), 500


@search_bp.route('/search/health', methods=['GET'])
def health_check():
    """
    搜索服务健康检查
    
    返回:
        {
            "status": "healthy",
            "rag_available": true/false,
            "vector_service": "ready"
        }
    """
    return jsonify({
        "status": "healthy",
        "rag_available": rag_service is not None,
        "vector_service": "ready"
    }), 200
