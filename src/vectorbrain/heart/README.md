# Heart v1

现在的 Heart v1 已经从“最小可用”升级到“可预演首轮测试”：
- 情绪/需求识别
- **带长期轨迹的 HeartState 更新**
- **恢复机制 / 稳态更新 / 模式粘性衰减**
- 回复风格 / 策略调节
- **情感记忆写入、会话摘要、状态续接**
- 保护性模式切换
- **runtime / orchestrator 可选 pre-process hook**

## 模块
- `heart/perception.py`：识别情绪、需求、紧急度、风险信号
- `heart/state.py`：核心数据结构（含恢复/稳定/轨迹字段）
- `heart/regulation.py`：由输入信号更新 HeartState
- `heart/policy.py`：根据状态输出更成熟的回复策略
- `heart/memory.py`：情感记忆数据库接口（SQLite）+ 会话摘要
- `heart/engine.py`：闭环总入口，支持从历史状态续接
- `runtime/heart_bridge.py`：runtime 调用适配层 + preprocess packet
- `runtime/orchestrator.py`：可选 `heart_preprocess` / `preprocess_hooks=["heart"]`
- `heart/validate.py`：最小验收脚本

## 快速示例
```python
from runtime.heart_bridge import runtime_heart

result = runtime_heart.assess(
    "我有点焦虑，怕事情搞砸，帮我一步一步来",
    session_id="sess-001",
)

print(result["state"]["protective_mode"])
print(result["state"]["trajectory_label"])
print(result["policy"]["strategy"])
```

## Orchestrator 可选 Hook
```python
from runtime.orchestrator import orchestrate
import asyncio

payload = {
    "title": "帮我回复用户，说得稳一点",
    "description": "用户刚表达焦虑，希望一步一步来",
    "metadata": {
        "session_id": "sess-001",
        "heart_preprocess": True,
        "heart_write_memory": False,
    },
}

result = asyncio.run(orchestrate(payload, dry_run=True))
print(result["task"]["metadata"]["heart"]["reply_guidance"])
```

## 最小验证
```bash
python3 ~/.vectorbrain/heart/validate.py
```
