#!/bin/bash
# name: import_knowledge_base
# description: 批量导入高价值文件知识到 VectorBrain information memory
# usage: import_knowledge_base.sh [target_dir]

TARGET_DIR="${1:-$HOME/Documents}"

echo "批量导入知识库: $TARGET_DIR"
echo "目标: $HOME/.vectorbrain/memory/information_memory.db"

if [ ! -f "$HOME/.vectorbrain/connector/import_information_files.py" ]; then
    echo "错误: import_information_files.py 未找到"
    exit 1
fi

python3 "$HOME/.vectorbrain/connector/import_information_files.py" "$TARGET_DIR"
