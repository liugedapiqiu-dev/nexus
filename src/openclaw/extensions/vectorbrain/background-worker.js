/**
 * VectorBrain Background Worker
 * Run as detached child process: node background-worker.js <sessionFile> <workflowId>
 * Reads session params, runs orchestration, sends notification, generates report.
 */
import fs from 'fs';
import path from 'path';
// Read session file path from argv
const [, , sessionFile, workflowId] = process.argv;
if (!sessionFile || !workflowId) {
    console.error('Usage: node background-worker.js <sessionFile> <workflowId>');
    process.exit(1);
}
const home = process.env.HOME ?? '';
const extensionDir = path.dirname(new URL(import.meta.url).pathname);
// Read session data
let session;
try {
    session = JSON.parse(fs.readFileSync(sessionFile, 'utf-8'));
}
catch (e) {
    console.error('Failed to read session file:', e);
    process.exit(1);
}
// Dynamic import of orchestrate
const orchestratePath = path.join(extensionDir, 'orchestrate.js');
async function main() {
    try {
        const { orchestrate } = await import(orchestratePath);
        console.log(`[BackgroundWorker] Starting workflow ${workflowId}: ${session.goal}`);
        const result = await orchestrate({
            goal: session.goal,
            tasks: session.tasks.map(t => ({
                title: t.title,
                description: t.description,
                spec: t.spec,
                agent_type: t.agent_type,
                depends_on: t.depends_on,
            })),
            model: session.model,
            maxAttempts: session.maxAttempts ?? 3,
        });
        console.log(`[BackgroundWorker] Workflow ${workflowId} completed: ${result.success}`);
        // Generate report
        await generateReport(result, session.reportPath ?? path.join(home, 'Desktop'));
        // Send notification
        if (session.notify !== 'none') {
            await sendFeishuNotification(result, session.goal);
        }
    }
    catch (err) {
        console.error(`[BackgroundWorker] Workflow ${workflowId} error:`, err);
    }
    finally {
        // Clean up session file
        try {
            if (sessionFile)
                fs.unlinkSync(sessionFile);
        }
        catch { }
        process.exit(0);
    }
}
async function generateReport(result, reportDir) {
    const lines = [
        `# 工作流执行报告`,
        ``,
        `**目标**: ${result.summary?.goal ?? 'unknown'}`,
        `**状态**: ${result.success ? '✅ 成功' : '❌ 失败'}`,
        `**完成**: ${result.completed_tasks}/${result.total_tasks} 个任务`,
        `**耗时**: ${((result.duration_ms ?? 0) / 1000).toFixed(1)}s`,
        ``,
    ];
    if (result.summary?.key_outputs?.length) {
        lines.push(`## 关键输出`);
        for (const output of result.summary.key_outputs) {
            lines.push(`- ${output}`);
        }
        lines.push('');
    }
    if (result.failed_tasks?.length) {
        lines.push(`## 失败任务`);
        for (const title of (result.summary?.failed_task_titles ?? [])) {
            lines.push(`- ❌ ${title}`);
        }
        lines.push('');
    }
    lines.push(`## 执行日志摘要`);
    lines.push(`<details>`);
    lines.push(`<summary>点击展开完整日志</summary>`);
    lines.push(``);
    lines.push(`\`\`\``);
    for (const log of (result.logs ?? []).slice(-20)) {
        lines.push(`[${log.timestamp}] [${log.level}] ${log.message}`);
    }
    lines.push(`\`\`\``);
    lines.push(`</details>`);
    lines.push('');
    lines.push(`---`);
    lines.push(`*由 VectorBrain Orchestration Engine 自动生成 | ${new Date().toISOString()}*`);
    const reportContent = lines.join('\n');
    const fileName = `report_${workflowId}_${Date.now()}.md`;
    const filePath = path.join(reportDir, fileName);
    fs.mkdirSync(reportDir, { recursive: true });
    fs.writeFileSync(filePath, reportContent, 'utf-8');
    console.log(`[BackgroundWorker] Report written to: ${filePath}`);
    return filePath;
}
async function sendFeishuNotification(result, goal) {
    try {
        const text = result.success
            ? `✅ 工作流完成\n\n目标: ${goal}\n完成: ${result.completed_tasks}/${result.total_tasks} 任务\n耗时: ${((result.duration_ms ?? 0) / 1000).toFixed(1)}秒`
            : `⚠️ 工作流部分失败\n\n目标: ${goal}\n完成: ${result.completed_tasks}/${result.total_tasks} 任务\n失败: ${result.failed_tasks?.length ?? 0} 个`;
        // Send via openclaw's internal HTTP hook (same as index.ts)
        const http = await import('http');
        const payload = JSON.stringify({ text, goal, workflow_id: result.workflow_id, success: result.success });
        // Try to notify via the preprocess endpoint that might forward to Feishu
        const req = http.request({
            hostname: '127.0.0.1',
            port: 18789,
            path: '/v1/openclaw/notify',
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
            timeout: 5000,
        }, (res) => {
            req.destroy();
        });
        req.on('error', () => req.destroy());
        req.write(payload);
        req.end();
    }
    catch (e) {
        console.warn('[BackgroundWorker] Feishu notification failed:', e);
    }
}
main();
//# sourceMappingURL=background-worker.js.map