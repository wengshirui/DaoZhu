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
    const text = textarea.value.trim();
    if (!text || this.isTyping) return;

    // 清空输入框
    textarea.value = '';
    textarea.style.height = 'auto';

    // 移除欢迎消息
    this._removeWelcome();

    // 添加用户消息
    this._addMessage('user', text);

    // 显示打字指示器
    this._showTyping();

    try {
      // SSE 流式请求
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_id: this.conversationId || null,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      this._hideTyping();

      // 创建助手消息容器
      const msgEl = this._addMessageElement('assistant', '');
      const bubble = msgEl.querySelector('.message__bubble');
      let fullText = '';

      // 读取 SSE 流
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.chunk) {
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
      Panel.addLog('info', `管家回复: ${fullText.substring(0, 30)}...`);

    } catch (err) {
      this._hideTyping();
      this._addMessage('assistant', `抱歉，出了点问题：${err.message}`);
      Panel.addLog('error', `发送失败: ${err.message}`);
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
      ? '<span>👤</span>'
      : '<div class="librarian librarian--idle"><div class="librarian__pixel"></div></div>';

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
        <div class="librarian librarian--large librarian--idle">
          <div class="librarian__pixel"></div>
        </div>
        <div class="chat__welcome-title">你好，我是图书管理员</div>
        <div class="chat__welcome-desc">
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
  show(content, title) {
    Chat.showingReadme = true;
    const container = document.getElementById('chat-messages');
    const form = document.getElementById('chat-form');
    form.style.display = 'none';

    // 简单 Markdown 渲染（标题、列表、代码块、粗体）
    const html = this._renderMarkdown(content);
    container.innerHTML = `
      <div style="padding:20px;overflow-y:auto;height:100%">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h2 style="font-size:1.2rem;color:var(--text-primary)">${title || '文档'}</h2>
          <button onclick="ReadmeViewer.hide()" style="padding:6px 14px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:0.85rem">← 返回聊天</button>
        </div>
        <div class="readme-content" style="line-height:1.8;color:var(--text-secondary)">${html}</div>
      </div>
    `;
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
