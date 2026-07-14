"""
番茄钟应用入口
用法: python main.py
"""

import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from window import PomodoroWindow


def main():
    # 高 DPI 支持（macOS Retina 屏）
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("番茄钟")
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口时不退出，最小化到托盘

    # 全局字体（PingFang SC 支持中文，Helvetica Neue 作回退）
    app.setFont(QFont("PingFang SC", 13))

    window = PomodoroWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
