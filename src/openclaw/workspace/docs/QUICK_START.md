# 🚀 [YOUR_AI_NAME]快速入门指南

**版本:** 1.0  
**创建时间:** 2026-03-10  
**适用对象:** 新用户/新设备部署

---

## 📋 目录

1. [快速开始](#快速开始)
2. [新设备安装](#新设备安装)
3. [配置检查清单](#配置检查清单)
4. **测试流程**](#测试流程)
5. [常见问题](#常见问题)
6. [下一步](#下一步)

---

## 快速开始

**5 分钟快速测试:**

```bash
# 1. 检查 OpenClaw 状态
openclaw gateway status

# 2. 发送测试消息（通过 Feishu）
@[YOUR_AI_NAME] 测试

# 3. 查看响应
# 应该收到："收到！[YOUR_AI_NAME]在线，随时为你服务 🧠"

# 4. 测试记忆检索
@[YOUR_AI_NAME] 你还记得我的名字吗？
# 应该回答关于[YOUR_NAME]的信息
```

**预期结果:**
- ✅ Gateway 状态正常
- ✅ 消息响应正常
- ✅ 记忆检索正常

---

## 新设备安装

### 前提条件

**系统要求:**
- macOS 11.0+ (或 Linux/Windows)
- Python 3.11+
- Git
- 至少 10GB 可用空间

**必需账号:**
- GitHub 账号
- Feishu 开放平台账号
- DashScope API Key（阿里云）

### 安装步骤

#### 步骤 1: 安装 OpenClaw

```bash
# 安装 OpenClaw
npm install -g openclaw

# 验证安装
openclaw --version
```

#### 步骤 2: 配置基础环境

```bash
# 运行配置向导
openclaw configure

# 按提示输入:
# - Feishu App ID 和 Secret
# - DashScope API Key
# - 模型配置
```

#### 步骤 3: 恢复备份

```bash
# 从备份恢复（如果有）
unzip ~/Desktop/skill-[YOUR_INITIALS]002_*.zip -d ~/Desktop/restore

# 复制工作区
cp -r ~/Desktop/restore/skill-[YOUR_INITIALS]002/workspace/* ~/.openclaw/workspace/

# 复制 VectorBrain 数据
cp -r ~/Desktop/restore/skill-[YOUR_INITIALS]002/vectorbrain/* ~/.vectorbrain/
```

#### 步骤 4: 启动服务

```bash
# 启动 Gateway
openclaw gateway start

# 检查状态
openclaw gateway status

# 应该显示：
# Gateway Status: Running
# Model: qwen3.5-plus
# Channel: feishu
```

---

## 配置检查清单

### 基础配置

- [ ] OpenClaw 安装成功
  ```bash
  openclaw --version
  ```

- [ ] Gateway 正常运行
  ```bash
  openclaw gateway status
  ```

- [ ] Feishu 配置正确
  ```bash
  # 工作区外文件不要直接用 read；用 shell/命令查看
  cat ~/.openclaw/extensions/feishu/config.json
  ```

- [ ] 模型配置正确
  ```bash
  openclaw status
  ```

### VectorBrain 配置

- [ ] 数据库文件存在
  ```bash
  ls -lh ~/.vectorbrain/memory/*.db
  ```

- [ ] 数据库可访问
  ```bash
  sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "SELECT COUNT(*) FROM knowledge;"
  ```

- [ ] 连接器正常
  ```bash
  python3 ~/.vectorbrain/connector/vector_search.py "测试"
  ```

### 技能系统

- [ ] 技能配置完整
  ```bash
  ls ~/.openclaw/skills/*/skill.json | wc -l
  # 应该 >= 9
  ```

- [ ] 核心技能可用
  ```bash
  # 测试记忆检索
  python3 ~/.openclaw/skills/vectorbrain-memory-search/vector_search.py "测试"
  ```

### 依赖检查

- [ ] Python 版本正确
  ```bash
  python3 --version
  # 应该 >= 3.11
  ```

- [ ] 必需包已安装
  ```bash
  pip3 list | grep -E "openpyxl|pandas|python-docx"
  ```

---

## 测试流程

### 测试 1: 基础对话

**发送:**
```
你好
```

**预期响应:**
```
[友好的问候，包含[YOUR_AI_NAME]的个性特征]
```

**检查点:**
- 响应时间 < 5 秒
- 语气自然
- 符合 SOUL.md 定义的人格

### 测试 2: 记忆检索

**发送:**
```
你还记得我是谁吗？
```

**预期响应:**
```
[应该提到[YOUR_NAME]、VectorBrain 等相关信息]
```

**检查点:**
- 正确检索知识记忆
- 回答准确
- 响应时间 < 5 秒

### 测试 3: 技能调用

**发送:**
```
检查一下系统健康状态
```

**预期响应:**
```
[运行健康检查并返回结果]
```

**检查点:**
- 正确调用 brain-health-monitor 技能
- 返回详细报告
- 健康度评分正确

### 测试 4: 记忆提炼

**发送:**
```
今天学到了一个新知识：Python 的装饰器可以用来缓存函数结果
```

**预期响应:**
```
[确认收到并记录]
```

**验证:**
```bash
# 检查是否已提炼
python3 ~/.vectorbrain/connector/vector_search.py "Python 装饰器 缓存"
```

### 测试 5: 任务反思

**发送:**
```
刚才的任务完成了，记录一下经验
```

**预期响应:**
```
[运行反思引擎并记录]
```

**验证:**
```bash
sqlite3 ~/.vectorbrain/reflection/reflections.db "SELECT COUNT(*) FROM reflections WHERE created_at > datetime('now', '-1 hour');"
```

---

## 常见问题

### Q1: Gateway 无法启动

**症状:**
```
Error: Address already in use
```

**解决方案:**
```bash
# 查找占用端口的进程
lsof -i :8080  # 或其他端口

# 杀死占用进程
kill -9 {PID}

# 重启 Gateway
openclaw gateway restart
```

### Q2: Feishu 不回复

**症状:**
- 消息发送成功但无回复

**排查步骤:**
```bash
# 1. 检查 Feishu 配置
cat ~/.openclaw/extensions/feishu/config.json

# 2. 测试 API
curl -X POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
  -H "Content-Type: application/json" \
  -d '{"app_id":"xxx","app_secret":"xxx"}'

# 3. 查看日志
tail -50 ~/openclaw_gateway.log | grep feishu
```

### Q3: 记忆检索失败

**症状:**
- "我不记得了"
- 检索结果为空

**解决方案:**
```bash
# 1. 检查数据库
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "SELECT COUNT(*) FROM knowledge;"

# 2. 测试检索
python3 ~/.vectorbrain/connector/vector_search.py "测试"

# 3. 如果数据库为空，从备份恢复
cp ~/Desktop/skill-[YOUR_INITIALS]002/vectorbrain/memory/*.db ~/.vectorbrain/memory/
```

### Q4: 技能无法调用

**症状:**
- 技能没有响应
- 提示"未找到技能"

**解决方案:**
```bash
# 1. 检查技能配置
ls ~/.openclaw/skills/{skill_name}/skill.json

# 2. 重新加载技能
openclaw gateway restart

# 3. 检查依赖
pip3 install -r ~/.openclaw/skills/{skill_name}/requirements.txt
```

### Q5: Git 推送失败

**症状:**
```
fatal: could not read Username for 'https://github.com'
```

**解决方案:**
```bash
# 1. 切换到 SSH
cd ~/.openclaw/workspace
git remote set-url origin git@github.com:{user}/{repo}.git

# 2. 测试 SSH
ssh -T git@github.com

# 3. 重新推送
git push -u origin main
```

---

## 下一步

### 入门后建议

**第 1 周:**
- [ ] 熟悉基本命令
- [ ] 测试所有核心技能
- [ ] 阅读系统架构图

**第 2 周:**
- [ ] 学习技能开发
- [ ] 阅读最佳实践指南
- [ ] 尝试创建自己的技能

**第 3 周:**
- [ ] 学习故障排查
- [ ] 配置自动化备份
- [ ] 优化性能

### 学习资源

**必读文档:**
1. [系统架构图](./SYSTEM_ARCHITECTURE.md)
2. [最佳实践指南](./BEST_PRACTICES.md)
3. [故障排查手册](./TROUBLESHOOTING.md)

**推荐学习路径:**
```
快速入门 → 系统架构 → 技能开发 → 最佳实践 → 故障排查
```

**外部资源:**
- OpenClaw 官方文档: https://docs.openclaw.ai
- GitHub: https://github.com/openclaw/openclaw
- Discord 社区: https://discord.com/invite/clawd

---

## 📞 获取帮助

### 自助资源
- **文档:** `~/.openclaw/workspace/docs/`
- **日志:** `~/openclaw_gateway.log`
- **示例:** `~/.openclaw/skills/*/examples/`

### 社区支持
- **GitHub Issues:** https://github.com/openclaw/openclaw/issues
- **Discord:** https://discord.com/invite/clawd

### 内部联系
- **管理员:** [YOUR_NAME] (Feishu)

---

## 🎯 快速参考

### 常用命令

```bash
# 服务管理
openclaw gateway start
openclaw gateway stop
openclaw gateway restart
openclaw gateway status

# 配置
openclaw configure
openclaw status

# 备份
cp -r ~/.openclaw/workspace ~/Desktop/workspace.backup
cp -r ~/.vectorbrain ~/Desktop/vectorbrain.backup

# 诊断
python3 ~/.openclaw/skills/brain-health-monitor/brain_health_monitor.py --force
tail -100 ~/openclaw_gateway.log
```

### 关键路径

```
~/.openclaw/               # OpenClaw 主目录（工作区外）
~/.openclaw/workspace/     # 工作区（可直接 read 的主范围）
~/.openclaw/skills/        # 本地系统技能（工作区外）
~/.openclaw/workspace/skills/ # 工作区自定义技能
~/.vectorbrain/            # VectorBrain 大脑（长期数据库记忆，工作区外）
~/Desktop/skill-[YOUR_INITIALS]002_*/  # 备份文件
```

### 路径边界提醒

- `~/.openclaw/workspace/memory/` 是**文件记忆层**，仍然有效。
- `~/.vectorbrain/` 是**长期数据库记忆层**。
- `read` 工具默认适合读工作区内文件；工作区外路径通常应改用 `exec`/shell 或技能调用。
- 统一规范见：`~/.openclaw/workspace/PATH_SPEC.md`

---

**最后更新:** 2026-03-10  
**维护状态:** ✅ 活跃维护
