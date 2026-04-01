/**
 * VectorBrain Templates Tool
 * List, save, and manage reusable task templates.
 */

import {
  listTemplates, saveTemplate, deleteTemplate, getTemplate,
  BUILTIN_TEMPLATES, TaskTemplate,
} from '../mcp/templates-store.js';

export default {
  name: 'vectorbrain.templates',
  description: 'Manage VectorBrain workflow templates. List available templates, save new ones, or delete templates. Templates let you save and reuse common task patterns (e.g., "代码审查", "数据分析", "深度研究").',

  parameters: {
    type: 'object',
    properties: {
      action: {
        type: 'string',
        description: 'Action to perform: list | save | delete | get',
        enum: ['list', 'save', 'delete', 'get'],
      },
      name: {
        type: 'string',
        description: 'Template name (for save action)',
      },
      description: {
        type: 'string',
        description: 'Template description (for save action)',
      },
      tasks: {
        type: 'array',
        description: 'Task definitions (for save action)',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            description: { type: 'string' },
            spec: { type: 'string' },
            agent_type: { type: 'string', enum: ['implementer', 'spec_reviewer', 'code_reviewer'] },
            depends_on: { type: 'array', items: { type: 'string' } },
          },
          required: ['title', 'description', 'agent_type'],
        },
      },
      template_id: {
        type: 'string',
        description: 'Template ID (for delete/get actions)',
      },
    },
    required: ['action'],
  },

  async execute(
    _toolCallId: string,
    opts: {
      action: 'list' | 'save' | 'delete' | 'get';
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
    },
    _signal?: AbortSignal
  ): Promise<{
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
  }> {
    switch (opts.action) {
      case 'list': {
        const user = await listTemplates();
        const builtin = BUILTIN_TEMPLATES.map(t => ({
          template_id: t.template_id,
          name: t.name,
          description: t.description,
          task_count: t.tasks.length,
          usage_count: t.usage_count,
          last_used_at: t.last_used_at,
        }));
        const custom = user.map(t => ({
          template_id: t.template_id,
          name: t.name,
          description: t.description,
          task_count: t.tasks.length,
          usage_count: t.usage_count,
          last_used_at: t.last_used_at,
        }));
        return {
          success: true,
          message: `共 ${builtin.length + custom.length} 个模板（${builtin.length} 内置 + ${custom.length} 自定义）`,
          templates: [...builtin, ...custom],
        };
      }

      case 'save': {
        if (!opts.name || !opts.tasks || opts.tasks.length === 0) {
          return { success: false, message: 'save 需要 name 和 tasks 参数' };
        }
        const saved = await saveTemplate({
          name: opts.name,
          description: opts.description ?? '',
          tasks: opts.tasks as TaskTemplate['tasks'],
        });
        return {
          success: true,
          message: `模板已保存: ${saved.template_id}`,
          template: {
            template_id: saved.template_id,
            name: saved.name,
            description: saved.description,
            tasks: saved.tasks,
            usage_count: saved.usage_count,
          },
        };
      }

      case 'get': {
        if (!opts.template_id) return { success: false, message: 'get 需要 template_id 参数' };
        const template = await getTemplate(opts.template_id);
        if (template) {
          return {
            success: true,
            message: `模板: ${template.name}`,
            template: {
              template_id: template.template_id,
              name: template.name,
              description: template.description,
              tasks: template.tasks,
              usage_count: template.usage_count,
            },
          };
        }
        const builtin = BUILTIN_TEMPLATES.find(t => t.template_id === opts.template_id);
        if (builtin) {
          return {
            success: true,
            message: `内置模板: ${builtin.name}`,
            template: {
              template_id: builtin.template_id,
              name: builtin.name,
              description: builtin.description,
              tasks: builtin.tasks,
              usage_count: builtin.usage_count,
            },
          };
        }
        return { success: false, message: `Template not found: ${opts.template_id}` };
      }

      case 'delete': {
        if (!opts.template_id) return { success: false, message: 'delete 需要 template_id 参数' };
        if (opts.template_id.startsWith('builtin:')) {
          return { success: false, message: '内置模板不能删除' };
        }
        await deleteTemplate(opts.template_id);
        return { success: true, message: `已删除模板: ${opts.template_id}` };
      }

      default:
        return { success: false, message: `Unknown action: ${opts.action}` };
    }
  },
};
