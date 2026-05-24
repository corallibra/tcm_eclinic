# -*- coding: utf-8 -*-
"""中医药诊所系统 - 日志模块"""

import logging
import traceback
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QObject, pyqtSignal
from config import APP_CONFIG

LOG_FILE = APP_CONFIG["log_path"]

logger = logging.getLogger("EClinic")
logger.setLevel(logging.INFO)

console = logging.StreamHandler()
console.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%H:%M:%S"))

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"))

logger.addHandler(console)
logger.addHandler(file_handler)


def get_logger(name=None):
    return logger if name is None else logger.getChild(name)


class QTextEditHandler(logging.Handler, QObject):
    """线程安全的 Qt 日志处理器"""
    sig_log = pyqtSignal(str, str)

    def __init__(self, log_console):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.console = log_console
        self.sig_log.connect(self._append_log)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.sig_log.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)

    def _append_log(self, level, msg):
        if hasattr(self.console, "append_log"):
            self.console.append_log(level, msg)

    def push_message(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.sig_log.emit("INFO", f"[{ts}] {msg}")


def log_unhandled_exception(exc_type, exc_value, exc_tb):
    """统一记录未捕获异常（给 sys.excepthook 调用）"""
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.error("未捕获异常：\n%s", tb_str)
