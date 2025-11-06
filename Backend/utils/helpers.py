# 工具函数模块，提供通用的辅助函数
import time
import json
from typing import Any, Dict, List, Generator
from bson import ObjectId
from datetime import datetime
from flask import Response

def convert_objectid(data: Any) -> Any:
    """
    递归转换 ObjectId 为字符串
    
    Args:
        data: 需要转换的数据
        
    Returns:
        转换后的数据
    """
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    if isinstance(data, dict):
        return {k: convert_objectid(v) for k, v in data.items()}
    if isinstance(data, ObjectId):
        return str(data)
    return data


def format_datetime(dt: datetime) -> str:
    """
    格式化日期时间为ISO格式字符串
    
    Args:
        dt: 日期时间对象
        
    Returns:
        ISO格式的日期时间字符串
    """
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def create_sse_response(generator_func: Generator, **kwargs) -> Response:
    """
    创建Server-Sent Events (SSE) 响应
    
    Args:
        generator_func: 生成器函数
        **kwargs: 传递给生成器函数的参数
        
    Returns:
        Flask Response对象
    """
    def generate():
        try:
            for data in generator_func(**kwargs):
                yield f"data: {data}\n\n"
                time.sleep(0.01)  # 控制推流节奏
            yield "event: end\ndata: [DONE]\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return Response(generate(), mimetype="text/event-stream")


def create_sse_error_response(error_message: str) -> Response:
    """
    创建SSE错误响应
    
    Args:
        error_message: 错误消息
        
    Returns:
        Flask Response对象
    """
    def generate_error():
        yield f"data: {error_message}\n\n"
        yield "event: error\ndata: [ERROR]\n\n"
    
    return Response(generate_error(), mimetype="text/event-stream")


def stream_todo_contents(contents: List[Dict]) -> Generator[str, None, None]:
    """
    流式发送Todo内容的生成器
    
    Args:
        contents: Todo内容列表
        
    Yields:
        JSON格式的内容字符串
    """
    for content in contents:
        # 确保时间格式正确
        if 'created_at' in content and isinstance(content['created_at'], datetime):
            content['created_at'] = content['created_at'].isoformat()
        
        yield json.dumps(content, ensure_ascii=False)
        time.sleep(0.05)  # 控制推流节奏


def validate_file_upload(files: List, max_count: int = 10, max_size: int = 200 * 1024 * 1024) -> tuple:
    """
    验证文件上传
    
    Args:
        files: 文件列表
        max_count: 最大文件数量
        max_size: 最大文件大小（字节）
        
    Returns:
        tuple: (是否有效, 错误消息)
    """
    if len(files) > max_count:
        return False, f"文件数量不能超过{max_count}个"
    
    for file in files:
        if file:
            # 检查文件大小
            file.seek(0, 2)  # 移动到文件末尾
            size = file.tell()
            file.seek(0)  # 重置文件指针
            
            if size > max_size:
                return False, f"文件 {file.filename} 超过大小限制"
    
    return True, ""


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    import uuid
    import os
    
    # 获取文件扩展名
    name, ext = os.path.splitext(filename)
    
    # 生成UUID作为文件名
    safe_name = str(uuid.uuid4())
    
    return f"{safe_name}{ext}"


def paginate_results(results: List[Any], page: int = 1, per_page: int = 20) -> Dict:
    """
    分页处理结果
    
    Args:
        results: 结果列表
        page: 页码（从1开始）
        per_page: 每页数量
        
    Returns:
        分页结果字典
    """
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        "data": results[start:end],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }
