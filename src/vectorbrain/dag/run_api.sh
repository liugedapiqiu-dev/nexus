#!/bin/bash
# VectorBrain API Server 启动脚本

cd "$(dirname "$0")"

echo "🚀 Starting VectorBrain API Server..."
python3 dag_api_server.py
