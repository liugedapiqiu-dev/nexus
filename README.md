# 🧠 Nexus Brain

> 一键部署的 AI Agent 智能体环境包
>
> 适配任意 Windows 电脑，开箱即用

---

## 目录

- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [快速安装](#快速安装)
- [安装向导详解](#安装向导详解)
- [首次启动配置](#首次启动配置)
- [核心功能介绍](#核心功能介绍)
- [监控中心](#监控中心)
- [常见问题](#常见问题)

---

## 功能特性

### 🧠 智能记忆系统

| 记忆类型 | 说明 |
|---------|------|
| **情景记忆** | 存储对话历史，跨会话保持上下文 |
| **知识图谱** | 结构化知识管理，自动关联 |
| **信息库** | 重要信息长期保存 |
| **习惯记忆** | 行为模式学习 |
| **工作记忆** | 任务规划与执行 |

### 🔄 自动反思引擎

- 周期性自我复盘
- 经验提取与总结
- 行为优化建议

### 📊 任务规划与调度

- DAG 有向无环图任务编排
- 定时任务自动执行
- 任务依赖管理

### 🎯 心脏评分系统

- 行动效果量化评估
- 健康度实时监控
- 趋势分析与告警

### 🌐 技能扩展

- 20+ 预置技能（飞书日历、Todoist、Jira 等）
- 自定义技能加载
- 技能市场生态

### 📈 实时监控

- Web 端实时日志
- 健康自检评分
- 性能指标追踪

---

## 系统要求

### 操作系统

| 版本 | 状态 | 说明 |
|------|------|------|
| Windows 10 | ✅ 支持 | 64位专业版/家庭版 |
| Windows 11 | ✅ 支持 | 64位全版本 |
| Windows Server 2019+ | ✅ 支持 | 需要桌面体验 |

> **注意：** 需要 64 位操作系统

### 必须安装的软件

| 软件 | 版本 | 下载地址 | 说明 |
|------|------|----------|------|
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) | JavaScript 运行时 |
| **Python** | 3.10+ | [python.org](https://www.python.org/) | Python 运行时 |
| **Ollama** | 最新 | [ollama.ai](https://ollama.ai/) | 本地 LLM 推理引擎 |

### 网络要求

- 安装时需要网络连接（下载依赖和模型）
- 首次运行需要下载 `nomic-embed-text` 向量模型（约 300MB）

---

## 快速安装

### 方法一：双击安装（推荐）

```
1. 解压本包到任意目录
2. 双击「安装.bat」
3. 选择安装模式
4. 等待安装完成
```

### 方法二：命令行安装

```powershell
cd nexus-brain
.\install\install.ps1 -MergeInstall
```

---

## 安装向导详解

### 第一步：选择安装模式

安装程序会检测您电脑上是否已有环境：

```
======================================================================
  Nexus Brain 安全安装程序 v4.0
======================================================================

检测到新电脑环境

安装模式选择:
  [M] 合并安装 (推荐) - 保留原有配置，只添加新文件
  [O] 覆盖安装 - 完整替换（会丢失原有配置）
  [Q] 退出

请选择 (M/O/Q):
```

#### 合并安装（推荐）

- 只添加缺失的文件
- 不覆盖任何已有配置
- 保留原有的 OpenClaw 配置、人格文件、记忆数据库
- **适用于已有 OpenClaw 环境的用户**

#### 覆盖安装

- 完整替换所有文件
- 会丢失原有的配置和数据
- **仅在新电脑全新安装时使用**

---

### 第二步：预检查系统

安装程序会检测依赖是否满足：

```
======================================================================
  系统预检查
======================================================================

[✓] Node.js v18.17.0      已安装
[✓] Python 3.11.9         已安装
[✓] Ollama                 已安装
[✓] pip                    已安装
[✓] npm                    已安装
[✗] faiss-cpu              未安装 [会自动安装]
[✗] pyautogui              未安装 [会自动安装]
[✗] nomic-embed-text       未安装 [首次运行时会提示下载]
...

继续安装? (Y/N):
```

---

### 第三步：文件复制

安装程序会自动创建目录结构并复制文件：

```
[3/14] 复制 VectorBrain 新文件...
  Added 127 files to connector
  Added 45 files to memory
  Added 23 files to skills
[OK] VectorBrain 合并完成

[4/14] 复制 OpenClaw 新文件...
  Added 8 files to skills
  Added 15 files to extensions/vectorbrain
[OK] OpenClaw 合并完成
```

---

### 第四步：插件注册

自动将 Nexus Brain 插件注册到 OpenClaw：

```
[5/14] 注册 VectorBrain 插件...
  添加 vectorbrain 到 plugins.allow
  添加 vectorbrain 到 plugins.entries
  添加 vectorbrain 到 plugins.installs
[OK] VectorBrain 插件注册完成
```

---

### 第五步：脱敏处理

自动移除配置文件中的敏感信息：

```
[6/14] 脱敏处理 - 移除 API Keys...
[OK] API Keys 已脱敏
```

---

### 第六步：安装完成

```
======================================================================
  安装完成!
======================================================================

安装模式: 合并安装 (保留原有配置)

安装摘要:
  VectorBrain: C:\Users\xxx\.vectorbrain
  OpenClaw:    C:\Users\xxx\.openclaw

后续步骤:
1. 配置 API Keys
2. 下载 Ollama 模型
3. 首次启动 Nexus
4. 启动 Ollama
```

---

## 首次启动配置

### 1. 配置 API Keys

```powershell
# 复制配置模板
copy $env:USERPROFILE\.vectorbrain\.env.template $env:USERPROFILE\.vectorbrain\.env

# 编辑配置文件
notepad $env:USERPROFILE\.vectorbrain\.env
```

### 2. 下载 Ollama 模型

运行首次启动引导：

```powershell
python $env:USERPROFILE\.vectorbrain\connector\nexus_bootstrap.py
```

程序会检测并自动下载缺失的模型：

```
[0/6] 检查 Ollama 模型...
  已安装模型: 无
  缺少以下模型:
    - nomic-embed-text: 向量模型 (必须)

  是否自动下载? (Y/n): Y
  下载 nomic-embed-text...
  ✅ nomic-embed-text 下载完成
```

### 3. 启动 Ollama

```powershell
ollama serve
```

---

## 核心功能介绍

### VectorBrain 记忆系统

VectorBrain 是 Nexus 的核心记忆引擎，基于向量相似度搜索：

```
~/.vectorbrain/memory/
├── episodic_memory.db      # 情景记忆
├── knowledge_memory.db      # 知识图谱
├── information_memory.db    # 信息库
├── habit_memory.db         # 习惯记忆
├── heart_memory.db         # 心脏评分
├── work_memory_hub.db      # 工作记忆
└── lessons_memory.db       # 经验总结
```

### Session Archiver 会话归档

自动将 OpenClaw 会话归档到 VectorBrain：

```
OpenClaw 会话 → session_archiver.py → episodic_memory.db
```

每小时自动执行增量归档，只插入新的记录。

### DAG 任务调度

可视化任务编排系统：

```
任务A → 任务B → 任务D
   ↓
任务C → 任务E → 任务F
```

支持任务依赖、并行执行、失败重试。

### 心脏评分系统

量化评估行动效果：

| 分数 | 状态 | 说明 |
|------|------|------|
| 90-100 | 🟢 优秀 | 超出预期 |
| 70-89 | 🔵 良好 | 正常完成 |
| 50-69 | 🟡 一般 | 需要改进 |
| <50 | 🔴 警告 | 需要关注 |

---

## 监控中心

### 启动监控面板

```bash
cd ~/.openclaw/workspace/skills/openclaw-live-monitor
npm install
node src/server.js
```

然后访问：**http://localhost:18790/**

### 功能概览

| 功能 | 说明 |
|------|------|
| 实时日志 | WebSocket 推送的日志流 |
| 健康评分 | 每分钟自动打分 |
| 级别过滤 | INFO / WARN / ERROR |
| 历史搜索 | 日志历史查询 |
| 性能图表 | 吞吐量和执行时间 |

### CLI 监控

```bash
# 系统健康检查
python ~/.vectorbrain/connector/nexus_health_check.py

# Metrics 仪表盘
python ~/.vectorbrain/metrics/metrics_dashboard.py
```

---

## 常见问题

### Q: 安装时提示「无法加载脚本」？

**解决方法：** 以管理员身份运行 PowerShell：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 合并安装会覆盖我的配置吗？

**不会。** 合并安装只添加缺失的文件，所有原有配置都会保留。

### Q: 首次启动卡在「检查 Ollama 模型」？

**解决方法：**
1. 确保 Ollama 已安装：`ollama --version`
2. 手动启动 Ollama：`ollama serve`
3. 手动下载模型：`ollama pull nomic-embed-text`

### Q: 监控面板无法访问？

**检查步骤：**
1. 确认已运行 `npm install`
2. 确认端口 18790 未被占用
3. 检查防火墙设置

### Q: 如何卸载？

Nexus Brain 采用绿色安装，卸载只需：

```powershell
# 删除安装目录
Remove-Item -Recurse $env:USERPROFILE\.vectorbrain
Remove-Item -Recurse $env:USERPROFILE\.openclaw\extensions\vectorbrain
```

---

## 端口清单

| 端口 | 服务 | 说明 |
|------|------|------|
| 11434 | Ollama | LLM 推理服务 |
| 18789 | OpenClaw Gateway | Agent 网关 |
| 18790 | Nexus Monitor | 监控面板 |
| 8999 | VectorBrain API | 记忆服务 |

---

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     OpenClaw                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Skills    │  │   Gateway   │  │ VectorBrain MCP │ │
│  └─────────────┘  └─────────────┘  └────────┬────────┘ │
└──────────────────────────────────────────────┼──────────┘
                                               │
                    ┌──────────────────────────┼──────────┐
                    │                          │          │
                    ▼                          ▼          ▼
         ┌──────────────────┐    ┌───────────────┐  ┌─────────┐
         │   Nexus API      │    │ Session       │  │ Ollama  │
         │   (port 8999)    │    │ Archiver      │  │         │
         └────────┬─────────┘    └───────┬───────┘  └─────────┘
                  │                      │
                  ▼                      ▼
         ┌─────────────────────────────────────┐
         │          VectorBrain Memory         │
         │  episodic | knowledge | habit | ... │
         └─────────────────────────────────────┘
```

---

## 版本信息

- **版本：** 4.0
- **发布日期：** 2026-04-02
- **许可证：** MIT

---

**Nexus Brain - 让 AI Agent 环境部署变得简单** 🧠
