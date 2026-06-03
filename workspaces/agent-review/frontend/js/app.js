/**
 * Agent 复盘工作区 — 前端
 */
(function() {
  'use strict';

  const API_BASE = '/ws/agent-review/api';

  async function loadStats() {
    const grid = document.getElementById('stats-grid');
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      const stats = data.tool_stats || [];

      if (stats.length === 0) {
        grid.innerHTML = '<p class="muted">暂无工具使用数据</p>';
        return;
      }

      grid.innerHTML = stats.map(s => {
        const rate = s.success_rate || 100;
        const color = rate >= 90 ? '#10b981' : rate >= 70 ? '#f59e0b' : '#ef4444';
        return `
          <div class="stat-card">
            <div class="stat-card__name">${s.tool_name}</div>
            <div class="stat-card__rate" style="color:${color}">${rate.toFixed(0)}%</div>
            <div class="stat-card__meta">${s.call_count} 次调用</div>
          </div>
        `;
      }).join('');
    } catch (e) {
      grid.innerHTML = `<p class="muted">加载失败: ${e.message}</p>`;
    }
  }

  async function loadReviews() {
    const list = document.getElementById('review-list');
    try {
      const res = await fetch(`${API_BASE}/reviews`);
      const data = await res.json();
      const reviews = data.reviews || [];

      if (reviews.length === 0) {
        list.innerHTML = '<div class="empty"><p>暂无复盘记录</p><p class="sub">点击"立即复盘"生成第一份报告</p></div>';
        return;
      }

      list.innerHTML = reviews.map(r => {
        const suggestions = r.suggestions || [];
        const sugHtml = suggestions.length > 0
          ? suggestions.map((s, idx) => {
              const icon = s.level === 'green' ? '🟢' : s.level === 'yellow' ? '🟡' : '🔴';
              const execBtn = (s.level === 'yellow' && !s.executed)
                ? `<button class="btn-confirm" data-review="${r.id}" data-idx="${idx}">确认执行</button>`
                : (s.executed ? `<span class="executed-tag">✅ ${s.result || '已执行'}</span>` : '');
              return `<div class="suggestion">${icon} ${s.text} ${execBtn}</div>`;
            }).join('')
          : '<div class="suggestion">✅ 无需优化</div>';

        return `
          <div class="review-card">
            <div class="review-card__header">
              <span class="review-card__date">${r.date}</span>
              <span class="review-card__summary">${r.summary}</span>
            </div>
            <div class="review-card__suggestions">${sugHtml}</div>
          </div>
        `;
      }).join('');

      // 绑定确认按钮
      list.querySelectorAll('.btn-confirm').forEach(btn => {
        btn.onclick = async () => {
          const reviewId = btn.dataset.review;
          const idx = parseInt(btn.dataset.idx);
          btn.textContent = '执行中...';
          btn.disabled = true;
          try {
            const res = await fetch(`${API_BASE}/suggestions/${reviewId}/confirm`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ index: idx }),
            });
            const data = await res.json();
            if (data.success) {
              btn.outerHTML = `<span class="executed-tag">✅ ${data.result}</span>`;
            }
          } catch (e) { btn.textContent = '失败'; }
        };
      });
    } catch (e) {
      list.innerHTML = `<div class="empty">加载失败: ${e.message}</div>`;
    }
  }

  async function triggerReview() {
    const btn = document.getElementById('btn-review');
    btn.textContent = '复盘中...';
    btn.disabled = true;
    try {
      const res = await fetch(`${API_BASE}/run`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        btn.textContent = '✅ 完成';
        loadStats();
        loadReviews();
      } else {
        btn.textContent = '失败';
      }
    } catch (e) {
      btn.textContent = '请求失败';
    }
    setTimeout(() => { btn.textContent = '▶ 立即复盘'; btn.disabled = false; }, 2000);
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadReviews();
    document.getElementById('btn-review').onclick = triggerReview;
  });
})();
