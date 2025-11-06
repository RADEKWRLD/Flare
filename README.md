# Flare - 多模态私有化文档管理系统

**基于 RAG 的智能文档管理与 AI 问答系统**

[![React](https://img.shields.io/badge/React-19.1.0-blue.svg)](https://reactjs.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green.svg)](https://www.mongodb.com/)
[![Redis](https://img.shields.io/badge/Redis-Stack-red.svg)](https://redis.io/)

## 📋 项目概述

**Flare** 是一个文档管理系统，结合了待办事项管理、Markdown 编辑、多模态文件处理和 AI 驱动的语义搜索功能。系统采用 **Flask + React** 全栈架构，项目解耦，添加规范化代码格式，集成 **BGE-M3 向量模型**和 **DeepSeek 大语言模型**，实现了完整的 RAG系统。

### 核心功能

- 📝 **智能文档编辑**: 支持 Markdown 语法、代码高亮、数学公式渲染
- 🤖 **AI 语义搜索**: RAG 系统驱动的智能问答，流式输出实时响应
- 📂 **多模态文件处理**: 支持图片 OCR 识别、PDF/Word 文档解析
- ⚡ **高性能架构**: Redis + MongoDB 两级缓存，SSE 流式传输
- 🔐 **安全认证**: JWT Token 认证，完善的权限控制
- 🎨 **现代化 UI**: GSAP 动画效果，流畅的用户体验

---

## 🏗️ 技术架构

### 技术栈总览

#### 后端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| **Flask** | 3.0.3 | Web 框架 |
| **MongoDB** | 7.0 | 文档数据库 |
| **Redis Stack** | Latest | 缓存 + 向量存储 |
| **BGE-M3** | 1.2.10 | 向量嵌入模型（1024维） |
| **DeepSeek** | - | 大语言模型 |
| **LangGraph** | 0.2.26 | RAG 流程编排 |
| **PaddleOCR** | 2.7.0+ | OCR 文字识别 |
| **PyMuPDF** | 1.23.8 | PDF 解析 |
| **Waitress** | 2.1.2 | 生产服务器 |

#### 前端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 19.1.0 | UI 框架 |
| **Vite** | 7.0.4 | 构建工具 |
| **Redux Toolkit** | 2.8.2 | 状态管理 |
| **React Router** | 7.7.1 | 路由管理 |
| **Axios** | 1.11.0 | HTTP 客户端 |
| **GSAP** | 3.13.0 | 动画库 |
| **CodeMirror** | - | Markdown 编辑器 |
| **react-markdown** | - | Markdown 渲染 |

### 系统架构图
<img width="1919" height="1079" alt="Index" src="https://github.com/user-attachments/assets/707d64fd-a6e9-493e-af89-9530fe2d75bb" />

<img width="1919" height="1079" alt="RAG" src="https://github.com/user-attachments/assets/ad19a8a8-26e7-4211-b53d-dd1de231ae13" />


---

## ✨ 核心技术亮点

### 1. RAG（检索增强生成）系统

#### 技术实现
- **LangGraph 状态编排**: 使用 `StateGraph` 设计模式，将检索（retrieve）和生成（generate）解耦
- **BGE-M3 向量模型**: 1024维多语言向量，支持中英文混合语义检索
- **DeepSeek 流式生成**: SSE（Server-Sent Events）实时推送 AI 回答
- **热数据缓存**：Redis返回文档流热数据，减少等待时间
- **内存开销调优**：设置RedisTTL，节约内存空间

#### 性能指标

使用RedisVectorSearch，采用HNSW算法，同时做布尔/字段过滤和向量搜索，并对结果过滤

在未做调优前，500个内容查询向量时间：

<img width="446" height="209" alt="Before" src="https://github.com/user-attachments/assets/178b029c-49a2-4186-ba8f-d0977e35f19c" />


经过调优后，1万个内容查询向量时间：

<img width="443" height="214" alt="After" src="https://github.com/user-attachments/assets/ab575bc7-72de-4d0d-87a0-d37eee7d553f" />


同时纯向量检索优化至2ms区间：

<img width="402" height="78" alt="Retrive" src="https://github.com/user-attachments/assets/d1af7ac3-68e6-44dd-aec3-46fb247c8e5f" />


---

### 2. 向量检索优化

#### 架构设计
```python
# services/vector_service.py
- 单例模式管理向量模型（避免重复加载 2GB 模型）
- Float32 精度优化：向量序列化为 bytes
- Redis Hash 存储：替代 MongoDB，速度提升 80%
- TTL 过期策略：向量数据 3 天自动过期
```

#### 性能对比
| 指标 | MongoDB | Redis Hash | 提升 |
|------|---------|-----------|------|
| 检索延迟 | 200ms | 2ms | **90% ↓** |
| 向量生成 | 500ms/文本 | 150ms/文本（批量） | **70% ↓** |
| 内存占用 | 8KB/向量 | 4KB/向量 | **50% ↓** |

#### RedisSearch 向量索引
```python
# config/database.py
VectorField(
    "vector",
    "HNSW",  # 高性能近似搜索算法
    {
        "TYPE": "FLOAT32",
        "DIM": 1024,
        "DISTANCE_METRIC": "COSINE",
        "M": 16,
        "EF_CONSTRUCTION": 200,
        "EF_RUNTIME": 10
    }
)
```

---

### 3. SSE 流式传输与缓存优化

#### 两级缓存策略
```
用户请求 → Redis 缓存（立即返回 10ms）
          ↓
      MongoDB 查询（异步加载 200ms）
          ↓
      对比差异 → 推送更新 → 结束标记
```

#### SSE 事件流设计
```javascript
event: cache      // 缓存命中状态
event: data       // 流式推送内容
event: cache_end  // 缓存数据结束
event: update     // 数据已更新通知
event: end        // 数据流结束
```

#### 性能优势
- ⚡ **首屏响应**: 10ms（Redis 缓存）
- 🎯 **完整渲染**: 50ms（缓存命中） / 200ms（数据库回源）
- 📉 **缓存命中率**: 85%+

---

### 4. 多模态文件处理

#### 支持格式
- **图片**: PNG, JPG, JPEG, GIF（OCR 识别）
- **文档**: PDF, DOCX, XLSX, XLS, MD

#### 技术实现
```python
# services/file_service.py
1. OCR 识别：PaddleOCR 处理图片文字
2. PDF 解析：PyMuPDF 高效提取文本
3. DOCX 解析：docx2txt 解析 Word 文档
4. 流式传输：8KB 分块读取，避免内存溢出
```

#### 安全防护
- ✅ 路径遍历防护：`os.path.normpath()` 规范化路径
- ✅ 文件类型白名单：严格限制上传格式
- ✅ 文件大小限制：200MB 上传限制
- ✅ 中文文件名处理：URL 编码/解码

---

### 5. 前端性能优化

#### React 优化策略
```javascript
// 1. Redux Toolkit 状态管理
- createSlice 自动生成 actions
- createAsyncThunk 简化异步逻辑
- Immer 内置实现不可变状态

// 2. 乐观更新
先更新 UI → 发送请求 → 失败回滚

// 3. SSE 实时推送
替代轮询，减少 90% 无效请求

// 4. Blob URL 缓存
图片下载一次，本地缓存复用
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.13+
- **Node.js**: 18+
- **Docker**: 20.10+ (可选)
- **MongoDB**: 7.0+
- **Redis**: Redis Stack

### 本地开发

#### 1. 克隆项目
```bash
git clone https://github.com/yourusername/flare.git
cd flare
```

#### 2. 后端启动
```bash
cd Backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置环境变量（创建 .env 文件）
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=todo_app
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
SECRET_KEY=your-secret-key
DEEPSEEK_API_KEY=your-deepseek-api-key
MODEL_NAME=./bge-m3  # 本地模型路径
HF_ENDPOINT=https://hf-mirror.com

# 启动服务
python app.py
```

#### 3. 前端启动
```bash
cd Frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 `http://localhost:3000` 即可使用。

---

### Docker 部署（推荐）

#### 1. 下载向量模型（⚠️ 必需步骤）

> **重要说明**：由于 BGE-M3 模型文件较大（约 2.5GB），且单文件超过 GitHub 的 2GB 限制，**模型文件未包含在仓库中**，需要手动下载。

```bash
cd Backend

# 安装 Hugging Face Hub 工具
pip install huggingface-hub

# 下载模型到 bge-m3 目录（使用镜像加速）
huggingface-cli download BAAI/bge-m3 --local-dir bge-m3 --endpoint https://hf-mirror.com
```

**下载说明**：
- 📦 **模型大小**: 约 2.5GB
- ⏱️ **下载时间**: 5-10 分钟（取决于网速）
- 🌐 **镜像加速**: 使用 `https://hf-mirror.com` 加速下载
- 📁 **目标路径**: `Backend/bge-m3/`

**验证模型下载**：
```bash
# 检查模型文件是否存在
ls Backend/bge-m3/

# 应该看到以下文件：
# - pytorch_model.bin (主模型文件，约 2GB)
# - config.json
# - tokenizer.json
# - 其他配置文件
```

#### 2. 修改配置

**修改 `Backend/config/settings.py`**：
```python
model_name:str = os.getenv('MODEL_NAME', './bge-m3')  # 使用本地模型
```

**修改 `docker-compose.yml`**：
```yaml
environment:
  - MODEL_NAME=./bge-m3  # 使用本地模型
```

#### 3. 构建并启动
```bash
# 停止旧容器（如果有）
docker-compose down

# 构建镜像
docker-compose build backend

# 启动所有服务
docker-compose up -d
```

#### 4. 验证部署
```bash
# 检查容器状态
docker-compose ps

# 查看后端日志（应看到 "向量模型加载成功"）
docker-compose logs -f backend

# 访问前端
浏览器打开：http://localhost:80
```

**预期日志输出**：
```
flare-backend | MongoDB连接成功
flare-backend | Redis客户端连接成功
flare-backend | 向量模型加载成功  ← 看到这行表示模型加载成功
flare-backend |  * Running on http://0.0.0.0:5000
```

---

### 模型文件说明

#### 为什么模型文件不在仓库中？

1. **文件过大**: BGE-M3 模型约 2.5GB，超过 GitHub 单文件 2GB 限制
2. **仓库精简**: AI 模型不应该直接存储在代码仓库中
3. **版本管理**: 模型可以独立更新，不影响代码版本
4. **最佳实践**: 业界标准做法是从模型托管平台下载

#### 模型下载失败怎么办？

**方案 1: 使用官方源（慢）**
```bash
huggingface-cli download BAAI/bge-m3 --local-dir bge-m3
```

**方案 2: 手动下载**
1. 访问 [Hugging Face Model Hub](https://huggingface.co/BAAI/bge-m3)
2. 下载所有文件到 `Backend/bge-m3/` 目录
3. 确保目录结构正确

**方案 3: 使用其他镜像**
```bash
# 使用阿里云镜像
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download BAAI/bge-m3 --local-dir bge-m3
```

#### 模型文件列表

下载完成后，`Backend/bge-m3/` 目录应包含：

```
bge-m3/
├── 1_Pooling/
│   └── config.json
├── pytorch_model.bin        # 主模型文件 (~2GB)
├── config.json              # 模型配置
├── tokenizer.json           # 分词器
├── sentencepiece.bpe.model  # 词表文件
├── special_tokens_map.json
├── tokenizer_config.json
└── modules.json
```

---

## 📂 项目总结构

```
Flare/
├── Backend/                 # 后端服务
│   ├── config/              # 配置层
│   │   ├── database.py      # 数据库连接配置
│   │   └── settings.py      # 环境变量配置
│   ├── models/              # 数据模型层
│   │   ├── base.py          # 基础模型类
│   │   ├── user.py          # 用户模型
│   │   └── todo.py          # Todo 模型
│   ├── services/            # 业务逻辑层
│   │   ├── auth_service.py  # 认证服务
│   │   ├── cache_service.py # 缓存服务
│   │   ├── vector_service.py# 向量服务
│   │   ├── rag_service.py   # RAG 服务
│   │   └── file_service.py  # 文件服务
│   ├── routes/              # 路由层
│   │   ├── auth_routes.py   # 认证路由
│   │   ├── todo_routes.py   # Todo 路由
│   │   └── search_routes.py # 搜索路由
│   ├── utils/               # 工具层
│   │   ├── decorators.py    # 装饰器（认证、异常处理）
│   │   ├── helpers.py       # 辅助函数
│   │   └── validators.py    # 数据验证
│   ├── bge-m3/              # 向量模型（本地）
│   ├── uploads/             # 文件上传目录
│   ├── app.py               # 应用入口
│   ├── requirements.txt     # Python 依赖
│   └── Dockerfile           # Docker 构建文件
├── Frontend/                # 前端服务
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   │   ├── Login.jsx    # 登录页
│   │   │   ├── Register.jsx # 注册页
│   │   │   ├── Layout.jsx   # 布局容器
│   │   │   ├── Newpage.jsx  # 新建文档页
│   │   │   ├── Todo.jsx     # 文档详情页
│   │   │   └── Search.jsx   # AI 搜索页
│   │   ├── component/       # 可复用组件
│   │   │   └── Navbar.jsx   # 侧边导航栏
│   │   ├── store/           # Redux 状态管理
│   │   │   ├── authSlice.js # 认证状态
│   │   │   └── todosSlice.js# 文档状态
│   │   ├── utils/           # 工具函数
│   │   │   ├── axiosConfig.js # Axios 配置
│   │   │   └── store.js     # Redux Store
│   │   └── main.jsx         # 应用入口
│   ├── package.json         # npm 依赖
│   ├── vite.config.js       # Vite 配置
│   ├── nginx.conf           # Nginx 配置
│   └── Dockerfile           # Docker 构建文件
├── docker-compose.yml       # Docker 编排文件
├── README.md                # 项目文档
```

---

## 📊 性能数据

并发性能

- **QPS**: 500+ (Waitress 32线程)

- **并发用户**: 1000+ (压测数据)

- **平均响应时间**: < 200ms

- **P99 响应时间**: < 500ms

  

---

## 🔐 安全措施

### 后端安全

- ✅ JWT Token 认证
- ✅ 路径遍历防护
- ✅ 文件类型白名单
- ✅ SQL 注入防护（参数化查询）
- ✅ XSS 防护（输入转义）
- ✅ CORS 配置

### 前端安全

- ✅ Token 自动过期检测
- ✅ 401 响应自动登出
- ✅ 文件下载需携带 Token
- ✅ Blob URL 隐藏真实路径
- ✅ React 自动转义

---

## 📈 未来优化方向

### 功能扩展

- [ ] 文档协作编辑（WebSocket）
- [ ] 版本历史记录
- [ ] 导出为 PDF/Word
- [ ] 暗黑模式切换
- [ ] 文档标签分类
- [ ] 全文搜索（Elasticsearch）

### 技术升级

- [ ] 迁移到 TypeScript
- [ ] React Query 优化数据获取
- [ ] Service Worker 离线缓存
- [ ] 虚拟滚动优化长列表
- [ ] GraphQL API
- [ ] 微服务化改造

### 性能优化

- [ ] 图片懒加载
- [ ] 代码分割（React.lazy）
- [ ] CDN 加速静态资源
- [ ] Gzip/Brotli 压缩
- [ ] 数据库读写分离
- [ ] Redis 集群

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 代码规范

- 后端遵循 PEP 8 规范
- 前端使用 ESLint 检查
- 提交信息遵循 Conventional Commits

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

<div align="center">
**Built with ❤️ using React + Flask**

[⬆ 回到顶部](#flare---智能todo管理系统)

</div>

