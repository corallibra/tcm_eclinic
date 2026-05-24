# -*- coding: utf-8 -*-
"""中医药诊所系统 - 统一应用配置（单一配置源：.env > 环境变量 > 默认值）"""

import os
from pathlib import Path

# 尝试加载 .env 文件（依赖 python-dotenv，可选）
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 未安装时使用系统环境变量


# -------------------------------
# 1. 项目根目录 + 基础路径
# -------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = OUTPUT_DIR / "logs"

for d in [DATA_DIR, OUTPUT_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# -------------------------------
# 2. 数据库配置
# -------------------------------
APP_DB_TYPE = os.environ.get("DB_TYPE", "postgres")

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DATABASE = os.getenv("PG_DATABASE", "tcm_eclinic_db")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

if APP_DB_TYPE == "sqlite":
    SQLITE_PATH = DATA_DIR / "eclinic.db"


# -------------------------------
# 3. 备份配置
# -------------------------------
BACKUP_ROOT_PATH = OUTPUT_DIR / f"backups_{APP_DB_TYPE.upper()}"
if not BACKUP_ROOT_PATH.exists():
    BACKUP_ROOT_PATH.mkdir(parents=True, exist_ok=True)


# -------------------------------
# 4. 应用配置字典
# -------------------------------
APP_CONFIG = {
    "app_name": os.getenv("APP_NAME", "中医 EClinic"),
    "version": os.getenv("APP_VERSION", "2.0.0-postgres-ready"),
    "db_type": str(APP_DB_TYPE or "postgres"),
    "author": os.getenv("APP_AUTHOR", "李玉贤工作室"),

    "sqlite_path": str(SQLITE_PATH) if APP_DB_TYPE == "sqlite" else None,
    "data_dir": str(DATA_DIR),
    "output_dir": str(OUTPUT_DIR),

    "log_path": str(LOGS_DIR / "ec clinic.log"),
    "backup_root": str(BACKUP_ROOT_PATH),

    "pg_host": PG_HOST,
    "pg_port": PG_PORT,
    "pg_database": PG_DATABASE,
    "pg_user": PG_USER,
}


# -------------------------------
# 5. 辅助函数
# -------------------------------
def ensure_dirs():
    """确保所有目录存在"""
    for path in [DATA_DIR, OUTPUT_DIR, LOGS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print(f"[Config] DB_TYPE={APP_DB_TYPE}")
    print(f"[Config] PGHOST={PG_HOST}:{PG_PORT}/{PG_DATABASE}")
    print(f"[Config] Backup root: {BACKUP_ROOT_PATH.absolute()}")
