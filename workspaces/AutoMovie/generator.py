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

1. 识别所有角色，为每个分配 id（中文拼音，如 'fuqin'、'wo'）和颜色
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
11. 如果输入是中文文本，所有输出（label/narr/dialogue）必须是中文，不要出现英文
12. 场景标签格式："📍 地点名"，用中文地名

## 可用 SVG 装饰素材（assets/ 目录）

场景装饰可引用以下素材（通过 decor action）：
- nature/sky: sun, moon, cloud, star, sunrise, sunset, rainbow, mist
- nature/trees: tree-pine, tree-deciduous, trees, flower, leaf, plant, shrub, tree-bare
- nature/water: droplets, ripple
- nature/mountains: mountain, mountain-snow
- buildings: house, building, castle, church, warehouse, fence, landmark, tower, pillars, barrier
- props/furniture: bed, bed-single, sofa, armchair, lamp, lamp-desk
- props/doors: door-open, door-closed, door, door-enter, door-exit
- props/items: book, book-open, cup, clock, key, phone, tv, laptop, umbrella, orange, suitcase
- animals: cat, dog, bird, fish, rabbit, horse, deer, butterfly
- effects: heart, sparkles, flame, music, idea, tear, rain, snow, wind
- vehicles: car, bike, bus, train, ship, plane

## action 类型

- enter: {t, action:"enter", id, x, y} — 入场（x:100-800, y:250-320）
- exit: {t, action:"exit", id} — 退场
- move: {t, action:"move", id, x, y?} — 移动（重要！每3-4个事件至少一次move）
- arm: {t, action:"arm", id, arm} — 姿态(normal/up/hip/point/hug/wave)
- emoji: {t, action:"emoji", id, e} — 弹出 emoji
- dialogue: {t, action:"dialogue", who, text} — 对话（who必须用中文角色名如"父亲"，不要用id！）
- narr: {t, action:"narr", text} — 旁白
- label: {t, action:"label", text} — 场景标签
- decor: {t, action:"decor", path, x, y, size?, color?} — 添加场景装饰
- decor_clear: {t, action:"decor_clear"} — 切换场景时清除所有装饰
- end: {t, action:"end"} — 结束

## ⚠️ 关键规则（必须遵守）

1. dialogue的who字段必须用中文角色名！正确："父亲" 错误："fuqin"
2. 角色不能一直站着不动！对话前后要有move动作（走近、走远、转身）
3. 例：父亲去买橘子 → move{id:"fuqin",x:700} → 回来 → move{id:"fuqin",x:400}
4. arm姿态配合情绪：生气=hip 安慰=hug 指示=point 告别=wave 努力=up

## 装饰使用规则

- 每个场景在 label 后立即用 decor 添加该场景的典型装饰
- 场景切换前先放一个 decor_clear 清除旧场景装饰
- 室外场景多用 nature（云、太阳、树、山），室内多用 props（灯、书、杯）
- 装饰坐标建议：天空区 (50-850, 20-100)，地面区 (50-850, 380-440)，中间区 (50-850, 150-350)
- 装饰颜色建议：暖色 #c49a6c、冷色 #6b7280、亮色 #f59e0b（与背景协调）

## 颜色参考

主角粉色#ec4899 温柔紫色#7c3aed 年幼金色#f59e0b
高贵红色#dc2626 冷静青色#0891b2 反面深红#991b1b

## emoji 参考

😊😄🥰😋🎉 开心 | 😤🤬😠 生气 | 😢😭🥺 悲伤
😱😵‍💫🤯 惊讶 | 🤔💭 思考 | 🚶👋🤝💪 动作
🍊🍲🧳📖🍰🍳☕ 物品

## 输出格式（纯 JSON，不要 markdown）

{"chars":{"id":{"color":"#hex","label":"名字","scale":1}},"timeline":[{"t":0,"action":"..."}]}"""


async def generate_timeline(text: str, max_retries: int = 3) -> dict:
    """调用 LLM 生成时间轴 JSON（含重试和容错）"""
    from daozhu.config_db import get_secret
    from daozhu.config import get_config_value

    api_key = get_secret("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 AI API Key")

    base_url = get_config_value("ai.base_url", "https://api.deepseek.com/v1")
    model = get_config_value("ai.model", "deepseek-chat")

    # 截短输入避免输出被截断
    truncated_text = text[:2000]

    messages = [
        {"role": "system", "content": DIRECTOR_PROMPT},
        {"role": "user", "content": f"请将以下文本转为火柴人动画时间轴：\n\n{truncated_text}"},
    ]

    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": 8000,
                        "temperature": 0.3,
                    },
                )

            if resp.status_code != 200:
                last_error = f"API 错误: {resp.status_code}"
                continue

            content = resp.json()["choices"][0]["message"]["content"]
            return _parse_json(content)

        except RuntimeError as e:
            last_error = str(e)
            # JSON 解析失败 → 重试时提醒 LLM
            if attempt < max_retries - 1:
                messages.append({"role": "assistant", "content": content if 'content' in dir() else ""})
                messages.append({"role": "user", "content": "你的输出不是有效的 JSON。请只输出纯 JSON，不要 markdown 代码块，不要任何解释文字。"})
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(f"AI 生成失败（重试 {max_retries} 次）: {last_error}")


def _parse_json(content: str) -> dict:
    """从 LLM 输出中提取 JSON（含 markdown 代码块和截断修复）"""
    if not content:
        raise RuntimeError("AI 输出为空")

    # 去除 markdown 代码块
    text = content.strip()
    if text.startswith("```"):
        # 去掉 ```json 或 ``` 开头
        text = re.sub(r'^```[a-zA-Z]*\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 提取最外层 JSON 对象
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        json_str = match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复截断的 JSON（补齐括号）
            repaired = _repair_truncated_json(json_str)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

    raise RuntimeError("AI 输出格式错误，无法解析 JSON")


def _repair_truncated_json(text: str) -> str:
    """尝试修复被截断的 JSON（补齐缺失的括号）"""
    # 计算未闭合的括号
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')

    if open_braces <= 0 and open_brackets <= 0:
        return text  # 不需要修复

    # 移除末尾不完整的元素（可能截断在字符串中间）
    # 找最后一个完整的 JSON 值结尾
    text = re.sub(r',\s*"[^"]*$', '', text)  # 去掉截断的 key
    text = re.sub(r',\s*$', '', text)  # 去掉尾部逗号

    # 补齐括号
    text += ']' * max(0, open_brackets)
    text += '}' * max(0, open_braces)

    return text


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
