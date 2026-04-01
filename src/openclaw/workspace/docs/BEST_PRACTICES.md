# 📖 [YOUR_AI_NAME]最佳实践指南

**版本:** 1.0  
**创建时间:** 2026-03-10  
**维护人:** [YOUR_AI_NAME] 🧠

---

## 📋 目录

1. [技能开发最佳实践](#技能开发最佳实践)
2. [记忆管理最佳实践](#记忆管理最佳实践)
3. [备份策略最佳实践](#备份策略最佳实践)
4. [性能优化最佳实践](#性能优化最佳实践)
5. [错误处理最佳实践](#错误处理最佳实践)
6. [文档编写最佳实践](#文档编写最佳实践)

---

## 技能开发最佳实践

### 1. 技能结构设计

**推荐结构:**
```
skill_name/
├── skill.json              # 必需：技能定义
├── SKILL.md                # 必需：使用说明
├── README.md               # 推荐：详细说明
├── requirements.txt        # 推荐：依赖列表
├── main.py                 # 主脚本
├── lib/                    # 库文件
└── examples/               # 示例
```

**当前机器的技能目录要分清：**
- `~/.openclaw/skills/` → 本地系统技能
- `~/.openclaw/workspace/skills/` → 工作区自定义技能
- `~/.npm-global/lib/node_modules/.../skills/` → 插件/npm 自带技能

不要只写模糊的 `skills/`，否则后续很容易指错路径。

**skill.json 必备字段:**
```json
{
  "name": "skill_name",
  "description": "清晰描述技能功能",
  "version": "1.0.0",
  "triggers": {
    "intent": ["触发词 1", "触发词 2"]
  },
  "entry": {
    "type": "script",
    "path": "./",
    "main": "main.py"
  },
  "examples": ["使用示例 1", "使用示例 2"]
}
```

### 2. 错误处理

**✅ 好的做法:**
```python
try:
    result = execute_task()
    if result:
        save_to_memory(result)
    else:
        log_warning("Task returned empty result")
except Exception as e:
    log_error(f"Task failed: {str(e)}")
    save_reflection({
        "task": "task_name",
        "error": str(e),
        "lesson": "需要添加输入验证"
    })
```

**❌ 避免的做法:**
```python
# 没有错误处理
result = execute_task()
save_to_memory(result)

# 或者捕获所有错误但不处理
try:
    execute_task()
except:
    pass
```

### 3. 日志记录

**推荐做法:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def process_data(data):
    logging.info(f"Starting processing with {len(data)} items")
    try:
        result = transform(data)
        logging.info(f"Successfully processed {len(result)} items")
        return result
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        raise
```

---

## 记忆管理最佳实践

### 1. 记忆提炼原则

**应该提炼的内容:**
- ✅ 架构决策
- ✅ 工作流程
- ✅ 经验教训
- ✅ 系统标准
- ✅ 技能配置

**不应提炼的内容:**
- ❌ 日常闲聊
- ❌ 临时信息
- ❌ 重复内容
- ❌ 系统日志

**提炼流程:**
```
原始对话 → 分类识别 → 质量评估 → 去重检查 → 保存到知识记忆
```

### 2. 记忆组织

**推荐分类:**
```
knowledge_memory.db
├── architecture_decision    # 架构决策
├── workflow                 # 工作流程
├── skill_configuration      # 技能配置
├── experience               # 经验教训
├── system_standard          # 系统标准
└── personal_info            # 个人信息
```

**命名规范:**
```
{category}_{description}_{YYYYMMDD}

示例:
- architecture_decision_vectorbrain_storage_20260310
- workflow_session_backup_20260310
- skill_configuration_office_automation_20260310
```

### 3. 记忆检索

**高效检索技巧:**
```python
# ✅ 好的做法：使用具体关键词
vector_search("会话备份工作流程", top_k=3)

# ❌ 避免：过于宽泛
vector_search("备份", top_k=10)  # 返回太多结果

# ✅ 好的做法：添加分类过滤
vector_search("架构决策 数据库存储", top_k=3)
```

**检索优化:**
```python
# 实现缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query, top_k=3):
    return vector_search(query, top_k)

# 使用示例
result = cached_search("会话备份", 3)
```

---

## 备份策略最佳实践

### 1. 备份频率

**推荐策略:**
| 数据类型 | 频率 | 方式 |
|----------|------|------|
| 代码配置 | 每次修改后 | Git 提交 |
| 工作区文档 | 每日 | 自动备份 |
| VectorBrain 数据库 | 每周 | 完整备份 |
| 会话记录 | 实时 | 自动存入 VectorBrain |

### 2. 备份验证

**每次备份后验证:**
```bash
# 1. 检查文件大小
ls -lh ~/Desktop/skill-[YOUR_INITIALS]002_*.zip

# 2. 验证完整性
unzip -t ~/Desktop/skill-[YOUR_INITIALS]002_*.zip

# 3. 测试恢复（每月）
unzip ~/Desktop/skill-[YOUR_INITIALS]002_*.zip -d ~/Desktop/test_restore
sqlite3 ~/Desktop/test_restore/vectorbrain/memory/knowledge_memory.db "SELECT COUNT(*) FROM knowledge;"
```

### 3. 3-2-1 备份原则

**实施建议:**
- **3 份数据:** 生产 + 本地备份 + 异地备份
- **2 种介质:** 硬盘 + 云端（推荐 GitHub）
- **1 个异地:** 本地 + GitHub 远程仓库

**当前实施:**
```
✅ 生产数据：~/.openclaw/ + ~/.vectorbrain/
✅ 本地备份：~/Desktop/skill-[YOUR_INITIALS]002_*.zip
⚠️ 异地备份：GitHub (需手动推送)
```

---

## 性能优化最佳实践

### 1. 数据库优化

**定期维护:**
```bash
# 每月执行一次
sqlite3 ~/.vectorbrain/memory/episodic_memory.db "VACUUM;"
sqlite3 ~/.vectorbrain/memory/knowledge_memory.db "VACUUM;"

# 清理过期数据（90 天前）
sqlite3 ~/.vectorbrain/memory/episodic_memory.db "DELETE FROM episodes WHERE event_type='system_log' AND timestamp < datetime('now', '-90 days');"
```

**索引优化:**
```sql
-- 为常用查询字段添加索引
CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp);
CREATE INDEX IF NOT EXISTS idx_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_status ON tasks(status);
```

### 2. 查询优化

**避免的查询:**
```sql
-- ❌ 避免：全表扫描
SELECT * FROM episodes WHERE content LIKE '%关键词%';

-- ✅ 推荐：使用索引
SELECT * FROM episodes WHERE timestamp > '2026-03-01';
```

**分页查询:**
```python
# 大数据集使用分页
def search_with_pagination(query, page=1, page_size=10):
    offset = (page - 1) * page_size
    return search(query, limit=page_size, offset=offset)
```

### 3. 内存管理

**推荐做法:**
```python
# ✅ 流式处理大数据集
def process_large_dataset():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM episodes")
    
    for row in cursor:  # 逐条处理，不一次性加载
        process(row)
    
    conn.close()

# ❌ 避免：一次性加载
def process_large_dataset_bad():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM episodes")
    all_rows = cursor.fetchall()  # 可能占用大量内存
    for row in all_rows:
        process(row)
```

---

## 错误处理最佳实践

### 1. 防御性编程

**输入验证:**
```python
def process_user_input(user_input):
    # 验证输入
    if not user_input or not isinstance(user_input, str):
        raise ValueError("Invalid input")
    
    if len(user_input) > 10000:
        raise ValueError("Input too long")
    
    # 处理输入
    return sanitize(user_input)
```

### 2. 错误恢复

**推荐模式:**
```python
def execute_with_retry(func, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logging.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            time.sleep(delay * (attempt + 1))  # 指数退避
```

### 3. 错误日志

**完整错误信息:**
```python
import traceback

def safe_execute(func):
    try:
        return func()
    except Exception as e:
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "function": func.__name__,
            "timestamp": datetime.now().isoformat()
        }
        logging.error(f"Error: {error_info}")
        save_to_reflection({
            "type": "error",
            "details": error_info,
            "lesson": f"需要处理 {func.__name__} 的异常情况"
        })
        raise
```

---

## 文档编写最佳实践

### 1. 文档结构

**推荐模板:**
```markdown
# 文档标题

**版本:** 1.0
**更新时间:** YYYY-MM-DD
**维护人:** 名字

## 概述
[简要说明文档目的]

## 目录
- [章节 1](#章节 1)
- [章节 2](#章节 2)

## 正文
[详细内容]

## 示例
[代码示例或使用示例]

## 相关文档
- [链接 1](./doc1.md)
- [链接 2](./doc2.md)
```

### 2. 代码示例

**好的示例:**
```python
# ✅ 完整、可运行的示例
def search_memory(query):
    """搜索记忆并返回 Top-3 结果"""
    result = vector_search(query, top_k=3)
    return result

# 使用示例
results = search_memory("会话备份")
for r in results:
    print(f"{r['score']}: {r['content']}")
```

**避免的示例:**
```python
# ❌ 不完整、无法运行
def search(query):
    # TODO: 实现
    pass
```

### 3. 文档更新

**更新原则:**
- ✅ 代码变更后立即更新文档
- ✅ 添加更新日期和版本号
- ✅ 记录重大变更
- ✅ 保持示例与代码同步

**变更日志:**
```markdown
## 更新历史

- 2026-03-10: 初始版本
- 2026-03-11: 添加错误处理示例
- 2026-03-15: 更新性能优化章节
```

---

## 📊 检查清单

### 技能开发检查清单
- [ ] skill.json 配置完整
- [ ] SKILL.md 说明清晰
- [ ] 错误处理完善
- [ ] 日志记录充分
- [ ] 依赖列表完整
- [ ] 示例代码可运行

### 记忆管理检查清单
- [ ] 分类合理
- [ ] 命名规范
- [ ] 无重复内容
- [ ] 定期清理过期数据
- [ ] 检索性能良好

### 备份检查清单
- [ ] 每周完整备份
- [ ] 备份验证通过
- [ ] 异地备份完成
- [ ] 恢复测试通过（每月）

---

## 🔗 相关文档

- [系统架构图](./SYSTEM_ARCHITECTURE.md)
- [故障排查手册](./TROUBLESHOOTING.md)
- [快速入门指南](./QUICK_START.md)
- [改进计划](./IMPROVEMENT_PLAN.md)

---

**最后更新:** 2026-03-10  
**下次审查:** 2026-03-17  
**维护状态:** ✅ 活跃维护
