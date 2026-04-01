#!/usr/bin/env python3
"""
VectorBrain File Tools

文件相关工具：
- read_file: 读取文件
- write_file: 写入文件
"""

from runtime.tools.registry import tool_registry, Tool
from typing import Dict, Any
from pathlib import Path
import asyncio

# ============================================================================
# read_file 工具
# ============================================================================

async def read_file_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    读取文件内容
    
    Args:
        input: {"path": str}
        
    Returns:
        {"success": bool, "data": {"content": str, "path": str}, "error": str|None}
    """
    try:
        path = input["path"]
        file_path = Path(path).expanduser()
        
        print(f"[read_file] Reading: {file_path}")
        
        if not file_path.exists():
            return {
                "success": False,
                "data": None,
                "error": f"File not found: {path}"
            }
        
        content = file_path.read_text(encoding="utf-8")
        
        return {
            "success": True,
            "data": {"content": content, "path": str(file_path)},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


read_file_tool = Tool(
    name="read_file",
    display_name="Read File",
    description="Read content from a file",
    capabilities=["analysis", "read"],
    input_schema={
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {"type": "string", "description": "File path to read"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "path": {"type": "string"}
        }
    },
    handler=read_file_handler,
    timeout=30,
    version="1.0",
    allow_dry_run=True
)

tool_registry.register(read_file_tool)


# ============================================================================
# write_file 工具
# ============================================================================

async def write_file_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    写入文件内容
    
    Args:
        input: {"path": str, "content": str}
        
    Returns:
        {"success": bool, "data": {"path": str, "bytes": int}, "error": str|None}
    """
    try:
        path = input["path"]
        content = input["content"]
        file_path = Path(path).expanduser()
        
        print(f"[write_file] Writing: {file_path}")
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        file_path.write_text(content, encoding="utf-8")
        
        return {
            "success": True,
            "data": {"path": str(file_path), "bytes": len(content)},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


write_file_tool = Tool(
    name="write_file",
    display_name="Write File",
    description="Write content to a file",
    capabilities=["coding", "writing", "write"],
    input_schema={
        "type": "object",
        "required": ["path", "content"],
        "properties": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "bytes": {"type": "integer"}
        }
    },
    handler=write_file_handler,
    timeout=30,
    version="1.0",
    allow_dry_run=True
)

tool_registry.register(write_file_tool)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("Testing file_tools...")
    
    async def test():
        # 测试 write_file
        result = await write_file_tool.handler({
            "path": "~/test_file.txt",
            "content": "Hello, World!"
        })
        print(f"write_file result: {result}")
        
        # 测试 read_file
        result = await read_file_tool.handler({
            "path": "~/test_file.txt"
        })
        print(f"read_file result: {result}")
    
    asyncio.run(test())
