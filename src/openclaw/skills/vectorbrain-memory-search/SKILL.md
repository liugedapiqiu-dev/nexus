---
name: vectorbrain-memory-search
description: 核心记忆检索技能 - 向量搜索 VectorBrain 记忆数据库
version: 1.0.0
author: [YOUR_AI_NAME] 🧠
metadata:
  openclaw:
    emoji: 🧠
    requires:
      bins: ["python3"]
      python_packages: ["sqlite3", "numpy"]
---

# VectorBrain 记忆检索技能

**核心记忆检索技能** - 当缺乏背景知识或用户询问历史经验时，必须主动调用此技能搜索 VectorBrain 记忆。

## 🎯 触发场景

**必须主动调用的情况：**

1. **用户询问过去的经验** - "上次那个备份的经验是什么？"
2. **用户询问项目上下文** - "蜘蛛侠书包项目进展如何？"
3. **用户询问个人习惯** - "健豪平时有什么习惯？"
4. **用户询问历史决策** - "为什么选择这个方案？"
5. **用户问你还记不记得某事** - "你忘记了 XXX 吗？"
6. **询问身份/背景/来源** - "你的老师是谁？"、"你是谁创建的？"
7. **意识到缺乏背景知识** - 对当前问题不了解，但 VectorBrain 里可能有答案

**⚠️ 重要原则：**
- 这是**意图驱动 (Function Calling)**，不是关键词触发
- LLM 会根据对话上下文自动判断是否需要调用
- **不要等用户提醒才去查！** 当发现自己不知道某个应该知道的信息时，立即调用

## 🚀 快速开始

### 基本用法

技能会自动执行向量检索，返回 Top-3 最相关的记忆记录：

```bash
python3 ~/.vectorbrain/connector/vector_search.py "{查询文本}"
```

### 使用示例

| 用户问题 | 调用 query |
|----------|-----------|
| "上次那个备份的经验是什么？" | `备份经验` |
| "高尔夫毛巾质检标准是什么？" | `高尔夫毛巾质检` |
| "健豪平时有什么习惯？" | `健豪习惯` |
| "002599 股票什么价格？" | `股票 002599` |
| "你有两个老师吗？" | `老师 两位` |
| "你忘记了 XXX 吗？" | `XXX` |

## 📊 返回结果格式

技能返回 Top-3 记忆记录，包含：

```
======================================================================
📊 检索完成！返回 Top-3 结果
======================================================================

[1] 匹配度：0.6943 | 标签：migrated_knowledge / Identity
    内容预览：# IDENTITY.md - Who Am I...

[2] 匹配度：0.5329 | 标签：migrated_knowledge / User
    内容预览：# USER.md - About Your Human...

[3] 匹配度：0.4901 | 标签：spiderman_group_messages
    内容预览：{"group": "蜘蛛侠 Switch 设计沟通", "sender": "[YOUR_NAME]"...
```

## 🧠 数据库来源

检索自以下 VectorBrain 数据库：

- **情景记忆** (`episodic_memory.db`) - 对话历史、事件记录
- **知识记忆** (`knowledge_memory.db`) - 技能、规则、流程
- **反思记录** (`reflections.db`) - 经验教训、复盘

## ⚙️ 技术细节

### 检索流程

1. **生成查询向量** - 使用嵌入模型将查询文本转换为 1024 维向量
2. **读取数据库记忆** - 从数据库加载所有带向量的记忆
3. **计算相似度** - 使用余弦相似度计算查询向量与记忆向量的匹配度
4. **返回 Top-3** - 按匹配度排序，返回最相关的 3 条记录

### 配置文件

- **技能配置**: `skill.json` - 定义触发意图和入口
- **执行脚本**: `~/.vectorbrain/connector/vector_search.py`

## 📝 使用注意事项

1. **自然吸收结果** - 不要告诉用户"我正在搜索记忆"，直接使用结果
2. **避免重复调用** - 同一上下文中不要反复调用
3. **结果验证** - 如果返回结果不相关，考虑换一种查询方式
4. **隐私保护** - 不要向第三方泄露 VectorBrain 中的敏感信息

## 🔗 相关技能

- **vectorbrain-connector** - VectorBrain 大脑连接器，提供更全面的记忆操作
- **self-improvement** - 持续改进技能，记录新的学习到记忆系统

## 📚 架构决策

详见知识记忆：`vectorbrain-db-naming-convention` (2026-03-10)

## 路径边界（本机当前实际规则）

- **工作区内**（`~/.openclaw/workspace`）可直接用 `read` 读取。
- **工作区外**（如 `~/.openclaw/skills/`、`~/.vectorbrain/`、npm 安装目录）**不要假设 `read` 能直接读到**；应改用 shell/`exec`、技能调用、或框架已暴露的工具。
- 当需要读取当日记忆文件时，本机当前应优先看：`~/.openclaw/workspace/memory/YYYY-MM-DD.md`。

---

*Made with ❤️ for VectorBrain Memory System*
