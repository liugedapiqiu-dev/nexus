/**
 * VectorBrain Task Templates
 * 保存和复用常见工作流模式
 * 存储在 ~/.vectorbrain/templates/
 */

import fs from 'fs';
import path from 'path';
import { readJson, writeJson, listFiles, getVbDir, ensureDir } from './utils.js';

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

const TEMPLATES_DIR = path.join(getVbDir(), 'templates');

function id(prefix = 'tmpl'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

export async function listTemplates(): Promise<TaskTemplate[]> {
  await ensureDir(TEMPLATES_DIR);
  const files = await listFiles(TEMPLATES_DIR, '.json');
  const templates = await Promise.all(files.map(f => readJson<TaskTemplate>(f)));
  return templates.filter(t => t !== null).sort((a, b) =>
    b.last_used_at?.localeCompare(a.last_used_at ?? '') ?? b.created_at.localeCompare(a.created_at));
}

export async function getTemplate(templateId: string): Promise<TaskTemplate | null> {
  return readJson<TaskTemplate>(path.join(TEMPLATES_DIR, `${templateId}.json`));
}

export async function saveTemplate(params: {
  name: string;
  description: string;
  tasks: TaskTemplate['tasks'];
}): Promise<TaskTemplate> {
  await ensureDir(TEMPLATES_DIR);
  const template: TaskTemplate = {
    template_id: id('tmpl'),
    name: params.name,
    description: params.description,
    tasks: params.tasks,
    created_at: new Date().toISOString(),
    usage_count: 0,
  };
  await writeJson(path.join(TEMPLATES_DIR, `${template.template_id}.json`), template);
  return template;
}

export async function incrementUsage(templateId: string): Promise<void> {
  const t = await getTemplate(templateId);
  if (!t) return;
  t.usage_count++;
  t.last_used_at = new Date().toISOString();
  await writeJson(path.join(TEMPLATES_DIR, `${templateId}.json`), t);
}

export async function deleteTemplate(templateId: string): Promise<void> {
  try {
    fs.unlinkSync(path.join(TEMPLATES_DIR, `${templateId}.json`));
  } catch {}
}

// ─── 内置模板 ────────────────────────────────────────────────────────────────

export const BUILTIN_TEMPLATES: TaskTemplate[] = [
  {
    template_id: 'builtin:code-review',
    name: '代码审查',
    description: '对指定代码文件或目录进行完整审查',
    tasks: [
      { title: '读取代码', description: '读取并分析指定路径的代码文件', agent_type: 'implementer', depends_on: [] },
      { title: '代码质量审查', description: '检查代码质量、可读性、错误处理', agent_type: 'code_reviewer', depends_on: [] },
      { title: '安全漏洞检查', description: '检查是否有安全漏洞：注入、依赖问题等', agent_type: 'implementer', depends_on: [] },
    ],
    created_at: '2026-04-01T00:00:00Z',
    usage_count: 0,
  },
  {
    template_id: 'builtin:data-analysis',
    name: '数据分析报告',
    description: '读取数据文件并生成分析报告',
    tasks: [
      { title: '读取数据', description: '读取并理解数据文件结构', agent_type: 'implementer', depends_on: [] },
      { title: '探索性分析', description: '进行探索性数据分析（EDA）', agent_type: 'implementer', depends_on: [] },
      { title: '生成报告', description: '生成结构化分析报告', agent_type: 'implementer', depends_on: [] },
    ],
    created_at: '2026-04-01T00:00:00Z',
    usage_count: 0,
  },
  {
    template_id: 'builtin:research',
    name: '深度研究',
    description: '对一个主题进行深度研究并输出报告',
    tasks: [
      { title: '搜集资料', description: '搜集与主题相关的资料和信息', agent_type: 'implementer', depends_on: [] },
      { title: '整理分析', description: '整理资料，提炼关键观点', agent_type: 'implementer', depends_on: [] },
      { title: '撰写报告', description: '撰写完整的研究报告', agent_type: 'implementer', depends_on: [] },
    ],
    created_at: '2026-04-01T00:00:00Z',
    usage_count: 0,
  },
];
