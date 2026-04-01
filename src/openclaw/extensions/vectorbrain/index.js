import http from 'http';
import { appendFileSync, mkdirSync } from 'fs';
function ensureLogDir() {
    mkdirSync('/tmp/openclaw', { recursive: true });
}
function appendHookLog(line) {
    try {
        ensureLogDir();
        appendFileSync('/tmp/openclaw/vectorbrain-hook.log', `${line}\n`);
    }
    catch {
        // non-critical path - don't let log write failures affect message processing
    }
}
function postJson(path, payload, timeoutMs = 1200) {
    const data = JSON.stringify(payload);
    return new Promise((resolve, reject) => {
        const req = http.request({
            hostname: '127.0.0.1',
            port: 8999,
            path,
            method: 'POST',
            timeout: timeoutMs,
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(data),
            },
        }, (res) => {
            let body = '';
            res.on('data', (chunk) => {
                body += chunk.toString();
            });
            res.on('end', () => {
                resolve({ statusCode: res.statusCode || 0, body });
            });
        });
        req.on('timeout', () => req.destroy(new Error(`timeout:${path}`)));
        req.on('error', reject);
        req.write(data);
        req.end();
    });
}
function normalizeMessage(msgCtx) {
    const rawMessage = msgCtx?.message || {};
    const text = rawMessage?.content || rawMessage?.text || '';
    const senderId = rawMessage?.senderId || rawMessage?.sender?.id || 'user';
    const senderName = rawMessage?.senderName || rawMessage?.sender?.name || '';
    const channelId = msgCtx?.channelId || rawMessage?.channelId || 'default';
    const sessionId = msgCtx?.sessionId || channelId;
    const messageId = rawMessage?.messageId || rawMessage?.id || '';
    const channel = msgCtx?.channel || msgCtx?.pluginName || 'unknown';
    const isBot = senderId.includes('bot') || senderId === 'nexus';
    return {
        text,
        senderId,
        senderName,
        channelId,
        sessionId,
        messageId,
        channel,
        role: isBot ? 'nexus' : 'user',
        rawMessage,
    };
}
async function sendUnifiedPreprocess(message) {
    return postJson('/v1/openclaw/preprocess', {
        session_id: message.sessionId,
        channel: message.channel,
        channel_id: message.channelId,
        message_id: message.messageId,
        sender_id: message.senderId,
        sender_name: message.senderName,
        text: message.text,
        raw: message.rawMessage,
        context: {
            is_dm: !String(message.channelId).includes('group'),
            is_group: String(message.channelId).includes('group'),
            mentioned: false,
        },
        metadata: {
            source: 'openclaw_vectorbrain_plugin',
            plugin_version: 'phase3-bridge-cleanup',
        },
    }, 1400);
}
// Tool modules to register as MCP tools
const toolModules = [
    './tools/orchestrate-goal.js',
    './tools/orchestrate-status.js',
    './tools/list-workflows.js',
    './tools/templates.js',
];
let toolsReady = false;
export default function register(api) {
    // Register orchestration tools before hook fires
    (async () => {
        for (const mod of toolModules) {
            try {
                const tool = await import(mod);
                if (tool.default) {
                    api.registerTool(tool.default);
                    api.logger.info(`[VectorBrain] Registered tool: ${tool.default.name}`);
                }
            }
            catch (e) {
                api.logger.error(`[VectorBrain] Failed to register tool ${mod}: ${e}`);
            }
        }
        toolsReady = true;
    })();
    // Existing message hook
    api.on('message_received', async (msgCtx) => {
        if (!toolsReady)
            return; // wait for tools to register
        const message = normalizeMessage(msgCtx);
        if (!message.text)
            return;
        const timestamp = new Date().toISOString();
        try {
            const primary = await sendUnifiedPreprocess(message);
            appendHookLog(`[${timestamp}] preprocess ${message.channelId} | ${message.senderId} | status=${primary.statusCode}`);
            if (primary.statusCode >= 200 && primary.statusCode < 300) {
                return;
            }
            throw new Error(`unexpected_status:${primary.statusCode}`);
        }
        catch (e) {
            appendHookLog(`[${timestamp}] preprocess_failed ${message.channelId} | ${message.senderId} | ${e?.message || e}`);
            console.error(`[VectorBrain] unified preprocess failed: ${e?.message || e}`);
        }
    });
}
//# sourceMappingURL=index.js.map