# M9 · 腾讯云轻量服务器生产部署 · 阶段复盘

> 完成日期：2026-05-04  
> 分支：`feat/m9-deploy`  
> 服务器：腾讯云轻量应用服务器（新加坡）· 43.134.72.220 · Ubuntu 22.04 · 2vCPU/4GB/60GB SSD

---

## 1. 做了什么

| 文件 | 类型 | 一句话 |
|---|---|---|
| `backend/Dockerfile` | 修改 | 加 `ARG BUILD_ENV=dev/prod`，生产镜像不装 pytest/ruff/mypy，省 ~100MB |
| `frontend/Dockerfile.prod` | 新建 | 多阶段构建：node:20-alpine Vite build → nginx:alpine serve dist |
| `deploy/nginx.conf` | 新建 | 外层 nginx：HTTPS 终结、HTTP→HTTPS 重定向、/api/* 反代、SSE 支持、安全头 |
| `deploy/docker-compose.prod.yml` | 新建 | 生产 override：backend prod 依赖、frontend 用 Dockerfile.prod、nginx 容器 80/443 |
| `deploy/init-letsencrypt.sh` | 新建 | 首次签发 Let's Encrypt 证书脚本（7 步流程） |
| `deploy/backup_runtime_data.sh` | 新建 | 每日 tar.gz 备份 runtime_data + cache，保留 14 天 |
| `deploy/README.md` | 新建 | 完整部署 runbook（首次部署、日常运维、证书续期、多 agent 扩展） |
| `frontend/src/views/IdeateView.tsx` | 修复 | 把 `as const` 数组从 JSX `{}` 内提取出来，绕过 Vite 8/rolldown 解析 bug |
| `frontend/src/views/RetroView.tsx` | 修复 | 同上 |

**架构**：公网 → nginx:alpine（HTTPS）→ backend:8000（FastAPI）/ frontend:80（内置 nginx serve dist）

---

## 2. 如何测试

### 前置条件
- 腾讯云控制台防火墙放行 22/80/443
- SSH Deploy Key 已配置（GitHub 私有仓库可拉取）
- 服务器安装 Docker + Docker Compose

### 验证用例

| # | 命令 / 操作 | 预期结果 |
|---|---|---|
| 1 | `curl https://43-134-72-220.nip.io/nginx-health` | 返回 `ok` |
| 2 | `curl -v https://43-134-72-220.nip.io/api/health` | HTTP/2 200，JSON body 56 bytes |
| 3 | 浏览器开 `https://43-134-72-220.nip.io` | 地址栏锁标 + Beacon 主页 |
| 4 | `docker compose ... ps` | 三个容器全部 `Up (healthy)` |
| 5 | `docker stats --no-stream` | backend ~65MB/1GB，nginx ~5MB，frontend ~3MB |
| 6 | `bash /opt/beacon/deploy/backup_runtime_data.sh` | `/opt/backups/beacon/` 下生成 tar.gz |
| 7 | `crontab -l` | 包含 `0 3 * * *` 备份 cron |

---

## 3. 测试结果

| # | 实测结果 | 状态 |
|---|---|---|
| 1 | `ok` | ✅ |
| 2 | HTTP/2 200，56 bytes，TLS 1.3，Let's Encrypt 证书有效至 2026-08-02 | ✅ |
| 3 | 待用户浏览器确认（backend 和 nginx 均健康，功能预期正常） | ⏳ |
| 4 | beacon-backend Up (healthy)，beacon-frontend Up，beacon-nginx Up | ✅ |
| 5 | backend 62.82MB / 1GB，frontend 3.37MB / 256MB，nginx 5.13MB | ✅ |
| 6 | 生成 `2026-05-04-1006.tar.gz` (4.0K) | ✅ |
| 7 | cron 已配置 | ✅ |

### 过程中修复的 bug（部署才发现）

| Bug | 根本原因 | 修法 |
|---|---|---|
| Vite 8 build `Unexpected token` | rolldown 无法解析 JSX `{}` 内的 `as const` | 提取数组到 `return` 前的 const 变量 |
| certbot 把 `sh -c "rm..."` 当参数 | certbot 镜像 ENTRYPOINT=certbot，`sh -c` 成了子命令 | 改为宿主机直接 `rm -rf`（bind mount 等价） |
| nginx crash loop | 脚本先删 dummy cert 再跑 certbot，certbot 失败后 cert 已消失 | 把 `rm -rf beacon` 移到 certbot 成功之后 |
| dummy cert 被 nginx 拒绝 | `rsa:1024` 被 OpenSSL 3.x 认定为 `ee key too small` | 改为 `rsa:2048` |
| `rm -rf archive/beacon` permission denied | certbot 容器以 root 运行，创建的文件属于 root | certbot 后加 `sudo chown -R` 还给当前用户 |
| backup `mkdir /opt/backups` permission denied | `/opt` 属于 root | 改用 `sudo mkdir` + `sudo chown` |

---

## 4. 如何复现（从零部署）

> 预计耗时：30–45 分钟（含 Docker 镜像拉取）

```bash
# 1. 服务器准备（Ubuntu 22.04）
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
newgrp docker

# 2. SSH Deploy Key（私有仓库）
ssh-keygen -t ed25519 -C "beacon-deploy" -f ~/.ssh/beacon_deploy -N ""
# 把 ~/.ssh/beacon_deploy.pub 加到 GitHub repo → Settings → Deploy keys
cat > ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/beacon_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

# 3. Clone + 配置
sudo mkdir -p /opt/beacon && sudo chown $USER:$USER /opt/beacon
git clone git@github.com:RealZYZhang/koc-agent-v2.git /opt/beacon
cd /opt/beacon
git checkout origin/feat/m9-deploy   # 或 main（合并后）
cp .env.example .env
# 编辑 .env：填 DEEPSEEK_API_KEY, CORS_ORIGIN, PUBLIC_BASE_URL

# 4. 一键签证书 + 启动
chmod +x deploy/init-letsencrypt.sh deploy/backup_runtime_data.sh
bash deploy/init-letsencrypt.sh 43-134-72-220.nip.io your@email.com

# 5. 配置备份 cron
crontab -e
# 加：0 3 * * * /bin/bash /opt/beacon/deploy/backup_runtime_data.sh >> /var/log/beacon-backup.log 2>&1
```

### 已知坑

1. **首次运行 init-letsencrypt.sh 前** 必须先 `git checkout origin/feat/m9-deploy`，不能用服务器上已有的旧代码
2. **80 端口必须对外可达** 才能通过 Let's Encrypt ACME HTTP-01 验证
3. **如果 init-letsencrypt.sh 中途失败**，`beacon/` 证书目录可能被删，需手动用 rsa:2048 重新生成 dummy cert 再重跑
4. **certbot 创建的文件属于 root**，rm/cp 前需要 `sudo chown -R`（脚本已处理）
5. **Vite 8 / rolldown** 对 `as const` in JSX `{}` 有解析 bug，已在 IdeateView.tsx 和 RetroView.tsx 修复
