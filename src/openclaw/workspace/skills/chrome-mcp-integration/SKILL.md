---
name: chrome-mcp-integration
description: 使用 Chrome MCP（首选 hangwin/mcp-chrome）接入你当前正在使用的 Google Chrome，复用登录态实现浏览器控制。
---

# Chrome MCP Integration

## 目标
让[YOUR_AI_NAME]在需要“直接使用你当前 Chrome、复用登录态、操作真实标签页”时，优先考虑 **Chrome 扩展式 MCP** 路线，而不是只依赖独立自动化浏览器。

## 当前选型
### 首选方案
- 仓库：`hangwin/mcp-chrome`
- 本机 bridge：`mcp-chrome-bridge`
- 本机 MCP 地址：`http://127.0.0.1:12306/mcp`

## 当前本机状态（2026-03-23）
- `mcp-chrome-bridge` 已安装成功
- Native Messaging host 已注册成功
- Chrome 扩展已可加载目录：
  - `~/.vectorbrain/integrations/chrome-mcp/extension-built`
- 当扩展点击 **Connect** 后，`mcp-chrome-bridge doctor` 已能通过 connectivity 检查

## 长期资产位置
- 候选对比：`~/.vectorbrain/integrations/chrome-mcp/CANDIDATE_COMPARISON_2026-03-23.md`
- 本机接入状态：`~/.vectorbrain/integrations/chrome-mcp/LOCAL_INTEGRATION_STATUS_2026-03-23.md`
- 扩展源码仓库：`~/.vectorbrain/integrations/chrome-mcp/mcp-chrome-repo`
- 可加载扩展目录：`~/.vectorbrain/integrations/chrome-mcp/extension-built`
- 本技能：`~/.openclaw/workspace/skills/chrome-mcp-integration/SKILL.md`

## 什么时候优先用这条路线
优先在这些场景考虑 Chrome MCP：
- 用户明确要求“操控我现在正在用的 Chrome”
- 需要复用现有登录态
- 需要操作已有标签页、多窗口、多标签上下文
- 需要访问浏览器历史、书签、网络、当前页面交互元素

## 什么时候不用这条路线
以下场景仍优先现有 browser 工具或普通浏览器自动化：
- 只需要打开一个隔离浏览器做普通网页操作
- 只需要简单网页抓取，不需要复用登录态
- 当前 Chrome 扩展未连接 / 本机 bridge 未通
- 需要完全无人工确认的首次接入

## 连接自检
### 检查 bridge 与扩展是否连通
```bash
mcp-chrome-bridge doctor
```

### 关键成功信号
- `Connectivity: GET http://127.0.0.1:12306/ping -> 200`

## 用户需要做的唯一人工动作
如果 doctor 提示未连接：
1. 打开 Chrome
2. 打开 mcp-chrome 扩展
3. 点击 **Connect**
4. 重新运行 `mcp-chrome-bridge doctor`

## 当前限制
- 当前这条能力已经“接通”，但还没有变成 OpenClaw 内建的一等 browser tool。
- 也就是说，它更像“已接入的外部 MCP 浏览器通道”，而不是自动出现在默认工具列表里的内建工具。
- 后续若要进一步深度融合，需要在宿主/客户端侧把 `http://127.0.0.1:12306/mcp` 正式注册进 MCP server 配置。

## 简化结论
- **桥接层已通**
- **扩展已能加载并连接**
- **[YOUR_AI_NAME]体系已记录这条路线**
- **适合用于复用你真实 Chrome 登录态的浏览器控制**
