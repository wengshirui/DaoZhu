"""OCR tool — extract text from invoice images.

Toolset: "voucher"
Supports: PaddleOCR (local, free) or LLM vision (fallback).
"""

import json
import logging
from pathlib import Path
from accobot.tools.registry import registry, tool_result, tool_error

logger = logging.getLogger(__name__)


def _try_paddleocr(image_path: str) -> dict:
    """Attempt OCR using PaddleOCR (local, free)."""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return {"error": "PaddleOCR 未安装。安装命令：pip install paddleocr paddlepaddle"}

    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    result = ocr.ocr(image_path, cls=True)

    if not result or not result[0]:
        return {"error": "未识别到文字内容"}

    lines = []
    for line_info in result[0]:
        text = line_info[1][0]
        confidence = line_info[1][1]
        lines.append({"text": text, "confidence": confidence})

    return {"lines": lines, "full_text": "\n".join(l["text"] for l in lines)}


def _extract_invoice_fields(ocr_text: str) -> dict:
    """Extract structured invoice fields from OCR text using heuristics."""
    import re

    fields = {}

    # Invoice code (发票代码): 10-12 digits
    code_match = re.search(r'发票代码[：:\s]*(\d{10,12})', ocr_text)
    if code_match:
        fields["invoice_code"] = code_match.group(1)

    # Invoice number (发票号码): 8 digits
    num_match = re.search(r'发票号码[：:\s]*(\d{8})', ocr_text)
    if num_match:
        fields["invoice_number"] = num_match.group(1)

    # Date (开票日期)
    date_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', ocr_text)
    if date_match:
        y, m, d = date_match.groups()
        fields["date"] = f"{y}-{int(m):02d}-{int(d):02d}"

    # Amount (金额/价税合计)
    amount_patterns = [
        r'价税合计[（(]大写[）)][：:\s]*.*?[￥¥]\s*([\d,]+\.?\d*)',
        r'价税合计[：:\s]*[￥¥]\s*([\d,]+\.?\d*)',
        r'合\s*计[：:\s]*[￥¥]?\s*([\d,]+\.?\d*)',
        r'金\s*额[：:\s]*[￥¥]?\s*([\d,]+\.?\d*)',
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, ocr_text)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                fields["amount"] = float(amount_str)
            except ValueError:
                pass
            break

    # Tax amount (税额)
    tax_match = re.search(r'税\s*额[：:\s]*[￥¥]?\s*([\d,]+\.?\d*)', ocr_text)
    if tax_match:
        try:
            fields["tax_amount"] = float(tax_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Buyer (购买方/购方名称)
    buyer_match = re.search(r'(?:购买方|购方)[名称]*[：:\s]*(.+?)(?:\n|$)', ocr_text)
    if buyer_match:
        fields["buyer"] = buyer_match.group(1).strip()

    # Seller (销售方/销方名称)
    seller_match = re.search(r'(?:销售方|销方)[名称]*[：:\s]*(.+?)(?:\n|$)', ocr_text)
    if seller_match:
        fields["seller"] = seller_match.group(1).strip()

    return fields


def ocr_invoice(args: dict, **kwargs) -> str:
    """OCR an invoice image and extract key fields."""
    file_path = args.get("file_path", "")

    if not file_path:
        return tool_error("请指定发票图片路径")

    path = Path(file_path)
    if not path.exists():
        return tool_error(f"文件不存在：{file_path}")

    # Check file type
    suffix = path.suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".bmp", ".pdf"):
        return tool_error(f"不支持的文件格式：{suffix}（支持 jpg/png/pdf）")

    # Strategy 1: Use LLM vision (preferred — better accuracy, understands context)
    try:
        from accobot.tools.vision_tool import vision_analyze
        vision_result = vision_analyze({"image_path": file_path})
        result_data = json.loads(vision_result)
        if result_data.get("success"):
            return vision_result
    except Exception as e:
        logger.debug("Vision fallback failed: %s", e)

    # Strategy 2: Fall back to PaddleOCR (local, free, no API needed)
    ocr_result = _try_paddleocr(str(path))

    if "error" in ocr_result:
        return tool_error(
            f"OCR 识别失败：{ocr_result['error']}\n"
            f"建议：配置支持视觉的模型（如 gpt-4o-mini）可获得更好的识别效果。"
        )

    full_text = ocr_result["full_text"]
    fields = _extract_invoice_fields(full_text)

    # Build response
    lines = ["📄 发票识别结果（PaddleOCR）："]
    if fields.get("invoice_code"):
        lines.append(f"  发票代码：{fields['invoice_code']}")
    if fields.get("invoice_number"):
        lines.append(f"  发票号码：{fields['invoice_number']}")
    if fields.get("date"):
        lines.append(f"  开票日期：{fields['date']}")
    if fields.get("amount"):
        lines.append(f"  金额：{fields['amount']:,.2f} 元")
    if fields.get("tax_amount"):
        lines.append(f"  税额：{fields['tax_amount']:,.2f} 元")
    if fields.get("buyer"):
        lines.append(f"  购买方：{fields['buyer']}")
    if fields.get("seller"):
        lines.append(f"  销售方：{fields['seller']}")

    if not fields:
        lines.append("  （未能提取结构化字段，原始文字如下）")
        lines.append(f"  {full_text[:200]}")

    return tool_result(
        success=True,
        fields=fields,
        full_text=full_text[:500],
        line_count=len(ocr_result.get("lines", [])),
        message="\n".join(lines),
    )


def check_ocr_available() -> bool:
    """Check if OCR is available (vision API or PaddleOCR)."""
    # Always available — vision_analyze uses the same API key as the agent,
    # PaddleOCR is a bonus fallback
    from accobot.config import load_env, get_api_key
    load_env()
    if get_api_key():
        return True
    try:
        import paddleocr  # noqa: F401
        return True
    except ImportError:
        return False


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="ocr_invoice",
    toolset="voucher",
    schema={
        "name": "ocr_invoice",
        "description": "识别发票图片，提取发票代码、号码、日期、金额、购销方等信息。用户上传发票照片或说'识别这张发票'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "发票图片文件的本地路径",
                },
            },
            "required": ["file_path"],
        },
    },
    handler=ocr_invoice,
    check_fn=check_ocr_available,
    emoji="🔍",
)
