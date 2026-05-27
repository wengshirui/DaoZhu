/**
 * Canvas 渲染器 — 手绘背景 + 核心角色
 * 负责：场景背景、父亲、儿子的精细绘制
 */
const Renderer = {
    canvas: null,
    ctx: null,
    W: 900,
    H: 460,

    // 角色状态
    father: { x: 340, y: 200, state: 'standing', opacity: 1, scale: 1 },
    son: { x: 540, y: 210, state: 'standing', opacity: 1 },

    init() {
        this.canvas = document.getElementById('canvas');
        this.ctx = this.canvas.getContext('2d');
    },

    // ===== 背景绘制 =====
    drawBackground() {
        const ctx = this.ctx;
        const W = this.W, H = this.H;

        // 冬日天空渐变
        const sky = ctx.createLinearGradient(0, 0, 0, H * 0.55);
        sky.addColorStop(0, '#9EAAB4');
        sky.addColorStop(0.4, '#B8C4CC');
        sky.addColorStop(0.7, '#C8C0B0');
        sky.addColorStop(1, '#A89070');
        ctx.fillStyle = sky;
        ctx.fillRect(0, 0, W, H * 0.55);

        // 远处建筑剪影
        ctx.fillStyle = 'rgba(80,70,60,0.3)';
        this._drawSilhouette(ctx, 0, H*0.35, W, H*0.2);

        // 月台
        const platform = ctx.createLinearGradient(0, H*0.55, 0, H);
        platform.addColorStop(0, '#8B7355');
        platform.addColorStop(0.1, '#7A6345');
        platform.addColorStop(1, '#5C4030');
        ctx.fillStyle = platform;
        ctx.fillRect(0, H*0.55, W, H*0.45);

        // 月台边缘
        ctx.fillStyle = '#4A3728';
        ctx.fillRect(0, H*0.54, W, 6);

        // 铁道（中间凹陷区域）
        ctx.fillStyle = '#3D2B1F';
        ctx.fillRect(0, H*0.55 - 2, W, 4);
        // 铁轨
        ctx.strokeStyle = '#6B5540';
        ctx.lineWidth = 2;
        for (let x = 0; x < W; x += 28) {
            ctx.beginPath();
            ctx.moveTo(x, H*0.55);
            ctx.lineTo(x+16, H*0.55);
            ctx.stroke();
        }

        // 月台地砖纹理
        ctx.strokeStyle = 'rgba(0,0,0,0.05)';
        ctx.lineWidth = 1;
        for (let y = H*0.58; y < H; y += 20) {
            ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke();
        }
        for (let x = 0; x < W; x += 60) {
            ctx.beginPath(); ctx.moveTo(x,H*0.55); ctx.lineTo(x,H); ctx.stroke();
        }
    },

    _drawSilhouette(ctx, x, y, w, h) {
        // 远处建筑群剪影
        ctx.beginPath();
        ctx.moveTo(x, y + h);
        let cx = x;
        while (cx < x + w) {
            const bw = 30 + Math.random() * 50;
            const bh = 20 + Math.random() * h * 0.6;
            ctx.lineTo(cx, y + h - bh);
            ctx.lineTo(cx + bw, y + h - bh);
            cx += bw + 5;
        }
        ctx.lineTo(x + w, y + h);
        ctx.closePath();
        ctx.fill();
    },

    // ===== 场景道具绘制 =====
    drawProps() {
        const ctx = this.ctx;
        const W = this.W, H = this.H;

        // 站台柱子
        this._drawPillar(ctx, 200, H*0.15, H*0.4);
        this._drawPillar(ctx, 650, H*0.15, H*0.4);

        // 枯树（远景）
        this._drawBareTree(ctx, 40, H*0.2, 60);
        this._drawBareTree(ctx, 820, H*0.18, 50);

        // 火车车厢（右侧远景）
        this._drawTrain(ctx, 550, H*0.08, 340, H*0.38);

        // 栅栏/栏杆
        this._drawFence(ctx, 0, H*0.52, W);
    },

    _drawPillar(ctx, x, y, h) {
        ctx.fillStyle = '#5C4030';
        ctx.fillRect(x-6, y, 12, h);
        ctx.fillStyle = '#4A3728';
        ctx.fillRect(x-10, y, 20, 8);
        ctx.fillRect(x-10, y+h-4, 20, 8);
    },

    _drawBareTree(ctx, x, y, h) {
        ctx.save();
        ctx.strokeStyle = '#57534E';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        // 树干
        ctx.beginPath();
        ctx.moveTo(x, y+h);
        ctx.lineTo(x, y+h*0.4);
        ctx.stroke();
        // 枝干
        ctx.lineWidth = 2;
        const branches = [[x,y+h*0.4, x-20,y+h*0.15], [x,y+h*0.5, x+18,y+h*0.25],
                          [x,y+h*0.35, x-12,y], [x,y+h*0.45, x+15,y+h*0.1]];
        for (const [x1,y1,x2,y2] of branches) {
            ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
        }
        ctx.restore();
    },

    _drawTrain(ctx, x, y, w, h) {
        ctx.save();
        // 车身
        ctx.fillStyle = '#4B5563';
        ctx.beginPath();
        ctx.roundRect(x, y+h*0.3, w, h*0.5, 8);
        ctx.fill();
        // 车顶
        ctx.fillStyle = '#374151';
        ctx.beginPath();
        ctx.roundRect(x+10, y+h*0.15, w-20, h*0.2, [8,8,0,0]);
        ctx.fill();
        // 车窗
        ctx.fillStyle = '#FEF3C7';
        for (let i = 0; i < 6; i++) {
            ctx.fillRect(x+30+i*50, y+h*0.38, 30, 22);
        }
        // 车轮
        ctx.fillStyle = '#1F2937';
        for (let i = 0; i < 8; i++) {
            ctx.beginPath();
            ctx.arc(x+40+i*40, y+h*0.82, 10, 0, Math.PI*2);
            ctx.fill();
        }
        ctx.restore();
    },

    _drawFence(ctx, x, y, w) {
        ctx.save();
        ctx.strokeStyle = '#78350F';
        ctx.lineWidth = 2;
        // 横杆
        ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x+w,y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x,y+12); ctx.lineTo(x+w,y+12); ctx.stroke();
        // 竖杆
        for (let px = x; px < x+w; px += 30) {
            ctx.beginPath(); ctx.moveTo(px,y-4); ctx.lineTo(px,y+16); ctx.stroke();
        }
        ctx.restore();
    },

    // ===== 父亲绘制（核心角色）=====
    drawFather() {
        const ctx = this.ctx;
        const f = this.father;
        if (f.opacity <= 0) return;

        ctx.save();
        ctx.globalAlpha = f.opacity;
        const x = f.x, y = f.y;
        const s = f.scale;

        // 攀爬时倾斜
        if (f.state === 'climbing') {
            ctx.translate(x, y);
            ctx.rotate(-0.15);
            ctx.translate(-x, -y);
        }

        // 阴影
        ctx.fillStyle = 'rgba(0,0,0,0.12)';
        ctx.beginPath();
        ctx.ellipse(x, y+70*s, 16*s, 5*s, 0, 0, Math.PI*2);
        ctx.fill();

        // 黑布棉袍（深青色长袍）
        ctx.fillStyle = '#2C3E50';
        ctx.beginPath();
        ctx.roundRect(x-18*s, y-10*s, 36*s, 60*s, 6*s);
        ctx.fill();

        // 黑布大马褂（外层）
        ctx.fillStyle = '#1a1a2e';
        ctx.beginPath();
        ctx.roundRect(x-20*s, y-12*s, 40*s, 50*s, 4*s);
        ctx.fill();
        // 马褂开襟
        ctx.strokeStyle = '#2C3E50';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x, y-12*s);
        ctx.lineTo(x, y+30*s);
        ctx.stroke();

        // 裤子
        ctx.fillStyle = '#1F2937';
        ctx.fillRect(x-14*s, y+38*s, 12*s, 24*s);
        ctx.fillRect(x+2*s, y+38*s, 12*s, 24*s);

        // 鞋
        ctx.fillStyle = '#111';
        ctx.beginPath();
        ctx.ellipse(x-8*s, y+64*s, 8*s, 4*s, 0, 0, Math.PI*2);
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(x+8*s, y+64*s, 8*s, 4*s, 0, 0, Math.PI*2);
        ctx.fill();

        // 头（黑布小帽）
        ctx.fillStyle = '#FDDCB5';
        ctx.beginPath();
        ctx.ellipse(x, y-28*s, 12*s, 14*s, 0, 0, Math.PI*2);
        ctx.fill();
        // 小帽
        ctx.fillStyle = '#111';
        ctx.beginPath();
        ctx.ellipse(x, y-38*s, 14*s, 8*s, 0, Math.PI, Math.PI*2);
        ctx.fill();
        ctx.fillRect(x-14*s, y-38*s, 28*s, 4*s);

        // 手臂
        ctx.fillStyle = '#1a1a2e';
        if (f.state === 'climbing') {
            // 攀爬：双手向上伸
            ctx.fillRect(x-24*s, y-30*s, 8*s, 28*s);
            ctx.fillRect(x+16*s, y-25*s, 8*s, 24*s);
            // 手
            ctx.fillStyle = '#FDDCB5';
            ctx.beginPath(); ctx.arc(x-20*s, y-32*s, 5*s, 0, Math.PI*2); ctx.fill();
            ctx.beginPath(); ctx.arc(x+20*s, y-27*s, 5*s, 0, Math.PI*2); ctx.fill();
        } else if (f.state === 'walking') {
            // 走路摆臂
            ctx.fillRect(x-24*s, y-2*s, 8*s, 20*s);
            ctx.fillRect(x+16*s, y+4*s, 8*s, 20*s);
        } else {
            // 自然下垂
            ctx.fillRect(x-24*s, y, 8*s, 24*s);
            ctx.fillRect(x+16*s, y, 8*s, 24*s);
        }

        // 名牌
        ctx.font = "bold 11px 'Noto Serif SC', serif";
        ctx.fillStyle = 'rgba(44,24,16,0.8)';
        const tw = ctx.measureText('父亲').width;
        ctx.beginPath();
        ctx.roundRect(x-tw/2-6, y-56*s, tw+12, 18, 8);
        ctx.fill();
        ctx.fillStyle = '#F5E6C8';
        ctx.fillText('父亲', x-tw/2, y-42*s);

        ctx.restore();
    },

    // ===== 儿子绘制 =====
    drawSon() {
        const ctx = this.ctx;
        const s = this.son;
        if (s.opacity <= 0) return;

        ctx.save();
        ctx.globalAlpha = s.opacity;
        const x = s.x, y = s.y;

        // 阴影
        ctx.fillStyle = 'rgba(0,0,0,0.1)';
        ctx.beginPath();
        ctx.ellipse(x, y+60, 14, 4, 0, 0, Math.PI*2);
        ctx.fill();

        // 紫毛大衣
        ctx.fillStyle = '#5B21B6';
        ctx.beginPath();
        ctx.roundRect(x-14, y-8, 28, 50, 4);
        ctx.fill();
        // 大衣领子
        ctx.fillStyle = '#7C3AED';
        ctx.beginPath();
        ctx.moveTo(x-8, y-8);
        ctx.lineTo(x, y+2);
        ctx.lineTo(x+8, y-8);
        ctx.closePath();
        ctx.fill();

        // 裤子
        ctx.fillStyle = '#1E3A5F';
        ctx.fillRect(x-10, y+38, 9, 18);
        ctx.fillRect(x+1, y+38, 9, 18);

        // 鞋
        ctx.fillStyle = '#1F2937';
        ctx.beginPath();
        ctx.ellipse(x-5, y+58, 7, 3, 0, 0, Math.PI*2);
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(x+5, y+58, 7, 3, 0, 0, Math.PI*2);
        ctx.fill();

        // 头
        ctx.fillStyle = '#2C1810';
        ctx.beginPath();
        ctx.ellipse(x, y-22, 13, 10, 0, Math.PI, Math.PI*2);
        ctx.fill();
        ctx.fillStyle = '#FDDCB5';
        ctx.beginPath();
        ctx.ellipse(x, y-18, 11, 13, 0, 0, Math.PI*2);
        ctx.fill();

        // 眼睛
        ctx.fillStyle = '#2C1810';
        ctx.beginPath(); ctx.arc(x-4, y-20, 2, 0, Math.PI*2); ctx.fill();
        ctx.beginPath(); ctx.arc(x+4, y-20, 2, 0, Math.PI*2); ctx.fill();

        // 手臂
        ctx.fillStyle = '#5B21B6';
        if (s.state === 'helping') {
            // 搀扶：手伸向左边
            ctx.fillRect(x-22, y+2, 12, 7);
            ctx.fillRect(x+12, y+4, 8, 18);
            // 手
            ctx.fillStyle = '#FDDCB5';
            ctx.beginPath(); ctx.arc(x-24, y+5, 4, 0, Math.PI*2); ctx.fill();
        } else {
            ctx.fillRect(x-18, y, 6, 18);
            ctx.fillRect(x+12, y, 6, 18);
        }

        // 泪水（如果在哭）
        if (s.state === 'crying') {
            ctx.fillStyle = 'rgba(100,160,220,0.7)';
            ctx.beginPath(); ctx.ellipse(x-6, y-14, 2, 3, 0, 0, Math.PI*2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(x+6, y-13, 2, 3, 0, 0, Math.PI*2); ctx.fill();
        }

        // 名牌
        ctx.font = "bold 11px 'Noto Serif SC', serif";
        ctx.fillStyle = 'rgba(44,24,16,0.8)';
        const tw = ctx.measureText('我').width;
        ctx.beginPath();
        ctx.roundRect(x-tw/2-6, y-44, tw+12, 18, 8);
        ctx.fill();
        ctx.fillStyle = '#F5E6C8';
        ctx.fillText('我', x-tw/2, y-30);

        ctx.restore();
    },

    // ===== 橘子 =====
    drawOranges(x, y, visible) {
        if (!visible) return;
        const ctx = this.ctx;
        ctx.save();
        // 3个朱红橘子
        const colors = ['#EA580C', '#F97316', '#DC2626'];
        for (let i = 0; i < 3; i++) {
            ctx.fillStyle = colors[i];
            ctx.beginPath();
            ctx.arc(x + i*14 - 14, y, 8, 0, Math.PI*2);
            ctx.fill();
            // 橘子蒂
            ctx.fillStyle = '#166534';
            ctx.fillRect(x + i*14 - 16, y-9, 4, 4);
        }
        ctx.restore();
    },

    // ===== 主渲染 =====
    render(state) {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.W, this.H);
        this.drawBackground();
        this.drawProps();
        this.drawOranges(state.orangeX || 0, state.orangeY || 0, state.orangeVisible);
        this.drawFather();
        this.drawSon();
    }
};
