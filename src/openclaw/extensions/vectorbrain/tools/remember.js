import fs from "fs";
import path from "path";
import { getVbDir, ensureDir } from "../mcp/utils.js";
export default {
    name: "vectorbrain.remember",
    description: "Store a memory to VectorBrain. Use this when user says 'remember', 'save this', 'don't forget', etc.",
    parameters: {
        type: "object",
        properties: {
            text: {
                type: "string",
                description: "The content to remember"
            },
            category: {
                type: "string",
                description: "Category of the memory (optional)",
                default: "general"
            }
        },
        required: ["text"]
    },
    async run({ text, category = "general" }) {
        const memoryDir = path.join(getVbDir(), "memory");
        const logPath = path.join(memoryDir, "log.txt");
        await ensureDir(memoryDir);
        // Format memory entry
        const timestamp = new Date().toISOString();
        const entry = `[${timestamp}] [${category}] ${text}\n`;
        // Append to log file
        fs.appendFileSync(logPath, entry, "utf-8");
        console.log(`✅ Memory stored: ${text.substring(0, 50)}...`);
        return {
            success: true,
            message: "Memory stored successfully",
            category: category,
            timestamp: timestamp
        };
    }
};
//# sourceMappingURL=remember.js.map