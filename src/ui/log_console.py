# -*- coding: utf-8 -*-
"""
log_console.py
全局日志输出控件，带颜色、信号机制、固定行数支持
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QTextBrowser


class LogConsole(QTextBrowser):
    """项目全局日志输出控件"""

    sig_log = pyqtSignal(str, str)  # (level, message)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setReadOnly(True)
        self.document().setDefaultFont(QFont("Microsoft YaHei", 10))
        self.setStyleSheet("""
        QTextBrowser {
            border: 1px solid #aaa;
            background: #fafafa;
            padding: 4px;
        }
        """)

        self.sig_log.connect(self._append_log)

    def _append_log(self, level: str, message: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")

        color = {
            "ERROR": "red",
            "WARN": "#cc8400",
            "INFO": "#0066cc",
        }.get(level, "black")

        html = f'<span style="color:{color}"><b>[{ts}] [{level}]</b></span> {message}'
        self.append(html)

    def set_fixed_4_rows(self):
        fm = self.fontMetrics()
        h = int(fm.lineSpacing() * 4 + 10)
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)

    def push_message(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.sig_log.emit("INFO", f"[{ts}] {msg}")


    # 简化接口
    def info(self, msg: str): self.sig_log.emit("INFO", msg)
    def warn(self, msg: str): self.sig_log.emit("WARN", msg)
    def error(self, msg: str): self.sig_log.emit("ERROR", msg)