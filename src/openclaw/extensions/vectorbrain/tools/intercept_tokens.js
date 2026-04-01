import path from 'path';
import { spawn } from 'child_process';
import { getVbDir } from '../mcp/utils.js';
const LOG_SCRIPT = path.join(getVbDir(), 'connector', 'token_logger.py');
export default {
    name: 'vectorbrain.intercept_tokens',
    description: '拦截 LLM API 调用并记录真实 token 消耗（从 API 响应中提取）',
    parameters: {
        type: 'object',
        properties: {
            model: { type: 'string', description: '模型名称' },
            provider: { type: 'string', description: '提供商 (dashscope|ollama)', enum: ['dashscope', 'ollama'] },
            input_tokens: { type: 'number', description: '输入 token 数（从 API 响应获取）' },
            output_tokens: { type: 'number', description: '输出 token 数（从 API 响应获取）' },
            session_key: { type: 'string', description: '会话标识' },
            duration_ms: { type: 'number', description: '请求耗时（毫秒）' },
            request_id: { type: 'string', description: '请求 ID' },
            cost: { type: 'number', description: '成本（人民币元）' }
        },
        required: ['model', 'provider', 'input_tokens', 'output_tokens']
    },
    async run({ model, provider, input_tokens, output_tokens, session_key = '', duration_ms = 0, request_id = '', cost = 0 }) {
        return new Promise((resolve, reject) => {
            const python = spawn('python3', [
                LOG_SCRIPT,
                'log',
                model,
                provider,
                input_tokens.toString(),
                output_tokens.toString(),
                session_key
            ]);
            const outputChunks = [];
            const errorChunks = [];
            python.stdout?.on('data', (data) => { outputChunks.push(data.toString()); });
            python.stderr?.on('data', (data) => { errorChunks.push(data.toString()); });
            python.on('close', (code) => {
                const output = outputChunks.join('');
                const error = errorChunks.join('');
                if (code === 0) {
                    resolve({
                        success: true,
                        message: `✅ Token 已记录：${model} - 输入 ${input_tokens.toLocaleString()} / 输出 ${output_tokens.toLocaleString()}`,
                        input_tokens,
                        output_tokens,
                        total_tokens: input_tokens + output_tokens,
                        session_key,
                        log_file: path.join(getVbDir(), 'logs', 'token_usage.log')
                    });
                }
                else {
                    resolve({
                        success: false,
                        message: `⚠️ 记录失败：${error}`,
                        error
                    });
                }
            });
        });
    }
};
//# sourceMappingURL=intercept_tokens.js.map