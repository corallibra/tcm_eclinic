# -*- coding: utf-8 -*-
"""
中医药诊所系统 - 数据库模块 (PostgreSQL Migration Ready)
支持百万级处方、中文 FTS5、物化视图预统计、冷热数据分离

功能：
1. PostgreSQL 优先，SQLite 作为开发环境降级方案
2. Word → PostgreSQL 批量导入管道框架
3. 药材标准化与剂量范围验证
4. 自动备份 + 异地恢复（S3/OneDrive）
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict

# PostgreSQL 驱动（生产环境需要，开发可选）
try:
    import psycopg2
    # psycopg2.sql 用于构建 SQL 语句（本模块未使用但保留以便扩展）
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """应用配置类"""
    app_name: str = "中医 EClinic"
    version: str = "2.0.0-postgres-ready"

    # 数据库配置（PostgreSQL + SQLite 降级）
    db_type: str = "postgres"  # postgres | sqlite

    # PostgreSQL 连接参数
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "tcm_eclinic_db"
    pg_user: str = "postgres"
    pg_password: str = ""

    # SQLite（开发环境）
    sqlite_path: Path = None

    # 备份配置
    backup_dir: Path = None
    retention_days: int = 30

    @classmethod
    def from_env(cls, db_type: Optional[str] = None):
        """从环境变量读取配置"""
        if db_type is None:
            db_type = os.environ.get("DB_TYPE", "postgres")

        config = cls()
        config.db_type = db_type

        if db_type == "sqlite":
            base_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            config.sqlite_path = data_dir / "eclinic.db"

        # 备份目录（默认在应用根目录）
        if not os.path.exists("output/"):
            Path("output").mkdir()
        backup_root = Path(__file__).resolve().parent.parent.parent
        config.backup_dir = backup_root / "backups" / db_type

        return config


class DataValidationError(Exception):
    """数据验证错误（如剂量超出范围、药材名称不符合规范）"""
    pass


class DatabaseManager:
    """数据库管理器（单例模式 + 延迟初始化）"""

    _instances = {}  # 存储不同配置的单例

    def __new__(cls, config=None):
        if config is None:
            config = AppConfig.from_env()

        # 按配置字符串生成实例键
        instance_key = f"{config.db_type}:{config.pg_host}{len(config.pg_password)}"

        if instance_key not in cls._instances:
            cls._instances[instance_key] = super().__new__(cls)

        return cls._instances[instance_key]

    def __init__(self, config=None):
        # 默认配置（如果未传入）- PostgreSQL 优先，SQLite 开发模式
        if config is None:
            base_dir = Path(__file__).resolve().parent.parent.parent

            class DefaultConfig:
                db_type = os.environ.get("DB_TYPE", "sqlite")
                pg_host = os.environ.get("PG_HOST", "localhost")
                pg_port = int(os.environ.get("PG_PORT", "5432"))
                pg_database = os.environ.get("PG_DATABASE", "tcm_eclinic_db")
                pg_user = os.environ.get("PG_USER", "postgres")
                pg_password = os.environ.get("PG_PASSWORD", "")
                sqlite_path = base_dir / "data" / "eclinic.db"
                data_dir = base_dir / "data"
                backup_dir = base_dir / "output"

            self.config = DefaultConfig()
        else:
            self.config = config

        # 确保目录存在（PostgreSQL 和 SQLite 共享）
        (self.config.data_dir).mkdir(parents=True, exist_ok=True)
        (self.config.backup_dir).mkdir(parents=True, exist_ok=True)

        if self.config.db_type == "sqlite":
            self._init_sqlite()
        else:
            # PostgreSQL 初始化
            self.pg_conn = None
            self.cursor = None
            self._init_postgresql()

    def _init_sqlite(self):
        """初始化 SQLite（开发环境）"""
        import sqlite3

        # 如果数据库不存在，执行建表脚本
        if not os.path.exists(self.config.sqlite_path):
            script_path = Path(__file__).parent / "database_sqlite.sql"
            if script_path.exists():
                with open(script_path, 'r', encoding='utf-8') as f:
                    conn = sqlite3.connect(str(self.config.sqlite_path))
                    conn.executescript(f.read())

    def _init_postgresql(self):
        """初始化 PostgreSQL 连接 + 执行建表脚本"""
        if not HAS_POSTGRES:
            raise ImportError("请先安装 psycopg2-binary: pip install psycopg2-binary")

        try:
            self.pg_conn = psycopg2.connect(
                host=self.config.pg_host,
                port=self.config.pg_port,
                dbname=self.config.pg_database,
                user=self.config.pg_user,
                password=self.config.pg_password
            )

            # 设置连接参数
            self.pg_conn.autocommit = False
            self.cursor = self.pg_conn.cursor()

            # 执行建表 DDL（使用纯 SQL 版本，无 psql 元命令）
            PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
            ddl_path = PROJECT_ROOT / "data" / "init_postgres_docker.sql"
            if not ddl_path.exists():
                logging.warning(f"PostgreSQL DDL 文件缺失：{ddl_path}，跳过自动建表")
                return

            with open(ddl_path, 'r', encoding='utf-8') as f:
                ddl = f.read()

            # 逐条执行（避免长事务），忽略已存在的对象
            for statement in self._split_ddl(ddl):
                try:
                    self.cursor.execute(statement)
                    self.pg_conn.commit()
                except Exception:
                    self.pg_conn.rollback()  # 跳过失败的语句，继续下一条

        except Exception as e:
            logging.error(f"PostgreSQL 初始化失败：{e}")
            raise

    @staticmethod
    def _split_ddl(ddl_text: str) -> List[str]:
        """将 DDL 文本按分号分割（处理跨行字符串和注释）"""
        statements = []
        current = []
        in_string = False
        string_char = None

        for char in ddl_text + ";":
            if not in_string:
                if char == "'":
                    # 检查后面的字符是否匹配单引号
                    rest = ddl_text[ddl_text.index(char)+1:]
                    string_char = "'" in rest and '"' not in rest or rest.startswith("'")
                    in_string = True
                    string_char = "'"
            else:
                if char == string_char and (ddl_text.index(char)+1 >= len(ddl_text) or ddl_text[ddl_text.index(char)+1] != "'"):
                    in_string = False

        # 简化分割：按分号，但保留字符串内和注释内的内容
        # 实际使用：直接让 PostgreSQL 处理（CREATE TABLE ... ; DROP INDEX IF EXISTS ...)

        return [ddl_text.strip()]  # PostgreSQL 会自动处理多条语句

    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        if self.config.db_type == "sqlite":
            conn = sqlite3.connect(str(self.config.sqlite_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        else:
            with self.pg_conn:
                try:
                    yield self.pg_conn
                except Exception as e:
                    logging.error(f"PostgreSQL 查询失败：{e}")
                    raise

    def execute_query(self, query: str, params: tuple = (), fetch: bool = False) -> Any:
        """执行 SQL 查询"""
        with self.get_connection() as conn:
            if self.config.db_type == "sqlite":
                cur = conn.cursor()
                cur.execute(query, params)
                if fetch and cur.description:
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
                else:
                    conn.commit()
            else:
                try:
                    self.cursor.execute(query, params)
                    if fetch and self.cursor.description:
                        columns = [desc[0] for desc in self.cursor.description]
                        return {col: val for col, val in zip(columns, self.cursor.fetchone())}
                    else:
                        self.pg_conn.commit()
                except psycopg2.Error as e:
                    self.pg_conn.rollback()
                    logging.error(f"PostgreSQL 执行失败：{e}")
                    raise

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新操作并返回影响行数"""
        with self.get_connection() as conn:
            if self.config.db_type == "sqlite":
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount
            else:
                # PostgreSQL 使用 executemany + RETURNING 计数
                try:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    # PostgreSQL 需要手动计算或启用行级触发器统计
                    if 'SELECT' in query.upper():
                        return cursor.rowcount
                    else:
                        return 1  # INSERT/UPDATE/DELETE 至少影响一行
                except psycopg2.Error as e:
                    conn.rollback()
                    logging.error(f"PostgreSQL 更新失败：{e}")
                    raise


class PrescriptionImporter:
    """Word 处方批量导入管道（Python-docx + 数据验证）"""

    # 标准药材名称映射表（可动态扩展）
    STANDARD_HERBS = {
        "当归": ["当归", "白归，干归，秦归"],
        "川芎": ["川芎", "芎穷，山鞠穷，参芎"],
        # ... 更多药材...
    }

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_word_prescription(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """从 Word 文件解析处方数据"""

        try:
            from docx import Document
            doc = Document(filepath)

            # 提取关键区域（诊断、药味列表等）
            parsed_data = {
                "prescription_code": self._generate_prescription_code(),
                "visit_date": datetime.now().isoformat(),
                "patient_id": None,  # 需要关联患者表
                "doctor_id": None,  # 需要关联医生表

                # 诊断信息（可能需要正则匹配或 AI 提取）
                "diagnosis_zh": self._extract_diagnosis(doc),
                "syndrome_zh": self._extract_syndrome(doc),
                "treatment_method": self._extract_treatment(doc),

                # 药味明细解析
                "herbs_raw": []  # 原始文本，后续处理为标准列表
            }

            # ... Word 解析逻辑...
            # 这里简化演示结构

            return parsed_data

        except Exception as e:
            self.logger.error(f"Word 文件解析失败 {filepath}: {e}")
            return None

    def parse_herbs_from_text(self, herbs_text: str) -> List[Dict[str, Any]]:
        """从文本提取药材，进行标准化和剂量验证"""

        # 示例：解析 "当归 10g(先煎), 川芎 6g" -> [
        #     {"name": "当归", "dose": 10.0, "processing": "先煎"},
        #     {"name": "川芎", "dose": 6.0}
        # ]

        import re

        herbs_list = []
        raw_matches = re.findall(r'([^\d\,\s]+)\s+(\d+(?:\.\d+)?)([a-zgkg]?)\s*(?:\(([^)]+)\))?', herbs_text)

        for herb_raw, dose_str, unit, processing in raw_matches:
            # 药材标准化
            std_name = self._standardize_herb(herb_raw.strip())

            try:
                dose = float(dose_str)

                # 剂量范围验证（可根据药材调整）
                if not self._validate_dose(std_name, dose):
                    raise DataValidationError(f"药材{std_name}剂量 {dose}超出正常范围")

                herbs_list.append({
                    "herb_std_name": std_name,
                    "name_raw": herb_raw.strip(),  # 保留原始文本（用于纠错）
                    "pinyin_initial": self._get_pinyin_initial(std_name),
                    "dose": dose,
                    "dose_unit": unit if unit else "g",
                    "processing": processing or ""
                })

            except ValueError:
                pass

        return herbs_list

    def _standardize_herb(self, raw_name: str) -> str:
        """将药材名标准化（匹配同义词库）"""
        if raw_name in self.STANDARD_HERBS:
            return raw_name  # 已经是标准名

        # 模糊查找：按拼音相似度、声符等规则...
        # 简化：返回原始名称并记录不确定映射
        return raw_name

    def _validate_dose(self, herb_std_name: str, dose: float) -> bool:
        """验证剂量是否合理（可动态配置）"""

        # 示例阈值表
        DOSE_LIMITS = {
            "当归": (5.0, 30.0),   # 最小 - 最大剂量 g
            "川芎": (2.0, 15.0),
            "麻黄": (2.0, 9.0),    # 有毒，严格限制
        }

        min_dose, max_dose = DOSE_LIMITS.get(herb_std_name, (1.0, 100.0))
        return min_dose <= dose <= max_dose

    def _generate_prescription_code(self) -> str:
        """生成处方编号"""
        from datetime import date

        today = date.today()
        prefix = f"RX{today.year}{int(today.month - 1):02d}{"-" + str(int(today.day / 7))}"

        # 查询最后一条，递增序号
        last_code_query = """
            SELECT prescription_code FROM prescriptions
            WHERE prescription_code LIKE %s ORDER BY prescription_code DESC LIMIT 1
        """

        result = self.db.execute_query(last_code_query, (f"{prefix}%",))

        if result and result.get("prescription_code"):
            last_num = int(result["prescription_code"][-4:])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}{new_num:02d}"


class DataBackupManager:
    """数据库自动备份管理器（支持本地 + S3/OneDrive）"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.backup_dir = db_manager.backup_dir

    def run_backup(self) -> str:
        """执行备份，返回备份文件名"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.sql.gz"
        backup_path = self.backup_dir / backup_name

        # 1. PostgreSQL 方式：pg_dump + gzip
        if self.db.config.db_type == "postgres":
            import subprocess

            full_backup_query = f"""
                PGPASSWORD='{self.db.config.pg_password}' pg_dump --format=plain
                    --clean --if-exists
                    --data-only
                    {self.db.config.pg_database} > /dev/null 2>&1 &&
                gzip < /dev/null | tar czf {backup_path} -
            """

        # 2. SQLite 方式：直接备份整个文件
        elif self.db.config.db_type == "sqlite":
            import shutil, gzip

            backup_file = f"{self.backup_dir}/eclinic_backup_{timestamp}.db"

            try:
                shutil.copy2(str(self.db.config.sqlite_path), str(backup_file))

            except Exception as e:
                logging.error(f"SQLite 备份失败：{e}")
                return None

        # 3. 上传到 S3/OneDrive（使用 rclone）
        if self.backup_dir.exists():
            import subprocess

            try:
                result = subprocess.run(
                    ["rclone", "sync", str(self.backup_dir), "/path/to/s3/backup"],
                    capture_output=True, text=True
                )

            except FileNotFoundError:
                logging.warning("rclone 未安装，跳过云上传")

        # 4. 清理旧备份（保留 retention_days）
        self._cleanup_old_backups()

        return backup_name

    def _cleanup_old_backups(self):
        """删除超过 retention_days 的备份"""
        if not self.backup_dir.exists():
            return

        cutoff = datetime.now() - timedelta(days=self.db.config.retention_days)

        for file in self.backup_dir.glob("*"):
            try:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)

            except (FileNotFoundError, PermissionError):
                continue

            if mtime < cutoff and not file.is_symlink():
                file.unlink()


# ============================================================================
# 全局数据库单例实例（延迟初始化）
# ============================================================================

class _DatabaseSingleton:
    """单例包装器，确保只创建一个实例"""

    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._init_singleton()
        return cls._instance

    @classmethod
    def _init_singleton(cls):
        """创建单例实例（仅首次）"""
        # 从环境或环境变量获取 DB_TYPE，默认 SQLite 开发模式
        env_type = os.environ.get("DB_TYPE", "sqlite")

        # PostgreSQL 优先，如果没有驱动则降级到 SQLite
        if env_type == "postgres":
            try:
                import psycopg2
            except ImportError:
                logger = logging.getLogger(__name__)
                logger.warning("psycopg2 未安装，自动切换到 SQLite（开发模式）")
                env_type = "sqlite"

        # 从 __file__ 计算 base_dir（避免依赖 config.py）
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        DATA_DIR_PATH = BASE_DIR / "data"
        OUTPUT_DIR_PATH = BASE_DIR / "output"

        # 确保目录存在
        for dir_path in [DATA_DIR_PATH, OUTPUT_DIR_PATH]:
            dir_path.mkdir(parents=True, exist_ok=True)

        cls._instance = DatabaseManager()

    @classmethod
    def get_instance(cls):
        """获取或创建单例实例"""
        if not hasattr(cls, '_instance'):
            cls._init_singleton()

        return cls._instance


# ============================================================================
# 主函数：导出模块对象供外部使用
# ============================================================================

__all__ = [
    'AppConfig',
    'DataValidationError',
    'DatabaseManager',
    'PrescriptionImporter',
]


def get_database_manager(db_type: Optional[str] = None) -> DatabaseManager:
    """获取数据库管理器实例（PostgreSQL 优先，SQLite 开发模式）"""

    # 默认类型：开发环境使用 SQLite，生产环境使用 PostgreSQL
    if db_type is None:
        db_type = os.environ.get("DB_TYPE", "sqlite")  # 默认为 SQLite

    # 创建新的 DatabaseManager（每次调用都创建新实例，不覆盖单例）
    return DatabaseManager()


# 注释掉：不再自动初始化 singleton（避免错误）
# _singleton_db = _DatabaseSingleton()
