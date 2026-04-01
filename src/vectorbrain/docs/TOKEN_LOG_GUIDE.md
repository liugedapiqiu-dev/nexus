# 📊 VectorBrain Token 使用日志

**最后更新:** 2026-03-13 12:43  
**作者:** [YOUR_AI_NAME] 🧠

---

## 📁 文件位置

| 类型 | 路径 | 说明 |
|------|------|------|
| **日志文件** | `~/.vectorbrain/logs/token_usage.log` | JSONL 格式，持久化存储 |
| **SQLite 数据库** | `~/.vectorbrain/state/global_token_stats.db` | 快速查询 |
| **Dashboard** | http://localhost:8501 | 实时可视化 |

---

## 🔍 数据准确性

### ✅ 数据来源

Token 数据来自**LLM API 的真实响应**，包含：

- **input_tokens**: 发送给模型的实际 token 数
- **output_tokens**: 模型返回的实际 token 数
- **total_tokens**: 总消耗

### 📊 示例 API 响应

**DashScope (Qwen):**
```json
{
  "choices": [...],
  "usage": {
    "input_tokens": 1500,
    "output_tokens": 890,
    "total_tokens": 2390
  }
}
```

**Ollama:**
```json
{
  "model": "qwen2.5:14b",
  "message": {...},
  "total_duration": 8900000000,
  "load_duration": 120000000,
  "prompt_eval_count": 800,
  "eval_count": 620
}
```

---

## 🔄 数据持久性

### ✅ 网关重启后数据会丢失吗？

**不会！** 数据持久化存储：

1. **JSONL 日志文件** - 永久保存，除非手动删除
2. **SQLite 数据库** - 每日汇总，快速查询
3. **Dashboard** - 从持久化存储读取

### 📁 日志文件格式

每行一条 JSON 记录：
```json
{
  "timestamp": "2026-03-13T04:43:06.670425+00:00",
  "model": "qwen3.5-plus",
  "provider": "dashscope",
  "input_tokens": 1500,
  "output_tokens": 890,
  "total_tokens": 2390,
  "session_key": "agent:main:webchat",
  "duration_ms": 3420,
  "request_id": "req-abc123"
}
```

---

## 🛠️ 使用方法

### 命令行工具

```bash
# 查看今日统计
python3 ~/.vectorbrain/connector/token_logger.py today

# 查看最近 7 天统计
python3 ~/.vectorbrain/connector/token_logger.py stats 7

# 查看最近使用记录
python3 ~/.vectorbrain/connector/token_logger.py recent

# 导出 CSV
python3 ~/.vectorbrain/connector/token_logger.py export 30

# 查看最后 10 条日志
python3 ~/.vectorbrain/connector/token_logger.py tail 10

# 手动记录一条（测试用）
python3 ~/.vectorbrain/connector/token_logger.py log qwen3.5-plus dashscope 1500 890 session-key
```

### API 端点

```bash
# 获取全局统计
curl 'http://localhost:8501/api/global-token-stats?days=7'

# 获取今日摘要
curl 'http://localhost:8501/api/global-token-stats?days=1'
```

### Dashboard

访问 **http://localhost:8501** 查看：
- 📊 今日 Token 使用
- 📈 近 7 天趋势
- 🤖 按模型分类
- 📝 最近使用记录

---

## 🔌 自动拦截配置

### 方式 1：OpenClaw 工具调用

在每次 LLM 调用后，调用拦截工具：

```typescript
import { intercept_tokens } from '@vectorbrain/tools'

await intercept_tokens({
  model: 'qwen3.5-plus',
  provider: 'dashscope',
  input_tokens: 1500,
  output_tokens: 890,
  session_key: 'agent:main:webchat',
  duration_ms: 3420,
  request_id: 'req-abc123'
})
```

### 方式 2：修改 Smart Proxy

在 `~/.vectorbrain/connector/smart_proxy.py` 中添加日志记录：

```python
from token_logger import log_token

# 在 API 响应处理后
response_data = await response.json()
usage = response_data.get('usage', {})

log_token(
    model=response_data.get('model', 'unknown'),
    provider='dashscope',
    input_tokens=usage.get('input_tokens', 0),
    output_tokens=usage.get('output_tokens', 0),
    session_key=session_key,
    duration_ms=duration_ms,
    request_id=response_data.get('request_id')
)
```

### 方式 3：OpenClaw 网关层

在 OpenClaw 的 model provider 中添加拦截器，自动记录所有调用。

---

## 📊 当前统计

**截至今日:**

| 指标 | 数值 |
|------|------|
| 总输入 | 4,500 tokens |
| 总输出 | 3,160 tokens |
| 总计 | 7,660 tokens |
| 请求数 | 3 次 |
| 会话数 | 3 个 |

**按模型:**
- qwen3.5-plus (dashscope): 6,240 tokens
- qwen2.5:14b (ollama): 1,420 tokens

---

## 🔒 数据安全

- ✅ 本地存储，不上传云端
- ✅ 仅记录 token 数，不记录内容
- ✅ 支持按会话隔离统计
- ✅ 可手动删除日志文件

---

## 📝 待办事项

- [ ] 在 Smart Proxy 中集成自动拦截
- [ ] 在 OpenClaw 网关层添加全局拦截器
- [ ] 添加 Token 成本估算（基于各模型定价）
- [ ] 添加 Token 使用告警（超过阈值时通知）

---

**问题反馈:** 在 VectorBrain 指挥中心查看实时数据或联系[YOUR_AI_NAME] 🧠
