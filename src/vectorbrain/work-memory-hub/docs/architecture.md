# Architecture

## 设计原则
1. 不复制已有记忆数据库
2. 不替换 `connector` 现有脚本
3. 通过独立目录承接未来 A / C 共用能力

## 依赖关系
- 上游共享：`~/.vectorbrain/memory/`
- 连接参考：`~/.vectorbrain/connector/`
- 监控参考：`~/.vectorbrain/monitor_center/`

## 下一步建议
- 增加记忆检索适配器
- 增加任务事件写入接口
- 接入 monitor_center 状态汇总
