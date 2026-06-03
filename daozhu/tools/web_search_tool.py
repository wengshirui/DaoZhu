"""
岛主工具 — 网络搜索
多引擎降级: DuckDuckGo → Bing → 搜狗，确保搜索稳定可用
"""

import json
import re
from urllib.parse import quote_plus

import httpx

from .registry import registry


async def web_search_tool(query: str, max_results: int = 5) -> str:
    """搜索网络，返回结果摘要（多引擎自动降级）"""
    proxy = _get_proxy()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 按优先级尝试多个引擎
    engines = [
        ("duckduckgo", _search_duckduckgo),
        ("bing", _search_bing),
        ("sogou", _search_sogou),
    ]

    last_error = ""
    for engine_name, engine_fn in engines:
        try:
            async with httpx.AsyncClient(
                timeout=12, follow_redirects=True, proxy=proxy
            ) as client:
                results = await engine_fn(client, query, max_results, headers)
                if results:
                    return json.dumps(
                        {"query": query, "results": results, "source": engine_name},
                        ensure_ascii=False,
                    )
        except Exception as e:
            last_error = f"{engine_name}: {e}"
            continue

    return json.dumps(
        {"error": f"所有搜索引擎均失败: {last_error}", "query": query},
        ensure_ascii=False,
    )


async def _search_duckduckgo(
    client: httpx.AsyncClient, query: str, max_results: int, headers: dict
) -> list[dict]:
    """DuckDuckGo Lite（隐私友好，需代理或国际网络）"""
    resp = await client.post(
        "https://lite.duckduckgo.com/lite/",
        data={"q": query},
        headers=headers,
    )
    if resp.status_code not in (200, 202):
        return []

    html = resp.text
    results = []

    links = re.findall(
        r'<a rel="nofollow" href="([^"]+)" class=\'result-link\'>(.*?)</a>', html
    )
    snippets = re.findall(
        r'<td class="result-snippet">(.*?)</td>', html, re.DOTALL
    )

    for i, (href, title) in enumerate(links[:max_results]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()[:200]
        if title:
            results.append({"title": title, "url": href, "snippet": snippet})

    return results


async def _search_bing(
    client: httpx.AsyncClient, query: str, max_results: int, headers: dict
) -> list[dict]:
    """Bing 搜索（国内可直连，结果质量好）"""
    url = f"https://www.bing.com/search?q={quote_plus(query)}&setlang=zh-Hans"
    resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        return []

    html = resp.text
    results = []

    # Bing 搜索结果块
    blocks = re.findall(
        r'<li class="b_algo">(.*?)</li>', html, re.DOTALL
    )

    for block in blocks[:max_results]:
        # 提取标题和链接
        link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block)
        if not link_match:
            continue
        href = link_match.group(1)
        title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()

        # 提取摘要
        snippet = ""
        snippet_match = re.search(
            r'<p class="b_lineclamp[^"]*">(.*?)</p>', block, re.DOTALL
        )
        if not snippet_match:
            snippet_match = re.search(
                r'<div class="b_caption">(.*?)</div>', block, re.DOTALL
            )
        if snippet_match:
            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()[:200]

        if title and href.startswith("http"):
            results.append({"title": title, "url": href, "snippet": snippet})

    return results


async def _search_sogou(
    client: httpx.AsyncClient, query: str, max_results: int, headers: dict
) -> list[dict]:
    """搜狗搜索（国内备用）"""
    url = f"https://www.sogou.com/web?query={quote_plus(query)}"
    resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        return []

    html = resp.text
    results = []

    blocks = re.findall(
        r'<div class="vrwrap">(.*?)</div>\s*</div>', html, re.DOTALL
    )
    if not blocks:
        blocks = re.findall(
            r'<div class="rb">(.*?)</div>\s*</div>', html, re.DOTALL
        )

    for block in blocks[:max_results]:
        link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block)
        if not link_match:
            continue
        href = link_match.group(1)
        title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()

        snippet = ""
        snippet_match = re.search(
            r'<p class="str[^"]*">(.*?)</p>', block, re.DOTALL
        )
        if snippet_match:
            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()[:200]

        if title:
            results.append({"title": title, "url": href, "snippet": snippet})

    return results


# === fetch_url 工具：让 Agent 能调用任何公开 API ===

async def fetch_url_tool(url: str, method: str = "GET") -> str:
    """访问指定 URL 获取内容（支持公开 API 如 wttr.in）"""
    try:
        proxy = _get_proxy()
        headers = {"User-Agent": "curl/7.88.0", "Accept": "text/plain, application/json"}

        async with httpx.AsyncClient(timeout=10, follow_redirects=True, proxy=proxy) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, headers=headers)

            if resp.status_code != 200:
                return json.dumps({"error": f"HTTP {resp.status_code}", "url": url}, ensure_ascii=False)

            content = resp.text[:3000]
            return json.dumps({"url": url, "status": resp.status_code, "content": content}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e), "url": url}, ensure_ascii=False)


def _get_proxy():
    """检测本地代理"""
    import os
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not proxy:
        import socket
        try:
            s = socket.socket()
            s.settimeout(0.3)
            s.connect(("127.0.0.1", 7890))
            s.close()
            proxy = "http://127.0.0.1:7890"
        except (OSError, socket.timeout):
            proxy = None
    return proxy


# === 注册工具 ===

registry.register(
    name="web_search",
    description="搜索互联网获取信息（多引擎自动降级: DuckDuckGo → Bing → 搜狗）。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "最大结果数，默认5", "default": 5},
        },
        "required": ["query"],
    },
    handler=web_search_tool,
    category="web",
    emoji="🔍",
)

registry.register(
    name="fetch_url",
    description="访问指定 URL 获取内容。可用于调用公开 API（如 wttr.in 天气、GitHub API 等）。例如查天气：fetch_url('https://wttr.in/南京?format=3')",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "要访问的 URL"},
            "method": {"type": "string", "description": "HTTP 方法，默认 GET", "default": "GET"},
        },
        "required": ["url"],
    },
    handler=fetch_url_tool,
    category="web",
    emoji="🌐",
)
