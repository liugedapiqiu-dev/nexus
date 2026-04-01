/**
 * VectorBrain Orchestrate Tool
 * Accepts a goal + optional task definitions.
 * Supports background execution, auto-decomposition, and task templates.
 */
import { OrchestrationResult } from '../mcp/orchestrate.js';
declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            goal: {
                type: string;
                description: string;
            };
            tasks: {
                type: string;
                description: string;
                items: {
                    type: string;
                    properties: {
                        title: {
                            type: string;
                        };
                        description: {
                            type: string;
                        };
                        spec: {
                            type: string;
                        };
                        agent_type: {
                            type: string;
                            enum: string[];
                        };
                        depends_on: {
                            type: string;
                            items: {
                                type: string;
                            };
                        };
                        timeout_ms: {
                            type: string;
                            description: string;
                        };
                    };
                    required: string[];
                };
            };
            model: {
                type: string;
                description: string;
            };
            max_attempts: {
                type: string;
                description: string;
                default: number;
            };
            max_cost_usd: {
                type: string;
                description: string;
            };
            cost_alert_threshold: {
                type: string;
                description: string;
            };
            auto_decompose: {
                type: string;
                description: string;
                default: boolean;
            };
            background: {
                type: string;
                description: string;
                default: boolean;
            };
            notify: {
                type: string;
                description: string;
                default: string;
            };
            template_id: {
                type: string;
                description: string;
            };
        };
        required: string[];
    };
    execute(_toolCallId: string, opts: {
        goal: string;
        tasks?: Array<{
            title: string;
            description: string;
            spec?: string;
            agent_type: "implementer" | "spec_reviewer" | "code_reviewer";
            depends_on?: string[];
            timeout_ms?: number;
        }>;
        model?: string;
        max_attempts?: number;
        max_cost_usd?: number;
        cost_alert_threshold?: number;
        auto_decompose?: boolean;
        background?: boolean;
        notify?: string;
        template_id?: string;
    }, _signal?: AbortSignal): Promise<OrchestrationResult | {
        workflow_id: string;
        background: true;
        message: string;
    }>;
};
export default _default;
//# sourceMappingURL=orchestrate-goal.d.ts.map