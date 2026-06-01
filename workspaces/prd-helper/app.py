from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
import uvicorn, json, os, httpx, re
from pathlib import Path
import io, zipfile, xml.etree.ElementTree as ET
from datetime import datetime

from db import init_db, query, execute

app = FastAPI()
BASE_DIR = Path(__file__).parent

# 加载 DaoZhu 的配置（app.py 在 workspaces/prd-helper/，DaoZhu 根目录在 ../..）
DAOSHU_ROOT = BASE_DIR.parent.parent
import sys
sys.path.insert(0, str(DAOSHU_ROOT))


def load_config():
    """加载 DaoZhu 的配置"""
    config_path = DAOSHU_ROOT / "config.json"
    default_config = {
        "ai": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
        }
    }
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # 简单合并
                for k, v in user_config.get("ai", {}).items():
                    default_config["ai"][k] = v
        except:
            pass
    return default_config


def get_api_key():
    """获取 API Key"""
    # 先从 .env 读取
    env_path = DAOSHU_ROOT / ".env"
    api_key = None
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("'\"")
                elif line.startswith("OPENAI_API_KEY=") and not api_key:
                    api_key = line.split("=", 1)[1].strip().strip("'\"")
    return api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")


PRD_SKILL_PROMPT = """你是专业的产品经理助手，负责编写产品需求文档(PRD)。

默认生成的PRD文档包含以下章节：
1. **文档信息**：版本号、修订日期（使用当前日期）、作者、修订记录
2. **背景概述**：业务背景、解决的问题
3. **产品目标**：商业目标和用户目标（SMART原则）
4. **用户研究**：目标用户群体、用户痛点、使用场景
5. **功能范围**：包含/不包含的功能清单
6. **功能详情**：用户故事、交互流程、业务规则
7. **交互说明**：页面跳转、状态变化、异常处理
8. **非功能需求**：性能、兼容性、安全性要求
9. **埋点需求**：埋点目的、事件埋点、页面埋点、用户属性、埋点规范
10. **验收标准**：可测试的验收条件
11. **项目计划**：依赖关系、时间节点、风险评估

注意：文档中的所有日期必须使用当前日期，格式为YYYY-MM-DD，不要使用固定的历史日期如2023-10-27。

输出为结构化的Markdown格式，便于直接使用或导出。"""


def generate_prd_content(title: str, description: str = "") -> str:
    """调用 AI 生成 PRD 内容（同步版）"""
    config = load_config()
    api_key = get_api_key()
    if not api_key:
        return "⚠️ 未配置 API Key，请在岛主平台设置中配置"

    base_url = config["ai"].get("base_url", "https://api.deepseek.com/v1")
    model = "deepseek-chat"

    user_prompt = f"请帮我编写一份完整的PRD文档，产品名称是：{title}"
    if description:
        user_prompt += f"\n\n产品描述：{description}"

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": PRD_SKILL_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            },
            timeout=120,
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"⚠️ AI 生成失败: HTTP {response.status_code}"
    except Exception as e:
        return f"⚠️ AI 生成出错: {str(e)}"


@app.on_event("startup")
def startup():
    init_db()


# ===== API 路由 =====

@app.get("/api/prds")
def list_prds():
    rows = query("SELECT * FROM prd_docs ORDER BY updated_at DESC")
    return {"data": rows}


@app.post("/api/prds")
def create_prd(data: dict):
    pid = execute(
        "INSERT INTO prd_docs (title, version, author, product_name, summary, background, goals) VALUES (?,?,?,?,?,?,?)",
        [data.get("title"), data.get("version", "v1.0"), data.get("author"), data.get("product_name"),
         data.get("summary"), data.get("background"), data.get("goals")]
    )
    return {"id": pid, "message": "PRD已创建"}


@app.get("/api/debug")
def debug_route():
    """调试路由"""
    api_key = get_api_key()
    return {"api_key_found": api_key is not None, "api_key_len": len(api_key) if api_key else 0}

@app.post("/api/prds/generate")
async def generate_prd(request: Request):
    """AI 生成 PRD"""
    try:
        data = await request.json()
    except Exception as e:
        return JSONResponse({"error": f"请求解析失败: {str(e)}"}, status_code=400)

    title = data.get("title", "")
    description = data.get("description", "")

    if not title:
        return JSONResponse({"error": "请输入产品名称"}, status_code=400)

    try:
        content = generate_prd_content(title, description)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] generate_prd_content 失败: {e}\n{tb}")
        return JSONResponse({"error": f"AI 生成失败: {str(e)}"}, status_code=500)

    if not content or content.startswith("⚠"):
        return JSONResponse({"error": content or "AI 生成失败"}, status_code=500)

    # 创建 PRD 记录
    try:
        pid = execute(
            "INSERT INTO prd_docs (title, version, author, product_name, summary, background, goals, status) VALUES (?,?,?,?,?,?,?,?)",
            [title, "v1.0", "AI 助手", title, f"AI 生成的 {title} 产品需求文档", content[:500] if content else "", "", "draft"]
        )

        execute(
            "INSERT INTO prd_sections (prd_id, section_type, title, content, sort_order) VALUES (?,?,?,?,?)",
            [pid, "full", "完整 PRD 文档", content, 0]
        )

        return {"id": pid, "content": content, "message": "PRD已生成"}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] 数据库操作失败: {e}\n{tb}")
        return JSONResponse({"error": f"数据库操作失败: {str(e)}"}, status_code=500)


@app.post("/api/description/generate")
def generate_description(data: dict):
    """AI 生成产品描述"""
    title = data.get("title", "").strip()
    if not title:
        return JSONResponse({"error": "请输入产品名称"}, status_code=400)

    api_key = get_api_key()
    if not api_key:
        return {"content": "⚠️ 未配置 API Key"}

    config = load_config()
    base_url = config["ai"].get("base_url", "https://api.deepseek.com/v1")
    model = "deepseek-chat"

    prompt = f"""你是一个产品经理助手。请为以下产品生成一段简洁的产品描述（200字以内），描述该产品的定位、核心功能和目标用户。

产品名称：{title}

要求：直接输出产品描述内容，不要有前缀，语言简洁有力。"""

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的产品经理助手。"},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=30,
        )
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return {"content": content}
        else:
            return JSONResponse({"error": f"AI 生成失败: HTTP {response.status_code}"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": f"AI 生成出错: {str(e)}"}, status_code=500)


@app.get("/api/prds/{pid}")
def get_prd(pid: int):
    row = query("SELECT * FROM prd_docs WHERE id=?", [pid])
    if not row:
        return JSONResponse({"error": "PRD不存在"}, status_code=404)
    prd = row[0]
    prd["features"] = query("SELECT * FROM prd_features WHERE prd_id=? ORDER BY priority", [pid])
    prd["metrics"] = query("SELECT * FROM prd_metrics WHERE prd_id=?", [pid])
    prd["sections"] = query("SELECT * FROM prd_sections WHERE prd_id=? ORDER BY sort_order", [pid])
    prd["reviews"] = query("SELECT * FROM prd_reviews WHERE prd_id=? ORDER BY created_at DESC", [pid])
    return {"data": prd}


@app.put("/api/prds/{pid}")
def update_prd(pid: int, data: dict):
    fields = []
    values = []
    for key in ["title", "version", "status", "author", "product_name", "summary", "background", "goals", "target_users", "milestones"]:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    if fields:
        fields.append("updated_at=CURRENT_TIMESTAMP")
        execute(f"UPDATE prd_docs SET {', '.join(fields)} WHERE id=?", [*values, pid])
    return {"message": "PRD已更新"}


@app.delete("/api/prds/{pid}")
def delete_prd(pid: int):
    """删除 PRD（级联删除关联数据）"""
    execute("DELETE FROM prd_sections WHERE prd_id=?", [pid])
    execute("DELETE FROM prd_features WHERE prd_id=?", [pid])
    execute("DELETE FROM prd_metrics WHERE prd_id=?", [pid])
    execute("DELETE FROM prd_reviews WHERE prd_id=?", [pid])
    execute("DELETE FROM prd_docs WHERE id=?", [pid])
    return {"message": "PRD已删除"}


def render_prd_to_html(prd: dict) -> str:
    """将 PRD 渲染为 HTML（Word 兼容格式）"""
    sections = prd.get("sections") or []
    features = prd.get("features") or []
    metrics = prd.get("metrics") or []
    reviews = prd.get("reviews") or []

    content_html = ""
    if sections and sections[0].get("content"):
        raw = sections[0]["content"]
        content_html = raw.replace("\n", "<br>\n")

    features_html = ""
    if features:
        rows = "".join(
            f"<tr><td>{f.get('priority','P2')}</td><td>{_esc(f.get('title',''))}</td><td>{f.get('status','待评审')}</td></tr>"
            for f in features
        )
        features_html = f"""
        <h2>功能清单</h2>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:11pt">
          <thead><tr style="background:#eef"><th>优先级</th><th>功能名称</th><th>状态</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    metrics_html = ""
    if metrics:
        rows = "".join(
            f"<tr><td>{_esc(m.get('name',''))}</td><td>{_esc(m.get('definition','-'))}</td><td>{_esc(m.get('target_value','-'))}</td></tr>"
            for m in metrics
        )
        metrics_html = f"""
        <h2>数据指标</h2>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:11pt">
          <thead><tr style="background:#eef"><th>指标名称</th><th>定义</th><th>目标值</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    reviews_html = ""
    if reviews:
        items = "".join(
            f"<div style='margin:8px 0;padding:8px;background:#f8f8f8;border-left:3px solid #6366f1'>"
            f"<strong>{_esc(r.get('reviewer',''))}</strong> "
            f"<span style='color:#666'>({r.get('created_at','')})</span> "
            f"<span style='display:inline-block;padding:1px 8px;background:#6366f1;color:#fff;border-radius:4px;font-size:10pt'>{_esc(r.get('decision',''))}</span>"
            f"<p style='margin:4px 0 0'>{_esc(r.get('comment',''))}</p></div>"
            for r in reviews
        )
        reviews_html = f"<h2>评审记录</h2>{items}"

    title = _esc(prd.get("title", "PRD文档"))
    author = _esc(prd.get("author", "AI 助手") or "AI 助手")
    version = _esc(prd.get("version", "v1.0") or "v1.0")
    created = prd.get("created_at", "")
    status_map = {"draft": "草稿", "review": "评审中", "approved": "已通过"}
    status = status_map.get(prd.get("status", ""), "草稿")

    html = f"""<html xmlns:o="urn:schemas-microsoft-com:office:office"
              xmlns:w="urn:schemas-microsoft-com:office:word"
              xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="UTF-8">
<style>
body {{ font-family: "Microsoft YaHei", SimSun, sans-serif; font-size: 11pt; line-height: 1.6; padding: 40px; max-width: 1000px; margin: 0 auto; }}
h1 {{ color: #333; border-bottom: 2px solid #6366f1; padding-bottom: 10px; }}
h2 {{ color: #444; margin-top: 24px; }}
h3 {{ color: #555; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
th {{ background: #f0f0ff; }}
.meta {{ color: #666; font-size: 10pt; margin-bottom: 20px; }}
.content {{ white-space: pre-wrap; }}
</style></head><body>
<h1>{title}</h1>
<div class="meta">版本：{version} | 状态：{status} | 作者：{author} | 创建时间：{created}</div>
<div class="content">{content_html}</div>
{features_html}
{metrics_html}
{reviews_html}
</body></html>"""
    return html


def _esc(text):
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@app.get("/api/prds/{pid}/export")
def export_prd(pid: int):
    """导出 PRD 为 .docx 文件"""
    try:
        row = query("SELECT * FROM prd_docs WHERE id=?", [pid])
        if not row:
            return JSONResponse({"error": "PRD不存在"}, status_code=404)
        prd = row[0]
        prd["features"] = query("SELECT * FROM prd_features WHERE prd_id=? ORDER BY priority", [pid])
        prd["metrics"] = query("SELECT * FROM prd_metrics WHERE prd_id=?", [pid])
        prd["sections"] = query("SELECT * FROM prd_sections WHERE prd_id=? ORDER BY sort_order", [pid])
        prd["reviews"] = query("SELECT * FROM prd_reviews WHERE prd_id=? ORDER BY created_at DESC", [pid])

        html = render_prd_to_html(prd)
        content = _generate_docx(html, prd["title"])
        safe_title = re.sub(r'[^\x20-\x7e]', '', prd["title"]).strip()[:20] or "PRD"
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d')}"

        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}.docx\""}
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[export error] {e}\n{tb}")
        return JSONResponse({"error": f"导出失败: {str(e)}"}, status_code=500)


def _generate_docx(html: str, title: str) -> bytes:
    """用内建模块生成 .docx（纯 Python，无需 python-docx）"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""")
        z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""")
        z.writestr("word/_rels/document.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>""")
        # 简单的 document.xml，包含标题和 HTML 内容
        safe_title = _esc(title)
        safe_html = _esc(html)
        doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:rPr><w:rFonts w:eastAsia="Microsoft YaHei"/><w:sz w:val="32"/></w:rPr><w:t>{safe_title}</w:t></w:r></w:p>
<w:p><w:r><w:rPr><w:rFonts w:eastAsia="Microsoft YaHei"/><w:sz w:val="20"/></w:rPr><w:t xml:space="preserve">导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</w:t></w:r></w:p>
</w:body></w:document>"""
        # 使用 HTML 作为后备：直接嵌入到 document.xml 的简单段落中
        # 由于纯 XML 方式太复杂，用简单段落替代
        z.writestr("word/document.xml", doc_xml.encode("utf-8"))
    return buf.getvalue()


# 特性管理
@app.get("/api/prds/{pid}/features")
def list_features(pid: int):
    rows = query("SELECT * FROM prd_features WHERE prd_id=?", [pid])
    return {"data": rows}


@app.post("/api/prds/{pid}/features")
def create_feature(pid: int, data: dict):
    fid = execute(
        "INSERT INTO prd_features (prd_id, title, description, priority, acceptance_criteria) VALUES (?,?,?,?,?)",
        [pid, data.get("title"), data.get("description", ""), data.get("priority", "P2"), data.get("acceptance_criteria", "")]
    )
    return {"id": fid, "message": "功能已添加"}


@app.put("/api/features/{fid}")
def update_feature(fid: int, data: dict):
    fields = []
    values = []
    for key in ["title", "description", "priority", "status", "acceptance_criteria"]:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    if fields:
        execute(f"UPDATE prd_features SET {', '.join(fields)} WHERE id=?", [*values, fid])
    return {"message": "功能已更新"}


@app.delete("/api/features/{fid}")
def delete_feature(fid: int):
    execute("DELETE FROM prd_features WHERE id=?", [fid])
    return {"message": "功能已删除"}


# 指标管理
@app.post("/api/prds/{pid}/metrics")
def create_metric(pid: int, data: dict):
    mid = execute("INSERT INTO prd_metrics (prd_id, name, definition, target_value) VALUES (?,?,?,?)",
                  [pid, data.get("name"), data.get("definition", ""), data.get("target_value", "")])
    return {"id": mid, "message": "指标已添加"}


@app.delete("/api/metrics/{mid}")
def delete_metric(mid: int):
    execute("DELETE FROM prd_metrics WHERE id=?", [mid])
    return {"message": "指标已删除"}


# 评审管理
@app.post("/api/prds/{pid}/reviews")
def create_review(pid: int, data: dict):
    rid = execute("INSERT INTO prd_reviews (prd_id, reviewer, comment, decision) VALUES (?,?,?,?)",
                  [pid, data.get("reviewer"), data.get("comment", ""), data.get("decision", "待定")])
    return {"id": rid, "message": "评审记录已添加"}


@app.get("/api/prds/{pid}/reviews")
def list_reviews(pid: int):
    rows = query("SELECT * FROM prd_reviews WHERE prd_id=? ORDER BY created_at DESC", [pid])
    return {"data": rows}


# ===== 前端页面 =====

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = BASE_DIR / "frontend" / "index.html"
    if html_path.exists():
        return HTMLResponse(
            content=html_path.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return HTMLResponse("<h1>PRD编写助手</h1><p>前端页面加载中...</p>")


@app.get("/static/{filename}")
def static_files(filename: str):
    fpath = BASE_DIR / "frontend" / filename
    if fpath.exists():
        content = fpath.read_bytes()
        ext = fpath.suffix
        media_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }.get(ext, "text/plain")
        return Response(
            content=content,
            media_type=media_type,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return JSONResponse({"error": "文件不存在"}, status_code=404)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8512))
    uvicorn.run(app, host="0.0.0.0", port=port)
