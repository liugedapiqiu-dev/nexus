/**
 * VectorBrain Background Runner
 * Spawns a detached child process to run orchestration without blocking.
 * Supports notification via Feishu when workflow completes.
 */
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { getVbDir, listFiles } from './mcp/utils.js';
/**
 * 在后台启动编排任务，立即返回 workflow_id。
 * 完成后自动发送飞书通知 + 生成报告文件。
 */
export function runInBackground(opts) {
    const { goal, tasks, model, maxAttempts = 3, notify = 'feishu', reportPath, } = opts;
    const vbDir = getVbDir();
    const scriptPath = path.join(vbDir, 'vb-sessions', `run_${Date.now()}.json`);
    // 写入会话参数文件，子进程读取
    const sessionData = {
        goal,
        tasks,
        model,
        maxAttempts,
        notify,
        reportPath: reportPath ?? path.join(process.env.HOME ?? '/tmp', 'Desktop'),
        startedAt: new Date().toISOString(),
    };
    fs.mkdirSync(path.dirname(scriptPath), { recursive: true });
    fs.writeFileSync(scriptPath, JSON.stringify(sessionData, null, 2), 'utf-8');
    // 生成临时 workflow_id 供追踪
    const workflowId = `bg_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    // 启动子进程
    const nodeBin = process.execPath;
    const extensionDir = path.dirname(new URL(import.meta.url).pathname);
    const child = spawn(nodeBin, [
        path.join(extensionDir, 'background-worker.js'),
        scriptPath,
        workflowId,
    ], {
        detached: true,
        stdio: 'ignore',
        cwd: process.env.HOME ?? '/tmp',
        env: { ...process.env },
    });
    child.unref();
    return { workflow_id: workflowId, pid: child.pid ?? 0 };
}
/**
 * 清理过期会话文件（callbacks 不会清理）
 */
export async function cleanupOldSessions(maxAgeMs = 24 * 60 * 60 * 1000) {
    try {
        const sessionsDir = path.join(getVbDir(), 'vb-sessions');
        const files = await listFiles(sessionsDir, '.json');
        const now = Date.now();
        for (const f of files) {
            const stat = fs.statSync(f);
            if (now - stat.mtimeMs > maxAgeMs) {
                fs.unlinkSync(f);
            }
        }
    }
    catch { }
}
//# sourceMappingURL=background-runner.js.map