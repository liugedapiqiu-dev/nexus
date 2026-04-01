# Work Memory Hub

最小可运行骨架，用于承接 A / C 共用的工作记忆中枢。

## 目标
- 统一接入 `~/.vectorbrain/memory/` 现有记忆层
- 复用 `~/.vectorbrain/connector/` 的连接/启动思路
- 复用 `~/.vectorbrain/monitor_center/` 的状态采集思路
- 为后续 A / C 子系统提供稳定入口

## 当前结构
- `configs/`：配置样例
- `bin/`：入口脚本
- `docs/`：设计说明与后续规划
- `src/`：Python 占位实现
- `runtime/`：运行期产物
- `logs/`：运行日志

## 快速开始
```bash
~/.vectorbrain/work-memory-hub/bin/work-memory-hub --help
~/.vectorbrain/work-memory-hub/bin/work-memory-hub status
```

## 共享依赖
- Memory root: `~/.vectorbrain/memory`
- Connector root: `~/.vectorbrain/connector`
- Monitor root: `~/.vectorbrain/monitor_center`

当前仅提供安全骨架，不会修改现有数据库或服务。
