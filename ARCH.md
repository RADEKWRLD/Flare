# Flare Architecture

## Overview

Flare 是一个全栈 Todo + RAG 语义搜索应用。用户可以创建笔记（支持 Markdown、图片、文件附件），系统通过向量化存储实现基于语义的智能检索，并结合 LLM 生成回答。

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | Flask 3.0 + Waitress (WSGI, 32 threads) |
| Frontend Framework | React 19 + Vite 7 |
| Database | MongoDB 7.0 |
| Cache & Vector Store | Redis Stack (HNSW index) |
| Embedding Model | BGE-M3 (1024-dim, multilingual) |
| LLM | DeepSeek API (streaming) |
| RAG Framework | LangGraph (StateGraph: retrieve → generate) |
| OCR | PaddleOCR (中英文) |
| State Management | Redux Toolkit |
| Markdown Editor | CodeMirror 6 |
| Animation | GSAP |
| Deployment | Docker Compose |

## Directory Structure

```
Flare/
├── Backend/
│   ├── config/
│   │   ├── database.py         # MongoDB & Redis 单例客户端
│   │   └── settings.py         # 环境变量 + dataclass 配置
│   ├── models/
│   │   ├── base.py             # BaseModel 抽象类
│   │   ├── user.py             # 用户模型
│   │   └── todo.py             # Todo + TodoContent 模型
│   ├── services/
│   │   ├── auth_service.py     # JWT 认证、注册、登录
│   │   ├── vector_service.py   # BGE-M3 编码 + Redis 向量搜索
│   │   ├── rag_service.py      # LangGraph RAG 管线 + DeepSeek
│   │   ├── file_service.py     # 文件上传、OCR、文档解析
│   │   └── cache_service.py    # Redis 缓存
│   ├── routes/
│   │   ├── auth_routes.py      # /api/register, /api/login
│   │   ├── todo_routes.py      # Todo CRUD + 内容管理
│   │   └── search_routes.py    # /api/search (SSE streaming)
│   ├── utils/
│   │   ├── decorators.py       # @token_required, @handle_exceptions, @singleton
│   │   ├── helpers.py          # SSE 响应、文件校验
│   │   └── validators.py       # 邮箱、密码、用户名校验
│   ├── uploads/                # 用户上传文件存储
│   ├── app.py                  # Flask app factory + Waitress 启动
│   ├── requirements.txt
│   └── Dockerfile
├── Frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx       # 登录页 (GSAP 动画)
│   │   │   ├── Register.jsx    # 注册页
│   │   │   ├── Layout.jsx      # 主布局 + 侧边栏
│   │   │   ├── Newpage.jsx     # 新建 Todo
│   │   │   ├── Todo.jsx        # Markdown 编辑器页
│   │   │   └── Search.jsx      # RAG 搜索页 (SSE)
│   │   ├── component/
│   │   │   └── Navbar.jsx      # 侧边栏导航
│   │   ├── store/
│   │   │   ├── authSlice.js    # 认证状态
│   │   │   └── todosSlice.js   # Todo 列表状态
│   │   ├── utils/
│   │   │   ├── axiosConfig.js  # Axios 实例 + JWT 拦截器
│   │   │   └── store.js        # Redux store
│   │   ├── main.jsx            # 入口
│   │   └── App.jsx             # 路由配置
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml          # 编排: MongoDB + Redis + Backend + Frontend
├── ARCH.md
├── CLAUDE.md
└── README.md
```

## Architecture Layers

### Backend: config → models → services → routes

```
HTTP Request
  → routes/ (Flask Blueprint, 参数校验, @token_required)
    → services/ (业务逻辑)
      → models/ (MongoDB CRUD)
      → config/ (DB 连接, 环境配置)
  → HTTP Response / SSE Stream
```

### Frontend: pages → components → store

```
User Interaction
  → pages/*.jsx (页面组件)
    → component/*.jsx (复用组件)
    → store/*Slice.js (Redux 状态 + Async Thunk)
      → utils/axiosConfig.js (API 请求)
  → UI Update
```

## Core Data Flows

### 1. Authentication

```
Register/Login → AuthService → UserModel (MongoDB)
  → bcrypt hash/verify → JWT token (HS256, 24h)
  → Frontend: localStorage + Redux + Axios interceptor
```

### 2. Todo Content Creation

```
用户输入内容 + 上传文件
  → FileService: 图片 OCR / PDF·Word·Excel 文本提取
  → TodoContentModel: 存入 MongoDB
  → VectorService: BGE-M3 编码 → Redis HNSW 索引 (TTL 3 天)
  → CacheService: Redis 缓存 (TTL 1 小时)
```

### 3. RAG Search

```
用户提问
  → SearchRoute (SSE stream)
  → RAGService (LangGraph StateGraph):
    ├─ retrieve: BGE-M3 编码 query → Redis KNN (top_k×3) → 过滤 user_id → MongoDB 取内容
    └─ generate: 拼接上下文 + prompt → DeepSeek streaming → SSE 逐块返回
  → Frontend EventSource 实时渲染
```

## Database Schema

### MongoDB

| Collection | Key Fields |
|-----------|-----------|
| `users` | id (UUID), username (unique), email (unique), password (bcrypt), created_at |
| `todos` | id (UUID), user_id, title, created_at; Index: (user_id, created_at) |
| `todosContent` | todo_id, user_id, content, extracted_content {ocr_texts, file_texts}, images[], files[], complete, created_at |

### Redis

| Key Pattern | Type | TTL | Purpose |
|------------|------|-----|---------|
| `vector:{doc_id}` | Hash (doc_id, user_id, text, raw, vector bytes) | 3 days | HNSW 向量索引 |
| `content:{user_id}:{todo_id}` | JSON string | 1 hour | 内容缓存 |

HNSW Index: 1024-dim, COSINE distance, M=16, EF_CONSTRUCTION=200, EF_RUNTIME=10

## API Endpoints

### Auth
- `POST /api/register` — 用户注册
- `POST /api/login` — 用户登录 → JWT

### Todo
- `GET /api/todos` — 获取用户 Todo 列表
- `POST /api/todos` — 创建 Todo
- `PUT /api/todos/{todo_id}` — 更新标题
- `DELETE /api/todos/{todo_id}` — 删除 Todo + 关联内容
- `POST /api/todos/{todo_id}/contents` — 添加内容（支持文件上传）
- `GET /api/todos/{todo_id}/contents` — 获取内容（SSE）
- `PUT /api/todos/{todo_id}/contents/{content_id}` — 更新内容
- `DELETE /api/todos/{todo_id}/contents/{content_id}` — 删除内容

### Search
- `GET/POST /api/search` — RAG 语义搜索 (SSE stream)

## Deployment

```bash
# Docker 一键部署
docker-compose up -d

# 服务端口
# MongoDB: 27017
# Redis:   6379
# Backend: 5000
# Frontend: 80 (Nginx → SPA + API proxy)
```
