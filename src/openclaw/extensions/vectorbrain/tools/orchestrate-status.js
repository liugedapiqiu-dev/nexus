/**
 * VectorBrain Workflow Status Tool
 * Query the status of a running or completed workflow.
 * Supports cancel, pause, and resume actions.
 */
import { getWorkflowSummary, cancelWorkflow as cancelWorkflowStore, pauseWorkflow as pauseWorkflowStore, resumeWorkflow as resumeWorkflowStore, cancelTask as cancelTaskStore, } from '../mcp/workflow-store.js';
export default {
    name: 'vectorbrain.workflow_status',
    description: 'Query the status of a VectorBrain workflow, or cancel/pause/resume it. Use to check progress of a running orchestration, retrieve results from a completed one, or control workflow lifecycle. Returns workflow summary with all tasks and logs.',
    parameters: {
        type: 'object',
        properties: {
            workflow_id: {
                type: 'string',
                description: 'The workflow ID returned from vectorbrain.orchestrate',
            },
            action: {
                type: 'string',
                description: 'Action to perform: status (default) | cancel | pause | resume',
                enum: ['status', 'cancel', 'pause', 'resume'],
            },
            task_id: {
                type: 'string',
                description: 'Task ID to cancel (only used when action=cancel and cancelling a specific task)',
            },
        },
        required: ['workflow_id'],
    },
    async execute(_toolCallId, opts, _signal) {
        try {
            // Handle lifecycle actions
            if (opts.action === 'cancel') {
                if (opts.task_id) {
                    // Cancel specific task
                    const result = await cancelTaskStore(opts.task_id, 'User cancelled');
                    return {
                        workflow_id: opts.workflow_id,
                        found: true,
                        action_result: `Task ${opts.task_id} cancelled`,
                        message: result ? 'Task cancelled successfully' : 'Task not found or already terminal',
                    };
                }
                else {
                    // Cancel entire workflow
                    const result = await cancelWorkflowStore(opts.workflow_id, 'User cancelled');
                    return {
                        workflow_id: opts.workflow_id,
                        found: !!result,
                        action_result: 'workflow_cancelled',
                        status: 'cancelled',
                        message: result ? 'Workflow cancelled successfully' : 'Workflow not found',
                    };
                }
            }
            if (opts.action === 'pause') {
                const result = await pauseWorkflowStore(opts.workflow_id);
                return {
                    workflow_id: opts.workflow_id,
                    found: !!result,
                    action_result: 'workflow_paused',
                    status: 'paused',
                    message: result ? 'Workflow paused successfully' : 'Workflow not found or not in running state',
                };
            }
            if (opts.action === 'resume') {
                const result = await resumeWorkflowStore(opts.workflow_id);
                return {
                    workflow_id: opts.workflow_id,
                    found: !!result,
                    action_result: 'workflow_resumed',
                    status: result?.status,
                    message: result ? 'Workflow resumed successfully' : 'Workflow not found or not in paused state',
                };
            }
            // Default: get status
            const summary = await getWorkflowSummary(opts.workflow_id);
            if (!summary.workflow) {
                return { workflow_id: opts.workflow_id, found: false, error: 'Workflow not found' };
            }
            return {
                workflow_id: opts.workflow_id,
                found: true,
                status: summary.workflow.status,
                goal: summary.workflow.goal,
                total_tasks: summary.workflow.total_tasks,
                completed_tasks: summary.workflow.completed_tasks,
                tasks: summary.tasks.map(t => ({
                    task_id: t.task_id,
                    title: t.title,
                    status: t.status,
                    error: t.error,
                    attempts: t.attempts,
                    review_notes: t.review_notes,
                })),
                logs: summary.logs,
            };
        }
        catch (err) {
            const errorMsg = err instanceof Error ? err.message : String(err);
            return { workflow_id: opts.workflow_id, found: false, error: errorMsg };
        }
    },
};
//# sourceMappingURL=orchestrate-status.js.map