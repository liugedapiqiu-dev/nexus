---
name: data-automation-service
description: 智能数据处理与自动化编排服务。当用户需要处理文件（Excel、CSV、PDF、Word）、分析数据、生成报告、或者需要后台执行复杂多步骤任务时使用。通过 VectorBrain 编排引擎实现子任务分解、并行执行、双阶段审查（spec合规审查+代码质量审查）。触发词：「帮我处理数据」「帮我分析Excel」「生成报告」「后台执行」「自动化」
---

# Data Automation Service

## 核心能力

智能数据处理与自动化编排服务。当用户需要完成涉及文件处理、数据分析、报告生成的复杂任务时，调用 VectorBrain 编排引擎来执行。

## 工作流程

### 1. 接收任务
识别用户的数据处理需求：
- Excel/CSV 数据处理和分析
- PDF/Word 文档处理
- 数据清洗和转换
- 报告生成
- 任何需要多步骤处理的自动化任务

### 2. 任务编排（调用 VectorBrain）

**使用 vectorbrain.orchestrate MCP 工具：**

```json
{
  "goal": "用户的数据处理目标",
  "tasks": [
    {
      "title": "读取数据文件",
      "description": "使用 xlsx 技能读取 Excel 文件...",
      "agent_type": "implementer"
    },
    {
      "title": "数据清洗",
      "description": "清理缺失值、格式转换...",
      "agent_type": "implementer",
      "depends_on": ["task_1"]
    }
  ],
  "auto_decompose": true,
  "background": true,
  "notify": "feishu"
}
```

### 3. 执行引擎（VectorBrain MCP）

VectorBrain 编排引擎负责：
1. **任务分解**：自动或手动将大任务拆解成可执行的子任务
2. **DAG 执行**：按依赖关系调度任务，支持并行执行
3. **双阶段审查**：
   - Spec 审查：检查实现是否符合需求
   - 代码质量审查：检查代码质量、错误处理
4. **生命周期管理**：支持 cancel/pause/resume
5. **成本控制**：支持最大成本预算和告警阈值

### 4. 完成通知

任务完成后：
- 通过飞书发送执行结果
- 在桌面生成执行报告

## 触发场景

| 用户说... | VectorBrain 行动 |
|---------|-----------------|
| "帮我分析这个 Excel" | 读取 → 清洗 → 分析 → 生成报告 |
| "处理这个 CSV 文件" | 读取 → 转换 → 清洗 → 保存 |
| "生成一份销售报告" | 读取数据 → 数据透视 → 生成 Excel |
| "后台处理这些数据" | 启动后台工作流 → 完成通知 |
| "帮我做数据清洗" | 识别字段 → 清洗规则 → 执行 |

## 任务模板

预定义的任务模板（通过 `template_id` 指定）：

| template_id | 用途 |
|-------------|------|
| `builtin:data-analysis` | 标准数据分析流程 |
| `builtin:excel-processing` | Excel 处理流程 |
| `builtin:report-generation` | 报告生成流程 |

## 使用示例

### 示例 1：数据分析
```
用户: 帮我分析这个销售数据 Excel
AI: 调用 vectorbrain.orchestrate
  - goal: "分析销售数据，生成汇总报告"
  - auto_decompose: true
  - background: true
  - VectorBrain 自动分解任务并执行
  - 完成时通过飞书发送报告
```

### 示例 2：带明确步骤
```
用户: 读取 Excel → 清洗数据 → 生成报告
AI: 调用 vectorbrain.orchestrate
  - goal: "销售数据分析报告"
  - tasks: [读取任务, 清洗任务, 报告任务]
  - 按依赖顺序执行
```

## 技术细节

### 可用技能（子任务执行时使用）
- `xlsx` - Excel 文件读写和处理
- `docx` - Word 文档处理
- `pdf` - PDF 读取和分析
- `spec` - 规范文档编写
- `mcp-builder` - MCP 工具构建

### 执行配置
- `max_attempts`: 单任务最大重试次数（默认3）
- `max_cost_usd`: 最大成本预算（可选）
- `cost_alert_threshold`: 成本告警阈值（可选）
- `timeout_ms`: 单任务超时（默认5分钟）

### 状态查询
使用 `vectorbrain.workflow_status` 查询任务进度：
```
vectorbrain.workflow_status(workflow_id="xxx", action="status")
```

## 限制与注意事项

1. 文件路径需要是绝对路径
2. 敏感数据处理请注意数据安全
3. 大文件处理可能需要较长时间，建议后台执行
4. 成本会累加，注意设置预算上限

## 与 Superpowers 的区别

Superpowers 专注于软件开发工作流（代码实现、测试、审查），而 Data Automation Service 专注于数据处理和自动化任务。两者都使用 VectorBrain 作为执行引擎。
