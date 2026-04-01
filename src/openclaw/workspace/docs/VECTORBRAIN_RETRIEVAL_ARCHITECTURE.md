# 🧠 VectorBrain 检索架构说明

**版本**: 1.0  
**更新时间**: 2026-03-15 23:31 (Asia/Shanghai)  
**维护目标**: 让[YOUR_AI_NAME]的记忆检索始终保持 **大脑优先、向量优先、稳定优先**

---

## 1. 这份文档是干什么的

这份文档说明当前 VectorBrain 的**真实检索架构**，重点回答四个问题：

1. 现在到底在用哪份数据库？
2. 为什么之前会出现“明明有几万条记忆，但搜出来很少”的问题？
3. 现在的正确架构是什么？
4. 以后如果又出问题，应该怎么排查？

一句话目标：

> **不要再让“小脑”接管“大脑”。**

---

## 2. 核心结论

当前采用的是：

> **大脑主检索（FAISS 向量检索） + 小脑增量补充（在线 SQL 检索）**

这是为了同时满足三个目标：

- **快**：优先使用 FAISS 向量索引
- **准**：优先使用历史大脑数据（几万条）
- **稳**：保留当前在线小库的实时写入能力，不粗暴切断现有运行链路

---

## 3. 当前架构一览

## 3.1 知识记忆（Knowledge Memory）

### 当前主库
- `~/.vectorbrain/memory/knowledge_memory.db`

### 当前检索方式
- Ollama 生成 query embedding
- FAISS 检索 `~/.vectorbrain/memory/knowledge.index`
- SQLite 回表 `knowledge_memory.db`

### 当前状态
- **已切回大脑版本**
- 当前记录数约：**2308 条**
- 检索已恢复正常

### 当前目标
知识记忆是：
- 长期知识
- 提炼经验
- 项目背景
- 个人习惯/偏好
- 流程规则
- 历史决策

---

## 3.2 情景记忆（Episodic Memory）

### 当前架构
情景记忆不是直接硬切在线库，而是采用：

- **主检索**：大脑历史库 + FAISS + metadata
- **增量补充**：在线小脑库 SQL 检索

### 组成

#### A. 大脑历史检索层
- 索引：`~/.vectorbrain/memory/episodic.index`
- 元数据：`~/.vectorbrain/memory/episodic_metadata.json`
- 主历史库：
  - `~/.vectorbrain/backups/restore_candidate_20260314_120845/skill-[YOUR_INITIALS]002_2026-03-11/vectorbrain/episodic_memory.db`

#### B. 在线增量层
- `~/.vectorbrain/memory/episodic_memory.db`

### 为什么这样设计
因为：

- 大脑历史库里有几万条记忆
- 在线小脑库还承担当前系统的写入逻辑
- 两者 schema 不一致
- 如果粗暴硬切，容易把现有运行链路弄断

所以现在采取的是：

> **历史用大脑查，增量用小脑补，避免失忆，也避免系统炸掉。**

---

## 4. 为什么之前会出问题

之前出现的问题不是“记忆没了”，而是：

> **索引看的是大脑，回表查的是小脑。**

这会导致：

- FAISS 检索命中的是大脑时代的数据
- 但 SQLite 查询却在当前在线小库里找记录
- 结果就是：
  - 要么查不到
  - 要么结果很少
  - 要么用户感觉像“失忆”

### 当时发现的典型错位

#### 小脑在线库
- `~/.vectorbrain/memory/knowledge_memory.db` → 一度只有 **10 条**
- `~/.vectorbrain/memory/episodic_memory.db` → 约 **285 条**

#### 大脑相关资产
- `knowledge.index` → **4150 vectors**
- `episodic.index` → **41895 vectors**
- `episodic_metadata.json` → **41895 条**

这说明：

- 索引和 metadata 明显来自“大脑时代”
- 在线数据库却是“小脑时代”

所以根本问题是：

> **数据库、索引、metadata 三件套不同步。**

---

## 5. 当前数据库真实情况

## 5.1 在线知识库
- 路径：`~/.vectorbrain/memory/knowledge_memory.db`
- 当前已切回大脑版本
- 记录数：约 **2308**

## 5.2 在线情景小脑库
- 路径：`~/.vectorbrain/memory/episodic_memory.db`
- 当前仍保留，用于在线增量和兼容现有写入逻辑

### 当前在线小脑 schema
#### `episodes`
- `episode_id`
- `task_id`
- `timestamp`
- `task_type`
- `task_input`
- `task_output`
- `status`
- `execution_time`
- `success`

#### `conversations`
- `id`
- `chat_id`
- `chat_name`
- `message_id`
- `sender_id`
- `sender_name`
- `content`
- `timestamp`
- `msg_type`
- `metadata`
- `created_at`

## 5.3 大脑历史情景库
- 正式主路径：
  - `~/.vectorbrain/memory/episodic_memory.db`
- 数据来源：
  - 从 `skill-[YOUR_INITIALS]002_2026-03-11` 备份原封不动覆盖回同名文件
- 记录数：约 **23975**

### 大脑历史库 schema
#### `episodes`
- `id`
- `timestamp`
- `worker_id`
- `event_type`
- `content`
- `metadata`
- `created_at`

注意：

> **大脑历史库和在线小脑库 schema 不一致。**

这就是为什么不能粗暴直接替换情景库。

---

## 6. 当前检索策略

## 6.1 知识检索策略

### 主路径
1. 用户输入 query
2. Ollama 生成 embedding
3. FAISS 检索 `knowledge.index`
4. 按命中 ID 回查 `knowledge_memory.db`
5. 返回 Top-K 结果

### 兼容策略
由于知识库存在新旧 schema 混用历史，检索代码已做兼容：

#### 新 schema（小脑时代）
- `id, content, metadata, source, importance, created_at`

#### 旧 schema（大脑时代）
- `id, category, key, value, source_worker, confidence, created_at, updated_at, embedding_vector`

当前检索代码会自动判断字段结构并选择正确回表方式。

---

## 6.2 情景检索策略

### 主路径
1. 用户输入 query
2. Ollama 生成 embedding
3. FAISS 检索 `episodic.index`
4. 通过 `episodic_metadata.json` 找到命中的 metadata
5. 优先尝试回查**大脑历史情景库**
6. 如果回表失败，则退回 metadata 中保存的内容摘要
7. 再补查在线小脑库中的最近增量记录
8. 合并、去重、排序后返回

### 当前原则

> **FAISS 主脑优先，SQL 小脑兜底。**

这保证了：

- 历史几万条记忆可检索
- 最新在线内容也不会完全丢
- 不破坏当前在线写入能力

---

## 7. 当前速度表现

以下为 2026-03-15 晚上的实测结果（端到端）：

### 知识检索
- `蜘蛛侠书包 项目` → ~264ms
- `备份 经验` → ~246ms
- `机会提醒` → ~248ms
- `健豪 习惯` → ~241ms

### 情景检索
- `蜘蛛侠书包 项目` → ~335ms
- `项目 进展` → ~330ms
- `设计 文件` → ~334ms

### 解释
这类耗时已经包含：
- query embedding 生成
- FAISS 检索
- SQLite 回表/结果整理

真正最慢的通常不是 FAISS，而是：

- **Ollama embedding 生成**

所以如果未来要继续提速，优先考虑优化 embedding 阶段，而不是怀疑 FAISS。

---

## 8. 这套架构为什么是目前最优解

## 优点

### 1. 不失忆
大脑历史记忆重新接管主检索，避免只看到几百条小库内容。

### 2. 不炸系统
没有粗暴替换在线情景库，所以现有写入逻辑仍能继续跑。

### 3. 检索速度快
向量主检索仍然走 FAISS，速度足够快。

### 4. 可平滑过渡
后续如果要统一 schema，可以慢慢迁移，不需要停机硬切。

---

## 9. 已做的关键修复

本次已完成：

- 修复 `vector_search.py` 的 knowledge schema 漂移问题
- 修复 `vectorbrain_speed_test.py` 的知识库 schema 漂移问题
- 将在线知识主库切回大脑版本
- 将情景检索改为：
  - 大脑主检索
  - 小脑增量补充
- 恢复蜘蛛侠书包等真实项目内容的检索命中
- 在切换前创建了完整快照备份

---

## 10. 备份与回滚

## 本次切换前备份目录
- `~/.vectorbrain/backups/live_switch_20260315_232247/`

### 其中包含
- `knowledge_memory.db.before`
- `episodic_memory.db.before`
- `knowledge.index.before`
- `episodic.index.before`
- `episodic_metadata.json.before`

如果后续真的出现需要回滚的情况，可以用这套备份恢复到切换前状态。

---

## 11. 以后怎么排查问题

如果哪天又出现“记忆不对劲”“搜不出来”“像失忆”的情况，按下面顺序检查。

## 第一步：看知识库是不是还在大脑版本
检查：
- `~/.vectorbrain/memory/knowledge_memory.db`

确认：
- 记录数是否仍在 **2000+** 级别
- 而不是掉回十几条/几十条

如果掉回很小的数量，说明知识主库又被替换成小脑版本了。

---

## 第二步：看索引数量和主库是否匹配
检查：
- `knowledge.index`
- `episodic.index`
- `episodic_metadata.json`

重点关注：
- `knowledge.index.ntotal`
- `episodic.index.ntotal`
- `episodic_metadata.json` 的长度

如果出现这种情况：
- 索引几千/几万
- 数据库只有几十/几百

那就说明：

> **索引和数据库又脱节了。**

---

## 第三步：看检索脚本是否又被改坏
重点文件：
- `~/.vectorbrain/connector/vector_search.py`
- `~/.openclaw/workspace/vectorbrain_speed_test.py`

重点看：
- 是否还兼容新旧 knowledge schema
- 情景检索是否仍然使用：
  - 大脑主检索
  - 小脑增量补充

---

## 第四步：看在线写入是否正常
如果用户说“最近的新记忆搜不到”，就检查：
- 小脑在线库有没有继续写入
- conversations / episodes 是否有新增

因为当前架构是：
- 历史靠大脑
- 增量靠小脑

如果小脑不写了，就会表现为“旧记忆能搜，新记忆不灵”。

---

## 12. 当前推荐原则

未来维护 VectorBrain 时，遵守这几个原则：

### 原则 1
> **大脑负责历史主检索，小脑负责实时增量。**

### 原则 2
> **不要在未检查 schema 的情况下直接替换数据库。**

### 原则 3
> **不要让 index / metadata / sqlite 三件套分家。**

### 原则 4
> **先备份，再切换。**

### 原则 5
> **优先保留向量主检索链路，不要轻易退回纯 SQL 模糊匹配。**

---

## 13. 未来优化方向

如果后续还要继续提升系统，可以按这个方向走：

### 1. 统一情景库 schema
最终把大脑历史库和在线小脑库统一成一套结构，减少兼容逻辑。

### 2. 重建完全一致的索引体系
确保：
- FAISS index
- metadata
- sqlite 主库

始终来自同一份数据源。

### 3. 优化 embedding 延迟
由于当前瓶颈主要在 embedding 生成，可以考虑：
- embedding 服务常驻优化
- 查询缓存
- 热词缓存
- 批量 embedding

### 4. 增量自动入脑
把小脑新增内容定时向量化并并入大脑索引，减少历史/实时割裂。

---

## 14. 最后的定义

当前这套架构不是“临时补丁”，而是：

> **一个现实可用、性能不错、且兼容现状的过渡型最佳实践架构。**

在完全统一 schema 之前，它是最适合当前系统状态的方案。

---

## 15. 一句话版本

> **现在的 VectorBrain 检索架构是：大脑做主检索，小脑做增量补充，FAISS 做高速向量搜索，Ollama 做 embedding，目标是既不失忆，也不炸系统。**

---

**维护建议**: 如果以后有人要动数据库、索引、metadata、检索脚本，先读完这份文档再动手。  
**备注**: 如果未来彻底统一 schema，这份文档需要更新到 2.0 版。
这份文档需要更新到 2.0 版。
�份文档需要更新到 2.0 版。
