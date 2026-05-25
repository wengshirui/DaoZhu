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
