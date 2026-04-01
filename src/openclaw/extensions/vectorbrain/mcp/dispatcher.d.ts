/**
 * VectorBrain Dispatcher
 * 通过 claude CLI 派发子 agent 执行任务
 */
import { Task } from './workflow-store.js';
/**
 * Load skill content from disk and cache it
 */
export declare function loadSkillContent(skillName: string): string | null;
/**
 * Detect relevant skills based on task description
 */
export declare function detectRelevantSkills(taskTitle: string, taskDescription?: string): string[];
export interface DispatchOptions {
    task: Task;
    workflowId: string;
    systemPrompt: string;
    taskPrompt: string;
    model?: string;
    maxDurationMs?: number;
    signal?: AbortSignal;
}
export interface DispatchResult {
    success: boolean;
    output?: unknown;
    error?: string;
    duration_ms: number;
    log_id: string;
    cost?: {
        inputTokens: number;
        outputTokens: number;
        cacheReadTokens: number;
        cacheWriteTokens: number;
        costUsd: number;
    };
}
export declare function dispatchTask(opts: DispatchOptions): Promise<DispatchResult>;
export declare function getSkillRegistry(): string;
export declare function buildSkillContent(skillNames: string[]): string;
export declare function getImplementerPrompt(context?: {
    workflowGoal?: string;
    taskSpec?: string;
    constraints?: string[];
    skillNames?: string[];
}): string;
export declare function getSpecReviewerPrompt(): string;
export declare function getCodeQualityReviewerPrompt(): string;
//# sourceMappingURL=dispatcher.d.ts.map