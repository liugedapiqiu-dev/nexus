declare const _default: {
    name: string;
    description: string;
    parameters: {
        type: string;
        properties: {
            model: {
                type: string;
                description: string;
            };
            provider: {
                type: string;
                description: string;
                enum: string[];
            };
            input_tokens: {
                type: string;
                description: string;
            };
            output_tokens: {
                type: string;
                description: string;
            };
            session_key: {
                type: string;
                description: string;
            };
            duration_ms: {
                type: string;
                description: string;
            };
            request_id: {
                type: string;
                description: string;
            };
            cost: {
                type: string;
                description: string;
            };
        };
        required: string[];
    };
    run({ model, provider, input_tokens, output_tokens, session_key, duration_ms, request_id, cost }: {
        model: string;
        provider: string;
        input_tokens: number;
        output_tokens: number;
        session_key?: string;
        duration_ms?: number;
        request_id?: string;
        cost?: number;
    }): Promise<unknown>;
};
export default _default;
//# sourceMappingURL=intercept_tokens.d.ts.map