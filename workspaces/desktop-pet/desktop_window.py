"""
桌面宠物 — PySide6 透明窗口
独立运行，不依赖 FastAPI 服务。
用法: pythonw desktop_window.py  (无 cmd 窗口)
      python desktop_window.py   (有 cmd 窗口，调试用)
"""

import sys
import sqlite3
import random
import time
from pathlib import Path
from collections import deque

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF
from PySide6.QtGui import QPixmap, QPainter, QIcon, QAction, QImage, QCursor
from PySide6.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu,
)

# === Petdex 标准状态 ===
PET_STATES = [
    {"id": "idle",          "row": 0, "frames": 6, "duration_ms": 1100},
    {"id": "running-right", "row": 1, "frames": 8, "duration_ms": 1060},
    {"id": "running-left",  "row": 2, "frames": 8, "duration_ms": 1060},
    {"id": "waving",        "row": 3, "frames": 4, "duration_ms": 700},
    {"id": "jumping",       "row": 4, "frames": 5, "duration_ms": 840},
    {"id": "failed",        "row": 5, "frames": 8, "duration_ms": 1220},
    {"id": "waiting",       "row": 6, "frames": 6, "duration_ms": 1010},
    {"id": "running",       "row": 7, "frames": 6, "duration_ms": 820},
    {"id": "review",        "row": 8, "frames": 6, "duration_ms": 1030},
]

# === 物理常量（对齐网页版 pet-floater.js）===
IDLE_CYCLE = ["idle", "idle", "waiting", "idle", "waving", "jumping", "review", "idle", "idle"]
IDLE_TICK_MIN_MS = 1700
IDLE_TICK_MAX_MS = 3000
REACTION_MS = 1100
RUN_TAIL_MS = 600
DRAG_THRESHOLD_PX = 4
SPRITE_DISPLAY_SIZE = 120

# #076 窗口尺寸（精灵居中留呼吸空间）+ 默认边距
PET_WINDOW_W = 140
PET_WINDOW_H = 150
PET_RIGHT_MARGIN = 40
PET_BOTTOM_MARGIN = 60

# 甩出物理
THROW_MIN_VELOCITY = 0.05
THROW_FRICTION = 0.92
THROW_BOUNCE = -0.5
THROW_SAMPLE_WINDOW_MS = 80
THROW_TICK_MS = 16  # ~60fps

WORKSPACE_DIR = Path(__file__).parent
DATA_DB = WORKSPACE_DIR / "data.db"
PETS_DIR = WORKSPACE_DIR / "pets"
PET_STATE_FILE = WORKSPACE_DIR / ".pet_state.json"


# === 数据库操作 ===
def get_active_pet() -> dict | None:
    if not DATA_DB.exists():
        return None
    conn = sqlite3.connect(str(DATA_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, name, display_name FROM pets WHERE is_active = 1 LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row["id"], "name": row["name"], "display_name": row["display_name"]}


def get_all_pets() -> list[dict]:
    if not DATA_DB.exists():
        return []
    conn = sqlite3.connect(str(DATA_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, name, display_name, is_active FROM pets").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_active_pet(pet_id: int):
    conn = sqlite3.connect(str(DATA_DB))
    conn.execute("UPDATE pets SET is_active = 0")
    conn.execute("UPDATE pets SET is_active = 1 WHERE id = ?", (pet_id,))
    conn.commit()
    conn.close()


# === #076 宠物窗口位置持久化 ===
def load_pet_state() -> dict | None:
    if not PET_STATE_FILE.exists():
        return None
    try:
        import json
        return json.loads(PET_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_pet_state(x: float, y: float):
    try:
        import json
        PET_STATE_FILE.write_text(
            json.dumps({"x": x, "y": y}), encoding="utf-8"
        )
    except Exception:
        pass


# === 桌面宠物窗口 ===
class PetWindow(QWidget):
    """透明无边框桌面宠物窗口（含甩出物理）"""

    def __init__(self, pet_name: str, spritesheet_path: Path):
        super().__init__()
        self.pet_name = pet_name
        self.current_state_idx = 0
        self.current_frame = 0
        self.idle_cycle_idx = 0

        # 拖拽状态
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.drag_moved = False
        self.drag_offset = QPoint()

        # 甩出物理
        self.throwing = False
        self.vx = 0.0
        self.vy = 0.0
        self.pos_x = 0.0
        self.pos_y = 0.0
        self._velocity_samples = deque(maxlen=6)

        # 加载 spritesheet
        self.spritesheet = QPixmap(str(spritesheet_path))
        if self.spritesheet.isNull():
            raise RuntimeError(f"无法加载: {spritesheet_path}")

        self.frame_w = self.spritesheet.width() // 8
        self.frame_h = self.spritesheet.height() // 9

        # 窗口：透明 + 无边框 + 置顶 + 不在任务栏
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(PET_WINDOW_W, PET_WINDOW_H)

        # #076 初始位置：优先恢复持久化，否则右下角（距右 40 / 距下 60）
        screen = QApplication.primaryScreen().geometry()
        saved = load_pet_state()
        if saved:
            self.pos_x = float(saved["x"])
            self.pos_y = float(saved["y"])
        else:
            self.pos_x = float(screen.width() - PET_WINDOW_W - PET_RIGHT_MARGIN)
            self.pos_y = float(screen.height() - PET_WINDOW_H - PET_BOTTOM_MARGIN)
        self.move(int(self.pos_x), int(self.pos_y))

        # 动画帧定时器
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._advance_frame)
        self._start_animation()

        # 空闲状态循环
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._next_idle_state)
        self._schedule_idle()

        # 甩出物理定时器
        self._throw_timer = QTimer(self)
        self._throw_timer.setInterval(THROW_TICK_MS)
        self._throw_timer.timeout.connect(self._throw_tick)

        # 跑步拖尾定时器（松手后延续 running 一小段）
        self._tail_timer = QTimer(self)
        self._tail_timer.setSingleShot(True)
        self._tail_timer.timeout.connect(self._end_run_tail)

        # 反应定时器
        self._reaction_timer = QTimer(self)
        self._reaction_timer.setSingleShot(True)
        self._reaction_timer.timeout.connect(self._end_reaction)

    # === 动画 ===
    def _start_animation(self):
        state = PET_STATES[self.current_state_idx]
        interval = max(16, state["duration_ms"] // state["frames"])
        self._anim_timer.start(interval)

    def _advance_frame(self):
        state = PET_STATES[self.current_state_idx]
        self.current_frame = (self.current_frame + 1) % state["frames"]
        self.update()

    def _set_state(self, state_id: str):
        idx = next((i for i, s in enumerate(PET_STATES) if s["id"] == state_id), 0)
        if idx != self.current_state_idx:
            self.current_state_idx = idx
            self.current_frame = 0
            self._start_animation()

    # === 空闲循环 ===
    def _schedule_idle(self):
        wait = random.randint(IDLE_TICK_MIN_MS, IDLE_TICK_MAX_MS)
        self._idle_timer.start(wait)

    def _next_idle_state(self):
        if self.dragging or self.throwing:
            self._schedule_idle()
            return
        self.idle_cycle_idx = (self.idle_cycle_idx + 1) % len(IDLE_CYCLE)
        self._set_state(IDLE_CYCLE[self.idle_cycle_idx])
        self._schedule_idle()

    # === 绘制 ===
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        state = PET_STATES[self.current_state_idx]
        from PySide6.QtCore import QRect
        src = QRect(
            self.current_frame * self.frame_w,
            state["row"] * self.frame_h,
            self.frame_w, self.frame_h,
        )
        # #076 精灵居中渲染（120 居中于 140x150 窗口）
        ox = (PET_WINDOW_W - SPRITE_DISPLAY_SIZE) // 2
        oy = (PET_WINDOW_H - SPRITE_DISPLAY_SIZE) // 2
        dst = QRect(ox, oy, SPRITE_DISPLAY_SIZE, SPRITE_DISPLAY_SIZE)
        painter.drawPixmap(dst, self.spritesheet, src)
        painter.end()

    # === 屏幕边界 ===
    def _screen_bounds(self):
        screen = QApplication.primaryScreen().geometry()
        return (0.0, 0.0,
                float(screen.width() - PET_WINDOW_W),
                float(screen.height() - PET_WINDOW_H))

    # === 鼠标交互 ===
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_moved = False
            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_offset = self.drag_start_pos - self.pos()
            self._velocity_samples.clear()
            self._velocity_samples.append((time.time() * 1000, self.pos_x, self.pos_y))
            # 停止甩出和空闲
            self._cancel_throw()
            self._idle_timer.stop()
            self._tail_timer.stop()
            self._reaction_timer.stop()

    def mouseMoveEvent(self, event):
        if not self.dragging:
            return
        global_pos = event.globalPosition().toPoint()
        dx = global_pos.x() - self.drag_start_pos.x()
        dy = global_pos.y() - self.drag_start_pos.y()

        if not self.drag_moved and (abs(dx) + abs(dy)) > DRAG_THRESHOLD_PX:
            self.drag_moved = True

        if self.drag_moved:
            new_pos = global_pos - self.drag_offset
            self.pos_x = float(new_pos.x())
            self.pos_y = float(new_pos.y())
            self.move(new_pos)

            # 速度采样
            now = time.time() * 1000
            self._velocity_samples.append((now, self.pos_x, self.pos_y))

            # 实时方向动画
            if len(self._velocity_samples) >= 2:
                prev = self._velocity_samples[-2]
                horizontal = self.pos_x - prev[1]
                if horizontal > 1:
                    self._set_state("running-right")
                elif horizontal < -1:
                    self._set_state("running-left")

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.dragging = False

        if not self.drag_moved:
            # 没移动 = 点击反应
            self._trigger_reaction()
            return

        # 计算释放速度（从最近采样）
        now = time.time() * 1000
        recent = [(t, x, y) for t, x, y in self._velocity_samples
                  if now - t <= THROW_SAMPLE_WINDOW_MS]
        samples = recent if len(recent) > 1 else list(self._velocity_samples)

        if len(samples) >= 2:
            first, last = samples[0], samples[-1]
            dt = last[0] - first[0]
            if dt > 0:
                self.vx = (last[1] - first[1]) / dt
                self.vy = (last[2] - first[2]) / dt

        if abs(self.vx) > THROW_MIN_VELOCITY or abs(self.vy) > THROW_MIN_VELOCITY:
            # 甩出！
            self.throwing = True
            self._throw_timer.start()
        else:
            self._start_run_tail()

    # === 甩出物理 ===
    def _throw_tick(self):
        min_x, min_y, max_x, max_y = self._screen_bounds()

        self.pos_x += self.vx * THROW_TICK_MS
        self.pos_y += self.vy * THROW_TICK_MS

        # 边界弹跳
        if self.pos_x < min_x or self.pos_x > max_x:
            self.vx *= THROW_BOUNCE
            self.pos_x = max(min_x, min(self.pos_x, max_x))
        if self.pos_y < min_y or self.pos_y > max_y:
            self.vy *= THROW_BOUNCE
            self.pos_y = max(min_y, min(self.pos_y, max_y))

        self.move(int(self.pos_x), int(self.pos_y))

        # 方向动画
        if self.vx > 0.02:
            self._set_state("running-right")
        elif self.vx < -0.02:
            self._set_state("running-left")

        # 摩擦
        self.vx *= THROW_FRICTION
        self.vy *= THROW_FRICTION

        # 停止
        if abs(self.vx) < THROW_MIN_VELOCITY and abs(self.vy) < THROW_MIN_VELOCITY:
            self._cancel_throw()
            self._start_run_tail()

    def _cancel_throw(self):
        self._throw_timer.stop()
        self.throwing = False
        self.vx = 0.0
        self.vy = 0.0

    # === #076 位置持久化 ===
    def save_position(self):
        save_pet_state(self.pos_x, self.pos_y)

    # === 跑步拖尾（松手后跑一小段再回 idle）===
    def _start_run_tail(self):
        self._tail_timer.start(RUN_TAIL_MS)

    def _end_run_tail(self):
        self._set_state("idle")
        self._schedule_idle()

    # === 点击反应 ===
    def _trigger_reaction(self):
        current = PET_STATES[self.current_state_idx]["id"]
        reaction = "jumping" if current == "waving" else "waving"
        self._set_state(reaction)
        self._reaction_timer.start(REACTION_MS)

    def _end_reaction(self):
        self._set_state("idle")
        self._schedule_idle()


# === 系统托盘 ===
class PetTrayApp:
    """系统托盘应用"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.pet_window = None
        self._init_pet()
        self._init_tray()

    def _init_pet(self):
        pet = get_active_pet()
        if not pet:
            return
        spritesheet = PETS_DIR / pet["name"] / "spritesheet.webp"
        if not spritesheet.exists():
            return
        self.pet_window = PetWindow(pet["display_name"] or pet["name"], spritesheet)
        self.pet_window.show()

    def _init_tray(self):
        icon = self._create_tray_icon()
        self.tray = QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip("桌面宠物 — 岛主 DaoZhu")
        self._rebuild_tray_menu()
        self.tray.activated.connect(self._on_tray_click)
        self.tray.show()

    def _rebuild_tray_menu(self):
        """重建托盘右键菜单（切换宠物后调用，不重建托盘图标）"""
        menu = QMenu()

        self.toggle_action = QAction("隐藏宠物", menu)
        self.toggle_action.triggered.connect(self._toggle_visibility)
        menu.addAction(self.toggle_action)

        menu.addSeparator()

        # 切换宠物
        pet_menu = QMenu("切换宠物", menu)
        pets = get_all_pets()
        for p in pets:
            label = f"{'● ' if p['is_active'] else '  '}{p['display_name'] or p['name']}"
            action = QAction(label, pet_menu)
            action.triggered.connect(lambda checked, pid=p["id"]: self._switch_pet(pid))
            pet_menu.addAction(action)
        if pets:
            menu.addMenu(pet_menu)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

    def _create_tray_icon(self) -> QIcon:
        img = QImage(16, 16, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        painter = QPainter(img)
        painter.setBrush(Qt.darkGreen)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(3, 6, 10, 8)
        painter.drawEllipse(2, 2, 4, 4)
        painter.drawEllipse(6, 1, 4, 4)
        painter.drawEllipse(10, 2, 4, 4)
        painter.end()
        return QIcon(QPixmap.fromImage(img))

    def _toggle_visibility(self):
        if self.pet_window and self.pet_window.isVisible():
            self.pet_window.hide()
            self.toggle_action.setText("显示宠物")
        elif self.pet_window:
            self.pet_window.show()
            self.toggle_action.setText("隐藏宠物")

    def _switch_pet(self, pet_id: int):
        set_active_pet(pet_id)
        if self.pet_window:
            self.pet_window.close()
            self.pet_window = None
        self._init_pet()
        # 只更新菜单，不重建托盘图标
        self._rebuild_tray_menu()

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()

    def _quit(self):
        if self.pet_window:
            self.pet_window.save_position()
            self.pet_window.close()
        self.tray.hide()
        self.app.quit()

    def run(self):
        if not self.pet_window:
            # 无 cmd 时用 MessageBox 提示
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None, "桌面宠物",
                "没有活跃宠物。\n请先在桌面宠物工作区中选择一只宠物。\n(http://localhost:7805 → 我的宠物 → 选择)"
            )
            sys.exit(1)
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = PetTrayApp()
    app.run()
