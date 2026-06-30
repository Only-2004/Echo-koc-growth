#!/usr/bin/env bash
# T51: 应急切换 — 切回实时 LLM 模式
# 用法: ./scripts/switch_to_live.sh [BASE_URL] [ADMIN_TOKEN]
# 默认: http://localhost:8000, 从 .env 读 ADMIN_TOKEN

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
ADMIN_TOKEN="${2:-}"

# 如果没传 token，尝试从 .env 读
if [ -z "$ADMIN_TOKEN" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
  if [ -f "$PROJECT_ROOT/.env" ]; then
    ADMIN_TOKEN=$(grep -E '^ADMIN_TOKEN=' "$PROJECT_ROOT/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'" | xargs)
  fi
fi

if [ -z "$ADMIN_TOKEN" ]; then
  echo "错误: ADMIN_TOKEN 未设置。请传参或在 .env 中配置。"
  exit 1
fi

echo "正在切回实时 LLM 模式..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/admin/mode" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"use_fallback_all": false, "use_cached_analysis": false}')

echo "响应: $RESPONSE"

if echo "$RESPONSE" | grep -q '"use_fallback_all":false'; then
  echo "✅ 已切回实时 LLM 模式"
else
  echo "❌ 切换失败"
  exit 1
fi
