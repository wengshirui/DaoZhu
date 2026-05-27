/**
 * 舞台渲染引擎 — Canvas 绘制 + 主循环
 */

(function () {
    const canvas = document.getElementById('stageCanvas');
    const ctx = canvas.getContext('2d');
    const W = 900, H = 520;

    // ===== 生成观众席 =====
    function generateAudience() {
        const rows = document.querySelectorAll('.audience-row');
        rows.forEach((row, ri) => {
            const count = ri === 0 ? 30 : 35;
            for (let i = 0; i < count; i++) {
                const head = document.createElement('div');
                head.className = 'audience-head';
                head.style.transform = `translateY(${Math.random() * 4}px)`;
                row.appendChild(head);
            }
        });
    }

    // ===== 绘制舞台背景 =====
    function drawBackground() {
        // 墙面 — 暖色渐变
        const wallGrad = ctx.createLinearGradient(0, 0, 0, H * 0.7);
        wallGrad.addColorStop(0, "#FFF3D4");
        wallGrad.addColorStop(0.5, "#F5E6C8");
        wallGrad.addColorStop(1, "#E8D5A8");
        ctx.fillStyle = wallGrad;
        ctx.fillRect(0, 0, W, H * 0.7);

        // 墙面纹理（细微噪点）
        ctx.fillStyle = "rgba(139, 107, 66, 0.03)";
        for (let i = 0; i < 60; i++) {
            const rx = Math.random() * W;
            const ry = Math.random() * H * 0.65;
            ctx.fillRect(rx, ry, 2, 2);
        }

        // 踢脚线
        ctx.fillStyle = "#5C3D2E";
        ctx.fillRect(0, H * 0.68 - 8, W, 10);

        // 木地板
        const floorGrad = ctx.createLinearGradient(0, H * 0.68, 0, H);
        floorGrad.addColorStop(0, "#8B6B4A");
        floorGrad.addColorStop(0.3, "#7A5C3E");
        floorGrad.addColorStop(1, "#5C3D2E");
        ctx.fillStyle = floorGrad;
        ctx.fillRect(0, H * 0.68, W, H * 0.32);

        // 地板木纹
        ctx.strokeStyle = "rgba(0,0,0,0.08)";
        ctx.lineWidth = 1;
        for (let i = 0; i < 12; i++) {
            const y = H * 0.68 + i * (H * 0.32 / 12);
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(W, y);
            ctx.stroke();
        }
        // 竖向木板缝
        ctx.strokeStyle = "rgba(0,0,0,0.04)";
        for (let i = 0; i < 8; i++) {
            const x = i * (W / 8) + 20;
            ctx.beginPath();
            ctx.moveTo(x, H * 0.68);
            ctx.lineTo(x, H);
            ctx.stroke();
        }

        // 舞台灯光效果（顶部暖光）
        const lightGrad = ctx.createRadialGradient(W / 2, 0, 50, W / 2, 0, 400);
        lightGrad.addColorStop(0, "rgba(255, 240, 180, 0.15)");
        lightGrad.addColorStop(1, "transparent");
        ctx.fillStyle = lightGrad;
        ctx.fillRect(0, 0, W, H);
    }

    // ===== 绘制对话气泡 =====
    function drawThought() {
        const thought = Director.getCurrentThought();
        if (!thought) return;

        const xm = Entities.xiaoming;
        const bubbleX = xm.x - 10;
        let bubbleY = xm.state === "lying" ? 340 : 280;

        ctx.save();
        ctx.font = "16px 'ZCOOL KuaiLe', sans-serif";
        const metrics = ctx.measureText(thought);
        const bw = metrics.width + 28;
        const bh = 34;

        // 气泡背景
        ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
        ctx.shadowColor = "rgba(0,0,0,0.1)";
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 2;
        ctx.beginPath();
        ctx.roundRect(bubbleX, bubbleY, bw, bh, 12);
        ctx.fill();

        // 气泡尖角
        ctx.shadowBlur = 0;
        ctx.beginPath();
        ctx.moveTo(bubbleX + 20, bubbleY + bh);
        ctx.lineTo(bubbleX + 26, bubbleY + bh + 8);
        ctx.lineTo(bubbleX + 32, bubbleY + bh);
        ctx.closePath();
        ctx.fill();

        // 气泡边框
        ctx.strokeStyle = "rgba(0,0,0,0.08)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(bubbleX, bubbleY, bw, bh, 12);
        ctx.stroke();

        // 文字
        ctx.fillStyle = "#3D2B1F";
        ctx.fillText(thought, bubbleX + 14, bubbleY + 22);

        ctx.restore();
    }

    // ===== 绘制场次信息 =====
    function drawSceneInfo() {
        if (Director.currentIdx < Director.scenes.length) {
            const scene = Director.scenes[Director.currentIdx];
            ctx.save();
            ctx.font = "italic 13px 'Noto Serif SC', serif";
            ctx.fillStyle = "rgba(90, 60, 30, 0.6)";
            ctx.fillText(
                `第${Director.currentIdx + 1}幕 · ${scene.description}`,
                20, 30
            );
            ctx.restore();
        } else {
            ctx.save();
            ctx.font = "bold 16px 'ZCOOL KuaiLe', sans-serif";
            ctx.fillStyle = "rgba(139, 26, 26, 0.7)";
            ctx.fillText("✨ 演出完毕 · 感谢观看 ✨", W / 2 - 100, 30);
            ctx.restore();
        }
    }

    // ===== 更新聚光灯位置 =====
    function updateSpotlight() {
        const spotlight = document.getElementById('spotlight');
        if (!spotlight) return;
        const xm = Entities.xiaoming;
        // 将实体 x 坐标映射到 stage-area 的百分比
        const percent = (xm.x / W) * 100;
        spotlight.style.left = `${percent}%`;
    }

    // ===== 主渲染循环 =====
    function render() {
        ctx.clearRect(0, 0, W, H);

        // 更新逻辑
        Director.updateWalking();

        // 绘制层次：背景 → 道具 → 角色 → UI
        drawBackground();
        Entities.window.draw(ctx);
        Entities.bed.draw(ctx);
        Entities.door.draw(ctx);
        Entities.xiaoming.draw(ctx);
        drawThought();
        drawSceneInfo();

        // 更新聚光灯
        updateSpotlight();

        requestAnimationFrame(render);
    }

    // ===== 初始化 =====
    function init() {
        generateAudience();

        // 绑定重播按钮
        document.getElementById('replayBtn').addEventListener('click', () => {
            Director.replay();
        });

        // 启动渲染循环
        render();

        // 延迟 0.5s 开始演出（让页面加载完成）
        setTimeout(() => Director.start(), 500);
    }

    // DOM 就绪后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
