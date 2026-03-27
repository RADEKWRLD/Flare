FROM python:3.10-slim

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
# 安装 PaddleOCR 需要的系统依赖
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libgl1 \
    libxrender-dev \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（使用清华镜像加速）
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 修复 FlagEmbedding 中缺失的 Optional 导入
RUN sed -i '/^class BiTrainer/i from typing import Optional' /usr/local/lib/python3.10/site-packages/FlagEmbedding/BGE_M3/trainer.py

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p uploads/files uploads/images

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV HF_ENDPOINT=https://hf-mirror.com

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app.py"]