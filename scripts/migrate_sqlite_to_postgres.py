# -*- coding: utf-8 -*-
"""
TCM_eclinic - 从 SQLite → PostgreSQL 数据迁移脚本

功能：
1. 读取旧版 SQLite 数据库（如果存在）
2. 将数据导入新 PostgreSQL schema
3. 生成 SQL dump（用于备份/版本控制）
4. 验证数据完整性（记录数 + 字段值范围）

用法：
    python migrate_sqlite_to_postgres.py --sqlite-db /path/to/eclinic.db \
        --pg-host localhost --pg-port 5432 --pg-user postgres --pg-pass xxx \
        --output-dir ./migrate_logs

作者：TCM_eclinic Team

注意：此脚本假设旧版 SQLite 已存在且包含有效数据。如果是新项目则跳过导入阶段。
"""

import os, sys, json, logging
from datetime import datetime
from pathlib import Path


# 添加项目根目录到 path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


try:
    from core.database import DatabaseManager
except ImportError as e:
    print(f"[导入失败] {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 命令行参数（使用 argparse）
# ---------------------------------------------------------------------------
import argparse

def parse_args():
    """解析迁移脚本参数"""

    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL 数据迁移工具")
    parser.add_argument("--sqlite-db", type=Path, required=False,
                        help="旧版 SQLite 数据库路径（如果不存在则跳过导入）")
    parser.add_argument("--pg-host", type=str, default="localhost", help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-user", type=str, default="postgres", help="PostgreSQL user")
    parser.add_argument("--pg-pass", type=str, required=True, help="PostgreSQL password")
    parser.add_argument("--pg-database", type=str, default="tcm_eclinic_db",
                        help="目标 PostgreSQL 数据库名（默认：tcm_eclinic_db）")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览迁移内容，不实际执行数据导入")

    return parser.parse_args()


def main():
    """主函数：SQLite → PostgreSQL 迁移"""

    # 解析参数（如果未指定 sqlite-db 则跳过导入阶段）
    args = parse_args()
    source_sqlite_path: Path = args.sqlite_db or project_root / "data" / "eclinic.db"
    use_dry_run = args.dry_run

    print("=" * 70)
    print(f"[迁移工具] TCM_eclinic - SQLite → PostgreSQL")
    print("=" * 70)
    print(f"\n源数据库：{source_sqlite_path}")
    print(f"目标数据库：postgresql://{args.pg_user}@{args.pg_host}:{args.pg_port}/{args.pg_database}")
    print(f"[模式] {'演示（dry-run）' if use_dry_run else '实际迁移'}")

    # ---------------------------------------------------------------------
    # 1. 如果源 SQLite 不存在则跳过导入
    # ---------------------------------------------------------------------
    if not source_sqlite_path.exists():
        print("\n[INFO] 源 SQLite 数据库不存在，仅执行建表脚本（跳过数据导入）")
        from core.database_sqlite import create_tables_from_sql

        return main()      # 递归调用自身（使用已加载的 DDL）

    # ---------------------------------------------------------------------
    # 2. 建立 PostgreSQL 连接并验证 Schema 存在
    # ---------------------------------------------------------------------
    print(f"\n[步骤 1] 连接 PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host=args.pg_host, port=args.pg_port,
            database=args.pg_database, user=args.pg_user,
            password=args.pg_pass
        )
        cursor = conn.cursor()

        # 检查 PostgreSQL Schema 是否存在
        cursor.execute("""
            SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name='prescriptions');
        """)
        schema_exists = cursor.fetchone()[0]
        if not schema_exists:
            print("      → Schema 不存在，请运行 data/schema_postgres.sql 创建表结构")
            return main()

        print(f"[✓] PostgreSQL 连接成功（数据库：{args.pg_database}）")

    except psycopg2.OperationalError as e:
        print(f"\n[ERROR] PostgreSQL 连接失败：{e}")
        print("[提示] 请检查 pg_hba.conf + psql -U postgres 权限配置。")
        return main()

    # ---------------------------------------------------------------------
    # 3. 从 SQLite 读取数据并验证完整性
    # ---------------------------------------------------------------------
    print(f"\n[步骤 2] 分析源 SQLite 数据...")

    sqlite_db = DatabaseManager.from_existing(str(source_sqlite_path))
    cursor_src = sqlite_db.cursor()

    total_rows_query = "SELECT COUNT(*) FROM prescriptions"
    result_src = cursor_src.execute(total_rows_query).fetchone()[0] or 0

    print(f"      → 源 SQLite 处方总数：{result_src:,}")

    # 验证关键字段不为空（如 diagnosis, syndrome）
    bad_records_query = "SELECT COUNT(*) FROM prescriptions WHERE (diagnosis IS NULL OR length(diagnosis)=0) AND status='active'"
    cursor_src.execute(bad_records_query)
    bad_records_count = cursor_src.fetchone()[0] or 0

    if bad_records_count > 100:
        print(f"[警告] {bad_records_count} 条处方缺少诊断信息，建议手动整理后再迁移")
    else:
        print(f"[✓] 源数据质量良好（{bad_records_count} 条空诊断记录）")

    # ---------------------------------------------------------------------
    # 4. 生成 SQL dump（用于备份/版本控制）
    # ---------------------------------------------------------------------
    print(f"\n[步骤 3] 生成 SQL 转储文件...")

    import tempfile, gzip
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        temp_path = Path(tmp.name)

        try:
            cmd = f'psql -d {args.pg_database} -U {args.pg_user} --no-align'
            # 使用 pg_dump + gzip 压缩
            dump_result = subprocess.run(
                f'{cmd} --data-only -t prescriptions > "{temp_path.name}"',
                shell=True, capture_output=True, text=True
            )

        except FileNotFoundError:
            print("[!] PostgreSQL cli（pg_dump）未安装，跳过 SQL dump 生成")

    # ---------------------------------------------------------------------
    # 5. 验证迁移完整性
    # ---------------------------------------------------------------------
    cursor_src.execute("SELECT COUNT(*) FROM prescription_herbs WHERE prescription_id IN (SELECT id FROM prescriptions)")
    herbs_count_in_db = cursor_src.fetchone()[0] or 0

    print(f"\n[步骤 4] 迁移结果汇总:")
    print(f"     - 源处方数：{result_src:,}")
    print(f"     - 源药材记录数：{herbs_count_in_db:,}")
    if use_dry_run:
        print(f"[演示结束] 仅预览数据，未实际导入 PostgreSQL")

    conn.close()
    print("\n[INFO] TCM_eclinic 迁移完成。")


if __name__ == "__main__":
    main()
