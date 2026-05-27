"""
火柴人剧场 — 核心生成器
1. generate_timeline(): 调用 LLM 将文本转为时间轴 JSON
2. render_html(): 将时间轴渲染为独立可播放的 HTML 文件
"""

import json
import re
from pathlib import Path

import httpx

TEMPLATE_PATH = Path(__file__).parent / "template.html"

# AI 导演 Prompt
DIRECTOR_PROMPT = """你是一个火柴人动画导演。用户输入一段文本（小说/散文/剧本），你输出时间轴 JSON。

## 规则

1. 识别所有角色，为每个分配 id（英文）和颜色
2. 按文本顺序生成事件，注意节奏：
   - 旁白/对话后至少等 3-4 秒
   - 角色入场后等 1.5 秒
   - 场景切换后等 2 秒
3. 角色说话 → dialogue，描述文字 → narr
4. 每句对话前给说话角色弹一个合适的 emoji
5. 场景变化 → label（格式："📍 地点名"）
6. 角色进出场 → enter/exit
7. 情绪变化 → arm 姿态 + emoji
8. 总时长 = 文本字数 / 7 秒（约每秒 7 字的阅读速度）
9. 同时在场角色不超过 5 个
10. t 的单位是毫秒！例如 3 秒 = 3000，不是 3

## action 类型

- enter: {t, action:"enter", id, x, y} — 入场（x:100-800, y:250-320）
- exit: {t, action:"exit", id} — 退场
- move: {t, action:"move", id, x, y?} — 移动
- arm: {t, action:"arm", id, arm} — 姿态(normal/up/hip/point/hug/wave)
- emoji: {t, action:"emoji", id, e} — 弹出 emoji
- dialogue: {t, action:"dialogue", who, text} — 对话
- narr: {t, action:"narr", text} — 旁白
- label: {t, action:"label", text} — 场景标签
- end: {t, action:"end"} — 结束

## 颜色参考

主角粉色#ec4899 温柔紫色#7c3aed 年幼金色#f59e0b
高贵红色#dc2626 冷静青色#0891b2 反面深红#991b1b

## emoji 参考

😊😄🥰😋🎉 开心 | 😤🤬😠 生气 | 😢😭🥺 悲伤
😱😵‍💫🤯 惊讶 | 🤔💭 思考 | 🚶👋🤝💪 动作
🍊🍲🧳📖🍰🍳☕ 物品

## 输出格式（纯 JSON，不要 markdown）

{"chars":{"id":{"color":"#hex","label":"名字","scale":1}},"timeline":[{"t":0,"action":"..."}]}"""


async def generate_timeline(text: str) -> dict:
    """调用 LLM 生成时间轴 JSON"""
    from daozhu.config_db import get_secret
    from daozhu.config import get_config_value

    api_key = get_secret("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 AI API Key")

    base_url = get_config_value("ai.base_url", "https://api.deepseek.com/v1")
    model = get_config_value("ai.model", "deepseek-chat")

    messages = [
        {"role": "system", "content": DIRECTOR_PROMPT},
        {"role": "user", "content": f"请将以下文本转为火柴人动画时间轴：\n\n{text[:3000]}"},
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "max_tokens": 4000, "temperature": 0.3},
        )

    if resp.status_code != 200:
        raise RuntimeError(f"API 错误: {resp.status_code}")

    content = resp.json()["choices"][0]["message"]["content"]
    return _parse_json(content)


def _parse_json(content: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # 提取 JSON 块
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise RuntimeError("AI 输出格式错误，无法解析 JSON")


def render_html(title: str, data: dict) -> str:
    """将时间轴数据渲染为独立 HTML 文件"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    chars_json = json.dumps(data.get("chars", {}), ensure_ascii=False)
    timeline_json = json.dumps(data.get("timeline", []), ensure_ascii=False)
    # 替换模板中的占位符
    html = template.replace("{{TITLE}}", title)
    html = html.replace("{{CHARS_JSON}}", chars_json)
    html = html.replace("{{TIMELINE_JSON}}", timeline_json)
    return html
