#!/bin/bash
# name: import_knowledge_base
# description: 批量导入高价值文件知识到 VectorBrain information memory
# version: 2.0.0
# author: Nexus

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
HOME_DIR="${HOME:-}"
IMPORT_SCRIPT="${HOME_DIR}/.vectorbrain/connector/import_information_files.py"
WORKSPACE_DIR="${HOME_DIR}/.openclaw/workspace"
VECTORBRAIN_MEMORY_DIR="${HOME_DIR}/.vectorbrain/memory"

TARGET_DIR="${1:-$WORKSPACE_DIR}"

if [ ! -f "$IMPORT_SCRIPT" ]; then
  echo "❌ 导入脚本不存在：$IMPORT_SCRIPT"
  exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "❌ 目标目录不存在：$TARGET_DIR"
  exit 1
fi

echo "🚀 开始导入文件知识到 VectorBrain information memory..."
echo "- 导入脚本: $IMPORT_SCRIPT"
echo "- 目标目录: $TARGET_DIR"
echo "- 输出数据库: $VECTORBRAIN_MEMORY_DIR/information_memory.db"
echo ""

exec "$PYTHON_BIN" "$IMPORT_SCRIPT" "$TARGET_DIR"
