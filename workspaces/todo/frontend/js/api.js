/**
 * api.js — 待办工作区 API 封装
 */
const API = {
  base: '/api',

  async _req(path, opts = {}) {
    const res = await fetch(`${this.base}${path}`, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  // 任务
  getTasks(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this._req(`/tasks/${qs ? '?' + qs : ''}`);
  },
  getTask(id) { return this._req(`/tasks/${id}`); },
  createTask(data) { return this._req('/tasks/', { method: 'POST', body: JSON.stringify(data) }); },
  updateTask(id, data) { return this._req(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }); },
  deleteTask(id) { return this._req(`/tasks/${id}`, { method: 'DELETE' }); },

  // 项目
  getProjects() { return this._req('/projects/'); },
  createProject(data) { return this._req('/projects/', { method: 'POST', body: JSON.stringify(data) }); },

  // 标签
  getTags() { return this._req('/tags/'); },
};
