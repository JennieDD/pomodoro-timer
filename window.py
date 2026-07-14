"""
番茄钟主窗口
- 圆形进度环（自定义 paintEvent）
- 时间数字 + 状态标签
- 开始/暂停/重置按钮
- 系统托盘图标
- macOS 通知
"""

import subprocess

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSystemTrayIcon, QMenu, QAction,
    QSizePolicy, QApplication,
)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush,
    QPixmap, QIcon,
)

from timer_logic import PomodoroTimer, Phase, PHASE_COLORS, PHASE_LABELS, LONG_BREAK_INTERVAL


# ────────────────────────────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────────────────────────────

# 每种颜色的图标只渲染一次
_icon_cache: dict[str, QPixmap] = {}


def make_tomato_icon(color: str = "#E74C3C", size: int = 64) -> QPixmap:
    """用代码生成一个简单的圆形番茄图标（结果按颜色缓存）。"""
    key = f"{color}:{size}"
    if key in _icon_cache:
        return _icon_cache[key]

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    margin = size * 0.08
    # 圆形主体
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(
        QRectF(margin, margin + size * 0.08,
               size - 2 * margin, size - 2 * margin - size * 0.08)
    )
    # 绿色叶子（小矩形）
    painter.setBrush(QBrush(QColor("#27AE60")))
    leaf_w = size * 0.18
    leaf_h = size * 0.22
    painter.drawRoundedRect(
        QRectF(size / 2 - leaf_w / 2, 0, leaf_w, leaf_h),
        leaf_w / 3, leaf_w / 3,
    )
    painter.end()

    _icon_cache[key] = pixmap
    return pixmap


def notify_macos(title: str, message: str, sound: str = "Glass"):
    """发送 macOS 系统通知（不阻塞 UI）。"""
    script = (
        f'display notification "{message}" '
        f'with title "{title}" '
        f'sound name "{sound}"'
    )
    subprocess.Popen(["osascript", "-e", script])


# ────────────────────────────────────────────────────────────────────────
# 圆形进度环组件
# ────────────────────────────────────────────────────────────────────────

class RingWidget(QWidget):
    """绘制一个带缺口的圆形进度环，中心显示时间和番茄数量。"""

    RING_WIDTH = 14        # 环的粗细（像素）
    TRACK_ALPHA = 40       # 背景轨道透明度
    FULL_ARC = 360 * 16    # Qt 弧度单位：一整圈

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0          # 0.0 ~ 1.0，1.0 = 满
        self._color = QColor(PHASE_COLORS[Phase.WORK])
        self._time_text = "25:00"
        self._phase_label = "专注"
        self._tomato_str = "🍅 × 0"   # 预构建，避免每帧重建
        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_state(self, progress: float, time_text: str,
                     phase_label: str, color: str, count: int):
        self._progress = max(0.0, min(1.0, progress))
        self._time_text = time_text
        self._phase_label = phase_label
        self._color = QColor(color)
        self._tomato_str = f"🍅 × {count}"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        margin = self.RING_WIDTH + 4
        rect = QRectF(
            (self.width() - side) / 2 + margin,
            (self.height() - side) / 2 + margin,
            side - 2 * margin,
            side - 2 * margin,
        )

        # 背景轨道（从颜色派生一次，复用 QColor 对象）
        base_color = QColor(self._color)
        track_color = QColor(base_color)
        track_color.setAlpha(self.TRACK_ALPHA)
        painter.setPen(QPen(track_color, self.RING_WIDTH, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, self.FULL_ARC)

        # 进度弧（从 12 点钟方向顺时针）
        if self._progress > 0:
            painter.setPen(QPen(base_color, self.RING_WIDTH, Qt.SolidLine, Qt.RoundCap))
            span_angle = -int(self._progress * self.FULL_ARC)
            painter.drawArc(rect, 90 * 16, span_angle)

        center_y = self.height() / 2

        # 时间数字
        painter.setPen(QPen(QColor("#FFFFFF")))
        painter.setFont(QFont("Helvetica Neue", int(side * 0.18), QFont.Bold))
        painter.drawText(
            QRectF(0, center_y - side * 0.18, self.width(), side * 0.24),
            Qt.AlignHCenter | Qt.AlignVCenter,
            self._time_text,
        )

        # 阶段标签
        label_color = QColor(base_color)
        label_color.setAlpha(220)
        painter.setPen(QPen(label_color))
        painter.setFont(QFont("PingFang SC", int(side * 0.065)))
        painter.drawText(
            QRectF(0, center_y + side * 0.08, self.width(), side * 0.12),
            Qt.AlignHCenter | Qt.AlignVCenter,
            self._phase_label,
        )

        # 番茄计数
        painter.setPen(QPen(QColor("#AAAAAA")))
        painter.setFont(QFont("PingFang SC", int(side * 0.055)))
        painter.drawText(
            QRectF(0, center_y + side * 0.2, self.width(), side * 0.1),
            Qt.AlignHCenter | Qt.AlignVCenter,
            self._tomato_str,
        )

        painter.end()


# ────────────────────────────────────────────────────────────────────────
# 主窗口
# ────────────────────────────────────────────────────────────────────────

BUTTON_STYLE = """
QPushButton {{
    background-color: {bg};
    color: {fg};
    border: none;
    border-radius: 20px;
    padding: 8px 28px;
    font-size: 14px;
    font-weight: 600;
    font-family: "PingFang SC", "Helvetica Neue", sans-serif;
    min-width: 90px;
}}
QPushButton:hover {{
    background-color: {hover};
}}
QPushButton:pressed {{
    background-color: {pressed};
}}
"""

WINDOW_BG = "#1A1A2E"


class PomodoroWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.timer = PomodoroTimer(self)
        self._current_color = PHASE_COLORS[Phase.WORK]

        self._build_ui()
        self._build_tray()
        self._connect_signals()

        # 初始化显示
        self._on_tick(self.timer.remaining, self.timer.total)
        self._on_phase_changed(Phase.WORK)

    # ------------------------------------------------------------------ #
    # UI 构建                                                             #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.setWindowTitle("番茄钟")
        self.setFixedSize(360, 480)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.setStyleSheet(f"QMainWindow {{ background-color: {WINDOW_BG}; }}")

        central = QWidget()
        central.setStyleSheet(f"background-color: {WINDOW_BG};")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 24, 24, 32)
        root_layout.setSpacing(0)

        # 顶部标题
        title_label = QLabel("🍅  番茄钟")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "color: #CCCCCC; font-size: 15px; font-weight: 500; "
            "font-family: 'PingFang SC', 'Helvetica Neue', sans-serif; margin-bottom: 8px;"
        )
        root_layout.addWidget(title_label)

        # 圆形进度环
        self.ring = RingWidget()
        root_layout.addWidget(self.ring, 1)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        btn_layout.setContentsMargins(0, 16, 0, 0)

        self.start_btn = self._make_button("开始", primary=True)
        self.reset_btn = self._make_button("重置", primary=False)

        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.start_btn)
        root_layout.addLayout(btn_layout)

    def _primary_button_style(self) -> str:
        """返回主按钮的 stylesheet，颜色跟随当前阶段。"""
        return BUTTON_STYLE.format(
            bg=self._current_color,
            fg="#FFFFFF",
            hover=self._adjust_color(self._current_color, 20),
            pressed=self._adjust_color(self._current_color, -20),
        )

    def _make_button(self, text: str, primary: bool) -> QPushButton:
        btn = QPushButton(text)
        if primary:
            btn.setStyleSheet(self._primary_button_style())
        else:
            btn.setStyleSheet(BUTTON_STYLE.format(
                bg="#2C2C44",
                fg="#AAAAAA",
                hover="#3A3A55",
                pressed="#252535",
            ))
        return btn

    # ------------------------------------------------------------------ #
    # 系统托盘                                                             #
    # ------------------------------------------------------------------ #

    def _build_tray(self):
        icon_pixmap = make_tomato_icon(PHASE_COLORS[Phase.WORK])
        self._tray_icon = QSystemTrayIcon(QIcon(icon_pixmap), self)
        self._tray_icon.setToolTip("番茄钟 — 25:00")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(
            "QMenu { background-color: #2C2C44; color: #FFFFFF; "
            "border: 1px solid #444466; border-radius: 6px; }"
            "QMenu::item:selected { background-color: #3A3A55; }"
        )
        self._tray_toggle_action = QAction("开始", self)
        self._tray_toggle_action.triggered.connect(self._toggle_timer)
        tray_menu.addAction(self._tray_toggle_action)

        reset_action = QAction("重置", self)
        reset_action.triggered.connect(self._reset_timer)
        tray_menu.addAction(reset_action)

        tray_menu.addSeparator()

        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    # ------------------------------------------------------------------ #
    # 信号连接                                                             #
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        self.timer.tick.connect(self._on_tick)
        self.timer.phase_changed.connect(self._on_phase_changed)
        self.timer.phase_finished.connect(self._on_phase_finished)
        self.start_btn.clicked.connect(self._toggle_timer)
        self.reset_btn.clicked.connect(self._reset_timer)

    # ------------------------------------------------------------------ #
    # 槽函数                                                               #
    # ------------------------------------------------------------------ #

    def _on_tick(self, remaining: int, total: int):
        mins, secs = divmod(remaining, 60)
        time_text = f"{mins:02d}:{secs:02d}"
        progress = remaining / total if total > 0 else 0.0
        label = PHASE_LABELS[self.timer.phase]

        self.ring.update_state(
            progress=progress,
            time_text=time_text,
            phase_label=label,
            color=self._current_color,
            count=self.timer.completed_pomodoros,
        )
        self._tray_icon.setToolTip(f"番茄钟 — {time_text}  {label}")
        self.setWindowTitle(f"🍅 {time_text} — {label}")

    def _on_phase_changed(self, phase: Phase):
        self._current_color = PHASE_COLORS[phase]
        self.start_btn.setStyleSheet(self._primary_button_style())
        self._tray_icon.setIcon(QIcon(make_tomato_icon(self._current_color)))

    def _on_phase_finished(self, phase: Phase):
        if phase == Phase.WORK:
            # timer.phase 在 phase_finished 触发前已经切换到下一阶段
            next_label = PHASE_LABELS[self.timer.phase]
            notify_macos("🍅 专注结束！", f"该休息了，即将进入{next_label}")
        else:
            notify_macos("☕️ 休息结束！", "该继续专注了，加油！")

    def _toggle_timer(self):
        if self.timer.is_running:
            self.timer.pause()
        else:
            self.timer.start()
        self._sync_toggle_label()

    def _reset_timer(self):
        self.timer.reset()
        self._sync_toggle_label()

    def _sync_toggle_label(self):
        """根据计时器状态同步开始/暂停/继续按钮文字。"""
        label = "暂停" if self.timer.is_running else (
            "继续" if self.timer.remaining < self.timer.total else "开始"
        )
        self.start_btn.setText(label)
        self._tray_toggle_action.setText(label)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit_app(self):
        self._tray_icon.hide()
        QApplication.quit()

    # ------------------------------------------------------------------ #
    # 关闭事件：最小化到托盘而非退出                                        #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self._tray_icon.showMessage(
            "番茄钟",
            "应用已最小化到菜单栏，双击图标可重新打开",
            QSystemTrayIcon.Information,
            2000,
        )

    # ------------------------------------------------------------------ #
    # 工具                                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _adjust_color(hex_color: str, delta: int) -> str:
        """将颜色明度调整 delta（正值更亮，负值更暗）。"""
        c = QColor(hex_color)
        h, s, v, a = c.getHsv()
        v = max(0, min(255, v + delta))
        c.setHsv(h, s, v, a)
        return c.name()
