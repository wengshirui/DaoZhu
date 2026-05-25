/**
 * sidebar.js — 左侧面板：Tab 切换 + 列表渲染
 */

const Sidebar = {
  currentTab: 'buildings',

  init() {
    this._bindTabs();
    this._bindToggle();
    this.loadAll();
  },

  // === Tab 切换 ===
  _bindTabs() {
    const tabs = document.querySelectorAll('.sidebar__tabs .tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        this._switchTab(tab.dataset.tab);
      });
    });
  },

  _switchTab(tabName) {
    this.currentTab = tabName;

    // 更新 Tab 状态
    document.querySelectorAll('.sidebar__tabs .tab').forEach(t => {
      const isActive = t.dataset.tab === tabName;
      t.classList.toggle('active', isActive);
      t.setAttribute('aria-selected', isActive);
    });

    // 更新面板显示
    document.querySelectorAll('.sidebar__content .tab-panel').forEach(p => {
      p.classList.toggle('active', p.id === `panel-${tabName}`);
    });
  },

  // === 折叠/展开 ===
  _bindToggle() {
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');

    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      toggle.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
    });
  },

  // === 加载所有数据 ===
  async loadAll() {
    await Promise.all([
      this.loadWorkspaces(),
      this.loadSkills(),
      this.loadTools()
    ]);
  },

  // === 工作区列表 ===
  async loadWorkspaces() {
    const container = document.getElementById('workspace-list');
    try {
      const workspaces = await API.getWorkspaces();
      if (workspaces.length === 0) {
        container.innerHTML = this._renderEmpty('🏗️', '还没有工作区', '告诉管家你想建造什么');
        return;
      }
      container.innerHTML = workspaces.map(w => this._renderWorkspaceCard(w)).join('');
      this._bindWorkspaceClicks(container);
    } catch (err) {
      container.innerHTML = this._renderEmpty('⚠️', '加载失败', err.message);
    }
  },

  _renderWorkspaceCard(workspace) {
    const statusClass = workspace.status === 'running' ? 'badge--running' : 'badge--stopped';
    const statusText = workspace.status === 'running' ? '运行中' : '已停止';

    return `
      <div class="card" data-id="${workspace.id}" data-port="${workspace.port}" data-status="${workspace.status}">
        <div class="card__icon" style="background: ${workspace.color}20">
          ${workspace.icon}
        </div>
        <div class="card__body">
          <div class="card__name">${workspace.name}</div>
          <div class="card__desc">${workspace.description}</div>
        </div>
        <span class="badge ${statusClass}">
          <span class="badge__dot"></span>
          ${statusText}
        </span>
      </div>
    `;
  },

  _bindWorkspaceClicks(container) {
    container.querySelectorAll('.card').forEach(card => {
      // 单击：显示 README
      card.addEventListener('click', async () => {
        const id = card.dataset.id;
        try {
          const res = await fetch(`/api/workspaces/${id}/readme`);
          const data = await res.json();
          ReadmeViewer.show(data.content, card.querySelector('.card__name').textContent, id);
        } catch (e) {
          App.showToast('加载说明失败');
        }
      });

      // 右键：隐藏工作区
      card.addEventListener('contextmenu', async (e) => {
        e.preventDefault();
        const id = card.dataset.id;
        const name = card.querySelector('.card__name').textContent;
        if (confirm(`隐藏「${name}」？\n\n隐藏后可在设置中恢复，文件不会删除。`)) {
          try {
            await fetch(`/api/workspaces/${id}/hide`, { method: 'POST' });
            await Sidebar.loadWorkspaces();
            Panel.addLog('info', `工作区「${name}」已隐藏`);
          } catch (e) {
            App.showToast('隐藏失败');
          }
        }
      });

      // 双击：启动并打开工作区
      card.addEventListener('dblclick', async () => {
        const status = card.dataset.status;
        const port = card.dataset.port;
        const id = card.dataset.id;

        if (status === 'running') {
          window.open(`http://localhost:${port}`, '_blank');
        } else {
          App.showToast('正在启动工作区...');
          try {
            const res = await fetch(`/api/workspaces/${id}/start`, { method: 'POST' });
            if (res.ok) {
              const data = await res.json();
              window.open(`http://localhost:${data.workspace.port}`, '_blank');
              await Sidebar.loadWorkspaces();
            } else {
              App.showToast('启动失败');
            }
          } catch (e) {
            App.showToast('启动失败: ' + e.message);
          }
        }
      });
    });
  },

  // === 技能列表 ===
  async loadSkills() {
    const container = document.getElementById('skill-list');
    try {
      const skills = await API.getSkills();
      if (skills.length === 0) {
        container.innerHTML = this._renderEmpty('📖', '暂无技能', '技能让管家更聪明');
        return;
      }
      container.innerHTML = skills.map(s => this._renderSkillCard(s)).join('');
      this._bindSkillClicks(container);
    } catch (err) {
      container.innerHTML = this._renderEmpty('⚠️', '加载失败', err.message);
    }
  },

  _bindSkillClicks(container) {
    container.querySelectorAll('.card[data-type="skill"]').forEach(card => {
      card.addEventListener('click', async () => {
        const id = card.dataset.id;
        try {
          const res = await fetch(`/api/skills/${id}/readme`);
          const data = await res.json();
          ReadmeViewer.show(data.content, card.querySelector('.card__name').textContent);
        } catch (e) {
          App.showToast('加载技能说明失败');
        }
      });
    });
  },

  _renderSkillCard(skill) {
    const statusClass = skill.status === 'active' ? 'badge--running' : 'badge--stopped';
    const statusText = skill.status === 'active' ? '已启用' : '未启用';

    return `
      <div class="card" data-id="${skill.id}" data-type="skill">
        <div class="card__icon">${skill.icon}</div>
        <div class="card__body">
          <div class="card__name">${skill.name}</div>
        </div>
        <span class="badge ${statusClass}">
          <span class="badge__dot"></span>
          ${statusText}
        </span>
      </div>
    `;
  },

  // === 工具列表 ===
  async loadTools() {
    const container = document.getElementById('tool-list');
    try {
      const tools = await API.getTools();
      if (tools.length === 0) {
        container.innerHTML = this._renderEmpty('🔧', '暂无工具', '工具连接外部世界');
        return;
      }
      container.innerHTML = tools.map(t => this._renderToolCard(t)).join('');
    } catch (err) {
      container.innerHTML = this._renderEmpty('⚠️', '加载失败', err.message);
    }
  },

  _renderToolCard(tool) {
    const statusClass = tool.status === 'connected' ? 'badge--connected' : 'badge--stopped';
    const statusText = tool.status === 'connected' ? '已连接' : '未连接';

    return `
      <div class="card" data-id="${tool.id}">
        <div class="card__icon">${tool.icon}</div>
        <div class="card__body">
          <div class="card__name">${tool.name}</div>
        </div>
        <span class="badge ${statusClass}">
          <span class="badge__dot"></span>
          ${statusText}
        </span>
      </div>
    `;
  },

  // === 空状态 ===
  _renderEmpty(icon, title, desc) {
    return `
      <div class="empty-state">
        <div class="empty-state__icon">${icon}</div>
        <div class="empty-state__title">${title}</div>
        <div class="empty-state__desc">${desc}</div>
      </div>
    `;
  }
};
