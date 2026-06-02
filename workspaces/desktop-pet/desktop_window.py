"""
桌面宠物 — PySide6 透明窗口
独立运行，不依赖 FastAPI 服务。
用法: python desktop_window.py
"""

import sys
import sqlite3
import random
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint, QSize, QRect
from PySide6.QtGui import QPixmap, QPainter, QIcon, QAction, QImage
from PySide6.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QLabel,
)

# Petdex 标准状态定义
PET_STATES = [
    {"id": "idle", "row": 0, "frames": 6, "duration_ms": 1100},
    {"id": "running-right", "row": 1, "frames": 8, "duration_ms": 1060},
    {"id": "running-left", "row": 2, "frames": 8, "duration_ms": 1060},
    {"id": "waving", "row": 3, "frames": 4, "duration_ms": 700},
    {"id": "jumping", "row": 4, "frames": 5, "duration_ms": 840},
    {"id": "failed", "row": 5, "frames": 8, "duration_ms": 1220},
    {"id": "waiting", "row": 6, "frames": 6, "duration_ms": 1010},
    {"id": "running", "row": 7, "frames": 6, "duration_ms": 820},
    {"id": "review", "row": 8, "frames": 6, "duration_ms": 1030},
]

IDLE_CYCLE = ["idle", "idle", "idle", "waiting", "waving", "jumping", "review", "idle"]
IDLE_TICK_MIN_MS = 2500
IDLE_TICK_MAX_MS = 5000
REACTION_MS = 1200
SPRITE_DISPLAY_SIZE = 140  # 显示尺寸（像素）

WORKSPACE_DIR = Path(__file__).parent
DATA_DB = WORKSPACE_DIR / "data.db"
PETS_DIR = WORKSPACE_DIR / "pets"


def get_active_pet() -> dict | None:
    """从数据库获取活跃宠物信息"""
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
    """获取所有已下载宠物"""
    if not DATA_DB.exists():
        return []
    conn = sqlite3.connect(str(DATA_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, name, display_name, is_active FROM pets").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_active_pet(pet_id: int):
    """设置活跃宠物"""
    conn = sqlite3.connect(str(DATA_DB))
    conn.execute("UPDATE pets SET is_active = 0")
    conn.execute("UPDATE pets SET is_active = 1 WHERE id = ?", (pet_id,))
    conn.commit()
    conn.close()


class PetWindow(QWidget):
    """透明无边框桌面宠物窗口"""

    def __init__(self, pet_name: str, spritesheet_path: Path):
        super().__init__()
        self.pet_name = pet_name
        self.current_state_idx = 0
        self.current_frame = 0
        self.idle_cycle_idx = 0
        self.dragging = False
        self.drag_offset = QPoint()

        # 加载 spritesheet
        self.spritesheet = QPixmap(str(spritesheet_path))
        if self.spritesheet.isNull():
            raise RuntimeError(f"无法加载: {spritesheet_path}")

        # 计算帧尺寸（8列 x 9行）
        self.frame_w = self.spritesheet.width() // 8
        self.frame_h = self.spritesheet.height() // 9

        # 窗口设置：透明 + 无边框 + 置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(SPRITE_DISPLAY_SIZE, SPRITE_DISPLAY_SIZE)

        # 初始位置：屏幕右下角
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - SPRITE_DISPLAY_SIZE - 80, screen.height() - SPRITE_DISPLAY_SIZE - 80)

        # 动画定时器
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._advance_frame)
        self._start_animation()

        # 自动状态循环定时器
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._next_idle_state)
        self._schedule_idle()

    def _start_animation(self):
        state = PET_STATES[self.current_state_idx]
        interval = state["duration_ms"] // state["frames"]
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

    def _schedule_idle(self):
        wait = random.randint(IDLE_TICK_MIN_MS, IDLE_TICK_MAX_MS)
        self._idle_timer.start(wait)

    def _next_idle_state(self):
        if self.dragging:
            self._schedule_idle()
            return
        self.idle_cycle_idx = (self.idle_cycle_idx + 1) % len(IDLE_CYCLE)
        self._set_state(IDLE_CYCLE[self.idle_cycle_idx])
        self._schedule_idle()

    # === 绘制 ===
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)  # 像素锐利

        state = PET_STATES[self.current_state_idx]
        src_rect = QRect(
            self.current_frame * self.frame_w,
            state["row"] * self.frame_h,
            self.frame_w,
            self.frame_h,
        )
        dst_rect = QRect(0, 0, SPRITE_DISPLAY_SIZE, SPRITE_DISPLAY_SIZE)
        painter.drawPixmap(dst_rect, self.spritesheet, src_rect)
        painter.end()

    # === 拖拽 ===
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self._idle_timer.stop()

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_pos)
            # 方向动画
            dx = event.globalPosition().x() - (self.pos().x() + self.drag_offset.x())
            if dx > 2:
                self._set_state("running-right")
            elif dx < -2:
                self._set_state("running-left")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self._set_state("idle")
            self._schedule_idle()

    # === 双击反应 ===
    def mouseDoubleClickEvent(self, event):
        current = PET_STATES[self.current_state_idx]["id"]
        reaction = "jumping" if current == "waving" else "waving"
        self._set_state(reaction)
        QTimer.singleShot(REACTION_MS, lambda: self._set_state("idle"))


class PetTrayApp:
    """系统托盘应用：管理桌面宠物窗口"""

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
        # 托盘图标（用 emoji 风格的简单图标）
        icon = self._create_tray_icon()
        self.tray = QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip("桌面宠物 — 岛主 DaoZhu")

        menu = QMenu()

        # 显示/隐藏
        self.toggle_action = QAction("隐藏宠物", menu)
        self.toggle_action.triggered.connect(self._toggle_visibility)
        menu.addAction(self.toggle_action)

        menu.addSeparator()

        # 切换宠物子菜单
        pet_menu = QMenu("切换宠物", menu)
        pets = get_all_pets()
        for p in pets:
            label = f"{'● ' if p['is_active'] else '  '}{p['display_name'] or p['name']}"
            action = QAction(label, pet_menu)
            action.setData(p["id"])
            action.triggered.connect(lambda checked, pid=p["id"]: self._switch_pet(pid))
            pet_menu.addAction(action)
        if pets:
            menu.addMenu(pet_menu)

        menu.addSeparator()

        # 退出
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_click)
        self.tray.show()

    def _create_tray_icon(self) -> QIcon:
        """创建一个简单的托盘图标（16x16 像素）"""
        img = QImage(16, 16, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        painter = QPainter(img)
        # 画一个简单的爪印
        painter.setBrush(Qt.darkGreen)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(3, 6, 10, 8)  # 掌心
        painter.drawEllipse(2, 2, 4, 4)   # 左趾
        painter.drawEllipse(6, 1, 4, 4)   # 中趾
        painter.drawEllipse(10, 2, 4, 4)  # 右趾
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
        # 销毁旧窗口，创建新的
        if self.pet_window:
            self.pet_window.close()
            self.pet_window = None
        self._init_pet()
        # 重建托盘菜单（更新选中标记）
        self._init_tray()

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()

    def _quit(self):
        if self.pet_window:
            self.pet_window.close()
        self.tray.hide()
        self.app.quit()

    def run(self):
        if not self.pet_window:
            print("⚠️ 没有活跃宠物。请先在桌面宠物工作区中选择一只宠物。")
            print("   打开 http://localhost:7805 → 我的宠物 → 选择")
            sys.exit(1)
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = PetTrayApp()
    app.run()
