/**
 * app.js — 待办工作区主逻辑
 */
const App = {
  currentFilter: 'all',
  currentProject: null,
  tasks: [],
  projects: [],
  editingTaskId: null,
  searchQuery: '',

  async init() {
    this.bindEvents();
    await this.loadProjects();
    await this.loadTasks();
  },

  bindEvents() {
    // 新建任务
    document.getElementById('task-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.createTask();
    });

    // 侧栏导航
    document.querySelectorAll('.nav-item[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => this.switchFilter(btn.dataset.filter));
    });

    // 搜索
    document.getElementById('search-input').addEventListener('input', (e) => {
      this.searchQuery = e.target.value.trim().toLowerCase();
      this.renderTasks();
    });

    // 优先级筛选
    document.getElementById('priority-filter').addEventListener('change', () => this.loadTasks());

    // 弹窗
    document.getElementById('modal-close').addEventListener('click', () => this.closeModal());
    document.getElementById('modal-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.saveTask();
    });
    document.getElementById('modal-delete').addEventListener('click', () => this.deleteTask());

    // 点击弹窗外部关闭
    const modal = document.getElementById('task-modal');
    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.closeModal();
    });

    // 新建分类
    document.getElementById('add-category-btn').addEventListener('click', () => this.addCategory());
  },

  // === 筛选 ===
  switchFilter(filter) {
    this.currentFilter = filter;
    this.currentProject = null;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('nav-item--active'));
    document.querySelector(`[data-filter="${filter}"]`)?.classList.add('nav-item--active');

    const titles = { all: '全部任务', today: '☀️ 今日聚焦', in_progress: '🔥 进行中', done: '✅ 已完成' };
    document.getElementById('view-title').textContent = titles[filter] || '全部任务';
    this.loadTasks();
  },

  switchProject(projectId) {
    this.currentFilter = 'project';
    this.currentProject = projectId;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('nav-item--active'));
    document.querySelector(`[data-project="${projectId}"]`)?.classList.add('nav-item--active');

    const p = this.projects.find(x => x.id == projectId);
    document.getElementById('view-title').textContent = p ? `${p.icon} ${p.name}` : '分类';
    this.loadTasks();
  },

  // === 加载任务 ===
  async loadTasks() {
    const params = {};
    if (this.currentFilter === 'today') params.today = true;
    else if (this.currentFilter === 'project' && this.currentProject) params.project_id = this.currentProject;
    else if (this.currentFilter !== 'all') params.status = this.currentFilter;

    const priority = document.getElementById('priority-filter').value;
    if (priority) params.priority = priority;

    try {
      const data = await API.getTasks(params);
      this.tasks = data.tasks;
      this.renderTasks();
      this.updateCounts();
    } catch (e) {
      console.error('加载任务失败:', e);
    }
  },

  renderTasks() {
    const container = document.getElementById('task-list');
    let filtered = this.tasks;

    // 搜索过滤
    if (this.searchQuery) {
      filtered = filtered.filter(t => t.title.toLowerCase().includes(this.searchQuery));
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">📝</div>
          <div class="empty-state__text">${this.searchQuery ? '没有匹配的任务' : '暂无任务，添加一个吧'}</div>
        </div>`;
      return;
    }

    container.innerHTML = filtered.map(task => this.renderTaskCard(task)).join('');

    // 绑定事件
    container.querySelectorAll('.task-card__check').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleTask(btn.dataset.id, btn.dataset.status);
      });
    });
    container.querySelectorAll('.task-card').forEach(card => {
      card.addEventListener('click', () => this.openModal(card.dataset.id));
    });
  },

  renderTaskCard(task) {
    const isDone = task.status === 'done';
    const doneClass = isDone ? 'task-card--done' : '';
    const checkIcon = isDone ? '✓' : '';

    // 优先级标签
    const priorityLabels = { urgent: '紧急', high: '高', medium: '中', low: '低' };
    const priorityTag = `<span class="task-card__priority-tag task-card__priority-tag--${task.priority}">${priorityLabels[task.priority]}</span>`;

    // 截止日期
    let dueTag = '';
    if (task.due_date) {
      const today = new Date().toISOString().split('T')[0];
      const isOverdue = task.due_date < today && !isDone;
      const d = new Date(task.due_date + 'T00:00:00');
      const label = task.due_date === today ? '今天' : `${d.getMonth()+1}/${d.getDate()}`;
      const cls = isOverdue ? 'task-card__due-tag--overdue' : '';
      dueTag = `<span class="task-card__due-tag ${cls}">📅 ${label}</span>`;
    }

    return `
      <div class="task-card ${doneClass}" data-id="${task.id}">
        <button class="task-card__check" data-id="${task.id}" data-status="${task.status}">
          ${checkIcon}
        </button>
        <div class="task-card__priority-bar task-card__priority-bar--${task.priority}"></div>
        <div class="task-card__body">
          <div class="task-card__title">${this.escapeHtml(task.title)}</div>
        </div>
        <div class="task-card__tags">
          ${priorityTag}
          ${dueTag}
        </div>
      </div>`;
  },

  // === 创建任务 ===
  async createTask() {
    const input = document.getElementById('task-title');
    const title = input.value.trim();
    if (!title) return;

    const priority = document.getElementById('task-priority').value;
    const due_date = document.getElementById('task-due').value || null;
    const project_id = this.currentProject || null;

    await API.createTask({ title, priority, due_date, project_id });
    input.value = '';
    document.getElementById('task-due').value = '';
    await this.loadTasks();
  },

  // === 切换完成状态 ===
  async toggleTask(id, currentStatus) {
    const newStatus = currentStatus === 'done' ? 'todo' : 'done';
    await API.updateTask(id, { status: newStatus });
    await this.loadTasks();
  },

  // === 弹窗编辑 ===
  async openModal(taskId) {
    this.editingTaskId = taskId;
    const task = await API.getTask(taskId);
    document.getElementById('modal-title').value = task.title;
    document.getElementById('modal-desc').value = task.description || '';
    document.getElementById('modal-priority').value = task.priority;
    document.getElementById('modal-due').value = task.due_date || '';

    // 填充分类选择
    const select = document.getElementById('modal-project');
    select.innerHTML = '<option value="">无分类</option>' +
      this.projects.map(p => `<option value="${p.id}" ${p.id == task.project_id ? 'selected' : ''}>${p.icon} ${p.name}</option>`).join('');

    document.getElementById('task-modal').showModal();
  },

  closeModal() {
    document.getElementById('task-modal').close();
    this.editingTaskId = null;
  },

  async saveTask() {
    if (!this.editingTaskId) return;
    const data = {
      title: document.getElementById('modal-title').value,
      description: document.getElementById('modal-desc').value,
      priority: document.getElementById('modal-priority').value,
      due_date: document.getElementById('modal-due').value || null,
      project_id: document.getElementById('modal-project').value || null,
    };
    await API.updateTask(this.editingTaskId, data);
    this.closeModal();
    await this.loadTasks();
  },

  async deleteTask() {
    if (!this.editingTaskId) return;
    if (!confirm('确定要删除这个任务吗？\n\n删除后无法恢复。')) return;
    await API.deleteTask(this.editingTaskId);
    this.closeModal();
    await this.loadTasks();
  },

  // === 分类管理 ===
  async loadProjects() {
    try {
      const data = await API.getProjects();
      this.projects = data.projects;
      this.renderProjects();
    } catch (e) { console.error(e); }
  },

  renderProjects() {
    const container = document.getElementById('project-list');
    container.innerHTML = this.projects.map(p => `
      <div class="nav-item" data-project="${p.id}">
        <span class="nav-item__icon">${p.icon}</span>
        <span class="nav-item__text">${p.name}</span>
        <span class="nav-item__count">${p.task_count - p.done_count}</span>
        <span class="nav-item__actions">
          <button class="nav-item__action-btn" data-edit-project="${p.id}" title="编辑">✏️</button>
          <button class="nav-item__action-btn nav-item__action-btn--danger" data-del-project="${p.id}" title="删除">🗑</button>
        </span>
      </div>
    `).join('');

    // 绑定点击切换分类
    container.querySelectorAll('[data-project]').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target.closest('[data-edit-project]') || e.target.closest('[data-del-project]')) return;
        this.switchProject(el.dataset.project);
      });
    });

    // 编辑分类
    container.querySelectorAll('[data-edit-project]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.editCategory(btn.dataset.editProject);
      });
    });

    // 删除分类
    container.querySelectorAll('[data-del-project]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.deleteCategory(btn.dataset.delProject);
      });
    });
  },

  async addCategory() {
    const name = prompt('新分类名称：');
    if (!name || !name.trim()) return;
    const icon = prompt('图标（emoji）：', '📁') || '📁';
    await API.createProject({ name: name.trim(), icon });
    await this.loadProjects();
  },

  async editCategory(id) {
    const p = this.projects.find(x => x.id == id);
    if (!p) return;
    const name = prompt('修改分类名称：', p.name);
    if (!name || !name.trim()) return;
    const icon = prompt('图标（emoji）：', p.icon) || p.icon;
    await API.updateProject(id, { name: name.trim(), icon });
    await this.loadProjects();
  },

  async deleteCategory(id) {
    const p = this.projects.find(x => x.id == id);
    if (!p) return;
    if (!confirm(`确定删除分类「${p.name}」吗？\n\n分类下的任务不会被删除，只是变为"无分类"。`)) return;
    await API.deleteProject(id);
    await this.loadProjects();
    if (this.currentProject == id) this.switchFilter('all');
  },

  // === 统计 ===
  async updateCounts() {
    try {
      const all = await API.getTasks({});
      const allTasks = all.tasks;
      document.getElementById('count-all').textContent = allTasks.length;
      document.getElementById('count-progress').textContent = allTasks.filter(t => t.status === 'in_progress').length;
      document.getElementById('count-done').textContent = allTasks.filter(t => t.status === 'done').length;

      const today = await API.getTasks({ today: true });
      document.getElementById('count-today').textContent = today.tasks.length;
    } catch (e) {}
  },

  escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
