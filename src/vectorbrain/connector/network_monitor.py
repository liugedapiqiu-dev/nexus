#!/usr/bin/env python3
"""
网络监控 + OpenClaw 模型自动切换脚本
- 每 10 秒检测一次网络
- 连续 6 次失败（60 秒）判定为断网，切换到本地模型
- 网络恢复后切换回云端模型
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 配置
CHECK_INTERVAL = 10  # 检测间隔（秒）
FAIL_THRESHOLD = 6   # 连续失败次数阈值（60 秒）
STATE_FILE = Path.home() / ".vectorbrain" / "state" / "network_state.json"
CONFIG_FILE = Path.home() / ".openclaw" / "config.json"
LOG_FILE = Path.home() / ".vectorbrain" / "connector" / "network_monitor.log"

# 模型配置
CLOUD_MODEL = "custom-coding-dashscope-aliyuncs-com/qwen3.5-plus"
LOCAL_MODEL = "ollama/qwen2.5:14b"

# 检测目标（阿里云 DashScope API）
CHECK_URLS = [
    "https://dashscope.aliyuncs.com",
    "https://www.baidu.com",
    "8.8.8.8"
]

# 飞书用户 ID
FEISHU_USER_ID = "[YOUR_USER_ID]"

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    # 写入日志文件
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception as e:
        print(f"写入日志失败：{e}")

def check_network():
    """检测网络连通性"""
    for url in CHECK_URLS:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", url],
                capture_output=True,
                timeout=3
            )
            if result.returncode == 0:
                return True
        except Exception:
            continue
    return False

def load_state():
    """加载网络状态"""
    default_state = {
        "is_online": True,
        "consecutive_failures": 0,
        "current_model": CLOUD_MODEL,
        "last_switch_time": None,
        "last_check_time": None
    }
    
    if not STATE_FILE.exists():
        return default_state
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            for key, value in default_state.items():
                if key not in state:
                    state[key] = value
            return state
    except Exception as e:
        log(f"读取状态失败：{e}")
        return default_state

def save_state(state):
    """保存网络状态"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"保存状态失败：{e}")

def load_config():
    """加载 OpenClaw 配置"""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    """保存 OpenClaw 配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def send_notification(message):
    """发送飞书通知（已禁用）"""
    # 已禁用飞书通知 - 断网时发不出去
    log(f"通知已禁用：{message[:50]}...")
    return True
    
    # 原代码已注释
    # try:
    #     subprocess.run(
    #         ["openclaw", "message", "send", "--channel", "feishu", 
    #          "-t", f"user:{FEISHU_USER_ID}", "-m", message],
    #         capture_output=True,
    #         timeout=10
    #     )
    #     log(f"通知已发送：{message[:50]}...")
    # except Exception as e:
    #     log(f"发送通知失败：{e}")
    # return False

def restart_gateway():
    """重启 OpenClaw Gateway"""
    try:
        log("正在重启 Gateway...")
        result = subprocess.run(
            ["openclaw", "gateway", "restart"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            log("Gateway 重启成功")
            return True
        else:
            log(f"Gateway 重启失败：{result.stderr}")
            return False
    except Exception as e:
        log(f"重启 Gateway 异常：{e}")
        return False

def switch_model(new_model):
    """切换 OpenClaw 模型"""
    try:
        config = load_config()
        old_model = config.get("model", CLOUD_MODEL)
        
        if old_model == new_model:
            log(f"模型已经是 {new_model}，无需切换")
            return False
        
        config["model"] = new_model
        config["__fallback__"] = {
            "enabled": True,
            "cloud_model": CLOUD_MODEL,
            "local_model": LOCAL_MODEL,
            "auto_switch": True,
            "last_switch_reason": "network_change"
        }
        
        save_config(config)
        log(f"配置已更新：{old_model} → {new_model}")
        
        if restart_gateway():
            send_notification(f"🧠 模型已切换：{'☁️ 云端' if 'qwen3.5' in new_model else '🏠 本地'} ({new_model})")
            return True
        return False
    except Exception as e:
        log(f"切换模型失败：{e}")
        return False

def main():
    """主循环"""
    log("=" * 50)
    log("网络监控启动")
    log(f"检测间隔：{CHECK_INTERVAL}秒，失败阈值：{FAIL_THRESHOLD}次")
    log(f"云端模型：{CLOUD_MODEL}")
    log(f"本地模型：{LOCAL_MODEL}")
    log("=" * 50)
    
    state = load_state()
    
    while True:
        try:
            # 检测网络
            is_online = check_network()
            state["last_check_time"] = datetime.now().isoformat()
            
            if is_online:
                # 网络正常
                if state["consecutive_failures"] > 0:
                    log(f"网络恢复（失败计数：{state['consecutive_failures']} → 0）")
                state["consecutive_failures"] = 0
                
                # 如果当前是离线状态，切换回云端模型
                if not state["is_online"]:
                    log("网络已恢复，准备切换回云端模型")
                    state["is_online"] = True
                    state["last_switch_time"] = datetime.now().isoformat()
                    save_state(state)
                    switch_model(CLOUD_MODEL)
            
            else:
                # 网络失败
                state["consecutive_failures"] += 1
                log(f"网络检测失败（连续 {state['consecutive_failures']}/{FAIL_THRESHOLD} 次）")
                
                # 达到阈值，切换到本地模型
                if state["consecutive_failures"] >= FAIL_THRESHOLD and state["is_online"]:
                    log("⚠️ 达到失败阈值，判定为断网，切换到本地模型")
                    state["is_online"] = False
                    state["last_switch_time"] = datetime.now().isoformat()
                    save_state(state)
                    switch_model(LOCAL_MODEL)
            
            save_state(state)
            
        except KeyboardInterrupt:
            log("监控被用户中断")
            sys.exit(0)
        except Exception as e:
            log(f"检测异常：{e}")
        
        # 等待下一次检测
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
