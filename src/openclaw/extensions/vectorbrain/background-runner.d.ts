/**
 * VectorBrain Background Runner
 * Spawns a detached child process to run orchestration without blocking.
 * Supports notification via Feishu when workflow completes.
 */
export interface BackgroundRunOptions {
    goal: string;
    tasks: Array<{
        title: string;
        description: string;
        spec?: string;
        agent_type: string;
        depends_on?: string[];
    }>;
    model?: string;
    maxAttempts?: number;
    /** 完成通知方式: feishu | none (默认 feishu) */
    notify?: 'feishu' | 'none';
    /** 完成后写报告的路径，默认桌面 */
    reportPath?: string;
}
/**
 * 在后台启动编排任务，立即返回 workflow_id。
 * 完成后自动发送飞书通知 + 生成报告文件。
 */
export declare function runInBackground(opts: BackgroundRunOptions): {
    workflow_id: string;
    pid: number;
};
/**
 * 清理过期会话文件（callbacks 不会清理）
 */
export declare function cleanupOldSessions(maxAgeMs?: number): Promise<void>;
//# sourceMappingURL=background-runner.d.ts.map