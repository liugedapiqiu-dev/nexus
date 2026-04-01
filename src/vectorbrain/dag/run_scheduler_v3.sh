#!/bin/bash
# VectorBrain V3 Scheduler Wrapper

cd "$(dirname "$0")"

echo "=================================="
echo "🧠 VectorBrain V3 Scheduler"
echo "=================================="

# 启动 scheduler，自动启用 Experience Collector
python3 -c "
import sys
sys.path.insert(0, '$(cd ~ && pwd)/.vectorbrain')
sys.path.insert(0, '$(cd ~ && pwd)/.vectorbrain/dag')

# 导入并启用 Experience Collector
from experience.experience_collector import record_episode
print('✅ Experience Collector 已启用')

# 现在运行 scheduler
exec(open('$(cd ~ && pwd)/.vectorbrain/dag/dag_scheduler.py').read())
" "$@"
