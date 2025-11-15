# -*- coding: utf-8 -*-
"""
parse_docx_multi — 一个 Word 多次就诊记录解析器（增强版）
在原有功能基础上增加：
    - 自动识别四诊信息：望 / 闻 / 问 / 切 + 舌 / 脉
    - 自动拆分：症状（symptoms）/ 证候（zhenghou）/ 治法（zhifa）/ 方药（prescription + herbs）
    - 医生署名不限于某个人：识别“医师 / 医生 / 接诊医师 / 签名”等模式
保持原有字段：
    patient_name, gender, age, complaint, diagnosis_clinic,
    zhenghou, prescription, herbs, doctor, date
"""

import os
import re
import zipfile
import traceback
from datetime import datetime

import mammoth
from docx import Document
from src.core import db


def _clean(s: str) -> str:
    return s.replace("\u3000", " ").replace("\xa0", " ").strip()


# -------------------------------
# 智能方药解析（保留原有能力并增强鲁棒性）
# -------------------------------
def parse_herb_line(line: str):
    line = line.strip()
    if not line:
        return None

    # 药名 + 数字剂量 + 单位
    # 例如：桂枝 9g / 白芍12克 / 炙甘草   3 g
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
def read_word_paragraphs(file_path: str):
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
    lines = [_clean(x) for x in text.split("\n") if _clean(x)]
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

    # 若整篇未出现日期标记，则当作单次就诊整体
    if not sessions and lines:
        sessions.append(dict(date="", lines=lines))

    return sessions


# -------------------------------
# 解析单次就诊记录（在原有基础上加入四诊等字段）
# -------------------------------
def parse_case_one(date, lines, file_name):
    """
    保留原有字段：
        patient_name, gender, age, complaint,
        diagnosis_clinic, zhenghou, prescription, herbs, doctor, date
    新增字段（不会破坏旧代码）：
        symptoms, history, inspection, auscultation_olfaction, inquiry,
        palpation, tongue, pulse, zhifa
    """
    data = {
        "patient_name": "",
        "gender": "",
        "age": "",
        "complaint": "",
        "diagnosis_clinic": "",
        "zhenghou": "",            # 原来就有：含脉/舌/证的行
        "prescription": "",
        "herbs": [],
        "doctor": "",
        "date": date,

        # 新增字段（中医结构化）
        "symptoms": "",                 # 主诉 + 问诊具体症状
        "history": "",                  # 现病史 / 既往史
        "inspection": "",               # 望诊
        "auscultation_olfaction": "",   # 闻诊
        "inquiry": "",                  # 问诊
        "palpation": "",                # 切诊
        "tongue": "",                   # 舌象
        "pulse": "",                    # 脉象
        "zhifa": "",                    # 治法 / 治则
    }

    # 保留原逻辑：姓名从文件名提取
    m_file = re.match(r"([\u4e00-\u9fa5·]{2,6})", file_name)
    if m_file:
        data["patient_name"] = m_file.group(1)

    herbs_section = False
    herb_lines = []

    # 四诊辅助词
    pulse_words = ["弦", "细", "滑", "数", "迟", "沉", "弱", "缓", "紧", "洪"]
    tongue_words = ["淡", "红", "绛", "胖", "瘦", "裂", "苔", "黄", "白", "腻", "厚", "薄"]

    for line in lines:
        if not line:
            continue

        # ========== 基本信息：保留原有行为 ==========
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

        # ========== 主诉 / 症状 ==========
        if line.startswith(("主诉", "主 诉")):
            content = line.split("：", 1)[-1].strip()
            data["complaint"] = content       # 保留原字段
            data["symptoms"] += content + " " # 新增：症状内容
            continue

        # 现病史 / 既往史
        if line.startswith(("现病史", "既往史")):
            content = line.split("：", 1)[-1].strip()
            data["history"] += content + " "
            continue

        # ========== 四诊：望闻问切 ==========
        # 望诊
        if re.match(r"^(望诊|望：|四诊所见)", line):
            content = line.split("：", 1)[-1].strip()
            data["inspection"] += content + " "
            continue

        # 闻诊
        if re.match(r"^(闻诊|闻：)", line):
            content = line.split("：", 1)[-1].strip()
            data["auscultation_olfaction"] += content + " "
            continue

        # 问诊
        if re.match(r"^(问诊|问：)", line) or line.startswith("问其"):
            content = line.split("：", 1)[-1].strip()
            data["inquiry"] += content + " "
            data["symptoms"] += content + " "
            continue

        # 切诊/脉象（明确标签）
        if re.match(r"^(切诊|切：|脉象)", line):
            content = line.split("：", 1)[-1].strip()
            data["palpation"] += content + " "
            if content:
                data["pulse"] = content
            continue

        # 舌象（模糊匹配）
        if "舌" in line and any(w in line for w in tongue_words):
            content = line.split("：", 1)[-1].strip() if "：" in line else line
            data["tongue"] = content

        # 脉象（模糊匹配）
        if "脉" in line and any(w in line for w in pulse_words):
            content = line.split("：", 1)[-1].strip() if "：" in line else line
            data["pulse"] = content

        # ========== 诊断 / 证候 / 治法：保留原逻辑并增强 ==========
        if "诊断" in line:
            data["diagnosis_clinic"] = line.split("：", 1)[-1].strip()

        # 原有逻辑：若含“脉/舌/证”，整行加入 zhenghou
        if "脉" in line or "舌" in line or "证" in line:
            data["zhenghou"] += line + " "

        # 专门辨证/证候标签
        if any(k in line for k in ["辨证", "证候", "中医诊断"]):
            content = line.split("：", 1)[-1].strip()
            data["zhenghou"] += content + " "

        # 治法/治则
        if any(k in line for k in ["治法", "治则"]):
            content = line.split("：", 1)[-1].strip()
            data["zhifa"] += content + " "
        # ========== 方药区块开始/继续（在原有基础上增强） ==========
        # 原逻辑：以部分中药名开头认为是方药
        if line.startswith(
            (
                "清", "炙", "熟", "金", "陈", "川", "当", "桑",
                "连", "款", "柴", "葛", "黄", "人参", "白芍", "甘草"
            )
        ):
            herbs_section = True

        # 新增：以“处方 / 方药 / 中药 / 用药”开头的行也视为方药段开始
        if re.match(r"^(处方|方药|中药|用药)[:：]?", line):
            content = line.split("：", 1)[-1].strip()
            if content:
                data["prescription"] += content + "\n"
                herb_lines.append(content)
            herbs_section = True
            continue

        if herbs_section:
            # 原逻辑：遇到“X数字”开头行则认为结束
            if re.match(r"^X?\d+", line):
                herbs_section = False
            else:
                herb_lines.append(line)
            # 继续下一行
            continue

        # 没有显式“处方：”但整行像“药名+剂量”的，也视作方药
        if re.match(r"^[\u4e00-\u9fa5·]+\s*[\d\.]*\s*[gG克qQ]*$", line):
            herb_lines.append(line)

        # ========== 医生署名（支持任意医生） ==========
        # 优先匹配“医师/医生/接诊医师/签名”等
        doctor_patterns = [
            r"(?:主治|接诊|出诊)?医师[:：]\s*([\u4e00-\u9fa5·]{2,10})",
            r"医生[:：]\s*([\u4e00-\u9fa5·]{2,10})",
            r"(?:签名|署名)[:：]\s*([\u4e00-\u9fa5·]{2,10})",
            r"医师$",
        ]
        for pat in doctor_patterns:
            m_doc = re.search(pat, line)
            if m_doc:
                name = m_doc.group(1) if m_doc.groups() else line.replace("医师", "").replace("医生", "").strip()
                if name:
                    data["doctor"] = name
                break

        # 特殊：整行形如“张三 医师”
        m_tail = re.match(r"([\u4e00-\u9fa5·]{2,10})[医醫]师$", line)
        if m_tail:
            data["doctor"] = m_tail.group(1)

        # 兼容旧逻辑：若行中直接出现具体医生姓名，也可认作 doctor
        # （比如文末孤立一行“李玉贤”）
        if not data["doctor"]:
            m_name_only = re.match(r"^[\u4e00-\u9fa5·]{2,10}$", line)
            if m_name_only:
                data["doctor"] = m_name_only.group(1)

    # ---------------- 方药最终解析（保留原行为） ----------------
    data["herbs"] = parse_herbs(herb_lines)
    if data["herbs"]:
        # 若 prescription 为空，则按原逻辑用 herbs 反生成
        if not data["prescription"]:
            data["prescription"] = "\n".join([f"{h['name']} {h['dose']}" for h in data["herbs"]])
    else:
        # 没有识别出 herbs 时，prescription 可能仍为手工内容（上方已写入）
        data["herbs"] = []

    return data


# -------------------------------
# 主接口：解析一个 Word 文件（多次就诊）
# -------------------------------
def parse_word_case_multi(file_path: str):
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
# 批量导入接口（保留原有行为）
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
