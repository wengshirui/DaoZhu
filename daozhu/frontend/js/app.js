/**
 * app.js — 主入口：初始化 + 主题切换 + 全局错误处理
 */

const App = {
  init() {
    this._initTheme();
    this._bindThemeToggle();
    this._initModules();
    this._updateStatus();
  },

  // === 模块初始化 ===
  _initModules() {
    try {
      Sidebar.init();
      Chat.init();
      Panel.init();
      Panel.addLog('success', '所有模块初始化完成');
    } catch (err) {
      console.error('初始化失败:', err);
      this.showToast('页面初始化失败，请刷新重试');
      Panel.addLog('error', `初始化失败: ${err.message}`);
    }
  },

  // === 主题 ===
  _initTheme() {
    const saved = localStorage.getItem('daozhu-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
  },

  _bindThemeToggle() {
    const btn = document.getElementById('btn-theme');
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('daozhu-theme', next);
      Panel.addLog('info', `主题切换为: ${next === 'dark' ? '暗色' : '亮色'}`);
    });

    // 设置按钮 → 打开设置面板
    const settingsBtn = document.getElementById('btn-settings');
    settingsBtn.addEventListener('click', () => this._showSettings());
  },

  // === 设置面板 ===
  async _showSettings() {
    const container = document.getElementById('chat-messages');
    const form = document.getElementById('chat-form');
    form.style.display = 'none';
    Chat.showingReadme = true;

    // 读取当前配置
    let config = {};
    try {
      const res = await fetch('/api/config');
      config = (await res.json()).config || {};
    } catch (e) {}

    container.innerHTML = `
      <div style="padding:24px;overflow-y:auto;height:100%">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
          <h2 style="font-size:1.2rem">⚙️ 设置</h2>
          <button onclick="ReadmeViewer.hide()" style="padding:6px 14px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:0.85rem">← 返回</button>
        </div>

        <div style="display:flex;flex-direction:column;gap:16px;max-width:400px">
          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🧠 DeepSeek API Key</label>
            <input type="password" id="settings-apikey" placeholder="sk-xxxxxxxx" value=""
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
          </div>

          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🔗 Gitee Token（论坛发帖用）</label>
            <input type="password" id="settings-gitee" placeholder="xxxxxxxx" value=""
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
          </div>

          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🎨 主题</label>
            <select id="settings-theme" style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
              <option value="light">☀️ 亮色</option>
              <option value="dark">🌙 暗色</option>
            </select>
          </div>

          <button onclick="App._saveSettings()" style="padding:10px 20px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font:inherit;font-weight:500;margin-top:8px">
            保存设置
          </button>
          <div id="settings-status" style="font-size:0.85rem;min-height:20px"></div>
        </div>
      </div>
    `;

    // 填充当前主题
    document.getElementById('settings-theme').value =
      document.documentElement.getAttribute('data-theme') || 'light';
  },

  async _saveSettings() {
    const status = document.getElementById('settings-status');
    const apiKey = document.getElementById('settings-apikey').value.trim();
    const giteeToken = document.getElementById('settings-gitee').value.trim();
    const theme = document.getElementById('settings-theme').value;

    try {
      // 保存 API Key
      if (apiKey) {
        await fetch('/api/onboarding/save-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: apiKey }),
        });
      }

      // 保存 Gitee Token
      if (giteeToken) {
        await fetch('/api/onboarding/save-gitee-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: giteeToken }),
        });
      }

      // 保存主题
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('daozhu-theme', theme);
      await fetch('/api/config/display.theme', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: theme }),
      });

      status.textContent = '✅ 设置已保存';
      status.style.color = 'var(--success)';
    } catch (e) {
      status.textContent = '❌ 保存失败: ' + e.message;
      status.style.color = 'var(--error)';
    }
  },

  // === 状态栏 ===
  _updateStatus() {
    const info = document.getElementById('status-info');
    API.getWorkspaces().then(workspaces => {
      const running = workspaces.filter(w => w.status === 'running').length;
      info.textContent = `${workspaces.length} 个工作区 | ${running} 个运行中`;
    }).catch(() => {
      info.textContent = '状态获取失败';
    });

    // 加载岛名到顶栏
    fetch('/api/config').then(r => r.json()).then(data => {
      const name = data.config?.island_name;
      if (name) {
        document.querySelector('.topbar__title').textContent = name;
      }
    }).catch(() => {});
  },

  // === 全局错误提示 ===
  showToast(message, duration = 3000) {
    let toast = document.querySelector('.error-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'error-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('visible');

    setTimeout(() => {
      toast.classList.remove('visible');
    }, duration);
  }
};

// === 启动 ===
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

// === 全局错误捕获 ===
window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled rejection:', e.reason);
  App.showToast('操作失败: ' + (e.reason?.message || '未知错误'));
});
