"""Accounting standards — rules and documentation for each supported standard.

Generates standard documents (accounting_rules.md + chart_of_accounts.json)
into the company folder for Agent consumption.

REQ-023: 账套会计准则维护
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# =========================================================================
# Standard Metadata
# =========================================================================

STANDARDS: Dict[str, Dict] = {
    "small_enterprise": {
        "name": "小企业会计准则",
        "full_name": "《小企业会计准则》（财会〔2011〕17号）",
        "applicable": "年营业收入不超过规定标准的小型企业和微型企业",
        "key_differences": [
            "不要求计提坏账准备（应收账款实际发生损失时直接核销）",
            "不使用递延所得税资产/负债科目",
            "不要求资产减值准备（固定资产、无形资产等不计提减值）",
            "不使用公允价值变动损益科目",
            "长期股权投资统一采用成本法",
            "财务报表较简化（无现金流量表附注要求）",
        ],
    },
    "enterprise": {
        "name": "企业会计准则",
        "full_name": "《企业会计准则》（财政部令第76号及后续修订）",
        "applicable": "上市公司、大中型企业、以及自愿执行的其他企业",
        "key_differences": [
            "要求计提坏账准备（预期信用损失模型）",
            "使用递延所得税资产/负债科目",
            "要求资产减值测试和计提减值准备",
            "使用公允价值变动损益科目",
            "长期股权投资区分成本法和权益法",
            "要求编制完整现金流量表",
            "要求更详细的附注披露",
        ],
    },
}


# =========================================================================
# Rules Document Generation
# =========================================================================

def generate_accounting_rules(standard: str) -> str:
    """Generate the accounting_rules.md content for a given standard."""
    info = STANDARDS.get(standard)
    if not info:
        info = STANDARDS["small_enterprise"]

    lines = [
        f"# {info['name']}",
        "",
        f"**全称：** {info['full_name']}",
        f"**适用范围：** {info['applicable']}",
        "",
        "## 核心规则",
        "",
    ]

    for i, rule in enumerate(info["key_differences"], 1):
        lines.append(f"{i}. {rule}")

    lines.extend([
        "",
        "## Agent 做账约束",
        "",
    ])

    if standard == "small_enterprise":
        lines.extend([
            "- 不得使用以下科目：递延所得税资产、递延所得税负债、坏账准备、资产减值损失、公允价值变动损益",
            "- 应收账款发生坏账时，直接借记营业外支出，贷记应收账款",
            "- 固定资产、无形资产不计提减值准备，只计提折旧/摊销",
            "- 长期股权投资一律采用成本法核算",
            "- 所得税费用 = 当期应交所得税，不做递延处理",
            "- 政府补助收到时直接计入营业外收入",
        ])
    else:
        lines.extend([
            "- 应收账款需按预期信用损失模型计提坏账准备",
            "- 每期末需评估递延所得税资产/负债",
            "- 固定资产、无形资产需进行减值测试",
            "- 交易性金融资产按公允价值计量，变动计入公允价值变动损益",
            "- 长期股权投资需区分成本法（控制）和权益法（重大影响）",
            "- 政府补助需区分与资产相关和与收益相关，分别处理",
            "- 期末需编制现金流量表",
        ])

    lines.extend([
        "",
        "## 报表要求",
        "",
    ])

    if standard == "small_enterprise":
        lines.extend([
            "- 资产负债表（简化格式）",
            "- 利润表（简化格式）",
            "- 现金流量表（可选）",
            "- 附注（简化）",
        ])
    else:
        lines.extend([
            "- 资产负债表（完整格式）",
            "- 利润表（完整格式）",
            "- 现金流量表（必须）",
            "- 所有者权益变动表",
            "- 附注（详细披露）",
        ])

    return "\n".join(lines)


def generate_chart_json(standard: str) -> str:
    """Generate chart_of_accounts.json for a given standard."""
    from accobot.db.templates import load_template

    template = load_template(standard)
    accounts = []
    for code, name, category, direction, parent in template:
        accounts.append({
            "code": code,
            "name": name,
            "category": category,
            "balance_direction": direction,
            "parent_code": parent,
        })

    data = {
        "standard": standard,
        "standard_name": STANDARDS.get(standard, {}).get("name", standard),
        "account_count": len(accounts),
        "accounts": accounts,
    }

    return json.dumps(data, ensure_ascii=False, indent=2)


# =========================================================================
# File Generation
# =========================================================================

def generate_standard_docs(company_dir: Path, standard: str) -> bool:
    """Generate standard documents in the company directory.

    Creates:
        company_dir/standard/accounting_rules.md
        company_dir/standard/chart_of_accounts.json

    Returns True on success.
    """
    standard_dir = company_dir / "standard"
    standard_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Generate rules document
        rules_content = generate_accounting_rules(standard)
        (standard_dir / "accounting_rules.md").write_text(rules_content, encoding="utf-8")

        # Generate chart of accounts JSON
        chart_content = generate_chart_json(standard)
        (standard_dir / "chart_of_accounts.json").write_text(chart_content, encoding="utf-8")

        logger.info("Generated standard docs for '%s' in %s", standard, standard_dir)
        return True
    except Exception as e:
        logger.error("Failed to generate standard docs: %s", e)
        return False


def load_standard_rules_summary(company_dir: Path) -> str:
    """Load a compact summary of accounting rules for system prompt injection.

    Returns empty string if no standard docs found.
    """
    rules_path = company_dir / "standard" / "accounting_rules.md"
    if not rules_path.exists():
        return ""

    try:
        content = rules_path.read_text(encoding="utf-8")
        # Return the full content (it's already concise)
        return f"\n\n## 当前账套适用的会计准则\n\n{content}"
    except Exception as e:
        logger.debug("Failed to load standard rules: %s", e)
        return ""
