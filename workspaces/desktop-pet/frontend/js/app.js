/**
 * 桌面宠物 — 主入口 v3（Petdex manifest 驱动）
 */
(function () {
    'use strict';

    let activePet = null;
    let mainRenderer = null;
    let interactRenderer = null;
    let cardRenderers = [];
    let currentPage = 1;
    let currentKind = '';

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    async function init() {
        setupTabs();
        setupSearch();
        setupActions();
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
                if (tab.dataset.tab === 'interact') loadInteractCanvas();
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

    // === 互动 ===
    function setupActions() {
        $$('.action-btn').forEach(btn => {
            btn.addEventListener('click', () => doInteract(btn.dataset.action));
        });
    }

    // === 商店 ===
    async function loadStore(page = 1) {
        currentPage = page;
        try {
            const data = await PetAPI.getManifest(page, currentKind);
            renderGallery(data.items);
            renderPagination(data);
            $('#total-label').textContent = `${data.total} 只宠物`;
        } catch (e) {
            $('#gallery-grid').innerHTML = '<div class="empty-hint"><p>点击「刷新目录」加载 Petdex 2700+ 宠物</p></div>';
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
        btn.textContent = '刷新中...';
        btn.disabled = true;
        try {
            const result = await PetAPI.refreshManifest();
            if (result.success) {
                await loadStore();
                await loadKinds();
            } else {
                alert(result.message || '刷新失败');
            }
        } catch (e) { alert('网络错误'); }
        btn.textContent = '↻ 刷新目录';
        btn.disabled = false;
    }

    function renderGallery(items) {
        cardRenderers.forEach(r => r.destroy());
        cardRenderers = [];
        const grid = $('#gallery-grid');
        if (!items || items.length === 0) {
            grid.innerHTML = '<div class="empty-hint"><p>没有找到宠物</p></div>';
            return;
        }
        grid.innerHTML = items.map((p, i) => `
            <div class="pet-card" data-slug="${p.slug}">
                <div class="card-preview">
                    <canvas id="preview-${i}" width="96" height="104"></canvas>
                </div>
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

        // 加载 spritesheet 动画预览（通过代理）
        items.forEach((p, i) => {
            if (p.spritesheetUrl) {
                const canvas = document.getElementById(`preview-${i}`);
                if (canvas) {
                    const r = createPreviewRenderer(canvas, p.spritesheetUrl, 0.5);
                    cardRenderers.push(r);
                }
            }
        });

        // 领养按钮
        grid.querySelectorAll('.btn-adopt').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const slug = btn.dataset.slug;
                btn.textContent = '下载中...';
                btn.disabled = true;
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
                    <canvas class="thumb-canvas" width="64" height="72"></canvas>
                    <div class="name">${p.display_name || p.name}</div>
                    <div class="actions">
                        ${p.is_active ? '<span class="badge-active">当前</span>' :
                            `<button class="btn-sm" data-act="activate" data-id="${p.id}">选择</button>`}
                        <button class="btn-sm danger" data-act="delete" data-id="${p.id}">删除</button>
                    </div>
                </div>
            `).join('');
            grid.querySelectorAll('[data-act="activate"]').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    await PetAPI.activatePet(parseInt(btn.dataset.id));
                    await loadMyPets(); await loadActivePet();
                });
            });
            grid.querySelectorAll('[data-act="delete"]').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (confirm('确定删除？')) {
                        await PetAPI.deletePet(parseInt(btn.dataset.id));
                        await loadMyPets(); await loadActivePet();
                    }
                });
            });
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

    // === 活跃宠物 ===
    async function loadActivePet() {
        try {
            const pet = await PetAPI.getActivePet();
            const stage = $('#active-stage');
            if (!pet) { stage.style.display = 'none'; return; }
            activePet = pet;
            stage.style.display = '';
            $('#active-pet-name').textContent = pet.display_name || pet.name;
            updateBars(pet);
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

    function updateBars(pet) {
        ['hunger', 'thirst', 'happiness', 'energy'].forEach(f => {
            const v = pet[f] ?? 100;
            const bar = $(`#bar-${f}`); if (bar) bar.style.width = `${v}%`;
            const num = $(`#val-${f}`); if (num) num.textContent = v;
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
            addLog(`✨ ${labels[action]} → ${result.effect}`);
            if (interactRenderer) interactRenderer.playOnce(1);
            if (mainRenderer) mainRenderer.playOnce(1);
            if (result.state) { Object.assign(activePet, result.state); updateBars(activePet); }
        } catch (e) { addLog(`❌ ${e.message}`); }
    }

    function addLog(msg) {
        const log = $('#interact-log');
        const el = document.createElement('div');
        el.className = 'log-line';
        el.textContent = msg;
        log.prepend(el);
        while (log.children.length > 20) log.removeChild(log.lastChild);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
