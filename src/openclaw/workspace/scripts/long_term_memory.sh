#!/bin/bash
# name: long_term_memory
# description: 访问长期记忆检索入口（当前以 VectorBrain 检索为准）
# usage: search/find/lookup/status/help

COMMAND="${1:-help}"

case $COMMAND in
    search|find|lookup)
        QUERY="${2:-}"
        if [ -z "$QUERY" ]; then
            echo "用法: long_term_memory.sh search <查询内容>"
            exit 1
        fi
        python3 "$HOME/.vectorbrain/planner/memory_retriever.py" "$QUERY"
        ;;
    status)
        echo "长期记忆状态:"
        ls -lh "$HOME/.vectorbrain/memory/"*.db 2>/dev/null
        echo ""
        echo "最近修改:"
        find "$HOME/.vectorbrain/memory/" -name "*.db" -mtime -7 2>/dev/null
        ;;
    help|*)
        echo "长期记忆检索工具"
        echo ""
        echo "用法:"
        echo "  long_term_memory.sh search <查询内容>  搜索记忆"
        echo "  long_term_memory.sh find <关键词>      查找记忆"
        echo "  long_term_memory.sh lookup <关键词>   查询记忆"
        echo "  long_term_memory.sh status            查看状态"
        echo "  long_term_memory.sh help              显示帮助"
        ;;
esac
