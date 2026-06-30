#!/usr/bin/env bash
# 回滚到某个任务检查点 tag。
# 用法：rollback.sh <task_number>

set -euo pipefail

TASK_NUM="${1:?用法：rollback.sh <task_number>}"
TAG="checkpoint-task-$(printf '%03d' "$TASK_NUM")"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BRANCH="rollback-backup-${TIMESTAMP}"

echo "正在检查检查点 tag：$TAG"

if ! git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "错误：未找到 tag $TAG。可用检查点如下："
    git tag -l 'checkpoint-task-*'
    exit 1
fi

echo "正在创建备份分支：$BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"

echo "正在重置到 $TAG..."
git reset --hard "$TAG"

echo ""
echo "回滚完成。"
echo "  已回滚至：$TAG"
echo "  备份分支：$BACKUP_BRANCH"
echo ""
echo "如需撤销本次回滚：git checkout $BACKUP_BRANCH"
