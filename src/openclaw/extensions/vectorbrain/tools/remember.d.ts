declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            text: {
                type: string;
                description: string;
            };
            category: {
                type: string;
                description: string;
                default: string;
            };
        };
        required: string[];
    };
    run({ text, category }: {
        text: string;
        category?: string;
    }): Promise<{
        success: boolean;
        message: string;
        category: string;
        timestamp: string;
    }>;
};
export default _default;
//# sourceMappingURL=remember.d.ts.map