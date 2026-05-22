# -*- coding: utf-8 -*-
"""
处方编辑器 - 按照标准处方格式重新设计
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from typing import Union
import datetime
from lunar_python import Lunar, Solar

SOLAR_TERMS = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
    "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
    "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"
]

def get_solar_term(date: Union[QDate, datetime.date]) -> str:
    if isinstance(date, QDate):
        month, day = date.month(), date.day()
    else:
        month, day = date.month, date.day
    idx = (month - 1) * 2
    if day >= 15:
        idx += 1
    idx = min(idx, len(SOLAR_TERMS) - 1)
    return SOLAR_TERMS[idx]

def solar_to_lunar(date_str: str) -> str:
    try:
        year, month, day = map(int, date_str.split("-"))
        solar = Solar.fromYmd(year, month, day)
        lunar = solar.getLunar()
        return f"{lunar.getYearInGanZhi()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
    except:
        return ""

def get_wuyunliuqi(date_str: str) -> dict:
    try:
        year, month, day = map(int, date_str.split("-"))
        solar = Solar.fromYmd(year, month, day)
        lunar = solar.getLunar()
        year_zhi = lunar.getYearZhi()
        sitian_zaiquan = {
            "子": ("少阴君火", "阳明燥金"),
            "丑": ("太阴湿土", "太阳寒水"),
            "寅": ("少阳相火", "厥阴风木"),
            "卯": ("阳明燥金", "少阴君火"),
            "辰": ("太阳寒水", "太阴湿土"),
            "巳": ("厥阴风木", "少阳相火"),
            "午": ("少阴君火", "阳明燥金"),
            "未": ("太阴湿土", "太阳寒水"),
            "申": ("少阳相火", "厥阴风木"),
            "酉": ("阳明燥金", "少阴君火"),
            "戌": ("太阳寒水", "太阴湿土"),
            "亥": ("厥阴风木", "少阳相火"),
        }
        sitian, zaiquan = sitian_zaiquan.get(year_zhi, ("", ""))
        year_gan = lunar.getYearGan()
        zhuyun_list = ["木运", "木运", "火运", "火运", "土运", "土运", "金运", "金运", "水运", "水运"]
        gan_index = "甲乙丙丁戊己庚辛壬癸".index(year_gan)
        zhuyun = zhuyun_list[gan_index]
        zhuqi = "厥阴风木"
        zhi_index = "子丑寅卯辰巳午未申酉戌亥".index(year_zhi)
        keqi_list = ["太阳寒水", "阳明燥金", "少阳相火", "太阴湿土", "厥阴风木", "少阴君火"]
        keqi = keqi_list[zhi_index % 6]
        return {
            "sitian": sitian,
            "keqi": keqi,
            "zhuyun": zhuyun,
            "zhuqi": zhuqi,
            "zaiquan": zaiquan
        }
    except Exception as e:
        print(f"五运六气计算错误: {e}")
        return {"sitian": "", "keqi": "", "zhuyun": "", "zhuqi": "", "zaiquan": ""}


class PrescriptionEditor(QWidget):
    """中医处方编辑器"""
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # ======== 一、处方基本信息 ========
        basic_box = QGroupBox("处方基本信息")
        basic_layout = QFormLayout(basic_box)
        basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        row1 = QHBoxLayout()
        self.jian_method = QComboBox()
        self.jian_method.addItems(["自煎", "院煎"])
        self.date_edit = QLineEdit(QDate.currentDate().toString("yyyy-MM-dd"))
        row1.addWidget(QLabel("煎药方式："))
        row1.addWidget(self.jian_method)
        row1.addWidget(QLabel("日期："))
        row1.addWidget(self.date_edit)
        basic_layout.addRow(row1)

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

        row3 = QHBoxLayout()
        self.phone_edit = QLineEdit()
        self.address_edit = QLineEdit()
        row3.addWidget(QLabel("电话："))
        row3.addWidget(self.phone_edit)
        row3.addWidget(QLabel("地址："))
        row3.addWidget(self.address_edit)
        basic_layout.addRow(row3)

        row4 = QHBoxLayout()
        self.lunar_edit = QLineEdit(solar_to_lunar(QDate.currentDate().toString("yyyy-MM-dd")))
        self.lunar_edit.setReadOnly(True)
        self.jieqi_edit = QLineEdit(get_solar_term(QDate.currentDate()))
        self.jieqi_edit.setReadOnly(True)
        self.jieqi_time_edit = QLineEdit()
        self.jieqi_time_edit.setPlaceholderText("交节时间")
        row4.addWidget(QLabel("农历："))
        row4.addWidget(self.lunar_edit)
        row4.addWidget(QLabel("节气："))
        row4.addWidget(self.jieqi_edit)
        row4.addWidget(QLabel("交节："))
        row4.addWidget(self.jieqi_time_edit)
        basic_layout.addRow(row4)

        row5 = QHBoxLayout()
        self.sitian_edit = QLineEdit()
        self.sitian_edit.setReadOnly(True)
        self.sitian_edit.setPlaceholderText("司天")
        self.keqi_edit = QLineEdit()
        self.keqi_edit.setReadOnly(True)
        self.keqi_edit.setPlaceholderText("客气")
        self.zhuyun_edit = QLineEdit()
        self.zhuyun_edit.setReadOnly(True)
        self.zhuyun_edit.setPlaceholderText("主运")
        self.zhuqi_edit = QLineEdit()
        self.zhuqi_edit.setReadOnly(True)
        self.zhuqi_edit.setPlaceholderText("主气")
        self.zaiquan_edit = QLineEdit()
        self.zaiquan_edit.setReadOnly(True)
        self.zaiquan_edit.setPlaceholderText("在泉")
        row5.addWidget(QLabel("司天："))
        row5.addWidget(self.sitian_edit)
        row5.addWidget(QLabel("客气："))
        row5.addWidget(self.keqi_edit)
        row5.addWidget(QLabel("主运："))
        row5.addWidget(self.zhuyun_edit)
        row5.addWidget(QLabel("主气："))
        row5.addWidget(self.zhuqi_edit)
        row5.addWidget(QLabel("在泉："))
        row5.addWidget(self.zaiquan_edit)
        basic_layout.addRow(row5)

        self.date_edit.textChanged.connect(self.on_date_changed)
        self.on_date_changed(QDate.currentDate().toString("yyyy-MM-dd"))

        # ======== 二、诊断与辨证信息 ========
        diag_box = QGroupBox("诊断与辨证信息")
        diag_layout = QVBoxLayout(diag_box)

        # 所有诊断字段使用固定标签宽度对齐
        LABEL_W = 80

        def make_row(label_text, edit_widget, stretch=True):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(LABEL_W)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(lbl)
            row.addWidget(edit_widget)
            if stretch:
                row.addStretch()
            return row

        self.complaint_edit = QLineEdit()
        diag_layout.addLayout(make_row("主诉：", self.complaint_edit))

        self.history_edit = QLineEdit()
        diag_layout.addLayout(make_row("现病史：", self.history_edit))

        tp_row = QHBoxLayout()
        lbl1 = QLabel("舌像：")
        lbl1.setFixedWidth(LABEL_W)
        lbl1.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tongue_edit = QLineEdit()
        lbl2 = QLabel("脉象：")
        lbl2.setFixedWidth(LABEL_W)
        lbl2.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.pulse_edit = QLineEdit()
        tp_row.addWidget(lbl1)
        tp_row.addWidget(self.tongue_edit)
        tp_row.addWidget(lbl2)
        tp_row.addWidget(self.pulse_edit)
        tp_row.addStretch()
        diag_layout.addLayout(tp_row)

        self.zhenghou_edit = QLineEdit()
        diag_layout.addLayout(make_row("辨证：", self.zhenghou_edit))

        zy_row = QHBoxLayout()
        lbl3 = QLabel("中医诊断：")
        lbl3.setFixedWidth(LABEL_W)
        lbl3.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.zhongyi_diagnosis = QLineEdit()
        lbl4 = QLabel("中医病机：")
        lbl4.setFixedWidth(LABEL_W)
        lbl4.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.zhongyi_bingji = QLineEdit()
        zy_row.addWidget(lbl3)
        zy_row.addWidget(self.zhongyi_diagnosis)
        zy_row.addWidget(lbl4)
        zy_row.addWidget(self.zhongyi_bingji)
        zy_row.addStretch()
        diag_layout.addLayout(zy_row)

        zx_row = QHBoxLayout()
        lbl5 = QLabel("中医证型：")
        lbl5.setFixedWidth(LABEL_W)
        lbl5.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.zhengxing_edit = QLineEdit()
        lbl6 = QLabel("中医治法：")
        lbl6.setFixedWidth(LABEL_W)
        lbl6.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.zhifa_edit = QLineEdit()
        zx_row.addWidget(lbl5)
        zx_row.addWidget(self.zhengxing_edit)
        zx_row.addWidget(lbl6)
        zx_row.addWidget(self.zhifa_edit)
        zx_row.addStretch()
        diag_layout.addLayout(zx_row)

        self.xiyi_diagnosis = QLineEdit()
        diag_layout.addLayout(make_row("西医诊断：", self.xiyi_diagnosis))

        # ======== 三、中药处方 ========
        herb_box = QGroupBox("中药处方")
        herb_layout = QVBoxLayout(herb_box)

        self.herb_table = QTableWidget(12, 3)
        self.herb_table.setHorizontalHeaderLabels(["药名", "剂量(g)", "备注"])
        self.herb_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        herb_layout.addWidget(self.herb_table)

        usage_layout = QHBoxLayout()
        self.dose_count = QLineEdit("7 剂")
        self.usage_edit = QLineEdit("每日一剂，水煎服")
        usage_layout.addWidget(QLabel("剂数："))
        usage_layout.addWidget(self.dose_count)
        usage_layout.addWidget(QLabel("用法："))
        usage_layout.addWidget(self.usage_edit)
        herb_layout.addLayout(usage_layout)

        doctor_layout = QHBoxLayout()
        self.doctor_edit = QLineEdit()
        doctor_layout.addWidget(QLabel("医师："))
        doctor_layout.addWidget(self.doctor_edit)
        doctor_layout.addStretch()
        herb_layout.addLayout(doctor_layout)

        layout.addWidget(basic_box)
        layout.addWidget(diag_box)
        layout.addWidget(herb_box)
        layout.addStretch()

        self._connect_signals()

    def _connect_signals(self):
        for w in [self.name_edit, self.phone_edit, self.address_edit,
                  self.date_edit, self.jieqi_time_edit,
                  self.complaint_edit, self.history_edit,
                  self.tongue_edit, self.pulse_edit,
                  self.zhenghou_edit, self.zhongyi_diagnosis,
                  self.zhongyi_bingji, self.zhengxing_edit,
                  self.zhifa_edit, self.xiyi_diagnosis,
                  self.dose_count, self.usage_edit, self.doctor_edit]:
            w.textChanged.connect(self.data_changed.emit)

        self.jian_method.currentTextChanged.connect(self.data_changed.emit)
        self.gender_edit.currentTextChanged.connect(self.data_changed.emit)
        self.age_edit.valueChanged.connect(self.data_changed.emit)

        self.herb_table.cellChanged.connect(self.data_changed.emit)

    def on_date_changed(self, date_str):
        lunar_str = solar_to_lunar(date_str)
        self.lunar_edit.setText(lunar_str)
        try:
            year, month, day = map(int, date_str.split("-"))
            qdate = QDate(year, month, day)
            self.jieqi_edit.setText(get_solar_term(qdate))
        except:
            pass
        wuyun = get_wuyunliuqi(date_str)
        self.sitian_edit.setText(wuyun.get("sitian", ""))
        self.keqi_edit.setText(wuyun.get("keqi", ""))
        self.zhuyun_edit.setText(wuyun.get("zhuyun", ""))
        self.zhuqi_edit.setText(wuyun.get("zhuqi", ""))
        self.zaiquan_edit.setText(wuyun.get("zaiquan", ""))
        self.data_changed.emit()

    def to_dict(self):
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
            "lunar": self.lunar_edit.text(),
            "patient_name": self.name_edit.text(),
            "gender": self.gender_edit.currentText(),
            "age": self.age_edit.value(),
            "phone": self.phone_edit.text(),
            "address": self.address_edit.text(),
            "jieqi": self.jieqi_edit.text(),
            "jieqi_time": self.jieqi_time_edit.text(),
            "sitian": self.sitian_edit.text(),
            "keqi": self.keqi_edit.text(),
            "zhuyun": self.zhuyun_edit.text(),
            "zhuqi": self.zhuqi_edit.text(),
            "zaiquan": self.zaiquan_edit.text(),
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
        self.herb_table.blockSignals(True)
        self.jian_method.setCurrentText(data.get("jian_method", "自煎"))
        self.date_edit.setText(data.get("date", QDate.currentDate().toString("yyyy-MM-dd")))
        if "lunar" in data and data.get("lunar"):
            self.lunar_edit.setText(data.get("lunar"))
        else:
            self.lunar_edit.setText(solar_to_lunar(self.date_edit.text()))
        self.name_edit.setText(data.get("patient_name", ""))
        self.gender_edit.setCurrentText(data.get("gender", "男"))
        age_val = data.get("age", 0)
        if isinstance(age_val, str):
            age_val = int(age_val) if age_val.isdigit() else 0
        self.age_edit.setValue(age_val)
        self.phone_edit.setText(data.get("phone", ""))
        self.address_edit.setText(data.get("address", ""))
        self.jieqi_edit.setText(data.get("jieqi", ""))
        self.jieqi_time_edit.setText(data.get("jieqi_time", ""))
        self.sitian_edit.setText(data.get("sitian", ""))
        self.keqi_edit.setText(data.get("keqi", ""))
        self.zhuyun_edit.setText(data.get("zhuyun", ""))
        self.zhuqi_edit.setText(data.get("zhuqi", ""))
        self.zaiquan_edit.setText(data.get("zaiquan", ""))
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
        herbs = data.get("herbs", [])
        for r, row in enumerate(herbs[:12]):
            self.herb_table.setItem(r, 0, QTableWidgetItem(row.get("name", "")))
            self.herb_table.setItem(r, 1, QTableWidgetItem(row.get("dose", "")))
            self.herb_table.setItem(r, 2, QTableWidgetItem(row.get("remark", "")))
        self.herb_table.blockSignals(False)
        self.data_changed.emit()
