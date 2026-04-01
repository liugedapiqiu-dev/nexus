declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            task_id: {
                type: string;
            };
            outcome: {
                type: string;
            };
            success: {
                type: string;
            };
            lessons: {
                type: string;
            };
        };
        required: string[];
    };
    run({ task_id, outcome, success, lessons }: {
        task_id?: string;
        outcome: string;
        success: boolean;
        lessons?: string;
    }): Promise<{
        success: boolean;
        message: string;
        reflection_id: string;
    }>;
};
export default _default;
//# sourceMappingURL=reflect.d.ts.map