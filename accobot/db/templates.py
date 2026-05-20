"""Chart of accounts templates.

Provides default account templates for different accounting standards.
"""

from typing import List, Tuple

# Format: (code, name, category, balance_direction, parent_code)
# category: asset, liability, equity, cost, income, expense
# balance_direction: debit, credit

SMALL_ENTERPRISE_ACCOUNTS: List[Tuple[str, str, str, str, str]] = [
    # 资产类
    ("1001", "库存现金", "asset", "debit", None),
    ("1002", "银行存款", "asset", "debit", None),
    ("1012", "其他货币资金", "asset", "debit", None),
    ("1101", "短期投资", "asset", "debit", None),
    ("1121", "应收票据", "asset", "debit", None),
    ("1122", "应收账款", "asset", "debit", None),
    ("1123", "预付账款", "asset", "debit", None),
    ("1131", "应收股利", "asset", "debit", None),
    ("1132", "应收利息", "asset", "debit", None),
    ("1221", "其他应收款", "asset", "debit", None),
    ("1401", "材料采购", "asset", "debit", None),
    ("1402", "在途物资", "asset", "debit", None),
    ("1403", "原材料", "asset", "debit", None),
    ("1404", "材料成本差异", "asset", "debit", None),
    ("1405", "库存商品", "asset", "debit", None),
    ("1407", "商品进销差价", "asset", "credit", None),
    ("1408", "委托加工物资", "asset", "debit", None),
    ("1411", "周转材料", "asset", "debit", None),
    ("1501", "长期债券投资", "asset", "debit", None),
    ("1511", "长期股权投资", "asset", "debit", None),
    ("1601", "固定资产", "asset", "debit", None),
    ("1602", "累计折旧", "asset", "credit", None),
    ("1604", "在建工程", "asset", "debit", None),
    ("1605", "工程物资", "asset", "debit", None),
    ("1606", "固定资产清理", "asset", "debit", None),
    ("1621", "生产性生物资产", "asset", "debit", None),
    ("1622", "生产性生物资产累计折旧", "asset", "credit", None),
    ("1701", "无形资产", "asset", "debit", None),
    ("1702", "累计摊销", "asset", "credit", None),
    ("1801", "长期待摊费用", "asset", "debit", None),
    ("1901", "待处理财产损溢", "asset", "debit", None),
    # 负债类
    ("2001", "短期借款", "liability", "credit", None),
    ("2201", "应付票据", "liability", "credit", None),
    ("2202", "应付账款", "liability", "credit", None),
    ("2203", "预收账款", "liability", "credit", None),
    ("2211", "应付职工薪酬", "liability", "credit", None),
    ("2221", "应交税费", "liability", "credit", None),
    ("222101", "应交增值税", "liability", "credit", "2221"),
    ("222102", "应交城市维护建设税", "liability", "credit", "2221"),
    ("222103", "应交教育费附加", "liability", "credit", "2221"),
    ("222104", "应交企业所得税", "liability", "credit", "2221"),
    ("222105", "应交个人所得税", "liability", "credit", "2221"),
    ("2231", "应付利息", "liability", "credit", None),
    ("2232", "应付股利", "liability", "credit", None),
    ("2241", "其他应付款", "liability", "credit", None),
    ("2401", "递延收益", "liability", "credit", None),
    ("2501", "长期借款", "liability", "credit", None),
    ("2701", "长期应付款", "liability", "credit", None),
    # 所有者权益类
    ("3001", "实收资本", "equity", "credit", None),
    ("3002", "资本公积", "equity", "credit", None),
    ("3101", "盈余公积", "equity", "credit", None),
    ("3103", "本年利润", "equity", "credit", None),
    ("3104", "利润分配", "equity", "credit", None),
    # 成本类
    ("4001", "生产成本", "cost", "debit", None),
    ("4101", "制造费用", "cost", "debit", None),
    ("4301", "研发支出", "cost", "debit", None),
    ("4401", "工程施工", "cost", "debit", None),
    # 损益类 - 收入
    ("5001", "主营业务收入", "income", "credit", None),
    ("5051", "其他业务收入", "income", "credit", None),
    ("5111", "投资收益", "income", "credit", None),
    ("5301", "营业外收入", "income", "credit", None),
    # 损益类 - 费用/支出
    ("5401", "主营业务成本", "expense", "debit", None),
    ("5402", "其他业务成本", "expense", "debit", None),
    ("5403", "税金及附加", "expense", "debit", None),
    ("5601", "销售费用", "expense", "debit", None),
    ("560101", "广告费", "expense", "debit", "5601"),
    ("560102", "运输费", "expense", "debit", "5601"),
    ("560103", "包装费", "expense", "debit", "5601"),
    ("5602", "管理费用", "expense", "debit", None),
    ("560201", "办公费", "expense", "debit", "5602"),
    ("560202", "差旅费", "expense", "debit", "5602"),
    ("560203", "租赁费", "expense", "debit", "5602"),
    ("560204", "折旧费", "expense", "debit", "5602"),
    ("560205", "水电费", "expense", "debit", "5602"),
    ("560206", "通讯费", "expense", "debit", "5602"),
    ("560207", "业务招待费", "expense", "debit", "5602"),
    ("560208", "工资薪金", "expense", "debit", "5602"),
    ("560209", "社保费", "expense", "debit", "5602"),
    ("560210", "邮寄费", "expense", "debit", "5602"),
    ("5603", "财务费用", "expense", "debit", None),
    ("560301", "利息支出", "expense", "debit", "5603"),
    ("560302", "手续费", "expense", "debit", "5603"),
    ("5711", "营业外支出", "expense", "debit", None),
    ("5801", "所得税费用", "expense", "debit", None),
]


def load_template(standard: str = "small_enterprise") -> List[Tuple[str, str, str, str, str]]:
    """Load account template by standard name."""
    if standard == "small_enterprise":
        return SMALL_ENTERPRISE_ACCOUNTS
    # TODO: Add enterprise standard (企业会计准则) template
    return SMALL_ENTERPRISE_ACCOUNTS


def init_accounts(db, standard: str = "small_enterprise") -> int:
    """Initialize chart of accounts from template. Returns count of accounts added."""
    template = load_template(standard)
    count = 0
    for code, name, category, direction, parent in template:
        is_leaf = not any(t[4] == code for t in template)
        db.add_account(
            code=code,
            name=name,
            category=category,
            balance_direction=direction,
            parent_code=parent,
            is_leaf=is_leaf,
        )
        count += 1
    return count


def init_periods(db, year: int) -> int:
    """Initialize 12 monthly periods for a year."""
    import calendar
    count = 0
    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        db.add_period(
            year=year,
            month=month,
            start_date=f"{year}-{month:02d}-01",
            end_date=f"{year}-{month:02d}-{last_day:02d}",
        )
        count += 1
    return count
