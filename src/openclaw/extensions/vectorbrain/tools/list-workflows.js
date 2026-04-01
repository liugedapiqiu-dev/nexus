/**
 * VectorBrain List Workflows Tool
 * List all workflows, optionally filtered by status.
 */
import { listWorkflows } from '../mcp/workflow-store.js';
export default {
    name: 'vectorbrain.list_workflows',
    description: 'List all VectorBrain workflows. Use to find workflow IDs and see overall status. Can filter by status: pending, running, paused, completed, failed, cancelled.',
    parameters: {
        type: 'object',
        properties: {
            status: {
                type: 'string',
                description: 'Filter by workflow status (optional)',
                enum: ['pending', 'running', 'paused', 'completed', 'failed', 'cancelled'],
            },
        },
    },
    async execute(_toolCallId, opts, _signal) {
        const status = opts?.status;
        const wfs = await listWorkflows(status);
        return {
            workflows: wfs.map(w => ({
                workflow_id: w.workflow_id,
                goal: w.goal,
                status: w.status,
                total_tasks: w.total_tasks,
                completed_tasks: w.completed_tasks,
                created_at: w.created_at,
                completed_at: w.completed_at,
            })),
        };
    },
};
//# sourceMappingURL=list-workflows.js.map