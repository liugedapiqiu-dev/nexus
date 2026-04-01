declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            status: {
                type: string;
                default: string;
            };
        };
    };
    run({ status }: {
        status?: string;
    }): Promise<{
        tasks: never[];
        success?: undefined;
    } | {
        success: boolean;
        tasks: any[];
    }>;
};
export default _default;
//# sourceMappingURL=list_tasks.d.ts.map