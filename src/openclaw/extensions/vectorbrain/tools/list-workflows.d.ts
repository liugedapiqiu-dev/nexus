/**
 * VectorBrain List Workflows Tool
 * List all workflows, optionally filtered by status.
 */
declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            status: {
                type: string;
                description: string;
                enum: string[];
            };
        };
    };
    execute(_toolCallId: string, opts?: {
        status?: string;
    }, _signal?: AbortSignal): Promise<{
        workflows: Array<{
            workflow_id: string;
            goal: string;
            status: string;
            total_tasks: number;
            completed_tasks: number;
            created_at: string;
            completed_at?: string;
        }>;
    }>;
};
export default _default;
//# sourceMappingURL=list-workflows.d.ts.map