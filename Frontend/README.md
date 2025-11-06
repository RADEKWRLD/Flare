# 前端生产环境部署指南

## 环境配置说明

本项目支持开发和生产两种环境配置：

- **开发环境**: 使用 `http://localhost:5000/api`
- **生产环境**: 使用相对路径 `/api`，由 nginx 代理转发

## 本地构建生产版本

```bash
# 进入前端目录
cd Frontend

# 安装依赖
npm install

# 启动项目
npm run dev

# 构建生产版本
npm run build

# 预览生产版本（可选）
npm run preview
```

构建后的文件将在 `dist` 目录中。

## Docker 部署方式

### 1. 单独构建前端镜像

```bash
# 在 Frontend 目录下
docker build -t flare-frontend:latest .
```

### 2. 运行前端容器

```bash
docker run -d \
  --name flare-frontend \
  -p 80:80 \
  flare-frontend:latest
```

### 3. 使用 docker-compose 部署（推荐）

更新项目根目录的 `docker-compose.yml`，然后运行：

```bash
# 在项目根目录
docker-compose up -d
```

## Nginx 配置说明

`nginx.conf` 文件包含以下配置：

1. **静态文件服务**: 服务前端构建后的文件
2. **SPA 路由支持**: 所有前端路由请求返回 `index.html`
3. **API 代理**: `/api/*` 请求转发到后端服务
4. **Gzip 压缩**: 优化传输性能
5. **静态资源缓存**: 优化加载速度

### 修改后端地址

如果你的后端不在 Docker 网络中，需要修改 `nginx.conf` 中的 `proxy_pass` 地址：

```nginx
location /api/ {
    # 修改为你的后端实际地址
    proxy_pass http://your-backend-host:5000/api/;
    # ...
}
```

## 生产环境部署检查清单

- [ ] 确认 `.env.production` 配置正确
- [ ] 修改 `nginx.conf` 中的后端地址
- [ ] 构建并测试 Docker 镜像
- [ ] 配置 HTTPS（生产环境推荐）
- [ ] 配置域名和 DNS
- [ ] 设置环境变量（如需要）
- [ ] 配置日志和监控
