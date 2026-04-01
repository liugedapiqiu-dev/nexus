/**
 * VectorBrain Task Templates
 * 保存和复用常见工作流模式
 * 存储在 ~/.vectorbrain/templates/
 */
export interface TaskTemplate {
    template_id: string;
    name: string;
    description: string;
    tasks: Array<{
        title: string;
        description: string;
        spec?: string;
        agent_type: 'implementer' | 'spec_reviewer' | 'code_reviewer';
        depends_on: string[];
    }>;
    created_at: string;
    usage_count: number;
    last_used_at?: string;
}
export declare function listTemplates(): Promise<TaskTemplate[]>;
export declare function getTemplate(templateId: string): Promise<TaskTemplate | null>;
export declare function saveTemplate(params: {
    name: string;
    description: string;
    tasks: TaskTemplate['tasks'];
}): Promise<TaskTemplate>;
export declare function incrementUsage(templateId: string): Promise<void>;
export declare function deleteTemplate(templateId: string): Promise<void>;
export declare const BUILTIN_TEMPLATES: TaskTemplate[];
//# sourceMappingURL=templates-store.d.ts.map