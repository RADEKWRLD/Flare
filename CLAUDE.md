# Flare — Claude Code Project Guide

## Project Summary

全栈 Todo + RAG 语义搜索应用。Backend: Flask + MongoDB + Redis + BGE-M3 + DeepSeek。Frontend: React 19 + Vite + Redux Toolkit。

架构文档详见 [ARCH.md](ARCH.md)。

## Development Commands

```bash
# Backend
cd Backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py                    # Waitress server on :5000

# Frontend
cd Frontend && npm install
npm run dev                      # Vite dev server on :5173
npm run build                    # Production build → dist/

# Docker
docker-compose up -d             # MongoDB + Redis + Backend + Frontend
docker-compose down
```

## Code Conventions

### Backend (Python)
- **命名**: snake_case（文件、函数、变量）
- **分层**: config → models → services → routes
- **装饰器模式**: 认证 `@token_required`、异常处理 `@handle_exceptions`、单例 `@singleton`
- **SSE 流式响应**: 使用 generator + `create_sse_response()` helper
- **配置**: `config/settings.py` 中的 dataclass，从环境变量读取

### Frontend (JavaScript/JSX)
- **命名**: camelCase（变量/函数）、PascalCase（组件）
- **状态管理**: Redux Toolkit `createSlice` + `createAsyncThunk`
- **API 请求**: 统一使用 `utils/axiosConfig.js` 的 axios 实例（自动附加 JWT）
- **路由**: React Router，受保护路由需要 token

## Key Files

| File | Purpose |
|------|---------|
| `Backend/app.py` | Flask app factory + 服务启动 |
| `Backend/config/database.py` | MongoDB & Redis 单例连接 |
| `Backend/config/settings.py` | 所有配置 dataclass |
| `Backend/services/vector_service.py` | 向量编码 + Redis 搜索 |
| `Backend/services/rag_service.py` | LangGraph RAG 管线 |
| `Backend/services/file_service.py` | 文件处理 + OCR |
| `Backend/utils/decorators.py` | 通用装饰器 |
| `Backend/utils/helpers.py` | SSE helper + 文件校验 |
| `Backend/utils/validators.py` | 输入校验函数 |
| `Frontend/src/App.jsx` | 路由配置 |
| `Frontend/src/store/authSlice.js` | 认证状态管理 |
| `Frontend/src/store/todosSlice.js` | Todo 状态管理 |
| `Frontend/src/utils/axiosConfig.js` | Axios 实例 + 拦截器 |
| `Frontend/src/pages/Search.jsx` | RAG 搜索 UI (SSE) |
| `Frontend/src/pages/Todo.jsx` | Markdown 编辑器 |

## Reusable Utilities (avoid reinventing)

- `@singleton` — 单例装饰器 (`Backend/utils/decorators.py`)
- `@token_required` — JWT 认证装饰器，注入 `current_user`
- `@handle_exceptions` — 统一异常捕获 + JSON 错误响应
- `create_sse_response()` — SSE 流式响应封装 (`Backend/utils/helpers.py`)
- `validate_email()`, `validate_password()`, `validate_username()` — 输入校验 (`Backend/utils/validators.py`)
- `validate_file()` — 文件类型 + 大小校验 (`Backend/utils/helpers.py`)
- `axiosInstance` — 带 JWT 拦截器的 axios 实例 (`Frontend/src/utils/axiosConfig.js`)

## Important Notes

- **环境变量**: 必须配置 `.env`（MONGODB_URI, REDIS_HOST, SECRET_KEY, DEEPSEEK_API_KEY, MODEL_NAME 等）
- **文件上传限制**: 最大 200MB / 单次最多 10 个文件
- **Redis 索引**: `vector_index`（HNSW 向量）和 `content_index`（内容缓存），启动时自动创建
- **MongoDB 索引**: users 表 username/email 唯一索引；todos/todosContent 按 (user_id, created_at) 索引
- **JWT**: HS256 算法，24 小时过期，前端 401 自动登出
- **SSE**: 搜索和内容加载使用 Server-Sent Events 流式传输
