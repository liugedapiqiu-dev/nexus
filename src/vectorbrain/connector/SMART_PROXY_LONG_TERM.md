# 🎯 长期目标：Smart Proxy 智能模型路由代理

**创建时间：** 2026-03-11 23:06  
**优先级：** ⭐⭐⭐ (中优先级)  
**状态：** ⏸️ 暂停（等待 Ollama 接口稳定性问题解决）

---

## 📋 目标描述

实现无缝断网自动降级：
- **网络正常时：** 使用云端 Qwen3.5-plus（聪明）
- **网络断开时：** 自动切换到本地 Ollama qwen2.5:14b（稳定）
- **要求：** 不重启 Gateway，用户无感知

---

## ✅ 已完成的工作

1. ✅ Gemini 老师提供完整代码和架构设计
2. ✅ Smart Proxy 代码已创建 (`smart_proxy.py`)
3. ✅ 依赖已安装 (fastapi, uvicorn, httpx)
4. ✅ 服务成功启动（端口 8000，PID 2323）
5. ✅ 黑盒测试方法已掌握
6. ✅ 健康检查和基础功能验证通过

---

## ❌ 遇到的问题

### Ollama OpenAI 兼容接口不稳定

**现象：**
- `/v1/chat/completions` 端点有时返回 502 Bad Gateway
- 即使模型已预热，仍然可能失败
- 原生 `/api/chat` 端点完全正常

**测试结果：**
```bash
# 原生 API - 成功 ✅
curl -X POST http://localhost:11434/api/chat \
  -d '{"model": "qwen2.5:14b", "messages": [{"role": "user", "content": "你好"}], "stream": false}'

# OpenAI 兼容 API - 有时失败 ❌
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:14b", "messages": [{"role": "user", "content": "你好"}], "stream": false}'
```

**根本原因：**
- Ollama 的 OpenAI 兼容接口本身稳定性问题
- 不是代码逻辑问题
- 可能需要等待 Ollama 后续版本修复

---

## 🔧 可能的解决方案（未来尝试）

### 方案 A：使用 Ollama 原生 API + 响应格式转换

**实现方式：**
```python
# 修改 Smart Proxy 降级逻辑
LOCAL_API_URL = "http://127.0.0.1:11434/api/chat"  # 改用原生端点

# 收到 Ollama 响应后转换为 OpenAI 格式
ollama_response = response.json()
openai_fake_response = {
    "id": "chatcmpl-local-fallback",
    "object": "chat.completion",
    "model": LOCAL_MODEL,
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": ollama_response.get("message", {}).get("content", "")
        },
        "finish_reason": "stop"
    }]
}
return JSONResponse(content=openai_fake_response, status_code=200)
```

**优点：** 彻底解决问题，不依赖 Ollama 兼容接口
**缺点：** 需要额外代码修改和测试
**工作量：** 约 15-30 分钟

---

### 方案 B：等待 Ollama 更新

**做法：**
- 关注 Ollama 版本更新
- 等待 `/v1/chat/completions` 端点稳定性改进
- 无需修改代码

**优点：** 无需额外工作
**缺点：** 时间不确定

---

### 方案 C：混合方案（双降级）

**实现方式：**
```python
# 优先使用 OpenAI 兼容接口
try:
    response = await client.post(OPENAI_COMPAT_URL, ...)
except:
    # 失败时降级到原生 API + 格式转换
    response = await client.post(NATIVE_API_URL, ...)
    return translate_to_openai_format(response)
```

**优点：** 更可靠
**缺点：** 代码更复杂

---

## 📂 相关文件

| 文件 | 路径 | 说明 |
|------|------|------|
| **代码** | `smart_proxy.py` | Smart Proxy 主程序 |
| **日志** | `smart_proxy.log` | 运行日志 |
| **虚拟环境** | `venv/` | Python 虚拟环境 |
| **长期目标** | `SMART_PROXY_LONG_TERM.md` | 本文档 |

---

## 📚 学习收获

1. ✅ Smart Proxy 架构设计（Sidecar Proxy 模式）
2. ✅ 断路器模式（Circuit Breaker）实现
3. ✅ FastAPI 异步 HTTP 代理开发
4. ✅ 黑盒测试方法
5. ✅ Ollama API 端点特性（原生 vs OpenAI 兼容）
6. ✅ HTTP Header 重要性（Content-Type）

---

## 🔄 重启条件

满足以下任一条件时重新启动此目标：

1. **Ollama 发布新版本** - 修复 `/v1/chat/completions` 稳定性问题
2. **有时间尝试方案 A** - 原生 API + 格式转换
3. **断网场景频繁** - 本地降级成为刚需
4. **用户明确要求** - 需要更高的可用性

---

## 💡 当前状态

### 系统配置
- **OpenClaw 模型：** 云端 Qwen3.5-plus ✅
- **Smart Proxy：** 已停止（端口 8000 空闲）✅
- **配置影响：** 无未完成配置，不影响正常使用 ✅

### 断网保护（独立工作）
- ✅ `network_monitor.py` 持续监控网络
- ✅ 断网 60 秒自动切换本地模型
- ✅ 网络恢复自动切回云端

**备注：**
- 这是一个"锦上添花"的功能，不是刚需
- 现有云端模型方案工作正常
- 可以安心等待更好的时机再优化

---

**最后更新：** 2026-03-11 23:06  
**下次审查：** 2026-04-11（或 Ollama 新版本发布时）
