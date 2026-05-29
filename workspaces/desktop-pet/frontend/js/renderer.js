/**
 * 桌面宠物 — Spritesheet 渲染
 * 商店预览：纯 CSS background-image + steps() 动画（参考 petdex.crafter.run）
 * 互动页：Canvas（需要动态切换状态行）
 */

/**
 * 为商店卡片创建 CSS sprite 动画
 * 直接从 CDN 加载图片（CSS background-image 不受 CORS 限制）
 * @param {HTMLElement} container - .card-preview 容器
 * @param {string} spritesheetUrl - spritesheet 图片 URL（CDN 直链）
 */
function createSpritePreview(container, spritesheetUrl) {
    // 外层 frame：裁剪窗口
    const frame = document.createElement('div');
    frame.className = 'sprite-frame';

    // 内层 sprite：实际动画元素
    const sprite = document.createElement('div');
    sprite.className = 'sprite-anim';
    sprite.style.backgroundImage = `url("${spritesheetUrl}")`;

    frame.appendChild(sprite);
    container.appendChild(frame);
}

// 注入全局 CSS（sprite 动画 keyframes）
(function injectSpriteCSS() {
    if (document.getElementById('sprite-css')) return;
    const style = document.createElement('style');
    style.id = 'sprite-css';
    style.textContent = `
        .sprite-frame {
            width: 96px;
            height: 104px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .sprite-anim {
            width: 192px;
            height: 208px;
            background-size: 1728px 1664px;
            background-repeat: no-repeat;
            background-position: 0 0;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            animation: pet-idle 1.5s steps(9) infinite;
            transform: scale(0.5);
            transform-origin: top left;
        }
        @keyframes pet-idle {
            from { background-position-x: 0; }
            to { background-position-x: -1728px; }
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
        this.columns = options.columns || 9;
        this.rows = options.rows || 8;
        this.fps = options.fps || 4;
        this.scale = options.scale || 1;

        this.currentRow = 0;
        this.currentFrame = 0;
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
            const interval = 1000 / this.fps;
            if (elapsed >= interval) {
                this.currentFrame = (this.currentFrame + 1) % this.columns;
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
            this.currentFrame = 0;
            if (this.loaded) this.render();
        }
    }

    setStateFromStatus(status) {
        if (!status) { this.setState(0); return; }
        const { hunger, thirst, happiness } = status;
        if (hunger !== undefined && hunger < 30) { this.setState(3); return; }
        if (thirst !== undefined && thirst < 30) { this.setState(4); return; }
        if (happiness !== undefined && happiness > 80) { this.setState(5); return; }
        this.setState(0);
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
