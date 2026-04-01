#!/usr/bin/env python3
"""
VectorBrain Shell Tools

Shell 命令相关工具：
- exec_shell: 执行 shell 命令
"""

from runtime.tools.registry import tool_registry, Tool
from typing import Dict, Any
import asyncio
import subprocess

# ============================================================================
# exec_shell 工具
# ============================================================================

async def exec_shell_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行 shell 命令
    
    Args:
        input: {"cmd": str}
        
    Returns:
        {"success": bool, "data": {"output": str, "exit_code": int}, "error": str|None}
    """
    try:
        cmd = input["cmd"]
        print(f"[exec_shell] Executing: {cmd}")
        
        # 执行命令
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        output = stdout.decode("utf-8").strip()
        error_output = stderr.decode("utf-8").strip()
        
        result = {
            "success": process.returncode == 0,
            "data": {
                "output": output if output else error_output,
                "exit_code": process.returncode
            },
            "error": None if process.returncode == 0 else f"Command failed with exit code {process.returncode}"
        }
        
        print(f"[exec_shell] Exit code: {process.returncode}")
        
        return result
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


exec_shell_tool = Tool(
    name="exec_shell",
    display_name="Execute Shell",
    description="Execute a shell command",
    capabilities=["automation", "shell", "execute"],
    input_schema={
        "type": "object",
        "required": ["cmd"],
        "properties": {
            "cmd": {"type": "string", "description": "Shell command to execute"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "output": {"type": "string"},
            "exit_code": {"type": "integer"}
        }
    },
    handler=exec_shell_handler,
    timeout=120,
    version="1.0",
    allow_dry_run=False  # Shell 命令不支持 dry_run
)

tool_registry.register(exec_shell_tool)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("Testing shell_tools...")
    
    async def test():
        # 测试简单命令
        result = await exec_shell_tool.handler({
            "cmd": "echo 'Hello, World!'"
        })
        print(f"exec_shell result: {result}")
        
        # 测试列出文件
        result = await exec_shell_tool.handler({
            "cmd": "ls -la ~/.vectorbrain/runtime/tools/builtin/"
        })
        print(f"exec_shell result: {result}")
    
    asyncio.run(test())
