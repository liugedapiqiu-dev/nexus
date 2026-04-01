# 会话历史自动归档系统

**版本:** 1.0.0  
**创建时间:** 2026-03-11  
**维护人:** [YOUR_AI_NAME] 🧠

---

## 📋 功能概述

自动将 OpenClaw 会话历史（jsonl 文件）归档到 VectorBrain 的 `episodic_memory.db` 数据库中，确保对话记录持久化保存，支持后续检索和分析。

---

## ⚙️ 设计原则

### 1. 可靠性第一
- ✅ **幂等性**: 基于文件 MD5 哈希，重复执行不会造成重复归档
- ✅ **原子性**: 使用 SQLite 事务，要么全部成功，要么全部回滚
- ✅ **容错性**: 单条记录失败不影响其他记录的归档
- ✅ **可追溯**: 详细的归档日志，便于问题排查

### 2. 简单即是美
- 无复杂依赖，纯 Python 标准库
- 状态追踪用简单的 JSON 文件
- 日志用 JSONL 格式，易于解析

---

## 🚀 使用方法

### 手动运行
```bash
python3 ~/.openclaw/skills/session-history-archiver/session_archiver.py
```

### 定时运行（推荐）
编辑 crontab：
```bash
crontab -e
```

添加以下行（每小时运行一次）：
```
0 * * * * python3 ~/.openclaw/skills/session-history-archiver/session_archiver.py >> ~/.vectorbrain/archiver.log 2>&1
```

---

## 📁 文件结构

```
~/.openclaw/skills/session-history-archiver/
├── session_archiver.py    # 主程序
├── skill.json             # 技能配置
└── SKILL.md               # 说明文档

~/.vectorbrain/
├── archive_state.json     # 归档状态（记录已归档的会话）
├── archive_log.jsonl      # 归档日志（每次归档的事件记录）
└── memory/
    └── episodic_memory.db # 归档目标数据库
```

---

## 🔄 工作流程

```
1. 扫描 ~/.openclaw/agents/main/sessions/*.jsonl
   ↓
2. 过滤活跃会话（排除 .deleted, .backup, .reset 等）
   ↓
3. 检查归档状态（通过 MD5 哈希判断是否已归档）
   ↓
4. 解析 jsonl 文件，提取 message 类型的记录
   ↓
5. 开启数据库事务
   ↓
6. 逐条插入 episodic_memory.db
   ↓
7. 提交事务，更新归档状态
   ↓
8. 记录归档日志
```

---

## 📊 数据库结构

归档到 `episodic_memory.db` 的 `episodes` 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| timestamp | TEXT | 消息时间戳 |
| worker_id | TEXT | 工作节点 ID（固定为"session_archiver"） |
| event_type | TEXT | 事件类型（如"message:user"、"message:assistant"） |
| content | TEXT | 消息内容（限制 10000 字符） |
| metadata | TEXT | JSON 元数据（包含 session_id, message_id, role 等） |
| created_at | TEXT | 归档时间 |

---

## 🔍 状态追踪

### archive_state.json
```json
{
  "last_updated": "2026-03-11T11:55:00",
  "archived_sessions": {
    "1ea0dd5f-7a62-43c4-9b02-74eef89b00d9": {
      "archived_at": "2026-03-11T11:55:00",
      "message_count": 42,
      "file_hash": "abc123...",
      "source_file": "1ea0dd5f-7a62-43c4-9b02-74eef89b00d9"
    }
  },
  "stats": {
    "total": 10,
    "success": 8,
    "failed": 0,
    "skipped": 2
  }
}
```

### archive_log.jsonl
```jsonl
{"timestamp": "2026-03-11T11:55:00", "event": "success", "session_id": "abc123", "details": "归档 42 条消息"}
{"timestamp": "2026-03-11T11:55:01", "event": "success", "session_id": "def456", "details": "归档 28 条消息"}
```

---

## 🛡️ 可靠性保障

### 1. 避免重复归档
- 每个会话归档后记录 MD5 哈希
- 下次运行时比较哈希值，相同则跳过
- 如果文件有更新（哈希变化），会重新归档（增量归档待实现）

### 2. 数据完整性
- 使用 SQLite 事务包裹整个归档过程
- 插入失败时自动回滚
- 单条消息错误不影响其他消息

### 3. 错误恢复
- 详细的错误日志记录
- 状态文件在每次成功后更新
- 可随时中断，下次继续

### 4. 监控和告警
- 查看日志：`tail -f ~/.vectorbrain/archive_log.jsonl`
- 查看状态：`cat ~/.vectorbrain/archive_state.json`
- 统计信息：每次运行后打印汇总

---

## 🐛 故障排查

### 问题 1：归档失败
```bash
# 查看详细日志
tail -100 ~/.vectorbrain/archive_log.jsonl | jq

# 检查数据库是否可写
sqlite3 ~/.vectorbrain/memory/episodic_memory.db ".tables"
```

### 问题 2：重复归档
```bash
# 检查状态文件
cat ~/.vectorbrain/archive_state.json | jq '.archived_sessions'

# 如果状态文件损坏，删除后重新运行
rm ~/.vectorbrain/archive_state.json
python3 ~/.openclaw/skills/session-history-archiver/session_archiver.py
```

### 问题 3：数据库锁定
```bash
# 检查是否有其他进程使用数据库
lsof ~/.vectorbrain/memory/episodic_memory.db

# 如果是归档进程卡住，终止后删除状态文件重试
kill <pid>
rm ~/.vectorbrain/archive_state.json
```

---

## 📈 性能优化建议

1. **批量插入**: 当前是逐条插入，可优化为批量插入（每 100 条提交一次）
2. **增量归档**: 当前检测到文件变化会重新归档，可实现真正的增量归档
3. **并发控制**: 多个实例同时运行时，需要文件锁机制
4. **压缩存储**: 长期归档可考虑压缩旧会话

---

## 🔮 未来扩展

- [ ] 增量归档（只归档新增的消息）
- [ ] 归档后压缩旧 jsonl 文件
- [ ] 支持 knowledge_memory.db 的自动提炼
- [ ] Webhook 通知归档完成
- [ ] 归档统计 Dashboard

---

## 📝 注意事项

1. **首次运行**: 会归档所有活跃会话，可能耗时较长
2. **磁盘空间**: 确保 `~/.vectorbrain/memory/` 有足够空间
3. **数据库备份**: 定期备份 episodic_memory.db
4. **权限问题**: 确保脚本有数据库写入权限

---

**最后更新:** 2026-03-11  
**维护状态:** ✅ 活跃维护
