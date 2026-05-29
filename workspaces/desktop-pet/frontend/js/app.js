/**
 * 桌面宠物 — 主入口 v5（CSS sprite 方案，对齐 Petdex）
 */
(function () {
    'use strict';

    let activePet = null;
    let currentPage = 1;
    let currentKind = '';

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    async function init() {
        setupTabs();
        setupSearch();
        await loadStore();
        await loadKinds();
        await loadMyPets();
        await loadActivePet();
    }

    // === Tab ===
    function setupTabs() {
        $$('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                $$('.nav-tab').forEach(t => t.classList.remove('active'));
                $$('.page').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                $(`#page-${tab.dataset.tab}`).classList.add('active');
            });
        });
    }

    // === 搜索 ===
    function setupSearch() {
        let timer;
        $('#search-input').addEventListener('input', (e) => {
            clearTimeout(timer);
            timer = setTimeout(() => doSearch(e.target.value), 400);
        });
        $('#btn-refresh').addEventListener('click', refreshStore);
    }

    async function doSearch(q) {
        if (!q.trim()) { await loadStore(); return; }
        try {
            const data = await PetAPI.searchPets(q);
            renderGallery(data.items || []);
            $('#total-label').textContent = `${data.total} 个结果`;
        } catch (e) { console.error(e); }
    }

    // === 商店 ===
    async function loadStore(page = 1) {
        currentPage = page;
        try {
            const data = await PetAPI.getManifest(page, currentKind);
            if (data.total === 0) { await autoRefresh(); return; }
            renderGallery(data.items);
            renderPagination(data);
            $('#total-label').textContent = `${data.total} 只宠物`;
        } catch (e) { await autoRefresh(); }
    }

    async function autoRefresh() {
        const grid = $('#gallery-grid');
        grid.innerHTML = '<div class="empty-hint"><div class="loading-spinner"></div><p>正在从 Petdex 加载...</p></div>';
        try {
            const result = await PetAPI.refreshManifest();
            if (result.success) {
                const data = await PetAPI.getManifest(1, currentKind);
                renderGallery(data.items);
                renderPagination(data);
                $('#total-label').textContent = `${data.total} 只宠物`;
                await loadKinds();
            } else {
                grid.innerHTML = '<div class="empty-hint"><div class="icon">📡</div><p>无法连接 Petdex</p></div>';
            }
        } catch (e) {
            grid.innerHTML = '<div class="empty-hint"><div class="icon">📡</div><p>网络错误</p></div>';
        }
    }

    async function loadKinds() {
        try {
            const kinds = await PetAPI.getKinds();
            const bar = $('#kind-bar');
            if (!kinds || kinds.length === 0) return;
            bar.innerHTML = '<button class="kind-chip active" data-kind="">全部</button>' +
                kinds.slice(0, 10).map(([k, c]) =>
                    `<button class="kind-chip" data-kind="${k}">${k} (${c})</button>`
                ).join('');
            bar.querySelectorAll('.kind-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    bar.querySelectorAll('.kind-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    currentKind = chip.dataset.kind;
                    loadStore(1);
                });
            });
        } catch (e) { /* optional */ }
    }

    async function refreshStore() {
        const btn = $('#btn-refresh');
        btn.textContent = '刷新中...'; btn.disabled = true;
        try {
            const result = await PetAPI.refreshManifest();
            if (result.success) {
                const data = await PetAPI.getManifest(1, currentKind);
                renderGallery(data.items);
                renderPagination(data);
                $('#total-label').textContent = `${data.total} 只宠物`;
                await loadKinds();
            }
        } catch (e) { /* ignore */ }
        btn.textContent = '↻ 刷新目录'; btn.disabled = false;
    }

    function renderGallery(items) {
        const grid = $('#gallery-grid');
        if (!items || items.length === 0) {
            grid.innerHTML = '<div class="empty-hint"><p>没有找到宠物</p></div>';
            return;
        }
        grid.innerHTML = items.map((p) => `
            <div class="pet-card" data-slug="${p.slug}">
                <div class="card-preview" data-sprite="${p.spritesheetUrl || ''}"></div>
                <div class="card-body">
                    <div class="card-title">${p.displayName || p.slug}</div>
                    <div class="card-meta">
                        <span class="card-kind">${p.kind || ''}</span>
                        <span class="card-author">by ${p.submittedBy || '?'}</span>
                    </div>
                    <button class="btn-adopt" data-slug="${p.slug}">领养</button>
                </div>
            </div>
        `).join('');

        // CSS sprite 动画预览
        grid.querySelectorAll('.card-preview').forEach(container => {
            const url = container.dataset.sprite;
            if (url) createSpritePreview(container, url);
        });

        // 领养按钮
        grid.querySelectorAll('.btn-adopt').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const slug = btn.dataset.slug;
                btn.textContent = '下载中...'; btn.disabled = true;
                try {
                    const result = await PetAPI.downloadPet(slug);
                    btn.textContent = `✓ ${result.display_name}`;
                    btn.classList.add('adopted');
                    await loadMyPets();
                } catch (err) {
                    btn.textContent = err.message.includes('已存在') ? '已拥有' : '失败';
                    setTimeout(() => { btn.textContent = '领养'; btn.disabled = false; }, 2000);
                }
            });
        });
    }

    function renderPagination(data) {
        const el = $('#pagination');
        if (!data.pages || data.pages <= 1) { el.innerHTML = ''; return; }
        el.innerHTML = `
            <button class="page-btn" ${data.page <= 1 ? 'disabled' : ''} data-p="${data.page - 1}">← 上一页</button>
            <span class="page-info">${data.page} / ${data.pages}</span>
            <button class="page-btn" ${data.page >= data.pages ? 'disabled' : ''} data-p="${data.page + 1}">下一页 →</button>
        `;
        el.querySelectorAll('.page-btn').forEach(btn => {
            btn.addEventListener('click', () => { if (!btn.disabled) loadStore(parseInt(btn.dataset.p)); });
        });
    }

    // === 我的宠物 ===
    async function loadMyPets() {
        try {
            const pets = await PetAPI.listPets();
            $('#pet-count').textContent = `${pets.length} 只宠物`;
            const grid = $('#my-pets-grid');
            if (!pets || pets.length === 0) {
                grid.innerHTML = '<div class="empty-hint"><p>还没有宠物</p><p class="sub">去商店领养一只吧 →</p></div>';
                return;
            }
            grid.innerHTML = pets.map(p => `
                <div class="my-pet-card ${p.is_active ? 'active' : ''}" data-id="${p.id}" data-name="${p.name}">
                    <canvas class="thumb-canvas" width="64" height="70"></canvas>
                    <div class="name">${p.display_name || p.name}</div>
                    <div class="actions">
                        ${p.is_active ? '<span class="badge-active">当前</span>' :
                            `<button class="btn-sm" data-act="activate" data-id="${p.id}">选择</button>`}
                        <button class="btn-sm danger" data-act="delete" data-id="${p.id}">×</button>
                    </div>
                </div>
            `).join('');

            grid.querySelectorAll('[data-act="activate"]').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    await PetAPI.activatePet(parseInt(btn.dataset.id));
                    await loadMyPets();
                    await loadActivePet();
                });
            });
            grid.querySelectorAll('[data-act="delete"]').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (confirm('确定删除？')) {
                        await PetAPI.deletePet(parseInt(btn.dataset.id));
                        await loadMyPets();
                        await loadActivePet();
                    }
                });
            });

            // 缩略图
            for (const p of pets) {
                const card = grid.querySelector(`[data-name="${p.name}"]`);
                if (!card) continue;
                const canvas = card.querySelector('.thumb-canvas');
                try {
                    const info = await PetAPI.getSpriteInfo(p.id);
                    createPreviewRenderer(canvas, info.spritesheet_url, 0.33);
                } catch (e) { /* skip */ }
            }
        } catch (e) { console.error(e); }
    }

    // === 活跃宠物详情（CSS sprite 方案，和 Petdex 一样） ===
    async function loadActivePet() {
        try {
            const pet = await PetAPI.getActivePet();
            const detail = $('#pet-detail');
            if (!pet) { detail.style.display = 'none'; return; }
            activePet = pet;
            detail.style.display = '';
            $('#active-pet-name').textContent = pet.display_name || pet.name;
            $('#active-pet-kind').textContent = pet.description || '';
            $('#active-pet-desc').textContent = '';
            updateBars(pet);

            // 用 CSS sprite 方案显示宠物动画（和 Petdex 完全一样）
            const info = await PetAPI.getSpriteInfo(pet.id);
            const sprite = $('#detail-sprite');
            sprite.style.backgroundImage = `url("${info.spritesheet_url}")`;
            // 默认 idle 状态
            setSpriteState(0);

            // 渲染状态切换器
            renderStateSwitcher();
        } catch (e) { console.error(e); }
    }

    /** 设置 CSS sprite 的动画状态行 */
    function setSpriteState(row) {
        const state = PET_STATES[row] || PET_STATES[0];
        const sprite = $('#detail-sprite');
        sprite.style.setProperty('--sprite-row', state.row);
        sprite.style.setProperty('--sprite-frames', state.frames);
        sprite.style.setProperty('--sprite-duration', `${state.durationMs}ms`);
    }

    // 状态切换器
    const STATE_LABELS = [
        { name: '待机', icon: '😊' },
        { name: '向右跑', icon: '🏃' },
        { name: '向左跑', icon: '🏃' },
        { name: '打招呼', icon: '👋' },
        { name: '跳跃', icon: '🦘' },
        { name: '难过', icon: '😢' },
        { name: '等待', icon: '⏳' },
        { name: '奔跑', icon: '💨' },
        { name: '思考', icon: '🤔' },
    ];

    function renderStateSwitcher() {
        const container = $('#state-switcher');
        container.innerHTML = STATE_LABELS.map((s, i) => {
            const state = PET_STATES[i];
            return `<button class="state-btn ${i === 0 ? 'active' : ''}" data-row="${i}">
                <span>${s.icon}</span>
                <span class="state-name">${s.name}</span>
                <span class="state-frames">${state.frames}帧</span>
            </button>`;
        }).join('');

        container.querySelectorAll('.state-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('.state-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                setSpriteState(parseInt(btn.dataset.row));
            });
        });
    }

    function updateBars(pet) {
        ['hunger', 'thirst', 'happiness', 'energy'].forEach(f => {
            const v = pet[f] ?? 100;
            const bar = $(`#bar-${f}`); if (bar) bar.style.width = `${v}%`;
            const num = $(`#val-${f}`); if (num) num.textContent = v;
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
