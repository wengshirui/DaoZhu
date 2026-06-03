/**
 * 定时任务工作区 — 前端
 */
(function() {
  'use strict';

  const API_BASE = '/ws/scheduler/api';

  async function loadTasks() {
    const container = document.getElementById('task-list');
    try {
      const res = await fetch(`${API_BASE}/tasks`);
      const data = await res.json();
      const tasks = data.tasks || [];

      if (tasks.length === 0) {
        container.innerHTML = '<div class="empty"><p>暂无定时任务</p><p class="sub">点击右上角"+ 新建任务"创建</p></div>';
        return;
      }

      container.innerHTML = tasks.map(t => `
        <div class="task-card ${t.enabled ? '' : 'disabled'}">
          <div class="task-card__header">
            <span class="task-card__status">${t.enabled ? '🟢' : '⏸️'}</span>
            <strong class="task-card__name">${t.name}</strong>
            <span class="task-card__schedule">${t.schedule}</span>
          </div>
          <div class="task-card__body">
            <p class="task-card__payload">${t.payload || t.description || ''}</p>
            <div class="task-card__meta">
              <span>上次: ${t.last_run_at ? new Date(t.last_run_at).toLocaleString() : '未执行'}</span>
              <span>下次: ${t.next_run_at ? new Date(t.next_run_at).toLocaleString() : '-'}</span>
            </div>
          </div>
        </div>
      `).join('');
    } catch (e) {
      container.innerHTML = `<div class="empty"><p>加载失败: ${e.message}</p></div>`;
    }
  }

  function setupCreateModal() {
    const modal = document.getElementById('modal-create');
    document.getElementById('btn-create').onclick = () => modal.style.display = 'flex';
    document.getElementById('btn-cancel').onclick = () => modal.style.display = 'none';
    modal.addEventListener('click', e => { if (e.target === modal) modal.style.display = 'none'; });

    document.getElementById('btn-confirm').onclick = async () => {
      const name = document.getElementById('inp-name').value.trim();
      const payload = document.getElementById('inp-payload').value.trim();
      const schedule = document.getElementById('inp-schedule').value.trim() || '24h';

      if (!name || !payload) { alert('名称和执行内容不能为空'); return; }

      try {
        // 调用平台级 API（不是工作区级的）
        const res = await fetch('/api/scheduler/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, payload, schedule, task_type: 'ai_prompt' }),
        });
        if (res.ok) {
          modal.style.display = 'none';
          document.getElementById('inp-name').value = '';
          document.getElementById('inp-payload').value = '';
          loadTasks();
        } else {
          const err = await res.json();
          alert(err.detail || '创建失败');
        }
      } catch (e) { alert('请求失败'); }
    };
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
    setupCreateModal();
  });
})();
