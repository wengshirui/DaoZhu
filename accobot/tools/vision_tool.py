"""Vision tool — analyze images using LLM vision capability.

Toolset: "vision"
Uses the same LLM provider (OpenAI-compatible) with vision support to analyze
invoice images, receipts, bank statements, etc.

This is superior to PaddleOCR for financial documents because:
1. Understands context (knows what an invoice looks like)
2. Can extract structured data directly
3. No extra dependencies (uses the same API key)
4. Handles poor quality photos, rotated images, etc.

Inspired by Hermes Agent's vision_tools.py — simplified for AccoBot.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

from accobot.tools.registry import registry, tool_result, tool_error

logger = logging.getLogger(__name__)

# Supported image formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB


def _image_to_base64_url(image_path: Path) -> str:
    """Convert a local image file to a base64 data URL."""
    suffix = image_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")

    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def _get_vision_client():
    """Get an OpenAI client configured for vision."""
    from accobot.config import load_config, load_env, get_api_key
    load_env()
    config = load_config()

    api_key = get_api_key()
    if not api_key:
        return None, None

    from openai import OpenAI

    model_config = config.get("model", {})
    provider = model_config.get("provider", "deepseek")
    base_url = model_config.get("base_url", "")

    # Default base URLs by provider
    if not base_url:
        base_urls = {
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
        }
        base_url = base_urls.get(provider, "https://api.openai.com/v1")

    client = OpenAI(api_key=api_key, base_url=base_url)

    # Vision model selection
    # DeepSeek doesn't support vision yet, fall back to a vision-capable model
    model_name = model_config.get("model_name", "")
    vision_model = model_config.get("vision_model", "")

    if vision_model:
        model = vision_model
    elif "gpt-4" in model_name:
        model = model_name  # GPT-4o supports vision
    elif provider == "openai":
        model = "gpt-4o-mini"
    else:
        # Use whatever model is configured — many providers support vision
        model = model_name or "deepseek-chat"

    return client, model


def vision_analyze(args: dict, **kwargs) -> str:
    """Analyze an image using LLM vision.

    Can be used for:
    - Invoice OCR (extract code, number, amount, date, buyer/seller)
    - Receipt recognition
    - Bank statement reading
    - Any document image analysis
    """
    image_path_str = args.get("image_path", "") or args.get("file_path", "")
    prompt = args.get("prompt", "")

    if not image_path_str:
        return tool_error("请指定图片路径")

    image_path = Path(os.path.expanduser(image_path_str))
    if not image_path.exists():
        return tool_error(f"文件不存在：{image_path_str}")

    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        return tool_error(
            f"不支持的图片格式：{image_path.suffix}（支持：{', '.join(IMAGE_EXTENSIONS)}）"
        )

    file_size = image_path.stat().st_size
    if file_size > MAX_IMAGE_SIZE:
        return tool_error(f"图片太大：{file_size / 1024 / 1024:.1f} MB（上限 20 MB）")

    # Default prompt for financial documents
    if not prompt:
        prompt = (
            "请仔细分析这张图片。如果是发票，请提取以下信息：\n"
            "1. 发票代码\n"
            "2. 发票号码\n"
            "3. 开票日期\n"
            "4. 价税合计金额\n"
            "5. 税额\n"
            "6. 购买方名称\n"
            "7. 销售方名称\n"
            "8. 商品/服务名称\n\n"
            "如果不是发票，请描述图片内容并提取所有可见的文字和数字信息。\n"
            "请用 JSON 格式返回结构化数据。"
        )

    # Get vision client
    client, model = _get_vision_client()
    if not client:
        return tool_error("未配置 API Key，无法使用视觉分析功能")

    # Convert image to base64
    try:
        image_data_url = _image_to_base64_url(image_path)
    except Exception as e:
        return tool_error(f"读取图片失败：{e}")

    # Call vision API
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url},
                        },
                    ],
                }
            ],
            max_tokens=2000,
            temperature=0.1,
        )

        analysis = response.choices[0].message.content or ""

        return tool_result(
            success=True,
            analysis=analysis,
            model=model,
            image_size_kb=round(file_size / 1024, 1),
            message=f"📄 图片分析完成（{model}）：\n\n{analysis}",
        )

    except Exception as e:
        error_str = str(e).lower()

        # Detect vision not supported
        if any(hint in error_str for hint in (
            "does not support", "not support image", "multimodal",
            "image_url", "unrecognized",
        )):
            return tool_error(
                f"当前模型 {model} 不支持图片分析。\n"
                "建议：在设置中配置 vision_model 为支持视觉的模型（如 gpt-4o-mini）。\n"
                f"原始错误：{e}"
            )

        return tool_error(f"图片分析失败：{e}")


def check_vision_available() -> bool:
    """Check if vision is available (needs API key)."""
    from accobot.config import load_env, get_api_key
    load_env()
    return bool(get_api_key())


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="vision_analyze",
    toolset="vision",
    schema={
        "name": "vision_analyze",
        "description": "分析图片内容（发票识别、收据识别、银行回单识别等）。使用 AI 视觉能力提取图片中的文字和结构化信息。用户上传发票照片或说'识别这张发票'、'看看这张图片'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "图片文件的本地路径",
                },
                "prompt": {
                    "type": "string",
                    "description": "分析提示词（可选，默认为发票识别模式）",
                },
            },
            "required": ["image_path"],
        },
    },
    handler=vision_analyze,
    check_fn=check_vision_available,
    emoji="👁️",
)
