# 验证器模块，提供各种数据验证功能
import re
from typing import List, Optional

def validate_email(email: str) -> bool:
    """
    验证邮箱格式
    
    Args:
        email: 邮箱地址
        
    Returns:
        bool: 是否为有效邮箱格式
    """
    if not email:
        return False
    
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_regex, email))


def validate_password(password: str) -> bool:
    """
    验证密码强度
    
    Args:
        password: 密码
        
    Returns:
        bool: 是否符合密码要求
    """
    if not password:
        return False
    
    # 至少8个字符
    return len(password) >= 8


def validate_username(username: str) -> bool:
    """
    验证用户名格式
    
    Args:
        username: 用户名
        
    Returns:
        bool: 是否为有效用户名
    """
    if not username:
        return False
    
    # 用户名长度3-20个字符，只允许字母、数字、下划线
    if len(username) < 3 or len(username) > 20:
        return False
    
    username_regex = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(username_regex, username))


def validate_todo_title(title: str) -> bool:
    """
    验证Todo标题
    
    Args:
        title: Todo标题
        
    Returns:
        bool: 是否为有效标题
    """
    if not title or not title.strip():
        return False
    
    # 标题长度不超过200个字符
    return len(title.strip()) <= 200


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    验证文件扩展名
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表
        
    Returns:
        bool: 是否为允许的文件类型
    """
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in [e.lower() for e in allowed_extensions]


def validate_image_file(filename: str) -> bool:
    """
    验证图片文件类型
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否为允许的图片类型
    """
    allowed_extensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
    return validate_file_extension(filename, allowed_extensions)


def validate_document_file(filename: str) -> bool:
    """
    验证文档文件类型
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否为允许的文档类型
    """
    allowed_extensions = ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']
    return validate_file_extension(filename, allowed_extensions)


def validate_search_query(query: str) -> bool:
    """
    验证搜索查询
    
    Args:
        query: 搜索查询字符串
        
    Returns:
        bool: 是否为有效查询
    """
    if not query or not query.strip():
        return False
    
    # 查询长度不超过500个字符
    return len(query.strip()) <= 500


def validate_pagination_params(page: Optional[int], per_page: Optional[int]) -> tuple:
    """
    验证分页参数
    
    Args:
        page: 页码
        per_page: 每页数量
        
    Returns:
        tuple: (验证后的页码, 验证后的每页数量)
    """
    # 默认值
    if page is None or page < 1:
        page = 1
    
    if per_page is None or per_page < 1:
        per_page = 20
    elif per_page > 100:  # 限制最大每页数量
        per_page = 100
    
    return page, per_page


def validate_uuid(uuid_string: str) -> bool:
    """
    验证UUID格式
    
    Args:
        uuid_string: UUID字符串
        
    Returns:
        bool: 是否为有效UUID格式
    """
    if not uuid_string:
        return False
    
    uuid_regex = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_regex, uuid_string.lower()))


def sanitize_input(text: str) -> str:
    """
    清理输入文本，移除潜在的危险字符
    
    Args:
        text: 输入文本
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 移除HTML标签
    import html
    text = html.escape(text)
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text