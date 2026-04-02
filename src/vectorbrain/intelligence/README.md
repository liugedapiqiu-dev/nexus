# 🕵️ 群聊情报网 - 使用指南

## 系统概述

## ⚠️ Phase 1 SSOT 维护口径（2026-03-19）

当前这套群聊抓取系统，维护时请只认下面这条主链：

- 主入口：`~/.vectorbrain/intelligence/chat_scraper_v2.py`
- 主结构化日志：`~/.vectorbrain/chat_scraper_log.jsonl`
- 主文本日志：`~/.vectorbrain/chat_scraper.log`
- 主状态：`~/.vectorbrain/chat_scraper_state.json`
- 最终数据面：`~/.vectorbrain/memory/episodic_memory.db -> conversations`

**禁止作为主判据：**
- `chat_scraper.py`
- `monitor_spiderman_group*.py`
- `intelligence/scraper_v2.log.deprecated-2026-03-19`
- `intelligence/chat_scraper_state.json.deprecated-2026-03-19`
- dashboard 页面或口头观察

真正验收时，必须同时核对：事件日志完成、state 推进、`conversations` 真入库。


群聊情报网是一个自动化的飞书群聊监控系统，它会：
- ✅ 每小时自动抓取所有群的聊天记录
- ✅ 将消息存储到 VectorBrain 向量数据库
- ✅ 提取重要信息（采购、质量、交期等）
- ✅ 在你询问时提供智能分析报告
- ✅ 平时保持安静，不问不说

## 监控的群组

| 群名 | 说明 |
|------|------|
| 蜘蛛侠 Switch 设计沟通 | 蜘蛛侠项目设计讨论 |
| 采购信息同步 | 采购订单、供应商信息 |
| 醇龙箱包对接 | 醇龙箱包业务 |
| 监督虾 | 外部监督群 |
| agent | 测试/自动化群 |

## 自动任务

### 每小时执行
- **脚本**: `chat_scraper_v2.py`（当前主链）
- **时间**: 每小时整点
- **功能**: 抓取所有群的新消息，保存到数据库

### 日志文件
- **位置**: `~/.vectorbrain/chat_scraper.log`
- **状态**: `~/.vectorbrain/chat_scraper_state.json`

## 查询方式

### 方式 1: 直接问我（推荐）
直接飞书私聊问我问题，例如：
- "最近有什么采购订单？"
- "蜘蛛侠项目有什么进展？"
- "有没有质量问题需要处理？"
- "各群最近在讨论什么？"
- "醇龙箱包那边有什么消息？"

我会自动查询数据库并给你分析报告。

### 方式 2: 命令行查询
```bash
# 查看帮助
python3 ~/.vectorbrain/intelligence/intelligence_cmd.py

# 查询问题
python3 ~/.vectorbrain/intelligence/intelligence_cmd.py "最近有什么采购订单？"

# 指定时间范围（最近 24 小时）
python3 ~/.vectorbrain/intelligence/intelligence_cmd.py "质量问题" 24
```

### 方式 3: 生成完整报告
```bash
# 生成最近 24 小时的详细报告
python3 ~/.vectorbrain/intelligence/chat_analyzer.py 24

# 生成最近 7 天的详细报告
python3 ~/.vectorbrain/intelligence/chat_analyzer.py 168

# 快速摘要
python3 ~/.vectorbrain/intelligence/chat_analyzer.py --quick 24
```

## 数据存储

### 情景记忆库
- **路径**: `~/.vectorbrain/memory/episodic_memory.db`
- **内容**: 所有群的原始聊天记录
- **表名**: `conversations`

### 知识记忆库
- **路径**: `~/.vectorbrain/memory/knowledge_memory.db`
- **内容**: 提取的重要信息（高价值情报）
- **表名**: `knowledge`

### 情报目录
- **路径**: `~/.vectorbrain/intelligence/`
- **内容**: 脚本、日志、报告

## 信息分类

系统会自动识别以下类别的消息：

| 类别 | 关键词 | 说明 |
|------|--------|------|
| 🛒 采购 | 采购、下单、订单、PO | 采购相关 |
| 🏭 生产 | 生产、加工、工厂、排期 | 生产进度 |
| ⚠️ 质量 | 质量、问题、不良、验货 | 质量问题 |
| 📦 交期 | 交期、交货、发货、物流 | 交付信息 |
| 💰 财务 | 付款、收款、发票、价格 | 财务事项 |
| 🎨 设计 | 设计、图纸、样品、打样 | 设计相关 |
| 🚨 紧急 | 紧急、急、尽快、马上 | 紧急事项 |

## 报告示例

当你询问时，我会提供：

1. **总体统计** - 消息数量、涉及群数
2. **紧急消息** - 优先显示需要立即处理的
3. **按类别统计** - 各类消息的分布
4. **各群动态** - 每个群的最新讨论
5. **重要知识** - 提取的高价值信息
6. **需要重视的信息** - 采购、质量、交期、财务等重点事项

## 管理系统

### 查看定时任务
```bash
crontab -l | grep chat_scraper
```

### 手动执行一次
```bash
python3 ~/.vectorbrain/intelligence/chat_scraper_v2.py
```

### 查看执行日志
```bash
tail -50 ~/.vectorbrain/chat_scraper.log
```

### 查看状态
```bash
cat ~/.vectorbrain/chat_scraper_state.json
```

## 注意事项

1. **数据库会自动增长** - 定期清理旧数据（未来可添加自动归档）
2. **飞书 API 限制** - 每小时抓取不会触发限流
3. **隐私安全** - 所有数据本地存储，不会外泄
4. **系统依赖** - 需要 Python 3.7+ 和 requests 库

## 故障排查

### 没有新消息？
- 检查飞书 API token 是否有效
- 查看日志：`tail ~/.vectorbrain/intelligence/scraper.log`
- 确认群 ID 配置正确

### 查询不到结果？
- 确认数据库文件存在
- 检查时间范围是否合适
- 尝试扩大查询范围（如从 24 小时改为 168 小时）

## 扩展功能（未来）

- [ ] 自动周报生成
- [ ] 关键事件告警（发现紧急消息时主动通知）
- [ ] 消息情绪分析
- [ ] 任务自动提取和跟踪
- [ ] 供应商/项目维度聚合

---

**最后更新**: 2026-03-13
**版本**: 1.0

## ⚠️ 2026-03-19 日志口径修正

当前**全群增量抓取**实际应以以下日志为准：

- `~/.vectorbrain/chat_scraper.log`
- `~/.vectorbrain/chat_scraper_log.jsonl`

`~/.vectorbrain/intelligence/` 目录下旧的：
- `scraper_v2.log.deprecated-2026-03-19`
- `chat_scraper_state.json.deprecated-2026-03-19`

以上文件已归档为**历史遗留/旧口径日志**，不再作为“最新执行状态”的主判断依据。


