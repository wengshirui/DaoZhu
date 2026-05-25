/**
 * app.js — 待办工作区主逻辑
 */
const App = {
  currentFilter: 'all',
  tasks: [],
  projects: [],
  editingTaskId: null,

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
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => this.switchFilter(btn.dataset.filter));
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
  },

  // === 筛选 ===
  switchFilter(filter) {
    this.currentFilter = filter;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('nav-item--active'));
    document.querySelector(`[data-filter="${filter}"]`).classList.add('nav-item--active');

    const titles = { all: '全部任务', today: '☀️ 今日聚焦', in_progress: '🔥 进行中', done: '✅ 已完成' };
    document.getElementById('view-title').textContent = titles[filter] || '全部任务';
    this.loadTasks();
  },

  // === 加载任务 ===
  async loadTasks() {
    const params = {};
    if (this.currentFilter === 'today') params.today = true;
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
    if (this.tasks.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">📝</div>
          <div class="empty-state__text">暂无任务，添加一个吧</div>
        </div>`;
      return;
    }

    container.innerHTML = this.tasks.map(task => this.renderTaskCard(task)).join('');

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
    const dueMeta = task.due_date ? this.formatDue(task.due_date) : '';
    const subtaskMeta = task.subtask_count > 0
      ? `<span class="task-card__subtasks">${task.subtask_done}/${task.subtask_count}</span>` : '';

    return `
      <div class="task-card ${doneClass}" data-id="${task.id}">
        <button class="task-card__check" data-id="${task.id}" data-status="${task.status}">
          ${checkIcon}
        </button>
        <div class="task-card__priority task-card__priority--${task.priority}"></div>
        <div class="task-card__body">
          <div class="task-card__title">${this.escapeHtml(task.title)}</div>
          <div class="task-card__meta">
            ${dueMeta}${subtaskMeta}
          </div>
        </div>
      </div>`;
  },

  formatDue(dateStr) {
    const today = new Date().toISOString().split('T')[0];
    const isOverdue = dateStr < today;
    const cls = isOverdue ? 'task-card__due--overdue' : 'task-card__due';
    const d = new Date(dateStr);
    const label = dateStr === today ? '今天' : `${d.getMonth()+1}/${d.getDate()}`;
    return `<span class="${cls}">📅 ${label}</span>`;
  },

  // === 创建任务 ===
  async createTask() {
    const input = document.getElementById('task-title');
    const title = input.value.trim();
    if (!title) return;

    await API.createTask({ title });
    input.value = '';
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

    // 填充项目选择
    const select = document.getElementById('modal-project');
    select.innerHTML = '<option value="">无项目</option>' +
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
    if (!confirm('确定删除这个任务？')) return;
    await API.deleteTask(this.editingTaskId);
    this.closeModal();
    await this.loadTasks();
  },

  // === 项目 ===
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
      <button class="nav-item" data-project="${p.id}">
        <span class="nav-item__icon">${p.icon}</span>
        <span class="nav-item__text">${p.name}</span>
        <span class="nav-item__count">${p.task_count - p.done_count}</span>
      </button>
    `).join('');
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
