"""
火柴人剧场 — Pexels 视频素材服务（#083 中级模式 - 重写）
参考: MoneyPrinterTurbo app/services/material.py

关键改进（对比 v1）：
1. 每帧用不同英文关键词搜索（由导演 LLM 生成）→ 视频多样性
2. URL hash 缓存（真正生效）→ 同 URL 只下载一次
3. 去重 → 不同帧不会拿到同一个视频
4. 分辨率+时长筛选 → 只取符合要求的素材

失败时返回 None → 降级到 SVG 背景（AC9）。
"""

import hashlib
import logging
import random
import threading
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output" / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PEXELS_API_URL = "https://api.pexels.com/videos/search"

# 已使用的视频 URL（会话级去重）
_used_urls: set[str] = set()
_used_lock = threading.Lock()

# Key 轮换
_key_counter = 0
_key_lock = threading.Lock()


def reset_session():
    """新任务开始时重置去重集合。"""
    global _used_urls
    with _used_lock:
        _used_urls = set()


def _get_api_key(keys: list[str]) -> str:
    global _key_counter
    if not keys:
        return ""
    with _key_lock:
        _key_counter += 1
        return keys[_key_counter % len(keys)]


async def search_and_download(
    keyword: str,
    scene_index: int,
    api_keys: list[str],
    orientation: str = "landscape",
    min_duration: int = 5,
    target_width: int = 1920,
    target_height: int = 1080,
) -> Optional[str]:
    """
    搜索并下载 Pexels 视频片段（参考 MoneyPrinterTurbo）。

    关键设计：
    - keyword 必须是英文（Pexels 英文搜索效果远好于中文）
    - 结果去重（同一视频不会被不同帧重复使用）
    - URL hash 缓存（已下载的文件不重复下载）

    Args:
        keyword: 英文搜索关键词（由导演 LLM 生成）
        scene_index: 场景序号（仅用于日志）
        api_keys: Pexels API Key 列表
        orientation: landscape / portrait / square
        min_duration: 最短时长（秒）
        target_width/height: 目标分辨率

    Returns:
        本地视频文件路径，失败返回 None
    """
    if not api_keys:
        logger.warning("[Pexels] 无 API Key")
        return None

    if not keyword or not keyword.strip():
        keyword = "nature scenery"

    api_key = _get_api_key(api_keys)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                PEXELS_API_URL,
                params={
                    "query": keyword.strip(),
                    "per_page": 15,
                    "orientation": orientation,
                },
                headers={
                    "Authorization": api_key,
                    "User-Agent": "DaoZhu-AutoMovie/1.0",
                },
            )

            if resp.status_code != 200:
                logger.warning(f"[Pexels] 搜索失败 HTTP {resp.status_code}")
                return None

            data = resp.json()
            videos = data.get("videos", [])
            if not videos:
                logger.info(f"[Pexels] '{keyword}' 无结果")
                return None

            # 筛选 + 去重
            video_url = _select_best_video(
                videos, min_duration, target_width, target_height
            )
            if not video_url:
                logger.info(f"[Pexels] '{keyword}' 无匹配视频（已去重后）")
                return None

            # 下载（URL hash 缓存）
            local_path = await _download_video(client, video_url)
            if local_path:
                logger.info(
                    f"[Pexels] 帧{scene_index} '{keyword}' → {Path(local_path).name}"
                )
            return local_path

    except httpx.TimeoutException:
        logger.warning(f"[Pexels] '{keyword}' 超时")
        return None
    except Exception as e:
        logger.warning(f"[Pexels] '{keyword}' 失败: {e}")
        return None


def _select_best_video(
    videos: list[dict],
    min_duration: int,
    target_width: int,
    target_height: int,
) -> Optional[str]:
    """
    从搜索结果中选择最佳视频 URL。
    参考 MoneyPrinterTurbo: 按分辨率匹配 + 时长过滤 + 去重。
    """
    candidates = []

    for v in videos:
        duration = v.get("duration", 0)
        if duration < min_duration:
            continue

        video_files = v.get("video_files", [])
        for vf in video_files:
            w = int(vf.get("width", 0))
            h = int(vf.get("height", 0))
            url = vf.get("link", "")

            if not url:
                continue

            # 分辨率筛选：至少达到目标的 80%
            if w >= target_width * 0.8 and h >= target_height * 0.8:
                # 去重：同一 URL 不重复使用
                url_clean = url.split("?")[0]
                with _used_lock:
                    if url_clean in _used_urls:
                        continue

                candidates.append({
                    "url": url,
                    "url_clean": url_clean,
                    "width": w,
                    "height": h,
                    "duration": duration,
                })
                break  # 每个视频只取一个最佳分辨率

    if not candidates:
        # 退而求其次：取任何可用视频的最大分辨率文件
        for v in videos:
            if v.get("duration", 0) < min_duration:
                continue
            files = v.get("video_files", [])
            if files:
                best = max(files, key=lambda f: int(f.get("width", 0)))
                url = best.get("link", "")
                url_clean = url.split("?")[0]
                with _used_lock:
                    if url_clean not in _used_urls:
                        candidates.append({
                            "url": url,
                            "url_clean": url_clean,
                            "width": int(best.get("width", 0)),
                            "height": int(best.get("height", 0)),
                            "duration": v["duration"],
                        })
                        break

    if not candidates:
        return None

    # 随机选一个（增加多样性），并标记为已用
    selected = random.choice(candidates)
    with _used_lock:
        _used_urls.add(selected["url_clean"])

    return selected["url"]


async def _download_video(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """下载视频到本地（URL hash 缓存，同 URL 只下载一次）。"""
    url_clean = url.split("?")[0]
    url_hash = hashlib.md5(url_clean.encode()).hexdigest()[:12]
    filename = f"pexels_{url_hash}.mp4"
    filepath = OUTPUT_DIR / filename

    # 已缓存则直接返回
    if filepath.exists() and filepath.stat().st_size > 10000:
        return str(filepath)

    # 下载
    try:
        resp = await client.get(url, timeout=60, follow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10000:
            filepath.write_bytes(resp.content)
            logger.info(f"[Pexels] 下载: {filename} ({len(resp.content)//1024}KB)")
            return str(filepath)
        else:
            logger.warning(f"[Pexels] 下载异常: HTTP {resp.status_code}")
            return None
    except Exception as e:
        logger.warning(f"[Pexels] 下载失败: {e}")
        return None
