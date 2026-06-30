#!/bin/bash
# =============================================================================
# Echo · runtime_data 每日备份脚本
# =============================================================================
#
# 用途：把 backend/runtime_data/ 打包成 tar.gz 存到 /opt/backups/beacon/，
#       保留最近 14 天，自动清理过期备份。
#
# 备份内容：profile_v*.json / strategy_snapshot_*.json / insights_report_*.json
#
# 用法（手动）：
#   bash /opt/beacon/deploy/backup_runtime_data.sh
#
# 用法（cron · 每日 03:00）：
#   crontab -e
#   0 3 * * * /bin/bash /opt/beacon/deploy/backup_runtime_data.sh >> /var/log/beacon-backup.log 2>&1
#
# 验证：
#   ls -lh /opt/backups/beacon/
#   tar tzf /opt/backups/beacon/<日期>.tar.gz | head
# =============================================================================

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/opt/beacon}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/beacon}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DATE="$(date +%F-%H%M)"

# ---- 校验源目录存在 ----
if [ ! -d "$PROJECT_ROOT/backend/runtime_data" ]; then
    echo "❌ 源目录不存在：$PROJECT_ROOT/backend/runtime_data"
    exit 1
fi

# ---- 创建目标目录（首次运行时，/opt 下需要 sudo）----
if [ ! -d "$BACKUP_DIR" ]; then
    sudo mkdir -p "$BACKUP_DIR"
    sudo chown "$(id -un):$(id -gn)" "$BACKUP_DIR"
fi

# ---- 备份 ----
ARCHIVE="$BACKUP_DIR/$DATE.tar.gz"
echo "[$(date -Iseconds)] 备份开始：$ARCHIVE"

tar czf "$ARCHIVE" -C "$PROJECT_ROOT" backend/runtime_data backend/cache 2>/dev/null || {
    echo "❌ tar 失败"
    exit 1
}

SIZE="$(du -h "$ARCHIVE" | cut -f1)"
echo "[$(date -Iseconds)] 备份完成：$ARCHIVE ($SIZE)"

# ---- 清理过期备份 ----
DELETED=$(find "$BACKUP_DIR" -name "*.tar.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
echo "[$(date -Iseconds)] 清理超过 $RETENTION_DAYS 天的备份：$DELETED 个文件"

# ---- 显示当前备份列表 ----
echo ""
echo "当前备份："
ls -lh "$BACKUP_DIR/" | tail -n +2 || true
