/**
 * 桌面宠物 — Spritesheet 渲染（对齐 Petdex 标准）
 *
 * 复用 Petdex（petdex.crafter.run）的渲染方案：
 * - 商店预览：纯 CSS background-image + steps() 动画（零 JS 开销）
 * - 互动页：Canvas（需要动态切换状态行）
 *
 * Spritesheet 规格：8列 × 9行，每帧 192×208px，总 1536×1872px
 * 参考：petdex/src/app/globals.css + petdex/src/lib/pet-states.ts
 */

/**
 * Petdex 标准状态定义（来自 petdex/src/lib/pet-states.ts）
 * 每行帧数和时长不同，必须按此表驱动动画
 */
const PET_STATES = [
    { id: "idle",          row: 0, frames: 6, durationMs: 1100 },
    { id: "running-right", row: 1, frames: 8, durationMs: 1060 },
    { id: "running-left",  row: 2, frames: 8, durationMs: 1060 },
    { id: "waving",        row: 3, frames: 4, durationMs: 700  },
    { id: "jumping",       row: 4, frames: 5, durationMs: 840  },
    { id: "failed",        row: 5, frames: 8, durationMs: 1220 },
    { id: "waiting",       row: 6, frames: 6, durationMs: 1010 },
    { id: "running",       row: 7, frames: 6, durationMs: 820  },
    { id: "review",        row: 8, frames: 6, durationMs: 1030 },
];

/**
 * 为商店卡片创建 CSS sprite 动画
 * 直接用 CDN URL（CSS background-image 不受 CORS 限制，无需代理）
 * @param {HTMLElement} container - .card-preview 容器
 * @param {string} spritesheetUrl - spritesheet 图片 URL（CDN 直链）
 * @param {object} options - { scale, stateRow }
 */
function createSpritePreview(container, spritesheetUrl, options = {}) {
    const scale = options.scale || 0.5;
    const stateRow = options.stateRow || 0;
    const state = PET_STATES[stateRow] || PET_STATES[0];

    // 外层 frame：裁剪窗口
    const frame = document.createElement('div');
    frame.className = 'sprite-frame';
    frame.style.setProperty('--pet-scale', scale);

    // 内层 sprite：实际动画元素（通过 CSS 变量控制状态）
    const sprite = document.createElement('div');
    sprite.className = 'sprite-anim';
    sprite.style.backgroundImage = `url("${spritesheetUrl}")`;
    sprite.style.setProperty('--sprite-row', state.row);
    sprite.style.setProperty('--sprite-frames', state.frames);
    sprite.style.setProperty('--sprite-duration', `${state.durationMs}ms`);
    sprite.style.setProperty('--pet-scale', scale);

    frame.appendChild(sprite);
    container.appendChild(frame);
    return { frame, sprite, state };
}

// 注入全局 CSS（sprite 动画 keyframes）— 对齐 Petdex 标准
(function injectSpriteCSS() {
    if (document.getElementById('sprite-css')) return;
    const style = document.createElement('style');
    style.id = 'sprite-css';
    // 复用 Petdex 的 CSS 变量驱动方案（src/app/globals.css）
    style.textContent = `
        .sprite-frame {
            --pet-scale: 0.5;
            width: calc(192px * var(--pet-scale));
            height: calc(208px * var(--pet-scale));
            overflow: hidden;
            contain: layout paint;
        }
        .sprite-anim {
            --sprite-row: 0;
            --sprite-frames: 6;
            --sprite-duration: 1100ms;
            --sprite-y: calc(var(--sprite-row) * -208px);
            --sprite-end-x: calc(var(--sprite-frames) * -192px);
            width: 192px;
            height: 208px;
            background-size: 1536px 1872px;
            background-repeat: no-repeat;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            transform: scale(var(--pet-scale)) translateZ(0);
            transform-origin: top left;
            will-change: background-position;
            animation: pet-state var(--sprite-duration) steps(var(--sprite-frames)) infinite;
        }
        @keyframes pet-state {
            from { background-position: 0 var(--sprite-y); }
            to { background-position: var(--sprite-end-x) var(--sprite-y); }
        }
        @media (prefers-reduced-motion: reduce) {
            .sprite-anim { animation: none; }
        }
    `;
    document.head.appendChild(style);
})();


/**
 * Canvas 渲染器（互动页 + 我的宠物页）
 * 用于需要动态切换状态行的场景
 */
class PetRenderer {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.spritesheet = null;
        this.frameWidth = options.frameWidth || 192;
        this.frameHeight = options.frameHeight || 208;
        this.columns = options.columns || 8;  // 8 列（最大帧数）
        this.rows = options.rows || 9;        // 9 行（9 种状态）
        this.scale = options.scale || 1;

        this.currentRow = 0;
        this.currentFrame = 0;
        this.currentState = PET_STATES[0];
        this.playing = false;
        this.rafId = null;
        this.lastFrameTime = 0;
        this.loaded = false;
    }

    async load(url) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                this.spritesheet = img;
                this.loaded = true;
                if (img.width > 0 && img.height > 0) {
                    this.frameWidth = Math.floor(img.width / this.columns);
                    this.frameHeight = Math.floor(img.height / this.rows);
                }
                this.canvas.width = Math.round(this.frameWidth * this.scale);
                this.canvas.height = Math.round(this.frameHeight * this.scale);
                this.ctx.imageSmoothingEnabled = false;
                this.render();
                resolve();
            };
            img.onerror = () => reject(new Error('加载失败'));
            img.src = url;
        });
    }

    play() {
        if (this.playing) return;
        this.playing = true;
        this.lastFrameTime = performance.now();
        this._tick();
    }

    _tick() {
        if (!this.playing) return;
        this.rafId = requestAnimationFrame((now) => {
            if (!this.playing) return;
            const elapsed = now - this.lastFrameTime;
            // 帧间隔根据当前状态的帧数和时长计算
            const interval = this.currentState.durationMs / this.currentState.frames;
            if (elapsed >= interval) {
                this.currentFrame = (this.currentFrame + 1) % this.currentState.frames;
                this.render();
                this.lastFrameTime = now - (elapsed % interval);
            }
            this._tick();
        });
    }

    stop() {
        this.playing = false;
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }
    }

    setState(row) {
        if (row >= 0 && row < this.rows) {
            this.currentRow = row;
            this.currentState = PET_STATES[row] || PET_STATES[0];
            this.currentFrame = 0;
            if (this.loaded) this.render();
        }
    }

    setStateById(stateId) {
        const state = PET_STATES.find(s => s.id === stateId);
        if (state) this.setState(state.row);
    }

    setStateFromStatus(status) {
        if (!status) { this.setState(0); return; }
        const { hunger, thirst, happiness } = status;
        if (hunger !== undefined && hunger < 30) { this.setState(5); return; }  // failed
        if (thirst !== undefined && thirst < 30) { this.setState(6); return; }  // waiting
        if (happiness !== undefined && happiness > 80) { this.setState(4); return; }  // jumping
        this.setState(0);  // idle
    }

    render() {
        if (!this.loaded || !this.spritesheet) return;
        const w = this.canvas.width;
        const h = this.canvas.height;
        this.ctx.clearRect(0, 0, w, h);
        this.ctx.drawImage(
            this.spritesheet,
            this.currentFrame * this.frameWidth,
            this.currentRow * this.frameHeight,
            this.frameWidth, this.frameHeight,
            0, 0, w, h
        );
    }

    destroy() {
        this.stop();
        this.spritesheet = null;
        this.loaded = false;
    }
}


/**
 * 为"我的宠物"缩略图创建 Canvas 渲染器
 * @param {HTMLCanvasElement} canvas - 缩略图 canvas
 * @param {string} url - spritesheet URL（需走代理）
 * @param {number} scale - 缩放比例（默认 0.33）
 */
async function createPreviewRenderer(canvas, url, scale = 0.33) {
    const renderer = new PetRenderer(canvas, { scale });
    try {
        await renderer.load(url);
        renderer.play();
    } catch (e) {
        // 加载失败静默处理
        console.warn('缩略图加载失败:', e.message);
    }
    return renderer;
}
