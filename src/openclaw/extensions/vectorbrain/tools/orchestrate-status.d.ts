/**
 * VectorBrain Workflow Status Tool
 * Query the status of a running or completed workflow.
 * Supports cancel, pause, and resume actions.
 */
declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            workflow_id: {
                type: string;
                description: string;
            };
            action: {
                type: string;
                description: string;
                enum: string[];
            };
            task_id: {
                type: string;
                description: string;
            };
        };
        required: string[];
    };
    execute(_toolCallId: string, opts: {
        workflow_id: string;
        action?: string;
        task_id?: string;
    }, _signal?: AbortSignal): Promise<{
        workflow_id: string;
        found?: boolean;
        status?: string;
        goal?: string;
        total_tasks?: number;
        completed_tasks?: number;
        tasks?: Array<{
            task_id: string;
            title: string;
            status: string;
            error?: string;
            attempts: number;
            review_notes: unknown[];
        }>;
        logs?: unknown[];
        error?: string;
        message?: string;
        action_result?: string;
    }>;
};
export default _default;
//# sourceMappingURL=orchestrate-status.d.ts.map