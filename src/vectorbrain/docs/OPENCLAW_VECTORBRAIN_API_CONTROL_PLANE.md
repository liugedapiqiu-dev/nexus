# OpenClaw ↔ VectorBrain Stable API Control Plane

更新日期：2026-03-20

## 目标

为 OpenClaw ↔ VectorBrain 提供一个 **稳定、轻依赖、可常驻托管** 的统一控制面，不替换现有主链事实源，也不重新发明第二状态库。

- 统一命名：`/v1/openclaw/*`
- 标准探针：`/health`、`/ready`、`/metrics`
- 兼容探针：`/api/health`、`/api/ready`、`/api/metrics`
- 运行模式：`read_only_proxy_control_plane`

## 文件

- 服务实现：`~/.vectorbrain/service_bridges/openclaw_control_plane.py`
- launchd 管理脚本：`~/.vectorbrain/bin/openclaw_api_service.sh`
- launchd label：`ai.vectorbrain.openclaw-api`
- 默认地址：`127.0.0.1:18991`

## 端点

### GET `/health` / `/v1/openclaw/health`
返回：
- control plane 自身存活状态
- OpenClaw gateway / legacy api / DAG / planner / monitor_center 可达性
- 核心 DB / state 文件存在情况
- 若可读取，则附带 `episodes / conversations / tasks / lessons` 计数

### GET `/ready` / `/v1/openclaw/ready`
**只看关键条件**：
- `memory/episodic_memory.db` 存在
- `tasks/task_queue.db` 存在
- `agent_core_loop.py` 存活
- OpenClaw gateway 18789 可达

说明：
- 9000 / 9100 / 18083 作为 advisory，不阻塞 ready
- 这样避免因为旁路 API 波动把整体 readiness 拉挂

### GET `/metrics` / `/v1/openclaw/metrics`
Prometheus 文本格式，包含：
- `openclaw_vectorbrain_up`
- `openclaw_vectorbrain_ready`
- `openclaw_vectorbrain_uptime_seconds`
- `openclaw_vectorbrain_requests_total`
- `openclaw_vectorbrain_errors_total`
- `openclaw_vectorbrain_preprocess_total`
- `openclaw_vectorbrain_postprocess_total`
- `openclaw_vectorbrain_backend_up{backend=...}`
- `openclaw_vectorbrain_db_rows{table=...}`

### POST `/v1/openclaw/preprocess`
输入标准化骨架：
- 接收 `text` / `input` / `messages`
- 返回 `canonical.normalized_text`
- 提供轻量 hints（memory/task candidate）

### POST `/v1/openclaw/postprocess`
输出标准化骨架：
- 接收 `result` / `output` / `text`
- 返回统一 `response` 包装

## 启动

### 手工前台
```bash
python3 ~/.vectorbrain/service_bridges/openclaw_control_plane.py --host 127.0.0.1 --port 18991
```

### launchd 常驻
```bash
~/.vectorbrain/bin/openclaw_api_service.sh install
~/.vectorbrain/bin/openclaw_api_service.sh status
```

### 重启
```bash
~/.vectorbrain/bin/openclaw_api_service.sh restart
```

### 卸载
```bash
~/.vectorbrain/bin/openclaw_api_service.sh uninstall
```

## 健康检查示例

```bash
python3 - <<'PY'
from urllib.request import urlopen
for path in ['/health', '/ready', '/metrics', '/v1/openclaw/health']:
    url = 'http://127.0.0.1:18991' + path
    with urlopen(url, timeout=2) as r:
        print(path, r.status)
        print(r.read(200).decode('utf-8', 'replace'))
        print('---')
PY
```

## 为什么不继续沿用旧 `connector/api_server.py`

旧服务存在这些问题：
- 依赖 `fastapi + uvicorn`，当前环境并未稳定安装
- `/api/health`、`/api/stats` 这类探针会直接 404
- 只覆盖旧 memory save/load + DAG 辅助，不是统一 control plane
- `nohup + uvicorn` 稳定性与可观测性都不够好

## 设计边界

- **不替换** `task_manager.py` / `session_archiver.py` / `chat_scraper_v2.py` 等主链执行器
- **不写入** 第二状态库
- **只读汇总 / 轻代理 / 统一探针 / 包装预处理后处理**
- 适合作为 OpenClaw 侧统一 API 门面，而不是新的业务真相源
