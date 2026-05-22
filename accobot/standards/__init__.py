"""Accounting standards configuration loader.

Loads standard-specific configurations (accounts, voucher templates,
report rules, tax rules, audit requirements) from the standards directory.

Directory structure:
    accobot/standards/{standard_name}/
        README.md, accounts/, vouchers/, reports/, tax/, audit/

REQ-025: 会计准则完整配置
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

STANDARDS_DIR = Path(__file__).parent


def get_standard_dir(standard: str) -> Path:
    """Get the directory for a specific accounting standard."""
    return STANDARDS_DIR / standard


def list_standards() -> List[str]:
    """List available accounting standards."""
    return [
        d.name for d in STANDARDS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    ]


def load_json(standard: str, *path_parts: str) -> Optional[Any]:
    """Load a JSON file from a standard's directory.

    Example: load_json("small_enterprise", "vouchers", "income.json")
    """
    file_path = get_standard_dir(standard) / Path(*path_parts)
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load %s: %s", file_path, e)
        return None


def load_voucher_templates(standard: str) -> List[Dict]:
    """Load all voucher templates for a standard."""
    templates = []
    voucher_dir = get_standard_dir(standard) / "vouchers"
    if not voucher_dir.exists():
        return templates

    for f in sorted(voucher_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                templates.extend(data)
        except Exception as e:
            logger.warning("Failed to load voucher template %s: %s", f, e)

    return templates


def load_report_rules(standard: str, report_type: str) -> Optional[Dict]:
    """Load report rules (profit_loss or balance_sheet)."""
    return load_json(standard, "reports", f"{report_type}.json")


def load_readme(standard: str) -> str:
    """Load the README.md for a standard."""
    readme_path = get_standard_dir(standard) / "README.md"
    if readme_path.exists():
        return readme_path.read_text(encoding="utf-8")
    return ""
