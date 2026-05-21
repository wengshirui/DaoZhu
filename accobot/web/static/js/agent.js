/**
 * AccoBot — Agent Module
 * MCP server management, Skills display, operation log, agent status indicator.
 */

// ===== Agent Status =====
function showAgentStatus(text) {
    const toolbar = document.getElementById('chat-toolbar');
    document.getElementById('status-text').textContent = text;
    toolbar.style.display = 'flex';
}

function hideAgentStatus() {
    document.getElementById('chat-toolbar').style.display = 'none';
}

// ===== Operation Log =====
let opLogEntries = [];

function addOpLogEntry(name, status, detail) {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
    opLogEntries.unshift({ time, name, status, detail });
    if (opLogEntries.length > 50) opLogEntries.pop();
    renderOpLog();
}

function renderOpLog() {
    const container = document.getElementById('op-log-list');
    if (!opLogEntries.length) { container.innerHTML = '<div class="op-log-empty">暂无操作记录</div>'; return; }
    container.innerHTML = opLogEntries.map(e => {
        const statusClass = e.status === 'ok' ? 'ok' : e.status === 'err' ? 'err' : '';
        const statusIcon = e.status === 'ok' ? '✓' : e.status === 'err' ? '✗' : '⋯';
        return `<div class="op-log-entry"><span class="op-time">${e.time}</span><span class="op-name">${e.name}</span><span class="op-status ${statusClass}">${statusIcon}</span></div>`;
    }).join('');
}

// ===== Agent Capabilities Display =====
async function loadCapabilities() {
    // MCP servers
    try {
        const r = await fetch('/api/mcp/status');
        const data = await r.json();
        const container = document.getElementById('cap-mcp-list');
        const servers = data.servers || [];
        if (!servers.length) { container.innerHTML = '<div class="cap-item" style="opacity:0.5">未配置</div>'; }
        else { container.innerHTML = servers.map(s => { const dotClass = s.connected ? 'connected' : 'disconnected'; const label = s.connected ? `${s.name} (${s.tool_count}工具)` : `${s.name} (未连接)`; return `<div class="cap-item"><span class="cap-dot ${dotClass}"></span>${label}</div>`; }).join(''); }
    } catch (e) { document.getElementById('cap-mcp-list').innerHTML = '<div class="cap-item" style="opacity:0.5">加载失败</div>'; }

    // Skills
    try {
        const r = await fetch('/api/skills/list');
        const data = await r.json();
        const container = document.getElementById('cap-skill-list');
        const skills = data.skills || [];
        if (!skills.length) { container.innerHTML = '<div class="cap-item" style="opacity:0.5">暂无 Skill</div>'; }
        else { container.innerHTML = skills.map(s => `<div class="cap-item"><span class="cap-dot skill"></span>${s.name}</div>`).join(''); }
    } catch (e) { document.getElementById('cap-skill-list').innerHTML = '<div class="cap-item" style="opacity:0.5">加载失败</div>'; }
}

// ===== MCP Management (Settings Tab) =====
async function loadMcpStatus() {
    const container = document.getElementById('mcp-server-list');
    try {
        const r = await fetch('/api/mcp/status');
        const data = await r.json();
        const servers = data.servers || [];
        if (!servers.length) { container.innerHTML = '<p class="data-placeholder">未配置 MCP 服务器。</p>'; return; }
        let html = '<table class="data-table" style="width:100%">';
        html += '<tr style="border-bottom:1px solid var(--border)"><td><b>服务器</b></td><td><b>状态</b></td><td><b>工具</b></td><td></td></tr>';
        for (const s of servers) {
            const status = s.connected ? '🟢 已连接' : (s.enabled ? '🟡 未连接' : '⚪ 已禁用');
            const toggleLabel = s.enabled ? '禁用' : '启用';
            const isPlaywright = s.name === 'playwright';
            html += `<tr><td>${s.name}</td><td>${status}</td><td>${s.tool_count} 个</td><td>
                <button class="btn-sm" onclick="reconnectMcp('${s.name}')">重连</button>
                <button class="btn-sm" onclick="toggleMcp('${s.name}', ${!s.enabled})">${toggleLabel}</button>
                ${isPlaywright ? '' : `<button class="btn-sm btn-danger-sm" onclick="removeMcp('${s.name}')">删除</button>`}
            </td></tr>`;
        }
        html += '</table>';
        container.innerHTML = html;
    } catch (e) { container.innerHTML = '<p class="data-placeholder">加载 MCP 状态失败</p>'; }
}

async function reconnectMcp(name) {
    const msg = document.getElementById('mcp-message');
    msg.textContent = '正在重连...'; msg.className = 'form-msg';
    try {
        const r = await fetch('/api/mcp/reconnect', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ name }) });
        const data = await r.json();
        msg.textContent = data.success ? '✅ ' + data.message : '❌ ' + (data.error || '重连失败');
        msg.className = data.success ? 'form-msg success' : 'form-msg error';
        loadMcpStatus(); loadCapabilities();
    } catch (e) { msg.textContent = '❌ 网络错误'; msg.className = 'form-msg error'; }
}

function onMcpTypeChange() {
    const type = document.getElementById('mcp-add-type').value;
    document.getElementById('mcp-cmd-group').style.display = type === 'stdio' ? 'block' : 'none';
    document.getElementById('mcp-args-group').style.display = type === 'stdio' ? 'block' : 'none';
    document.getElementById('mcp-url-group').style.display = type === 'http' ? 'block' : 'none';
}

async function addMcpServer() {
    const msg = document.getElementById('mcp-message');
    const name = document.getElementById('mcp-add-name').value.trim();
    const type = document.getElementById('mcp-add-type').value;
    if (!name) { msg.textContent = '❌ 请输入服务器名称'; msg.className = 'form-msg error'; return; }
    const body = { name, type };
    if (type === 'http') body.url = document.getElementById('mcp-add-url').value.trim();
    else { body.command = document.getElementById('mcp-add-command').value.trim(); body.args = document.getElementById('mcp-add-args').value.trim(); }
    try {
        const r = await fetch('/api/mcp/add', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
        const data = await r.json();
        msg.textContent = data.success ? '✅ ' + data.message : '❌ ' + data.error;
        msg.className = data.success ? 'form-msg success' : 'form-msg error';
        if (data.success) { document.getElementById('mcp-add-name').value = ''; document.getElementById('mcp-add-command').value = ''; document.getElementById('mcp-add-args').value = ''; document.getElementById('mcp-add-url').value = ''; loadMcpStatus(); }
    } catch (e) { msg.textContent = '❌ 网络错误'; msg.className = 'form-msg error'; }
}

async function toggleMcp(name, enabled) {
    try {
        const r = await fetch('/api/mcp/toggle', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, enabled }) });
        const data = await r.json();
        const msg = document.getElementById('mcp-message');
        msg.textContent = data.success ? '✅ ' + data.message : '❌ ' + data.error;
        msg.className = data.success ? 'form-msg success' : 'form-msg error';
        loadMcpStatus(); loadCapabilities();
    } catch (e) {}
}

async function removeMcp(name) {
    if (!confirm(`确定删除 MCP 服务器 "${name}" 吗？`)) return;
    try {
        const r = await fetch('/api/mcp/remove', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name }) });
        const data = await r.json();
        const msg = document.getElementById('mcp-message');
        msg.textContent = data.success ? '✅ ' + data.message : '❌ ' + data.error;
        msg.className = data.success ? 'form-msg success' : 'form-msg error';
        loadMcpStatus(); loadCapabilities();
    } catch (e) {}
}

// ===== Collapsible Sections =====
function toggleSection(name) {
    const content = document.getElementById(`content-${name}`);
    const arrow = document.getElementById(`arrow-${name}`);
    content.classList.toggle('collapsed');
    arrow.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
}
