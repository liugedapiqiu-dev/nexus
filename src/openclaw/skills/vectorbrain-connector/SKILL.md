---
name: vectorbrain-connector
description: VectorBrain 大脑连接器 - 读取记忆/执行规划/写入反思
version: 0.1.0
metadata: {"openclaw": {"requires": {"bins": ["python3"]}, "emoji": "🧠"}}
---

# VectorBrain Connector

连接 OpenClaw 和 VectorBrain 大脑的技能。

## 功能

1. **读取记忆** - 从 VectorBrain 读取情景记忆和知识记忆
2. **写入记忆** - 将 OpenClaw 执行的任务写入 VectorBrain
3. **执行规划** - 调用 VectorBrain 的 Planner 拆解任务
4. **机会扫描** - 触发 VectorBrain 的机会扫描引擎

## 用法

### 1. 读取记忆

```bash
# 读取最近 10 条情景记忆
python3 ~/.vectorbrain/src/memory_manager.py load --type episodic --limit 10

# 读取知识记忆
python3 ~/.vectorbrain/src/memory_manager.py load --type knowledge --limit 10
```

### 2. 写入记忆

```bash
# 写入情景记忆
python3 ~/.vectorbrain/src/memory_manager.py save --type episodic --content "任务已完成" --worker "openclaw"
```

### 3. 查看 VectorBrain 状态

```bash
# 查看任务队列
ls ~/.vectorbrain/tasks/

# 查看运行日志
tail -f ~/.vectorbrain/agent_core.log
```

## 集成架构

```
[USER] (指挥官)
  ↓
VectorBrain (大脑) - 思考/规划/反思/记忆
  ↓
OpenClaw (身体) - 执行/交互/工具调用
  ↓
飞书/浏览器/搜索等工具
```

## 注意事项

⚠️ **重要配置变更 (2026-03-07):**

- **唯一记忆路径:** `~/.vectorbrain/memory/`
- **旧路径已禁用:** `~/.openclaw/memory/` ❌ **不再使用**
- **默认行为:** 只从 VectorBrain 读取，除非特别指定

- VectorBrain 必须先运行：`~/.vectorbrain/start.sh`
- 记忆数据库位置：`~/.vectorbrain/memory/` ✅ **唯一正确路径**
- 任务队列位置：`~/.vectorbrain/tasks/`
- 日志位置：`~/.vectorbrain/agent_core.log`

## 记忆路径说明

### ✅ 正确路径 (使用)

```bash
情景记忆：~/.vectorbrain/memory/episodic_memory.db
知识记忆：~/.vectorbrain/memory/knowledge_memory.db
反思记忆：~/.vectorbrain/reflection/reflections.db
目标任务：~/.vectorbrain/tasks/task_queue.db
```

### ❌ 错误路径 (已禁用，不要使用)

```bash
~/.openclaw/memory/lancedb/          # 旧向量库 - 已废弃
~/.openclaw/memory/main.sqlite       # 旧 SQLite - 已废弃
~/.openclaw/memory/autonomous/       # 旧自主记忆 - 已废弃
```

### 如何强制使用旧路径 (仅测试用)

只有在特别测试时，才临时指定旧路径：
```bash
# 不推荐，仅用于数据迁移测试
export VECTORBRAIN_LEGACY_MODE=1
python3 ~/.vectorbrain/src/memory_manager.py --legacy
```

## 测试命令

```bash
# 测试记忆读取
python3 ~/.vectorbrain/src/memory_manager.py load --type episodic --limit 5

# 测试记忆写入
python3 ~/.vectorbrain/src/memory_manager.py save --type episodic --content "测试记忆" --worker "test"

# 验证写入成功
python3 ~/.vectorbrain/src/memory_manager.py load --type episodic --limit 1
```
