# boot.md - Startup Protocol

## 启动序列

1. 检查 startup_manifest.json
2. 验证所有必需文件存在
3. 检查服务状态
4. 执行健康检查
5. 加载人格文件
6. 初始化记忆系统
7. 开始心跳监控

## 启动钩子

执行 `~/.openclaw/hooks/on-start.ps1` (Windows)
或 `~/.openclaw/hooks/on-start.sh` (Linux/Mac)

## 必需文件

- IDENTITY.md
- SOUL.md
- HEART.md
- AGENTS.md
- TOOLS.md
- USER.md
- MEMORY.md
- HEARTBEAT.md
