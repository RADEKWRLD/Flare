# 文件处理服务层，处理文件上传、OCR识别和文档解析
import os
from pydoc import text
import uuid
from typing import List, Tuple, Optional
from PIL import Image
import fitz  # PyMuPDF for PDF OCR识别
import docx2txt#DOCX文件解析
from paddleocr import PaddleOCR#图片中英文识别
from urllib.parse import quote, unquote
from config.settings import ai_config, app_config
import openpyxl#xlsx文件解析
import xlrd#xls文件解析

class FileService:
    """文件处理服务类"""
    
    # 允许的文件类型
    ALLOWED_IMAGE_EXTENSIONS = app_config.allowed_image_extensions
    ALLOWED_FILE_EXTENSIONS = app_config.allowed_file_extensions
    MAX_FILES_COUNT = app_config.max_file_count  # 每种文件类型最多上传数量
    
    def __init__(self):
        """初始化文件服务"""
        
        # 设置上传目录
        self.upload_folder = app_config.upload_folder
        self.max_file_size = app_config.max_file_size

        #设置PaddleOCR
        self.ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False)
        
        # 创建上传目录
        self.image_folder = os.path.join(self.upload_folder, 'images')
        self.file_folder = os.path.join(self.upload_folder, 'files')
        os.makedirs(self.image_folder, exist_ok=True)
        os.makedirs(self.file_folder, exist_ok=True)
    
    def allowed_image_file(self, filename: str) -> bool:
        """
        检查是否为允许的图片文件类型
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 是否允许
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.ALLOWED_IMAGE_EXTENSIONS
    
    def allowed_document_file(self, filename: str) -> bool:
        """
        检查是否为允许的文档文件类型
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 是否允许
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.ALLOWED_FILE_EXTENSIONS
    
    def validate_file_size(self, file) -> bool:
        """
        验证文件大小
        
        Args:
            file: 上传的文件对象
            
        Returns:
            bool: 是否符合大小限制
        """
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        return size <= self.max_file_size
    
    def save_uploaded_file(self, file, file_type: str) -> Tuple[str, str]:
        """
        保存上传的文件
        
        Args:
            file: 上传的文件对象
            file_type: 文件类型 ('image' 或 'file')
            
        Returns:
            Tuple[str, str]: (文件路径, URL路径)
        """
        if file_type == 'image':
            folder = self.image_folder
            url_prefix = "/uploads/images/"
        else:
            folder = self.file_folder
            url_prefix = "/uploads/files/"
        
        # 生成唯一文件名（保留原始中文文件名）
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(folder, filename)
        
        # 保存文件（使用原始文件名）
        file.save(file_path)
        
        # URL中使用编码后的文件名
        url_filename = quote(filename)
        return file_path, f"{url_prefix}{url_filename}"
    
    def process_image_ocr(self, image_path: str) -> str:
        """
        OCR图片识别文字
        
        Args:
            image_path: 图片路径
            
        Returns:
            str: 识别出的文字
        """
        try:
            result = self.ocr.predict(image_path)
            #提取文字
            texts = []

            # print(result)
            #提取文字和置信度
            # Bug修复：需要检查result是否为空或格式是否正确
            if not result or len(result) == 0:
                return ""
            
            ocr_text = result[0].get('rec_texts', [])
            ocr_confidence = result[0].get('rec_scores', [])
            
            for text,confidence in zip(ocr_text,ocr_confidence):
                if confidence > 0.5:
                    texts.append(text)
            full_text = '\n'.join(texts).strip()
            return full_text

        except Exception as e:
            raise ValueError(f"OCR处理失败: {e}")
            
    def process_pdf_file(self, file_path: str) -> str:
        """
        处理PDF文件，提取文本
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            str: 提取的文本
        """
        try:
            doc = fitz.open(file_path)
            texts = []
            for page in doc:
                texts.append(page.get_text())
            doc.close()
            return '\n'.join(texts)
        except Exception as e:
            print(f"PDF处理失败: {e}")
            return ""
    
    def process_docx_file(self, file_path: str) -> str:
        """
        处理DOCX文件，提取文本
        
        Args:
            file_path: DOCX文件路径
            
        Returns:
            str: 提取的文本
        """
        try:
            return docx2txt.process(file_path)
        except Exception as e:
            print(f"DOCX处理失败: {e}")
            return ""

    def process_excel_file(self, file_path: str, file_extension: str) -> str:
        """
        处理Excel文件，提取文本
        
        Args:
            file_path: Excel文件路径
            file_extension: 文件扩展名
            
        Returns:
            str: 提取的文本
        """
        try:
            texts = []

            if file_extension == 'xlsx':
                workbook = openpyxl.load_workbook(file_path, data_only=True)
                sheet = workbook.active
                for row in sheet.iter_rows(values_only=True):
                    for cell in row:
                        if cell is not None:
                            texts.append(str(cell))

            elif file_extension == 'xls':
                workbook = xlrd.open_workbook(file_path)
                sheet = workbook.sheet_by_index(0)
                for r in range(sheet.nrows):
                    for c in range(sheet.ncols):
                        value = sheet.cell_value(r, c)
                        if value != "":
                            texts.append(str(value))

            else:
                return ""

            return "\n".join(texts).strip()

        except Exception as e:
            print(f"Excel处理失败: {e}")
            return ""

    def process_markdown_file(self, file_path: str) -> str:
        """
        处理Markdown文件，提取文本
        
        Args:
            file_path: Markdown文件路径
            
        Returns:
            str: 提取的文本
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Markdown处理失败: {e}")
            return ""


    def extract_text_from_file(self, file_path: str, file_extension: str) -> str:
        """
        根据文件类型提取文本
        
        Args:
            file_path: 文件路径
            file_extension: 文件扩展名
            
        Returns:
            str: 提取的文本
        """
        ext = file_extension.lower()
        if ext == 'pdf':
            return self.process_pdf_file(file_path)
        elif ext == 'docx':
            return self.process_docx_file(file_path)
        elif ext == 'xlsx':
            return self.process_excel_file(file_path, ext)
        elif ext == 'xls':
            return self.process_excel_file(file_path, ext)
        elif ext == 'md':
            return self.process_markdown_file(file_path)
        else:
            return ""
    
    def process_uploaded_files(self, images, files) -> Tuple[bool, str, List[str], List[str], List[str], List[str]]:
        """
        处理上传的文件（图片和文档）
        
        Args:
            images: 上传的图片列表
            files: 上传的文档列表
            
        Returns:
            Tuple[bool, str, List[str], List[str], List[str], List[str]]: 
            (是否成功, 错误消息, 图片URL列表, 文件URL列表, OCR文本列表, 文档文本列表)
        """
        # 验证文件数量
        if len(images) > self.MAX_FILES_COUNT or len(files) > self.MAX_FILES_COUNT:
            return False, "每种文件类型最多只能上传10个", [], [], [], []
        
        uploaded_images = []
        uploaded_files = []
        ocr_texts = []     
        file_texts = []     
        
        try:
            # 处理图片文件
            for img in images:
                if img and self.allowed_image_file(img.filename):
                    # 验证文件大小
                    if not self.validate_file_size(img):
                        return False, f"图片 {img.filename} 超过200MB限制", [], [], [], []
                    
                    # 保存文件
                    file_path, url_path = self.save_uploaded_file(img, 'image')
                    uploaded_images.append(url_path)
                    
                    # OCR提取文字
                    text = self.process_image_ocr(file_path)
                    if text:
                        ocr_texts.append(text)
            
            # 处理文档文件
            for file in files:
                if file and self.allowed_document_file(file.filename):
                    # 验证文件大小
                    if not self.validate_file_size(file):
                        return False, f"文件 {file.filename} 超过200MB限制", [], [], [], []
                    
                    # 保存文件
                    file_path, url_path = self.save_uploaded_file(file, 'file')
                    uploaded_files.append(url_path)
                    
                    # 提取文档文本
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    text = self.extract_text_from_file(file_path, ext)
                    if text:
                        file_texts.append(text)
            
            return True, "文件处理成功", uploaded_images, uploaded_files, ocr_texts, file_texts
            
        except Exception as e:
            return False, f"文件处理失败: {str(e)}", [], [], [], []
    
    def get_file_path(self, url_path: str, file_type: str) -> str:
        """
        根据URL路径获取实际文件路径
        
        Args:
            url_path: URL路径（可能包含URL编码）
            file_type: 文件类型 ('image' 或 'file')
            
        Returns:
            str: 实际文件路径
        """
        if file_type == 'image':
            folder = self.image_folder
            prefix = "/uploads/images/"
        else:
            folder = self.file_folder
            prefix = "/uploads/files/"
        
        # 提取文件名并URL解码（因为URL中是编码的，但文件系统中是原始中文名）
        filename = url_path.replace(prefix, "")
        decoded_filename = unquote(filename)
        return os.path.join(folder, decoded_filename)

    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False