# 🎨 AI 工程助手 UI 学习路线

**创建时间:** 2026-03-13  
**目标:** 让[YOUR_AI_NAME]能够独立设计 AI 工具的前端界面、文档系统、控制台

---

## 📋 学习路线总览

| 层级 | 内容 | 目标 |
|------|------|------|
| 第一层 | AI 工具界面设计标准 | 掌握现代 AI 产品 UI 组件 |
| 第二层 | AI SaaS UI 架构 | 学会控制台布局 |
| 第三层 | AI Chat UI | 实现对话界面 |
| 第四层 | AI Agent 可视化 | 展示任务依赖图 |
| 第五层 | AI IDE 设计 | 理解代码工具界面 |
| 第六层 | AI Agent UI | 多 Agent 监控 |
| 第七层 | 文档系统 | 编写技能文档 |
| 第八层 | 开发者文档设计 | 学习最佳实践 |

---

## 🎯 学习项目列表

### 1️⃣ shadcn/ui
- **官网:** https://ui.shadcn.com
- **用途:** AI 产品界面组件库
- **学习重点:**
  - Sidebar
  - Command
  - Tabs
  - Dialog
  - Card
  - Table

### 2️⃣ Next.js Dashboard
- **GitHub:** https://github.com/vercel/nextjs-dashboard
- **用途:** 标准 SaaS 控制台 UI 模板
- **学习重点:**
  - Dashboard 布局
  - Analytics
  - Table + Filters
  - Charts

### 3️⃣ Vercel AI SDK
- **GitHub:** https://github.com/vercel/ai
- **用途:** AI Chat UI
- **学习重点:**
  - Chat window
  - Message streaming
  - Tool calling
  - Message history

### 4️⃣ LangGraph Studio
- **GitHub:** https://github.com/langchain-ai/langgraph-studio
- **用途:** Agent flow visualization
- **学习重点:**
  - Task graph
  - Tool execution
  - Agent state

### 5️⃣ Continue
- **GitHub:** https://github.com/continuedev/continue
- **用途:** AI IDE 插件
- **学习重点:**
  - Context panel
  - Tool output
  - Streaming messages

### 6️⃣ CrewAI
- **GitHub:** https://github.com/joaomdmoura/crewAI
- **用途:** 多 Agent 监控
- **学习重点:**
  - Agent dashboard
  - Task status
  - Tool usage

### 7️⃣ Docusaurus
- **GitHub:** https://github.com/facebook/docusaurus
- **用途:** 文档系统
- **学习重点:**
  - Docs 结构
  - API 文档
  - Tutorials

### 8️⃣ Vercel 文档
- **官网:** https://vercel.com/docs
- **用途:** 开发者文档设计天花板
- **学习重点:**
  - Page layout
  - Navigation
  - Search
  - Code examples

---

## 🏗️ OpenClaw Studio UI 设计

### 界面结构
```
Sidebar
 ├ Agents
 ├ Skills
 ├ Tasks
 ├ Memory
 ├ Tools
 ├ Logs
 └ Settings

Main
 ├ Chat
 ├ Task Graph
 ├ Execution Logs
```

### 参考产品
- Cursor
- Replit
- Vercel

---

## 📖 文档结构建议

```
OpenClaw Docs
├── Getting Started
│   ├── install
│   └── hello skill
├── Concepts
│   ├── skill lifecycle
│   ├── events
│   └── hooks
├── Development
│   ├── create skill
│   ├── testing
│   └── debugging
├── API
│   ├── gateway api
│   └── plugin api
└── Examples
    ├── feishu skill
    └── vectorbrain skill
```

---

## 🎯 学习任务

### 任务 1: 研究 UI 组件体系
**目标:** 掌握 shadcn/ui 核心组件
**产出:** 组件使用文档

### 任务 2: 学习 Dashboard 布局
**目标:** 理解 SaaS 控制台结构
**产出:** OpenClaw 控制台原型

### 任务 3: 实现 AI Chat 界面
**目标:** 掌握流式消息显示
**产出:** Chat UI 组件

### 任务 4: 设计 Agent 可视化
**目标:** 展示任务依赖图
**产出:** DAG 可视化组件

### 任务 5: 编写技能文档
**目标:** 掌握 Docusaurus
**产出:** OpenClaw 技能文档模板

---

## 🚀 下一步

1. 将学习资源存入 VectorBrain 知识记忆
2. 创建 DAG 学习任务
3. 执行学习计划
4. 产出 OpenClaw Studio UI 设计方案

---

**💡 核心理念:** 不是零散学习，而是通过实际项目（OpenClaw Studio）驱动学习！
