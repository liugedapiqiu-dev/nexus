#!/bin/bash
# name: long_term_memory
# description: 访问长期记忆检索入口（当前以 VectorBrain 检索为准）
# version: 2.0.0
# author: 健豪 + Nexus
# usage: 支持 search/find/lookup/status/help；旧 add/list/stats 已废弃

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
VECTOR_SEARCH_SCRIPT="/home/user/.vectorbrain/connector/vector_search.py"
LEGACY_MEMORY_SCRIPT="/home/user/.openclaw/memory/autonomous/memory_cli.py"

ACTION="${1:-help}"
if [ $# -gt 0 ]; then
  shift
fi

if [ ! -f "$VECTOR_SEARCH_SCRIPT" ]; then
  echo "❌ VectorBrain 检索脚本不存在：$VECTOR_SEARCH_SCRIPT"
  exit 1
fi

case "$ACTION" in
  search|find|lookup)
    QUERY="${1:-}"
    if [ -z "$QUERY" ]; then
      echo "❌ 用法：search \"查询文本\""
      exit 1
    fi
    exec "$PYTHON_BIN" "$VECTOR_SEARCH_SCRIPT" "$QUERY"
    ;;

  status|info|stats)
    echo "🧠 long_term_memory 当前状态"
    echo "- 主检索入口：$VECTOR_SEARCH_SCRIPT"
    if [ -f "$LEGACY_MEMORY_SCRIPT" ]; then
      echo "- 旧自主记忆 CLI 仍存在：$LEGACY_MEMORY_SCRIPT"
      echo "- 但它位于 ~/.openclaw/memory/autonomous/ 旧路径，仅作历史兼容，不再作为默认入口"
    else
      echo "- 旧自主记忆 CLI：未发现"
    fi
    echo "- 知识记忆 DB：/home/user/.vectorbrain/memory/knowledge_memory.db"
    echo "- 情景记忆 DB：/home/user/.vectorbrain/memory/episodic_memory.db"
    ;;

  add|list|ls|all)
    echo "⚠️ long_term_memory 的 add/list 已废弃。"
    echo "原因：默认长期记忆体系已切换到 VectorBrain（~/.vectorbrain/），不再写入 ~/.openclaw/memory/autonomous/ 旧路径。"
    echo "建议："
    echo "- 检索：long_term_memory search \"你的问题\""
    echo "- 导入文件知识：使用 /home/user/.vectorbrain/connector/import_information_files.py <dir>"
    exit 2
    ;;

  help|--help|-h|*)
    echo "🧠 long_term_memory（VectorBrain 版）"
    echo ""
    echo "用法:"
    echo "  search \"查询文本\""
    echo "     通过 ~/.vectorbrain/connector/vector_search.py 检索长期记忆"
    echo ""
    echo "  status"
    echo "     查看当前路径与兼容状态"
    echo ""
    echo "说明:"
    echo "  - 工作区文件记忆：~/.openclaw/workspace/memory/"
    echo "  - 长期向量记忆：~/.vectorbrain/memory/knowledge_memory.db"
    echo "  - 情景记忆：~/.vectorbrain/memory/episodic_memory.db"
    echo "  - ~/.openclaw/memory/autonomous/ 仅为旧系统遗留，不再作为默认入口"
    ;;
esac
