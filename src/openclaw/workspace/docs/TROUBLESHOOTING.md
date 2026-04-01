# 🔧 故障排查手册

**版本:** 1.0  
**创建时间:** 2026-03-10  
**维护人:** [YOUR_AI_NAME] 🧠

---

## 📋 目录

1. [快速诊断流程](#快速诊断流程)
2. [常见问题](#常见问题)
3. [数据库问题](#数据库问题)
4. [技能问题](#技能问题)
5. [网络连接问题](#网络连接问题)
6. [备份与恢复](#备份与恢复)
7. [紧急联系](#紧急联系)

---

## 🚨 快速诊断流程

### 第一步：检查系统状态

```bash
# 1. 检查 OpenClaw 状态
openclaw gateway status

# 2. 检查 VectorBrain 数据库
sqlite3 ~/.vectorbrain/memory/episodic_memory.db "SELECT COUNT(*) FROM episodes;"
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "SELECT COUNT(*) FROM knowledge;"

# 3. 检查技能配置
ls ~/.openclaw/skills/*/skill.json | wc -l
```

### 第二步：识别问题类型

```
问题现象 → 对应章节

❌ 无法响应消息 → 网络连接问题
❌ 回答错误/遗忘 → 数据库问题
❌ 技能无法调用 → 技能问题
❌ 系统崩溃 → 备份与恢复
```

### 第三步：执行诊断命令

```bash
# 运行健康检查
python3 ~/.openclaw/skills/brain-health-monitor/brain_health_monitor.py --force

# 查看最近日志
tail -100 ~/openclaw_gateway.log
```

---

## 常见问题

### 问题 1: 不回复消息

**症状:**
- 发送消息后无响应
- Gateway 显示运行但无回复

**可能原因:**
1. Feishu 配置错误
2. Gateway 卡死
3. 模型 API 失败

**排查步骤:**
```bash
# 1. 检查 Gateway 状态
openclaw gateway status

# 2. 重启 Gateway
openclaw gateway restart

# 3. 查看日志
tail -50 ~/openclaw_gateway.log | grep -i error

# 4. 检查 Feishu 配置
cat ~/.openclaw/extensions/feishu/config.json
```

**解决方案:**
```bash
# 方案 A: 重启 Gateway
openclaw gateway stop
openclaw gateway start

# 方案 B: 重新配置 Feishu
openclaw configure --section feishu

# 方案 C: 检查模型配置
openclaw configure --section model
```

---

### 问题 2: 记忆检索失败

**症状:**
- 回答"我不记得了"
- 检索结果不准确
- 检索时间过长 (>5 秒)

**可能原因:**
1. VectorBrain 数据库损坏
2. 向量索引缺失
3. 检索脚本错误

**排查步骤:**
```bash
# 1. 检查数据库完整性
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "PRAGMA integrity_check;"

# 2. 检查数据量
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "SELECT COUNT(*) FROM knowledge;"

# 3. 测试检索
python3 ~/.vectorbrain/connector/vector_search.py "测试检索"
```

**解决方案:**
```bash
# 方案 A: 数据库修复
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "VACUUM;"
sqlite3 ~/.vectorbrain/memory/episodic_memory.db "VACUUM;"

# 方案 B: 从备份恢复
cp ~/Desktop/skill-[YOUR_INITIALS]002/vectorbrain/memory/*.db ~/.vectorbrain/memory/

# 方案 C: 重建索引（需要专业支持）
```

---

### 问题 3: 技能无法调用

**症状:**
- 技能没有响应
- 提示"未找到技能"
- 技能执行错误

**可能原因:**
1. skill.json 缺失
2. 技能脚本错误
3. 依赖未安装

**排查步骤:**
```bash
# 1. 检查技能配置
ls ~/.openclaw/skills/{skill_name}/skill.json

# 2. 检查技能脚本
ls ~/.openclaw/skills/{skill_name}/*.py

# 3. 测试技能
python3 ~/.openclaw/skills/{skill_name}/{script}.py

# 4. 检查依赖
pip3 list | grep {dependency}
```

**解决方案:**
```bash
# 方案 A: 重新创建 skill.json
cd ~/.openclaw/skills/{skill_name}
# 参考其他技能的 skill.json 模板

# 方案 B: 安装依赖
pip3 install -r requirements.txt

# 方案 C: 重新安装技能
clawhub install {skill_name}
```

---

## 数据库问题

### 数据库损坏

**症状:**
- 查询报错 "database disk image is malformed"
- 数据丢失
- 无法写入

**诊断:**
```bash
sqlite3 ~/.vectorbrain/memory/{database}.db "PRAGMA integrity_check;"
```

**解决方案:**
```bash
# 1. 尝试修复
sqlite3 ~/.vectorbrain/memory/{database}.db ".recover" | sqlite3 fixed.db
mv fixed.db ~/.vectorbrain/memory/{database}.db

# 2. 从备份恢复
cp ~/Desktop/skill-[YOUR_INITIALS]002/vectorbrain/memory/{database}.db ~/.vectorbrain/memory/

# 3. 如果都失败，重建数据库（数据会丢失）
```

### 数据库锁死

**症状:**
- "database is locked" 错误
- 无法写入数据

**解决方案:**
```bash
# 1. 查找占用进程
lsof ~/.vectorbrain/memory/*.db

# 2. 杀死占用进程
kill -9 {PID}

# 3. 删除锁文件
rm ~/.vectorbrain/memory/*.db-journal

# 4. 重启相关服务
```

---

## 技能问题

### 技能配置丢失

**症状:**
- skill.json 文件消失
- 技能无法识别

**解决方案:**
```bash
# 1. 从 Git 恢复
cd ~/.openclaw/skills/{skill_name}
git checkout skill.json

# 2. 从备份恢复
cp ~/Desktop/skill-[YOUR_INITIALS]002/skills/{skill_name}/skill.json ./

# 3. 重新创建（参考其他技能）
```

### 技能依赖缺失

**症状:**
- ImportError: No module named 'xxx'
- 技能执行失败

**解决方案:**
```bash
# 查看技能需要的依赖
cat ~/.openclaw/skills/{skill_name}/requirements.txt

# 安装依赖
pip3 install -r ~/.openclaw/skills/{skill_name}/requirements.txt

# 或者使用 skill.json 中定义的依赖
```

---

## 网络连接问题

### GitHub 连接失败

**症状:**
- git push 失败
- SSH 认证错误

**解决方案:**
```bash
# 1. 测试 SSH 连接
ssh -T git@github.com

# 2. 检查 SSH 密钥
ls -la ~/.ssh/id_*

# 3. 重新添加密钥到 ssh-agent
ssh-add ~/.ssh/id_ed25519

# 4. 检查远程仓库配置
cd ~/.openclaw/workspace
git remote -v
git remote set-url origin git@github.com:{user}/{repo}.git
```

### Feishu API 失败

**症状:**
- 消息发送失败
- API 返回错误

**解决方案:**
```bash
# 1. 检查 App ID 和 Secret
cat ~/.openclaw/extensions/feishu/config.json

# 2. 测试 API
curl -X POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
  -H "Content-Type: application/json" \
  -d '{"app_id":"xxx","app_secret":"xxx"}'

# 3. 重新配置
openclaw configure --section feishu
```

---

## 备份与恢复

### 紧急恢复流程

**场景:** 系统完全崩溃，需要快速恢复

**步骤:**
```bash
# 1. 停止所有服务
pkill -f openclaw
pkill -f vectorbrain

# 2. 备份当前状态（以防万一）
cp -r ~/.vectorbrain ~/Desktop/vectorbrain.broken.$(date +%Y%m%d_%H%M%S)
cp -r ~/.openclaw/workspace ~/Desktop/workspace.broken.$(date +%Y%m%d_%H%M%S)

# 3. 从备份恢复
unzip ~/Desktop/skill-[YOUR_INITIALS]002_*.zip -d ~/Desktop/restore
cp -r ~/Desktop/restore/skill-[YOUR_INITIALS]002/vectorbrain/* ~/.vectorbrain/
cp -r ~/Desktop/restore/skill-[YOUR_INITIALS]002/workspace/* ~/.openclaw/workspace/

# 4. 验证恢复
sqlite3 ~/.vectorbrain/memory/episodic_memory.db "SELECT COUNT(*) FROM episodes;"
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "SELECT COUNT(*) FROM knowledge;"

# 5. 重启服务
openclaw gateway start
```

### 数据恢复验证

```bash
# 验证数据库完整性
sqlite3 ~/.vectorbrain/memory/episodic_memory.db "PRAGMA integrity_check;"
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "PRAGMA integrity_check;"

# 验证数据量（应该接近备份前的数量）
sqlite3 ~/.vectorbrain/memory/episodic_memory.db "SELECT COUNT(*) FROM episodes;"
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "SELECT COUNT(*) FROM knowledge;"

# 验证技能配置
ls ~/.openclaw/skills/*/skill.json | wc -l
```

---

## 📞 紧急联系

### 自助资源
- **文档:** `~/.openclaw/workspace/docs/`
- **日志:** `~/openclaw_gateway.log`
- **备份:** `~/Desktop/skill-[YOUR_INITIALS]002_*.zip`

### 技术支持
- **GitHub Issues:** https://github.com/openclaw/openclaw/issues
- **Discord:** https://discord.com/invite/clawd
- **文档:** https://docs.openclaw.ai

### 内部联系
- **管理员:** [YOUR_NAME] (Feishu)
- **Backup 位置:** `~/Desktop/skill-[YOUR_INITIALS]002_YYYY-MM-DD.zip`

---

## 📊 故障记录模板

```markdown
## 故障记录

**日期:** YYYY-MM-DD HH:MM
**现象:** [描述问题现象]
**原因:** [根本原因]
**解决:** [解决方案]
**预防:** [如何预防再次发生]
**耗时:** [解决用时]
```

---

## 🔗 相关文档

- [系统架构图](./SYSTEM_ARCHITECTURE.md)
- [最佳实践指南](./BEST_PRACTICES.md)
- [快速入门指南](./QUICK_START.md)
- [备份指南](../BACKUP_GUIDE.md)
- [改进计划](./IMPROVEMENT_PLAN.md)

---

**最后更新:** 2026-03-10  
**下次审查:** 2026-03-17  
**维护状态:** ✅ 活跃维护
