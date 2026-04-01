#!/usr/bin/env python3
"""VectorBrain Web Tools - usable adapters."""

from __future__ import annotations

from runtime.tools.registry import tool_registry, Tool
from typing import Dict, Any, List
from urllib.parse import urlencode, urlparse, parse_qs, unquote
from urllib.request import Request, urlopen
import asyncio
import html
import os
import re


def _http_get(url: str, *, timeout: int = 20) -> str:
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (VectorBrain MCP Orchestrator)",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    })
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="ignore")


def _strip_html(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _clean_ddg_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return unquote(qs["uddg"][0])
    return href


def _parse_duckduckgo_results(html_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    pattern = re.compile(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
    for href, title_html in pattern.findall(html_text):
        title = _strip_html(title_html)
        url = _clean_ddg_url(html.unescape(href))
        if not title or not url:
            continue
        if url.startswith("/"):
            continue
        results.append({"title": title, "url": url})
        if len(results) >= limit:
            break
    return results


async def web_search_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        query = input["query"]
        count = int(input.get("count", 5) or 5)
        print(f"[web_search] Searching for: {query}")

        lat = float(os.getenv("VECTORBRAIN_SIM_LATENCY", "0") or "0")
        if lat > 0:
            await asyncio.sleep(lat)

        url = "https://html.duckduckgo.com/html/?" + urlencode({"q": query})
        page = await asyncio.to_thread(_http_get, url, timeout=20)
        results = _parse_duckduckgo_results(page, limit=count)

        return {
            "success": True,
            "data": {"results": results, "query": query, "engine": "duckduckgo_html", "count": len(results)},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


def web_search_score(input: Dict[str, Any]) -> float:
    q = (input or {}).get("query", "") or ""
    if len(q.strip()) < 5:
        return 0.6
    return 0.92


web_search_tool = Tool(
    name="web_search",
    display_name="Web Search",
    description="Search the web via a real HTTP adapter (DuckDuckGo HTML endpoint)",
    capabilities=["research", "search"],
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {"type": "integer", "description": "Max result count", "default": 5},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "results": {"type": "array"},
            "query": {"type": "string"},
            "engine": {"type": "string"},
            "count": {"type": "integer"},
        },
    },
    handler=web_search_handler,
    score_fn=web_search_score,
    timeout=60,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(web_search_tool)


async def web_fetch_handler(input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        url = input["url"]
        max_chars = int(input.get("max_chars", 8000) or 8000)
        print(f"[web_fetch] Fetching: {url}")

        lat = float(os.getenv("VECTORBRAIN_SIM_LATENCY", "0") or "0")
        if lat > 0:
            await asyncio.sleep(lat)

        raw = await asyncio.to_thread(_http_get, url, timeout=20)
        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.I | re.S)
        title = _strip_html(title_match.group(1)) if title_match else ""
        content = _strip_html(raw)
        if max_chars > 0:
            content = content[:max_chars]

        return {
            "success": True,
            "data": {"content": content, "url": url, "title": title, "chars": len(content)},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


web_fetch_tool = Tool(
    name="web_fetch",
    display_name="Web Fetch",
    description="Fetch a URL and return extracted readable text via a real HTTP adapter",
    capabilities=["research", "fetch"],
    input_schema={
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "max_chars": {"type": "integer", "description": "Max readable chars to return", "default": 8000},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "url": {"type": "string"},
            "title": {"type": "string"},
            "chars": {"type": "integer"},
        },
    },
    handler=web_fetch_handler,
    timeout=60,
    version="2.0",
    allow_dry_run=True,
)

tool_registry.register(web_fetch_tool)
