#!/bin/bash
# =============================================================================
# Beacon · Let's Encrypt 首次签证书脚本
# =============================================================================
#
# 用途：在生产服务器上首次申请 SSL 证书，并把证书放到正确位置供 nginx 容器使用。
#
# 前置条件：
#   1. 域名已解析到本机公网 IP（nip.io 自动支持，无需配置）
#   2. 服务器 80 端口已对公网开放（防火墙 + 安全组）
#   3. docker 已安装并启动
#   4. /opt/beacon 目录存在且当前用户有写权限
#
# 用法：
#   cd /opt/beacon
#   bash deploy/init-letsencrypt.sh <domain> <email>
#
# 示例（用 nip.io 域名）：
#   bash deploy/init-letsencrypt.sh 43-134-72-220.nip.io your@email.com
#
# 流程：
#   1. 创建必要目录
#   2. 下载 SSL 推荐参数文件（options-ssl-nginx.conf, ssl-dhparams.pem）
#   3. 生成临时 dummy 证书（让 nginx 能先启动）
#   4. 启动 nginx 容器（80 端口 listen）
#   5. 用 certbot webroot 模式申请正式证书
#   6. 把正式证书重命名为 /etc/letsencrypt/live/beacon/（nginx.conf 写死的路径）
#   7. reload nginx
# =============================================================================

set -euo pipefail

# ---- 参数校验 ----
if [ "$#" -ne 2 ]; then
    echo "用法：bash deploy/init-letsencrypt.sh <domain> <email>"
    echo "示例：bash deploy/init-letsencrypt.sh 43-134-72-220.nip.io your@email.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

# ---- 校验项目结构 ----
if [ ! -f docker-compose.yml ] || [ ! -f deploy/docker-compose.prod.yml ]; then
    echo "❌ 找不到 docker-compose.yml 或 deploy/docker-compose.prod.yml"
    echo "   请在项目根目录运行此脚本"
    exit 1
fi

COMPOSE="docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml"
LETSENCRYPT_DIR="$PROJECT_ROOT/deploy/letsencrypt"
CERTBOT_WWW="$PROJECT_ROOT/deploy/certbot-www"

echo "==> [1/7] 创建必要目录"
mkdir -p "$LETSENCRYPT_DIR" "$CERTBOT_WWW"

# ---- 2. 下载 SSL 推荐参数（如果还没有）----
echo "==> [2/7] 下载 SSL 推荐参数文件"
if [ ! -e "$LETSENCRYPT_DIR/options-ssl-nginx.conf" ] || [ ! -e "$LETSENCRYPT_DIR/ssl-dhparams.pem" ]; then
    curl -fsSL https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$LETSENCRYPT_DIR/options-ssl-nginx.conf"
    curl -fsSL https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$LETSENCRYPT_DIR/ssl-dhparams.pem"
fi

# ---- 3. 生成临时 dummy 证书（让 nginx 能启动）----
echo "==> [3/7] 生成临时 dummy 证书（让 nginx 能先启动）"
DUMMY_PATH="/etc/letsencrypt/live/beacon"
mkdir -p "$LETSENCRYPT_DIR/live/beacon"
docker run --rm \
    -v "$LETSENCRYPT_DIR:/etc/letsencrypt" \
    --entrypoint openssl \
    certbot/certbot \
    req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$DUMMY_PATH/privkey.pem" \
        -out    "$DUMMY_PATH/fullchain.pem" \
        -subj   "/CN=localhost"

# ---- 4. 启动 nginx + frontend + backend ----
echo "==> [4/7] 启动 nginx + frontend + backend（带 dummy 证书）"
$COMPOSE up -d --force-recreate nginx frontend backend

# 等待 nginx 起来
echo "    等 nginx 启动 5 秒..."
sleep 5

# ---- 5. 申请正式 Let's Encrypt 证书（不先删 beacon！nginx 需要它保持运行）----
echo "==> [5/7] 申请正式 Let's Encrypt 证书（webroot 模式）"
# certbot 写入 /etc/letsencrypt/live/${DOMAIN}/，不会碰 beacon/ 目录
# 保留 dummy beacon 证书让 nginx 在 certbot 运行期间持续服务 80 端口
$COMPOSE --profile certbot run --rm certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN"

# ---- 6. certbot 成功 → 替换 beacon 证书（此时删 dummy 才安全）----
echo "==> [6/7] 替换 beacon 证书（nginx.conf 引用的固定路径）"
# certbot 容器以 root 运行，创建的文件属于 root；先改回当前用户所有权
sudo chown -R "$(id -un):$(id -gn)" "$LETSENCRYPT_DIR"
# 先删旧 beacon（可能是 dummy 或上次的真证书）
rm -rf "$LETSENCRYPT_DIR/live/beacon" \
       "$LETSENCRYPT_DIR/archive/beacon" \
       "$LETSENCRYPT_DIR/renewal/beacon.conf"
# 再从 $DOMAIN 目录复制真证书
if [ -d "$LETSENCRYPT_DIR/live/$DOMAIN" ]; then
    cp -RL "$LETSENCRYPT_DIR/live/$DOMAIN"    "$LETSENCRYPT_DIR/live/beacon"
    cp -RL "$LETSENCRYPT_DIR/archive/$DOMAIN" "$LETSENCRYPT_DIR/archive/beacon" 2>/dev/null || true
else
    echo "❌ certbot 完成但找不到 $LETSENCRYPT_DIR/live/$DOMAIN，请检查 certbot 日志"
    exit 1
fi

# ---- 7. reload nginx ----
echo "==> [7/7] reload nginx 加载正式证书"
$COMPOSE exec nginx nginx -s reload

echo ""
echo "✅ 完成！"
echo "   域名：https://$DOMAIN"
echo "   测试：curl -I https://$DOMAIN/api/health"
echo ""
echo "续期方法（90 天到期前）："
echo "  $COMPOSE --profile certbot run --rm certbot renew"
echo "  $COMPOSE exec nginx nginx -s reload"
