# -*- coding: utf-8 -*-
"""
处方编辑器 - 按照标准处方格式重新设计
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QSizePolicy, QPushButton, QFrame, QFileDialog, QDialog,
    QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QPixmap
from typing import Union
import datetime
import os
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
        self.jian_method.addItems(["自煎", "院煎", "膏方"])
        self.dosage_form = QComboBox()
        self.dosage_form.addItems(["颗粒剂", "饮片"])
        self.dosage_form.currentTextChanged.connect(self._on_dosage_form_changed)
        self.date_edit = QLineEdit(QDate.currentDate().toString("yyyy-MM-dd"))
        row1.addWidget(QLabel("煎药方式："))
        row1.addWidget(self.jian_method)
        row1.addWidget(QLabel("剂型："))
        row1.addWidget(self.dosage_form)
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

        self.past_history_edit = QLineEdit()
        diag_layout.addLayout(make_row("既往史：", self.past_history_edit))

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

        # ======== 二点五、辅助检查（可折叠） ========
        self.exam_box = QGroupBox("辅助检查")
        exam_outer = QVBoxLayout(self.exam_box)
        exam_outer.setContentsMargins(6, 4, 6, 4)

        # 标题栏：展开/收起按钮
        exam_header = QHBoxLayout()
        self.exam_toggle_btn = QPushButton("展开 ▼")
        self.exam_toggle_btn.setFixedWidth(80)
        self.exam_toggle_btn.setStyleSheet("QPushButton { text-align: left; border: none; padding: 2px 6px; }")
        self.exam_toggle_btn.clicked.connect(self._toggle_exam)
        exam_header.addWidget(self.exam_toggle_btn)
        exam_header.addStretch()
        exam_outer.addLayout(exam_header)

        # 检查列表容器（初始隐藏）
        self.exam_content = QFrame()
        self.exam_content.setVisible(False)
        exam_content_layout = QVBoxLayout(self.exam_content)
        exam_content_layout.setContentsMargins(0, 0, 0, 0)

        self.exam_entries = []  # list of dicts: {type_combo, date_edit, summary_edit, image_path, thumbnail_btn, row_widget}
        self.exam_scroll = QScrollArea()
        self.exam_scroll.setWidgetResizable(True)
        self.exam_scroll.setMaximumHeight(200)
        self.exam_list_widget = QWidget()
        self.exam_list_layout = QVBoxLayout(self.exam_list_widget)
        self.exam_list_layout.setContentsMargins(0, 0, 0, 0)
        self.exam_list_layout.addStretch()
        self.exam_scroll.setWidget(self.exam_list_widget)
        exam_content_layout.addWidget(self.exam_scroll)

        # 添加检查按钮
        exam_btn_row = QHBoxLayout()
        self.add_exam_btn = QPushButton("+ 添加检查项目")
        self.add_exam_btn.clicked.connect(self._add_exam_entry)
        exam_btn_row.addWidget(self.add_exam_btn)
        exam_btn_row.addStretch()
        exam_content_layout.addLayout(exam_btn_row)

        exam_outer.addWidget(self.exam_content)

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
        layout.addWidget(self.exam_box)
        layout.addWidget(herb_box)
        layout.addStretch()

        self._connect_signals()
        self._on_dosage_form_changed("颗粒剂")

    def _connect_signals(self):
        for w in [self.name_edit, self.phone_edit, self.address_edit,
                  self.date_edit, self.jieqi_time_edit,
                  self.complaint_edit, self.history_edit, self.past_history_edit,
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

    def _toggle_exam(self):
        visible = not self.exam_content.isVisible()
        self.exam_content.setVisible(visible)
        self.exam_toggle_btn.setText("收起 ▲" if visible else "展开 ▼")

    def _add_exam_entry(self, exam_data=None):
        exam_data = exam_data or {}
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)

        type_combo = QComboBox()
        type_combo.addItems(["心电图", "血常规", "生化检查", "CT", "超声", "X光", "核磁共振", "其他"])
        type_combo.setCurrentText(exam_data.get("type", "心电图"))
        type_combo.currentTextChanged.connect(self.data_changed.emit)

        date_edit = QLineEdit(exam_data.get("date", ""))
        date_edit.setPlaceholderText("日期")
        date_edit.setMaximumWidth(110)
        date_edit.textChanged.connect(self.data_changed.emit)

        summary_edit = QLineEdit(exam_data.get("summary", ""))
        summary_edit.setPlaceholderText("检查结果概要…")
        summary_edit.textChanged.connect(self.data_changed.emit)

        thumbnail_btn = QPushButton("图片")
        thumbnail_btn.setFixedWidth(50)
        btn_remove = QPushButton("✕")
        btn_remove.setFixedWidth(30)

        image_path = exam_data.get("image_path", "")
        entry = {
            "type_combo": type_combo,
            "date_edit": date_edit,
            "summary_edit": summary_edit,
            "image_path": image_path,
            "thumbnail_btn": thumbnail_btn,
            "btn_remove": btn_remove,
            "row_widget": row_widget,
        }
        self.exam_entries.append(entry)

        # Connect thumbnail button to image viewer
        thumbnail_btn.clicked.connect(lambda checked, e=entry: self._show_exam_image(e))
        btn_remove.clicked.connect(lambda checked, e=entry: self._remove_exam_entry(e))

        row_layout.addWidget(QLabel("类型："))
        row_layout.addWidget(type_combo)
        row_layout.addWidget(QLabel("日期："))
        row_layout.addWidget(date_edit)
        row_layout.addWidget(summary_edit)
        row_layout.addWidget(thumbnail_btn)
        row_layout.addWidget(btn_remove)

        # Insert before the stretch
        idx = self.exam_list_layout.count() - 1
        self.exam_list_layout.insertWidget(idx, row_widget)
        self.data_changed.emit()

    def _remove_exam_entry(self, entry):
        self.exam_list_layout.removeWidget(entry["row_widget"])
        entry["row_widget"].deleteLater()
        self.exam_entries.remove(entry)
        self.data_changed.emit()

    def _show_exam_image(self, entry):
        current_path = entry.get("image_path", "")
        file, _ = QFileDialog.getOpenFileName(
            self, "选择检查图片", current_path or "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        )
        if not file:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("辅助检查图片")
        dlg.setMinimumSize(500, 400)
        layout = QVBoxLayout(dlg)

        scroll = QScrollArea()
        pixmap = QPixmap(file)
        if pixmap.isNull():
            QMessageBox.warning(self, "错误", "无法加载图片")
            return
        img_label = QLabel()
        max_w = 700
        if pixmap.width() > max_w:
            pixmap = pixmap.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
        img_label.setPixmap(pixmap)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(img_label)
        layout.addWidget(scroll)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)

        entry["image_path"] = file
        dlg.exec()

    def _on_dosage_form_changed(self, form_text):
        if form_text == "颗粒剂":
            self.jian_method.clear()
            self.jian_method.addItem("免煎")
        else:
            self.jian_method.clear()
            self.jian_method.addItems(["自煎", "院煎", "膏方"])
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
            "dosage_form": self.dosage_form.currentText(),
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
            "past_history": self.past_history_edit.text(),
            "tongue": self.tongue_edit.text(),
            "pulse": self.pulse_edit.text(),
            "zhenghou": self.zhenghou_edit.text(),
            "zhongyi_diagnosis": self.zhongyi_diagnosis.text(),
            "zhongyi_bingji": self.zhongyi_bingji.text(),
            "zhengxing": self.zhengxing_edit.text(),
            "zhifa": self.zhifa_edit.text(),
            "xiyi_diagnosis": self.xiyi_diagnosis.text(),
            "herbs": herbs,
            "examinations": self._get_examinations(),
            "dose_count": self.dose_count.text(),
            "usage": self.usage_edit.text(),
        }

    def _clear_exam_entries(self):
        for entry in list(self.exam_entries):
            self.exam_list_layout.removeWidget(entry["row_widget"])
            entry["row_widget"].deleteLater()
        self.exam_entries.clear()

    def _get_examinations(self):
        result = []
        for entry in self.exam_entries:
            result.append({
                "type": entry["type_combo"].currentText(),
                "date": entry["date_edit"].text(),
                "summary": entry["summary_edit"].text(),
                "image_path": entry.get("image_path", ""),
            })
        return result

    def load_from_dict(self, data: dict):
        self.herb_table.blockSignals(True)
        self.dosage_form.blockSignals(True)
        self.dosage_form.setCurrentText(data.get("dosage_form", "颗粒剂"))
        self.dosage_form.blockSignals(False)
        self._on_dosage_form_changed(data.get("dosage_form", "颗粒剂"))
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
        self.past_history_edit.setText(data.get("past_history", ""))
        self.tongue_edit.setText(data.get("tongue", ""))
        self.pulse_edit.setText(data.get("pulse", ""))
        self.zhenghou_edit.setText(data.get("zhenghou", ""))
        self.zhongyi_diagnosis.setText(data.get("zhongyi_diagnosis", ""))
        self.zhongyi_bingji.setText(data.get("zhongyi_bingji", ""))
        self.zhengxing_edit.setText(data.get("zhengxing", ""))
        self.zhifa_edit.setText(data.get("zhifa", ""))
        self.xiyi_diagnosis.setText(data.get("xiyi_diagnosis", ""))
        # Load examinations
        self._clear_exam_entries()
        for exam in data.get("examinations", []):
            self._add_exam_entry(exam)
        self.dose_count.setText(data.get("dose_count", "7 剂"))
        self.usage_edit.setText(data.get("usage", "每日一剂，水煎服"))
        herbs = data.get("herbs", [])
        for r, row in enumerate(herbs[:12]):
            self.herb_table.setItem(r, 0, QTableWidgetItem(row.get("name", "")))
            self.herb_table.setItem(r, 1, QTableWidgetItem(row.get("dose", "")))
            self.herb_table.setItem(r, 2, QTableWidgetItem(row.get("remark", "")))
        self.herb_table.blockSignals(False)
        self.data_changed.emit()
