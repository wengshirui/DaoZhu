/**
 * 桌面宠物 — Spritesheet 动画渲染器
 * 兼容 Codex Pet 格式（8列×9行 spritesheet）
 */
class PetRenderer {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.spritesheet = null;
        this.frameWidth = options.frameWidth || 192;
        this.frameHeight = options.frameHeight || 208;
        this.columns = options.columns || 8;
        this.rows = options.rows || 9;
        this.fps = options.fps || 5;
        this.scale = options.scale || 1;

        this.currentRow = 0;
        this.currentFrame = 0;
        this.animTimer = null;
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
                resolve();
            };
            img.onerror = () => reject(new Error('加载失败'));
            img.src = url;
        });
    }

    play() {
        if (this.animTimer) return;
        this.animTimer = setInterval(() => {
            this.currentFrame = (this.currentFrame + 1) % this.columns;
            this.render();
        }, 1000 / this.fps);
        this.render();
    }

    stop() {
        if (this.animTimer) {
            clearInterval(this.animTimer);
            this.animTimer = null;
        }
    }

    setState(row) {
        if (row >= 0 && row < this.rows) {
            this.currentRow = row;
            this.currentFrame = 0;
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
        this.currentFrame = 0;
        let framesPlayed = 0;
        const onceTimer = setInterval(() => {
            framesPlayed++;
            if (framesPlayed >= this.columns) {
                clearInterval(onceTimer);
                this.setState(prevRow);
                if (callback) callback();
            }
        }, 1000 / this.fps);
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
 * 快速创建一个预览渲染器（用于商店卡片）
 * 远程 URL 通过后端代理加载（解决 CORS），本地路径直接加载
 */
function createPreviewRenderer(canvas, spritesheetUrl, scale = 0.5) {
    const renderer = new PetRenderer(canvas, { fps: 3, scale });
    let loadUrl = spritesheetUrl;
    // 远程 URL 走代理
    if (spritesheetUrl.startsWith('http')) {
        loadUrl = `/api/proxy/spritesheet?url=${encodeURIComponent(spritesheetUrl)}`;
    }
    renderer.load(loadUrl).then(() => renderer.play()).catch(() => {
        const ctx = canvas.getContext('2d');
        canvas.width = Math.round(192 * scale);
        canvas.height = Math.round(208 * scale);
        ctx.fillStyle = '#12122a';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.font = '24px serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('🐾', canvas.width / 2, canvas.height / 2);
    });
    return renderer;
}
