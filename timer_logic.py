"""
番茄钟计时器状态机
状态流转：WORK → SHORT_BREAK → WORK → ... → LONG_BREAK（每4个番茄后）
"""

from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class Phase(Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


# 各阶段时长（秒）
PHASE_DURATIONS = {
    Phase.WORK: 25 * 60,
    Phase.SHORT_BREAK: 5 * 60,
    Phase.LONG_BREAK: 15 * 60,
}

PHASE_LABELS = {
    Phase.WORK: "专注",
    Phase.SHORT_BREAK: "短休息",
    Phase.LONG_BREAK: "长休息",
}

# 颜色主题
PHASE_COLORS = {
    Phase.WORK: "#E74C3C",
    Phase.SHORT_BREAK: "#27AE60",
    Phase.LONG_BREAK: "#2980B9",
}

# 每完成几个番茄触发长休息
LONG_BREAK_INTERVAL = 4


class PomodoroTimer(QObject):
    """番茄钟状态机，通过 Qt 信号通知 UI。"""

    # 每秒 tick，携带 (remaining_seconds, total_seconds)
    tick = pyqtSignal(int, int)
    # 阶段切换，携带新的 Phase
    phase_changed = pyqtSignal(object)
    # 阶段完成（需要发送通知）
    phase_finished = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = Phase.WORK
        self._completed_pomodoros = 0
        self._running = False

        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(1000)
        self._qt_timer.timeout.connect(self._on_tick)

        self._remaining = self.total  # 初始化为当前阶段时长

    # ------------------------------------------------------------------ #
    # 属性                                                                 #
    # ------------------------------------------------------------------ #

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def remaining(self) -> int:
        return self._remaining

    @property
    def total(self) -> int:
        return PHASE_DURATIONS[self._phase]

    @property
    def completed_pomodoros(self) -> int:
        return self._completed_pomodoros

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------ #
    # 控制接口                                                             #
    # ------------------------------------------------------------------ #

    def start(self):
        if not self._running:
            self._running = True
            self._qt_timer.start()

    def pause(self):
        if self._running:
            self._stop()

    def reset(self):
        """重置当前阶段计时，不改变已完成计数。"""
        self._stop()
        self._remaining = self.total
        self.tick.emit(self._remaining, self.total)

    def reset_all(self):
        """完全重置：回到 WORK 阶段，清空计数。"""
        self._stop()
        self._completed_pomodoros = 0
        self._switch_phase(Phase.WORK)

    # ------------------------------------------------------------------ #
    # 内部逻辑                                                             #
    # ------------------------------------------------------------------ #

    def _stop(self):
        """停止计时器并标记为未运行。"""
        self._running = False
        self._qt_timer.stop()

    def _on_tick(self):
        self._remaining -= 1
        self.tick.emit(self._remaining, self.total)
        if self._remaining <= 0:
            self._finish_phase()

    def _finish_phase(self):
        finished_phase = self._phase
        self._stop()
        self.phase_finished.emit(finished_phase)

        if finished_phase == Phase.WORK:
            self._completed_pomodoros += 1
            if self._completed_pomodoros % LONG_BREAK_INTERVAL == 0:
                self._switch_phase(Phase.LONG_BREAK)
            else:
                self._switch_phase(Phase.SHORT_BREAK)
        else:
            # 休息结束，回到专注
            self._switch_phase(Phase.WORK)

    def _switch_phase(self, new_phase: Phase):
        self._phase = new_phase
        self._remaining = PHASE_DURATIONS[new_phase]
        self.phase_changed.emit(new_phase)
        self.tick.emit(self._remaining, self.total)
