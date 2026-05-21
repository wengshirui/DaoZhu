/**
 * AccoBot — Business Module
 * Account management, todos, data overview, settings, gateway config.
 */

// ===== Companies =====
async function loadCompanies() {
    try {
        const r = await fetch('/api/companies'); const d = await r.json();
        const sel = document.getElementById('current-company');
        sel.innerHTML = '<option value="">未选择账套</option>';
        (d.companies || []).forEach(c => {
            const o = document.createElement('option'); o.value = c.id; o.textContent = c.name;
            if (c.id === d.current) o.selected = true;
            sel.appendChild(o);
        });
    } catch(e) {}
}

async function switchCompany(id) {
    if (!id) return;
    await fetch('/api/companies/switch', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({company_id: id}) });
    loadTodos();
    loadDataOverview();
    if (ws) ws.close(); connectWebSocket();
}

async function openCompanyFolder() {
    const id = document.getElementById('current-company').value;
    if (!id) { alert('请先选择账套'); return; }
    const r = await fetch('/api/companies/open-folder', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({company_id:id}) });
    const d = await r.json(); if (!d.success) alert(d.error);
}

function showNewCompany() { document.getElementById('company-modal').style.display = 'flex'; }
function closeCompanyModal() { document.getElementById('company-modal').style.display = 'none'; }

async function createCompany() {
    const name = document.getElementById('company-name').value.trim();
    const msg = document.getElementById('company-message');
    if (!name) { msg.textContent = '请输入公司名称'; msg.className = 'form-msg error'; return; }
    msg.textContent = '创建中...'; msg.className = 'form-msg';
    const r = await fetch('/api/companies/create', { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name, industry: document.getElementById('company-industry').value.trim(),
            taxpayer_type: document.getElementById('company-taxpayer').value,
            accounting_standard: document.getElementById('company-standard').value }) });
    const d = await r.json();
    if (!d.success) { msg.textContent = d.error; msg.className = 'form-msg error'; return; }
    msg.textContent = `✅ 已初始化 ${d.company.accounts_initialized} 个科目`; msg.className = 'form-msg success';
    setTimeout(() => { closeCompanyModal(); loadCompanies(); loadTodos(); document.getElementById('company-name').value = ''; }, 1200);
}

// ===== Delete Company (two-step) =====
let deleteStep = 0, deleteId = '', deleteName = '';

function deleteCompanyStep1() {
    const sel = document.getElementById('current-company');
    deleteId = sel.value;
    if (!deleteId) { alert('请先选择账套'); return; }
    deleteName = sel.options[sel.selectedIndex].text;
    deleteStep = 1;
    document.getElementById('delete-warning-text').textContent = `确定要删除「${deleteName}」的账套吗？所有数据将被删除。`;
    document.getElementById('delete-confirm-group').style.display = 'none';
    document.getElementById('delete-message').textContent = '';
    document.getElementById('delete-modal').style.display = 'flex';
}

function deleteCompanyNext() {
    if (deleteStep === 1) {
        deleteStep = 2;
        document.getElementById('delete-warning-text').textContent = `⚠️ 不可恢复！请输入「${deleteName}」确认。`;
        document.getElementById('delete-confirm-group').style.display = 'block';
        document.getElementById('delete-confirm-name').value = '';
        document.getElementById('delete-confirm-name').focus();
    } else if (deleteStep === 2) {
        const input = document.getElementById('delete-confirm-name').value.trim();
        const msg = document.getElementById('delete-message');
        if (input !== deleteName) { msg.textContent = '名称不匹配'; msg.className = 'form-msg error'; return; }
        executeDelete();
    }
}

async function executeDelete() {
    const msg = document.getElementById('delete-message');
    msg.textContent = '删除中...'; msg.className = 'form-msg';
    const r = await fetch('/api/companies/delete', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({company_id:deleteId, confirm_name:deleteName}) });
    const d = await r.json();
    if (!d.success) { msg.textContent = d.error; msg.className = 'form-msg error'; return; }
    msg.textContent = '✅ 已删除'; msg.className = 'form-msg success';
    setTimeout(() => { closeDeleteModal(); loadCompanies(); loadTodos(); }, 1000);
}

function closeDeleteModal() { document.getElementById('delete-modal').style.display = 'none'; deleteStep = 0; }

// ===== Todos =====
async function loadTodos() {
    try { const r = await fetch('/api/todos'); renderTodos(await r.json()); }
    catch(e) { renderTodos({accounting:[],tax:[],business:[],social:[]}); }
}

function renderTodos(data) {
    const cats = { accounting:'todo-accounting', tax:'todo-tax', business:'todo-business', social:'todo-social' };
    for (const [key, elId] of Object.entries(cats)) {
        const items = data[key] || [];
        const badge = document.getElementById(`badge-${key}`);
        badge.textContent = items.length;
        badge.className = items.length > 0 ? 'badge active' : 'badge';
        const container = document.getElementById(elId);
        container.innerHTML = items.length === 0 ? '<div class="todo-item" style="font-style:italic">暂无</div>'
            : items.map(i => `<div class="todo-item">${i.title}${i.due_date ? `<span class="due ${i.overdue?'overdue':''}">${i.due_date}</span>` : ''}</div>`).join('');
    }
}

function toggleTodo(el) { const items = el.nextElementSibling; if (items) items.classList.toggle('show'); }

// ===== Data Overview =====
async function loadDataOverview() {
    const container = document.getElementById('data-display');
    try {
        const r = await fetch('/api/data/overview');
        const data = await r.json();
        if (data.error) { container.innerHTML = `<p>${data.error}</p>`; return; }
        let html = '<table class="data-table">';
        html += '<tr><td>💰 银行存款</td><td class="num">' + formatNum(data.bank_balance) + '</td></tr>';
        html += '<tr><td>📥 应收账款</td><td class="num">' + formatNum(data.receivable) + '</td></tr>';
        html += '<tr><td>📤 应付账款</td><td class="num">' + formatNum(data.payable) + '</td></tr>';
        html += '<tr><td>📊 本月收入</td><td class="num">' + formatNum(data.monthly_income) + '</td></tr>';
        html += '<tr><td>📉 本月支出</td><td class="num">' + formatNum(data.monthly_expense) + '</td></tr>';
        html += '<tr><td>📝 待审凭证</td><td class="num">' + (data.draft_count || 0) + ' 张</td></tr>';
        html += '</table>';
        container.innerHTML = html;
    } catch (e) { container.innerHTML = '<p>加载数据失败</p>'; }
}

function formatNum(n) {
    if (n === undefined || n === null) return '-';
    return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' 元';
}

// ===== Settings =====
function showSettings() { document.getElementById('settings-modal').style.display = 'flex'; }
function closeSettings() { document.getElementById('settings-modal').style.display = 'none'; }

function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tab-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tab}`).style.display = 'block';
    event.target.classList.add('active');
    if (tab === 'gateway') loadGatewayConfig();
    if (tab === 'mcp') loadMcpStatus();
}

function onProviderChange() {
    const p = document.getElementById('cfg-provider').value;
    document.getElementById('cfg-baseurl-group').style.display = p === 'other' ? 'block' : 'none';
    document.getElementById('cfg-model-group').style.display = p === 'other' ? 'block' : 'none';
    const hint = document.getElementById('cfg-apikey-hint');
    if (p === 'deepseek') hint.innerHTML = '获取：<a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek 控制台</a>';
    else if (p === 'openai') hint.innerHTML = '获取：<a href="https://platform.openai.com/api-keys" target="_blank">OpenAI 控制台</a>';
    else hint.innerHTML = '填写你的 API Key';
}

async function saveSettings() {
    const provider = document.getElementById('cfg-provider').value;
    const apiKey = document.getElementById('cfg-apikey').value.trim();
    const msg = document.getElementById('cfg-message');
    if (!apiKey) { msg.textContent = '请输入 API Key'; msg.className = 'form-msg error'; return; }
    msg.textContent = '保存中...'; msg.className = 'form-msg';
    await fetch('/api/config/apikey', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({api_key:apiKey, provider}) });
    const modelCfg = provider === 'deepseek' ? {provider:'deepseek', base_url:'https://api.deepseek.com/v1', model_name:'deepseek-chat'}
        : provider === 'openai' ? {provider:'openai', base_url:null, model_name:'gpt-4o'}
        : {provider:'custom', base_url: document.getElementById('cfg-baseurl').value.trim(), model_name: document.getElementById('cfg-model').value.trim() || 'gpt-4o'};
    await fetch('/api/config/model', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(modelCfg) });
    msg.textContent = '✅ 已保存'; msg.className = 'form-msg success';
    setTimeout(() => { closeSettings(); configError = false; if (ws) ws.close(); connectWebSocket(); }, 800);
}

async function checkAndShowSettings() {
    try { const r = await fetch('/api/status'); const d = await r.json(); if (!d.has_api_key) showSettings(); } catch(e) {}
}

async function fetchStatus() {
    try { const r = await fetch('/api/status'); const d = await r.json(); document.getElementById('version').textContent = `v${d.version}`; } catch(e) {}
}

// ===== Gateway Config =====
async function loadGatewayConfig() {
    try {
        const r = await fetch('/api/config/gateway');
        const data = await r.json();
        if (data.wecom) { document.getElementById('gw-wecom-corpid').value = data.wecom.corp_id || ''; document.getElementById('gw-wecom-agentid').value = data.wecom.agent_id || ''; document.getElementById('gw-wecom-secret').value = data.wecom.secret ? '••••••' : ''; }
        if (data.dingtalk) { document.getElementById('gw-dingtalk-appkey').value = data.dingtalk.app_key || ''; document.getElementById('gw-dingtalk-secret').value = data.dingtalk.secret ? '••••••' : ''; }
        if (data.feishu) { document.getElementById('gw-feishu-appid').value = data.feishu.app_id || ''; document.getElementById('gw-feishu-secret').value = data.feishu.secret ? '••••••' : ''; }
    } catch (e) { /* ignore */ }
}

async function saveGatewayConfig() {
    const msg = document.getElementById('gw-message');
    const config = { wecom: { corp_id: document.getElementById('gw-wecom-corpid').value.trim(), agent_id: document.getElementById('gw-wecom-agentid').value.trim(), secret: document.getElementById('gw-wecom-secret').value.trim() },
        dingtalk: { app_key: document.getElementById('gw-dingtalk-appkey').value.trim(), secret: document.getElementById('gw-dingtalk-secret').value.trim() },
        feishu: { app_id: document.getElementById('gw-feishu-appid').value.trim(), secret: document.getElementById('gw-feishu-secret').value.trim() } };
    if (config.wecom.secret === '••••••') delete config.wecom.secret;
    if (config.dingtalk.secret === '••••••') delete config.dingtalk.secret;
    if (config.feishu.secret === '••••••') delete config.feishu.secret;
    try {
        const r = await fetch('/api/config/gateway', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(config) });
        const data = await r.json();
        msg.textContent = data.success ? '✅ 平台配置已保存' : '❌ ' + (data.error || '保存失败');
        msg.className = data.success ? 'form-msg success' : 'form-msg error';
    } catch (e) { msg.textContent = '❌ 网络错误'; msg.className = 'form-msg error'; }
}
