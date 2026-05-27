/**
 * 导演系统 — 剧本调度 + 场景管理
 */

const Director = {
    // 剧本分镜
    scenes: [
        {
            id: 0,
            description: "清晨，阳光透过窗帘洒进房间，小明还在沉睡。",
            actorAction: "wake",
            duration: 2000,
            note: "小明从睡梦中醒来",
            thought: "💤 再睡五分钟..."
        },
        {
            id: 1,
            description: "小明揉了揉眼睛，慢慢坐起身来。",
            actorAction: "sit",
            duration: 1500,
            note: "小明坐起来，伸了个懒腰",
            thought: "😴 今天是什么日子来着..."
        },
        {
            id: 2,
            description: "小明站起来，迈步走向房门。",
            actorAction: "stand",
            duration: 800,
            note: "小明站起身",
            thought: ""
        },
        {
            id: 3,
            description: "小明穿过房间，走到门前。",
            actorAction: "walk_to_door",
            duration: 2500,
            note: "小明走向门口",
            thought: "🚶 去看看外面的世界"
        },
        {
            id: 4,
            description: "小明伸出手，转动门把手。",
            actorAction: "open_door",
            duration: 1500,
            note: "小明打开了门",
            thought: "🔓 咔嗒..."
        },
        {
            id: 5,
            description: "门缓缓打开，清晨的光线涌入房间。新的一天开始了。",
            actorAction: "finish",
            duration: 2000,
            note: "表演结束 — 新的一天开始",
            thought: "☀️ 早安，世界！"
        }
    ],

    currentIdx: 0,
    timer: null,
    takeCount: 1,
    isPlaying: false,

    // 走路动画状态
    walking: {
        active: false,
        startX: 0,
        targetX: 0,
        startTime: 0,
        duration: 2500
    },

    // 开始演出
    start() {
        this.currentIdx = 0;
        this.isPlaying = true;
        this.resetEntities();
        this.executeScene(0);
    },

    // 重置实体状态
    resetEntities() {
        const xm = Entities.xiaoming;
        xm.state = "lying";
        xm.x = 280;
        xm.y = 380;
        xm.walkTargetX = null;
        Entities.door.isOpen = false;
        this.walking.active = false;
    },

    // 重播
    replay() {
        if (this.timer) clearTimeout(this.timer);
        this.takeCount++;
        this.walking.active = false;
        this.start();
        this.updateUI();
    },

    // 执行一幕
    executeScene(index) {
        if (index >= this.scenes.length) {
            this.isPlaying = false;
            this.updateNote("🏁 全剧终 — 谢幕！");
            return;
        }

        const scene = this.scenes[index];
        this.currentIdx = index;
        this.updateNote(`${scene.note}`);
        this.updateUI();

        const xm = Entities.xiaoming;

        switch (scene.actorAction) {
            case "wake":
                xm.state = "lying";
                setTimeout(() => { xm.state = "sitting"; }, 800);
                break;

            case "sit":
                xm.state = "sitting";
                xm.y = 372;
                break;

            case "stand":
                xm.state = "standing";
                xm.y = 342;
                break;

            case "walk_to_door":
                xm.state = "walking";
                xm.y = 342;
                this.walking.active = true;
                this.walking.startX = xm.x;
                this.walking.targetX = Entities.door.x - 40;
                this.walking.startTime = performance.now();
                this.walking.duration = scene.duration;
                break;

            case "open_door":
                xm.state = "opening_door";
                // 延迟开门，模拟转动把手
                setTimeout(() => { Entities.door.open(); }, 600);
                break;

            case "finish":
                xm.state = "idle";
                break;
        }

        // 定时进入下一幕
        if (this.timer) clearTimeout(this.timer);
        this.timer = setTimeout(() => {
            // 走路结束时确保到位
            if (xm.state === "walking") {
                xm.x = this.walking.targetX;
                xm.state = "standing";
                this.walking.active = false;
            }
            this.currentIdx++;
            this.executeScene(this.currentIdx);
        }, scene.duration);
    },

    // 更新走路插值（每帧调用）
    updateWalking() {
        if (!this.walking.active) return;

        const xm = Entities.xiaoming;
        const w = this.walking;
        const elapsed = performance.now() - w.startTime;
        let t = Math.min(1, elapsed / w.duration);

        if (t >= 1) {
            xm.x = w.targetX;
            xm.state = "standing";
            this.walking.active = false;
        } else {
            // easeInOutCubic — 更自然的加减速
            const ease = t < 0.5
                ? 4 * t * t * t
                : 1 - Math.pow(-2 * t + 2, 3) / 2;
            xm.x = w.startX + (w.targetX - w.startX) * ease;
        }
    },

    // 获取当前台词
    getCurrentThought() {
        if (this.currentIdx < this.scenes.length) {
            return this.scenes[this.currentIdx].thought || "";
        }
        return "";
    },

    // 更新导演台词
    updateNote(text) {
        const noteEl = document.querySelector('.note-text');
        if (noteEl) noteEl.textContent = `导演：${text}`;
    },

    // 更新场记板 UI
    updateUI() {
        const sceneEl = document.getElementById('sceneNum');
        const takeEl = document.getElementById('takeNum');
        if (sceneEl) sceneEl.textContent = `${this.currentIdx + 1}/${this.scenes.length}`;
        if (takeEl) takeEl.textContent = this.takeCount;
    }
};
