declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            limit: {
                type: string;
                description: string;
                default: number;
            };
            keyword: {
                type: string;
                description: string;
            };
        };
        required: never[];
    };
    run({ limit, keyword }: {
        limit?: number;
        keyword?: string;
    }): Promise<{
        success: boolean;
        message: string;
        memories: never[];
        total?: undefined;
    } | {
        success: boolean;
        message: string;
        memories: ({
            timestamp: string | undefined;
            category: string | undefined;
            text: string | undefined;
        } | {
            text: string;
            timestamp?: undefined;
            category?: undefined;
        })[];
        total: number;
    }>;
};
export default _default;
//# sourceMappingURL=recall.d.ts.map