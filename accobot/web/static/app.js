// AccoBot Web UI — Three-column layout

let ws = null;
let isStreaming = false;
let currentAssistantMsg = null;
let configError = false;

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    fetchStatus();
    checkAndShowSettings().then(() => { connectWebSocket(); });
    loadCompanies();
    loadTodos();
});

// ===== WebSocket =====
function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/chat`);
    ws.onopen = () => {};
    ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
    ws.onclose = () => { if (!configError) setTimeout(connectWebSocket, 3000); };
    ws.onerror = () => {};
}

function handleMessage(data) {
    switch (data.type) {
        case 'token':
            if (!currentAssistantMsg) currentAssistantMsg = addMsg('assistant', '');
            appendToMsg(currentAssistantMsg, data.content);
            break;
        case 'tool_call': addToolCall(data.name, data.args); break;
        case 'tool_result': addToolResult(data.name, data.result); break;
        case 'done': finishStreaming(); break;
        case 'error':
            if (data.content && data.content.includes('API Key')) configError = true;
            addMsg('assistant', `⚠️ ${data.content}`);
            finishStreaming();
            break;
    }
}

// ===== Chat =====
function sendMessage() {
    const input = document.getElementById('input');
    const msg = input.value.trim();
    if (!msg || isStreaming || !ws || ws.readyState !== WebSocket.OPEN) return;
    addMsg('user', msg);
    input.value = ''; autoResize(input);
    isStreaming = true; currentAssistantMsg = null;
    document.getElementById('btn-send').disabled = true;
    ws.send(JSON.stringify({ message: msg }));
    // Update history title
    const title = document.querySelector('#current-chat .history-title');
    if (title && title.textContent === '新对话') title.textContent = msg.slice(0, 20) + (msg.length > 20 ? '...' : '');
}

function finishStreaming() { isStreaming = false; currentAssistantMsg = null; document.getElementById('btn-send').disabled = false; }

function addMsg(role, content) {
    const el = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `msg msg-${role}`;
    div.innerHTML = `<p>${formatContent(content)}</p>`;
    el.appendChild(div); el.scrollTop = el.scrollHeight;
    return div.querySelector('p');
}

function appendToMsg(el, text) {
    if (!el) return;
    el.dataset.raw = (el.dataset.raw || '') + text;
    el.innerHTML = formatContent(el.dataset.raw);
    el.closest('.chat-messages').scrollTop = el.closest('.chat-messages').scrollHeight;
}

function addToolCall(name, args) {
    const el = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'msg msg-assistant';
    div.innerHTML = `<div class="tool-call"><div class="tool-call-header">🔧 ${esc(name)}</div><div class="tool-call-args">${esc(JSON.stringify(args, null, 2))}</div></div>`;
    el.appendChild(div); el.scrollTop = el.scrollHeight;
}

function addToolResult(name, result) {
    const el = document.getElementById('messages');
    let display = result;
    try { const p = JSON.parse(result); display = p.message || JSON.stringify(p, null, 2); } catch(e) {}
    const div = document.createElement('div');
    div.className = 'msg msg-assistant';
    div.innerHTML = `<div class="tool-result">✅ ${esc(name)}: ${esc(display)}</div>`;
    el.appendChild(div); el.scrollTop = el.scrollHeight;
}

function newChat() {
    document.getElementById('messages').innerHTML = '<div class="msg msg-system"><p>👋 新对话已开始。</p></div>';
    configError = false;
    if (ws) ws.close();
    connectWebSocket();
    // Update history
    const title = document.querySelector('#current-chat .history-title');
    if (title) title.textContent = '新对话';
}

function formatContent(t) {
    if (!t) return '';
    let h = esc(t);
    h = h.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/`(.*?)`/g, '<code>$1</code>');
    h = h.replace(/\n/g, '<br>');
    return h;
}

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
function handleKeyDown(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
function autoResize(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px'; }

// ===== Panel Toggle =====
function togglePanel(side) {
    const panel = document.getElementById(`panel-${side}`);
    const expandBtn = document.getElementById(`expand-${side}`);
    panel.classList.toggle('collapsed');
    if (panel.classList.contains('collapsed')) {
        expandBtn.classList.add('visible');
    } else {
        expandBtn.classList.remove('visible');
    }
}

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
    try {
        const r = await fetch('/api/todos'); const d = await r.json();
        renderTodos(d);
    } catch(e) { renderTodos({accounting:[],tax:[],business:[],social:[]}); }
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

// ===== Settings =====
function showSettings() { document.getElementById('settings-modal').style.display = 'flex'; }
function closeSettings() { document.getElementById('settings-modal').style.display = 'none'; }

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

// ===== File Upload =====
function triggerFileUpload() {
    document.getElementById('file-input').click();
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
    event.target.value = ''; // Reset for re-upload
}

function hideUploadZone() {
    document.getElementById('upload-zone').style.display = 'none';
}

async function uploadFiles(files) {
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        addMsg('system', `📎 正在上传 ${file.name}...`);

        try {
            const response = await fetch('/api/upload/file', {
                method: 'POST',
                body: formData,
            });
            const result = await response.json();
            if (result.success) {
                addMsg('system', `✅ ${result.message}（${(result.size / 1024).toFixed(1)} KB）`);
            } else {
                addMsg('system', `❌ 上传失败：${result.error}`);
            }
        } catch (e) {
            addMsg('system', `❌ 上传出错：${e.message}`);
        }
    }
}

// Drag and drop support
(function setupDragDrop() {
    const center = document.querySelector('.panel-center');
    if (!center) return;

    center.addEventListener('dragover', (e) => {
        e.preventDefault();
        const zone = document.getElementById('upload-zone');
        zone.style.display = 'flex';
        zone.classList.add('dragover');
    });

    center.addEventListener('dragleave', (e) => {
        if (!center.contains(e.relatedTarget)) {
            const zone = document.getElementById('upload-zone');
            zone.classList.remove('dragover');
        }
    });

    center.addEventListener('drop', (e) => {
        e.preventDefault();
        const zone = document.getElementById('upload-zone');
        zone.style.display = 'none';
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    });
})();

// ===== Chat History =====
let currentSessionId = null;
let chatSessions = [];

async function loadChatSessions() {
    try {
        const r = await fetch('/api/chat/sessions');
        const data = await r.json();
        chatSessions = data.sessions || [];
        renderChatHistory();
    } catch (e) { /* ignore */ }
}

function renderChatHistory() {
    const container = document.getElementById('chat-history');
    if (!chatSessions.length) {
        container.innerHTML = '<div class="history-group"><div class="history-date">暂无历史对话</div></div>';
        return;
    }

    // Group by date
    const groups = {};
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();

    for (const s of chatSessions) {
        const d = new Date(s.updated_at * 1000).toDateString();
        let label = d;
        if (d === today) label = '今天';
        else if (d === yesterday) label = '昨天';
        else label = new Date(s.updated_at * 1000).toLocaleDateString('zh-CN');
        if (!groups[label]) groups[label] = [];
        groups[label].push(s);
    }

    let html = '';
    for (const [label, sessions] of Object.entries(groups)) {
        html += `<div class="history-group"><div class="history-date">${label}</div>`;
        for (const s of sessions) {
            const active = s.id === currentSessionId ? ' active' : '';
            html += `<div class="history-item${active}" onclick="switchSession('${s.id}')">
                <span class="history-title">${esc(s.title)}</span>
            </div>`;
        }
        html += '</div>';
    }
    container.innerHTML = html;
}

async function switchSession(sessionId) {
    currentSessionId = sessionId;
    renderChatHistory();

    // Load messages
    try {
        const r = await fetch(`/api/chat/sessions/${sessionId}/messages`);
        const data = await r.json();
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = '';
        for (const msg of (data.messages || [])) {
            if (msg.role === 'user' || msg.role === 'assistant') {
                addMsg(msg.role, msg.content);
            }
        }
    } catch (e) { /* ignore */ }
}

async function createNewSession() {
    try {
        const r = await fetch('/api/chat/sessions', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await r.json();
        if (data.success) {
            currentSessionId = data.session.id;
            await loadChatSessions();
        }
    } catch (e) { /* ignore */ }
    return currentSessionId;
}

// Override newChat to use sessions
const _originalNewChat = newChat;
newChat = async function() {
    document.getElementById('messages').innerHTML = `<div class="msg msg-system"><p>👋 新对话已开始。有什么可以帮你的？</p></div>`;
    currentSessionId = null;
    await createNewSession();
};

// Save messages to history after each turn
async function saveMessageToHistory(role, content) {
    if (!currentSessionId) {
        await createNewSession();
    }
    try {
        await fetch(`/api/chat/sessions/${currentSessionId}/messages`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ session_id: currentSessionId, role, content }),
        });
        // Auto-title from first user message
        if (role === 'user' && chatSessions.length > 0) {
            const session = chatSessions.find(s => s.id === currentSessionId);
            if (session && session.title === '新对话') {
                const title = content.slice(0, 20) + (content.length > 20 ? '...' : '');
                await fetch(`/api/chat/sessions/${currentSessionId}`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title }),
                });
                loadChatSessions();
            }
        }
    } catch (e) { /* ignore */ }
}

// Load sessions on startup
loadChatSessions();

// ===== Data Overview =====
async function loadDataOverview() {
    const container = document.getElementById('data-display');
    try {
        const r = await fetch('/api/data/overview');
        const data = await r.json();
        if (data.error) {
            container.innerHTML = `<p>${data.error}</p>`;
            return;
        }
        let html = '<table class="data-table">';
        html += '<tr><td>💰 银行存款</td><td class="num">' + formatNum(data.bank_balance) + '</td></tr>';
        html += '<tr><td>📥 应收账款</td><td class="num">' + formatNum(data.receivable) + '</td></tr>';
        html += '<tr><td>📤 应付账款</td><td class="num">' + formatNum(data.payable) + '</td></tr>';
        html += '<tr><td>📊 本月收入</td><td class="num">' + formatNum(data.monthly_income) + '</td></tr>';
        html += '<tr><td>📉 本月支出</td><td class="num">' + formatNum(data.monthly_expense) + '</td></tr>';
        html += '<tr><td>📝 待审凭证</td><td class="num">' + (data.draft_count || 0) + ' 张</td></tr>';
        html += '</table>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<p>加载数据失败</p>';
    }
}

function formatNum(n) {
    if (n === undefined || n === null) return '-';
    return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' 元';
}

// Load data overview on startup if company is selected
(async function() {
    const sel = document.getElementById('current-company');
    if (sel && sel.value) loadDataOverview();
})();

// ===== Settings Tabs & Gateway Config =====
function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tab-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tab}`).style.display = 'block';
    event.target.classList.add('active');
    if (tab === 'gateway') loadGatewayConfig();
}

async function loadGatewayConfig() {
    try {
        const r = await fetch('/api/config/gateway');
        const data = await r.json();
        if (data.wecom) {
            document.getElementById('gw-wecom-corpid').value = data.wecom.corp_id || '';
            document.getElementById('gw-wecom-agentid').value = data.wecom.agent_id || '';
            document.getElementById('gw-wecom-secret').value = data.wecom.secret ? '••••••' : '';
        }
        if (data.dingtalk) {
            document.getElementById('gw-dingtalk-appkey').value = data.dingtalk.app_key || '';
            document.getElementById('gw-dingtalk-secret').value = data.dingtalk.secret ? '••••••' : '';
        }
        if (data.feishu) {
            document.getElementById('gw-feishu-appid').value = data.feishu.app_id || '';
            document.getElementById('gw-feishu-secret').value = data.feishu.secret ? '••••••' : '';
        }
    } catch (e) { /* ignore */ }
}

async function saveGatewayConfig() {
    const msg = document.getElementById('gw-message');
    const config = {
        wecom: {
            corp_id: document.getElementById('gw-wecom-corpid').value.trim(),
            agent_id: document.getElementById('gw-wecom-agentid').value.trim(),
            secret: document.getElementById('gw-wecom-secret').value.trim(),
        },
        dingtalk: {
            app_key: document.getElementById('gw-dingtalk-appkey').value.trim(),
            secret: document.getElementById('gw-dingtalk-secret').value.trim(),
        },
        feishu: {
            app_id: document.getElementById('gw-feishu-appid').value.trim(),
            secret: document.getElementById('gw-feishu-secret').value.trim(),
        },
    };

    // Don't send masked values
    if (config.wecom.secret === '••••••') delete config.wecom.secret;
    if (config.dingtalk.secret === '••••••') delete config.dingtalk.secret;
    if (config.feishu.secret === '••••••') delete config.feishu.secret;

    try {
        const r = await fetch('/api/config/gateway', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config),
        });
        const data = await r.json();
        if (data.success) {
            msg.textContent = '✅ 平台配置已保存';
            msg.className = 'form-msg success';
        } else {
            msg.textContent = '❌ ' + (data.error || '保存失败');
            msg.className = 'form-msg error';
        }
    } catch (e) {
        msg.textContent = '❌ 网络错误';
        msg.className = 'form-msg error';
    }
}
