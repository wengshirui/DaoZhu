/**
 * 桌面宠物 — Spritesheet 动画渲染器
 * 使用纯 CSS background-position + steps() 动画（参考 codex-pet.org）
 * 零 Canvas、零 JS 定时器、零闪烁
 */

/**
 * 为商店卡片创建 CSS sprite 动画预览
 * @param {HTMLElement} container - 预览容器 div
 * @param {string} spritesheetUrl - spritesheet 图片 URL
 * @param {object} options - { width, height, columns, rows, fps }
 */
function createSpritePreview(container, spritesheetUrl, options = {}) {
    const cols = options.columns || 9;
    const rows = options.rows || 8;
    const fps = options.fps || 4;
    const width = options.width || 128;
    const height = options.height || 139;

    // 远程 URL 走代理
    let imgUrl = spritesheetUrl;
    if (spritesheetUrl.startsWith('http')) {
        imgUrl = `/api/proxy/spritesheet?url=${encodeURIComponent(spritesheetUrl)}`;
    }

    // 创建 sprite 元素
    const sprite = document.createElement('span');
    sprite.className = 'sprite-anim';
    sprite.style.display = 'inline-block';
    sprite.style.width = width + 'px';
    sprite.style.height = height + 'px';
    sprite.style.backgroundImage = `url("${imgUrl}")`;
    sprite.style.backgroundSize = `${cols * 100}% ${rows * 100}%`;
    sprite.style.backgroundPosition = '0 0';
    sprite.style.backgroundRepeat = 'no-repeat';
    sprite.style.imageRendering = 'pixelated';

    // 动画：只播放第一行（idle），cols 帧循环
    const duration = cols / fps; // 秒
    sprite.style.animation = `sprite-row-${cols} ${duration}s steps(${cols}) infinite`;

    container.innerHTML = '';
    container.appendChild(sprite);

    return sprite;
}

/**
 * 注入全局 CSS keyframes（只需一次）
 */
(function injectKeyframes() {
    if (document.getElementById('sprite-keyframes')) return;
    const style = document.createElement('style');
    style.id = 'sprite-keyframes';
    // 为不同列数生成 keyframes
    style.textContent = `
        @keyframes sprite-row-8 {
            from { background-position-x: 0; }
            to { background-position-x: -800%; }
        }
        @keyframes sprite-row-9 {
            from { background-position-x: 0; }
            to { background-position-x: -900%; }
        }
        .sprite-anim {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
        }
    `;
    document.head.appendChild(style);
})();


/**
 * Canvas 渲染器（用于互动页大画面，需要动态切换状态行）
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

    playOnce(row, callback) {
        const prevRow = this.currentRow;
        this.setState(row);
        let count = 0;
        const check = () => {
            count++;
            if (count >= this.columns) {
                this.setState(prevRow);
                if (callback) callback();
                this._onFrame = null;
            }
        };
        this._onFrame = check;
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
        if (this._onFrame) this._onFrame();
    }

    destroy() {
        this.stop();
        this.spritesheet = null;
        this.loaded = false;
        this._onFrame = null;
    }
}
