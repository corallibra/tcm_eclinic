# -*- coding: utf-8 -*-
"""
parse_docx_multi — 一个 Word 多次就诊记录解析器（终极版）
"""

import os
import re
import zipfile
import traceback
from datetime import datetime

import mammoth
from docx import Document
from src.core import db


def _clean(s):
    return s.replace("\u3000", " ").replace("\xa0", " ").strip()


# -------------------------------
# 智能方药解析
# -------------------------------
def parse_herb_line(line):
    line = line.strip()
    if not line:
        return None

    # 药名 + 数字剂量 + 单位
    m = re.match(r"([\u4e00-\u9fa5·]+)\s*([\d\.]+)?\s*([gG克qQ]*)", line)
    if not m:
        return None

    name = m.group(1).strip()
    dose = (m.group(2) or "") + (m.group(3) or "")

    return dict(name=name, dose=dose, remark="")


def parse_herbs(block_lines):
    herbs = []
    for line in block_lines:
        h = parse_herb_line(line)
        if h:
            herbs.append(h)
    return herbs


# -------------------------------
# 解析 Word 内容 → 文本片段
# -------------------------------
def read_word_paragraphs(file_path):
    lower = file_path.lower()

    # 排除主题文件
    if "theme" in lower:
        raise ValueError("此文件是主题模板，不包含正文")

    # docx 或伪装 docx
    if lower.endswith(".docx") or zipfile.is_zipfile(file_path):
        doc = Document(file_path)
        return [_clean(p.text) for p in doc.paragraphs if _clean(p.text)]

    # 旧 doc → HTML → 文本
    with open(file_path, "rb") as f:
        html = mammoth.convert_to_html(f).value
    text = re.sub("<[^>]+>", "\n", html)
    lines = [ _clean(x) for x in text.split("\n") if _clean(x) ]
    return lines


# -------------------------------
# 拆分多次就诊（核心逻辑）
# -------------------------------

DATE_PATTERN = re.compile(r"(\d{4}[年/-]\d{1,2}[月/-]\d{1,2})")
DATE_PATTERN2 = re.compile(r"就诊时间[:：]\s*(\d{4}[年/-]\d{1,2}[月/-]\d{1,2})")


def split_by_dates(lines):
    """
    输入：整篇 Word 文本行
    输出：一个包含多个 {date, lines[]} 的列表
    """

    sessions = []
    current = None

    for line in lines:
        # 匹配 YYYY-MM-DD / YYYY年MM月DD日
        m = DATE_PATTERN.search(line)
        m2 = DATE_PATTERN2.search(line)

        if m or m2:
            date_raw = m.group(1) if m else m2.group(1)
            date_std = (
                date_raw.replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
                .replace("/", "-")
            )

            # 开启新的就诊记录
            current = dict(date=date_std, lines=[])
            sessions.append(current)
            continue

        # 普通行 → 加入当前记录
        if current:
            current["lines"].append(line)

    return sessions


# -------------------------------
# 解析单次就诊记录
# -------------------------------
def parse_case_one(date, lines, file_name):
    data = {
        "patient_name": "",
        "gender": "",
        "age": "",
        "complaint": "",
        "diagnosis_clinic": "",
        "zhenghou": "",
        "prescription": "",
        "herbs": [],
        "doctor": "",
        "date": date,
    }

    # 姓名从文件名提取
    m_file = re.match(r"([\u4e00-\u9fa5·]{2,6})", file_name)
    if m_file:
        data["patient_name"] = m_file.group(1)

    herbs_section = False
    herb_lines = []

    for line in lines:

        # 姓名性别年龄
        if "姓名" in line:
            mn = re.search(r"姓名[:：]\s*([\u4e00-\u9fa5·]{1,10})", line)
            if mn:
                data["patient_name"] = mn.group(1)

            mg = re.search(r"性别[:：]\s*([男女])", line)
            if mg:
                data["gender"] = mg.group(1)

            ma = re.search(r"年龄[:：]\s*(\d+)", line)
            if ma:
                data["age"] = ma.group(1)

        # 主诉
        if line.startswith(("主诉", "主 诉")):
            data["complaint"] = line.split("：", 1)[-1].strip()

        # 诊断
        if "诊断" in line:
            data["diagnosis_clinic"] = line.split("：", 1)[-1].strip()

        # 证候/辨证
        if "脉" in line or "舌" in line or "证" in line:
            data["zhenghou"] += line + " "

        # 方药开始标志
        if line.startswith(("清", "炙", "熟", "金", "陈", "川", "当", "桑", "连", "款", "柴", "葛", "黄", "人参", "白芍", "甘草")):
            herbs_section = True

        if herbs_section:
            # 遇到非药物段落 → 结束
            if re.match(r"^X?\d+", line):
                herbs_section = False
            else:
                herb_lines.append(line)

        # 医生
        if "李玉贤" in line or "医师" in line or "医生" in line:
            data["doctor"] = line.replace("医师", "").replace("医生", "").strip()

    # 方药最终解析
    data["herbs"] = parse_herbs(herb_lines)
    data["prescription"] = "\n".join([f"{h['name']} {h['dose']}" for h in data["herbs"]])

    return data


# -------------------------------
# 主接口：解析一个 Word 文件（多次就诊）
# -------------------------------
def parse_word_case_multi(file_path):
    lines = read_word_paragraphs(file_path)
    file_name = os.path.basename(file_path)

    # 拆分多个就诊段
    sessions = split_by_dates(lines)

    cases = []
    for s in sessions:
        case = parse_case_one(s["date"], s["lines"], file_name)
        cases.append(case)

    return cases


# -------------------------------
# 批量导入接口
# -------------------------------
def import_cases_from_folder(folder):
    ok = 0
    fail = 0

    for root, dirs, files in os.walk(folder):
        for fn in files:
            fpath = os.path.join(root, fn)
            if not fn.lower().endswith((".docx", ".doc")):
                continue

            try:
                case_list = parse_word_case_multi(fpath)
                for c in case_list:
                    db.save_prescription(c)
                    ok += 1
                print(f"✔ {fn} → {len(case_list)} 条记录导入成功")
            except Exception as e:
                fail += 1
                print(f"❌ {fn} 解析失败 | {e}")
                traceback.print_exc()

    print(f"\n📊 导入完成：成功 {ok} 条，就诊记录；失败 {fail} 文件。")

# -------------------------------
# 向后兼容旧接口：parse_word_case()
# -------------------------------
def parse_word_case(file_path):
    """
    兼容旧版本接口：
    返回 Word 文件中第一条就诊记录。
    用于 GUI 的单次导入功能。
    """
    cases = parse_word_case_multi(file_path)
    return cases[0] if cases else {}
