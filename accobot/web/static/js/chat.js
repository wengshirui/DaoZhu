/**
 * AccoBot — Chat Module
 * WebSocket connection, message sending/receiving, streaming, history persistence.
 */

let ws = null;
let isStreaming = false;
let currentAssistantMsg = null;
let configError = false;

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
            showAgentStatus('回复中...');
            break;
        case 'tool_call':
            // Reset assistant msg so next text tokens create a new bubble AFTER tools
            currentAssistantMsg = null;
            addToolCall(data.name, data.args);
            addOpLogEntry(data.name, 'running', '');
            showAgentStatus(`调用工具: ${data.name}`);
            break;
        case 'tool_result':
            addToolResult(data.name, data.result);
            try {
                const parsed = JSON.parse(data.result);
                addOpLogEntry(data.name, parsed.error ? 'err' : 'ok', '');
            } catch(e) { addOpLogEntry(data.name, 'ok', ''); }
            showAgentStatus('分析结果...');
            break;
        case 'done':
            if (currentAssistantMsg && currentAssistantMsg.dataset.raw) {
                saveMessageToHistory('assistant', currentAssistantMsg.dataset.raw);
            }
            finishStreaming();
            // Refresh data overview after agent completes (data may have changed)
            if (typeof loadDataOverview === 'function') loadDataOverview();
            break;
        case 'error':
            if (data.content && data.content.includes('API Key')) configError = true;
            addMsg('assistant', `⚠️ ${data.content}`);
            saveMessageToHistory('assistant', data.content);
            finishStreaming();
            break;
    }
}

// ===== Send / Stop =====
function sendMessage() {
    const input = document.getElementById('input');
    const msg = input.value.trim();
    if (!msg || isStreaming || !ws || ws.readyState !== WebSocket.OPEN) return;
    addMsg('user', msg);
    saveMessageToHistory('user', msg);
    input.value = ''; autoResize(input);
    isStreaming = true; currentAssistantMsg = null;
    document.getElementById('btn-send').disabled = true;
    showAgentStatus('思考中...');
    ws.send(JSON.stringify({ message: msg }));
}

function finishStreaming() {
    isStreaming = false; currentAssistantMsg = null;
    document.getElementById('btn-send').disabled = false;
    hideAgentStatus();
}

function stopAgent() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'stop' }));
    }
    addMsg('system', '⏹ 已手动停止');
    finishStreaming();
}

// ===== Message Rendering =====
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
    div.className = 'msg msg-tool-block';
    const argsStr = JSON.stringify(args, null, 2);
    div.innerHTML = `<div class="tool-block collapsed" onclick="this.classList.toggle('collapsed')">
        <div class="tool-block-header"><span class="tool-icon">🔧</span><span class="tool-name">${esc(name)}</span><span class="tool-toggle">▶</span></div>
        <div class="tool-block-body"><pre>${esc(argsStr)}</pre></div>
    </div>`;
    el.appendChild(div); el.scrollTop = el.scrollHeight;
}

function addToolResult(name, result) {
    const el = document.getElementById('messages');
    let display = result;
    let isError = false;
    try { const p = JSON.parse(result); display = p.message || JSON.stringify(p, null, 2); isError = !!p.error; } catch(e) {}
    const div = document.createElement('div');
    div.className = 'msg msg-tool-block';
    const icon = isError ? '❌' : '✅';
    const statusClass = isError ? 'error' : 'success';
    div.innerHTML = `<div class="tool-block collapsed ${statusClass}" onclick="this.classList.toggle('collapsed')">
        <div class="tool-block-header"><span class="tool-icon">${icon}</span><span class="tool-name">${esc(name)}</span><span class="tool-toggle">▶</span></div>
        <div class="tool-block-body"><pre>${esc(display)}</pre></div>
    </div>`;
    el.appendChild(div); el.scrollTop = el.scrollHeight;
}

// ===== Chat History / Sessions =====
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
    const groups = {};
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    for (const s of chatSessions) {
        const d = new Date(s.updated_at * 1000).toDateString();
        let label = d === today ? '今天' : d === yesterday ? '昨天' : new Date(s.updated_at * 1000).toLocaleDateString('zh-CN');
        if (!groups[label]) groups[label] = [];
        groups[label].push(s);
    }
    let html = '';
    for (const [label, sessions] of Object.entries(groups)) {
        html += `<div class="history-group"><div class="history-date">${label}</div>`;
        for (const s of sessions) {
            const active = s.id === currentSessionId ? ' active' : '';
            html += `<div class="history-item${active}" onclick="switchSession('${s.id}')"><span class="history-title">${esc(s.title)}</span></div>`;
        }
        html += '</div>';
    }
    container.innerHTML = html;
}

async function switchSession(sessionId) {
    currentSessionId = sessionId;
    renderChatHistory();
    try {
        const r = await fetch(`/api/chat/sessions/${sessionId}/messages`);
        const data = await r.json();
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = '';
        const messages = data.messages || [];
        if (!messages.length) messagesDiv.innerHTML = '<div class="msg msg-system"><p>（此对话暂无消息）</p></div>';
        for (const msg of messages) {
            if (msg.role === 'user' || msg.role === 'assistant') addMsg(msg.role, msg.content);
        }
        if (ws) ws.close();
        connectWebSocket();
    } catch (e) { /* ignore */ }
}

async function createNewSession() {
    try {
        const r = await fetch('/api/chat/sessions', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        const data = await r.json();
        if (data.success) { currentSessionId = data.session.id; await loadChatSessions(); }
    } catch (e) { /* ignore */ }
    return currentSessionId;
}

async function newChat() {
    document.getElementById('messages').innerHTML = `<div class="msg msg-system"><p>👋 新对话已开始。有什么可以帮你的？</p></div>`;
    currentSessionId = null;
    await createNewSession();
    if (ws) ws.close();
    connectWebSocket();
}

async function saveMessageToHistory(role, content) {
    if (!content) return;
    if (!currentSessionId) await createNewSession();
    if (!currentSessionId) return;
    try {
        await fetch(`/api/chat/sessions/${currentSessionId}/messages`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ session_id: currentSessionId, role, content }),
        });
        if (role === 'user') {
            const session = chatSessions.find(s => s.id === currentSessionId);
            if (session && session.title === '新对话') {
                const title = content.slice(0, 20) + (content.length > 20 ? '...' : '');
                session.title = title;
                await fetch(`/api/chat/sessions/${currentSessionId}`, {
                    method: 'PATCH', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title }),
                });
                renderChatHistory();
            }
        }
    } catch (e) { /* ignore */ }
}

// ===== File Upload =====
function triggerFileUpload() { document.getElementById('file-input').click(); }
function handleFileSelect(event) { if (event.target.files.length > 0) uploadFiles(event.target.files); event.target.value = ''; }
function hideUploadZone() { document.getElementById('upload-zone').style.display = 'none'; }

async function uploadFiles(files) {
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        addMsg('system', `📎 正在上传 ${file.name}...`);
        try {
            const response = await fetch('/api/upload/file', { method: 'POST', body: formData });
            const result = await response.json();
            addMsg('system', result.success ? `✅ ${result.message}（${(result.size / 1024).toFixed(1)} KB）` : `❌ 上传失败：${result.error}`);
        } catch (e) { addMsg('system', `❌ 上传出错：${e.message}`); }
    }
}

// Drag and drop
(function setupDragDrop() {
    const center = document.querySelector('.panel-center');
    if (!center) return;
    center.addEventListener('dragover', (e) => { e.preventDefault(); const z = document.getElementById('upload-zone'); z.style.display = 'flex'; z.classList.add('dragover'); });
    center.addEventListener('dragleave', (e) => { if (!center.contains(e.relatedTarget)) document.getElementById('upload-zone').classList.remove('dragover'); });
    center.addEventListener('drop', (e) => { e.preventDefault(); const z = document.getElementById('upload-zone'); z.style.display = 'none'; z.classList.remove('dragover'); if (e.dataTransfer.files.length > 0) uploadFiles(e.dataTransfer.files); });
})();
