/**
 * 浮动宠物 — 复用 Petdex pet-floater.tsx 的物理逻辑
 * 拖拽 + 甩出弹跳 + 点击反应 + 自动状态循环
 */
(function () {
    'use strict';

    // Petdex 标准状态定义
    const PET_STATES = [
        { id: 'idle', row: 0, frames: 6, durationMs: 1100 },
        { id: 'running-right', row: 1, frames: 8, durationMs: 1060 },
        { id: 'running-left', row: 2, frames: 8, durationMs: 1060 },
        { id: 'waving', row: 3, frames: 4, durationMs: 700 },
        { id: 'jumping', row: 4, frames: 5, durationMs: 840 },
        { id: 'failed', row: 5, frames: 8, durationMs: 1220 },
        { id: 'waiting', row: 6, frames: 6, durationMs: 1010 },
        { id: 'running', row: 7, frames: 6, durationMs: 820 },
        { id: 'review', row: 8, frames: 6, durationMs: 1030 },
    ];

    // 物理常量（直接从 Petdex 复制）
    const IDLE_CYCLE = ['idle','idle','idle','idle','waiting','waving','jumping','review','idle'];
    const IDLE_TICK_MIN_MS = 1700;
    const IDLE_TICK_MAX_MS = 3000;
    const REACTION_MS = 1100;
    const RUN_TAIL_MS = 600;
    const SAFE_MARGIN_PX = 12;
    const DRAG_THRESHOLD_PX = 4;
    const SPRITE_SIZE_PX = 110;
    const THROW_MIN_VELOCITY = 0.05;
    const THROW_FRICTION = 0.92;
    const THROW_BOUNCE = -0.5;
    const THROW_SAMPLE_WINDOW_MS = 80;

    class PetFloater {
        constructor(container, spritesheetUrl, petName) {
            this.container = container;
            this.spritesheetUrl = spritesheetUrl;
            this.petName = petName;
            this.pos = { x: 0, y: 0 };
            this.state = 'idle';
            this.dragging = false;
            this.throwing = false;
            this.vx = 0;
            this.vy = 0;
            this.rafId = null;
            this.idleTimer = null;
            this.tailTimer = null;
            this.reactionTimer = null;
            this.idleIndex = 0;

            this._createDOM();
            this._initPosition();
            this._startIdleCycle();
            this._bindEvents();
        }

        _createDOM() {
            // 浮动按钮（和 Petdex 一样用 button 保证可访问性）
            this.el = document.createElement('button');
            this.el.className = 'pet-floater';
            this.el.setAttribute('aria-label', `${this.petName}: 拖拽或点击`);
            this.el.title = `${this.petName}: 拖我玩`;
            this.el.style.touchAction = 'none';

            // 内部 sprite（CSS 动画驱动）
            this.frame = document.createElement('div');
            this.frame.className = 'pet-floater__frame';

            this.sprite = document.createElement('div');
            this.sprite.className = 'pet-floater__sprite';
            this.sprite.style.backgroundImage = `url("${this.spritesheetUrl}")`;

            this.frame.appendChild(this.sprite);
            this.el.appendChild(this.frame);
            this.container.appendChild(this.el);

            this._applyState('idle');
        }

        _initPosition() {
            const rect = this.container.getBoundingClientRect();
            this.bounds = { width: rect.width, height: rect.height };
            this.pos.x = Math.min(rect.width * 0.7, rect.width - SPRITE_SIZE_PX - SAFE_MARGIN_PX);
            this.pos.y = Math.max(SAFE_MARGIN_PX, rect.height - SPRITE_SIZE_PX - 40);
            this._updatePosition();
        }

        _updatePosition() {
            this.el.style.transform = `translate(${this.pos.x}px, ${this.pos.y}px)`;
        }

        _applyState(stateId) {
            this.state = stateId;
            const state = PET_STATES.find(s => s.id === stateId) || PET_STATES[0];
            this.sprite.style.setProperty('--sprite-row', state.row);
            this.sprite.style.setProperty('--sprite-frames', state.frames);
            this.sprite.style.setProperty('--sprite-duration', `${state.durationMs}ms`);
        }

        _clamp(x, y) {
            const maxX = this.bounds.width - SPRITE_SIZE_PX - SAFE_MARGIN_PX;
            const maxY = this.bounds.height - SPRITE_SIZE_PX - SAFE_MARGIN_PX;
            return {
                x: Math.min(Math.max(x, SAFE_MARGIN_PX), maxX),
                y: Math.min(Math.max(y, SAFE_MARGIN_PX), maxY),
            };
        }

        // === 自动状态循环 ===
        _startIdleCycle() {
            if (this.dragging || this.throwing) return;
            const wait = IDLE_TICK_MIN_MS + Math.random() * (IDLE_TICK_MAX_MS - IDLE_TICK_MIN_MS);
            this.idleTimer = setTimeout(() => {
                if (this.dragging || this.throwing) return;
                this.idleIndex = (this.idleIndex + 1) % IDLE_CYCLE.length;
                this._applyState(IDLE_CYCLE[this.idleIndex]);
                this._startIdleCycle();
            }, wait);
        }

        _stopIdleCycle() {
            if (this.idleTimer) { clearTimeout(this.idleTimer); this.idleTimer = null; }
        }

        // === 拖拽 + 甩出 ===
        _bindEvents() {
            this.el.addEventListener('pointerdown', (e) => this._onPointerDown(e));
            // 窗口 resize 时更新边界
            window.addEventListener('resize', () => {
                const rect = this.container.getBoundingClientRect();
                this.bounds = { width: rect.width, height: rect.height };
                const clamped = this._clamp(this.pos.x, this.pos.y);
                this.pos = clamped;
                this._updatePosition();
            });
        }

        _onPointerDown(e) {
            if (e.button !== 0) return;
            e.preventDefault();

            const startX = e.clientX;
            const startY = e.clientY;
            const originX = this.pos.x;
            const originY = this.pos.y;
            let moved = false;
            let lastClientX = startX;
            const samples = [{ time: e.timeStamp, x: originX, y: originY }];

            this._cancelThrow();
            this._stopIdleCycle();
            this._clearTimers();
            this.dragging = true;
            this.el.classList.add('pet-floater--dragging');

            const onMove = (ev) => {
                const dx = ev.clientX - startX;
                const dy = ev.clientY - startY;
                if (!moved && Math.abs(dx) + Math.abs(dy) > DRAG_THRESHOLD_PX) moved = true;

                const clamped = this._clamp(originX + dx, originY + dy);
                this.pos = clamped;
                this._updatePosition();

                // 采样速度
                samples.push({ time: ev.timeStamp, x: clamped.x, y: clamped.y });
                while (samples.length > 4) samples.shift();

                // 方向动画
                const horizontal = ev.clientX - lastClientX;
                lastClientX = ev.clientX;
                if (horizontal > 1) this._applyState('running-right');
                else if (horizontal < -1) this._applyState('running-left');
            };

            const onUp = (ev) => {
                window.removeEventListener('pointermove', onMove);
                window.removeEventListener('pointerup', onUp);
                window.removeEventListener('pointercancel', onUp);
                this.dragging = false;
                this.el.classList.remove('pet-floater--dragging');

                if (!moved) {
                    // 点击反应
                    this._triggerReaction();
                    return;
                }

                // 计算释放速度
                const recent = samples.filter(s => ev.timeStamp - s.time <= THROW_SAMPLE_WINDOW_MS);
                const vs = recent.length > 1 ? recent : samples;
                const first = vs[0], last = vs[vs.length - 1];
                const dt = last.time - first.time;
                const vx = dt > 0 ? (last.x - first.x) / dt : 0;
                const vy = dt > 0 ? (last.y - first.y) / dt : 0;

                if (Math.abs(vx) < THROW_MIN_VELOCITY && Math.abs(vy) < THROW_MIN_VELOCITY) {
                    this._scheduleIdle();
                    return;
                }

                // 甩出！
                this.vx = vx;
                this.vy = vy;
                this.throwing = true;
                this._throwLoop(performance.now());
            };

            window.addEventListener('pointermove', onMove);
            window.addEventListener('pointerup', onUp);
            window.addEventListener('pointercancel', onUp);
        }

        // === 甩出物理（惯性 + 摩擦 + 弹跳） ===
        _throwLoop(prevTime) {
            this.rafId = requestAnimationFrame((now) => {
                if (!this.throwing) return;
                const dt = Math.max(now - prevTime, 1);

                const maxX = this.bounds.width - SPRITE_SIZE_PX - SAFE_MARGIN_PX;
                const maxY = this.bounds.height - SPRITE_SIZE_PX - SAFE_MARGIN_PX;

                let nx = this.pos.x + this.vx * dt;
                let ny = this.pos.y + this.vy * dt;

                // 边界弹跳
                if (nx < SAFE_MARGIN_PX || nx > maxX) this.vx *= THROW_BOUNCE;
                if (ny < SAFE_MARGIN_PX || ny > maxY) this.vy *= THROW_BOUNCE;

                nx = Math.min(Math.max(nx, SAFE_MARGIN_PX), maxX);
                ny = Math.min(Math.max(ny, SAFE_MARGIN_PX), maxY);

                this.pos = { x: nx, y: ny };
                this._updatePosition();

                // 方向动画
                if (this.vx > 0.01) this._applyState('running-right');
                else if (this.vx < -0.01) this._applyState('running-left');

                // 摩擦减速
                const friction = Math.pow(THROW_FRICTION, dt / (1000 / 60));
                this.vx *= friction;
                this.vy *= friction;

                // 停止条件
                if (Math.abs(this.vx) < THROW_MIN_VELOCITY && Math.abs(this.vy) < THROW_MIN_VELOCITY) {
                    this._cancelThrow();
                    this._scheduleIdle();
                    return;
                }

                this._throwLoop(now);
            });
        }

        _cancelThrow() {
            if (this.rafId) { cancelAnimationFrame(this.rafId); this.rafId = null; }
            this.vx = 0;
            this.vy = 0;
            this.throwing = false;
        }

        // === 点击反应 ===
        _triggerReaction() {
            this._clearTimers();
            this._applyState(this.state === 'waving' ? 'jumping' : 'waving');
            this.reactionTimer = setTimeout(() => {
                this._applyState('idle');
                this._startIdleCycle();
            }, REACTION_MS);
        }

        _scheduleIdle() {
            this.tailTimer = setTimeout(() => {
                this._applyState('idle');
                this._startIdleCycle();
            }, RUN_TAIL_MS);
        }

        _clearTimers() {
            if (this.tailTimer) { clearTimeout(this.tailTimer); this.tailTimer = null; }
            if (this.reactionTimer) { clearTimeout(this.reactionTimer); this.reactionTimer = null; }
        }

        destroy() {
            this._cancelThrow();
            this._stopIdleCycle();
            this._clearTimers();
            if (this.el && this.el.parentNode) this.el.parentNode.removeChild(this.el);
        }
    }

    // === 初始化：加载活跃宠物并创建浮动实例 ===
    async function initPetFloater() {
        try {
            const res = await fetch('/api/pet/active');
            const data = await res.json();
            if (!data.pet) return; // 没有活跃宠物

            const container = document.querySelector('.workspace') || document.body;
            window._petFloater = new PetFloater(
                container,
                data.pet.spritesheetUrl,
                data.pet.displayName
            );
        } catch (e) {
            // 静默失败，宠物是锦上添花
            console.debug('Pet floater init skipped:', e.message);
        }
    }

    // 页面加载后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPetFloater);
    } else {
        initPetFloater();
    }
})();
