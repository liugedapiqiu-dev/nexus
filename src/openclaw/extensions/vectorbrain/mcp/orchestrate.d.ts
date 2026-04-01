/**
 * VectorBrain Orchestration Engine
 *
 * 完整工作流:
 * 1. 接收 goal，拆解成 plan（Task 列表）
 * 2. 依次派发任务 → Review → 通过则完成
 * 3. 全链路日志，输出汇总报告
 */
import { AgentType, LogEntry } from './workflow-store.js';
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
export declare function orchestrate(opts: OrchestrateOptions): Promise<OrchestrationResult>;
//# sourceMappingURL=orchestrate.d.ts.map