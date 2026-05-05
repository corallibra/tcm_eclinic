# -*- coding: utf-8 -*-
"""
处方编辑器 - 按照标准处方格式重新设计
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, QDate
from typing import Union
import datetime

# ===================== 节气计算辅助 =====================
SOLAR_TERMS = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
    "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
    "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"
]

def get_solar_term(date: Union[QDate, datetime.date]) -> str:
    """简单节气计算"""
    if isinstance(date, QDate):
        month, day = date.month(), date.day()
    else:
        month, day = date.month, date.day
    idx = (month - 1) * 2
    if day >= 15:
        idx += 1
    idx = min(idx, len(SOLAR_TERMS) - 1)
    return SOLAR_TERMS[idx]


class PrescriptionEditor(QWidget):
    """中医处方编辑器（按照标准处方格式）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # ======== 一、处方基本信息 ========
        basic_box = QGroupBox("处方基本信息")
        basic_layout = QFormLayout(basic_box)

        # 第一行：煎药方式；日期
        row1 = QHBoxLayout()
        self.jian_method = QComboBox()
        self.jian_method.addItems(["自煎", "院煎"])
        self.date_edit = QLineEdit(QDate.currentDate().toString("yyyy-MM-dd"))
        row1.addWidget(QLabel("煎药方式："))
        row1.addWidget(self.jian_method)
        row1.addWidget(QLabel("日期："))
        row1.addWidget(self.date_edit)
        basic_layout.addRow(row1)

        # 第二行：姓名；性别；年龄
        row2 = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.gender_edit = QComboBox()
        self.gender_edit.addItems(["男", "女"])
        self.age_edit = QSpinBox()
        self.age_edit.setRange(0, 120)
        row2.addWidget(QLabel("姓名："))
        row2.addWidget(self.name_edit)
        row2.addWidget(QLabel("性别："))
        row2.addWidget(self.gender_edit)
        row2.addWidget(QLabel("年龄："))
        row2.addWidget(self.age_edit)
        basic_layout.addRow(row2)

        # 第三行：电话；地址
        row3 = QHBoxLayout()
        self.phone_edit = QLineEdit()
        self.address_edit = QLineEdit()
        row3.addWidget(QLabel("电话："))
        row3.addWidget(self.phone_edit)
        row3.addWidget(QLabel("地址："))
        row3.addWidget(self.address_edit)
        basic_layout.addRow(row3)

        # 第四行：节气；主运；客运；节点五运六气
        row4 = QHBoxLayout()
        self.jieqi_edit = QLineEdit(get_solar_term(QDate.currentDate()))
        self.zhuyun_edit = QLineEdit()
        self.keyun_edit = QLineEdit()
        self.wuyun_edit = QLineEdit()
        row4.addWidget(QLabel("节气："))
        row4.addWidget(self.jieqi_edit)
        row4.addWidget(QLabel("主运："))
        row4.addWidget(self.zhuyun_edit)
        row4.addWidget(QLabel("客运："))
        row4.addWidget(self.keyun_edit)
        row4.addWidget(QLabel("五运："))
        row4.addWidget(self.wuyun_edit)
        basic_layout.addRow(row4)

        # ======== 二、诊断与辨证信息 ========
        diag_box = QGroupBox("诊断与辨证信息")
        diag_layout = QVBoxLayout(diag_box)

        # 主诉
        complaint_layout = QHBoxLayout()
        complaint_layout.addWidget(QLabel("主诉："))
        self.complaint_edit = QLineEdit()
        complaint_layout.addWidget(self.complaint_edit)
        complaint_layout.addStretch()
        diag_layout.addLayout(complaint_layout)

        # 现病史
        history_layout = QHBoxLayout()
        history_layout.addWidget(QLabel("现病史："))
        self.history_edit = QLineEdit()
        history_layout.addWidget(self.history_edit)
        history_layout.addStretch()
        diag_layout.addLayout(history_layout)

        # 舌像；脉象
        tp_layout = QHBoxLayout()
        tp_layout.addWidget(QLabel("舌像："))
        self.tongue_edit = QLineEdit()
        tp_layout.addWidget(self.tongue_edit)
        tp_layout.addWidget(QLabel("脉象："))
        self.pulse_edit = QLineEdit()
        tp_layout.addWidget(self.pulse_edit)
        tp_layout.addStretch()
        diag_layout.addLayout(tp_layout)

        # 辨证
        zhenghou_layout = QHBoxLayout()
        zhenghou_layout.addWidget(QLabel("辨证："))
        self.zhenghou_edit = QLineEdit()
        zhenghou_layout.addWidget(self.zhenghou_edit)
        zhenghou_layout.addStretch()
        diag_layout.addLayout(zhenghou_layout)

        # 中医诊断；中医病机
        zy_layout = QHBoxLayout()
        zy_layout.addWidget(QLabel("中医诊断："))
        self.zhongyi_diagnosis = QLineEdit()
        zy_layout.addWidget(self.zhongyi_diagnosis)
        zy_layout.addWidget(QLabel("中医病机："))
        self.zhongyi_bingji = QLineEdit()
        zy_layout.addWidget(self.zhongyi_bingji)
        zy_layout.addStretch()
        diag_layout.addLayout(zy_layout)

        # 中医证型；中医治法
        zx_layout = QHBoxLayout()
        zx_layout.addWidget(QLabel("中医证型："))
        self.zhengxing_edit = QLineEdit()
        zx_layout.addWidget(self.zhengxing_edit)
        zx_layout.addWidget(QLabel("中医治法："))
        self.zhifa_edit = QLineEdit()
        zx_layout.addWidget(self.zhifa_edit)
        zx_layout.addStretch()
        diag_layout.addLayout(zx_layout)

        # 西医诊断
        xiyi_layout = QHBoxLayout()
        xiyi_layout.addWidget(QLabel("西医诊断："))
        self.xiyi_diagnosis = QLineEdit()
        xiyi_layout.addWidget(self.xiyi_diagnosis)
        xiyi_layout.addStretch()
        diag_layout.addLayout(xiyi_layout)

        # ======== 三、中药处方 ========
        herb_box = QGroupBox("中药处方")
        herb_layout = QVBoxLayout(herb_box)

        self.herb_table = QTableWidget(12, 3)
        self.herb_table.setHorizontalHeaderLabels(["药名", "剂量(g)", "备注"])
        self.herb_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        herb_layout.addWidget(self.herb_table)

        # 用法
        usage_layout = QHBoxLayout()
        self.dose_count = QLineEdit("7 剂")
        self.usage_edit = QLineEdit("每日一剂，水煎服")
        usage_layout.addWidget(QLabel("剂数："))
        usage_layout.addWidget(self.dose_count)
        usage_layout.addWidget(QLabel("用法："))
        usage_layout.addWidget(self.usage_edit)
        herb_layout.addLayout(usage_layout)

        # 医师
        doctor_layout = QHBoxLayout()
        self.doctor_edit = QLineEdit()
        doctor_layout.addWidget(QLabel("医师："))
        doctor_layout.addWidget(self.doctor_edit)
        doctor_layout.addStretch()
        herb_layout.addLayout(doctor_layout)

        # ======== 组装布局 ========
        layout.addWidget(basic_box)
        layout.addWidget(diag_box)
        layout.addWidget(herb_box)
        layout.addStretch()

    # =====================================================
    # 数据接口
    # =====================================================
    def to_dict(self):
        """导出表单为 dict"""
        herbs = []
        for r in range(self.herb_table.rowCount()):
            row_data = {
                "name": self.herb_table.item(r, 0).text() if self.herb_table.item(r, 0) else "",
                "dose": self.herb_table.item(r, 1).text() if self.herb_table.item(r, 1) else "",
                "remark": self.herb_table.item(r, 2).text() if self.herb_table.item(r, 2) else "",
            }
            if row_data["name"]:
                herbs.append(row_data)

        return {
            "jian_method": self.jian_method.currentText(),
            "date": self.date_edit.text(),
            "patient_name": self.name_edit.text(),
            "gender": self.gender_edit.currentText(),
            "age": self.age_edit.value(),
            "phone": self.phone_edit.text(),
            "address": self.address_edit.text(),
            "jieqi": self.jieqi_edit.text(),
            "zhuyun": self.zhuyun_edit.text(),
            "keyun": self.keyun_edit.text(),
            "wuyun": self.wuyun_edit.text(),
            "doctor": self.doctor_edit.text(),
            "complaint": self.complaint_edit.text(),
            "history": self.history_edit.text(),
            "tongue": self.tongue_edit.text(),
            "pulse": self.pulse_edit.text(),
            "zhenghou": self.zhenghou_edit.text(),
            "zhongyi_diagnosis": self.zhongyi_diagnosis.text(),
            "zhongyi_bingji": self.zhongyi_bingji.text(),
            "zhengxing": self.zhengxing_edit.text(),
            "zhifa": self.zhifa_edit.text(),
            "xiyi_diagnosis": self.xiyi_diagnosis.text(),
            "herbs": herbs,
            "dose_count": self.dose_count.text(),
            "usage": self.usage_edit.text(),
        }

    def load_from_dict(self, data: dict):
        """从 dict 填充表单"""
        self.jian_method.setCurrentText(data.get("jian_method", "自煎"))
        self.date_edit.setText(data.get("date", QDate.currentDate().toString("yyyy-MM-dd")))
        self.name_edit.setText(data.get("patient_name", ""))
        self.gender_edit.setCurrentText(data.get("gender", "男"))
        
        age_val = data.get("age", 0)
        if isinstance(age_val, str):
            age_val = int(age_val) if age_val.isdigit() else 0
        self.age_edit.setValue(age_val)
        
        self.phone_edit.setText(data.get("phone", ""))
        self.address_edit.setText(data.get("address", ""))
        self.jieqi_edit.setText(data.get("jieqi", ""))
        self.zhuyun_edit.setText(data.get("zhuyun", ""))
        self.keyun_edit.setText(data.get("keyun", ""))
        self.wuyun_edit.setText(data.get("wuyun", ""))
        self.doctor_edit.setText(data.get("doctor", ""))
        self.complaint_edit.setText(data.get("complaint", ""))
        self.history_edit.setText(data.get("history", ""))
        self.tongue_edit.setText(data.get("tongue", ""))
        self.pulse_edit.setText(data.get("pulse", ""))
        self.zhenghou_edit.setText(data.get("zhenghou", ""))
        self.zhongyi_diagnosis.setText(data.get("zhongyi_diagnosis", ""))
        self.zhongyi_bingji.setText(data.get("zhongyi_bingji", ""))
        self.zhengxing_edit.setText(data.get("zhengxing", ""))
        self.zhifa_edit.setText(data.get("zhifa", ""))
        self.xiyi_diagnosis.setText(data.get("xiyi_diagnosis", ""))
        self.dose_count.setText(data.get("dose_count", "7 剂"))
        self.usage_edit.setText(data.get("usage", "每日一剂，水煎服"))

        # 加载药材
        herbs = data.get("herbs", [])
        for r, row in enumerate(herbs[:12]):
            self.herb_table.setItem(r, 0, QTableWidgetItem(row.get("name", "")))
            self.herb_table.setItem(r, 1, QTableWidgetItem(row.get("dose", "")))
            self.herb_table.setItem(r, 2, QTableWidgetItem(row.get("remark", "")))
