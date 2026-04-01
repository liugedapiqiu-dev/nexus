import fs from "fs"
import path from "path"
import { getVbDir } from "../mcp/utils.js"

export default {
  name: "vectorbrain.recall",
  description: "Read memories from VectorBrain. Use this when user asks 'what did I say', 'show me my memories', 'recall', etc.",

  parameters: {
    type: "object",
    properties: {
      limit: {
        type: "number",
        description: "Number of recent memories to return",
        default: 10
      },
      keyword: {
        type: "string",
        description: "Keyword to filter memories (optional)"
      }
    },
    required: []
  },

  async run({ limit = 10, keyword }: { limit?: number, keyword?: string }) {
    const logPath = path.join(getVbDir(), "memory", "log.txt")

    // Check if memory file exists
    if (!fs.existsSync(logPath)) {
      return {
        success: true,
        message: "No memories found",
        memories: []
      }
    }

    // Read all memories
    const content = fs.readFileSync(logPath, "utf-8")
    const lines = content.trim().split("\n").filter(line => line.trim())

    // Filter by keyword if provided
    let memories = lines
    if (keyword) {
      memories = memories.filter(line =>
        line.toLowerCase().includes(keyword.toLowerCase())
      )
    }

    // Get recent memories
    const recent = memories.slice(-limit).reverse()

    // Parse memories
    const parsed = recent.map(line => {
      const match = line.match(/^\[(.*?)\] \[(.*?)\] (.*)$/)
      if (match) {
        return {
          timestamp: match[1],
          category: match[2],
          text: match[3]
        }
      }
      return { text: line }
    })

    return {
      success: true,
      message: `Found ${parsed.length} memories`,
      memories: parsed,
      total: memories.length
    }
  }
}
