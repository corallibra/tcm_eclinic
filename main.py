# main.py
import sys
import traceback
from PyQt6.QtWidgets import QApplication
from src.ui.gui_main import MainWindow
from logger import log_unhandled_exception  # 刚才在 logger.py 里加的函数

def qt_excepthook(exc_type, exc_value, exc_tb):
    """
    全局未捕获异常钩子：
    - 交给 logger 记录（logger 已经通过 QTextEditHandler 连到 GUI 日志）
    - 避免程序直接崩溃
    """
    # 保留 Ctrl+C 退出行为
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    # 记录到日志（→ GUI 上方日志）
    log_unhandled_exception(exc_type, exc_value, exc_tb)

def main():
    # 替换默认的 excepthook
    sys.excepthook = qt_excepthook

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
