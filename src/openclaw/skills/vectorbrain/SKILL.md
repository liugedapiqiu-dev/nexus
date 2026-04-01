---
name: vectorbrain
description: VectorBrain 任务编排引擎。当用户需要完成复杂多步骤任务、需要后台执行并返回报告、处理涉及多个子任务的工作流、或需要将大任务自动分解为小任务并行执行时使用。例如："帮我分析销售数据"、"帮我写一个网站"、"帮我重构这个模块"、"帮我生成一份报告"。支持 cancel/pause/resume、per-task timeout、cost budget 控制。
---

# VectorBrain Orchestration Engine

## Overview

VectorBrain is an advanced task orchestration engine that decomposes complex goals into executable tasks, dispatches sub-agents to execute them in parallel or sequence, and provides full lifecycle management (cancel/pause/resume).

## When to Use This Skill

Use VectorBrain when:
- **Complex multi-step tasks**: Goal requires multiple steps that need orchestration
- **Background execution**: User wants task to run and get notification when complete
- **Auto-decomposition**: Large task needs to be automatically broken into smaller tasks
- **Parallel execution**: Independent tasks can run simultaneously for speed
- **Task dependencies**: Some tasks depend on others' outputs
- **Background with notification**: User wants to continue other work while task runs

## How VectorBrain Works

1. **Goal Analysis**: Accepts a high-level goal and optionally auto-decomposes it into tasks
2. **Task Planning**: Creates a DAG of tasks with dependencies
3. **Parallel Dispatch**: Spawns Claude CLI sub-processes to execute tasks
4. **Review Pipeline**: Each task result goes through spec review + code quality review
5. **Completion**: Returns summary report, key outputs, and logs

## Features

- **Auto-decomposition**: LLM-powered task breakdown
- **Parallel execution**: Tasks without dependencies run concurrently
- **Per-task timeout**: Individual timeout per task (default 5 min for implementer, 2 min for reviews)
- **Cancel/Pause/Resume**: Full workflow lifecycle control
- **Cost tracking**: Accumulates and reports cost per workflow
- **Background execution**: Runs detached, sends Feishu notification on completion
- **Retry logic**: Failed tasks retry up to max_attempts times
- **DAG execution**: Respects task dependencies

## Tool Interface

VectorBrain registers these MCP tools:
- `vectorbrain.orchestrate(goal, tasks?, auto_decompose?, background?, ...)`: Start orchestration
- `vectorbrain.workflow_status(workflow_id, action?)`: Query or control workflow
- `vectorbrain.list_workflows(status?)`: List all workflows
- `vectorbrain.templates(action?, ...)`: Manage task templates

## Usage Examples

```
# Simple orchestration
vectorbrain.orchestrate(goal="帮我写一个用户登录模块")

# With explicit tasks
vectorbrain.orchestrate(goal="分析销售数据", tasks=[
  {title: "读取数据", description: "...", agent_type: "implementer"},
  {title: "数据清洗", description: "...", agent_type: "implementer", depends_on: ["task_1"]},
])

# Background execution with notification
vectorbrain.orchestrate(goal="帮我写完这个项目", background=true)
```

## Task Templates

VectorBrain supports reusable templates:
- `builtin:code-review` - Standard code review workflow
- `builtin:data-analysis` - Data analysis pipeline
- Custom templates saved via `vectorbrain.templates`

## Constraints

- Maximum cost budget per workflow (optional)
- Cost alert threshold for warnings
- Per-task timeout overrides global timeout
- Maximum retry attempts per task (default: 3)
