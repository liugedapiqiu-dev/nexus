# OpenClaw 启动自检汇报系统

## 📋 功能说明

每次 OpenClaw 启动后自动执行系统自检，并汇报：
- VectorBrain 状态（进程/记忆记录数）
- OpenClaw 状态（网关端口/通道/技能数）
- 系统就绪确认

## 🚀 安装方式

### 方式 1: 手动触发（推荐先用这个测试）

```bash
# 测试自检脚本
python3 ~/.openclaw/skills/startup-healthcheck/src/healthcheck.py
```

### 方式 2: 集成到启动流程

**Option A: 修改 OpenClaw 启动脚本**

编辑 `~/.npm-global/lib/node_modules/openclaw/bin/openclaw.js` 或相应的启动入口，在启动完成后添加：

```javascript
// 启动完成后执行
setTimeout(() => {
  const { exec } = require('child_process');
  exec('~/.openclaw/hooks/on-start.sh');
}, 3000);
```

**Option B: 使用 systemd/init.d 钩子**

如果你用 systemd 管理 OpenClaw：

```bash
# 编辑 service 文件
sudo systemctl edit openclaw

# 添加：
[Service]
ExecStartPost=/home/jo/.openclaw/hooks/on-start.sh
```

**Option C: 包装启动命令**

创建新的启动脚本 `~/.openclaw/start-with-check.sh`：

```bash
#!/bin/bash
# 启动 OpenClaw
openclaw gateway --port 18789 &
OPENCLAW_PID=$!

# 等待启动
sleep 5

# 执行自检
~/.openclaw/hooks/on-start.sh

# 保持运行
wait $OPENCLAW_PID
```

## 📊 输出示例

```
🏥 OpenClaw 启动自检报告

启动时间：2026-03-07 03:45:00
运行进程：✅ 正常 (PID: 12345)

🧠 VectorBrain 状态
  - 进程状态：✅ 运行中 (PID: 56653)
  - 情景记忆：12 条
  - 知识记忆：12 条

🦾 OpenClaw 状态
  - 网关端口：✅ 18789 正常
  - 飞书通道：✅ 已配置
  - 技能数量：10 个

✅ 系统就绪，等待指令
```

## 🔧 自定义配置

编辑 `~/.openclaw/skills/startup-healthcheck/src/healthcheck.py`：

```python
# 修改检查项目
GATEWAY_PORT = 18789  # 网关端口
VECTORBRAIN_PATTERN = 'agent_core_loop.py'  # VectorBrain 进程名

# 添加新的检查项
def check_your_custom_item():
    # 你的自定义检查逻辑
    pass
```

## 🐛 故障排查

### 问题 1: 自检脚本不执行

```bash
# 检查权限
ls -la ~/.openclaw/hooks/on-start.sh
chmod +x ~/.openclaw/hooks/on-start.sh
```

### 问题 2: 消息发送失败

```bash
# 测试 openclaw send 命令
openclaw send "测试消息"

# 检查 Gateway 是否运行
openclaw gateway status
```

### 问题 3: VectorBrain 检测失败

```bash
# 检查 VectorBrain 是否运行
ps aux | grep agent_core_loop

# 启动 VectorBrain
~/.vectorbrain/start.sh
```

## 📝 更新日志

- **v1.0.0** (2026-03-07): 初始版本
  - VectorBrain 状态检查
  - 记忆系统记录数统计
  - OpenClaw 网关状态检查
  - 自动消息汇报

---

*创建者：[YOUR_AI_NAME] 👊*
*最后更新：2026-03-07 03:45*
