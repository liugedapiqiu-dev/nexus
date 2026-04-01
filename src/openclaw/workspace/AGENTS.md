# AGENTS.md - Multi-Agent Coordination

## Agent 架构

- 主 Agent: [YOUR_AI_NAME]
- 子 Agent: 根据需要创建
- 记忆共享: 通过 VectorBrain

## 工作流协议

1. 任务分解
2. 子任务分配
3. 结果汇总
4. 质量检查

## 通信协议

- 主 Agent 负责任务分配
- 子 Agent 定期报告进度
- 异常情况立即上报

## 记忆同步

所有 Agent 共享 VectorBrain 向量记忆数据库，确保信息一致性。
