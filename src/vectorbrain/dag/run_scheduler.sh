#!/bin/bash
# VectorBrain DAG Scheduler 启动脚本

cd "$(dirname "$0")"

echo "🚀 Starting VectorBrain DAG Scheduler..."
python3 dag_scheduler.py
