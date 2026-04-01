---
name: openclaw-live-monitor
description: 实时日志监控 + 健康自检 + 中文转译 Dashboard
version: 1.0.0
port: 18790
---

# OpenClaw Live Monitor

实时监控网关日志、健康自检、技术术语中文转译的 Dashboard。

## 启动方式

```bash
cd ~/.openclaw/workspace/skills/openclaw-live-monitor
npm install
node src/server.js
```

访问：http://localhost:18790/

## 功能清单

- ✅ 实时日志流（WebSocket 推送）
- ✅ 健康自检（每分钟打分）
- ✅ 中文转译（技术术语→人话）
- ✅ 级别过滤（INFO/WARN/ERROR）
- ✅ 错误高亮 + 告警
- ✅ 性能图表
- ✅ 历史搜索
