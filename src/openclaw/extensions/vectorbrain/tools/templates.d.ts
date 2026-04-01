/**
 * VectorBrain Templates Tool
 * List, save, and manage reusable task templates.
 */
declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            action: {
                type: string;
                description: string;
                enum: string[];
            };
            name: {
                type: string;
                description: string;
            };
            description: {
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
                    };
                    required: string[];
                };
            };
            template_id: {
                type: string;
                description: string;
            };
        };
        required: string[];
    };
    execute(_toolCallId: string, opts: {
        action: "list" | "save" | "delete" | "get";
        name?: string;
        description?: string;
        tasks?: Array<{
            title: string;
            description: string;
            spec?: string;
            agent_type: string;
            depends_on?: string[];
        }>;
        template_id?: string;
    }, _signal?: AbortSignal): Promise<{
        success: boolean;
        message: string;
        templates?: Array<{
            template_id: string;
            name: string;
            description: string;
            task_count: number;
            usage_count: number;
            last_used_at?: string;
        }>;
        template?: {
            template_id: string;
            name: string;
            description: string;
            tasks: unknown[];
            usage_count: number;
        };
    }>;
};
export default _default;
//# sourceMappingURL=templates.d.ts.map