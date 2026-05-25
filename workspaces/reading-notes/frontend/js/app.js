/**
 * 读书笔记 — 前端主逻辑
 */
const App = {
  async init() {
    document.getElementById('create-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.create();
    });
    await this.load();
  },

  async load() {
    const res = await fetch('/api/items/');
    const data = await res.json();
    this.render(data.items);
  },

  render(items) {
    const container = document.getElementById('item-list');
    if (items.length === 0) {
      container.innerHTML = '<p style="color:var(--muted);text-align:center;padding:40px">暂无数据</p>';
      return;
    }
    container.innerHTML = items.map(item => `
      <div class="item" data-id="${item.id}">
        <span class="item__title">${item.title}</span>
        <button class="item__delete" onclick="App.remove(${item.id})">✕</button>
      </div>
    `).join('');
  },

  async create() {
    const input = document.getElementById('input-title');
    const title = input.value.trim();
    if (!title) return;
    await fetch('/api/items/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    input.value = '';
    await this.load();
  },

  async remove(id) {
    await fetch(`/api/items/${id}`, { method: 'DELETE' });
    await this.load();
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
