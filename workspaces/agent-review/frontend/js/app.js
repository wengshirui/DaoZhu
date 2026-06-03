/**
 * Agent 成长工作�?�?前端
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
            <div class="stat-card__meta">${s.call_count} �?/div>
          </div>
        `;
      }).join('');
    } catch (e) {
      grid.innerHTML = `<p class="muted">加载失败</p>`;
    }
  }

  async function loadReviews() {
    const list = document.getElementById('review-list');
    try {
      const res = await fetch(`${API_BASE}/reports`);
      const data = await res.json();
      const reviews = data.reviews || [];

      if (reviews.length === 0) {
        list.innerHTML = '<div class="empty"><p>暂无成长记录</p><p class="sub">点击"立即成长"生成第一份报�?/p></div>';
        return;
      }

      list.innerHTML = reviews.map(r => {
        const suggestions = r.suggestions || [];
        const autoActions = r.auto_executed || [];
        const insights = r.growth_insights || {};

        // 自动执行动作
        const autoHtml = autoActions.length > 0
          ? autoActions.map(a => `<div class="auto-action">${a}</div>`).join('')
          : '';

        // 建议
        const sugHtml = suggestions.length > 0
          ? suggestions.map((s, idx) => {
              const icon = s.level === 'green' ? '🟢' : s.level === 'yellow' ? '🟡' : '🔴';
              const btn = (s.level === 'yellow' && !s.executed)
                ? `<button class="btn-confirm" data-review="${r.id}" data-idx="${idx}">确认</button>`
                : (s.executed ? `<span class="executed-tag">�?${s.result || ''}</span>` : '');
              return `<div class="suggestion">${icon} ${s.text} ${btn}</div>`;
            }).join('')
          : '';

        // 洞察数据
        let insightHtml = '';
        if (insights.patterns && insights.patterns.length > 0) {
          insightHtml = `<div class="insights">
            <span class="insight-tag">🎯 ${insights.patterns[0][0]}: ${insights.patterns[0][1]}�?/span>
            ${insights.peak_hour !== null ? `<span class="insight-tag">�?高峰 ${insights.peak_hour}:00</span>` : ''}
            ${insights.repeated_count ? `<span class="insight-tag">🔁 ${insights.repeated_count} 个重复模�?/span>` : ''}
          </div>`;
        }

        return `
          <div class="review-card">
            <div class="review-card__header">
              <span class="review-card__date">${r.date}</span>
              <span class="review-card__summary">${r.summary}</span>
            </div>
            ${insightHtml}
            ${autoHtml ? `<div class="review-card__auto">${autoHtml}</div>` : ''}
            ${sugHtml ? `<div class="review-card__suggestions">${sugHtml}</div>` : ''}
          </div>
        `;
      }).join('');

      // 绑定确认按钮
      list.querySelectorAll('.btn-confirm').forEach(btn => {
        btn.onclick = async () => {
          const reviewId = btn.dataset.review;
          const idx = parseInt(btn.dataset.idx);
          btn.textContent = '...';
          btn.disabled = true;
          try {
            const res = await fetch(`${API_BASE}/suggestions/${reviewId}/confirm`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ index: idx }),
            });
            const data = await res.json();
            btn.outerHTML = `<span class="executed-tag">�?${data.result || ''}</span>`;
          } catch (e) { btn.textContent = '失败'; }
        };
      });
    } catch (e) {
      list.innerHTML = `<div class="empty">加载失败</div>`;
    }
  }

  async function triggerGrowth() {
    const btn = document.getElementById('btn-review');
    btn.textContent = '分析�?..';
    btn.disabled = true;
    try {
      const res = await fetch(`${API_BASE}/run`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        btn.textContent = '�?完成';
        loadStats();
        loadReviews();
      }
    } catch (e) { btn.textContent = '失败'; }
    setTimeout(() => { btn.textContent = '�?立即成长'; btn.disabled = false; }, 2000);
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadReviews();
    document.getElementById('btn-review').onclick = triggerGrowth;
  });
})();
