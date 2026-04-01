/**
 * VectorBrain Workflow Store
 * 负责 workflow / task / log 的持久化和状态管理
 * 数据存储在 ~/.vectorbrain/vb-workflows/
 */
export type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
export type TaskStatus = 'pending' | 'dispatched' | 'running' | 'review' | 'passed' | 'failed' | 'done' | 'paused' | 'cancelled';
export type AgentType = 'implementer' | 'spec_reviewer' | 'code_reviewer';
export type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS' | 'DEBUG';
export type WorkflowPhase = 'orchestrate' | 'plan' | 'dispatch' | 'review' | 'complete' | 'cancel';
export interface LogEntry {
    log_id: string;
    workflow_id: string;
    task_id?: string;
    timestamp: string;
    level: LogLevel;
    phase: WorkflowPhase;
    message: string;
    details?: Record<string, unknown>;
}
export interface ReviewNote {
    reviewer: AgentType;
    passed: boolean;
    notes: string;
    timestamp: string;
    attempt: number;
}
export interface Task {
    task_id: string;
    workflow_id: string;
    title: string;
    description: string;
    spec?: string;
    agent_type: AgentType;
    status: TaskStatus;
    attempts: number;
    max_attempts: number;
    depends_on: string[];
    output?: unknown;
    review_notes: ReviewNote[];
    created_at: string;
    dispatched_at?: string;
    completed_at?: string;
    error?: string;
    timeout_ms?: number;
    cost?: {
        inputTokens: number;
        outputTokens: number;
        cacheReadTokens: number;
        cacheWriteTokens: number;
        costUsd: number;
    };
}
export interface Workflow {
    workflow_id: string;
    goal: string;
    plan?: string;
    status: WorkflowStatus;
    tasks: string[];
    created_at: string;
    updated_at: string;
    completed_at?: string;
    result?: unknown;
    error?: string;
    total_tasks: number;
    completed_tasks: number;
    total_cost?: {
        inputTokens: number;
        outputTokens: number;
        cacheReadTokens: number;
        cacheWriteTokens: number;
        costUsd: number;
    };
    background?: boolean;
    report_path?: string;
    max_cost_usd?: number;
    cost_alert_threshold?: number;
    accumulated_cost_usd?: number;
}
export declare function initStore(): Promise<void>;
export declare function createWorkflow(goal: string, plan?: string): Promise<Workflow>;
export declare function getWorkflow(wfId: string): Promise<Workflow | null>;
export declare function updateWorkflow(wfId: string, updates: Partial<Workflow>): Promise<Workflow | null>;
export declare function listWorkflows(status?: WorkflowStatus): Promise<Workflow[]>;
export declare function deleteWorkflow(wfId: string): Promise<void>;
export declare function createTask(params: {
    workflow_id: string;
    title: string;
    description: string;
    spec?: string;
    agent_type: AgentType;
    depends_on?: string[];
    max_attempts?: number;
    timeout_ms?: number;
}): Promise<Task>;
export declare function getTask(taskId: string): Promise<Task | null>;
export declare function updateTask(taskId: string, updates: Partial<Task>): Promise<Task | null>;
export declare function deleteTask(taskId: string): Promise<void>;
export declare function getRunnableTasks(wfId: string): Promise<Task[]>;
export declare function cancelWorkflow(wfId: string, reason?: string): Promise<Workflow | null>;
export declare function pauseWorkflow(wfId: string): Promise<Workflow | null>;
export declare function resumeWorkflow(wfId: string): Promise<Workflow | null>;
export declare function cancelTask(taskId: string, reason?: string): Promise<Task | null>;
export declare function pauseTask(taskId: string): Promise<Task | null>;
export declare function resumeTask(taskId: string): Promise<Task | null>;
export declare function accumulateCost(wfId: string, costUsd: number): Promise<number>;
export declare function getAccumulatedCost(wfId: string): Promise<number>;
export declare function appendLog(entry: Omit<LogEntry, 'log_id' | 'timestamp'>): Promise<LogEntry>;
export declare function getLogs(wfId: string, taskId?: string): Promise<LogEntry[]>;
export declare function getWorkflowSummary(wfId: string): Promise<{
    workflow: Workflow | null;
    tasks: Task[];
    logs: LogEntry[];
}>;
//# sourceMappingURL=workflow-store.d.ts.map