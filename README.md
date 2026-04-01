# Nexus Brain - AI Agent 环境复制包 v4.0

> 一键将 Nexus AI Agent 环境安装到新电脑
> 智能检测已有环境，合并安装不破坏原有生态
> 自动适配任意路径，真正的开箱即用

---

## 核心特性

### 🧠 自动路径适配
- **动态路径解析** - 所有脚本使用 `nexus_paths.py` 自动检测路径
- **首次运行自动初始化** - `nexus_bootstrap.py` 自动检测 OpenClaw sessions、配置定时任务
- **无需手动配置** - 新电脑直接运行，自动发现所有路径

### 🔒 安全安装
- **合并模式** - 检测到已有 OpenClaw 时，只添加新文件，保留原有配置
- **覆盖模式** - 完整替换（需确认）
- **自动脱敏** - 所有 API Keys 在安装时自动移除

### 📦 完整功能
- ✅ 所有 Python 模块 (memory, heart, planner, intelligence, connector 等)
- ✅ 所有技能 (skills): agent-browser, desktop-control, self-improvement, gupiaozhushou, tavily, jira 等
- ✅ 会话归档系统 - 自动发现 OpenClaw sessions，自动创建定时任务
- ✅ 自动反思引擎 (auto-reflection-engine)
- ✅ VectorBrain MCP 扩展
- ✅ 完整的 workspace 配置

---

## 预检查系统

安装程序会自动检测新电脑的以下依赖：

### 运行时环境

| 软件 | 必须 | 说明 |
|------|------|------|
| Node.js 18+ | ✅ | JavaScript 运行时 |
| Python 3.10+ | ✅ | Python 运行时 |
| Ollama | ✅ | 本地 LLM 推理引擎 |
| Git | ❌ | 版本控制 (可选) |

### Python 包

| 包名 | 必须 | 说明 |
|------|------|------|
| faiss-cpu | ✅ | 向量相似度搜索 |
| pyautogui | ✅ | 桌面自动化 |
| pandas | ✅ | 数据分析 |
| numpy | ✅ | 向量计算 |
| pillow | ✅ | 图片处理 |
| pygetwindow | ✅ | 窗口管理 |
| opencv-python | ❌ | 图像识别 |
| yfinance | ❌ | 股票数据 |

### Ollama 模型

| 模型 | 必须 | 说明 |
|------|------|------|
| qwen2.5:14b | ✅ | 主用模型 |

---

## 快速开始

### 方法 1: 双击安装 (推荐)

```
1. 解压本包到任意目录
2. 双击 "安装.bat"
3. 选择安装模式:
   [M] 合并安装 - 保留原有配置，只添加新文件 (推荐)
   [O] 覆盖安装 - 完整替换
   [Q] 退出
```

### 方法 2: PowerShell

```powershell
cd nexus-brain
.\install\install.ps1 -MergeInstall
```

---

## 自动适配机制

### 1. 路径自动检测

```python
# 所有脚本都使用动态路径
from nexus_paths import VB, OC, get_path

VB.memory_dir       # ~/.vectorbrain/memory (自动检测)
OC.sessions_dir     # ~/.openclaw/agents/main/sessions (自动检测)
```

### 2. 首次运行初始化

首次运行 `nexus_bootstrap.py` 时自动：

```
[1/5] 检测路径...
    VectorBrain: C:\Users\xxx\.vectorbrain
    OpenClaw:   C:\Users\xxx\.openclaw
    Sessions:    C:\Users\xxx\.openclaw\agents\main\sessions

[2/5] 初始化记忆数据库...
    Created: episodic_memory.db
    Created: knowledge_memory.db
    ...

[3/5] 配置会话归档器...
    发现 Sessions: C:\Users\xxx\.openclaw\agents\main\sessions
    创建归档配置...

[4/5] 配置定时任务...
    创建 cron 配置: ~/.vectorbrain/cron_config.json

[5/5] 完成!
```

### 3. 会话归档自动发现

session_archiver.py 自动检测：

1. OpenClaw sessions 目录位置
2. VectorBrain 记忆数据库位置
3. 归档状态文件位置

```python
# 动态路径解析
SESSIONS_DIR = auto_detect_openclaw_sessions()
EPISODIC_DB = auto_detect_vectorbrain_memory() / "episodic_memory.db"
```

### 4. 定时任务自动配置

nexus_bootstrap.py 自动创建定时任务：

| 任务 | 频率 | 功能 |
|------|------|------|
| Session Archive | 每小时 | 自动归档 OpenClaw 会话 |
| Chat Scrap | 每3小时 | 增量抓取飞书消息 |

---

## 合并安装 vs 覆盖安装

### 合并安装 (M) - 推荐

- 只添加 src 中有、目标中没有的文件
- 不覆盖任何已有文件
- 保留: openclaw.json、workspace、skills、记忆数据库、身份

### 覆盖安装 (O)

- 完整替换所有文件
- 会丢失原有的配置和数据
- 仅在新电脑全新安装时使用

---

## 必须安装的软件

### 1. Node.js 18+
https://nodejs.org/

### 2. Python 3.10+
https://www.python.org/

### 3. Ollama
https://ollama.ai/

```bash
ollama pull qwen2.5:14b
ollama serve
```

---

## API Keys 配置

安装后必须配置 API Keys：

```powershell
# 1. 复制模板
copy $env:USERPROFILE\.vectorbrain\.env.template $env:USERPROFILE\.vectorbrain\.env

# 2. 编辑并填写你的 API Keys
notepad $env:USERPROFILE\.vectorbrain\.env
```

### 需要配置的 API Keys

| API | 用途 | 获取地址 |
|-----|------|----------|
| DashScope / OpenAI | LLM 推理 | https://dashscope.console.aliyun.com/ |
| Tavily | 网络搜索 | https://tavily.com/ |
| Brave Search | 网页搜索 | https://brave.com/search/api/ |
| Feishu | 飞书日历 | https://open.feishu.cn/ |

---

## 环境变量

在系统环境变量中设置：

| 变量 | 值 |
|------|-----|
| `CLAUDE_CODE_DIR` | `C:\Users\<用户名>\.vectorbrain` |
| `OPENCLAW_DIR` | `C:\Users\<用户名>\.openclaw` |
| `OLLAMA_HOST` | `127.0.0.1:11434` |

---

## 启动

### 首次启动

```powershell
# 1. 首次运行自动初始化
python $env:USERPROFILE\.vectorbrain\connector\nexus_bootstrap.py

# 2. 启动 Ollama
ollama serve

# 3. 启动钩子
~\.openclaw\hooks\on-start.ps1
```

### 后续启动

```powershell
# 直接运行启动钩子
~\.openclaw\hooks\on-start.ps1
```

---

## 目录结构

```
~/.vectorbrain/           # Nexus VectorBrain 主目录
├── connector/             # 连接器
│   ├── nexus_config.py    # 路径自动配置
│   ├── nexus_bootstrap.py # 首次启动初始化
│   ├── nexus_health_check.py # 健康检查
│   ├── nexus_service_manager.py # 服务管理
│   ├── api_server.py     # API 服务 (port 9000)
│   └── session_archiver.py # 会话归档 (动态路径)
├── memory/               # 向量记忆数据库
├── heart/               # 心脏评分系统
├── planner/             # 任务规划器
├── intelligence/        # 聊天智能分析
├── skills/             # 技能
├── dag/                # DAG 任务调度
└── .nexus_config.json  # 自动生成的配置

~/.openclaw/              # OpenClaw 主目录
├── workspace/            # 工作区 (Nexus 人格配置)
│   ├── IDENTITY.md      # Nexus 身份定义
│   ├── SOUL.md          # 行为准则
│   ├── HEART.md         # 评分系统
│   └── skills/          # 工作区技能
├── skills/              # 平台技能
├── extensions/          # 扩展
│   └── vectorbrain/     # Nexus MCP 扩展
└── hooks/               # Hooks
```

---

## MCP 服务器

| 服务 | 类型 | 地址 |
|------|------|------|
| VectorBrain MCP | stdio | 通过 Gateway |
| Ollama | HTTP | 127.0.0.1:11434 |

---

## 端口清单

| 端口 | 服务 | 说明 |
|------|------|------|
| 11434 | Ollama | LLM 推理服务 |
| 9000 | VectorBrain API | DAG 任务 API |
| 18789 | OpenClaw Gateway | Agent 网关 |

---

## 版本

- **包版本:** 4.0
- **名称:** Nexus Brain
- **日期:** 2026-04-02

---

## 文件清单

```
nexus-brain/
├── README.md              # 本文件
├── 安装.bat                # 双击安装 (选择 M/O/Q)
├── install/
│   └── install.ps1        # v4.0 安全安装脚本
├── src/
│   ├── vectorbrain/       # Nexus VectorBrain (~1.3MB)
│   └── openclaw/          # Nexus OpenClaw (~2.6MB)
└── scripts/
    ├── healthcheck.ps1     # 健康检查
    ├── install-deps.ps1    # 依赖安装
    └── start-all.ps1       # 启动所有服务
```

---

**Nexus Brain - 真正的开箱即用 🧠**
