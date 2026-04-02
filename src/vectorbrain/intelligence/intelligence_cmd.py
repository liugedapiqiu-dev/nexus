#!/usr/bin/env python3
"""
群聊情报网 - 快速查询命令
用法：intelligence <问题>
"""

import sys
import os

# 添加到路径
sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))

from chat_intelligence_query import answer_question

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 70)
        print("🕵️ 群聊情报网 - 查询系统")
        print("=" * 70)
        print()
        print("用法：intelligence <你的问题>")
        print()
        print("示例问题：")
        print("  • 最近有什么采购订单？")
        print("  • 项目有什么进展？")
        print("  • 有没有质量问题需要处理？")
        print("  • 各群最近在讨论什么？")
        print()
        print("=" * 70)
        sys.exit(0)
    
    question = " ".join(sys.argv[1:])
    
    # 默认查询最近 7 天
    hours = 168
    
    # 如果问题中包含时间词，调整查询范围
    if "今天" in question or "最近" in question:
        hours = 24
    elif "本周" in question or "这周" in question:
        hours = 72
    elif "上月" in question or "上个月" in question:
        hours = 720
    
    answer_question(question, hours)
