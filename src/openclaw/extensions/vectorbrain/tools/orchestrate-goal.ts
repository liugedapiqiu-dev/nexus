/**
 * VectorBrain Orchestrate Tool
 * Accepts a goal + optional task definitions.
 * Supports background execution, auto-decomposition, and task templates.
 */

import { orchestrate, OrchestrateOptions, OrchestrationResult } from '../mcp/orchestrate.js';
import { dispatchTask } from '../mcp/dispatcher.js';
import { runInBackground } from '../background-runner.js';
import {
  listTemplates, getTemplate, saveTemplate, BUILTIN_TEMPLATES,
} from '../mcp/templates-store.js';

export default {
  name: 'vectorbrain.orchestrate',
  description: 'Orchestrate a complex goal by decomposing it into tasks and dispatching sub-agents. Use when user wants to accomplish a complex multi-step task (e.g., "帮我分析销售数据", "帮我写一个网站", "帮我重构这个模块"). Supports background execution, task templates, and auto-decomposition. Returns workflow_id and summary.',

  parameters: {
    type: 'object',
    properties: {
      goal: {
        type: 'string',
        description: 'The high-level goal to accomplish',
      },
      tasks: {
        type: 'array',
        description: 'Task definitions. If empty and auto_decompose=true, auto-decomposes via LLM.',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            description: { type: 'string' },
            spec: { type: 'string' },
            agent_type: { type: 'string', enum: ['implementer', 'spec_reviewer', 'code_reviewer'] },
            depends_on: { type: 'array', items: { type: 'string' } },
            timeout_ms: { type: 'number', description: 'Per-task timeout in milliseconds (default: 5 minutes for implementer, 2 minutes for reviews)' },
          },
          required: ['title', 'description', 'agent_type'],
        },
      },
      model: {
        type: 'string',
        description: 'Model to use for sub-agents (default: sonnet)',
      },
      max_attempts: {
        type: 'number',
        description: 'Max retry attempts per task (default: 3)',
        default: 3,
      },
      max_cost_usd: {
        type: 'number',
        description: 'Maximum cost budget in USD. Workflow stops if exceeded (default: no limit)',
      },
      cost_alert_threshold: {
        type: 'number',
        description: 'Cost threshold to trigger alert callback (default: no alert)',
      },
      auto_decompose: {
        type: 'boolean',
        description: 'Auto-decompose goal into tasks via LLM if tasks is empty (default: true)',
        default: true,
      },
      background: {
        type: 'boolean',
        description: 'Run in background immediately and return workflow_id (default: false). Completion notification sent via Feishu.',
        default: false,
      },
      notify: {
        type: 'string',
        description: 'Notification method when background job completes: feishu | none (default: feishu)',
        default: 'feishu',
      },
      template_id: {
        type: 'string',
        description: 'Use a saved or builtin template (e.g., "builtin:code-review"). Overrides tasks parameter.',
      },
    },
    required: ['goal'],
  },

  async execute(
    _toolCallId: string,
    opts: {
      goal: string;
      tasks?: Array<{
        title: string;
        description: string;
        spec?: string;
        agent_type: 'implementer' | 'spec_reviewer' | 'code_reviewer';
        depends_on?: string[];
        timeout_ms?: number;
      }>;
      model?: string;
      max_attempts?: number;
      max_cost_usd?: number;
      cost_alert_threshold?: number;
      auto_decompose?: boolean;
      background?: boolean;
      notify?: string;
      template_id?: string;
    },
    _signal?: AbortSignal
  ): Promise<OrchestrationResult | { workflow_id: string; background: true; message: string }> {
    const startTime = Date.now();

    // ── 模板加载 ────────────────────────────────────────────────────
    if (opts.template_id) {
      const template = await getTemplate(opts.template_id);
      if (template) {
        opts.tasks = template.tasks;
      } else {
        const builtin = BUILTIN_TEMPLATES.find(t => t.template_id === opts.template_id);
        if (builtin) {
          opts.tasks = builtin.tasks;
        } else {
          return makeErrorResult(opts.goal, `Template not found: ${opts.template_id}`, 0, startTime);
        }
      }
    }

    // ── 自动分解 ───────────────────────────────────────────────────
    const shouldAutoDecompose = (opts.auto_decompose !== false) && (!opts.tasks || opts.tasks.length === 0);
    if (shouldAutoDecompose) {
      const planResult = await decomposeGoal(opts.goal, opts.model);
      if (!planResult.success || !planResult.tasks || planResult.tasks.length === 0) {
        return makeErrorResult(opts.goal, '无法分解目标', opts.tasks?.length ?? 0, startTime);
      }
      opts.tasks = planResult.tasks;
    }

    if (!opts.tasks || opts.tasks.length === 0) {
      return makeErrorResult(opts.goal, '没有可执行的任务', 0, startTime);
    }

    // ── 后台执行 ───────────────────────────────────────────────────
    if (opts.background) {
      const { workflow_id } = runInBackground({
        goal: opts.goal,
        tasks: opts.tasks,
        model: opts.model,
        maxAttempts: opts.max_attempts ?? 3,
        notify: (opts.notify as any) ?? 'feishu',
      });
      return {
        workflow_id,
        background: true,
        message: `工作流已在后台启动: ${workflow_id}，完成后将发送飞书通知`,
      };
    }

    // ── 同步执行 ───────────────────────────────────────────────────
    const orchestrationOptions: OrchestrateOptions = {
      goal: opts.goal,
      tasks: opts.tasks.map(t => ({
        title: t.title,
        description: t.description,
        spec: t.spec,
        agent_type: t.agent_type as any,
        depends_on: t.depends_on,
        timeout_ms: t.timeout_ms,
      })),
      model: opts.model,
      maxAttempts: opts.max_attempts ?? 3,
      maxCostUsd: opts.max_cost_usd,
      costAlertThreshold: opts.cost_alert_threshold,
    };

    try {
      const result = await orchestrate(orchestrationOptions);
      return result;
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      return makeErrorResult(opts.goal, errorMsg, opts.tasks?.length ?? 0, startTime);
    }
  },
};

// ─── Goal 自动分解 ────────────────────────────────────────────────────────────

interface DecomposedTask {
  title: string;
  description: string;
  spec?: string;
  agent_type: 'implementer';
  depends_on: string[];
}

interface DecomposeResult {
  success: boolean;
  tasks?: DecomposedTask[];
  error?: string;
}

async function decomposeGoal(goal: string, model?: string): Promise<DecomposeResult> {
  const planningPrompt = `你是一个任务规划专家。请将以下目标分解成具体的执行任务：

目标：${goal}

要求：
1. 每个任务要有清晰的 title（简短标题）和 description（详细描述）
2. 任务之间有依赖关系的话，用 depends_on 字段标注
3. 第一个任务通常是收集信息或准备环境，最后一个任务通常是总结或输出
4. 每个任务只做一件事，不要拆分太细（3-8个任务比较合适）
5. agent_type 统一使用 "implementer"

请以 JSON 格式返回任务列表：
{
  "tasks": [
    { "title": "任务1标题", "description": "详细描述...", "agent_type": "implementer", "depends_on": [] },
    { "title": "任务2标题", "description": "详细描述...", "agent_type": "implementer", "depends_on": ["task_1"] }
  ]
}`;

  try {
    const result = await dispatchTask({
      task: {
        task_id: `plan_${Date.now()}`,
        workflow_id: 'planning',
        title: '[Planning] 分解目标',
        description: `分解目标: ${goal}`,
        agent_type: 'implementer',
        status: 'pending',
        attempts: 0,
        max_attempts: 1,
        depends_on: [],
        review_notes: [],
        created_at: new Date().toISOString(),
      },
      workflowId: 'planning',
      systemPrompt: '你是一个任务规划专家。请只返回 JSON，不要有其他内容。',
      taskPrompt: planningPrompt,
      model: model,
      maxDurationMs: 60000,
    });

    if (!result.success) {
      return { success: false, error: result.error ?? 'Planning failed' };
    }

    let outputText = '';
    if (typeof result.output === 'string') {
      outputText = result.output;
    } else if (result.output && typeof result.output === 'object') {
      const obj = result.output as Record<string, unknown>;
      if ('result' in obj && typeof obj.result === 'string') {
        outputText = obj.result as string;
      } else {
        outputText = JSON.stringify(result.output);
      }
    }

    const jsonMatch = outputText.match(/```json\n?([\s\S]*?)\n?```/) || outputText.match(/\{[\s\S]*"tasks"[\s\S]*\}/);
    if (!jsonMatch) {
      return { success: false, error: '无法从 Planning 结果中提取任务列表' };
    }

    const parsed = JSON.parse(jsonMatch[1] as string);
    if (!parsed.tasks || !Array.isArray(parsed.tasks)) {
      return { success: false, error: 'Planning 返回格式错误，缺少 tasks 数组' };
    }

    let taskCount = 0;
    const idMap = new Map<string, string>();
    const tasks: DecomposedTask[] = parsed.tasks.map((t: any) => {
      const id = `task_${++taskCount}`;
      // 同时存储 title->id 和 task_N->id（支持序号引用如 "task_1"）
      idMap.set(t.title, id);
      idMap.set(`task_${taskCount}`, id);
      return {
        title: t.title,
        description: t.description ?? t.title,
        spec: t.spec,
        agent_type: 'implementer',
        depends_on: (t.depends_on ?? []).map((dep: string) => {
          return idMap.get(dep) ?? dep;
        }),
      };
    });

    return { success: true, tasks };
  } catch (err: unknown) {
    return { success: false, error: err instanceof Error ? err.message : String(err) };
  }
}

function makeErrorResult(goal: string, error: string, totalTasks: number, startTime: number): OrchestrationResult {
  return {
    workflow_id: 'error',
    success: false,
    total_tasks: totalTasks,
    completed_tasks: 0,
    failed_tasks: [],
    duration_ms: Date.now() - startTime,
    error,
    logs: [],
    summary: {
      goal,
      status: 'failed',
      completed: 0,
      total: totalTasks,
      failed_task_titles: [],
      key_outputs: [],
      duration_ms: Date.now() - startTime,
    },
  };
}
