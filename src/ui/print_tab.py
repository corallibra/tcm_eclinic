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
    QFrame, QFormLayout, QGridLayout
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QTimer, QObject, pyqtSlot
from PyQt6.QtGui import QFont

from config import DATA_DIR, OUTPUT_DIR
from src.ui.prescription_editor import PrescriptionEditor
from src.core.parse_docx import parse_word_case_multi
from src.core import db
from src.printing.pdf_template import generate_prescription_pdf
from src.ui.log_console import LogConsole
from src.core.similarity_engine import find_similar_cases

# 常用中药列表
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
    """左侧药材列表组件"""
    herb_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索药材...")
        self.search_edit.textChanged.connect(self.filter_herbs)
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.filter_herbs)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_btn)
        
        # 药材分类标签
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "解表药", "清热药", "泻下药", "祛湿药", "温里药"])
        self.category_combo.currentTextChanged.connect(self.filter_herbs)
        
        # 药材列表
        self.herb_list = QListWidget()
        self.herb_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.herb_list.itemDoubleClicked.connect(self.on_herb_double_click)
        self.load_herbs()
        
        # 布局
        layout.addLayout(search_layout)
        layout.addWidget(self.category_combo)
        layout.addWidget(self.herb_list)
    
    def load_herbs(self):
        """加载药材列表"""
        self.herb_list.clear()
        for herb in COMMON_HERBS:
            item = QListWidgetItem(herb)
            self.herb_list.addItem(item)
    
    def filter_herbs(self):
        """过滤药材列表"""
        keyword = self.search_edit.text().lower()
        category = self.category_combo.currentText()
        
        for i in range(self.herb_list.count()):
            item = self.herb_list.item(i)
            herb_name = item.text().lower()
            visible = True
            
            if keyword and keyword not in herb_name:
                visible = False
            
            item.setHidden(not visible)
    
    def on_herb_double_click(self, item):
        """双击药材添加到处方"""
        self.herb_selected.emit(item.text())


class PrescriptionPreview(QWidget):
    """实时处方预览组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        # 预览内容
        self.preview_content = QWidget()
        self.content_layout = QVBoxLayout(self.preview_content)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.content_layout.setSpacing(4)
        
        # 设置白色背景
        self.preview_content.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        
        self.scroll_area.setWidget(self.preview_content)
        self.layout.addWidget(self.scroll_area)
        
        # 初始预览内容
        self.update_preview({})
    
    def update_preview(self, data):
        """更新预览内容"""
        # 清空旧内容
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 创建标题
        title_label = QLabel("李玉贤中医工作室 医案笺")
        title_font = QFont("Arial", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setContentsMargins(0, 0, 0, 8)
        self.content_layout.addWidget(title_label)
        
        # 医案编号和日期
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel(f"医案编号：{data.get('prescription_code', '00001')}"))
        code_layout.addSpacing(20)
        code_layout.addWidget(QLabel(f"就诊日期：{data.get('date', '')}"))
        code_layout.addStretch()
        self.content_layout.addLayout(code_layout)
        
        # 第一行：姓名、性别、年龄
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(f"姓名：{data.get('patient_name', '')}"))
        row1.addSpacing(15)
        row1.addWidget(QLabel(f"性别：{data.get('gender', '')}"))
        row1.addSpacing(15)
        row1.addWidget(QLabel(f"年龄：{data.get('age', '')}岁"))
        row1.addStretch()
        self.content_layout.addLayout(row1)
        
        # 第二行：电话、地址
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(f"电话：{data.get('phone', '')}"))
        row2.addSpacing(15)
        row2.addWidget(QLabel(f"地址：{data.get('address', '')}"))
        row2.addStretch()
        self.content_layout.addLayout(row2)
        
        # 五运六气
        if data.get("jieqi") or data.get("zhuyun") or data.get("keyun") or data.get("wuyun"):
            wuliu_layout = QHBoxLayout()
            wuliu_layout.addWidget(QLabel(f"节气：{data.get('jieqi', '')}"))
            wuliu_layout.addSpacing(15)
            wuliu_layout.addWidget(QLabel(f"主运：{data.get('zhuyun', '')}"))
            wuliu_layout.addSpacing(15)
            wuliu_layout.addWidget(QLabel(f"客运：{data.get('keyun', '')}"))
            wuliu_layout.addSpacing(15)
            wuliu_layout.addWidget(QLabel(f"五运：{data.get('wuyun', '')}"))
            wuliu_layout.addStretch()
            self.content_layout.addLayout(wuliu_layout)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setContentsMargins(0, 4, 0, 4)
        self.content_layout.addWidget(line)
        
        # 主诉
        if data.get("complaint"):
            complaint_label = QLabel(f"主诉：{data.get('complaint')}")
            complaint_label.setWordWrap(True)
            self.content_layout.addWidget(complaint_label)
        
        # 现病史
        if data.get("history"):
            history_label = QLabel(f"现病史：{data.get('history')}")
            history_label.setWordWrap(True)
            self.content_layout.addWidget(history_label)
        
        # 舌像、脉象
        if data.get("tongue") or data.get("pulse"):
            tp_layout = QHBoxLayout()
            tp_layout.addWidget(QLabel(f"舌像：{data.get('tongue', '')}"))
            tp_layout.addSpacing(20)
            tp_layout.addWidget(QLabel(f"脉象：{data.get('pulse', '')}"))
            tp_layout.addStretch()
            self.content_layout.addWidget(tp_layout)
        
        # 辨证
        if data.get("zhenghou"):
            zhenghou_label = QLabel(f"辨证：{data.get('zhenghou')}")
            zhenghou_label.setWordWrap(True)
            self.content_layout.addWidget(zhenghou_label)
        
        # 中医诊断、病机
        if data.get("zhongyi_diagnosis") or data.get("zhongyi_bingji"):
            zy_layout = QHBoxLayout()
            zy_layout.addWidget(QLabel(f"中医诊断：{data.get('zhongyi_diagnosis', '')}"))
            zy_layout.addSpacing(20)
            zy_layout.addWidget(QLabel(f"中医病机：{data.get('zhongyi_bingji', '')}"))
            zy_layout.addStretch()
            self.content_layout.addWidget(zy_layout)
        
        # 中医证型、治法
        if data.get("zhengxing") or data.get("zhifa"):
            zx_layout = QHBoxLayout()
            zx_layout.addWidget(QLabel(f"中医证型：{data.get('zhengxing', '')}"))
            zx_layout.addSpacing(20)
            zx_layout.addWidget(QLabel(f"中医治法：{data.get('zhifa', '')}"))
            zx_layout.addStretch()
            self.content_layout.addWidget(zx_layout)
        
        # 西医诊断
        if data.get("xiyi_diagnosis"):
            xiyi_label = QLabel(f"西医诊断：{data.get('xiyi_diagnosis')}")
            xiyi_label.setWordWrap(True)
            self.content_layout.addWidget(xiyi_label)
        
        # 分割线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        self.content_layout.addWidget(line2)
        
        # Rp. 标记
        rp_label = QLabel("Rp.")
        rp_font = QFont("Arial", 12)
        rp_label.setFont(rp_font)
        self.content_layout.addWidget(rp_label)
        
        # 中药处方表格（三列）
        herbs = data.get("herbs", [])
        if herbs:
            herb_grid = QWidget()
            herb_layout = QGridLayout(herb_grid)
            herb_layout.setHorizontalSpacing(20)
            herb_layout.setVerticalSpacing(4)
            
            for i, herb in enumerate(herbs):
                row = i // 3
                col = i % 3
                herb_text = f"{herb.get('name', '')} {herb.get('dose', '')}g"
                if herb.get('remark'):
                    herb_text += f"（{herb.get('remark')}）"
                herb_label = QLabel(herb_text)
                herb_layout.addWidget(herb_label, row, col)
            
            self.content_layout.addWidget(herb_grid)
        
        # 用法
        if data.get("dose_count") or data.get("usage"):
            usage_label = QLabel(f"{data.get('dose_count', '')} {data.get('usage', '')}")
            usage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(usage_label)
        
        # 医师信息
        if data.get("doctor"):
            doctor_frame = QFrame()
            doctor_layout = QVBoxLayout(doctor_frame)
            doctor_layout.addWidget(QLabel(f"医师：{data.get('doctor', '')}"))
            self.content_layout.addWidget(doctor_frame)
        
        # 空白区域
        self.content_layout.addStretch()


class PrintTab(QWidget):
    """模块2：处方编辑与打印（重新设计版）"""
    def __init__(self, log_console: LogConsole, parent=None):
        super().__init__(parent)
        self.log_console = log_console
        
        # 主布局：顶部工具栏 + 主体区域
        main_layout = QVBoxLayout(self)
        
        # ======== 顶部工具栏 ========
        toolbar = QHBoxLayout()
        
        # 左侧功能按钮
        btn_new = QPushButton("新建")
        btn_open = QPushButton("打开")
        btn_save = QPushButton("保存")
        btn_print = QPushButton("打印")
        btn_log = QPushButton("日志")
        btn_stat = QPushButton("统计")
        btn_as_template = QPushButton("存为模板")
        
        # 右侧功能按钮
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
        
        # 连接信号
        btn_load_docx.clicked.connect(self.load_docx)
        btn_similar.clicked.connect(self.calc_similarity)
        btn_preview.clicked.connect(self.make_preview)
        btn_save_db.clicked.connect(self.save_to_db)
        btn_export.clicked.connect(self.export_and_print)
        
        # ======== 主体区域 ========
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：药材列表
        self.herb_list = HerbListWidget()
        self.herb_list.herb_selected.connect(self.add_herb_to_editor)
        
        # 中间：处方编辑器
        try:
            self.editor = PrescriptionEditor()
        except Exception as e:
            self.log_console.push_message(f"❌ 载入编辑器失败：{e}")
            self.editor = QWidget()
        
        # 右侧：实时预览
        self.preview = PrescriptionPreview()
        
        splitter.addWidget(self.herb_list)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([200, 500, 400])
        
        # ======== 底部状态栏 ========
        status_bar = QHBoxLayout()
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        status_bar.addStretch()
        
        # 组装布局
        main_layout.addLayout(toolbar)
        main_layout.addWidget(splitter)
        main_layout.addLayout(status_bar)
        
        # 实时预览定时器
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(500)  # 每500ms更新一次
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start()
    
    def add_herb_to_editor(self, herb_name):
        """添加药材到编辑器的药材表格"""
        table = self.editor.herb_table
        for row in range(table.rowCount()):
            if not table.item(row, 0) or not table.item(row, 0).text():
                table.setItem(row, 0, QTableWidgetItem(herb_name))
                table.setItem(row, 1, QTableWidgetItem("10"))
                return
        
        # 如果已满，添加新行
        table.insertRow(table.rowCount())
        table.setItem(table.rowCount() - 1, 0, QTableWidgetItem(herb_name))
        table.setItem(table.rowCount() - 1, 1, QTableWidgetItem("10"))
    
    def update_preview(self):
        """更新实时预览"""
        try:
            data = self.get_prescription_data()
            self.preview.update_preview(data)
        except Exception as e:
            # 预览更新失败不影响主程序
            pass
    
    def get_prescription_data(self):
        """整合编辑器数据"""
        if hasattr(self.editor, "to_dict"):
            return self.editor.to_dict()
        return {}
    
    # ============================================================
    # 导入 Word 医案
    # ============================================================
    def load_docx(self):
        """支持一个 Word 中包含多个就诊记录"""
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
        """将病例数据加载到UI"""
        if hasattr(self.editor, "load_from_dict"):
            self.editor.load_from_dict(data)
    
    # ============================================================
    # 相似病例计算
    # ============================================================
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
    
    # ============================================================
    # PDF 预览
    # ============================================================
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
    
    # ============================================================
    # 保存处方到数据库
    # ============================================================
    def save_to_db(self):
        try:
            data = self.get_prescription_data()
            cid = db.save_prescription(data)
            self.log_console.push_message(f"💾 已保存处方（ID={cid}）")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 保存失败：{e}\n{tb}")
    
    # ============================================================
    # 导出 PDF + 打印
    # ============================================================
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
