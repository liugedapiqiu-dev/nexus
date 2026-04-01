/**
 * VectorBrain Orchestration Engine
 *
 * 完整工作流:
 * 1. 接收 goal，拆解成 plan（Task 列表）
 * 2. 依次派发任务 → Review → 通过则完成
 * 3. 全链路日志，输出汇总报告
 */

import {
  Workflow, Task, AgentType,
  createWorkflow, getWorkflow, updateWorkflow,
  createTask, getTask, updateTask, getRunnableTasks,
  listWorkflows, appendLog, getLogs, LogEntry,
  cancelWorkflow as cancelWorkflowStore,
  pauseWorkflow as pauseWorkflowStore,
  resumeWorkflow as resumeWorkflowStore,
  cancelTask as cancelTaskStore,
  accumulateCost, getAccumulatedCost,
} from './workflow-store.js';
import {
  dispatchTask, DispatchOptions,
  getImplementerPrompt, getSpecReviewerPrompt, getCodeQualityReviewerPrompt,
  detectRelevantSkills,
} from './dispatcher.js';
import { sleep, getVbDir } from './utils.js';

export interface OrchestrateOptions {
  goal: string;
  tasks: Array<{
    title: string;
    description: string;
    spec?: string;
    agent_type: AgentType;
    depends_on?: string[];
    timeout_ms?: number;
  }>;
  workflowId?: string;
  model?: string;
  maxAttempts?: number;
  maxCostUsd?: number;
  costAlertThreshold?: number;
  onCostAlert?: (accumulatedCost: number, threshold: number) => void;
  onProgress?: (event: ProgressEvent) => void;
  autoRemember?: boolean;
  deduplicate?: boolean;
}

export interface ProgressEvent {
  workflow_id: string;
  task_id: string;
  task_title: string;
  completed: number;
  total: number;
  status: 'done' | 'failed' | 'cancelled' | 'paused';
}

export interface OrchestrationResult {
  workflow_id: string;
  success: boolean;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: string[];
  duration_ms: number;
  result?: unknown;
  error?: string;
  logs: LogEntry[];
  summary: {
    goal: string;
    status: 'completed' | 'failed' | 'cancelled';
    completed: number;
    total: number;
    failed_task_titles: string[];
    key_outputs: string[];
    duration_ms: number;
  };
}

export async function orchestrate(opts: OrchestrateOptions): Promise<OrchestrationResult> {
  const startTime = Date.now();
  const {
    goal, tasks: taskDefs, workflowId: existingWfId,
    model, maxAttempts = 3,
    maxCostUsd, costAlertThreshold,
    onCostAlert,
    onProgress, autoRemember = true, deduplicate = true,
  } = opts;

  // ── AbortController for cancellation ────────────────────────────
  const workflowController = new AbortController();
  let cancelled = false;

  // ── 幂等性检查 ──────────────────────────────────────────────────
  if (!existingWfId && deduplicate) {
    const similar = await findSimilarWorkflow(goal);
    if (similar) {
      await appendLog({
        workflow_id: 'dedup',
        level: 'WARN',
        phase: 'orchestrate',
        message: `检测到相似工作流已存在: ${similar.workflow_id}，跳过创建`,
        details: { similar_workflow_id: similar.workflow_id, similar_goal: similar.goal },
      });
      return {
        workflow_id: similar.workflow_id,
        success: similar.status === 'completed',
        total_tasks: similar.total_tasks,
        completed_tasks: similar.completed_tasks,
        failed_tasks: [],
        duration_ms: 0,
        summary: {
          goal: similar.goal,
          status: similar.status as 'completed' | 'failed',
          completed: similar.completed_tasks,
          total: similar.total_tasks,
          failed_task_titles: [],
          key_outputs: [],
          duration_ms: 0,
        },
        error: undefined,
        logs: [],
      };
    }
  }

  await appendLog({
    workflow_id: existingWfId ?? 'new',
    level: 'INFO',
    phase: 'orchestrate',
    message: `🚀 开始编排工作流: ${goal}`,
    details: { task_count: taskDefs.length, workflow_id: existingWfId },
  });

  let wf: Workflow;
  if (existingWfId) {
    const existing = await getWorkflow(existingWfId);
    if (!existing) throw new Error(`Workflow not found: ${existingWfId}`);
    wf = existing;
  } else {
    wf = await createWorkflow(goal);
  }
  await updateWorkflow(wf.workflow_id, {
    status: 'running',
    max_cost_usd: maxCostUsd,
    cost_alert_threshold: costAlertThreshold,
    accumulated_cost_usd: 0,
  });

  await appendLog({
    workflow_id: wf.workflow_id,
    level: 'INFO',
    phase: 'orchestrate',
    message: `工作流已创建: ${wf.workflow_id}`,
  });

  // ── 创建所有 task ──────────────────────────────────────────────
  for (const td of taskDefs) {
    const task = await createTask({
      workflow_id: wf.workflow_id,
      title: td.title,
      description: td.description,
      spec: td.spec,
      agent_type: td.agent_type,
      depends_on: td.depends_on,
      max_attempts: maxAttempts,
      timeout_ms: td.timeout_ms,
    });
    await appendLog({
      workflow_id: wf.workflow_id,
      task_id: task.task_id,
      level: 'INFO',
      phase: 'plan',
      message: `Task 创建: ${task.title} (${task.task_id})`,
      details: { agent_type: task.agent_type, depends_on: td.depends_on ?? [], timeout_ms: td.timeout_ms },
    });
  }

  // ── 执行循环 ──────────────────────────────────────────────────
  const failedTasks: string[] = [];
  const failedTaskTitles: string[] = [];
  const keyOutputs: string[] = [];
  let completedCount = 0;

  while (true) {
    // ── 检查外部取消信号 ──────────────────────────────────────────
    if (workflowController.signal.aborted || cancelled) {
      break;
    }

    // ── 检查 workflow 状态（暂停/取消）─────────────────────────────
    const wfNow = await getWorkflow(wf.workflow_id);
    if (wfNow?.status === 'cancelled') {
      cancelled = true;
      break;
    }
    if (wfNow?.status === 'paused') {
      await sleep(2000);
      continue;
    }

    const runnable = await getRunnableTasks(wf.workflow_id);
    if (runnable.length === 0 && completedCount < taskDefs.length) {
      const allTasks = await Promise.all(wf.tasks.map(tid => getTask(tid)));
      const pending = allTasks.filter(t => t && t.status === 'pending');
      const blocked = pending.filter(t =>
        t!.depends_on.some(depId =>
          allTasks.some(x => x?.task_id === depId && (x?.status === 'failed' || x?.status === 'cancelled'))
        )
      );
      if (blocked.length > 0) {
        for (const t of blocked) {
          await updateTask(t!.task_id, { status: 'failed', error: '依赖任务失败或被取消' });
          failedTasks.push(t!.task_id);
          failedTaskTitles.push(t!.title);
        }
      }
      if (allTasks.every(t => t && (t.status === 'done' || t.status === 'failed' || t.status === 'passed' || t.status === 'cancelled'))) {
        break;
      }
      await sleep(1000);
      continue;
    }

    const byDepth = groupByDepth(runnable);
    for (const group of byDepth) {
      // ── 检查取消信号 ───────────────────────────────────────────
      if (workflowController.signal.aborted || cancelled) break;

      await sleep(50); // 确保同一批真正并行启动
      const results = await Promise.all(
        group.map(task => runTask(wf.workflow_id, task, { model, maxAttempts, signal: workflowController.signal }))
      );

      for (const [task, result] of zip(group, results)) {
        // ── 检查取消信号 ─────────────────────────────────────────
        if (workflowController.signal.aborted || cancelled) break;

        if (result.status === 'done' || result.status === 'passed') {
          completedCount++;
          if (result.output) keyOutputs.push(extractKeyOutput(result.output));
          onProgress?.({
            workflow_id: wf.workflow_id,
            task_id: task.task_id,
            task_title: task.title,
            completed: completedCount,
            total: taskDefs.length,
            status: 'done',
          });
        } else if (result.status === 'failed' || result.status === 'cancelled') {
          failedTasks.push(task.task_id);
          failedTaskTitles.push(task.title);
          onProgress?.({
            workflow_id: wf.workflow_id,
            task_id: task.task_id,
            task_title: task.title,
            completed: completedCount,
            total: taskDefs.length,
            status: result.status === 'cancelled' ? 'cancelled' : 'failed',
          });
        }
      }

      // ── 成本检查 ───────────────────────────────────────────────
      if (maxCostUsd !== undefined) {
        const currentCost = await getAccumulatedCost(wf.workflow_id);
        if (currentCost >= maxCostUsd) {
          await appendLog({
            workflow_id: wf.workflow_id,
            level: 'ERROR',
            phase: 'orchestrate',
            message: `成本超预算: $${currentCost.toFixed(4)} >= $${maxCostUsd}，取消工作流`,
          });
          workflowController.abort();
          cancelled = true;
          break;
        }
        if (costAlertThreshold !== undefined && currentCost >= costAlertThreshold) {
          onCostAlert?.(currentCost, costAlertThreshold);
        }
      }
    }

    const wfAfterGroup = await getWorkflow(wf.workflow_id);
    if (wfAfterGroup && (wfAfterGroup.completed_tasks >= taskDefs.length || failedTasks.length > 0)) {
      break;
    }
  }

  // ── 结束 workflow ─────────────────────────────────────────────
  const duration_ms = Date.now() - startTime;
  const wfFinal = await getWorkflow(wf.workflow_id);
  let finalStatus: Workflow['status'];
  let finalError: string | undefined;

  if (cancelled) {
    finalStatus = 'cancelled';
    finalError = '工作流已被取消';
  } else if (failedTasks.length === 0) {
    finalStatus = 'completed';
  } else {
    finalStatus = 'failed';
    finalError = `${failedTasks.length} 个任务失败`;
  }

  await updateWorkflow(wf.workflow_id, {
    status: finalStatus,
    completed_at: new Date().toISOString(),
    result: { completed_tasks: completedCount, failed_tasks: failedTasks, duration_ms },
    error: finalError,
  });

  const logs = await getLogs(wf.workflow_id);

  await appendLog({
    workflow_id: wf.workflow_id,
    level: finalStatus === 'completed' ? 'SUCCESS' : finalStatus === 'cancelled' ? 'WARN' : 'ERROR',
    phase: 'complete',
    message: `工作流结束: ${finalStatus}，耗时 ${duration_ms}ms，完成 ${completedCount}/${taskDefs.length} 个任务`,
    details: { failed_tasks: failedTasks, duration_ms },
  });

  if (autoRemember) {
    await autoWriteMemory(wf.workflow_id, goal, finalStatus, completedCount, taskDefs.length, duration_ms, keyOutputs);
  }

  return {
    workflow_id: wf.workflow_id,
    success: finalStatus === 'completed',
    total_tasks: taskDefs.length,
    completed_tasks: completedCount,
    failed_tasks: failedTasks,
    duration_ms,
    result: { completed_tasks: completedCount, failed_tasks: failedTasks },
    error: finalError,
    logs,
    summary: {
      goal,
      status: finalStatus as 'completed' | 'failed' | 'cancelled',
      completed: completedCount,
      total: taskDefs.length,
      failed_task_titles: failedTaskTitles,
      key_outputs: keyOutputs.slice(0, 5),
      duration_ms,
    },
  };
}

// ─── 内部：运行单个 Task ──────────────────────────────────────────────────

interface RunResult { status: 'done' | 'passed' | 'failed' | 'cancelled'; output?: unknown }

async function runTask(
  workflowId: string,
  task: Task,
  opts: { model?: string; maxAttempts?: number; signal?: AbortSignal }
): Promise<RunResult> {
  // Check abort before starting
  if (opts.signal?.aborted) {
    await updateTask(task.task_id, { status: 'cancelled', error: '工作流已被取消' });
    return { status: 'cancelled' };
  }

  const detectedSkills = detectRelevantSkills(task.title, task.description);

  const dispatchOpts: DispatchOptions = {
    task,
    workflowId,
    systemPrompt: getImplementerPrompt({
      workflowGoal: (await getWorkflow(workflowId))?.goal,
      taskSpec: task.spec,
      constraints: [
        '不要改变其他文件',
        '完成后总结做了什么',
        '遇到问题及时报告',
      ],
      skillNames: detectedSkills,
    }),
    taskPrompt: task.description,
    model: opts.model,
    signal: opts.signal,
  };

  await updateTask(task.task_id, { status: 'dispatched', attempts: task.attempts + 1 });
  const result = await dispatchTask(dispatchOpts);

  // Handle abort or cancellation
  if (opts.signal?.aborted) {
    await updateTask(task.task_id, { status: 'cancelled', error: '工作流已被取消' });
    return { status: 'cancelled' };
  }

  if (!result.success) {
    const isAbort = result.error?.includes('ABORTED') || result.error?.includes('cancelled by user');
    await updateTask(task.task_id, {
      status: isAbort ? 'cancelled' : 'failed',
      error: result.error,
      completed_at: new Date().toISOString(),
    });
    return { status: isAbort ? 'cancelled' : 'failed' };
  }

  // Accumulate cost
  if (result.cost) {
    await accumulateCost(workflowId, result.cost.costUsd);
  }

  // Spec Review
  if (opts.signal?.aborted) {
    await updateTask(task.task_id, { status: 'cancelled', error: '工作流已被取消' });
    return { status: 'cancelled' };
  }

  await updateTask(task.task_id, { status: 'review' });

  const specReview = await dispatchTask({
    task: {
      ...task,
      task_id: `specrev_${task.task_id}`,
      agent_type: 'spec_reviewer',
      title: `[Spec Review] ${task.title}`,
      description: `检查实现是否符合 spec:\n${task.spec ?? task.description}`,
      review_notes: [],
    },
    workflowId,
    systemPrompt: getSpecReviewerPrompt(),
    taskPrompt: `实现结果:\n${JSON.stringify(result.output, null, 2)}\n\n原始 spec:\n${task.spec ?? task.description}`,
    model: opts.model,
    maxDurationMs: 2 * 60 * 1000,
    signal: opts.signal,
  });

  if (opts.signal?.aborted) {
    await updateTask(task.task_id, { status: 'cancelled', error: '工作流已被取消' });
    return { status: 'cancelled' };
  }

  const specPassed = specReview.success && extractPass(specReview.output);

  await updateTask(task.task_id, {
    review_notes: [
      ...task.review_notes,
      {
        reviewer: 'spec_reviewer',
        passed: specPassed,
        notes: JSON.stringify(specReview.output),
        timestamp: new Date().toISOString(),
        attempt: task.attempts,
      },
    ],
  });

  if (!specPassed) {
    if (task.attempts < (opts.maxAttempts ?? 3)) {
      await updateTask(task.task_id, { status: 'pending' });
      return runTask(workflowId, { ...task, status: 'pending', attempts: task.attempts + 1 }, opts);
    } else {
      await updateTask(task.task_id, { status: 'failed', error: 'Spec Review 失败，已达最大重试次数' });
      return { status: 'failed' };
    }
  }

  // Code Quality Review - Skip for non-code tasks (data analysis, file processing, etc.)
  // If the result doesn't contain code patterns, auto-pass
  const resultStr = typeof result.output === 'string' ? result.output : JSON.stringify(result.output ?? '');
  const isCodeTask = /function\b|const |let |var |import |export |def |class |public |private |async |await\b/i.test(resultStr);
  let qualityPassed = true;
  let qualityOutput: unknown = null;

  if (isCodeTask) {
    const qualityReview = await dispatchTask({
      task: {
        ...task,
        task_id: `qualrev_${task.task_id}`,
        agent_type: 'code_reviewer',
        title: `[Quality Review] ${task.title}`,
        description: `检查代码质量:\n${task.description}`,
        review_notes: [],
      },
      workflowId,
      systemPrompt: getCodeQualityReviewerPrompt(),
      taskPrompt: `实现结果:\n${JSON.stringify(result.output, null, 2)}`,
      model: opts.model,
      maxDurationMs: 2 * 60 * 1000,
      signal: opts.signal,
    });

    if (opts.signal?.aborted) {
      await updateTask(task.task_id, { status: 'cancelled', error: '工作流已被取消' });
      return { status: 'cancelled' };
    }

    qualityPassed = qualityReview.success && extractPass(qualityReview.output);
    qualityOutput = qualityReview.output;

    await updateTask(task.task_id, {
      review_notes: [
        ...task.review_notes,
        {
          reviewer: 'code_reviewer',
          passed: qualityPassed,
          notes: JSON.stringify(qualityReview.output),
          timestamp: new Date().toISOString(),
          attempt: task.attempts,
        },
      ],
    });

    if (!qualityPassed) {
      if (task.attempts < (opts.maxAttempts ?? 3)) {
        await updateTask(task.task_id, { status: 'pending' });
        return runTask(workflowId, { ...task, status: 'pending', attempts: task.attempts + 1 }, opts);
      } else {
        await updateTask(task.task_id, { status: 'failed', error: 'Quality Review 失败，已达最大重试次数' });
        return { status: 'failed' };
      }
    }
  }

  await updateTask(task.task_id, {
    status: 'done',
    output: result.output,
    completed_at: new Date().toISOString(),
  });

  return { status: 'done', output: result.output };
}

// ─── 辅助函数 ────────────────────────────────────────────────────────────────

function groupByDepth(tasks: Task[]): Task[][] {
  const depthMap = new Map<string, number>();
  const result: Task[][] = [];
  const taskMap = new Map(tasks.map(t => [t.task_id, t]));
  const visiting = new Set<string>();

  function depth(t: Task): number {
    if (depthMap.has(t.task_id)) return depthMap.get(t.task_id)!;
    if (visiting.has(t.task_id)) {
      console.error(`[orchestrate] 循环依赖检测到: ${t.task_id}`);
      depthMap.set(t.task_id, 0);
      return 0;
    }
    if (t.depends_on.length === 0) { depthMap.set(t.task_id, 0); return 0; }
    visiting.add(t.task_id);
    let max = 0;
    for (const depId of t.depends_on) {
      const dep = taskMap.get(depId);
      if (dep) max = Math.max(max, depth(dep));
    }
    visiting.delete(t.task_id);
    const d = max + 1;
    depthMap.set(t.task_id, d);
    return d;
  }

  for (const t of tasks) depth(t);
  const maxDepth = Math.max(...Array.from(depthMap.values()), 0);
  for (let d = 0; d <= maxDepth; d++) {
    const group = tasks.filter(t => depthMap.get(t.task_id) === d);
    if (group.length > 0) result.push(group);
  }
  return result;
}

function extractPass(output: unknown): boolean {
  if (!output) return false;
  if (typeof output === 'boolean') return output;
  if (typeof output === 'object') {
    const obj = output as Record<string, unknown>;
    if ('result' in obj && typeof obj.result === 'string') {
      try {
        const stripped = (obj.result as string)
          .replace(/^```json\n?/, '')
          .replace(/\n?```$/, '');
        const inner = JSON.parse(stripped);
        if (typeof inner === 'object' && inner !== null) {
          if ('passed' in inner) return Boolean(inner.passed);
          if ('pass' in inner) return Boolean(inner.pass);
          if ('success' in inner) return Boolean(inner.success);
        }
        if (typeof inner === 'boolean') return inner;
      } catch { /* fall through */ }
    }
    if ('passed' in obj) return Boolean(obj.passed);
    if ('pass' in obj) return Boolean(obj.pass);
    if ('success' in obj) return Boolean(obj.success);
  }
  return false;
}

function extractKeyOutput(output: unknown): string {
  if (!output) return '';
  if (typeof output === 'string') return output.slice(0, 100);
  const obj = output as Record<string, unknown>;
  if (typeof obj === 'object' && obj !== null) {
    if ('result' in obj) {
      const r = obj.result;
      if (typeof r === 'string') return r.slice(0, 100);
      if (typeof r === 'object' && r !== null) {
        const ro = r as Record<string, unknown>;
        if ('summary' in ro) return String(ro.summary).slice(0, 100);
        if ('text' in ro) return String(ro.text).slice(0, 100);
      }
    }
    if ('summary' in obj) return String(obj.summary).slice(0, 100);
    if ('text' in obj) return String(obj.text).slice(0, 100);
  }
  return JSON.stringify(output).slice(0, 100);
}

function zip<T, U>(a: T[], b: (U | undefined)[]): Array<[T, U]> {
  return a.map((v, i) => [v, b[i] as U]);
}

async function findSimilarWorkflow(goal: string): Promise<Workflow | null> {
  const wfs = await listWorkflows();
  const kw = goal.replace(/\s+/g, '').slice(0, 10);
  for (const wf of wfs) {
    if (wf.status === 'running' || wf.status === 'completed') {
      const wfkw = wf.goal.replace(/\s+/g, '').slice(0, 10);
      if (wfkw === kw) return wf;
    }
  }
  return null;
}

async function autoWriteMemory(
  workflowId: string,
  goal: string,
  status: string,
  completed: number,
  total: number,
  duration_ms: number,
  keyOutputs: string[]
): Promise<void> {
  try {
    const fs = await import('fs');
    const path = await import('path');
    const memoryPath = path.join(getVbDir(), 'memory', 'log.txt');
    const date = new Date().toISOString().slice(0, 10);
    const lines = [
      `[${date}] [orchestration] workflow=${workflowId}`,
      `  goal: ${goal}`,
      `  status: ${status}`,
      `  completed: ${completed}/${total}`,
      `  duration: ${(duration_ms / 1000).toFixed(1)}s`,
    ];
    if (keyOutputs.length > 0) {
      lines.push(`  outputs: ${keyOutputs.join(' | ').slice(0, 200)}`);
    }
    lines.push('');
    fs.appendFileSync(memoryPath, lines.join('\n') + '\n', 'utf-8');
  }
  catch (e) {
    // ignore
  }
}

