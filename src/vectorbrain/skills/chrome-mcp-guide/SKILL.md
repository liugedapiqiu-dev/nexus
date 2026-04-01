---
name: chrome-mcp-guide
description: 使用 Chrome MCP（首选 hangwin/mcp-chrome）把日常 Chrome 浏览器接入[YOUR_AI_NAME]，实现复用登录态的浏览器控制。
---

# Chrome MCP 接入指南

## 目标
让[YOUR_AI_NAME]优先通过 **Chrome 扩展式 MCP** 接入你平时正在使用的 Google Chrome，而不是只开一个独立自动化浏览器。

## 当前首选方案
- **仓库**：`hangwin/mcp-chrome`
- **定位**：Chrome extension-based MCP server
- **优势**：
  - 复用现有登录态
  - 复用已打开的 Chrome 环境
  - 更适合“个人助理式浏览器控制”

## 当前本机落地资产
- 候选对比：`~/.vectorbrain/integrations/chrome-mcp/CANDIDATE_COMPARISON_2026-03-23.md`
- 本技能：`~/.vectorbrain/skills/chrome-mcp-guide/SKILL.md`

## 标准接入步骤
### 1. 安装本地 bridge
优先命令：
```bash
npm install -g mcp-chrome-bridge
```

### 2. 安装 Chrome 扩展
- 打开 Chrome
- 进入 `chrome://extensions/`
- 开启开发者模式
- 加载下载的扩展目录（来自 `hangwin/mcp-chrome` release）
- 点击扩展并连接 bridge

### 3. MCP 配置（推荐 streamable HTTP）
```json
{
  "mcpServers": {
    "chrome-mcp-server": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:12306/mcp"
    }
  }
}
```

## [YOUR_AI_NAME]后续应如何使用
- 当用户明确要“操控他正在使用的 Chrome / 复用登录态”时，优先考虑本路线。
- 当任务偏“开发调试 / DevTools / 页面诊断”时，可改考虑 `chrome-devtools-mcp` 路线。

## 适用场景
- 操控当前登录中的网站
- 多标签页切换和内容提取
- 截图、点击、填表、书签/历史查询
- 让 AI 像日常助手一样使用浏览器

## 不适用场景
- 完全无人工确认的首次扩展接入
- 纯云浏览器自动化需求
- 企业多租户高隔离浏览器执行场景
