/**
 * 桌面宠物 — 主入口
 */
(function () {
    'use strict';

    let activePet = null;
    let mainRenderer = null;
    let interactRenderer = null;

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    async function init() {
        setupTabs();
        setupDownload();
        setupActions();
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

    // === 商店下载 ===
    function setupDownload() {
        const btn = $('#btn-download');
        const input = $('#download-name');
        btn.addEventListener('click', () => doDownload());
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') doDownload();
        });
    }

    async function doDownload() {
        const input = $('#download-name');
        const status = $('#download-status');
        const name = input.value.trim().toLowerCase().replace(/\s+/g, '-');
        if (!name) {
            status.textContent = '⚠️ 请输入宠物名称';
            status.className = 'download-status error';
            return;
        }
        status.textContent = '⏳ 正在下载...';
        status.className = 'download-status loading';
        try {
            const result = await PetAPI.downloadPet(name);
            status.textContent = `✅ 已下载「${name}」(${result.size_kb}KB)`;
            status.className = 'download-status success';
            input.value = '';
            await loadMyPets();
            await loadActivePet();
        } catch (e) {
            status.textContent = `❌ ${e.message}`;
            status.className = 'download-status error';
        }
    }

    // === 互动按钮 ===
    function setupActions() {
        $$('.action-btn').forEach(btn => {
            btn.addEventListener('click', () => doInteract(btn.dataset.action));
        });
    }

    // === 我的宠物 ===
    async function loadMyPets() {
        try {
            const pets = await PetAPI.listPets();
            const grid = $('#my-pets-grid');
            if (!pets || pets.length === 0) {
                grid.innerHTML = '<div class="empty-hint"><p>还没有宠物</p><p class="sub">去商店浏览并下载一只吧 →</p></div>';
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

            // 事件绑定
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
                    if (confirm('确定删除这只宠物吗？')) {
                        await PetAPI.deletePet(parseInt(btn.dataset.id));
                        await loadMyPets();
                        await loadActivePet();
                    }
                });
            });

            // 缩略图动画
            for (const p of pets) {
                const card = grid.querySelector(`[data-name="${p.name}"]`);
                if (!card) continue;
                const canvas = card.querySelector('.thumb-canvas');
                try {
                    const info = await PetAPI.getSpriteInfo(p.id);
                    createPreviewRenderer(canvas, info.spritesheet_url, 0.33);
                } catch (e) { /* skip */ }
            }
        } catch (e) { console.error('加载宠物列表失败:', e); }
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
