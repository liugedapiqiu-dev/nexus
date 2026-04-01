#!/usr/bin/env python3
"""
🛡️ [YOUR_AI_NAME]智能模型路由代理 (Nexus Smart Proxy)
实现无缝断网降级：云端超时自动切换本地 Ollama

🆕 v1.1 (2026-03-13): 添加 Token 使用日志（非阻塞异步记录）

状态标记（2026-03-19）：
- 当前归类：旧旁路 / 非主链
- 当前判断：不是稳定主模型链路的主判据，更偏实验/备用代理
- 排查原则：不要优先用它判断当前主框架是否健康
- 参考清单：~/.vectorbrain/SCRIPT_REGISTRY.md
"""

import logging
import threading
import time
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - 🛡️ SmartProxy - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nexus Smart Proxy")

# --- 配置区 ---
# 云端 API 配置
CLOUD_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
CLOUD_MODEL = "qwen3.5-plus"

# 本地 Ollama 配置
LOCAL_API_URL = "http://127.0.0.1:11434/v1/chat/completions"
LOCAL_MODEL = "qwen2.5:14b"

# 断路器超时设置
CLOUD_TIMEOUT = 3.0      # 云端 3 秒无响应即判定断网/超时
LOCAL_TIMEOUT = 120.0    # 本地推理给予充分时间

# 🆕 Token 日志配置
TOKEN_LOG_ENABLED = True
TOKEN_LOG_SCRIPT = Path.home() / '.vectorbrain' / 'connector' / 'token_logger.py'


def _log_token_usage(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    session_key: str = None,
    duration_ms: int = None,
    request_id: str = None
):
    """
    🆕 异步记录 Token 使用（后台线程，非阻塞）
    
    安全设计：
    1. 后台线程运行，不阻塞 API 响应
    2. 异常捕获，日志失败不影响主流程
    3. 静默失败，只记录到 SmartProxy 日志
    """
    if not TOKEN_LOG_ENABLED:
        return
    
    def _write_log():
        try:
            import subprocess
            subprocess.run(
                ['python3', str(TOKEN_LOG_SCRIPT), 'log', model, provider, 
                 str(input_tokens), str(output_tokens), session_key or ''],
                capture_output=True,
                timeout=5
            )
            logger.debug(f"📊 Token 日志成功：{model} - 输入{input_tokens}/输出{output_tokens}")
        except Exception as e:
            # ⚠️ 静默失败 - 日志失败不影响 API 调用
            logger.debug(f"⚠️ Token 日志失败（已忽略）: {e}")
    
    # 启动后台线程（daemon=True 确保不会阻止进程退出）
    thread = threading.Thread(target=_write_log, daemon=True)
    thread.start()


def _extract_tokens_from_response(response_data: dict, provider: str) -> dict:
    """
    🆕 从 API 响应中提取 token 数（兼容不同提供商格式）
    
    Args:
        response_data: API 响应 JSON
        provider: "dashscope" 或 "ollama"
    
    Returns:
        {"input_tokens": int, "output_tokens": int}
    """
    try:
        if provider == "dashscope":
            # DashScope 格式：usage.input_tokens / usage.output_tokens
            usage = response_data.get("usage", {})
            return {
                "input_tokens": usage.get("input_tokens", usage.get("prompt_tokens", 0)),
                "output_tokens": usage.get("output_tokens", usage.get("completion_tokens", 0))
            }
        elif provider == "ollama":
            # Ollama 格式：prompt_eval_count / eval_count
            return {
                "input_tokens": response_data.get("prompt_eval_count", 0),
                "output_tokens": response_data.get("eval_count", 0)
            }
        else:
            logger.warning(f"⚠️ 未知提供商：{provider}，无法提取 token")
            return {"input_tokens": 0, "output_tokens": 0}
    except Exception as e:
        logger.debug(f"⚠️ Token 提取失败（已忽略）: {e}")
        return {"input_tokens": 0, "output_tokens": 0}


def _extract_session_key(request: Request, payload: dict) -> str:
    """
    🆕 从请求中提取会话标识
    
    优先级：X-Session-Key 头 > payload.session_key > 默认值
    """
    # 1. 尝试从 HTTP 头获取
    session_key = request.headers.get("X-Session-Key", "")
    if session_key:
        return session_key
    
    # 2. 尝试从 payload 获取
    if payload.get("session_key"):
        return str(payload["session_key"])
    
    # 3. 默认值（匿名会话）
    return "smart_proxy:anonymous"


@app.post("/v1/chat/completions")
async def proxy_chat(request: Request):
    """
    代理聊天请求
    优先使用云端，超时自动降级到本地
    """
    try:
        # 获取请求数据
        payload = await request.json()
        auth_header = request.headers.get("Authorization", "")
        
        # ========== 1. 尝试请求云端模型 ==========
        cloud_payload = payload.copy()
        cloud_payload["model"] = CLOUD_MODEL
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"🌐 尝试连接云端 [{CLOUD_MODEL}]...")
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CLOUD_API_URL,
                    json=cloud_payload,
                    headers=headers,
                    timeout=CLOUD_TIMEOUT
                )
                response.raise_for_status()
                logger.info("✅ 云端请求成功！")
                
                # 🆕 记录 Token 使用（异步非阻塞）
                try:
                    response_data = response.json()
                    duration_ms = int((time.time() - start_time) * 1000)
                    tokens = _extract_tokens_from_response(response_data, "dashscope")
                    session_key = _extract_session_key(request, payload)
                    request_id = response_data.get("request_id", "")
                    
                    _log_token_usage(
                        model=CLOUD_MODEL,
                        provider="dashscope",
                        input_tokens=tokens["input_tokens"],
                        output_tokens=tokens["output_tokens"],
                        session_key=session_key,
                        duration_ms=duration_ms,
                        request_id=request_id
                    )
                except Exception as log_e:
                    # ⚠️ 日志失败不影响主流程
                    logger.debug(f"⚠️ Token 日志失败（已忽略）: {log_e}")
                
                return JSONResponse(
                    content=response_data,
                    status_code=response.status_code
                )
        
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"⚠️ 云端无响应 (超时/断网): {e}。触发降级机制...")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ 云端返回错误状态码：{e.response.status_code}。触发降级机制...")
        
        # ========== 2. 断路器打开，降级到本地 Ollama ==========
        local_payload = payload.copy()
        local_payload["model"] = LOCAL_MODEL
        
        try:
            logger.info(f"🏠 启动本地备用模型 [{LOCAL_MODEL}]...")
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                # Ollama 本地调用通常不需要强校验 Auth
                response = await client.post(
                    LOCAL_API_URL,
                    json=local_payload,
                    timeout=LOCAL_TIMEOUT
                )
                response.raise_for_status()
                logger.info("✅ 本地模型接管成功！")
                
                # 🆕 记录 Token 使用（异步非阻塞）
                try:
                    response_data = response.json()
                    duration_ms = int((time.time() - start_time) * 1000)
                    tokens = _extract_tokens_from_response(response_data, "ollama")
                    session_key = _extract_session_key(request, payload)
                    
                    _log_token_usage(
                        model=LOCAL_MODEL,
                        provider="ollama",
                        input_tokens=tokens["input_tokens"],
                        output_tokens=tokens["output_tokens"],
                        session_key=session_key,
                        duration_ms=duration_ms
                    )
                except Exception as log_e:
                    # ⚠️ 日志失败不影响主流程
                    logger.debug(f"⚠️ Token 日志失败（已忽略）: {log_e}")
                
                return JSONResponse(
                    content=response_data,
                    status_code=response.status_code
                )
        
        except Exception as e:
            logger.critical(f"🚨 本地模型也失败了：{e}")
            raise HTTPException(
                status_code=500,
                detail="Fatal: Both Cloud and Local models failed."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 未知错误：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "Nexus Smart Proxy",
        "cloud_model": CLOUD_MODEL,
        "local_model": LOCAL_MODEL
    }


@app.get("/")
async def root():
    """根路径信息"""
    return {
        "service": "Nexus Smart Proxy",
        "version": "1.0.0",
        "description": "智能模型路由代理 - 云端超时自动降级本地",
        "endpoints": {
            "chat": "POST /v1/chat/completions",
            "health": "GET /health"
        }
    }


if __name__ == "__main__":
    # 监听本地 8000 端口
    logger.info("=" * 60)
    logger.info("🛡️ [YOUR_AI_NAME]智能模型路由代理启动")
    logger.info("=" * 60)
    logger.info(f"🌐 监听地址：http://127.0.0.1:8000")
    logger.info(f"☁️ 云端模型：{CLOUD_MODEL}")
    logger.info(f"🏠 本地模型：{LOCAL_MODEL}")
    logger.info(f"⏱️ 超时阈值：{CLOUD_TIMEOUT}秒")
    logger.info("=" * 60)
    logger.info("🚀 启动中...")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
