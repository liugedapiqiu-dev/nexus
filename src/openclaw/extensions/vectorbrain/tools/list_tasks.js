import path from "path";
import { listFiles, getVbDir } from "../mcp/utils.js";
export default {
    name: "vectorbrain.list_tasks",
    description: "List pending tasks from VectorBrain",
    parameters: {
        type: "object",
        properties: {
            status: { type: "string", default: "pending" }
        }
    },
    async run({ status = "pending" }) {
        const tasksDir = path.join(getVbDir(), "tasks");
        const files = await listFiles(tasksDir, ".json");
        if (files.length === 0)
            return { tasks: [] };
        const { readJson } = await import("../mcp/utils.js");
        const all = await Promise.all(files.map(f => readJson(f)));
        const tasks = all.filter(t => t && t.status === status);
        return {
            success: true,
            tasks: tasks.sort((a, b) => a.priority - b.priority)
        };
    }
};
//# sourceMappingURL=list_tasks.js.map