# Echo 部署 Runbook

> 腾讯云轻量应用服务器（2vCPU/4GB/60GB）· Ubuntu 22.04 · Docker Compose

## 目录

1. [架构概览](#架构概览)
2. [首次部署（从零开始）](#首次部署从零开始)
3. [日常运维](#日常运维)
4. [证书续期](#证书续期)
5. [备份与恢复](#备份与恢复)
6. [故障排查](#故障排查)
7. [扩展：在同一台机器上挂载其他 agent](#扩展在同一台机器上挂载其他-agent)

---

## 架构概览

```
公网 :80/:443
      │
      ▼
┌──────────────┐
│  nginx 容器  │  ← HTTPS 终结、SSL 证书、HTTP→HTTPS 重定向
│  (alpine)    │
└──────┬───────┘
       │ docker network 内部
       ├─→ /api/*  → backend:8000   (FastAPI · uvicorn)
       └─→ /*      → frontend:80    (内置 nginx serve dist)
```

**容器清单**（`docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml ps`）：

| 容器 | 镜像 | 端口 | 资源限制 |
|---|---|---|---|
| `beacon-nginx` | `nginx:alpine` | 80, 443 | - |
| `beacon-backend` (build) | python:3.11-slim | 内部 8000 | 1GB mem |
| `beacon-frontend` (build) | nginx:alpine + dist | 内部 80 | 256MB mem |

---

## 首次部署（从零开始）

### 前置：服务器准备

1. 腾讯云控制台 → 轻量应用服务器 → 防火墙放行：22 / 80 / 443
2. SSH 登录服务器，确认是 Ubuntu 22.04
3. 安装 Docker：
   ```bash
   curl -fsSL https://get.docker.com | sudo bash
   sudo usermod -aG docker $USER
   newgrp docker   # 或重新登录
   docker --version && docker compose version
   ```

### 1. 配置 SSH Deploy Key（私有仓库 clone 用）

```bash
ssh-keygen -t ed25519 -C "beacon-server-deploy" -f ~/.ssh/beacon_deploy -N ""
cat ~/.ssh/beacon_deploy.pub
# 复制输出到 GitHub repo → Settings → Deploy keys → Add deploy key

# SSH 配置
cat > ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/beacon_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

# 测试
ssh -T git@github.com   # 应看到 Hi xxx! You've successfully authenticated
```

### 2. Clone 代码

```bash
sudo mkdir -p /opt/beacon
sudo chown $USER:$USER /opt/beacon
git clone git@github.com:RealZYZhang/koc-agent-v2.git /opt/beacon
cd /opt/beacon
```

### 3. 配置 .env

```bash
cp .env.example .env
nano .env
```

**必须修改**：
```bash
DEEPSEEK_API_KEY=sk-xxxxxxx   # 你的 DeepSeek key
USE_CACHED_ANALYSIS=true       # 演示稳定性首选
CORS_ORIGIN=https://43-134-72-220.nip.io   # 替换为你的域名
PUBLIC_BASE_URL=https://43-134-72-220.nip.io
```

### 4. 申请 HTTPS 证书 + 启动

```bash
chmod +x deploy/init-letsencrypt.sh deploy/backup_runtime_data.sh
bash deploy/init-letsencrypt.sh 43-134-72-220.nip.io your@email.com
```

> 把 `43-134-72-220.nip.io` 替换成你的域名（用公网 IP 把 `.` 替换成 `-` 即可）。
> 把 `your@email.com` 替换成你的邮箱（Let's Encrypt 用于过期提醒）。

脚本会自动：
1. 创建必要目录
2. 启动 nginx + frontend + backend
3. 用 certbot 申请正式证书
4. reload nginx 加载证书

### 5. 验证

```bash
# 1. nginx 自身健康
curl https://43-134-72-220.nip.io/nginx-health
# 期望：ok

# 2. 后端 API 健康
curl https://43-134-72-220.nip.io/api/health
# 期望：{"ok":true,"service":"beacon-backend","version":"0.1.0"}

# 3. 浏览器访问 https://43-134-72-220.nip.io
# 期望：地址栏锁标 + Echo 主页

# 4. 容器状态
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml ps
# 期望：3 个容器都是 Up (healthy)

# 5. 资源占用
docker stats --no-stream
```

### 6. 配置每日备份 cron

```bash
crontab -e
# 加这一行：
0 3 * * * /bin/bash /opt/beacon/deploy/backup_runtime_data.sh >> /var/log/beacon-backup.log 2>&1
```

---

## 日常运维

### 启动 / 停止 / 重启

```bash
cd /opt/beacon
COMPOSE="docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml"

# 启动（后台）
$COMPOSE up -d

# 停止
$COMPOSE down

# 重启某个服务
$COMPOSE restart backend
$COMPOSE restart nginx

# 查看日志
$COMPOSE logs -f
$COMPOSE logs -f backend
$COMPOSE logs --tail=100 nginx
```

### 更新代码（拉新版本）

```bash
cd /opt/beacon
git fetch origin
git checkout origin/main   # detached HEAD，安全
$COMPOSE up -d --build     # 重新构建并启动
```

### 修改 nginx 配置（不重启容器）

```bash
nano deploy/nginx.conf
$COMPOSE exec nginx nginx -t       # 语法检查
$COMPOSE exec nginx nginx -s reload   # 热重载
```

---

## 证书续期

Let's Encrypt 证书 90 天到期。**手动续期**：

```bash
cd /opt/beacon
$COMPOSE --profile certbot run --rm certbot renew
$COMPOSE exec nginx nginx -s reload
```

**自动续期**（推荐 cron 每月 1 号执行）：

```bash
crontab -e
# 加这一行：
0 0 1 * * cd /opt/beacon && docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml --profile certbot run --rm certbot renew && docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml exec nginx nginx -s reload
```

**dry-run 测试**（不会真的续期）：

```bash
$COMPOSE --profile certbot run --rm certbot renew --dry-run
```

---

## 备份与恢复

### 备份

```bash
# 手动跑一次
bash /opt/beacon/deploy/backup_runtime_data.sh

# 查看备份
ls -lh /opt/backups/beacon/
```

### 恢复（从某个备份）

```bash
cd /opt/beacon
$COMPOSE down
tar xzf /opt/backups/beacon/2026-05-03-0300.tar.gz -C ./
$COMPOSE up -d
```

---

## 故障排查

### 问题：容器起不来

```bash
$COMPOSE logs --tail=200 <service名>
$COMPOSE ps
docker stats --no-stream
```

### 问题：HTTPS 证书申请失败

常见原因：
1. **80 端口未开放** → 检查防火墙 + 安全组
2. **域名解析不对** → `dig 43-134-72-220.nip.io` 应返回 43.134.72.220
3. **Rate limit** → Let's Encrypt 同域名每周最多 5 次，等一下再试

```bash
# 看 certbot 详细日志
$COMPOSE --profile certbot run --rm certbot certificates
```

### 问题：API 504 / 502

```bash
# nginx 看不到后端
$COMPOSE exec nginx ping -c 3 backend
$COMPOSE logs backend | tail -50
$COMPOSE exec backend curl -s http://localhost:8000/api/health
```

### 问题：内存不够

```bash
docker stats --no-stream
free -h

# 临时收紧 backend 限制
# 编辑 deploy/docker-compose.prod.yml 把 mem_limit: 1g 改成 512m
$COMPOSE up -d backend
```

### 问题：前端白屏

```bash
# 确认 dist 已构建并在 frontend 容器里
$COMPOSE exec frontend ls /usr/share/nginx/html
# 应看到 index.html 和 assets/

# 清浏览器缓存或硬刷（Cmd+Shift+R）
```

---

## 扩展：在同一台机器上挂载其他 agent

### 端口规划

| 范围 | 用途 |
|---|---|
| `80, 443` | 唯一公网入口（共享 nginx） |
| `8000-8099` | Echo backend / 子服务 |
| `8100-8199` | Agent 2 |
| `8200-8299` | Agent 3 |
| ... | ... |

### 推荐方案：subdomain 分流

每个 agent 用 nip.io 子域：

| 域名 | 路由到 |
|---|---|
| `beacon.43-134-72-220.nip.io` | Echo |
| `agent2.43-134-72-220.nip.io` | Agent 2 |

> 注：nip.io 的 `*.43-134-72-220.nip.io` 和 `43-134-72-220.nip.io` 都自动解析到 43.134.72.220，子域无需任何 DNS 配置。

### 实施步骤（加新 agent 时）

1. 新 agent 用独立 docker-compose project：
   ```bash
   git clone <agent2 repo> /opt/agent2
   cd /opt/agent2
   ```
2. 加入共享 docker network（首次需创建）：
   ```bash
   docker network create koc-shared 2>/dev/null || true
   ```
3. 修改 agent2 的 docker-compose 让它加入 `koc-shared` 网络
4. 让 Echo 的 nginx 容器也加入 `koc-shared`（在 deploy/docker-compose.prod.yml 加 `networks` 段）
5. 在 `deploy/nginx.conf` 加新的 server 块：
   ```nginx
   server {
       listen 443 ssl http2;
       server_name agent2.43-134-72-220.nip.io;
       # SSL 配置同上...
       location / {
           proxy_pass http://agent2-frontend;
       }
       location /api/ {
           proxy_pass http://agent2-backend:8100;
       }
   }
   ```
6. 给新域名申请证书：
   ```bash
   bash deploy/init-letsencrypt.sh agent2.43-134-72-220.nip.io your@email.com
   ```
7. reload nginx：
   ```bash
   $COMPOSE exec nginx nginx -s reload
   ```

---

## 资源使用基线

正常运行时（参考）：

```
CONTAINER         CPU %    MEM USAGE / LIMIT
beacon-nginx      0.01%    8MB    / 默认
beacon-backend    0.20%    280MB  / 1GB
beacon-frontend   0.00%    5MB    / 256MB
```

**告警阈值建议**：
- backend mem > 800MB → 检查 LLM 调用是否泄漏
- backend CPU > 80% 持续 5 分钟 → 检查并发请求
- 磁盘 > 80% → 检查 docker logs / runtime_data 增长
