/**
 * 桌面宠物 — 主入口（Codex Pet Gallery 风格）
 */
(function () {
    'use strict';

    let activePet = null;
    let mainRenderer = null;
    let interactRenderer = null;
    let cardRenderers = [];
    let currentPage = 1;
    let currentTag = '';

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    async function init() {
        setupTabs();
        setupActions();
        setupSearch();
        await loadStore();
        await loadTags();
        await loadMyPets();
        await loadActivePet();
    }

    // === Tab 切换 ===
    function setupTabs() {
        $$('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                $$('.nav-tab').forEach(t => t.classList.remove('active'));
                $$('.page').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                $(`#page-${tab.dataset.tab}`).classList.add('active');
                if (tab.dataset.tab === 'interact') loadInteractCanvas();
            });
        });
    }

    // === 搜索 ===
    function setupSearch() {
        let timer;
        const input = $('#search-input');
        input.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => searchPets(input.value), 300);
        });
    }

    async function searchPets(q) {
        if (!q.trim()) { await loadStore(); return; }
        try {
            const data = await PetAPI.searchCatalog(q);
            renderGallery(data.items || data);
            $('#total-label').textContent = `${(data.total || data.length)} 个结果`;
        } catch (e) { console.error(e); }
    }

    // === 互动按钮 ===
    function setupActions() {
        $$('.action-btn').forEach(btn => {
            btn.addEventListener('click', () => doInteract(btn.dataset.action));
        });
        $('#btn-refresh').addEventListener('click', refreshStore);
    }

    // === 商店 ===
    async function loadStore(page = 1) {
        currentPage = page;
        try {
            const data = await PetAPI.getCatalog(page);
            renderGallery(data.items);
            renderPagination(data);
            $('#total-label').textContent = `${data.total} 个宠物`;
        } catch (e) { console.error('加载商店失败:', e); }
    }

    async function loadTags() {
        try {
            const res = await fetch('/api/store/tags');
            const tags = await res.json();
            const bar = $('#tag-bar');
            bar.innerHTML = '<button class="tag-chip active" data-tag="">全部</button>' +
                tags.map(t => `<button class="tag-chip" data-tag="${t.name}">${t.name}</button>`).join('');
            bar.querySelectorAll('.tag-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    bar.querySelectorAll('.tag-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    currentTag = chip.dataset.tag;
                    loadStoreWithTag();
                });
            });
        } catch (e) { /* tags are optional */ }
    }

    async function loadStoreWithTag() {
        try {
            const res = await fetch(`/api/store/catalog?page=1&tag=${encodeURIComponent(currentTag)}`);
            const data = await res.json();
            renderGallery(data.items);
            renderPagination(data);
            $('#total-label').textContent = `${data.total} 个宠物`;
        } catch (e) { console.error(e); }
    }

    async function refreshStore() {
        const btn = $('#btn-refresh');
        btn.textContent = '刷新中...';
        btn.disabled = true;
        try {
            await PetAPI.refreshCatalog();
            await loadStore();
            await loadTags();
        } catch (e) { console.error(e); }
        btn.textContent = '↻ 刷新';
        btn.disabled = false;
    }

    function renderGallery(items) {
        // 清理旧渲染器
        cardRenderers.forEach(r => r.destroy());
        cardRenderers = [];

        const grid = $('#gallery-grid');
        if (!items || items.length === 0) {
            grid.innerHTML = '<div class="empty-hint"><p>没有找到宠物</p></div>';
            return;
        }

        grid.innerHTML = items.map((p, i) => `
            <div class="pet-card" data-name="${p.name}" data-idx="${i}">
                <div class="card-preview">
                    <canvas id="preview-${i}" width="96" height="104"></canvas>
                </div>
                <div class="card-body">
                    <div class="card-title">${p.display_name || p.name}</div>
                    <div class="card-desc">${p.description || ''}</div>
                    ${p.tags && p.tags.length ? `<div class="card-tags">${p.tags.map(t => `<span class="card-tag">${t}</span>`).join('')}</div>` : ''}
                    <div class="card-footer">
                        <span class="card-creator">${p.creator || ''}</span>
                        <button class="btn-adopt" data-name="${p.name}">领养</button>
                    </div>
                </div>
            </div>
        `).join('');

        // 为每张卡片加载 spritesheet 动画预览
        items.forEach((p, i) => {
            if (p.spritesheet_url) {
                const canvas = document.getElementById(`preview-${i}`);
                if (canvas) {
                    const r = createPreviewRenderer(canvas, p.spritesheet_url, 0.5);
                    cardRenderers.push(r);
                }
            }
        });

        // 领养按钮
        grid.querySelectorAll('.btn-adopt').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const name = btn.dataset.name;
                btn.textContent = '下载中...';
                btn.disabled = true;
                try {
                    await PetAPI.downloadPet(name);
                    btn.textContent = '✓ 已领养';
                    btn.classList.add('adopted');
                    await loadMyPets();
                    updatePetCount();
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
            <button class="page-btn" ${data.page <= 1 ? 'disabled' : ''} data-page="${data.page - 1}">← 上一页</button>
            <span class="page-info">第 ${data.page} / ${data.pages} 页</span>
            <button class="page-btn" ${data.page >= data.pages ? 'disabled' : ''} data-page="${data.page + 1}">下一页 →</button>
        `;
        el.querySelectorAll('.page-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (!btn.disabled) loadStore(parseInt(btn.dataset.page));
            });
        });
    }

    // === 我的宠物 ===
    async function loadMyPets() {
        try {
            const pets = await PetAPI.listPets();
            updatePetCount(pets.length);
            const grid = $('#my-pets-grid');
            if (!pets || pets.length === 0) {
                grid.innerHTML = '<div class="empty-hint"><p>还没有宠物</p><p class="sub">去宠物库领养一只吧 →</p></div>';
                return;
            }
            grid.innerHTML = pets.map(p => `
                <div class="my-pet-card ${p.is_active ? 'active' : ''}" data-id="${p.id}" data-name="${p.name}">
                    <canvas class="thumb-canvas" width="64" height="72"></canvas>
                    <div class="name">${p.display_name || p.name}</div>
                    <div class="actions">
                        ${p.is_active ? '<span class="badge-active">当前</span>' :
                            `<button class="btn-sm" data-act="activate" data-id="${p.id}">选择</button>`}
                        <button class="btn-sm danger" data-act="delete" data-id="${p.id}">删除</button>
                    </div>
                </div>
            `).join('');

            // 事件
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

    function updatePetCount(count) {
        const el = $('#pet-count');
        if (el) el.textContent = `${count || 0} 只宠物`;
    }

    // === 活跃宠物 ===
    async function loadActivePet() {
        try {
            const pet = await PetAPI.getActivePet();
            const stage = $('#active-stage');
            if (!pet) { stage.style.display = 'none'; return; }
            activePet = pet;
            stage.style.display = '';
            $('#active-pet-name').textContent = pet.display_name || pet.name;
            updateStatusBars(pet);

            const info = await PetAPI.getSpriteInfo(pet.id);
            const canvas = $('#pet-canvas');
            if (mainRenderer) mainRenderer.destroy();
            mainRenderer = new PetRenderer(canvas, {
                frameWidth: info.frame_width, frameHeight: info.frame_height,
                columns: info.columns, rows: info.rows, fps: 8, scale: 1,
            });
            await mainRenderer.load(info.spritesheet_url);
            mainRenderer.setStateFromStatus(pet);
            mainRenderer.play();
        } catch (e) { console.error(e); }
    }

    function updateStatusBars(pet) {
        ['hunger', 'thirst', 'happiness', 'energy'].forEach(f => {
            const val = pet[f] ?? 100;
            const bar = $(`#bar-${f}`);
            const num = $(`#val-${f}`);
            if (bar) bar.style.width = `${val}%`;
            if (num) num.textContent = val;
        });
    }

    // === 互动 ===
    async function loadInteractCanvas() {
        if (!activePet) return;
        try {
            const info = await PetAPI.getSpriteInfo(activePet.id);
            const canvas = $('#interact-canvas');
            if (interactRenderer) interactRenderer.destroy();
            interactRenderer = new PetRenderer(canvas, {
                frameWidth: info.frame_width, frameHeight: info.frame_height,
                columns: info.columns, rows: info.rows, fps: 8, scale: 2,
            });
            await interactRenderer.load(info.spritesheet_url);
            interactRenderer.setStateFromStatus(activePet);
            interactRenderer.play();
        } catch (e) { console.error(e); }
    }

    async function doInteract(action) {
        if (!activePet) { addLog('⚠️ 请先选择一只宠物'); return; }
        try {
            const result = await PetAPI.interact(activePet.id, action);
            const labels = { feed: '🍖 喂食', water: '💧 喂水', pet: '🤚 抚摸', play: '🎾 玩耍' };
            addLog(`✨ ${labels[action] || action} → ${result.effect}`);
            const animRow = { feed: 7, water: 8, pet: 1, play: 1 };
            if (interactRenderer) interactRenderer.playOnce(animRow[action] || 1);
            if (mainRenderer) mainRenderer.playOnce(animRow[action] || 1);
            if (result.state) { Object.assign(activePet, result.state); updateStatusBars(activePet); }
        } catch (e) { addLog(`❌ ${e.message}`); }
    }

    function addLog(msg) {
        const log = $('#interact-log');
        const line = document.createElement('div');
        line.className = 'log-line';
        line.textContent = msg;
        log.prepend(line);
        while (log.children.length > 20) log.removeChild(log.lastChild);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
