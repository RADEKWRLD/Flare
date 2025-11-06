# Todo路由模块，处理Todo相关的所有路由
import os
import time
import json
import traceback
from flask import Blueprint, request, jsonify, Response, stream_with_context
from bson import ObjectId
from models.todo import TodoModel, TodoContentModel
from services.file_service import FileService
from services.vector_service import VectorService
from services.cache_service import CacheService
from utils.decorators import token_required, handle_exceptions
from utils.helpers import create_sse_response, stream_todo_contents
from urllib.parse import unquote, quote

# 创建Todo蓝图
todo_bp = Blueprint('todo', __name__, url_prefix='/api')

# 初始化模型和服务
todo_model = TodoModel()
content_model = TodoContentModel()
file_service = FileService()
vector_service = VectorService()
cache_service = CacheService()


@todo_bp.route('/todos', methods=['GET'])
@handle_exceptions
@token_required
def get_todos(current_user):
    """
    获取用户的所有Todo列表
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        成功: [Todo列表], 200
        失败: {"message": "错误信息"}, 500
    """
    todos = todo_model.get_user_todos(current_user['id'])
    return jsonify(todos), 200


@todo_bp.route('/todos', methods=['POST'])
@handle_exceptions
@token_required
def add_todo(current_user):
    """
    创建新的Todo
    
    请求头:
        Authorization: Bearer <token>
    
    请求体:
        {
            "title": "Todo标题"
        }
    
    返回:
        成功: Todo对象, 201
        失败: {"message": "错误信息"}, 400
    """
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求体不能为空"}), 400
    
    title = data.get('title', '').strip()
    
    success, message, todo_data = todo_model.create_todo(current_user['id'], title)
    
    if success:
        return jsonify(todo_data), 201
    else:
        return jsonify({"message": message}), 400


@todo_bp.route('/todos/<todo_id>', methods=['PUT'])
@handle_exceptions
@token_required
def update_todo(current_user, todo_id):
    """
    更新Todo标题
    
    请求头:
        Authorization: Bearer <token>
    
    请求体:
        {
            "title": "新标题"
        }
    
    返回:
        成功: 更新后的Todo对象, 200
        失败: {"message": "错误信息"}, 400/404
    """
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求体不能为空"}), 400
    
    title = data.get('title', '').strip()
    
    success, message, updated_todo = todo_model.update_todo(todo_id, current_user['id'], title)
    
    if success:
        return jsonify(updated_todo), 200
    else:
        status_code = 404 if "not found" in message.lower() else 400
        return jsonify({"message": message}), status_code


@todo_bp.route('/todos/<todo_id>', methods=['DELETE'])
@handle_exceptions
@token_required
def delete_todo(current_user, todo_id):
    """
    删除Todo及其所有相关内容、向量和文件
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        成功: {"message": "Todo deleted"}, 200
        失败: {"message": "错误信息"}, 404
    """
    try:
        # 获取Todo的所有内容，以便删除关联的文件
        success, message, contents = content_model.get_todo_contents(todo_id, current_user['id'])
        
        if success and contents:
            # 删除所有关联的文件
            for content in contents:
                # 删除图片文件
                for image_url in content.get('images', []):
                    try:
                        image_path = file_service.get_file_path(image_url, 'image')
                        file_service.delete_file(image_path)
                    except Exception as e:
                        print(f"删除图片文件失败 {image_url}: {e}")
                
                # 删除文档文件
                for file_url in content.get('files', []):
                    try:
                        file_path = file_service.get_file_path(file_url, 'file')
                        file_service.delete_file(file_path)
                    except Exception as e:
                        print(f"删除文档文件失败 {file_url}: {e}")
        
        # 删除向量数据
        vector_service.delete_by_todo_id(todo_id, current_user['id'])
        
        # 删除Todo和内容
        success, message = todo_model.delete_todo(todo_id, current_user['id'])
        
        if success:
            # 使缓存失效
            cache_service.invalidate_todo_cache(todo_id, current_user['id'])
            return jsonify({"message": "Todo deleted"}), 200
        else:
            return jsonify({"message": message}), 404
            
    except Exception as e:
        print(f"删除Todo异常: {traceback.format_exc()}")
        return jsonify({"message": f"删除失败: {str(e)}"}), 500


@todo_bp.route('/todos/content/<todo_id>', methods=['POST'])
@handle_exceptions
@token_required
def add_todos_content(current_user, todo_id):
    """
    添加Todo内容（支持文字、图片、文件）
    
    请求头:
        Authorization: Bearer <token>
    
    表单数据:
        content: 文字内容
        images: 图片文件列表
        files: 文档文件列表
    
    返回:
        成功: {"message": "内容添加成功", "data": 内容对象}, 201
        失败: {"error": "错误信息"}, 400/500
    """
    try:
        # 获取文字内容
        content_text = request.form.get('content', '').strip()
        
        # 获取上传的文件
        images = request.files.getlist('images')
        files = request.files.getlist('files')
        
        # 验证至少有一种内容
        if not content_text and len(images) == 0 and len(files) == 0:
            return jsonify({"message": "至少需要文字或文件"}), 400
        
        # 处理文件上传
        uploaded_images = []
        uploaded_files = []
        ocr_texts = []     
        file_texts = []    
        
        if images or files:
            success, message, img_urls, file_urls, ocr_list, file_list = file_service.process_uploaded_files(images, files)
            if not success:
                return jsonify({"error": message}), 400
            
            uploaded_images = img_urls
            uploaded_files = file_urls
            ocr_texts = ocr_list
            file_texts = file_list
        
        # 添加Todo内容（分离存储）
        success, message, content_data = content_model.create_content(
            todo_id, 
            current_user['id'], 
            content_text,  # 用户输入
            uploaded_images, 
            uploaded_files,
            ocr_texts,     # OCR文本列表
            file_texts     # 文档文本列表
        )
        
        if not success:
            return jsonify({"message": message}), 400
        
        # 保存向量嵌入（合并所有文本用于搜索）
        all_text_parts = []
        if content_text:
            all_text_parts.append(content_text)
        if ocr_texts:
            all_text_parts.extend(ocr_texts)
        if file_texts:
            all_text_parts.extend(file_texts)
        
        full_text = "\n\n".join(all_text_parts).strip()
        
        if full_text:
            try:
                vector_service.save_embedding(
                    doc_id=content_data["_id"],
                    user_id=current_user["id"],
                    text=full_text,  # 合并后的完整文本
                    raw_data={
                        "images": uploaded_images, 
                        "files": uploaded_files,
                        "has_ocr": len(ocr_texts) > 0,
                        "has_file_text": len(file_texts) > 0
                    }
                )
            except Exception as e:
                print(f"向量保存失败: {e}")
                # 向量保存失败不影响内容保存
        
        # 使缓存失效
        cache_service.invalidate_todo_cache(todo_id, current_user['id'])
        
        return jsonify({"message": "内容添加成功", "data": content_data}), 201
        
    except Exception as e:
        print(f"添加内容异常: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@todo_bp.route('/todos/content/<todo_id>', methods=['GET'])
@handle_exceptions
@token_required
def get_todos_content(current_user, todo_id):
    """
    获取Todo的所有内容（SSE流式返回）
    先从Redis缓存快速返回，然后从MongoDB加载完整数据
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        SSE流式数据
        event: cache - 缓存数据
        event: data - 数据库数据
        event: end - 结束标记
        event: error - 错误信息
    """
    def generate():
        try:
            cache_hit = False
            
            # 第一步：尝试从Redis缓存获取
            cached_contents = cache_service.get_todo_contents_cache(todo_id, current_user['id'])
            
            if cached_contents:
                cache_hit = True
                # 发送缓存标记
                yield f"event: cache\ndata: {json.dumps({'hit': True, 'count': len(cached_contents)}, ensure_ascii=False)}\n\n"
                
                # 流式发送缓存内容
                for content in cached_contents:
                    yield f"event: data\ndata: {json.dumps(content, ensure_ascii=False)}\n\n"
                    # time.sleep(0.01)  # 快速推送缓存数据
                
                # 发送缓存结束标记
                yield f"event: cache_end\ndata: {json.dumps({'message': '缓存数据加载完成'}, ensure_ascii=False)}\n\n"
            else:
                # 缓存未命中
                yield f"event: cache\ndata: {json.dumps({'hit': False}, ensure_ascii=False)}\n\n"
            
            # 第二步：从MongoDB获取最新数据
            success, message, db_contents = content_model.get_todo_contents(todo_id, current_user['id'])
            
            if not success:
                yield f"event: error\ndata: {json.dumps({'message': message}, ensure_ascii=False)}\n\n"
                return
            
            # 如果数据库数据与缓存不同，发送更新
            if not cache_hit or json.dumps(db_contents, sort_keys=True) != json.dumps(cached_contents, sort_keys=True):
                if cache_hit:
                    # 如果有缓存但数据不同，发送更新标记
                    yield f"event: update\ndata: {json.dumps({'message': '数据已更新'}, ensure_ascii=False)}\n\n"
                
                # 流式发送数据库内容
                for content in db_contents:
                    yield f"event: data\ndata: {json.dumps(content, ensure_ascii=False)}\n\n"
                    time.sleep(0.02)  # 控制推流节奏
                
                # 更新Redis缓存
                cache_service.set_todo_contents_cache(todo_id, current_user['id'], db_contents)
                yield f"event: cache_updated\ndata: {json.dumps({'message': '缓存已更新'}, ensure_ascii=False)}\n\n"
            else:
                # 数据一致，无需重新发送
                yield f"event: sync\ndata: {json.dumps({'message': '数据已同步'}, ensure_ascii=False)}\n\n"
            
            # 发送结束标记
            yield f"event: end\ndata: {json.dumps({'message': 'DONE', 'total': len(db_contents)}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            print(f"获取内容异常: {traceback.format_exc()}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@todo_bp.route('/todos/content/<content_id>', methods=['PUT'])
@handle_exceptions
@token_required
def update_todos_content(current_user, content_id):
    """
    更新Todo内容
    
    请求头:
        Authorization: Bearer <token>
    
    请求体:
        {
            "content": "新内容",
            "images": ["图片URL列表"],
            "files": ["文件URL列表"]
        }
    
    返回:
        成功: 更新后的内容对象, 200
        失败: {"message": "错误信息"}, 404
    """
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求体不能为空"}), 400
    
    update_fields = {}
    
    # 获取原始内容以获取todo_id
    original_content = content_model.find_content_by_id(content_id, current_user['id'])
    if not original_content:
        return jsonify({"message": "找不到Todo内容"}), 404
    
    todo_id = original_content.get('todo_id')
    
    # 更新文字内容
    if 'content' in data:
        update_fields['content'] = data['content']
        
        # 如果更新了文字内容，需要更新向量
        try:
            vector_service.update_embedding(
                doc_id=content_id,
                user_id=current_user["id"],
                text=data['content'],
                raw_data={
                    "images": original_content.get("images", []),
                    "files": original_content.get("files", [])
                }
            )
        except Exception as e:
            print(f"向量更新失败: {e}")
    
    # 更新图片和文件
    if 'images' in data:
        update_fields['images'] = data['images']
    
    if 'files' in data:
        update_fields['files'] = data['files']
    
    # 执行更新
    success, message, updated_content = content_model.update_content(
        content_id, current_user['id'], update_fields
    )
    
    if success:
        # 使缓存失效
        if todo_id:
            cache_service.invalidate_todo_cache(todo_id, current_user['id'])
        return jsonify(updated_content), 200
    else:
        return jsonify({"message": message}), 404


@todo_bp.route('/todos/content/<content_id>', methods=['DELETE'])
@handle_exceptions
@token_required
def delete_todo_content(current_user, content_id):
    """
    删除Todo内容及其关联的文件
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        成功: {"message": "内容已删除"}, 200
        失败: {"message": "错误信息"}, 404
    """
    try:
        # 获取内容以获取todo_id和文件信息
        content = content_model.find_content_by_id(content_id, current_user['id'])
        
        if not content:
            return jsonify({"message": "找不到内容"}), 404
        
        todo_id = content.get('todo_id')
        
        # 删除关联的图片文件
        for image_url in content.get('images', []):
            try:
                image_path = file_service.get_file_path(image_url, 'image')
                file_service.delete_file(image_path)
            except Exception as e:
                print(f"删除图片文件失败 {image_url}: {e}")
        
        # 删除关联的文档文件
        for file_url in content.get('files', []):
            try:
                file_path = file_service.get_file_path(file_url, 'file')
                file_service.delete_file(file_path)
            except Exception as e:
                print(f"删除文档文件失败 {file_url}: {e}")
        
        # 删除向量数据
        vector_service.delete_by_doc_id(content_id, current_user['id'])
        
        # 删除内容
        success, message = content_model.delete_content(content_id, current_user['id'])
        
        if success:
            # 使缓存失效
            if todo_id:
                cache_service.invalidate_todo_cache(todo_id, current_user['id'])
            return jsonify({"message": message}), 200
        else:
            return jsonify({"message": message}), 404
            
    except Exception as e:
        print(f"删除内容异常: {traceback.format_exc()}")
        return jsonify({"message": f"删除失败: {str(e)}"}), 500


@todo_bp.route('/todos/content/image/<path:imagename>', methods=['GET'])
@handle_exceptions
@token_required
def serve_image(current_user, imagename):
    """
    安全获取图片文件（HTTP流式返回）
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        图片文件流
    """
    try:
        # URL解码文件名（Flask已经自动解码了，但为了确保兼容性）
        decoded_imagename = unquote(imagename)
        
        # 使用规范化的路径
        file_path = file_service.get_file_path(f"/uploads/images/{decoded_imagename}", 'image')
        
        # 规范化文件路径（解决Windows路径问题）
        file_path = os.path.normpath(file_path)
        
        # 安全检查：确保文件路径在允许的目录内
        image_folder = os.path.normpath(file_service.image_folder)
        if not os.path.abspath(file_path).startswith(os.path.abspath(image_folder)):
            return jsonify({"message": "非法的文件路径"}), 403
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            # 尝试查找文件（有时编码问题会导致文件名不匹配）
            image_files = os.listdir(image_folder)
            for img_file in image_files:
                if img_file.startswith(decoded_imagename.split('_')[0]):
                    print(f"找到相似文件: {img_file}")
            return jsonify({"message": "图片不存在"}), 404
        
        def generate():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk
        
        # 根据文件扩展名设置正确的MIME类型
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }
        mimetype = mime_types.get(ext, 'image/png')
        
        return Response(generate(), mimetype=mimetype)
        
    except FileNotFoundError as e:
        print(f"FileNotFoundError: {e}")
        return jsonify({"message": "图片不存在"}), 404
    except Exception as e:
        print(f"获取图片异常: {traceback.format_exc()}")
        return jsonify({"message": f"获取图片失败: {str(e)}"}), 500


@todo_bp.route('/todos/content/file/<path:filename>', methods=['GET'])
@handle_exceptions
@token_required
def serve_file(current_user, filename):
    """
    安全获取文档文件（HTTP流式返回）
    
    请求头:
        Authorization: Bearer <token>
    
    返回:
        文档文件流
    """
    try:
        # URL解码文件名
        decoded_filename = unquote(filename)
        
        # 使用规范化的路径
        file_path = file_service.get_file_path(f"/uploads/files/{decoded_filename}", 'file')
        
        # 规范化文件路径
        file_path = os.path.normpath(file_path)
        
        # 安全检查
        file_folder = os.path.normpath(file_service.file_folder)
        if not os.path.abspath(file_path).startswith(os.path.abspath(file_folder)):
            return jsonify({"message": "非法的文件路径"}), 403
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return jsonify({"message": "文件不存在"}), 404
        
        def generate():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk
        
        # 设置文件下载头
        quoted_filename = quote(decoded_filename.encode('utf-8'))
        
        return Response(
            generate(),
            mimetype="application/octet-stream",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{quoted_filename}"
            }
        )
        
    except FileNotFoundError as e:
        print(f"FileNotFoundError: {e}")
        return jsonify({"message": "文件不存在"}), 404
    except Exception as e:
        print(f"获取文件异常: {traceback.format_exc()}")
        return jsonify({"message": f"获取文件失败: {str(e)}"}), 500