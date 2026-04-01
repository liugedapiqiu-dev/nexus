---
name: startup-healthcheck
description: OpenClaw 启动自检 - 自动汇报 VectorBrain 状态/记忆系统/网关状态
version: 1.0.0
metadata: {"openclaw": {"requires": {"bins": ["python3", "sqlite3"]}, "emoji": "🏥", "always": true}}
---

# OpenClaw 启动自检技能

每次 OpenClaw 启动后自动执行，汇报系统状态。

## 自动触发

在 `~/.openclaw/hooks/on-start.sh` 中添加：

```bash
#!/bin/bash
# OpenClaw 启动后自动执行

echo "🏥 OpenClaw 启动自检中..."

# 等待 Gateway 就绪
sleep 3

# 执行自检并发送消息
python3 ~/.openclaw/skills/startup-healthcheck/src/healthcheck.py
```

## 自检项目

1. ✅ VectorBrain 连接状态
2. ✅ 记忆系统记录数（情景 + 知识）
3. ✅ 网关端口状态
4. ✅ 飞书通道状态
5. ✅ 运行进程检查

## 输出格式

```
🏥 OpenClaw 启动自检报告

启动时间：2026-03-07 03:45:00
运行进程：✅ 正常

🧠 VectorBrain 状态
  - 进程状态：✅ 运行中 (PID: 56653)
  - 情景记忆：12 条
  - 知识记忆：12 条
  - 机会扫描：2 条

🦾 OpenClaw 状态
  - 网关端口：✅ 18789 正常
  - 飞书通道：✅ 在线
  - 技能数量：XX 个

✅ 系统就绪，等待指令
```

## 文件结构

```
~/.openclaw/skills/startup-healthcheck/
├── SKILL.md              (本文件)
├── src/
│   └── healthcheck.py    (自检脚本)
└── hooks/
    └── on-start.sh       (启动钩子)
```
