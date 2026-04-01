# [YOUR_AI_NAME]后台加载器 (Ahao Loader)

独立进程加载记忆和状态，不依赖会话生命周期

## 触发意图

当用户提到以下需求时调用此技能：

- 加载记忆
- 初始化状态
- 后台加载
- 会话准备
- 记忆预加载
- 加载记忆
- 后台加载
- 状态初始化
- 预加载
- 会话启动

## 核心功能

| 功能 | 说明 |
|------|------|
| **记忆加载** | 从 VectorBrain 加载情景记忆和知识记忆 |
| **任务加载** | 加载待办任务队列 |
| **状态跟踪** | 更新加载状态到 `.ahao_loading_status.json` |
| **独立进程** | 独立进程运行，不依赖会话生命周期 |
| **PID 管理** | PID 文件管理，防止重复启动 |
| **心跳监测** | 心跳监测确保加载器正常运行 |

## 加载级别

| 级别 | 内容 |
|------|------|
| **Level 1** | 核心身份加载 (SOUL.md, IDENTITY.md) |
| **Level 2** | 工作上下文检索 (USER.md, TOOLS.md, AGENTS.md) |
| **Level 3** | 记忆系统初始化 (VectorBrain 连接) |
| **Level 4** | 待办事项加载 (任务队列) |
| **Level 5** | 系统检测 (后台运行) |

## 数据库配置

| 数据库 | 路径 |
|--------|------|
| 情景记忆 | `~/.vectorbrain/memory/episodic_memory.db` |
| 知识记忆 | `~/.vectorbrain/memory/knowledge_memory.db` |
| 反思 | `~/.vectorbrain/reflection/reflections.db` |
| 任务 | `~/.vectorbrain/tasks/task_queue.db` |
| 目标 | `~/.vectorbrain/goals/goals.db` |

## 输出格式

状态文件格式 (JSON)：

```json
{
  "session_id": "...",
  "start_time": "...",
  "status": "...",
  "progress": "...",
  "message": "...",
  "last_heartbeat": "..."
}
```

## 配置文件

- 状态文件：`~/.openclaw/workspace/.ahao_loading_status.json`
- PID 文件：`/tmp/ahao_loader.pid`
- VectorBrain 目录：`~/.vectorbrain/`

## Bug 防护机制

| 防护类型 | 措施 |
|----------|------|
| PID 文件清理 | 防止进程泄露 |
| 原子写入 | 状态文件损坏防护 |
| 容错机制 | 单级失败不影响整体 |
| 时区统一 | Asia/Shanghai (UTC+8) |

## 使用示例

```
加载记忆
初始化状态
后台加载
会话准备
记忆预加载
```

## 相关文件

- 主脚本：`background_loader.py`
- 技能目录：`~/.openclaw/skills/ahao-loader/`

## 作者

[YOUR_AI_NAME] 🧠 | 版本：1.0.0
