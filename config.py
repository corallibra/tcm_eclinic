# -*- coding: utf-8 -*-
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = OUTPUT_DIR / "logs"
DB_PATH = DATA_DIR / "eclinic.db"
for d in [DATA_DIR, OUTPUT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)
APP_CONFIG = {
    "app_name": "中医EClinic",
    "version": "1.0.0",
    "author": "李玉贤工作室",
    "db_path": str(DB_PATH),
    "samples_dir": str(DATA_DIR / "samples"),
    "log_path": str(LOG_DIR / "app.log"),
}
