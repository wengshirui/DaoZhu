/**
 * 实体系统 — 定义舞台上的所有角色和道具
 * 采用简笔画/涂鸦风格绘制
 */

const Entities = {
    // ===== 小明（主角）=====
    xiaoming: {
        type: "human",
        name: "小明",
        x: 280,
        y: 380,
        state: "lying", // lying, sitting, standing, walking, opening_door, idle
        facingRight: true,
        walkTargetX: null,
        walkSpeed: 2.5,

        draw(ctx) {
            const x = this.x;
            let y = this.y;

            // 根据状态调整 y 基线
            if (this.state === "standing" || this.state === "walking" ||
                this.state === "opening_door" || this.state === "idle") y = 342;
            if (this.state === "sitting") y = 372;
            if (this.state === "lying") y = 390;

            ctx.save();

            // === 身体阴影（地面投影）===
            if (this.state !== "lying") {
                ctx.fillStyle = "rgba(0,0,0,0.12)";
                ctx.beginPath();
                ctx.ellipse(x, y + 22, 16, 5, 0, 0, Math.PI * 2);
                ctx.fill();
            }

            // === 头部 ===
            // 头发
            ctx.fillStyle = "#2C1810";
            ctx.beginPath();
            ctx.ellipse(x, y - 38, 16, 14, 0, Math.PI, Math.PI * 2);
            ctx.fill();

            // 脸
            ctx.fillStyle = "#FDDCB5";
            ctx.beginPath();
            ctx.ellipse(x, y - 30, 14, 16, 0, 0, Math.PI * 2);
            ctx.fill();

            // 腮红
            ctx.fillStyle = "rgba(255, 150, 130, 0.3)";
            ctx.beginPath();
            ctx.ellipse(x - 9, y - 26, 5, 3, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.ellipse(x + 9, y - 26, 5, 3, 0, 0, Math.PI * 2);
            ctx.fill();

            // 眼睛（根据状态变化）
            ctx.fillStyle = "#2C1810";
            if (this.state === "lying") {
                // 闭眼 — 弧线
                ctx.beginPath();
                ctx.arc(x - 5, y - 32, 3, 0, Math.PI);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(x + 5, y - 32, 3, 0, Math.PI);
                ctx.stroke();
            } else {
                // 睁眼 — 圆点
                ctx.beginPath();
                ctx.arc(x - 5, y - 33, 2.5, 0, Math.PI * 2);
                ctx.fill();
                ctx.beginPath();
                ctx.arc(x + 5, y - 33, 2.5, 0, Math.PI * 2);
                ctx.fill();
                // 眼睛高光
                ctx.fillStyle = "#FFF";
                ctx.beginPath();
                ctx.arc(x - 4, y - 34, 1, 0, Math.PI * 2);
                ctx.fill();
                ctx.beginPath();
                ctx.arc(x + 6, y - 34, 1, 0, Math.PI * 2);
                ctx.fill();
            }

            // 嘴巴
            ctx.strokeStyle = "#C0705A";
            ctx.lineWidth = 1.5;
            ctx.lineCap = "round";
            if (this.state === "idle") {
                // 微笑
                ctx.beginPath();
                ctx.arc(x, y - 24, 5, 0.2, Math.PI - 0.2);
                ctx.stroke();
            } else {
                // 小嘴
                ctx.beginPath();
                ctx.arc(x, y - 25, 3, 0.3, Math.PI - 0.3);
                ctx.stroke();
            }

            // === 身体 ===
            if (this.state === "lying") {
                // 躺着 — 被子
                ctx.fillStyle = "#7EB5A0";
                ctx.beginPath();
                ctx.roundRect(x - 20, y - 14, 50, 24, 6);
                ctx.fill();
                // 被子花纹
                ctx.strokeStyle = "rgba(255,255,255,0.3)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(x - 10, y - 8);
                ctx.lineTo(x + 20, y - 8);
                ctx.stroke();
            } else {
                // 上衣
                ctx.fillStyle = "#5B9BD5";
                ctx.beginPath();
                ctx.roundRect(x - 12, y - 16, 24, 26, 4);
                ctx.fill();
                // 衣服细节 — 领口
                ctx.fillStyle = "#FFF";
                ctx.beginPath();
                ctx.moveTo(x - 4, y - 16);
                ctx.lineTo(x, y - 10);
                ctx.lineTo(x + 4, y - 16);
                ctx.closePath();
                ctx.fill();

                // 裤子
                ctx.fillStyle = "#4A6741";
                ctx.fillRect(x - 10, y + 8, 9, 16);
                ctx.fillRect(x + 1, y + 8, 9, 16);

                // 手臂
                ctx.fillStyle = "#FDDCB5";
                if (this.state === "walking") {
                    // 摆臂
                    ctx.fillRect(x - 18, y - 10, 7, 14);
                    ctx.fillRect(x + 11, y - 6, 7, 14);
                } else if (this.state === "opening_door") {
                    // 伸手开门
                    ctx.fillRect(x + 11, y - 14, 18, 7);
                } else {
                    // 自然下垂
                    ctx.fillRect(x - 17, y - 10, 6, 16);
                    ctx.fillRect(x + 11, y - 10, 6, 16);
                }
            }

            // === 睡帽（躺着或坐着时）===
            if (this.state === "lying" || this.state === "sitting") {
                ctx.fillStyle = "#E8A838";
                ctx.beginPath();
                ctx.moveTo(x - 12, y - 44);
                ctx.lineTo(x + 4, y - 56);
                ctx.lineTo(x + 14, y - 44);
                ctx.closePath();
                ctx.fill();
                // 帽球
                ctx.fillStyle = "#FFF";
                ctx.beginPath();
                ctx.arc(x + 4, y - 56, 4, 0, Math.PI * 2);
                ctx.fill();
            }

            ctx.restore();
        }
    },

    // ===== 门 =====
    door: {
        type: "door",
        name: "房门",
        x: 650,
        y: 180,
        width: 60,
        height: 160,
        isOpen: false,

        open() {
            this.isOpen = true;
        },
        close() {
            this.isOpen = false;
        },

        draw(ctx) {
            const { x, y, width, height } = this;
            ctx.save();

            if (!this.isOpen) {
                // 关闭状态 — 木门
                // 门框
                ctx.fillStyle = "#5C3D2E";
                ctx.fillRect(x - 4, y - 4, width + 8, height + 8);

                // 门板
                const grad = ctx.createLinearGradient(x, y, x + width, y);
                grad.addColorStop(0, "#8B6B4A");
                grad.addColorStop(0.5, "#A0825E");
                grad.addColorStop(1, "#7A5C3E");
                ctx.fillStyle = grad;
                ctx.fillRect(x, y, width, height);

                // 门板纹理
                ctx.strokeStyle = "rgba(0,0,0,0.15)";
                ctx.lineWidth = 1;
                ctx.strokeRect(x + 8, y + 10, width - 16, height / 2 - 15);
                ctx.strokeRect(x + 8, y + height / 2 + 5, width - 16, height / 2 - 15);

                // 门把手
                ctx.fillStyle = "#D4A843";
                ctx.beginPath();
                ctx.ellipse(x + width - 14, y + height / 2, 5, 7, 0, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = "#B8922E";
                ctx.beginPath();
                ctx.arc(x + width - 14, y + height / 2, 3, 0, Math.PI * 2);
                ctx.fill();
            } else {
                // 打开状态 — 透视效果
                // 门框
                ctx.fillStyle = "#5C3D2E";
                ctx.fillRect(x - 4, y - 4, width + 8, height + 8);

                // 门后空间（深色）
                ctx.fillStyle = "#2A1F15";
                ctx.fillRect(x, y, width, height);

                // 门板（透视缩短）
                ctx.fillStyle = "#A0825E";
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(x + 20, y + 8);
                ctx.lineTo(x + 20, y + height - 8);
                ctx.lineTo(x, y + height);
                ctx.closePath();
                ctx.fill();

                // 门后光线
                const lightGrad = ctx.createLinearGradient(x + 20, y, x + width, y);
                lightGrad.addColorStop(0, "rgba(255,240,180,0.1)");
                lightGrad.addColorStop(1, "rgba(255,240,180,0.4)");
                ctx.fillStyle = lightGrad;
                ctx.fillRect(x + 20, y, width - 20, height);
            }

            ctx.restore();
        }
    },

    // ===== 床 =====
    bed: {
        type: "prop",
        name: "床",
        x: 200,
        y: 340,
        w: 130,
        h: 70,

        draw(ctx) {
            const { x, y, w, h } = this;
            ctx.save();

            // 床架
            ctx.fillStyle = "#6B4226";
            ctx.beginPath();
            ctx.roundRect(x, y + 10, w, h - 10, 6);
            ctx.fill();

            // 床垫
            ctx.fillStyle = "#F5E6C8";
            ctx.beginPath();
            ctx.roundRect(x + 6, y + 4, w - 12, h - 20, 4);
            ctx.fill();

            // 被子
            ctx.fillStyle = "#7EB5A0";
            ctx.beginPath();
            ctx.roundRect(x + 10, y + 8, w - 50, h - 26, 4);
            ctx.fill();
            // 被子褶皱
            ctx.strokeStyle = "rgba(0,0,0,0.1)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x + 30, y + 12);
            ctx.quadraticCurveTo(x + 40, y + 20, x + 35, y + h - 22);
            ctx.stroke();

            // 枕头
            ctx.fillStyle = "#FFF9E8";
            ctx.beginPath();
            ctx.ellipse(x + w - 25, y + 18, 22, 12, -0.1, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "rgba(0,0,0,0.08)";
            ctx.stroke();

            // 床头板
            ctx.fillStyle = "#5C3D2E";
            ctx.beginPath();
            ctx.roundRect(x + w - 8, y - 20, 12, h + 20, [6, 6, 0, 0]);
            ctx.fill();

            ctx.restore();
        }
    },

    // ===== 窗户 =====
    window: {
        type: "prop",
        name: "窗户",
        x: 80,
        y: 80,
        w: 110,
        h: 120,

        draw(ctx) {
            const { x, y, w, h } = this;
            ctx.save();

            // 窗框
            ctx.fillStyle = "#F5E6C8";
            ctx.fillRect(x - 6, y - 6, w + 12, h + 12);
            ctx.fillStyle = "#5C3D2E";
            ctx.fillRect(x - 4, y - 4, w + 8, h + 8);

            // 天空渐变
            const skyGrad = ctx.createLinearGradient(x, y, x, y + h);
            skyGrad.addColorStop(0, "#87CEEB");
            skyGrad.addColorStop(0.6, "#FDB777");
            skyGrad.addColorStop(1, "#FF9A76");
            ctx.fillStyle = skyGrad;
            ctx.fillRect(x, y, w, h);

            // 太阳
            ctx.fillStyle = "#FFE066";
            ctx.beginPath();
            ctx.arc(x + w - 25, y + 30, 18, 0, Math.PI * 2);
            ctx.fill();
            // 光芒
            ctx.strokeStyle = "rgba(255,224,102,0.5)";
            ctx.lineWidth = 2;
            for (let i = 0; i < 8; i++) {
                const angle = (i / 8) * Math.PI * 2;
                ctx.beginPath();
                ctx.moveTo(x + w - 25 + Math.cos(angle) * 22, y + 30 + Math.sin(angle) * 22);
                ctx.lineTo(x + w - 25 + Math.cos(angle) * 28, y + 30 + Math.sin(angle) * 28);
                ctx.stroke();
            }

            // 窗格
            ctx.strokeStyle = "#5C3D2E";
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(x + w / 2, y);
            ctx.lineTo(x + w / 2, y + h);
            ctx.moveTo(x, y + h / 2);
            ctx.lineTo(x + w, y + h / 2);
            ctx.stroke();

            // 窗帘
            ctx.fillStyle = "rgba(139, 26, 26, 0.6)";
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.quadraticCurveTo(x + 15, y + h * 0.4, x + 8, y + h);
            ctx.lineTo(x, y + h);
            ctx.closePath();
            ctx.fill();

            ctx.beginPath();
            ctx.moveTo(x + w, y);
            ctx.quadraticCurveTo(x + w - 15, y + h * 0.4, x + w - 8, y + h);
            ctx.lineTo(x + w, y + h);
            ctx.closePath();
            ctx.fill();

            ctx.restore();
        }
    }
};
