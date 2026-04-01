declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            title: {
                type: string;
                description: string;
            };
            description: {
                type: string;
                description: string;
            };
            priority: {
                type: string;
                description: string;
                default: number;
            };
        };
        required: string[];
    };
    run({ title, description, priority }: {
        title: string;
        description?: string;
        priority?: number;
    }): Promise<{
        success: boolean;
        message: string;
        task_id: string;
    }>;
};
export default _default;
//# sourceMappingURL=create_task.d.ts.map