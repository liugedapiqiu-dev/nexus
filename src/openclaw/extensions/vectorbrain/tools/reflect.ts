import fs from "fs"
import path from "path"
import { getVbDir, ensureDir } from "../mcp/utils.js"

export default {
  name: "vectorbrain.reflect",
  description: "Record a reflection after completing a task",

  parameters: {
    type: "object",
    properties: {
      task_id: { type: "string" },
      outcome: { type: "string" },
      success: { type: "boolean" },
      lessons: { type: "string" }
    },
    required: ["outcome", "success"]
  },

  async run({ task_id, outcome, success, lessons = "" }: { task_id?: string, outcome: string, success: boolean, lessons?: string }) {
    const reflectDir = path.join(getVbDir(), "reflection")
    await ensureDir(reflectDir)

    const reflection = {
      reflection_id: `ref_${Date.now()}`,
      task_id,
      outcome,
      success,
      lessons,
      created_at: new Date().toISOString()
    }

    const reflectFile = path.join(reflectDir, `${reflection.reflection_id}.json`)
    fs.writeFileSync(reflectFile, JSON.stringify(reflection, null, 2))

    return {
      success: true,
      message: "Reflection recorded",
      reflection_id: reflection.reflection_id
    }
  }
}
