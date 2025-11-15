# -*- coding: utf-8 -*-
"""
李玉贤名医工作室 — 处方录入编辑器（PyQt6 专用版本）
完全对应《AAAF.doc》模板结构。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton
)
from PyQt6.QtCore import Qt, QDate
import json
import math
import datetime


# ===================== 节气计算辅助 =====================
SOLAR_TERMS = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
    "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
    "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"
]

def get_solar_term(date: QDate | datetime.date) -> str:
    """简单节气计算：根据月份近似返回节气"""
    if isinstance(date, QDate):
        month, day = date.month(), date.day()
    else:
        month, day = date.month, date.day
    idx = (month - 1) * 2
    if day >= 15:
        idx += 1
    idx = min(idx, len(SOLAR_TERMS) - 1)
    return SOLAR_TERMS[idx]


# ===================== 主界面 =====================
class PrescriptionEditor(QWidget):
    """中医处方编辑器（PyQt6版本）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # ======== 头部信息区 ========
        header_box = QGroupBox("处方抬头信息")
        header_layout = QFormLayout(header_box)

        self.jian_method = QComboBox()
        self.jian_method.addItems(["自煎", "院煎"])

        today = QDate.currentDate()
        self.date_edit = QLineEdit(today.toString("yyyy-MM-dd"))

        self.jieqi_edit = QLineEdit(get_solar_term(today))
        self.yunqi_edit = QLineEdit("五运六气自动生成")

        header_layout.addRow("煎药方式：", self.jian_method)
        header_layout.addRow("开具日期：", self.date_edit)
        header_layout.addRow("节气：", self.jieqi_edit)
        header_layout.addRow("五运六气：", self.yunqi_edit)

        # ======== 患者基本信息 ========
        info_box = QGroupBox("患者基本信息")
        info_layout = QFormLayout(info_box)

        self.name_edit = QLineEdit()
        self.gender_edit = QComboBox()
        self.gender_edit.addItems(["男", "女"])
        self.age_edit = QSpinBox()
        self.age_edit.setRange(0, 120)
        self.phone_edit = QLineEdit()
        self.address_edit = QLineEdit()

        info_layout.addRow("姓名：", self.name_edit)
        info_layout.addRow("性别：", self.gender_edit)
        info_layout.addRow("年龄：", self.age_edit)
        info_layout.addRow("电话：", self.phone_edit)
        info_layout.addRow("地址：", self.address_edit)

        # ======== 诊断与辨证区 ========
        diag_box = QGroupBox("诊断与辨证信息")
        diag_layout = QFormLayout(diag_box)

        self.diagnosis_clinic = QLineEdit()
        self.zhengxing = QLineEdit()
        self.zhilaw = QLineEdit()
        self.diagnosis_western = QLineEdit()
        self.complaint = QTextEdit()
        self.zhenghou = QTextEdit()

        diag_layout.addRow("临床诊断：", self.diagnosis_clinic)
        diag_layout.addRow("证型：", self.zhengxing)
        diag_layout.addRow("治法：", self.zhilaw)
        diag_layout.addRow("西医诊断：", self.diagnosis_western)
        diag_layout.addRow("主诉：", self.complaint)
        diag_layout.addRow("症状、舌脉辨证：", self.zhenghou)

        # ======== 中药处方表格 ========
        herb_box = QGroupBox("中药处方（每行三味）")
        vbox = QVBoxLayout(herb_box)
        self.herb_table = QTableWidget(9, 3)
        self.herb_table.setHorizontalHeaderLabels(["药名", "剂量(g)", "备注（先煎/后下/烊化等）"])
        self.herb_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        vbox.addWidget(self.herb_table)

        self.btn_add_row = QPushButton("＋ 添加药物行")
        self.btn_add_row.clicked.connect(lambda: self.herb_table.insertRow(self.herb_table.rowCount()))
        vbox.addWidget(self.btn_add_row, alignment=Qt.AlignmentFlag.AlignRight)

        # ======== 用法与签名区 ========
        usage_box = QGroupBox("用法与医师签名")
        usage_layout = QFormLayout(usage_box)

        self.usage_edit = QTextEdit()
        self.dose_edit = QLineEdit("7 剂")
        self.doctor_edit = QLineEdit("李玉贤")
        self.sign_date = QLineEdit(today.toString("yyyy-MM-dd"))

        usage_layout.addRow("用法说明：", self.usage_edit)
        usage_layout.addRow("剂数：", self.dose_edit)
        usage_layout.addRow("医师签名：", self.doctor_edit)
        usage_layout.addRow("日期：", self.sign_date)

        # ======== 整体布局 ========
        layout.addWidget(header_box)
        layout.addWidget(info_box)
        layout.addWidget(diag_box)
        layout.addWidget(herb_box)
        layout.addWidget(usage_box)
        layout.addStretch()

    # =====================================================
    # 数据接口
    # =====================================================
    def to_dict(self):
        """导出表单为 dict"""
        herbs = []
        for r in range(self.herb_table.rowCount()):
            row_data = {}
            for c, key in enumerate(["name", "dose", "remark"]):
                item = self.herb_table.item(r, c)
                row_data[key] = item.text() if item else ""
            if any(row_data.values()):
                herbs.append(row_data)

        return {
            "jian_method": self.jian_method.currentText(),
            "date": self.date_edit.text(),
            "jieqi": self.jieqi_edit.text(),
            "yunqi": self.yunqi_edit.text(),
            "patient_name": self.name_edit.text(),
            "gender": self.gender_edit.currentText(),
            "age": self.age_edit.value(),
            "phone": self.phone_edit.text(),
            "address": self.address_edit.text(),
            "diagnosis_clinic": self.diagnosis_clinic.text(),
            "zhengxing": self.zhengxing.text(),
            "zhilaw": self.zhilaw.text(),
            "diagnosis_western": self.diagnosis_western.text(),
            "complaint": self.complaint.toPlainText(),
            "zhenghou": self.zhenghou.toPlainText(),
            "herbs": herbs,
            "usage": self.usage_edit.toPlainText(),
            "dose_count": self.dose_edit.text(),
            "doctor": self.doctor_edit.text(),
            "sign_date": self.sign_date.text(),
        }

    def load_from_dict(self, data: dict):
        """从 dict 填充表单"""
        self.name_edit.setText(data.get("patient_name", ""))
        self.gender_edit.setCurrentText(data.get("gender", "男"))
        age_raw = str(data.get("age", "")).strip()
        try:
            age_val = int(age_raw) if age_raw.isdigit() else 0
        except:
            age_val = 0
        self.age_edit.setValue(age_val)
        self.phone_edit.setText(data.get("phone", ""))
        self.address_edit.setText(data.get("address", ""))
        self.diagnosis_clinic.setText(data.get("diagnosis_clinic", ""))
        self.zhengxing.setText(data.get("zhengxing", ""))
        self.zhilaw.setText(data.get("zhilaw", ""))
        self.diagnosis_western.setText(data.get("diagnosis_western", ""))
        self.complaint.setPlainText(data.get("complaint", ""))
        self.zhenghou.setPlainText(data.get("zhenghou", ""))

        herbs = data.get("herbs", [])
        self.herb_table.setRowCount(len(herbs) or 9)
        for r, row in enumerate(herbs):
            for c, key in enumerate(["name", "dose", "remark"]):
                self.herb_table.setItem(r, c, QTableWidgetItem(row.get(key, "")))

        self.usage_edit.setPlainText(data.get("usage", ""))
        self.dose_edit.setText(data.get("dose_count", ""))
        self.doctor_edit.setText(data.get("doctor", "李玉贤"))
        self.sign_date.setText(data.get("sign_date", QDate.currentDate().toString("yyyy-MM-dd")))
