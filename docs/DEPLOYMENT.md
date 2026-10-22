# 部署指南

## 目录

- [方式一：Docker Compose（推荐）](#方式一docker-compose推荐)
- [方式二：手动部署](#方式二手动部署)
- [Nginx 反向代理（生产环境）](#nginx-反向代理)
- [HTTPS / SSL 配置](#https--ssl-配置)
- [PostgreSQL 切换](#postgresql-切换)
- [升级说明](#升级说明)
- [备份与恢复](#备份与恢复)

---

## 方式一：Docker Compose（推荐）

### 前置要求

- Docker >= 20.10
- Docker Compose v2
- 至少 2GB 可用内存
- 至少 2GB 磁盘空间

### 步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd geo-platform

# 2. 配置环境变量
cp .env.example .env
```

编辑 `.env`：

```bash
# 必须修改！使用强密码
API_KEY=your-strong-random-api-key-here

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=80

# 生产环境改为实际域名，多个域名用逗号分隔
CORS_ORIGINS=https://your-domain.com
```

```bash
# 3. 构建并启动
docker-compose up -d --build

# 4. 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 5. 验证服务
curl http://localhost:8000/health
# {"status":"ok","version":"2.0.0"}
```

启动后访问：
- **前端**：http://localhost（或配置的 FRONTEND_PORT）
- **后端 API 文档**：http://localhost:8000/docs

### Docker Compose 服务说明

| 服务 | 镜像 | 端口 | 数据持久化 |
|------|------|------|-----------|
| backend | `./backend/Dockerfile` | 8000 | `backend_data` 卷（数据库），`uploads` 卷（文件） |
| frontend | `./frontend/Dockerfile` | 80 | 无静态数据，构建后为纯静态文件 |

### 常用命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 重新构建（代码更新后）
docker-compose up -d --build

# 进入后端容器
docker-compose exec backend bash

# 手动执行数据库迁移
docker-compose exec backend alembic upgrade head
```

---

## 方式二：手动部署

适合需要更精细控制的场景。

### 后端

```bash
# 1. 安装 Python 3.10+
python3 --version

# 2. 进入后端目录
cd backend

# 3. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
export API_KEY=your-secret-key
export DATABASE_URL=sqlite+aiosqlite:///./data/app.db
export CORS_ORIGINS=https://your-domain.com

# 6. 运行迁移
mkdir -p data uploads
alembic upgrade head

# 7. 启动（使用 gunicorn/uvicorn 多 worker）
pip install uvicorn[standard]
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --loop uvloop \
  --http httptools
```

建议使用 systemd 管理进程：

```ini
# /etc/systemd/system/geo-backend.service
[Unit]
Description=GEO Platform Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/geo-platform/backend
Environment=API_KEY=your-secret-key
Environment=DATABASE_URL=sqlite+aiosqlite:////opt/geo-platform/backend/data/app.db
Environment=CORS_ORIGINS=https://your-domain.com
ExecStart=/opt/geo-platform/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable geo-backend
sudo systemctl start geo-backend
```

### 前端

```bash
# 1. 安装 Node.js 20+
node --version

# 2. 进入前端目录
cd frontend

# 3. 安装依赖
npm install

# 4. 配置 API 地址
echo "VITE_API_BASE_URL=https://your-domain.com/api/v1" > .env.production
echo "VITE_API_KEY=your-secret-key" >> .env.production

# 5. 构建
npm run build

# 6. dist/ 目录为静态文件，由 Nginx 托管
ls dist/
```

---

## Nginx 反向代理

### 单服务器部署（前端 + 后端）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /var/www/geo/dist;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript
               image/svg+xml;

    # API 反向代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式响应支持（关键！）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        chunked_transfer_encoding on;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # SPA 路由 fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 上传文件大小限制
    client_max_body_size 10M;
}
```

---

## HTTPS / SSL 配置

使用 Let's Encrypt + Certbot：

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书（自动修改 Nginx 配置）
sudo certbot --nginx -d your-domain.com

# 自动续期（certbot 会自动添加 cron）
sudo certbot renew --dry-run
```

配置完成后，确保：
1. `CORS_ORIGINS` 环境变量改为 `https://your-domain.com`
2. 前端 `VITE_API_BASE_URL` 使用 `https://your-domain.com/api/v1`
3. 重启后端服务

---

## PostgreSQL 切换（可选）

SQLite 适合中小规模使用。如需支持更高并发，切换到 PostgreSQL：

1. 安装 `asyncpg`：
```bash
pip install asyncpg
```

2. 修改环境变量：
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/geo_platform
```

3. 运行迁移：
```bash
alembic upgrade head
```

Docker Compose 添加 PostgreSQL 服务：
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: geo_platform
      POSTGRES_USER: geo
      POSTGRES_PASSWORD: your-db-password
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  backend:
    # ... existing config ...
    environment:
      - DATABASE_URL=postgresql+asyncpg://geo:your-db-password@db:5432/geo_platform
    depends_on:
      - db

volumes:
  pgdata:
  backend_data:
  uploads:
```

---

## 升级说明

### 版本升级步骤

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 备份数据库
cp backend/data/app.db backend/data/app.db.bak

# Docker 部署：
docker-compose exec backend cp /app/data/geo_app.db /app/data/geo_app.db.bak

# 3. 重新构建
docker-compose up -d --build

# 4. 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 5. 验证
curl http://localhost:8000/health
```

升级前建议先在测试环境验证。

---

## 备份与恢复

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh - 数据库和文件备份脚本
BACKUP_DIR=/opt/backups/geo
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份 SQLite 数据库
cp /opt/geo-platform/backend/data/app.db $BACKUP_DIR/app_$DATE.db

# 备份上传文件
tar czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/geo-platform/backend/uploads/

# 保留最近 30 天
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

添加 crontab（每天凌晨 3 点执行）：
```bash
0 3 * * * /opt/geo-platform/backup.sh >> /var/log/geo-backup.log 2>&1
```

### 从界面导出（更简单）

1. 进入 **设置 → 数据管理**
2. 点击 **全量导出**，下载 JSON 文件
3. 可同时导出 CSV 模块文件
4. 恢复时使用 **数据导入** 功能
