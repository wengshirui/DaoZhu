/**
 * AccoBot — Reports Module (split from data-panel.js)
 * Financial reports: Profit & Loss, Balance Sheet.
 */

// ===== Reports (利润表 / 资产负债表) =====
async function loadReports() {
    const container = document.getElementById('data-panel-content');
    container.innerHTML = `<div class="dp-quick-actions" style="margin-top:12px;">
        <button class="dp-action-btn" onclick="showReportModal('profit')">📊 利润表</button>
        <button class="dp-action-btn" onclick="showReportModal('balance')">📋 资产负债表</button>
    </div>
    <div class="dp-empty" style="padding-top:30px;">点击上方按钮查看报表（弹窗展示）</div>`;
}

async function showReportModal(type) {
    try {
        const r = await fetch('/api/ledger/balance-sheet');
        const data = await r.json();
        if (data.error) { alert(data.error); return; }
        if (!data.accounts || !data.accounts.length) { alert('暂无数据（需要有已过账的凭证）'); return; }

        const title = type === 'profit' ? '📊 利润表' : '📋 资产负债表';
        const content = type === 'profit' ? renderProfitReport(data.accounts) : renderBalanceReport(data.accounts);

        let html = `<div class="detail-modal" onclick="if(event.target===this)closeDetailModal()">
            <div class="detail-modal-content">
                <div class="detail-modal-header">
                    <h3>${title}</h3>
                    <button class="detail-modal-close" onclick="closeDetailModal()">×</button>
                </div>
                ${content}
            </div>
        </div>`;

        const div = document.createElement('div');
        div.id = 'detail-modal-container';
        div.innerHTML = html;
        document.body.appendChild(div);
    } catch (e) {
        alert('加载报表失败');
    }
}

function renderProfitReport(accounts) {
    const income = accounts.filter(a => a.category === 'income');
    const expense = accounts.filter(a => a.category === 'expense');
    const totalIncome = income.reduce((s, a) => s + a.balance, 0);
    const totalExpense = expense.reduce((s, a) => s + a.balance, 0);
    const profit = totalIncome - totalExpense;

    let html = '<table class="dp-table">';
    html += '<thead><tr><th colspan="2">利润表</th></tr></thead><tbody>';

    html += '<tr><td colspan="2" style="font-weight:600;padding-top:10px;">一、营业收入</td></tr>';
    for (const a of income) {
        html += `<tr><td style="padding-left:16px;">${esc(a.name)}</td><td class="num">${formatNum(a.balance)}</td></tr>`;
    }
    html += `<tr class="dp-total"><td>收入合计</td><td class="num">${formatNum(totalIncome)}</td></tr>`;

    html += '<tr><td colspan="2" style="font-weight:600;padding-top:10px;">二、营业支出</td></tr>';
    for (const a of expense) {
        html += `<tr><td style="padding-left:16px;">${esc(a.name)}</td><td class="num">${formatNum(a.balance)}</td></tr>`;
    }
    html += `<tr class="dp-total"><td>支出合计</td><td class="num">${formatNum(totalExpense)}</td></tr>`;

    const profitColor = profit >= 0 ? 'dp-income' : 'dp-expense';
    html += `<tr class="dp-total"><td style="font-weight:700;">三、净利润</td><td class="num ${profitColor}" style="font-weight:700;">${formatNum(profit)}</td></tr>`;

    html += '</tbody></table>';
    return html;
}

function renderBalanceReport(accounts) {
    const assets = accounts.filter(a => a.category === 'asset');
    const liabilities = accounts.filter(a => a.category === 'liability');
    const equity = accounts.filter(a => a.category === 'equity');
    const totalAssets = assets.reduce((s, a) => s + a.balance, 0);
    const totalLiabilities = liabilities.reduce((s, a) => s + a.balance, 0);
    const totalEquity = equity.reduce((s, a) => s + a.balance, 0);

    let html = '<table class="dp-table">';
    html += '<thead><tr><th colspan="2">资产负债表</th></tr></thead><tbody>';

    html += '<tr><td colspan="2" style="font-weight:600;padding-top:10px;">资产</td></tr>';
    for (const a of assets) {
        html += `<tr><td style="padding-left:16px;">${esc(a.name)}</td><td class="num">${formatNum(a.balance)}</td></tr>`;
    }
    html += `<tr class="dp-total"><td>资产合计</td><td class="num">${formatNum(totalAssets)}</td></tr>`;

    html += '<tr><td colspan="2" style="font-weight:600;padding-top:10px;">负债</td></tr>';
    for (const a of liabilities) {
        html += `<tr><td style="padding-left:16px;">${esc(a.name)}</td><td class="num">${formatNum(a.balance)}</td></tr>`;
    }
    html += `<tr class="dp-total"><td>负债合计</td><td class="num">${formatNum(totalLiabilities)}</td></tr>`;

    html += '<tr><td colspan="2" style="font-weight:600;padding-top:10px;">所有者权益</td></tr>';
    for (const a of equity) {
        html += `<tr><td style="padding-left:16px;">${esc(a.name)}</td><td class="num">${formatNum(a.balance)}</td></tr>`;
    }
    html += `<tr class="dp-total"><td>权益合计</td><td class="num">${formatNum(totalEquity)}</td></tr>`;

    const liabEquity = totalLiabilities + totalEquity;
    const balanced = Math.abs(totalAssets - liabEquity) < 0.01;
    const checkIcon = balanced ? '✅' : '⚠️';
    html += `<tr><td colspan="2" style="padding-top:10px;font-size:11px;color:var(--dim);">${checkIcon} 资产 ${formatNum(totalAssets)} = 负债+权益 ${formatNum(liabEquity)}</td></tr>`;

    html += '</tbody></table>';
    return html;
}
