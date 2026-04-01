#!/bin/bash
# Thin startup hook: delegate all startup logic to the single Ahao bootstrap.

mkdir -p ~/.openclaw/logs

echo "[$(date '+%Y-%m-%d %H:%M:%S')] on-start begin" >> ~/.openclaw/logs/startup.log
python3 ~/.vectorbrain/connector/ahao_bootstrap.py >> ~/.openclaw/logs/startup.log 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] on-start end" >> ~/.openclaw/logs/startup.log
