#!/usr/bin/env python3
"""
VectorBrain V4 - Planner API

提供 REST API 接口接收用户目标
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path.home() / ".vectorbrain"))

from flask import Flask, request, jsonify
from planner.planner_core import run_planner

app = Flask(__name__)


@app.route('/api/v1/goals', methods=['POST'])
def create_goal():
    """
    创建新目标并自动生成任务计划
    
    Request JSON:
    {
        "goal": "列出当前目录的文件",
        "priority": 5  # 可选，默认 5
    }
    
    Response JSON:
    {
        "success": true,
        "goal_id": "goal_xxx",
        "tasks": ["task_xxx", "task_yyy"],
        "tasks_count": 2,
        "patterns_used": 1
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'goal' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'goal' field"
            }), 400
        
        goal_text = data['goal']
        priority = data.get('priority', 5)
        
        print(f"\n🎯 收到新目标：{goal_text}")
        
        # 运行 Planner
        result = run_planner(goal_text, priority)
        
        return jsonify({
            "success": result["success"],
            "goal_id": result["goal_id"],
            "tasks": result["task_ids"],
            "tasks_count": result["tasks_count"],
            "patterns_used": result["patterns_found"]
        })
    
    except Exception as e:
        print(f"❌ API 错误：{e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/goals/<goal_id>/status', methods=['GET'])
def get_goal_status(goal_id):
    """
    查询目标执行状态
    
    需要实现任务追踪功能
    """
    return jsonify({
        "goal_id": goal_id,
        "status": "not_implemented",
        "message": "Goal status tracking not yet implemented"
    })


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "service": "VectorBrain V4 Planner"
    })


@app.route('/', methods=['GET'])
def index():
    """API 首页"""
    return jsonify({
        "service": "VectorBrain V4 Planner API",
        "version": "1.0",
        "endpoints": {
            "POST /api/v1/goals": "Create new goal and generate tasks",
            "GET /api/v1/goals/<id>/status": "Get goal status",
            "GET /health": "Health check"
        }
    })


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 VectorBrain V4 Planner API")
    print("=" * 60)
    print("\n启动服务...")
    print("📍 监听地址：http://0.0.0.0:9100")
    print("\n可用端点:")
    print("  POST /api/v1/goals - 创建目标")
    print("  GET  /health        - 健康检查")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=9100, debug=False)
