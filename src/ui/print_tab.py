# -*- coding: utf-8 -*-
"""
处方编辑与打印模块 - 带实时预览功能
"""

import os
import traceback
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QGroupBox, QTextEdit, QComboBox,
    QDateEdit, QSpinBox, QDialog, QCheckBox, QFileDialog,
    QMessageBox, QListWidget, QListWidgetItem, QScrollArea,
    QFrame, QFormLayout, QGridLayout, QTextBrowser
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QTimer, QObject, pyqtSlot
from PyQt6.QtGui import QFont, QTextDocument

from config import DATA_DIR, OUTPUT_DIR
from src.ui.prescription_editor import PrescriptionEditor
from src.core.parse_docx import parse_word_case_multi
from src.core import db
from src.printing.pdf_template import generate_prescription_pdf
from src.ui.log_console import LogConsole
from src.core.similarity_engine import find_similar_cases

COMMON_HERBS = [
    "麻黄", "桂枝", "杏仁", "甘草", "生姜", "大枣",
    "柴胡", "黄芩", "半夏", "党参", "白术", "茯苓",
    "当归", "白芍", "川芎", "熟地", "黄芪", "防风",
    "白芷", "细辛", "羌活", "独活", "薄荷", "桑叶",
    "菊花", "金银花", "连翘", "蒲公英", "板蓝根", "黄连",
    "黄芩", "黄柏", "栀子", "大黄", "枳实", "厚朴",
    "陈皮", "半夏", "茯苓", "甘草", "干姜", "高良姜",
    "附子", "肉桂", "吴茱萸", "丁香", "小茴香", "花椒",
    "山楂", "神曲", "麦芽", "鸡内金", "陈皮", "半夏",
    "藿香", "佩兰", "苍术", "厚朴", "砂仁", "豆蔻"
]


class HerbListWidget(QWidget):
    herb_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索药材...")
        self.search_edit.textChanged.connect(self.filter_herbs)
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.filter_herbs)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_btn)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "解表药", "清热药", "泻下药", "祛湿药", "温里药"])
        self.category_combo.currentTextChanged.connect(self.filter_herbs)

        self.herb_list = QListWidget()
        self.herb_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.herb_list.itemDoubleClicked.connect(self.on_herb_double_click)
        self.load_herbs()

        layout.addLayout(search_layout)
        layout.addWidget(self.category_combo)
        layout.addWidget(self.herb_list)

    def load_herbs(self):
        self.herb_list.clear()
        for herb in COMMON_HERBS:
            item = QListWidgetItem(herb)
            self.herb_list.addItem(item)

    def filter_herbs(self):
        keyword = self.search_edit.text().lower()
        for i in range(self.herb_list.count()):
            item = self.herb_list.item(i)
            herb_name = item.text().lower()
            item.setHidden(bool(keyword and keyword not in herb_name))

    def on_herb_double_click(self, item):
        self.herb_selected.emit(item.text())


class PrescriptionPreview(QWidget):
    """实时处方预览组件"""
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title_label = QLabel("处方预览")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #666; padding: 2px;")

        self.browser = QTextBrowser()
        self.browser.setReadOnly(True)
        self.browser.setOpenExternalLinks(False)
        self.browser.setStyleSheet(
            "QTextBrowser { background-color: white; border: 1px solid #ccc; padding: 8px; }"
        )

        layout.addWidget(title_label)
        layout.addWidget(self.browser)

        self.update_preview({})

    def update_preview(self, data):
        def v(key, placeholder=''):
            val = data.get(key, '')
            if val is None:
                val = ''
            val = str(val).strip()
            return val if val else placeholder

        html = """
        <html>
        <head>
            <style>
                body {{
                    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
                    font-size: 13px;
                    line-height: 1.6;
                    margin: 0;
                    padding: 8px;
                }}
                .title {{
                    text-align: center;
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 8px;
                }}
                .divider {{
                    border-top: 1px solid #333;
                    margin: 6px 0;
                }}
                .herb-grid {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 4px 20px;
                }}
                .herb-item {{
                    min-width: 80px;
                }}
                .usage {{
                    text-align: center;
                    margin-top: 6px;
                }}
                .doctor-row {{
                    text-align: right;
                    margin-top: 20px;
                    padding-right: 20px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                td {{
                    padding: 2px 4px;
                    vertical-align: top;
                }}
                .left-label {{
                    text-align: left;
                    white-space: nowrap;
                }}
                .right-value {{
                    text-align: left;
                }}
            </style>
        </head>
        <body>
            <div class="title">李玉贤中医工作室 医案笺</div>

            <table>
                <tr>
                    <td class="left-label">医案编号：{prescription_code}</td>
                    <td class="right-value"></td>
                    <td class="right-value"></td>
                    <td style="text-align: right;">日期：{date}</td>
                </tr>
                <tr>
                    <td class="left-label">姓名：{patient_name}</td>
                    <td class="left-label">性别：{gender}</td>
                    <td class="left-label">年龄：{age}岁</td>
                    <td></td>
                </tr>
                <tr>
                    <td class="left-label">电话：{phone}</td>
                    <td colspan="3" class="right-value">地址：{address}</td>
                </tr>
                <tr>
                    <td class="left-label">农历：{lunar}</td>
                    <td class="left-label">节气：{jieqi}</td>
                    <td colspan="2" class="right-value">交节：{jieqi_time}</td>
                </tr>
                <tr>
                    <td class="left-label">司天：{sitian}</td>
                    <td class="left-label">客气：{keqi}</td>
                    <td class="left-label">主运：{zhuyun}</td>
                    <td class="left-label">在泉：{zaiquan}</td>
                </tr>
            </table>

            <div class="divider"></div>

            <table>
                <tr>
                    <td class="left-label">主诉：{complaint}</td>
                </tr>
                <tr>
                    <td class="left-label">现病史：{history}</td>
                </tr>
                <tr>
                    <td class="left-label">舌像：{tongue}</td>
                    <td class="left-label">脉象：{pulse}</td>
                    <td colspan="2"></td>
                </tr>
                <tr>
                    <td class="left-label">辨证：{zhenghou}</td>
                </tr>
                <tr>
                    <td class="left-label">中医诊断：{zhongyi_diagnosis}</td>
                    <td class="left-label">中医病机：{zhongyi_bingji}</td>
                    <td colspan="2"></td>
                </tr>
                <tr>
                    <td class="left-label">中医证型：{zhengxing}</td>
                    <td class="left-label">中医治法：{zhifa}</td>
                    <td colspan="2"></td>
                </tr>
                <tr>
                    <td class="left-label">西医诊断：{xiyi_diagnosis}</td>
                </tr>
            </table>

            <div class="divider"></div>

            <div class="herb-grid">{herbs}</div>

            <div class="usage">{dose_count} {usage}</div>

            <div class="doctor-row">医师：{doctor}</div>
        </body>
        </html>
        """.format(
            prescription_code=v('prescription_code', '00001'),
            date=v('date', ''),
            patient_name=v('patient_name', '______'),
            gender=v('gender', '______'),
            age=v('age', '______'),
            phone=v('phone', '______'),
            address=v('address', '____________________'),
            lunar=v('lunar', ''),
            jieqi=v('jieqi', ''),
            jieqi_time=v('jieqi_time', ''),
            sitian=v('sitian', ''),
            keqi=v('keqi', ''),
            zhuyun=v('zhuyun', ''),
            zaiquan=v('zaiquan', ''),
            complaint=v('complaint', '________________________'),
            history=v('history', '________________________'),
            tongue=v('tongue', '________'),
            pulse=v('pulse', '________'),
            zhenghou=v('zhenghou', '________________________'),
            zhongyi_diagnosis=v('zhongyi_diagnosis', '________'),
            zhongyi_bingji=v('zhongyi_bingji', '________'),
            zhengxing=v('zhengxing', '________'),
            zhifa=v('zhifa', '________'),
            xiyi_diagnosis=v('xiyi_diagnosis', '____________________'),
            herbs=self._format_herbs(data.get('herbs', [])),
            dose_count=v('dose_count', ''),
            usage=v('usage', ''),
            doctor=v('doctor', '                    ')
        )

        self.browser.setHtml(html)

    def _format_herbs(self, herbs):
        if not herbs:
            return ""
        items = []
        for herb in herbs:
            text = f"{herb.get('name', '')} {herb.get('dose', '')}g"
            if herb.get('remark'):
                text += f"（{herb.get('remark')}）"
            items.append(f'<span class="herb-item">{text}</span>')
        return "    ".join(items)


class PrintTab(QWidget):
    """模块2：处方编辑与打印"""
    def __init__(self, log_console: LogConsole, parent=None):
        super().__init__(parent)
        self.log_console = log_console

        main_layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        btn_new = QPushButton("新建")
        btn_open = QPushButton("打开")
        btn_save = QPushButton("保存")
        btn_print = QPushButton("打印")
        btn_log = QPushButton("日志")
        btn_stat = QPushButton("统计")
        btn_as_template = QPushButton("存为模板")

        btn_load_docx = QPushButton("导入Word医案")
        btn_similar = QPushButton("相似病案计算")
        btn_preview = QPushButton("预览PDF")
        btn_save_db = QPushButton("保存到数据库")
        btn_export = QPushButton("导出并打印")

        toolbar.addWidget(btn_new)
        toolbar.addWidget(btn_open)
        toolbar.addWidget(btn_save)
        toolbar.addWidget(btn_print)
        toolbar.addWidget(btn_log)
        toolbar.addWidget(btn_stat)
        toolbar.addWidget(btn_as_template)
        toolbar.addStretch()
        toolbar.addWidget(btn_load_docx)
        toolbar.addWidget(btn_similar)
        toolbar.addWidget(btn_preview)
        toolbar.addWidget(btn_save_db)
        toolbar.addWidget(btn_export)

        btn_load_docx.clicked.connect(self.load_docx)
        btn_similar.clicked.connect(self.calc_similarity)
        btn_preview.clicked.connect(self.make_preview)
        btn_save_db.clicked.connect(self.save_to_db)
        btn_export.clicked.connect(self.export_and_print)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.herb_list = HerbListWidget()
        self.herb_list.herb_selected.connect(self.add_herb_to_editor)

        self.editor = PrescriptionEditor()
        self.preview = PrescriptionPreview()

        splitter.addWidget(self.herb_list)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([200, 500, 400])

        status_bar = QHBoxLayout()
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        status_bar.addStretch()

        main_layout.addLayout(toolbar)
        main_layout.addWidget(splitter)
        main_layout.addLayout(status_bar)

        # 连接信号
        self.editor.data_changed.connect(self._on_editor_data_changed)

        # 初始刷新
        self._refresh_preview()

    def _on_editor_data_changed(self):
        self._refresh_preview()

    def _refresh_preview(self):
        data = self.get_prescription_data()
        self.preview.update_preview(data)

    def add_herb_to_editor(self, herb_name):
        table = self.editor.herb_table
        for row in range(table.rowCount()):
            if not table.item(row, 0) or not table.item(row, 0).text():
                table.setItem(row, 0, QTableWidgetItem(herb_name))
                table.setItem(row, 1, QTableWidgetItem("10"))
                return
        table.insertRow(table.rowCount())
        table.setItem(table.rowCount() - 1, 0, QTableWidgetItem(herb_name))
        table.setItem(table.rowCount() - 1, 1, QTableWidgetItem("10"))

    def get_prescription_data(self):
        if hasattr(self.editor, "to_dict"):
            try:
                return self.editor.to_dict()
            except Exception:
                return {}
        return {}

    def load_docx(self):
        try:
            file, _ = QFileDialog.getOpenFileName(
                self, "选择 Word 医案", str(DATA_DIR), "Word 文件 (*.docx *.doc)"
            )
            if not file:
                return

            self.log_console.push_message(f"📄 开始导入：{os.path.basename(file)}")

            cases = parse_word_case_multi(file)

            if not cases:
                self.log_console.push_message("⚠️ 未检测到任何就诊记录")
                return

            if len(cases) == 1:
                data = cases[0]
                self.load_case_to_ui(data)
                cid = db.save_prescription(data)
                self.log_console.push_message(f"✅ 已保存到数据库（ID={cid}）")
                return

            dlg = QDialog(self)
            dlg.setWindowTitle("选择要导入的就诊记录")
            layout = QVBoxLayout(dlg)

            cb_list = []
            for c in cases:
                date_str = c.get("date", "未知日期")
                complaint = c.get("complaint", "")[:20] + "..." if len(c.get("complaint", "")) > 20 else c.get("complaint", "")
                cb = QCheckBox(f"{date_str} - {complaint}")
                layout.addWidget(cb)
                cb_list.append((cb, c))

            btn_all = QPushButton("全部导入")
            btn_ok = QPushButton("导入所选记录")
            btn_cancel = QPushButton("取消")

            hbox = QHBoxLayout()
            hbox.addWidget(btn_all)
            hbox.addWidget(btn_ok)
            hbox.addWidget(btn_cancel)
            layout.addLayout(hbox)

            selected_cases = []

            def import_all():
                nonlocal selected_cases
                selected_cases = [c for _, c in cb_list]
                dlg.accept()

            def import_selected():
                nonlocal selected_cases
                selected_cases = [c for cb, c in cb_list if cb.isChecked()]
                dlg.accept()

            btn_all.clicked.connect(import_all)
            btn_ok.clicked.connect(import_selected)
            btn_cancel.clicked.connect(dlg.reject)

            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.log_console.push_message("取消导入")
                return

            if not selected_cases:
                self.log_console.push_message("⚠️ 未选择任何记录")
                return

            for data in selected_cases:
                cid = db.save_prescription(data)
                self.log_console.push_message(f"✅ {data.get('date', '未知日期')} 已导入（ID={cid}）")

            self.load_case_to_ui(selected_cases[-1])

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 导入失败：{e}\n{tb}")

    def load_case_to_ui(self, data):
        if hasattr(self.editor, "load_from_dict"):
            self.editor.load_from_dict(data)

    def calc_similarity(self):
        try:
            data = self.get_prescription_data()
            text = (data.get("zhongyi_diagnosis", "") + "\n" +
                    data.get("zhenghou", "") + "\n" +
                    "\n".join([h.get("name", "") for h in data.get("herbs", [])])).strip()

            if not text:
                self.log_console.info("无比对文本（诊断或处方为空）")
                return

            results = find_similar_cases(text, topk=5)
            if not results:
                self.log_console.info("未找到相似病例")
                return

            self.log_console.push_message("📊 相似病例匹配结果：")
            for r in results:
                name = r.get("name", "未知患者")
                score = r.get("similarity", 0)
                self.log_console.push_message(f"🔍 {name} | 相似度 {score:.3f}")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 相似计算异常：{e}\n{tb}")

    def make_preview(self):
        try:
            data = self.get_prescription_data()
            if not data.get("patient_name"):
                QMessageBox.information(self, "提示", "请先填写患者信息")
                return

            out_path = OUTPUT_DIR / "prescription_preview.pdf"
            generate_prescription_pdf(data, str(out_path), paper="C6")

            self.log_console.push_message(f"📄 PDF 预览已生成：{out_path}")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 预览生成失败：{e}\n{tb}")

    def save_to_db(self):
        try:
            data = self.get_prescription_data()
            cid = db.save_prescription(data)
            self.log_console.push_message(f"💾 已保存处方（ID={cid}）")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 保存失败：{e}\n{tb}")

    def export_and_print(self):
        try:
            data = self.get_prescription_data()
            if not data.get("patient_name"):
                QMessageBox.information(self, "提示", "请先填写患者信息与处方内容")
                return

            fn, _ = QFileDialog.getSaveFileName(
                self, "导出处方 PDF", str(OUTPUT_DIR / "prescription.pdf"), "PDF 文件 (*.pdf)"
            )
            if not fn:
                return

            generate_prescription_pdf(data, fn, paper="C6")

            self.log_console.push_message(f"📁 已导出 PDF：{fn}")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 导出失败：{e}\n{tb}")
