# -*- coding: utf-8 -*-
"""
中医药诊所系统 - 主程序入口 (v2.0 PostgreSQL Ready)

功能：
1. 初始化 PostgreSQL（或 SQLite 降级）数据库
2. 全局异常钩子 → 日志控制台
3. MainWindow → GUI 主窗口 + Word 导入进度条

使用方式：
    python main.py [--db-type postgres|sqlite] --help

作者：TCM_eclinic Team
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# -------------------------------
# 添加项目根目录到 Python path
# -------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# -------------------------------
# 初始化配置和日志系统
# -------------------------------
from config import ensure_dirs, APP_DB_TYPE, APP_CONFIG, DATA_DIR, PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD

ensure_dirs()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("main")

# -------------------------------
# 导入数据库模块（延迟初始化，相对路径）
# -------------------------------
import sys, os
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.database import get_database_manager, DatabaseManager, DataValidationError

# -------------------------------
# PostgreSQL DDL 自动执行函数（仅当驱动可用且文件存在时运行）
# -------------------------------
def auto_run_postgres_ddl(project_root):
    """自动检测并运行 PostgreSQL DDL 脚本（如果适用）"""
    # 仅在 PostgreSQL 模式下运行
    if APP_DB_TYPE != "postgres":
        return

    # 检查 psycopg2 驱动
    try:
        import psycopg2
        HAS_PG = True
    except ImportError:
        print("[i] PostgreSQL 驱动 psycopg2 未安装，跳过 DDL 执行")
        return False

    if not HAS_PG:
        print("[i] PostgreSQL 驱动 psycopg2 未安装，跳过 DDL 执行")
        return False

    # 检查 DDL 文件是否存在
    ddl_path = project_root / "data" / "schema_postgres.sql"
    if not ddl_path.exists():
        print(f"[!] PostgreSQL DDL 文件不存在：{ddl_path}")
        return None

    # 连接 PostgreSQL 默认数据库，创建目标数据库（如果不存在）
    conn = None
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            dbname="postgres",
            user=PG_USER,
            password=PG_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (PG_DATABASE,))
        if not cursor.fetchone():
            cursor.execute(f'CREATE DATABASE "{PG_DATABASE}"')

    except psycopg2.OperationalError as e:
        print(f"[!] PostgreSQL 连接失败：{e}")
        return None

    except Exception as e:
        print(f"[!] DDL 执行异常：{type(e).__name__}: {e}")
        return None

    finally:
        if conn:
            conn.close()

    print("[✓] PostgreSQL DDL 执行完成")
    return True


# -------------------------------
# PyQt6 + GUI 导入（使用全局异常钩子保护）
# -------------------------------
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QStyleFactory
    from src.ui.gui_main import MainWindow

except ImportError as e:
    logger.error(f"GUI 模块缺失：{e}")
    sys.exit(1)


def qt_uncaught_exception(exc_type, exc_value, exc_tb):
    """未捕获异常 → 全局日志，而不是崩溃（允许用户手动保存进度）"""

    # Ctrl+C 保留原生行为
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    # 打印详细的异常信息
    import traceback
    print("\n" + "=" * 60)
    print("未捕获的异常:")
    print("=" * 60)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    print("=" * 60)

    logger.exception("未捕获的 PyQt6 异常:")

    # 避免程序立即崩溃 → 返回给 Qt 事件循环处理
    return


def setup_uncaught_exception_handler():
    """替换默认 Python uncaught exception 钩子"""
    sys.excepthook = qt_uncaught_exception


# -------------------------------
# 主函数
# -------------------------------
def main():

    # 设置未捕获异常处理（保护 GUI）
    setup_uncaught_exception_handler()

    app_name = APP_CONFIG["app_name"]

    # 创建 Qt 应用实例
    try:
        QApplication.setApplicationName(app_name)
        app = QApplication(sys.argv)

    except Exception as e:
        logger.error(f"Qt 初始化失败：{e}")
        sys.exit(1)

    # -------------------------------
    # 自动执行 PostgreSQL DDL（如果适用）
    # -------------------------------
    ddl_result = auto_run_postgres_ddl(PROJECT_ROOT)

    # 显示启动信息（控制台 + GUI）
    print("\n" + "=" * 50)
    print(f"{app_name} v{APP_CONFIG['version']}")
    print(f"[配置] DB_TYPE={APP_DB_TYPE.upper()}")
    if APP_DB_TYPE == "sqlite":
        print(f"[数据库] SQLite 路径：{DATA_DIR / 'eclinic.db'}")
    else:
        print(f"[数据库] PostgreSQL: {PG_HOST}:{PG_PORT}/{PG_DATABASE}")

    # -------------------------------
    # 初始化全局数据库管理器（仅首次）
    # -------------------------------
    try:
        db_manager = get_database_manager(APP_DB_TYPE)
        logger.info("数据库连接成功")

    except ImportError as e:
        print(f"\n[!] 依赖缺失：{e}")
        print("\n安装指南:")
        if APP_DB_TYPE == "postgres":
            print('   pip install psycopg2-binary')
        else:
            print('   pip install python-docx pillow pandas sqlalchemy')
        sys.exit(1)

    except Exception as e:
        print(f"\n[!] 数据库连接失败：{e}")
        print(f"\n当前配置：DB_TYPE={APP_DB_TYPE}")

        if APP_DB_TYPE == "postgres":
            print("\nPostgreSQL 连接失败，可能的原因：")
            print("  1. PostgreSQL 服务未启动")
            print("  2. 连接参数错误（host/port/database/user/password）")
            print("  3. 数据库不存在")
            print("\n解决方案：")
            print("  - 启动 PostgreSQL 服务")
            print("  - 检查环境变量：PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD")
            print("  - 或使用 SQLite 开发模式：export DB_TYPE=sqlite")

        sys.exit(1)

    # -------------------------------
    # 创建主窗口 + 加载配置
    # -------------------------------
    try:
        window = MainWindow(
            db=db_manager,              # 传入数据库管理器（用于 Word 导入）
            app_config=APP_CONFIG       # 其他应用配置参数
        )

    except DataValidationError as e:
        print(f"\n[数据验证错误] {e}")
        sys.exit(1)

    # -------------------------------
    # 显示窗口 + 运行事件循环
    # -------------------------------
    window.show()

    logger.info("主窗口已启动，进入 GUI 模式")

    return_code = app.exec()

    # -------------------------------
    # 程序退出时关闭数据库连接
    # -------------------------------
    if hasattr(db_manager, 'pg_conn'):
        try:
            db_manager.pg_conn.close()
        except Exception as e:
            logger.warning(f"断开 PostgreSQL 连接失败：{e}")

    sys.exit(return_code)


if __name__ == "__main__":
    # 命令行参数支持（仅占位，方便后续扩展）
    import argparse

    parser = argparse.ArgumentParser(
        description=f"{APP_CONFIG['app_name']} - Word 处方录入系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s                    # 使用默认 PostgreSQL
    python main.py --db-type sqlite   # 开发环境（仅测试）

更多模块:
    - src/core/import_words_to_postgres.py   # Word → PostgreSQL 导入工具
    - src/core/backup_manager.py             # 自动备份管理器
        """
    )

    args = parser.parse_args()

    main()
