/**
 * VectorBrain Workflow Store
 * 负责 workflow / task / log 的持久化和状态管理
 * 数据存储在 ~/.vectorbrain/vb-workflows/
 */
import fs from 'fs';
import path from 'path';
import { ensureDir, readJson, writeJson, listFiles, getVbDir } from './utils.js';
const VB_DIR = path.join(getVbDir(), 'vb-workflows');
const WORKFLOWS_DIR = path.join(VB_DIR, 'workflows');
const TASKS_DIR = path.join(VB_DIR, 'tasks');
const LOGS_DIR = path.join(VB_DIR, 'logs');
function id(prefix) {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}
// ─── Init ────────────────────────────────────────────────────────────────────
export async function initStore() {
    await ensureDir(WORKFLOWS_DIR);
    await ensureDir(TASKS_DIR);
    await ensureDir(LOGS_DIR);
}
// ─── Workflow ────────────────────────────────────────────────────────────────
export async function createWorkflow(goal, plan) {
    await initStore();
    const wf = {
        workflow_id: id('wf'),
        goal,
        plan,
        status: 'pending',
        tasks: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        total_tasks: 0,
        completed_tasks: 0,
    };
    await writeJson(path.join(WORKFLOWS_DIR, `${wf.workflow_id}.json`), wf);
    return wf;
}
export async function getWorkflow(wfId) {
    return readJson(path.join(WORKFLOWS_DIR, `${wfId}.json`));
}
export async function updateWorkflow(wfId, updates) {
    const wf = await getWorkflow(wfId);
    if (!wf)
        return null;
    const updated = { ...wf, ...updates, updated_at: new Date().toISOString() };
    await writeJson(path.join(WORKFLOWS_DIR, `${wfId}.json`), updated);
    return updated;
}
export async function listWorkflows(status) {
    const files = await listFiles(WORKFLOWS_DIR, '.json');
    const wfs = await Promise.all(files.map(f => readJson(f)));
    if (status)
        return wfs.filter((w) => !!w && w.status === status);
    return wfs.filter((w) => w !== null).sort((a, b) => b.created_at.localeCompare(a.created_at));
}
export async function deleteWorkflow(wfId) {
    const wf = await getWorkflow(wfId);
    if (!wf)
        return;
    for (const tid of wf.tasks) {
        await deleteTask(tid);
    }
    try {
        fs.unlinkSync(path.join(WORKFLOWS_DIR, `${wfId}.json`));
    }
    catch (err) {
        console.error(`[workflow-store] Failed to delete workflow file ${wfId}:`, err);
    }
}
// ─── Task ───────────────────────────────────────────────────────────────────
export async function createTask(params) {
    await initStore();
    const task = {
        task_id: id('task'),
        workflow_id: params.workflow_id,
        title: params.title,
        description: params.description,
        spec: params.spec,
        agent_type: params.agent_type,
        status: 'pending',
        attempts: 0,
        max_attempts: params.max_attempts ?? 3,
        depends_on: params.depends_on ?? [],
        review_notes: [],
        created_at: new Date().toISOString(),
        timeout_ms: params.timeout_ms,
    };
    await writeJson(path.join(TASKS_DIR, `${task.task_id}.json`), task);
    const wf = await getWorkflow(params.workflow_id);
    if (wf) {
        wf.tasks.push(task.task_id);
        wf.total_tasks = wf.tasks.length;
        await updateWorkflow(wf.workflow_id, { tasks: wf.tasks, total_tasks: wf.total_tasks });
    }
    return task;
}
export async function getTask(taskId) {
    return readJson(path.join(TASKS_DIR, `${taskId}.json`));
}
export async function updateTask(taskId, updates) {
    const task = await getTask(taskId);
    if (!task)
        return null;
    const updated = { ...task, ...updates };
    await writeJson(path.join(TASKS_DIR, `${taskId}.json`), updated);
    if (updates.status === 'done' || updates.status === 'passed') {
        const wf = await getWorkflow(task.workflow_id);
        if (wf) {
            const doneCount = await Promise.all(wf.tasks.map(tid => getTask(tid))).then(tasks => tasks.filter(t => t && (t.status === 'done' || t.status === 'passed')).length);
            await updateWorkflow(wf.workflow_id, { completed_tasks: doneCount });
        }
    }
    return updated;
}
export async function deleteTask(taskId) {
    try {
        fs.unlinkSync(path.join(TASKS_DIR, `${taskId}.json`));
    }
    catch (err) {
        console.error(`[workflow-store] Failed to delete task file ${taskId}:`, err);
    }
}
export async function getRunnableTasks(wfId) {
    const wf = await getWorkflow(wfId);
    if (!wf)
        return [];
    const tasks = await Promise.all(wf.tasks.map(tid => getTask(tid)));
    return tasks.filter(t => {
        if (!t || t.status !== 'pending')
            return false;
        if (t.depends_on.length === 0)
            return true;
        return t.depends_on.every(depId => {
            const dep = tasks.find(x => x?.task_id === depId);
            return dep && (dep.status === 'done' || dep.status === 'passed');
        });
    });
}
// ─── Cancellation / Pause / Resume ─────────────────────────────────────────────
export async function cancelWorkflow(wfId, reason = '用户取消') {
    const wf = await getWorkflow(wfId);
    if (!wf)
        return null;
    // Cancel all non-terminal tasks
    await Promise.all(wf.tasks.map(async (tid) => {
        const t = await getTask(tid);
        if (t && !['done', 'passed', 'failed', 'cancelled'].includes(t.status)) {
            await updateTask(tid, { status: 'cancelled', error: reason });
        }
    }));
    return updateWorkflow(wfId, {
        status: 'cancelled',
        error: reason,
        completed_at: new Date().toISOString(),
    });
}
export async function pauseWorkflow(wfId) {
    const wf = await getWorkflow(wfId);
    if (!wf || wf.status !== 'running')
        return null;
    // Pause all pending tasks
    await Promise.all(wf.tasks.map(async (tid) => {
        const t = await getTask(tid);
        if (t && t.status === 'pending') {
            await updateTask(tid, { status: 'paused' });
        }
    }));
    return updateWorkflow(wfId, { status: 'paused' });
}
export async function resumeWorkflow(wfId) {
    const wf = await getWorkflow(wfId);
    if (!wf || wf.status !== 'paused')
        return null;
    // Resume all paused tasks back to pending
    await Promise.all(wf.tasks.map(async (tid) => {
        const t = await getTask(tid);
        if (t && t.status === 'paused') {
            await updateTask(tid, { status: 'pending' });
        }
    }));
    return updateWorkflow(wfId, { status: 'running' });
}
export async function cancelTask(taskId, reason = '用户取消') {
    return updateTask(taskId, { status: 'cancelled', error: reason });
}
export async function pauseTask(taskId) {
    return updateTask(taskId, { status: 'paused' });
}
export async function resumeTask(taskId) {
    const t = await getTask(taskId);
    if (!t || t.status !== 'paused')
        return null;
    return updateTask(taskId, { status: 'pending' });
}
// ─── Cost Tracking ────────────────────────────────────────────────────────────
export async function accumulateCost(wfId, costUsd) {
    const wf = await getWorkflow(wfId);
    if (!wf)
        return 0;
    const current = wf.accumulated_cost_usd ?? 0;
    const newTotal = current + costUsd;
    await updateWorkflow(wfId, { accumulated_cost_usd: newTotal });
    return newTotal;
}
export async function getAccumulatedCost(wfId) {
    const wf = await getWorkflow(wfId);
    return wf?.accumulated_cost_usd ?? 0;
}
// ─── Logging ─────────────────────────────────────────────────────────────────
export async function appendLog(entry) {
    await initStore();
    const logEntry = {
        ...entry,
        log_id: id('log'),
        timestamp: new Date().toISOString(),
    };
    const logFile = path.join(LOGS_DIR, `workflow_${new Date().toISOString().slice(0, 10)}.jsonl`);
    const line = JSON.stringify(logEntry) + '\n';
    fs.appendFileSync(logFile, line, 'utf-8');
    return logEntry;
}
export async function getLogs(wfId, taskId) {
    if (!fs.existsSync(LOGS_DIR))
        return [];
    const files = fs.readdirSync(LOGS_DIR)
        .filter(f => f.startsWith('workflow_') && f.endsWith('.jsonl'))
        .map(f => path.join(LOGS_DIR, f))
        .sort(); // oldest first
    const entries = [];
    for (const file of files) {
        const lines = fs.readFileSync(file, 'utf-8').split('\n').filter(Boolean);
        for (const line of lines) {
            try {
                const e = JSON.parse(line);
                if (e.workflow_id !== wfId)
                    continue;
                if (taskId && e.task_id !== taskId)
                    continue;
                entries.push(e);
            }
            catch {
                // skip malformed lines silently
            }
        }
    }
    return entries.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}
export async function getWorkflowSummary(wfId) {
    const [workflow, logs] = await Promise.all([
        getWorkflow(wfId),
        getLogs(wfId),
    ]);
    if (!workflow)
        return { workflow: null, tasks: [], logs: [] };
    const tasks = await Promise.all(workflow.tasks.map(tid => getTask(tid)));
    return { workflow, tasks: tasks.filter(t => t !== null), logs };
}
//# sourceMappingURL=workflow-store.js.map