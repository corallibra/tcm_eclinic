# -*- coding: utf-8 -*-
"""
parse_docx V4 — 医院级兼容·稳定版
---------------------------------
特点：
    ✔ 不破坏原有任何字段与逻辑
    ✔ 主诉/证候自动识别（即使不含“主诉：”标签）
    ✔ 医生识别加入黑名单，避免误判实验室检查
    ✔ 支持 20 字以内姓名（少数民族姓名兼容）
    ✔ 舌脉自由行识别
    ✔ 药物智能解析（数字+单位 全格式）
    ✔ 多次就诊自动拆分
    ✔ .doc/.docx 全兼容（mammoth 转换）
"""

import os
import re
import zipfile
import traceback
from datetime import datetime

import mammoth
from docx import Document
from src.core import db
# 医学检查/检验项目黑名单
LAB_HINT = [
    "血常规", "尿常规", "肝功", "肾功", "心电图", "CT", "B超", "彩超",
    "淋巴", "比率", "蛋白", "乳酸", "葡萄糖", "球蛋白", "红细胞",
]

# 医技/指标黑名单
LAB_UNITS = ["mmol", "g/L", "mg", "IU", "%", "×", "10^"]

def is_lab_line(line: str):
    if any(k in line for k in LAB_HINT):
        return True
    if any(u in line for u in LAB_UNITS):
        return True
    # 单独的医学指标/检查编号
    if re.fullmatch(r"[A-Z]{1,3}\d{1,3}", line):
        return True
    return False
def _clean(s: str) -> str:
    if not s:
        return ""
    return s.replace("\u3000", " ").replace("\xa0", " ").strip()


def is_garbage_line(line: str) -> bool:
    if not line:
        return True

    # 页码/单独数字
    if re.fullmatch(r"\d{1,3}", line.strip()):
        return True

    # 表格符号
    if re.fullmatch(r"[·\.×x\*○●□■]+", line):
        return True

    # PAGE
    if line.strip().lower() in ("page", "pages"):
        return True

    # 仅符号
    if re.fullmatch(r"[-=]{3,}", line):
        return True

    return False
DOSE = re.compile(r"(?P<num>[\d\.]+)\s*(?P<unit>g|G|克|q|Q|片|粒|枚|付)?")

def parse_herb_line(line: str):
    line = _clean(line)

    m = re.match(r"([\u4e00-\u9fa5·]+)\s*([\d\.]+)?\s*([gG克qQ片粒枚付]*)", line)
    if not m:
        return None

    name = m.group(1)
    num = m.group(2) or ""
    unit = m.group(3) or ""
    dose = f"{num}{unit}".strip()

    return dict(name=name, dose=dose, remark="")
def read_word_paragraphs(file_path: str):
    lower = file_path.lower()

    # .docx 或 zip 格式
    if lower.endswith(".docx") or zipfile.is_zipfile(file_path):
        try:
            doc = Document(file_path)
            out = []
            for p in doc.paragraphs:
                t = _clean(p.text)
                if t:
                    out.append(t)
            return out
        except Exception:
            pass  # 尝试 fallback

    # 其他情况 → mammoth
    try:
        with open(file_path, "rb") as f:
            html = mammoth.convert_to_html(f).value
        text = re.sub("<[^>]+>", "\n", html)
        return [_clean(x) for x in text.split("\n") if _clean(x)]
    except Exception:
        raise ValueError(f"无法读取 Word 文档：{file_path}")
# -------------------------------------------------------------
# 日期识别（自由格式 → 标准 yyyy-mm-dd）
# -------------------------------------------------------------
DATE_PATTERNS = [
    r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?",
    r"就诊时间[:：]\s*(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
]

def extract_date(line: str):
    for pat in DATE_PATTERNS:
        m = re.search(pat, line)
        if m:
            y, mth, d = m.groups()
            return f"{y}-{int(mth):02d}-{int(d):02d}"
    return None


# -------------------------------------------------------------
# 舌脉识别（自由行 + 模糊匹配）
# -------------------------------------------------------------
TONGUE_HINT = ["舌", "苔", "淡", "红", "黄", "白", "腻", "厚", "薄"]
PULSE_HINT  = ["脉", "弦", "细", "滑", "数", "迟", "沉", "弱", "浮", "紧", "洪"]

def is_tongue_line(line: str):
    return "舌" in line and any(w in line for w in TONGUE_HINT)

def is_pulse_line(line: str):
    return "脉" in line and any(w in line for w in PULSE_HINT)


# -------------------------------------------------------------
# 多次就诊拆分（完全兼容多格式）
# -------------------------------------------------------------
def split_by_dates(lines):
    sessions = []
    current = None

    for line in lines:
        if not line or is_garbage_line(line):
            continue

        dt = extract_date(line)
        if dt:
            current = dict(date=dt, lines=[])
            sessions.append(current)
            continue

        if current:
            current["lines"].append(line)

    # 无日期 → 当成单次就诊
    if not sessions:
        return [dict(date="", lines=[l for l in lines if not is_garbage_line(l)])]

    return sessions


# -------------------------------------------------------------
# 医生识别（白名单 + 黑名单过滤）
# -------------------------------------------------------------
# 常用医生后缀
DOCTOR_SUFFIX = ["医师", "医生", "主任医师", "主治医师"]

def extract_doctor(line: str):
    line = _clean(line)

    # 黑名单：实验室检查
    if is_lab_line(line):
        return ""

    # 格式：**医师：张三**
    m = re.search(r"(?:主治|接诊|出诊|主任)?医师[:：]\s*([\u4e00-\u9fa5·]{2,20})", line)
    if m:
        return m.group(1)

    # 格式：**医生：张三**
    m = re.search(r"医生[:：]\s*([\u4e00-\u9fa5·]{2,20})", line)
    if m:
        return m.group(1)

    # 格式：张三 医师
    for suf in DOCTOR_SUFFIX:
        if line.endswith(suf):
            name = line[:-len(suf)].strip()
            if 2 <= len(name) <= 20:
                return name

    # 全汉字可能是医生名，但需排除药物与症状与检查
    if re.fullmatch(r"[\u4e00-\u9fa5·]{2,20}", line):
        # 排除症状（痛/胀/咳嗽等开头）
        if any(x in line for x in ["痛", "胀", "咳", "痒", "乏"]):
            return ""
        # 排除常见检查词
        if is_lab_line(line):
            return ""
        # 排除短病名（一般为2～4字）
        if len(line) <= 4:
            return ""
        return line

    return ""


# -------------------------------------------------------------
# 解析单次就诊（最核心函数）
# -------------------------------------------------------------
def parse_case_one(date: str, lines, file_name: str):
    # 完整字段（不删除任何旧字段）
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

        # 四诊扩展
        "symptoms": "",
        "history": "",
        "inspection": "",
        "auscultation_olfaction": "",
        "inquiry": "",
        "palpation": "",
        "tongue": "",
        "pulse": "",
        "zhifa": "",
    }

    # 从文件名提取姓名（增强：支持最长 20 字）
    m_file = re.match(r"([\u4e00-\u9fa5·]{2,20})", file_name)
    if m_file:
        data["patient_name"] = m_file.group(1)

    herbs_section = False
    herb_lines = []

    for line in lines:
        if not line or is_garbage_line(line):
            continue

        # -------------------------
        # 基本信息
        # -------------------------
        if "姓名" in line:
            m = re.search(r"姓名[:：]\s*([\u4e00-\u9fa5·]{2,20})", line)
            if m:
                data["patient_name"] = m.group(1)

        if "性别" in line:
            m = re.search(r"性别[:：]\s*([男女])", line)
            if m:
                data["gender"] = m.group(1)

        if "年龄" in line:
            m = re.search(r"年龄[:：]\s*(\d+)", line)
            if m:
                data["age"] = m.group(1)

        # -------------------------
        # 主诉（无标签自由识别）
        # -------------------------
        if "主诉" in line:
            c = line.split("：", 1)[-1].strip()
            data["complaint"] = c
            data["symptoms"] += c + " "
            continue

        # 自由行方式识别：出现“痛/胀/咳/痒/乏”即视为症状/主诉
        if any(k in line for k in ["痛", "胀", "咳", "痒", "乏", "不适", "肿"]):
            if not data["complaint"]:  # 若还没找到明确主诉
                data["complaint"] = line
            data["symptoms"] += line + " "
            continue

        # -------------------------
        # 舌脉（模糊识别）
        # -------------------------
        if is_tongue_line(line):
            content = line.split("：", 1)[-1].strip() if "：" in line else line
            data["tongue"] = content
            continue

        if is_pulse_line(line):
            content = line.split("：", 1)[-1].strip() if "：" in line else line
            data["pulse"] = content
            continue

        # -------------------------
        # 诊断 / 证候 / 治法
        # -------------------------
        if "诊断" in line:
            data["diagnosis_clinic"] = line.split("：", 1)[-1].strip()
            continue

        if any(k in line for k in ["证候", "辨证"]):
            data["zhenghou"] += line.split("：", 1)[-1].strip() + " "
            continue

        if any(k in line for k in ["治法", "治则"]):
            data["zhifa"] += line.split("：", 1)[-1].strip() + " "
            continue

        # -------------------------
        # 方药段判断（智能触发）
        # -------------------------
        if re.match(r"^(处方|方药|中药|用药)[:：]?", line):
            herbs_section = True
            content = line.split("：", 1)[-1].strip()
            if content:
                herb_lines.append(content)
                data["prescription"] += content + "\n"
            continue

        # 药材自由行，如 “桂枝 9g”
        if re.match(r"^[\u4e00-\u9fa5·]+\s*[\d\.]+", line):
            herbs_section = True
            herb_lines.append(line)
            continue

        # 方药段进行中
        if herbs_section:
            # 若出现“水煎”“每日”“7剂”“10剂” → 方药段结束
            if any(k in line for k in ["水煎", "每日", "每服", "7付", "10剂", "×", "X"]):
                herbs_section = False
            else:
                herb_lines.append(line)
            continue

        # -------------------------
        # 医生识别
        # -------------------------
        doc = extract_doctor(line)
        if doc:
            data["doctor"] = doc

    # -------------------------
    # 方药解析
    # -------------------------
    data["herbs"] = [h for h in (parse_herb_line(x) for x in herb_lines) if h]

    if data["herbs"] and not data["prescription"]:
        data["prescription"] = "\n".join([f"{h['name']} {h['dose']}" for h in data["herbs"]])

    return data
# -------------------------------------------------------------
# 主入口：解析整个 Word 文件（多次就诊）
# -------------------------------------------------------------
def parse_word_case_multi(file_path: str):
    """
    解析 Word → 返回一个列表（多次就诊）
    每条结构都是 parse_case_one 的输出。
    """
    # 文本行
    lines = read_word_paragraphs(file_path)

    # 清除垃圾行
    lines = [l for l in lines if not is_garbage_line(l)]

    file_name = os.path.basename(file_path)
    sessions = split_by_dates(lines)

    cases = []
    for s in sessions:
        case = parse_case_one(s["date"], s["lines"], file_name)
        cases.append(case)

    return cases


# -------------------------------------------------------------
# 批量导入文件夹（保留原有 GUI 行为 + 更安全）
# -------------------------------------------------------------
def import_cases_from_folder(folder):
    ok = 0
    fail = 0

    for root, dirs, files in os.walk(folder):
        for fn in files:
            if not fn.lower().endswith((".docx", ".doc")):
                continue

            fpath = os.path.join(root, fn)

            try:
                case_list = parse_word_case_multi(fpath)

                for c in case_list:
                    db.save_prescription(c)
                    ok += 1

                print(f"✔ {fn} → {len(case_list)} 条记录导入成功")

            except Exception as e:
                fail += 1
                print(f"❌ {fn} 解析失败：{e}")
                traceback.print_exc()

    print(f"\n📊 批量导入完成：成功 {ok} 条、失败 {fail} 条。")


# -------------------------------------------------------------
# 旧接口兼容（GUI 在单个导入时会用到）
# -------------------------------------------------------------
def parse_word_case(file_path: str):
    """
    返回 Word 内的第一条就诊记录
    兼容旧版 GUI 逻辑（PrintTab.load_docx 使用）
    """
    cases = parse_word_case_multi(file_path)
    return cases[0] if cases else {}