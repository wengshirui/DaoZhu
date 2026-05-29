/**
 * 桌面宠物 — Spritesheet 动画渲染器
 * 使用 requestAnimationFrame 驱动，平滑无跳帧
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
        this.frameInterval = 1000 / this.fps;
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
                this.ctx.imageSmoothingEnabled = false;
                // 立即渲染第一帧（无闪烁）
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
            if (elapsed >= this.frameInterval) {
                this.currentFrame = (this.currentFrame + 1) % this.columns;
                this.render();
                this.lastFrameTime = now - (elapsed % this.frameInterval);
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
        if (hunger !== undefined && hunger < 30) { this.setState(2); return; }
        if (thirst !== undefined && thirst < 30) { this.setState(3); return; }
        if (happiness !== undefined && happiness > 80) { this.setState(1); return; }
        this.setState(0);
    }

    playOnce(row, callback) {
        const prevRow = this.currentRow;
        this.setState(row);
        let framesPlayed = 0;
        const origFps = this.fps;
        // 临时用稍快的帧率播放一次性动画
        this.fps = 6;
        this.frameInterval = 1000 / this.fps;
        const checkDone = () => {
            framesPlayed++;
            if (framesPlayed >= this.columns) {
                this.fps = origFps;
                this.frameInterval = 1000 / this.fps;
                this.setState(prevRow);
                if (callback) callback();
            }
        };
        // 监听帧变化
        this._onceCallback = checkDone;
    }

    render() {
        if (!this.loaded || !this.spritesheet) return;
        const w = this.canvas.width;
        const h = this.canvas.height;
        // 直接绘制，不 clearRect（spritesheet 帧本身有透明背景会自动覆盖）
        // 但为了安全还是清一下
        this.ctx.clearRect(0, 0, w, h);
        this.ctx.drawImage(
            this.spritesheet,
            this.currentFrame * this.frameWidth,
            this.currentRow * this.frameHeight,
            this.frameWidth, this.frameHeight,
            0, 0, w, h
        );
        // 一次性动画回调
        if (this._onceCallback) {
            this._onceCallback();
        }
    }

    destroy() {
        this.stop();
        this.spritesheet = null;
        this.loaded = false;
        this._onceCallback = null;
    }
}

/**
 * 创建预览渲染器（商店卡片用）
 */
function createPreviewRenderer(canvas, spritesheetUrl, scale = 0.5) {
    // 预设固定尺寸
    const w = Math.round(192 * scale);
    const h = Math.round(208 * scale);
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    // 先画一个淡色占位背景
    ctx.fillStyle = '#eaf1ff';
    ctx.fillRect(0, 0, w, h);

    const renderer = new PetRenderer(canvas, { fps: 4, scale });
    let loadUrl = spritesheetUrl;
    if (spritesheetUrl.startsWith('http')) {
        loadUrl = `/api/proxy/spritesheet?url=${encodeURIComponent(spritesheetUrl)}`;
    }
    renderer.load(loadUrl).then(() => {
        renderer.play();
    }).catch(() => {
        // 加载失败保持占位
        ctx.fillStyle = '#eaf1ff';
        ctx.fillRect(0, 0, w, h);
        ctx.font = '20px serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('🐾', w / 2, h / 2);
    });
    return renderer;
}
