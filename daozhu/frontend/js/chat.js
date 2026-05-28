/**
 * chat.js — 聊天窗口：消息渲染 + 输入发送 + 自动滚动
 */

const Chat = {
  messages: [],
  isTyping: false,
  conversationId: null,
  showingReadme: false,

  init() {
    this._bindForm();
    this._bindTextarea();
    this._showWelcome();
  },

  // === 表单提交 ===
  _bindForm() {
    const form = document.getElementById('chat-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      this._handleSend();
    });
  },

  // === 输入框自适应高度 + 快捷键 ===
  _bindTextarea() {
    const textarea = document.getElementById('chat-input');

    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });

    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._handleSend();
      }
    });
  },

  // === 发送消息 ===
  async _handleSend() {
    const textarea = document.getElementById('chat-input');
    const sendBtn = document.querySelector('.chat__send');
    const text = textarea.value.trim();

    // 如果正在输出，点击停止
    if (this.isTyping) {
      this._stopGeneration();
      return;
    }

    if (!text) return;

    textarea.value = '';
    textarea.style.height = 'auto';
    this._removeWelcome();
    this._addMessage('user', text);

    // 切换为停止按钮
    sendBtn.textContent = '⏹ 停止';
    sendBtn.classList.add('chat__send--stop');
    this.isTyping = true;
    this._abortController = new AbortController();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_id: this.conversationId || null,
        }),
        signal: this._abortController.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let msgEl = null;
      let bubble = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.tool) {
              // 工具调用状态行
              const container = document.getElementById('chat-messages');
              const toolLine = document.createElement('div');
              toolLine.className = 'tool-status-line';
              toolLine.innerHTML = `<span class="tool-status-icon">🔧</span> <span class="tool-status-name">${data.tool}</span> <span class="tool-status-state">执行中...</span>`;
              toolLine.id = `tool-${Date.now()}`;
              container.appendChild(toolLine);
              this._lastToolLine = toolLine;
              this._scrollToBottom();
              Panel.addLog('info', `🔧 调用工具: ${data.tool}`);
              continue;
            }
            if (data.tool_done) {
              // 更新工具状态行
              if (this._lastToolLine) {
                const stateEl = this._lastToolLine.querySelector('.tool-status-state');
                if (data.status === 'ok') {
                  stateEl.textContent = '✅ 完成';
                  stateEl.style.color = 'var(--success)';
                } else {
                  stateEl.textContent = '❌ ' + (data.error || '失败').slice(0, 30);
                  stateEl.style.color = 'var(--error)';
                }
              }
              const icon = data.status === 'ok' ? '✅' : '❌';
              Panel.addLog(data.status === 'ok' ? 'success' : 'error',
                `${icon} ${data.tool_done} ${data.error || '完成'}`);
              continue;
            }
            if (data.chunk) {
              // 收到文本 chunk 时，确保消息气泡在工具行之后
              if (!msgEl) {
                msgEl = this._addMessageElement('assistant', '');
                bubble = msgEl.querySelector('.message__bubble');
                fullText = '';
              }
              fullText += data.chunk;
              bubble.textContent = fullText;
              this._scrollToBottom();
            }
            if (data.conversation_id) {
              this.conversationId = data.conversation_id;
            }
          } catch (e) {}
        }
      }

      this.messages.push({ role: 'assistant', content: fullText });
      Panel.addLog('info', `管理员回复: ${fullText.substring(0, 30)}...`);

    } catch (err) {
      if (err.name === 'AbortError') {
        this._addMessage('assistant', '（已停止）');
        Panel.addLog('info', '用户打断了输出');
      } else {
        this._addMessage('assistant', `抱歉，出了点问题：${err.message}`);
        Panel.addLog('error', `发送失败: ${err.message}`);
      }
    } finally {
      this.isTyping = false;
      sendBtn.textContent = '发送';
      sendBtn.classList.remove('chat__send--stop');
      this._abortController = null;
    }
  },

  _stopGeneration() {
    if (this._abortController) {
      this._abortController.abort();
    }
  },

  // === 添加消息到列表 ===
  _addMessage(role, content) {
    const msgEl = this._addMessageElement(role, content);
    this.messages.push({ role, content });
    this._scrollToBottom();
  },

  _addMessageElement(role, content) {
    const container = document.getElementById('chat-messages');
    const avatar = role === 'user'
      ? '<div class="avatar-user">我</div>'
      : '<img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar">';

    const msgEl = document.createElement('div');
    msgEl.className = `message message--${role}`;
    msgEl.innerHTML = `
      <div class="message__avatar">${avatar}</div>
      <div class="message__bubble">${this._escapeHtml(content)}</div>
    `;

    container.appendChild(msgEl);
    this._scrollToBottom();
    return msgEl;
  },

  // === 欢迎消息 ===
  _showWelcome() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
      <div class="chat__welcome" id="chat-welcome">
        <div class="chat__welcome-scene">
          <img src="/img/decor/cloud.svg" class="chat__welcome-cloud chat__welcome-cloud--1" alt="">
          <img src="/img/decor/cloud.svg" class="chat__welcome-cloud chat__welcome-cloud--2" alt="">
          <img src="/img/decor/cloud.svg" class="chat__welcome-cloud chat__welcome-cloud--3" alt="">
          <img src="/img/decor/birds.svg" class="chat__welcome-birds" alt="">
          <img src="/img/decor/island.svg" class="chat__welcome-island" alt="">
          <img src="/img/decor/wave.svg" class="chat__welcome-wave" alt="">
        </div>
        <img src="/img/librarian.svg" alt="岛管理员" style="width:80px;height:80px;image-rendering:pixelated;margin-bottom:16px;position:relative;z-index:1" class="librarian-avatar librarian-avatar--float">
        <div class="chat__welcome-title" style="position:relative;z-index:1">你好，我是岛管理员</div>
        <div class="chat__welcome-desc" style="position:relative;z-index:1">
          告诉我你想建造什么工作区，或者问我任何问题。<br>
          比如："帮我建一个读书笔记工作区"<br>
          <small style="color:var(--text-muted);margin-top:8px;display:block">
            💡 单击左侧资源查看说明 · 双击工作区打开
          </small>
        </div>
      </div>
    `;
  },

  _removeWelcome() {
    const welcome = document.getElementById('chat-welcome');
    if (welcome) welcome.remove();
  },

  // === 打字指示器 ===
  _showTyping() {
    this.isTyping = true;
    const container = document.getElementById('chat-messages');
    const typing = document.createElement('div');
    typing.id = 'typing-indicator';
    typing.className = 'message message--assistant';
    typing.innerHTML = `
      <div class="message__avatar">
        <div class="librarian librarian--thinking"><div class="librarian__pixel"></div></div>
      </div>
      <div class="typing-indicator">
        <div class="typing-indicator__dot"></div>
        <div class="typing-indicator__dot"></div>
        <div class="typing-indicator__dot"></div>
      </div>
    `;
    container.appendChild(typing);
    this._scrollToBottom();
  },

  _hideTyping() {
    this.isTyping = false;
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
  },

  // === 工具方法 ===
  _scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
  },

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
};


// === README 展示 ===
const ReadmeViewer = {
  show(content, title, workspaceId) {
    Chat.showingReadme = true;
    const container = document.getElementById('chat-messages');
    const form = document.getElementById('chat-form');
    form.style.display = 'none';

    const openBtn = workspaceId
      ? `<button onclick="ReadmeViewer.openWorkspace('${workspaceId}')" style="padding:6px 14px;background:var(--success);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:0.85rem">▶ 打开工作区</button>`
      : '';

    const deleteBtn = workspaceId
      ? `<button onclick="ReadmeViewer.hideWorkspace('${workspaceId}')" style="padding:6px 14px;background:transparent;color:var(--error);border:1px solid var(--error);border-radius:8px;cursor:pointer;font-size:0.8rem">🗑 隐藏工作区</button>`
      : '';

    const html = this._renderMarkdown(content);
    container.innerHTML = `
      <div style="padding:20px;overflow-y:auto;height:100%;display:flex;flex-direction:column">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <button onclick="ReadmeViewer.hide()" style="padding:6px 14px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:0.85rem">← 返回聊天</button>
          ${openBtn}
        </div>
        <div class="readme-content" style="line-height:1.8;color:var(--text-secondary);flex:1">${html}</div>
        ${workspaceId ? `<div style="padding-top:16px;border-top:1px solid var(--border-color);margin-top:16px;text-align:right">${deleteBtn}</div>` : ''}
      </div>
    `;
  },

  async openWorkspace(id) {
    App.showToast('正在启动...');
    try {
      // 检查是否是 lightweight 模式
      const wsRes = await fetch(`/api/workspaces`);
      const wsData = await wsRes.json();
      const ws = wsData.workspaces.find(w => w.id === id);
      if (ws && ws.mode === 'lightweight') {
        window.open(`/ws/${id}`, '_blank');
        return;
      }

      const res = await fetch(`/api/workspaces/${id}/start`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        window.open(`http://localhost:${data.workspace.port}`, '_blank');
      } else {
        App.showToast('启动失败');
      }
    } catch (e) {
      App.showToast('启动失败: ' + e.message);
    }
  },

  async hideWorkspace(id) {
    if (!confirm('隐藏此工作区？\n\n隐藏后可在设置中恢复，文件不会删除。')) return;
    try {
      await fetch(`/api/workspaces/${id}/hide`, { method: 'POST' });
      ReadmeViewer.hide();
      Sidebar.loadWorkspaces();
      Panel.addLog('info', '工作区已隐藏');
    } catch (e) {
      App.showToast('操作失败');
    }
  },

  hide() {
    Chat.showingReadme = false;
    const form = document.getElementById('chat-form');
    form.style.display = 'flex';
    Chat._showWelcome();
  },

  _renderMarkdown(md) {
    return md
      .replace(/^### (.+)$/gm, '<h4 style="margin:16px 0 8px;color:var(--text-primary)">$1</h4>')
      .replace(/^## (.+)$/gm, '<h3 style="margin:20px 0 10px;color:var(--text-primary)">$1</h3>')
      .replace(/^# (.+)$/gm, '<h2 style="margin:24px 0 12px;color:var(--text-primary)">$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code style="background:var(--bg-tertiary);padding:2px 6px;border-radius:4px;font-size:0.85em">$1</code>')
      .replace(/^- \[x\] (.+)$/gm, '<div style="padding:3px 0">✅ $1</div>')
      .replace(/^- \[ \] (.+)$/gm, '<div style="padding:3px 0">⬜ $1</div>')
      .replace(/^- (.+)$/gm, '<div style="padding:3px 0;padding-left:12px">• $1</div>')
      .replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid var(--accent);padding-left:12px;color:var(--text-muted);margin:8px 0">$1</blockquote>')
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>');
  },
};
