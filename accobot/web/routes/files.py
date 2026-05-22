"""File upload & attachment routes."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile

router = APIRouter()


@router.post("/api/upload/file")
async def handle_file_upload(file: UploadFile):
    """Upload a single file. Stores in the current company's documents folder."""
    from accobot.db.manager import DBManager
    from datetime import date as date_mod

    mgr = DBManager.get_instance()
    if not mgr.current_company_id:
        return {"success": False, "error": "请先选择账套"}

    company_dir = mgr.get_company_dir(mgr.current_company_id)
    if not company_dir:
        return {"success": False, "error": "账套文件夹不存在"}

    today = date_mod.today()
    period_folder = f"{today.year}-{today.month:02d}"
    target_dir = company_dir / "documents" / period_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or f"upload_{today.isoformat()}_{uuid.uuid4().hex[:6]}"
    safe_name = "".join(c for c in filename if c.isalnum() or c in ".-_ ()（）")
    if not safe_name:
        safe_name = f"file_{uuid.uuid4().hex[:8]}"

    target_path = target_dir / safe_name
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        target_path = target_dir / f"{stem}_{uuid.uuid4().hex[:4]}{suffix}"

    content = await file.read()
    target_path.write_bytes(content)

    return {
        "success": True,
        "filename": target_path.name,
        "path": str(target_path),
        "size": len(content),
        "period": period_folder,
        "message": f"文件 {target_path.name} 已上传到 {period_folder}/",
    }


@router.get("/api/files/list")
async def list_uploaded_files(period: str = None):
    """List uploaded files for the current company."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.current_company_id:
        return {"files": [], "error": "请先选择账套"}

    company_dir = mgr.get_company_dir(mgr.current_company_id)
    if not company_dir:
        return {"files": [], "error": "账套文件夹不存在"}

    docs_dir = company_dir / "documents"
    if not docs_dir.exists():
        return {"files": [], "periods": []}

    files = []
    periods = []

    for period_dir in sorted(docs_dir.iterdir()):
        if not period_dir.is_dir():
            continue
        periods.append(period_dir.name)
        if period and period_dir.name != period:
            continue
        for f in sorted(period_dir.iterdir()):
            if f.is_file():
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "period": period_dir.name,
                })

    return {"files": files, "periods": periods, "count": len(files)}


@router.post("/api/attachments/link")
async def link_attachment(request: dict):
    """Link an uploaded file to a voucher."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"success": False, "error": "请先选择账套"}

    voucher_id = request.get("voucher_id", "")
    file_path = request.get("file_path", "")
    filename = request.get("filename", "")

    if not voucher_id or not file_path:
        return {"success": False, "error": "缺少凭证ID或文件路径"}

    voucher = mgr.accounting.get_voucher_with_entries(voucher_id)
    if not voucher:
        return {"success": False, "error": f"凭证 {voucher_id} 不存在"}

    fp = Path(file_path)
    size = fp.stat().st_size if fp.exists() else 0
    name = filename or fp.name

    att_id = mgr.accounting.add_attachment(voucher_id, name, file_path, file_size=size)
    return {"success": True, "attachment_id": att_id, "message": f"附件 {name} 已关联到凭证 {voucher_id}"}


@router.get("/api/attachments/{voucher_id}")
async def get_attachments(voucher_id: str):
    """Get attachments for a voucher."""
    from accobot.db.manager import DBManager

    mgr = DBManager.get_instance()
    if not mgr.accounting:
        return {"attachments": [], "error": "请先选择账套"}

    attachments = mgr.accounting.get_attachments(voucher_id)
    return {"attachments": attachments, "count": len(attachments)}
