# VectorBrain 自主稳定运行 Runbook

## 目标
让系统在无人盯盘时，尽量做到：
- 队列不会长期卡死
- 关键脚本掉了能被看见
- 日志长期没动能被发现
- 通知失败不会静默堆积
- 异常有固定处理口径，而不是每次临场发挥

## 已建立的长期机制

### 1. 稳定性巡检 (`maintenance/stability_check.py`)
检查 4 类信号：
- 任务队列状态分布
- `running` 任务是否陈旧
- 关键日志新鲜度
- 关键进程是否还活着
- pending notification 是否出现失败堆积

输出：
- `~/.vectorbrain/state/stability_report.json`
- `~/.vectorbrain/reports/stability_report_latest.md`

### 2. 坏队列守卫 (`maintenance/task_queue_guard.py`)
能力：
- 干跑识别陈旧 `running` 任务
- 干跑识别超过重试上限的任务
- `--apply` 时自动隔离为 `failed`
- 将修复动作追加到 `~/.vectorbrain/logs/stability_guard.log`

设计原则：
- 默认 dry-run，避免误伤
- 只处理“明显坏掉”的任务：长时间 running / 重试耗尽
- 不重启 gateway，不直接粗暴杀全局服务

### 3. 运行约束配置 (`maintenance/stability_config.json`)
把阈值显式化：
- stale running 超时阈值
- log freshness 阈值
- 关键进程白名单
- 巡检输出位置

这样后续调优不用改脚本逻辑，只改配置。

## 建议维护节奏

### 每 30~60 分钟
运行：
```bash
python3 ~/.vectorbrain/maintenance/stability_check.py
```
用途：发现脚本掉线、日志停更、通知积压。

### 每 6~12 小时
先 dry-run：
```bash
python3 ~/.vectorbrain/maintenance/task_queue_guard.py
```
如果确认存在陈旧 running 任务，再 apply：
```bash
python3 ~/.vectorbrain/maintenance/task_queue_guard.py --apply
```
用途：防止坏任务长期占坑。

### 每周一次
人工 review：
- 看 `stability_report_latest.md`
- 看 `stability_guard.log`
- 看 `pending_notifications.json`
- 评估关键进程名单是否需要调整
- 评估 stale timeout 是否过严/过松

## 异常处理口径

### A. 发现 stale running task
1. 先跑 guard dry-run
2. 确认是否真是僵尸任务（尤其看 `updated_at`、worker id）
3. 确认后 `--apply` 隔离
4. 后续再补查根因（脚本崩溃、状态未回写、worker 退出）

### B. 发现日志不新鲜
1. 先确认对应进程是否还活着
2. 若进程活着但日志不动，优先怀疑卡死/阻塞
3. 若进程不在，记录到维护清单，由主进程或人工决定是否恢复

### C. 通知队列失败堆积
1. 检查 `pending_notifications.json`
2. 关注 `failed` 和 `retry_count` 高的通知
3. 排查 Feishu 发送或 runtime 环境问题

## 现在这个框架能减少哪些“长歪”
- **卡死不自知**：通过 stale-running 扫描把“看似在跑、其实早死了”的任务挑出来
- **服务掉线不自知**：通过 expected process + log freshness 做双判据
- **坏消息静默堆积**：对 pending/failed notifications 单独成块观察
- **维护口径漂移**：runbook 固化后，后续谁来维护都按同一套动作走

## 后续增强建议（下一阶段）
- 把巡检结果推送到 Feishu/面板，而不是只落文件
- 给 `tasks` 表补 `heartbeat_at` 字段，替代单靠 `updated_at`
- 给不同 worker 设不同 timeout
- 对 `failed` 任务建立 quarantine 子状态（比如 `failed_stale`, `failed_retry_exhausted`）
- 做“连续 N 次异常才报警”的降噪层
