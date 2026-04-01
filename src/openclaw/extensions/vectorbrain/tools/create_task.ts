import fs from "fs"
import path from "path"
import { getVbDir, ensureDir } from "../mcp/utils.js"

export default {
  name: "vectorbrain.create_task",
  description: "Create a task in VectorBrain task queue. Use when user says 'create a task', 'add to todo', 'remind me to', etc.",

  parameters: {
    type: "object",
    properties: {
      title: { type: "string", description: "Task title" },
      description: { type: "string", description: "Task description" },
      priority: { type: "number", description: "Priority 1-10", default: 5 }
    },
    required: ["title"]
  },

  async run({ title, description = "", priority = 5 }: { title: string, description?: string, priority?: number }) {
    const tasksDir = path.join(getVbDir(), "tasks")
    await ensureDir(tasksDir)

    const task = {
      task_id: `task_${Date.now()}`,
      title,
      description,
      priority,
      status: "pending",
      created_at: new Date().toISOString()
    }

    const taskFile = path.join(tasksDir, `${task.task_id}.json`)
    fs.writeFileSync(taskFile, JSON.stringify(task, null, 2))

    return {
      success: true,
      message: `Task created: ${title}`,
      task_id: task.task_id
    }
  }
}
