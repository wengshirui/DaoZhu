/**
 * AccoBot — Data Panel Module (REQ-024)
 * Business operation area: browse and filter financial data.
 * Categories: 凭证, 科目, 账簿(余额表), 辅助属性
 */

// ===== State =====
let dataPanelTab = 'overview';  // default to overview (not raw voucher list)
let voucherFilters = { status: '', keyword: '', date_from: '', date_to: '' };
let voucherPage = 0;
const PAGE_SIZE = 20;

// ===== Tab Navigation =====
function switchDataTab(tab) {
    dataPanelTab = tab;
    document.querySelectorAll('.data-tab-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.data-tab-btn[data-tab="${tab}"]`);
    if (btn) btn.classList.add('active');

    if (tab === 'overview') loadOverviewPanel();
    else if (tab === 'vouchers') loadVoucherList();
    else if (tab === 'accounts') loadAccountList();
    else if (tab === 'ledger') loadLedgerBalance();
    else if (tab === 'reports') loadReports();
    else if (tab === 'aux') loadAuxItems();
}

// ===== Overview (Dashboard) =====
async function loadOverviewPanel() {
    const container = document.getElementById('data-panel-content');
    container.innerHTML = '<div class="dp-loading">加载中...</div>';

    try {
        const [overviewR, vouchersR, taxR] = await Promise.all([
            fetch('/api/data/overview'),
            fetch('/api/vouchers?status=draft&limit=5'),
            fetch('/api/tax/summary'),
        ]);
        const overview = await overviewR.json();
        const drafts = await vouchersR.json();
        const tax = await taxR.json();

        if (overview.error) {
            container.innerHTML = `<div class="dp-empty">${overview.error}</div>`;
            return;
        }

        let html = '<div class="dp-overview">';

        // Key metrics
        html += '<div class="dp-metrics">';
        html += `<div class="dp-metric"><span class="dp-metric-label">银行存款</span><span class="dp-metric-value">${formatNum(overview.bank_balance)}</span></div>`;
        html += `<div class="dp-metric"><span class="dp-metric-label">应收账款</span><span class="dp-metric-value">${formatNum(overview.receivable)}</span></div>`;
        html += `<div class="dp-metric"><span class="dp-metric-label">应付账款</span><span class="dp-metric-value">${formatNum(overview.payable)}</span></div>`;
        html += `<div class="dp-metric"><span class="dp-metric-label">本月收入</span><span class="dp-metric-value dp-income">${formatNum(overview.monthly_income)}</span></div>`;
        html += `<div class="dp-metric"><span class="dp-metric-label">本月支出</span><span class="dp-metric-value dp-expense">${formatNum(overview.monthly_expense)}</span></div>`;

        // Tax summary card (clickable → has › indicator)
        html += `<div class="dp-metric dp-metric-tax" onclick="showTaxDetail()"><span class="dp-metric-label">应交税费 <span class="dp-clickable-hint">›</span></span><span class="dp-metric-value">${formatNum(tax.total_tax || 0)}</span></div>`;
        html += '</div>';

        // Anomaly alerts (data self-check)
        html += await renderAnomalyAlerts(overview);

        // Degraded data warning
        if (overview.degraded && overview.degraded_reasons && overview.degraded_reasons.length) {
            html += '<div class="dp-degraded">';
            for (const reason of overview.degraded_reasons) {
                html += `<div class="dp-degraded-item">⚡ ${esc(reason)}</div>`;
            }
            html += '</div>';
        }

        // Draft vouchers needing attention
        if (drafts.vouchers && drafts.vouchers.length > 0) {
            html += '<div class="dp-section-title">📋 待处理凭证</div>';
            html += '<div class="dp-list">';
            for (const v of drafts.vouchers) {
                html += `<div class="dp-item dp-item-sm" onclick="showVoucherDetail('${v.id}')">
                    <span class="dp-date">${v.voucher_date}</span>
                    <span class="dp-summary">${esc(v.summary || '(无摘要)')}</span>
                    <span class="dp-status status-draft">草稿</span>
                </div>`;
            }
            html += '</div>';
            if (drafts.total > 5) {
                html += `<div class="dp-more" onclick="switchDataTab('vouchers'); voucherFilters.status='draft'; loadVoucherList()">查看全部 ${drafts.total} 张 →</div>`;
            }
        }

        // Quick actions
        html += '<div class="dp-section-title">⚡ 快捷操作</div>';
        html += '<div class="dp-quick-actions">';
        html += '<button class="dp-action-btn" onclick="quickAction(\'帮我做一下本月的质检\')">🔍 质检</button>';
        html += '<button class="dp-action-btn" onclick="quickAction(\'本月利润是多少\')">📊 利润</button>';
        html += '<button class="dp-action-btn" onclick="quickAction(\'帮我结转本月损益\')">📅 结转</button>';
        html += '</div>';

        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="dp-empty">加载失败</div>';
    }
}

async function renderAnomalyAlerts(overview) {
    // Simple data self-check based on accounting logic
    let alerts = [];

    // Check: income but no expense (unusual)
    if (overview.monthly_income > 0 && overview.monthly_expense === 0) {
        alerts.push({ icon: '⚠️', msg: '本月有收入但无支出记录，请检查是否有遗漏' });
    }
    // Check: negative bank balance
    if (overview.bank_balance < 0) {
        alerts.push({ icon: '🔴', msg: `银行存款为负数（${formatNum(overview.bank_balance)}），请核实` });
    }
    // Check: large draft backlog
    if (overview.draft_count >= 10) {
        alerts.push({ icon: '📋', msg: `${overview.draft_count} 张凭证未过账，建议及时处理` });
    }

    if (!alerts.length) return '';

    let html = '<div class="dp-section-title">⚠️ 异常提示</div><div class="dp-alerts">';
    for (const a of alerts) {
        html += `<div class="dp-alert">${a.icon} ${a.msg}</div>`;
    }
    html += '</div>';
    return html;
}

function quickAction(prompt) {
    // Send a message to the chat input and trigger send
    const input = document.getElementById('input');
    if (input) {
        input.value = prompt;
        sendMessage();
    }
}

// ===== Vouchers =====
async function loadVoucherList() {
    const container = document.getElementById('data-panel-content');
    container.innerHTML = '<div class="dp-loading">加载中...</div>';

    const params = new URLSearchParams();
    if (voucherFilters.status) params.set('status', voucherFilters.status);
    if (voucherFilters.keyword) params.set('keyword', voucherFilters.keyword);
    if (voucherFilters.date_from) params.set('date_from', voucherFilters.date_from);
    if (voucherFilters.date_to) params.set('date_to', voucherFilters.date_to);
    params.set('limit', PAGE_SIZE);
    params.set('offset', voucherPage * PAGE_SIZE);

    try {
        const r = await fetch(`/api/vouchers?${params}`);
        const data = await r.json();

        if (data.error) { container.innerHTML = `<div class="dp-empty">${data.error}</div>`; return; }

        let html = renderVoucherFilters();
        if (!data.vouchers.length) {
            html += '<div class="dp-empty">暂无凭证</div>';
        } else {
            html += '<div class="dp-list">';
            for (const v of data.vouchers) {
                const statusCls = v.status === 'posted' ? 'status-posted' : 'status-draft';
                const statusText = v.status === 'posted' ? '已过账' : '草稿';
                html += `<div class="dp-item" onclick="showVoucherDetail('${v.id}')">
                    <div class="dp-item-main">
                        <span class="dp-date">${v.voucher_date}</span>
                        <span class="dp-summary">${esc(v.summary || '(无摘要)')}</span>
                    </div>
                    <div class="dp-item-meta">
                        <span class="dp-amount">${formatNum(v.total_debit)}</span>
                        <span class="dp-status ${statusCls}">${statusText}</span>
                    </div>
                </div>`;
            }
            html += '</div>';

            // Pagination
            const totalPages = Math.ceil(data.total / PAGE_SIZE);
            if (totalPages > 1) {
                html += `<div class="dp-pagination">
                    <button class="btn-sm" onclick="voucherPrev()" ${voucherPage === 0 ? 'disabled' : ''}>上一页</button>
                    <span>${voucherPage + 1} / ${totalPages}</span>
                    <button class="btn-sm" onclick="voucherNext(${totalPages})" ${voucherPage >= totalPages - 1 ? 'disabled' : ''}>下一页</button>
                </div>`;
            }
        }
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="dp-empty">加载失败</div>';
    }
}

function renderVoucherFilters() {
    return `<div class="dp-filters">
        <select onchange="voucherFilters.status=this.value; voucherPage=0; loadVoucherList()">
            <option value="">全部状态</option>
            <option value="draft" ${voucherFilters.status==='draft'?'selected':''}>草稿</option>
            <option value="posted" ${voucherFilters.status==='posted'?'selected':''}>已过账</option>
        </select>
        <input type="text" placeholder="搜索摘要..." value="${esc(voucherFilters.keyword)}"
            onchange="voucherFilters.keyword=this.value; voucherPage=0; loadVoucherList()" />
    </div>`;
}

function voucherPrev() { if (voucherPage > 0) { voucherPage--; loadVoucherList(); } }
function voucherNext(total) { if (voucherPage < total - 1) { voucherPage++; loadVoucherList(); } }

async function showVoucherDetail(id) {
    // Show in modal instead of left panel (too narrow)
    try {
        const r = await fetch(`/api/vouchers/${id}`);
        const data = await r.json();
        if (data.error) { alert(data.error); return; }

        const v = data.voucher;
        const statusText = v.status === 'posted' ? '已过账' : '草稿';
        let html = `<div class="detail-modal" onclick="if(event.target===this)closeDetailModal()">
            <div class="detail-modal-content">
                <div class="detail-modal-header">
                    <h3>📋 ${esc(v.summary || '凭证详情')}</h3>
                    <button class="detail-modal-close" onclick="closeDetailModal()">×</button>
                </div>
                <div class="dp-detail-meta">
                    <span>编号: ${v.id}</span>
                    <span>日期: ${v.voucher_date}</span>
                    <span>状态: ${statusText}</span>
                    <span>期间: ${v.period_id || '-'}</span>
                </div>
                <table class="dp-table">
                    <thead><tr><th>摘要</th><th>科目</th><th>借方</th><th>贷方</th></tr></thead>
                    <tbody>`;
        for (const e of v.entries || []) {
            html += `<tr>
                <td>${esc(e.summary || v.summary || '')}</td>
                <td>${e.account_name} (${e.account_code})</td>
                <td class="num">${e.debit > 0 ? formatNum(e.debit) : ''}</td>
                <td class="num">${e.credit > 0 ? formatNum(e.credit) : ''}</td>
            </tr>`;
        }
        const totalD = (v.entries || []).reduce((s, e) => s + e.debit, 0);
        const totalC = (v.entries || []).reduce((s, e) => s + e.credit, 0);
        html += `<tr class="dp-total"><td colspan="2">合计</td><td class="num">${formatNum(totalD)}</td><td class="num">${formatNum(totalC)}</td></tr>`;
        html += '</tbody></table></div></div>';

        // Append modal to body
        const div = document.createElement('div');
        div.id = 'detail-modal-container';
        div.innerHTML = html;
        document.body.appendChild(div);
    } catch (e) {
        alert('加载凭证详情失败');
    }
}

function closeDetailModal() {
    const el = document.getElementById('detail-modal-container');
    if (el) el.remove();
}

async function showTaxDetail() {
    try {
        const r = await fetch('/api/tax/summary');
        const tax = await r.json();
        if (tax.error) { alert(tax.error); return; }

        let rows = '';
        for (const d of (tax.details || [])) {
            rows += `<tr><td>${esc(d.name)}</td><td class="num">${formatNum(d.balance)}</td></tr>`;
        }
        if (!rows) {
            rows = '<tr><td colspan="2" style="text-align:center;color:var(--dim);">暂无税费数据</td></tr>';
        }

        let html = `<div class="detail-modal" onclick="if(event.target===this)closeDetailModal()">
            <div class="detail-modal-content">
                <div class="detail-modal-header">
                    <h3>应交税费明细</h3>
                    <button class="detail-modal-close" onclick="closeDetailModal()">×</button>
                </div>
                <table class="dp-table">
                    <thead><tr><th>税种</th><th>应交金额</th></tr></thead>
                    <tbody>
                        ${rows}
                        <tr class="dp-total"><td>合计</td><td class="num">${formatNum(tax.total_tax || 0)}</td></tr>
                    </tbody>
                </table>
                <div style="margin-top:12px;font-size:11px;color:var(--dim);">数据来源：应交税费科目（2221）已过账余额</div>
            </div>
        </div>`;

        const div = document.createElement('div');
        div.id = 'detail-modal-container';
        div.innerHTML = html;
        document.body.appendChild(div);
    } catch (e) {
        alert('加载税费详情失败');
    }
}

// ===== Accounts =====
async function loadAccountList() {
    const container = document.getElementById('data-panel-content');
    container.innerHTML = '<div class="dp-loading">加载中...</div>';

    try {
        const r = await fetch('/api/accounts');
        const data = await r.json();
        if (data.error) { container.innerHTML = `<div class="dp-empty">${data.error}</div>`; return; }

        let html = `<div class="dp-filters">
            <select onchange="loadAccountsByCategory(this.value)">
                <option value="">全部类别</option>
                <option value="asset">资产</option>
                <option value="liability">负债</option>
                <option value="equity">所有者权益</option>
                <option value="cost">成本</option>
                <option value="income">收入</option>
                <option value="expense">费用</option>
            </select>
            <span class="dp-count">${data.count} 个科目</span>
        </div>`;

        html += '<div class="dp-list dp-list-compact">';
        for (const a of data.accounts || []) {
            const indent = a.parent_code ? 'dp-indent' : '';
            html += `<div class="dp-item ${indent}">
                <span class="dp-code">${a.code}</span>
                <span class="dp-name">${esc(a.name)}</span>
                <span class="dp-cat">${categoryLabel(a.category)}</span>
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="dp-empty">加载失败</div>';
    }
}

async function loadAccountsByCategory(category) {
    const container = document.getElementById('data-panel-content');
    const params = category ? `?category=${category}` : '';
    try {
        const r = await fetch(`/api/accounts${params}`);
        const data = await r.json();
        // Re-render with same structure
        let html = `<div class="dp-filters">
            <select onchange="loadAccountsByCategory(this.value)">
                <option value="" ${!category?'selected':''}>全部类别</option>
                <option value="asset" ${category==='asset'?'selected':''}>资产</option>
                <option value="liability" ${category==='liability'?'selected':''}>负债</option>
                <option value="equity" ${category==='equity'?'selected':''}>所有者权益</option>
                <option value="cost" ${category==='cost'?'selected':''}>成本</option>
                <option value="income" ${category==='income'?'selected':''}>收入</option>
                <option value="expense" ${category==='expense'?'selected':''}>费用</option>
            </select>
            <span class="dp-count">${data.count} 个科目</span>
        </div>`;
        html += '<div class="dp-list dp-list-compact">';
        for (const a of data.accounts || []) {
            const indent = a.parent_code ? 'dp-indent' : '';
            html += `<div class="dp-item ${indent}">
                <span class="dp-code">${a.code}</span>
                <span class="dp-name">${esc(a.name)}</span>
                <span class="dp-cat">${categoryLabel(a.category)}</span>
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {}
}

function categoryLabel(cat) {
    const map = { asset:'资产', liability:'负债', equity:'权益', cost:'成本', income:'收入', expense:'费用' };
    return map[cat] || cat;
}

// ===== Ledger (Trial Balance) =====
async function loadLedgerBalance() {
    const container = document.getElementById('data-panel-content');
    container.innerHTML = '<div class="dp-loading">加载中...</div>';

    try {
        const r = await fetch('/api/ledger/balance-sheet');
        const data = await r.json();
        if (data.error) { container.innerHTML = `<div class="dp-empty">${data.error}</div>`; return; }
        if (!data.accounts.length) { container.innerHTML = '<div class="dp-empty">暂无账簿数据（需要有已过账的凭证）</div>'; return; }

        let html = `<div class="dp-filters"><span class="dp-count">${data.count} 个有发生额的科目</span></div>`;
        if (data.degraded && data.degraded_reasons && data.degraded_reasons.length) {
            html += '<div class="dp-degraded">';
            for (const reason of data.degraded_reasons) {
                html += `<div class="dp-degraded-item">⚡ ${esc(reason)}</div>`;
            }
            html += '</div>';
        }
        html += '<div class="dp-list">';
        for (const a of data.accounts) {
            const balClass = a.balance >= 0 ? '' : 'dp-expense';
            html += `<div class="dp-item dp-ledger-row" onclick="showAccountDetail('${a.code}')">
                <span class="dp-name">${esc(a.name)}</span>
                <span class="dp-balance num ${balClass}">${formatNum(a.balance)}</span>
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="dp-empty">加载失败</div>';
    }
}

async function showAccountDetail(code) {
    try {
        const r = await fetch(`/api/ledger/account-detail/${code}`);
        const data = await r.json();
        if (data.error) { alert(data.error); return; }

        const periodLabel = data.period_id ? `期间: ${data.period_id}` : '全部期间';
        let degradedHtml = '';
        if (data.degraded && data.degraded_reasons && data.degraded_reasons.length) {
            degradedHtml = '<div class="dp-degraded" style="margin-bottom:10px;">';
            for (const reason of data.degraded_reasons) {
                degradedHtml += `<div class="dp-degraded-item">⚡ ${esc(reason)}</div>`;
            }
            degradedHtml += '</div>';
        }
        let html = `<div class="detail-modal" onclick="if(event.target===this)closeDetailModal()">
            <div class="detail-modal-content">
                <div class="detail-modal-header">
                    <h3>📒 ${esc(data.name)}</h3>
                    <button class="detail-modal-close" onclick="closeDetailModal()">×</button>
                </div>
                <div style="font-size:11px;color:var(--dim);margin-bottom:12px;">${data.code} · ${periodLabel} · 余额方向: ${data.direction === 'debit' ? '借' : '贷'}</div>
                ${degradedHtml}
                <table class="dp-table">
                    <tbody>
                        <tr><td>期初余额</td><td class="num">${formatNum(data.opening_balance)}</td></tr>
                        <tr><td>本期借方</td><td class="num">${formatNum(data.period_debit)}</td></tr>
                        <tr><td>本期贷方</td><td class="num">${formatNum(data.period_credit)}</td></tr>
                        <tr class="dp-total"><td>期末余额</td><td class="num">${formatNum(data.closing_balance)}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>`;

        const div = document.createElement('div');
        div.id = 'detail-modal-container';
        div.innerHTML = html;
        document.body.appendChild(div);
    } catch (e) {
        alert('加载科目明细失败');
    }
}

// ===== Auxiliary Items =====
async function loadAuxItems() {
    const container = document.getElementById('data-panel-content');
    container.innerHTML = '<div class="dp-loading">加载中...</div>';

    try {
        const r = await fetch('/api/aux-items');
        const data = await r.json();
        if (data.error) { container.innerHTML = `<div class="dp-empty">${data.error}</div>`; return; }
        if (!data.items.length) { container.innerHTML = '<div class="dp-empty">暂无辅助核算项</div>'; return; }

        let html = '<div class="dp-list dp-list-compact">';
        let currentType = '';
        for (const item of data.items) {
            if (item.type !== currentType) {
                currentType = item.type;
                html += `<div class="dp-group-header">${esc(currentType)}</div>`;
            }
            html += `<div class="dp-item">
                <span class="dp-code">${item.code || ''}</span>
                <span class="dp-name">${esc(item.name)}</span>
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="dp-empty">加载失败</div>';
    }
}

// Reports are in data-reports.js
