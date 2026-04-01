/**
 * VectorBrain Dispatcher
 * 通过 claude CLI 派发子 agent 执行任务
 */
import { spawn } from 'child_process';
import path from 'path';
import { readFileSync, existsSync } from 'fs';
import { appendLog } from './workflow-store.js';
// Skill content cache
const skillCache = new Map();
const SKILL_BASE_PATH = path.join(process.env.HOME || '', '.claude/skills');
/**
 * Load skill content from disk and cache it
 */
export function loadSkillContent(skillName) {
    if (skillCache.has(skillName)) {
        return skillCache.get(skillName);
    }
    const skillPath = path.join(SKILL_BASE_PATH, skillName, 'SKILL.md');
    try {
        if (existsSync(skillPath)) {
            const content = readFileSync(skillPath, 'utf-8');
            // Strip YAML frontmatter (between --- markers)
            const stripped = content.replace(/^---[\s\S]*?---\n/, '');
            skillCache.set(skillName, stripped);
            return stripped;
        }
    }
    catch (err) {
        console.error(`[dispatcher] Failed to load skill ${skillName}:`, err);
    }
    return null;
}
/**
 * Detect relevant skills based on task description
 */
export function detectRelevantSkills(taskTitle, taskDescription) {
    const text = `${taskTitle} ${taskDescription || ''}`.toLowerCase();
    const skills = [];
    const skillSignals = {
        'xlsx': ['.xlsx', '.xls', '.csv', 'excel', 'spreadsheet', '电子表格', 'excel文件'],
        'docx': ['.doc', '.docx', 'word', '文档', 'word文件'],
        'pdf': ['.pdf', 'pdf文件'],
        'pptx': ['.pptx', '.ppt', 'powerpoint', '演示文稿'],
    };
    for (const [skill, signals] of Object.entries(skillSignals)) {
        if (signals.some(s => text.includes(s))) {
            skills.push(skill);
        }
    }
    return skills;
}
const DEFAULT_TIMEOUT_MS = 5 * 60 * 1000;
export async function dispatchTask(opts) {
    const { task, workflowId, systemPrompt, taskPrompt, model, maxDurationMs, signal } = opts;
    // Per-task timeout takes precedence, then explicit maxDurationMs, then default
    const effectiveTimeout = task.timeout_ms ?? maxDurationMs ?? DEFAULT_TIMEOUT_MS;
    const startTime = Date.now();
    await appendLog({
        workflow_id: workflowId,
        task_id: task.task_id,
        level: 'INFO',
        phase: 'dispatch',
        message: `开始派发任务: ${task.title} (${task.task_id})`,
        details: {
            agent_type: task.agent_type,
            model: model ?? 'default',
            timeout_ms: effectiveTimeout,
        },
    });
    const logEntry = await appendLog({
        workflow_id: workflowId,
        task_id: task.task_id,
        level: 'INFO',
        phase: 'dispatch',
        message: `[DISPATCHER] 正在启动 claude CLI...`,
        details: { taskPrompt: taskPrompt.slice(0, 200) },
    });
    try {
        const args = [
            '-p',
            '--dangerously-skip-permissions',
            '--output-format', 'json',
            '--model', model ?? 'sonnet',
        ];
        const fullPrompt = `【角色设定】
${systemPrompt}

【具体任务】
${taskPrompt}

【输出要求】
请以 JSON 格式返回结果，包含：
{
  "success": true/false,
  "result": "具体完成内容",
  "summary": "一句话总结",
  "files_changed": ["文件列表"],
  "issues": ["发现的问题，如果有的话"]
}`;
        const result = await runClaudeCLI(args, fullPrompt, effectiveTimeout, signal);
        const duration_ms = Date.now() - startTime;
        if (result.success) {
            await appendLog({
                workflow_id: workflowId,
                task_id: task.task_id,
                level: 'SUCCESS',
                phase: 'dispatch',
                message: `任务完成 (${duration_ms}ms): ${task.title}`,
                details: { output: result.output, duration_ms },
            });
            const cost = parseCost(result.output);
            return { ...result, duration_ms, log_id: logEntry.log_id, cost };
        }
        else {
            await appendLog({
                workflow_id: workflowId,
                task_id: task.task_id,
                level: 'ERROR',
                phase: 'dispatch',
                message: `任务失败: ${task.title} - ${result.error}`,
                details: { error: result.error, duration_ms },
            });
            return { ...result, duration_ms, log_id: logEntry.log_id };
        }
    }
    catch (err) {
        const duration_ms = Date.now() - startTime;
        const errorMsg = err instanceof Error ? err.message : String(err);
        await appendLog({
            workflow_id: workflowId,
            task_id: task.task_id,
            level: 'ERROR',
            phase: 'dispatch',
            message: `派发异常: ${errorMsg}`,
            details: { duration_ms },
        });
        return { success: false, error: errorMsg, duration_ms, log_id: logEntry.log_id };
    }
}
function runClaudeCLI(args, prompt, timeoutMs, signal) {
    return new Promise((resolve) => {
        const proc = spawn('claude', args, {
            cwd: process.env.HOME && process.env.HOME.length > 0 ? process.env.HOME : '/tmp',
            env: { ...process.env, NO_COLOR: '1' },
        });
        const stdoutChunks = [];
        const stderrChunks = [];
        let finished = false;
        let timeoutId = null;
        let abortHandler = null;
        function cleanup() {
            if (timeoutId)
                clearTimeout(timeoutId);
            if (signal && abortHandler)
                signal.removeEventListener('abort', abortHandler);
        }
        // Handle timeout
        timeoutId = setTimeout(() => {
            if (finished)
                return;
            finished = true;
            cleanup();
            proc.kill('SIGTERM');
            resolve({ success: false, error: `TIMEOUT: Task exceeded ${timeoutMs}ms` });
        }, timeoutMs);
        // Handle abort signal
        if (signal) {
            abortHandler = () => {
                if (finished)
                    return;
                finished = true;
                cleanup();
                proc.kill('SIGTERM');
                resolve({ success: false, error: 'ABORTED: Task was cancelled by user or budget exceeded' });
            };
            signal.addEventListener('abort', abortHandler, { once: true });
        }
        proc.stdout?.on('data', (data) => { stdoutChunks.push(data.toString()); });
        proc.stderr?.on('data', (data) => { stderrChunks.push(data.toString()); });
        proc.on('close', (code) => {
            if (finished)
                return;
            finished = true;
            cleanup();
            const stdout = stdoutChunks.join('');
            const stderr = stderrChunks.join('');
            if (code === 0) {
                try {
                    const trimmed = stdout.trim();
                    const parsed = JSON.parse(trimmed);
                    resolve({ success: true, output: parsed });
                }
                catch {
                    resolve({ success: true, output: stdout.trim() });
                }
            }
            else {
                resolve({ success: false, error: stderr || `exit code ${code}: ${stdout.slice(0, 500)}` });
            }
        });
        proc.on('error', (err) => {
            if (finished)
                return;
            finished = true;
            cleanup();
            resolve({ success: false, error: err.message });
        });
        const stdinOk = proc.stdin?.write(prompt, (err) => {
            if (err && !finished) {
                finished = true;
                cleanup();
                resolve({ success: false, error: `stdin error: ${err.message}` });
            }
        });
        if (stdinOk !== false) {
            proc.stdin?.end();
        }
    });
}
export function getSkillRegistry() {
    return `【可用技能注册表】
当任务涉及以下场景时，通过 /<skill-name> 激活对应技能：

技能调用格式：在消息中发送 /<skill-name> 即可激活技能

| 技能名 | 使用场景 |
|--------|----------|
| docx | 创建或编辑 Word 文档（.docx） |
| xlsx | 创建或编辑 Excel 电子表格（.xlsx） |
| pptx | 创建或编辑 PowerPoint 演示文稿 |
| pdf | 读取、分析或操作 PDF 文件 |
| mcp-builder | 构建 MCP 服务器和工具 |
| skill-creator | 创建新的 Claude Code 技能 |
| webapp-testing | Web 应用测试相关 |
| frontend-design | 前端 UI/UX 设计和实现 |
| canvas-design | Canvas 画布图形设计 |
| algorithmic-art | 算法生成艺术图形 |
| brand-guidelines | 品牌风格和指南 |
| doc-coauthoring | 文档协作编写 |
| internal-comms | 内部沟通文案 |
| slack-gif-creator | Slack 表情包/GIF 创建 |
| spec | 规范文档编写 |
| template | 模板创建 |
| theme-factory | 主题工厂 |
| web-artifacts-builder | Web 工件构建 |

重要：当你处理文件任务时，先判断文件类型，选择对应的技能。`;
}
export function buildSkillContent(skillNames) {
    if (!skillNames.length)
        return '';
    const sections = ['【技能文档】\n'];
    for (const name of skillNames) {
        const content = loadSkillContent(name);
        if (content) {
            sections.push(`\n=== ${name} 技能 ===\n${content}\n`);
        }
    }
    return sections.join('\n');
}
export function getImplementerPrompt(context) {
    const skillContent = context?.skillNames?.length ? buildSkillContent(context.skillNames) : '';
    return `${getSkillRegistry()}
${skillContent}

你是一个专业的软件工程师（implementer）。

【你的职责】
1. 严格按照给定的 spec 实现任务
2. 编写测试验证你的实现
3. 保持代码简洁，遵循 YAGNI 和 DRY 原则
4. 不要改变 spec 之外的文件
5. 完成后用一句话总结你做了什么
6. 处理文件任务时，优先使用对应技能（见上方技能文档）

【约束】
${context?.constraints?.map(c => `- ${c}`).join('\n') ?? '- 不改变不相关的文件\n- 写测试，不写无测试的代码\n- 遵循项目现有的代码风格'}

${context?.taskSpec ? `【参考 spec】\n${context.taskSpec}\n` : ''}
${context?.workflowGoal ? `【整体目标】\n${context.workflowGoal}\n` : ''}`;
}
export function getSpecReviewerPrompt() {
    return `${getSkillRegistry()}

你是一个严格的 spec 审查员（spec reviewer）。

【你的职责】
1. 检查实现是否完全符合 spec
2. 逐条对照 spec，列出每一项的符合情况
3. 发现任何不符之处必须报告
4. 只有全部符合才可通过

【判断标准】
- 实现完全覆盖了 spec 的所有要求 → pass
- 有任何遗漏或偏差 → fail（需详细说明）

【输出格式】
{
  "passed": true/false,
  "checks": [
    { "spec_item": "原文", "status": "pass|fail", "note": "说明" }
  ],
  "overall": "总体评价"
}`;
}
export function getCodeQualityReviewerPrompt() {
    return `${getSkillRegistry()}

你是一个代码质量审查员（code quality reviewer）。

【你的职责】
1. 检查代码质量：可读性、错误处理、边界情况
2. 检查是否有调试代码（console.log 等）
3. 检查测试覆盖率
4. 发现问题按严重程度分级：critical / warning / info

【严重程度定义】
- critical: 必须修复，否则后果严重
- warning: 应该修复，影响可维护性
- info: 建议优化

【输出格式】
{
  "passed": true/false,
  "issues": [
    { "severity": "critical|warning|info", "file": "文件", "line": "行号（如果有）", "description": "问题描述" }
  ],
  "summary": "总体评价"
}`;
}
function parseCost(output) {
    if (!output || typeof output !== 'object')
        return undefined;
    const obj = output;
    if ('result' in obj && typeof obj.result === 'string') {
        try {
            const stripped = obj.result
                .replace(/^```json\n?/, '')
                .replace(/\n?```$/, '');
            const inner = JSON.parse(stripped);
            if (typeof inner === 'object' && inner !== null) {
                return extractFromObj(inner);
            }
        }
        catch { /* fall through */ }
    }
    return extractFromObj(obj);
}
function extractFromObj(obj) {
    const mu = obj.modelUsage;
    if (mu && typeof mu === 'object') {
        const m = mu;
        for (const key of Object.keys(m)) {
            const v = m[key];
            if (v && typeof v === 'object') {
                const vv = v;
                return {
                    inputTokens: vv.inputTokens ?? 0,
                    outputTokens: vv.outputTokens ?? 0,
                    cacheReadTokens: vv.cacheReadInputTokens ?? 0,
                    cacheWriteTokens: vv.cacheCreationInputTokens ?? 0,
                    costUsd: vv.costUSD ?? 0,
                };
            }
        }
    }
    return undefined;
}
//# sourceMappingURL=dispatcher.js.map