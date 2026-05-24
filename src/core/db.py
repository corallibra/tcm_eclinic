# -*- coding: utf-8 -*-
"""
中医电子病案数据库（医院级 V4 稳定版）
-------------------------------------
✔ 修复所有 query / timeline / 词云错误
✔ 不损失原有字段（id / name / zhenghou / prescription / doctor / date）
✔ 新增 full_json 字段 → 保存完整医案（complaint, tongue, pulse…）
✔ 完全兼容 parse_docx V4
✔ GUI Timeline / 词云 / 检索都不需要改动
"""

import os
import json
import sqlite3
from datetime import datetime

# -------------------------------
# 路径设置
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "eclinic.db")


# -------------------------------
# 数据库连接 & 初始化
# -------------------------------
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # —— 升级 cases 表，不破坏旧字段 ——
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            name TEXT,                -- 患者姓名
            zhenghou TEXT,            -- 证候/诊断（兼容旧字段）
            prescription TEXT,        -- 处方文本或 herbs JSON
            doctor TEXT,
            date TEXT,
            full_json TEXT            -- 新增：完整医案 JSON（complaint, symptoms, tongue…）
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            val TEXT
        )
    """)

    conn.commit()
    return conn


# -------------------------------
# 通用查询函数（修复 query 未定义问题）
# -------------------------------
def query(sql, params=None):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(sql, params or [])
    rows = cur.fetchall()
    conn.close()
    return rows


# -------------------------------
# 自动生成 9 位就诊号（20251115001）
# -------------------------------
def _generate_case_id(conn):
    today = datetime.now().strftime("%Y%m%d")
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM cases WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (today + "%",),
    )
    last = cur.fetchone()
    if last:
        seq = int(last["id"][-3:]) + 1
    else:
        seq = 1
    return f"{today}{seq:03d}"


# -------------------------------
# 保存医案（兼容所有旧字段 + 解析器 V4 字段）
# -------------------------------
def save_prescription(data: dict) -> str:
    conn = _conn()
    cid = _generate_case_id(conn)
    cur = conn.cursor()

    # —— 基本字段（兼容） ——
    name = (
        data.get("patient_name")
        or data.get("name")
        or data.get("姓名")
        or ""
    )

    zhenghou = (
        data.get("zhenghou")
        or data.get("diagnosis_clinic")
        or data.get("complaint")
        or ""
    )

    # —— prescription 兼容（文字 / herbs JSON） ——
    prescription = data.get("prescription")
    if not prescription and "herbs" in data:
        try:
            prescription = json.dumps(data["herbs"], ensure_ascii=False)
        except:
            prescription = str(data["herbs"])

    # —— 新增完整医案 JSON ——（timeline 使用）
    full_json = json.dumps(data, ensure_ascii=False)

    cur.execute(
        """
        INSERT INTO cases (id, name, zhenghou, prescription, doctor, date, full_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cid,
            name,
            zhenghou,
            prescription or "",
            data.get("doctor", ""),
            data.get("date", ""),
            full_json,
        ),
    )

    conn.commit()
    conn.close()

    print(f"[DB] 保存成功 → {cid} | {name}")
    return cid


# -------------------------------
# 模糊搜索（供 QueryTab 使用）
# -------------------------------
def search_cases(keyword=""):
    kw = f"%{keyword.strip()}%" if keyword.strip() else "%"

    rows = query(
        """
        SELECT id, name, zhenghou, date, doctor
        FROM cases
        WHERE name LIKE ? OR zhenghou LIKE ? OR doctor LIKE ?
        ORDER BY date DESC, id DESC
        """,
        (kw, kw, kw),
    )
    return rows


# -------------------------------
# Timeline：按姓名查所有记录（修复字段映射）
# -------------------------------
def get_all_cases_by_name(name):
    rows = query(
        """
        SELECT full_json
        FROM cases
        WHERE name = ?
        ORDER BY date ASC, id ASC
        """,
        (name,),
    )

    result = []
    for r in rows:
        try:
            result.append(json.loads(r["full_json"]))
        except:
            pass
    return result


# -------------------------------
# 词云模块：提取所有病例
# -------------------------------
def get_all_cases():
    rows = query("SELECT full_json FROM cases ORDER BY id DESC")
    result = []
    for r in rows:
        try:
            result.append(json.loads(r["full_json"]))
        except:
            pass
    return result


# -------------------------------
# 高频药材统计（兼容旧逻辑）
# -------------------------------
def stat_cases(start="", end=""):
    base = "SELECT prescription FROM cases"
    params = []

    if start and end:
        base += " WHERE date BETWEEN ? AND ?"
        params = [start, end]

    rows = query(base, params)

    from collections import Counter
    herbs_counter = Counter()

    for (txt,) in rows:
        try:
            arr = json.loads(txt)
            if isinstance(arr, list):
                for h in arr:
                    nm = (h.get("name") or "").strip()
                    if nm:
                        herbs_counter[nm] += 1
        except:
            pass

    return herbs_counter.most_common(20)


# -------------------------------
# 设置接口
# -------------------------------
def save_settings(d: dict):
    conn = _conn()
    cur = conn.cursor()
    for k, v in d.items():
        cur.execute(
            "REPLACE INTO settings(key,val) VALUES(?,?)",
            (k, str(v)),
        )
    conn.commit()
    conn.close()
    return True
