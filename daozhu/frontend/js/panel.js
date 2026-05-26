/**
 * panel.js — 右侧面板：历史对话 + 输出日志
 */

const Panel = {
  currentTab: 'history',
  logs: [],

  init() {
    this._bindTabs();
    this._bindToggle();
    this.loadHistory();
    this._addInitLogs();
  },

  // === Tab 切换 ===
  _bindTabs() {
    const tabs = document.querySelectorAll('.infopanel__tabs .tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        this._switchTab(tab.dataset.tab);
      });
    });
  },

  _switchTab(tabName) {
    this.currentTab = tabName;

    document.querySelectorAll('.infopanel__tabs .tab').forEach(t => {
      const isActive = t.dataset.tab === tabName;
      t.classList.toggle('active', isActive);
      t.setAttribute('aria-selected', isActive);
    });

    document.querySelectorAll('.infopanel__content .tab-panel').forEach(p => {
      p.classList.toggle('active', p.id === `panel-${tabName}`);
    });
  },

  // === 折叠/展开 ===
  _bindToggle() {
    const toggle = document.getElementById('infopanel-toggle');
    const panel = document.getElementById('infopanel');

    toggle.addEventListener('click', () => {
      panel.classList.toggle('collapsed');
      toggle.textContent = panel.classList.contains('collapsed') ? '◀' : '▶';
    });
  },

  // === 历史对话 ===
  async loadHistory() {
    const container = document.getElementById('history-list');
    try {
      const conversations = await API.getConversations();
      if (conversations.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state__icon">💬</div>
            <div class="empty-state__title">暂无对话</div>
            <div class="empty-state__desc">开始和管理员聊天吧</div>
          </div>
        `;
        return;
      }

      // 按日期分组
      const groups = this._groupByDate(conversations);
      let html = '';
      for (const [label, convs] of Object.entries(groups)) {
        html += `<div class="history-group"><div class="history-date">${label}</div>`;
        for (const c of convs) {
          const active = c.id === Chat.conversationId ? ' history-item--active' : '';
          html += `
            <div class="history-item${active}" data-id="${c.id}">
              <span class="history-item__icon">💬</span>
              <div class="history-item__body">
                <div class="history-item__title">${c.title}</div>
              </div>
              <button class="history-item__delete" data-id="${c.id}" title="删除对话">✕</button>
            </div>`;
        }
        html += '</div>';
      }

      // 新建对话按钮
      html = `<button class="history-new-btn" onclick="Panel.newChat()">+ 新对话</button>` + html;
      container.innerHTML = html;

      // 绑定点击切换
      container.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', (e) => {
          if (e.target.classList.contains('history-item__delete')) return;
          this.switchConversation(item.dataset.id);
        });
      });

      // 绑定删除按钮
      container.querySelectorAll('.history-item__delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          if (!confirm('删除这个对话？')) return;
          try {
            await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
            if (Chat.conversationId === id) {
              Chat.conversationId = null;
              Chat._showWelcome();
            }
            this.loadHistory();
          } catch (err) {
            App.showToast('删除失败');
          }
        });
      });

      // 首次加载：如果没有当前对话，加载第一个
      if (!Chat.conversationId && conversations.length > 0) {
        this.switchConversation(conversations[0].id);
      }
    } catch (err) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">⚠️</div>
          <div class="empty-state__title">加载失败</div>
          <div class="empty-state__desc">${err.message}</div>
        </div>
      `;
    }
  },

  async switchConversation(convId) {
    Chat.conversationId = convId;

    // 更新高亮
    document.querySelectorAll('.history-item').forEach(i => i.classList.remove('history-item--active'));
    const active = document.querySelector(`.history-item[data-id="${convId}"]`);
    if (active) active.classList.add('history-item--active');

    // 加载对话消息
    try {
      const res = await fetch(`/api/conversations/${convId}`);
      const data = await res.json();
      const container = document.getElementById('chat-messages');
      const form = document.getElementById('chat-form');
      form.style.display = 'flex';
      Chat.showingReadme = false;
      container.innerHTML = '';

      if (data.messages && data.messages.length > 0) {
        for (const msg of data.messages) {
          if (msg.role === 'user' || msg.role === 'assistant') {
            Chat._addMessageElement(msg.role, msg.content);
          }
        }
        Chat.messages = data.messages;
      } else {
        Chat._showWelcome();
      }
    } catch (e) {
      App.showToast('加载对话失败');
    }
  },

  newChat() {
    Chat.conversationId = null;
    Chat.messages = [];
    Chat.showingReadme = false;
    const form = document.getElementById('chat-form');
    form.style.display = 'flex';
    Chat._showWelcome();
    this.loadHistory();
  },

  _groupByDate(conversations) {
    const groups = {};
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();

    for (const c of conversations) {
      const d = new Date(c.updated_at).toDateString();
      let label = '更早';
      if (d === today) label = '今天';
      else if (d === yesterday) label = '昨天';
      else {
        const date = new Date(c.updated_at);
        label = `${date.getMonth() + 1}月${date.getDate()}日`;
      }
      if (!groups[label]) groups[label] = [];
      groups[label].push(c);
    }
    return groups;
  },

  // === 输出日志 ===
  _addInitLogs() {
    this.addLog('info', '岛主平台启动中...');
    this.addLog('success', '平台服务已就绪 (端口 7788)');
    this.addLog('info', '加载工作区列表...');
    this.addLog('success', '3 个工作区已加载');
  },

  addLog(level, message) {
    const container = document.getElementById('log-list');
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    const prefix = { info: 'INFO', success: ' OK ', warning: 'WARN', error: ' ERR' }[level] || 'INFO';

    const entry = document.createElement('div');
    entry.className = `log-entry log-entry--${level}`;
    entry.textContent = `[${time}] [${prefix}] ${message}`;

    container.appendChild(entry);
    this.logs.push({ level, message, time });

    // 自动滚动到底部
    container.scrollTop = container.scrollHeight;
  }
};
