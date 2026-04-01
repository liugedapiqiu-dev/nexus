# 🧠 Nexus Brain

> 一键部署的企业级 AI Agent 智能体环境包
>
> 适配任意 Windows 电脑，开箱即用

---

## 目录

- [震撼登场](#震撼登场)
- [系统要求](#系统要求)
- [快速安装](#快速安装)
- [安装向导详解](#安装向导详解)
- [首次启动配置](#首次启动配置)
- [核心功能详解](#核心功能详解)
- [监控中心](#监控中心)
- [定时任务说明](#定时任务说明)
- [常见问题](#常见问题)

---

## 震撼登场

### 为什么需要 Nexus Brain？

传统 AI 对话的痛点：

```
对话结束 = 记忆消失
第二天 = 一切从头开始
长期任务 = 上下文溢出，遗忘关键信息
```

Nexus Brain 的解决方案：

```
一次对话 → 永久记忆 → 持续进化
```

---

### Nexus 能做什么？

#### 🧠 真正的长期记忆

不是简单的对话存档，而是**语义级别的记忆检索**：

| 能力 | 说明 |
|------|------|
| **向量相似度检索** | 0.01 秒内从百万条记忆中找到最相关的 |
| **跨会话记忆** | 昨天聊的内容，今天继续 |
| **语义理解** | "我想起了上次讨论的那个项目" → 自动定位 |
| **自动归档** | 会话结束自动整理，无需手动操作 |

#### ⚡ 向量检索有多快？

```
传统全文搜索：     100万条 → 2-5 秒
Nexus 向量检索：   100万条 → 0.01 秒 (毫秒级)

提升：200-500 倍
```

基于 FAISS 向量数据库 + nomic-embed-text 嵌入模型，即使在普通 PC 上也能实现毫秒级响应。

#### 🔄 会话归档的革命性优势

**传统方式：**
- 手动导出聊天记录
- 复制粘贴到笔记软件
- 事后整理，耗时耗力

**Nexus 方式：**
```
OpenClaw 会话 → 自动检测 → 智能解析 → 增量归档 → 永久记忆
```

**核心优势：**

| 特性 | 传统方式 | Nexus |
|------|---------|-------|
| 触发方式 | 手动 | 自动 |
| 去重机制 | 无 | 精确去重 |
| 增量更新 | 全量覆盖 | 只增不减 |
| 检索速度 | 秒级 | 毫秒级 |
| 内容保留 | 文本 | 语义向量 |

#### 💓 心脏评分系统

不是打分，而是**行为效果的量化评估**：

```
行动 → 执行 → 评分 → 反馈 → 优化
```

实时监控代理执行效果，自动记录异常，让 AI 越用越聪明。

#### 🌐 技能扩展生态

20+ 预置技能，开箱即用：

| 类别 | 技能 |
|------|------|
| **日历** | 飞书日历、Todoist |
| **项目管理** | Jira、ClickUp |
| **效率** | 自动排程、习惯追踪 |
| **开发** | 浏览器控制、桌面自动化 |
| **记忆** | 三层记忆系统、自动反思 |

---

## 系统要求

### 操作系统

| 版本 | 状态 | 说明 |
|------|------|------|
| Windows 10 (64位) | ✅ 支持 | 专业版/家庭版均可 |
| Windows 11 (64位) | ✅ 支持 | 全版本支持 |
| Windows Server 2019+ | ✅ 支持 | 需要桌面体验 |

> **注意：**
> - 仅支持 64 位系统
> - 需要至少 8GB 内存（16GB 推荐）
> - 需要至少 20GB 可用磁盘空间

### 必须安装的软件

| 软件 | 版本 | 下载地址 | 必须 |
|------|------|----------|------|
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) | ✅ |
| **Python** | 3.10+ | [python.org](https://www.python.org/) | ✅ |
| **Ollama** | 最新 | [ollama.ai](https://ollama.ai/) | ✅ |

### 网络要求

- 安装时需要网络连接
- 首次运行需要下载 `nomic-embed-text` 向量模型（约 300MB）

---

## 快速安装

### 方法一：双击安装（推荐）

```
1. 解压本包到任意目录
2. 双击「安装.bat」
3. 选择 [M] 合并安装
4. 等待安装完成（约 3-5 分钟）
```

### 方法二：PowerShell 命令行

```powershell
cd nexus-brain
.\install\install.ps1 -MergeInstall
```

---

## 安装向导详解

### 安装模式选择

安装程序会自动检测您电脑上是否已有环境：

```
======================================================================
  Nexus Brain 安全安装程序 v4.0
======================================================================

检测到新电脑环境

安装模式选择:
  ┌──────────────────────────────────────────────────────┐
  │  [M] 合并安装 (推荐)                                  │
  │     • 只添加缺失文件                                  │
  │     • 保留原有 OpenClaw 配置                          │
  │     • 保留原有记忆数据库                              │
  │     • 适合已有 OpenClaw 的用户                        │
  ├──────────────────────────────────────────────────────┤
  │  [O] 覆盖安装                                        │
  │     • 完整替换所有文件                                │
  │     • 会丢失原有配置和数据                            │
  │     • 仅新电脑全新安装时使用                          │
  ├──────────────────────────────────────────────────────┤
  │  [Q] 退出                                            │
  └──────────────────────────────────────────────────────┘

请选择 (M/O/Q):
```

> 💡 **推荐选择合并安装**，即使新电脑也没有任何风险

---

### 预检查系统

安装程序会全面检测依赖：

```
======================================================================
  系统预检查
======================================================================

[✓] Node.js v18.17.0      ✅ 已安装
[✓] Python 3.11.9          ✅ 已安装
[✓] Ollama v0.5.6          ✅ 已安装
[✓] pip                    ✅ 已安装
[✓] npm                    ✅ 已安装
[✗] faiss-cpu              ⏳ 未安装 [将由脚本自动安装]
[✗] pyautogui              ⏳ 未安装 [将由脚本自动安装]
[✗] numpy                  ⏳ 未安装 [将由脚本自动安装]
[✗] pandas                 ⏳ 未安装 [将由脚本自动安装]
[✗] nomic-embed-text       ⏳ 未安装 [首次运行时会提示下载]

─────────────────────────────────────────────────────
✅ 所有运行时依赖就绪
⏳ 部分 Python 依赖将由脚本自动安装
❌ Ollama 模型需要手动下载
─────────────────────────────────────────────────────

继续安装? (Y/N):
```

---

### 文件复制过程

```
[3/14] 复制 VectorBrain 新文件...
  ✅ connector     (+127 files)
  ✅ memory        (+45 files)
  ✅ skills        (+23 files)
  ✅ heart         (+18 files)
  ✅ planner       (+12 files)
  ✅ metrics       (+8 files)
  ✅ ...
[OK] VectorBrain 合并完成

[4/14] 复制 OpenClaw 新文件...
  ✅ skills        (+8 files)
  ✅ extensions/vectorbrain  (+15 files)
  ✅ cron          (+3 files)
  ✅ agents        (+5 files)
[OK] OpenClaw 合并完成

[5/14] 注册 VectorBrain 插件...
  ✅ 添加 vectorbrain 到 plugins.allow
  ✅ 添加 vectorbrain 到 plugins.entries
  ✅ 添加 vectorbrain 到 plugins.installs
[OK] VectorBrain 插件注册完成
```

---

### 安装完成

```
======================================================================
  🎉 安装完成!
======================================================================

安装模式: 合并安装 (保留原有配置)

📦 安装摘要:
  VectorBrain: C:\Users\xxx\.vectorbrain
  OpenClaw:    C:\Users\xxx\.openclaw

📋 后续步骤:
  1️⃣  配置 API Keys (复制 .env.template)
  2️⃣  下载 Ollama 模型 (首次运行引导)
  3️⃣  启动 Ollama 服务
  4️⃣  运行首次初始化

======================================================================
```

---

## 首次启动配置

### 1. 配置 API Keys

```powershell
# 复制配置模板
copy $env:USERPROFILE\.vectorbrain\.env.template $env:USERPROFILE\.vectorbrain\.env

# 编辑配置
notepad $env:USERPROFILE\.vectorbrain\.env
```

### 2. 运行首次启动引导

```powershell
python $env:USERPROFILE\.vectorbrain\connector\nexus_bootstrap.py
```

引导程序会自动：

```
✅ 检测 Ollama 服务状态
✅ 检查已安装模型
✅ 下载缺失的模型
✅ 初始化记忆数据库
✅ 配置会话归档器
✅ 设置定时任务
```

### 3. 启动 Ollama

```powershell
ollama serve
```

---

## 核心功能详解

### 向量记忆系统

#### 工作原理

```
用户输入 → nomic-embed-text → 向量嵌入 → FAISS 数据库
                                    ↓
检索时 → 语义相似度匹配 → Top-K 结果 → 返回记忆
```

#### 为什么这么快？

| 技术 | 作用 |
|------|------|
| **nomic-embed-text** | 高质量语义嵌入 |
| **FAISS 索引** | 量化和分区索引 |
| **内存映射** | 避免磁盘 IO |
| **批量处理** | 一次提取多条记忆 |

#### 记忆类型

```
~/.vectorbrain/memory/
├── episodic_memory.db      # 🗂️ 情景记忆 - 对话历史
├── knowledge_memory.db     # 📚 知识图谱 - 概念关系
├── information_memory.db   # 📝 信息库 - 重要摘录
├── habit_memory.db        # 🔄 习惯记忆 - 行为模式
├── heart_memory.db        # 💓 心脏评分 - 效果评估
├── work_memory_hub.db    # 💼 工作记忆 - 任务上下文
└── lessons_memory.db     # 📖 经验总结 - 反思复盘
```

---

### 会话归档系统

#### 核心特性

| 特性 | 说明 |
|------|------|
| **幂等归档** | 多次运行结果一致，不重复归档 |
| **增量更新** | 只处理新增内容，已归档的不再处理 |
| **精确去重** | 基于 record_id + logical_session_id 去重 |
| **文件变化检测** | MD5 哈希检测，文件变化才处理 |
| **断点恢复** | 状态持久化，中断后可继续 |

#### 去重原理

```python
# 每条记录有唯一指纹
fingerprint = f"id:{logical_session_id}:{record_id}"
# 归档前检查注册表，已存在则跳过
INSERT OR IGNORE INTO archive_ingest_records ...
```

#### 归档流程

```
1. 检测 sessions 目录下的 .jsonl 文件
2. 计算文件 MD5，与上次归档对比
3. 无变化 → 跳过
4. 有变化 → 读取新增行
5. 解析每条记录，提取内容
6. 写入去重注册表
7. 写入 episodic_memory.db
8. 更新归档状态
```

---

## 定时任务说明

### 默认执行时间

| 任务 | 频率 | 执行时间 | 功能 |
|------|------|----------|------|
| **Session Archive** | 每小时 | +0:00 | 会话归档 |
| **Chat Scrap** | 每3小时 | +0:00 / +3:00 / +6:00... | 飞书消息抓取 |

### 配置文件位置

```
~/.vectorbrain/cron_config.json
~/.openclaw/cron/nexus_jobs.json
```

### 如何修改执行时间？

编辑 `cron_config.json`：

```json
{
  "jobs": [
    {
      "id": "nexus-session-archive",
      "name": "Nexus Session Archive",
      "enabled": true,
      "schedule": {
        "kind": "every",
        "everyMs": 3600000  // ← 改这里！3600000ms = 1小时
      },
      "action": "archive_sessions"
    },
    {
      "id": "nexus-chat-scrap",
      "name": "Nexus Chat Scrap",
      "enabled": true,
      "schedule": {
        "kind": "every",
        "everyMs": 10800000  // ← 改这里！10800000ms = 3小时
      },
      "action": "--mode incremental"
    }
  ]
}
```

**时间换算参考：**

| everyMs | 实际间隔 |
|---------|----------|
| 1800000 | 30 分钟 |
| 3600000 | 1 小时 |
| 7200000 | 2 小时 |
| 10800000 | 3 小时 |
| 21600000 | 6 小时 |
| 86400000 | 24 小时 |

### 手动触发归档

```bash
python ~/.vectorbrain/connector/session_archiver.py
```

---

## 监控中心

### 启动 Web 监控面板

```bash
cd ~/.openclaw/workspace/skills/openclaw-live-monitor
npm install
node src/server.js
```

访问：**http://localhost:18790/**

### 功能概览

| 功能 | 说明 |
|------|------|
| **实时日志** | WebSocket 推送，毫秒级延迟 |
| **健康评分** | 每分钟自动评估系统状态 |
| **术语翻译** | 技术术语 → 中文解释 |
| **级别过滤** | INFO / WARN / ERROR |
| **历史搜索** | 关键词检索历史日志 |
| **性能图表** | 吞吐量、执行时间趋势 |

### CLI 健康检查

```bash
# 快速状态查看
python ~/.vectorbrain/connector/nexus_health_check.py

# Metrics 仪表盘
python ~/.vectorbrain/metrics/metrics_dashboard.py
```

---

## 常见问题

### Q: 安装时提示「无法加载脚本」？

**解决方法：** 在 PowerShell 中设置执行策略：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 合并安装会覆盖我的 OpenClaw 配置吗？

**不会。** 合并安装只添加缺失的文件：
- ✅ 保留原有的 `openclaw.json`
- ✅ 保留原有的 `workspace/*.md` 人格文件
- ✅ 保留原有的记忆数据库
- ✅ 保留原有的 API Keys 配置

### Q: 首次启动卡在「检查 Ollama 模型」？

**解决步骤：**

```powershell
# 1. 确认 Ollama 已安装
ollama --version

# 2. 手动启动 Ollama
ollama serve

# 3. 在另一个窗口下载模型
ollama pull nomic-embed-text

# 4. 重新运行引导
python $env:USERPROFILE\.vectorbrain\connector\nexus_bootstrap.py
```

### Q: 监控面板无法访问？

**检查清单：**

```powershell
# 1. 确认端口未被占用
netstat -an | findstr 18790

# 2. 确认服务已启动
tasklist | findstr node

# 3. 检查防火墙
#   Windows 防火墙 → 允许应用 → 允许 node.exe 私有网络
```

### Q: 如何完全卸载？

```powershell
# 删除 VectorBrain 主目录
Remove-Item -Recurse $env:USERPROFILE\.vectorbrain

# 删除 Nexus 扩展（保留 OpenClaw 其他部分）
Remove-Item -Recurse $env:USERPROFILE\.openclaw\extensions\vectorbrain

# 取消注册插件（编辑 openclaw.json，移除 vectorbrain 相关配置）
notepad $env:USERPROFILE\.openclaw\openclaw.json
```

---

## 端口清单

| 端口 | 服务 | 状态 | 说明 |
|------|------|------|------|
| 11434 | Ollama | 必须 | LLM 推理服务 |
| 18789 | OpenClaw Gateway | 必须 | Agent 网关 |
| 18790 | Nexus Monitor | 可选 | Web 监控面板 |
| 8999 | VectorBrain API | 可选 | 记忆服务 API |

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        OpenClaw                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │   Skills    │  │  Gateway    │  │  VectorBrain MCP  │   │
│  │   20+ 技能   │  │   18789     │  │     Plugin        │   │
│  └─────────────┘  └─────────────┘  └─────────┬─────────┘   │
└────────────────────────────────────────────────┼────────────┘
                                                 │
                     ┌──────────────────────────┼────────────┐
                     │                          │            │
                     ▼                          ▼            ▼
          ┌──────────────────┐    ┌───────────────┐  ┌────────────┐
          │  Nexus API       │    │   Session     │  │   Ollama   │
          │  (port 8999)     │    │   Archiver    │  │  (向量模型) │
          └────────┬─────────┘    └───────┬───────┘  └────────────┘
                   │                      │
                   ▼                      ▼
          ┌─────────────────────────────────────┐
          │          VectorBrain Memory           │
          │  ┌─────────────────────────────────┐│
          │  │  FAISS 向量引擎                   ││
          │  │  nomic-embed-text 嵌入           ││
          │  │  毫秒级相似度检索                 ││
          │  └─────────────────────────────────┘│
          │  episodic | knowledge | habit | ...  │
          └─────────────────────────────────────┘
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 4.0 | 2026-04-02 | 完全重写，支持合并安装，插件化架构 |
| 3.0 | 2026-03 | 添加心脏评分系统 |
| 2.0 | 2026-02 | 向量记忆系统上线 |
| 1.0 | 2026-01 | 初始版本 |

---

**Nexus Brain - 让 AI Agent 拥有真正的记忆** 🧠
