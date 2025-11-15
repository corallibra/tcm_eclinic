# -*- coding: utf-8 -*-
# TCM_eclinic/src/ui/gui_main.py
import os
import sys
import tempfile
import traceback
from datetime import datetime
import logging
import re

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QIcon, QFont, QTextOption
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextBrowser, QTextEdit, QTabWidget, QFileDialog, QMessageBox, QLineEdit, QPushButton,
    QLabel, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, 
    QProgressBar
)
from PyQt6.QtCore import QThread, pyqtSignal

# ✅ 统一路径引用
from config import DATA_DIR, OUTPUT_DIR, APP_CONFIG
SAMPLES_DIR = DATA_DIR / "samples"

# ---- UI 控件 ----
from src.ui.similarity_strip import SimilarityStrip
from src.core.similarity_engine import find_similar_cases
from src.ui.log_console import LogConsole
from src.ui.prescription_editor import PrescriptionEditor

# ---- 业务逻辑层 ----
from src.core import db, parse_docx
from src.core import parse_docx
from src.core.parse_docx import parse_word_case, parse_word_case_multi, import_cases_from_folder

# ---- PDF 打印层 ----
from src.printing.pdf_template import generate_prescription_pdf
from src.printing.print_template import render_prescription_pdf


# === 日志控制台类 ===

class ImportWorker(QThread):
    """后台批量导入线程"""
    progress_signal = pyqtSignal(int, int)       # 当前进度, 总数
    message_signal = pyqtSignal(str)             # 输出消息
    finished_signal = pyqtSignal(int, int)       # 成功, 失败

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

    def run(self):
        success, fail = 0, 0
        self.message_signal.emit(f"开始批量导入：{self.folder}")
        all_files = []
        for root, _, files in os.walk(self.folder):
            for fn in files:
                if fn.lower().endswith((".docx", ".doc")):
                    all_files.append(os.path.join(root, fn))
        total = len(all_files)
        if not total:
            self.message_signal.emit("❌ 未找到 Word 文件 (.docx / .doc)")
            self.finished_signal.emit(0, 0)
            return

        for i, path in enumerate(all_files, 1):
            try:
                data = parse_docx.parse_word_case(path)
                # 若姓名为空尝试从文件名提取
                if not data.get("patient_name"):
                    base = os.path.splitext(os.path.basename(path))[0]
                    m = re.match(r"^([\u4e00-\u9fa5]{2,5})", base)
                    if m:
                        data["patient_name"] = m.group(1)
                        self.message_signal.emit(f"📛 从文件名提取姓名：{data['patient_name']} ← {os.path.basename(path)}")
                    else:
                        self.message_signal.emit(f"⚠️ 跳过文件（未识别姓名）：{os.path.basename(path)}")
                        continue

                cid = db.save_prescription(data)
                success += 1
                self.message_signal.emit(f"✅ {os.path.basename(path)} → {data['patient_name']} | ID={cid}")
            except Exception as e:
                fail += 1
                import traceback
                tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                self.message_signal.emit(f"❌ 解析失败：{os.path.basename(path)} | {e}\n{tb}")
            self.progress_signal.emit(i, total)
        self.finished_signal.emit(success, fail)

# 预览所需（QtPdf）
try:
    from PyQt6.QtPdf import QPdfDocument
    from PyQt6.QtPdfWidgets import QPdfView
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

# 本项目模块
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
# DATA_DIR = os.path.join(PROJECT_ROOT, "data")
# SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
# os.makedirs(OUTPUT_DIR, exist_ok=True)

class PdfPreview(QWidget):
    """右侧 PDF 预览（Qt6 原生），若缺失 QtPdf 自动退化"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        if PDF_AVAILABLE:
            self.doc = QPdfDocument(self)
            self.viewer = QPdfView(self)
            self.viewer.setDocument(self.doc)
            layout.addWidget(self.viewer)
        else:
            self.doc = None
            self.viewer = PreviewFallback()
            layout.addWidget(self.viewer)

    def load_pdf(self, path: str):
        if PDF_AVAILABLE and self.doc is not None:
            self.doc.load(path)
        else:
            self.viewer.show_hint(path)

class QueryTab(QWidget):
    """模块1：医案查询检索 + 时间线视图"""
    def __init__(self, log_console, parent=None):
        super().__init__(parent)
        self.log_console = log_console

        # ---- 主布局：左右结构 ----
        main_layout = QHBoxLayout(self)

        # ================================
        # 左侧：搜索框 + 表格
        # ================================
        left_layout = QVBoxLayout()

        # 搜索条
        search_box = QHBoxLayout()
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("患者姓名 / 证候 / 关键词…")
        btn_search = QPushButton("搜索")
        btn_search.clicked.connect(self.do_search)
        search_box.addWidget(self.keyword)
        search_box.addWidget(btn_search)

        # 结果表格
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["就诊ID", "姓名", "主诉/证候", "日期", "医生"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_table_select)

        left_layout.addLayout(search_box)
        left_layout.addWidget(self.table)

        # ================================
        # 右侧：时间线 + 详情
        # ================================
        right_layout = QVBoxLayout()

        # 时间线

        self.timeline = QTextBrowser()
        self.timeline.setPlaceholderText("请选择左侧患者查看就诊时间线…")
        self.timeline.setOpenExternalLinks(False)
        self.timeline.setReadOnly(True)
        self.timeline.setStyleSheet("font-size:14px;")
        self.timeline.anchorClicked.connect(self.on_timeline_clicked)

        # 详情框
        self.detail_box = QTextEdit()
        self.detail_box.setReadOnly(True)
        self.detail_box.setPlaceholderText("点击时间线记录查看详细病案…")
        self.detail_box.setStyleSheet("font-size:14px;")

        right_layout.addWidget(QLabel("📜 就诊时间线："))
        right_layout.addWidget(self.timeline, 3)
        right_layout.addWidget(QLabel("📝 本次就诊详情："))
        right_layout.addWidget(self.detail_box, 2)

        # 添加左右结构
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 3)

        # 缓存点击后 timeline 记录
        self.timeline_records = []

    # ---------------------------------------------
    # 左侧选中患者 → 加载 timeline
    # ---------------------------------------------
    def on_table_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        name = self.table.item(rows[0].row(), 1).text()
        self.load_timeline(name)

    # ---------------------------------------------
    # 时间线显示
    # ---------------------------------------------
    def load_timeline(self, patient_name):
        try:
            records = db.get_all_cases_by_name(patient_name)
        except Exception as e:
            self.timeline.setText(f"❌ 时间线加载失败：{e}")
            return

        if not records:
            self.timeline.setText("（无历史就诊记录）")
            return

        # 按日期排序
        records_sorted = sorted(records, key=lambda r: r.get("date", ""))
        self.timeline_records = records_sorted

        html = ""
        for idx, rec in enumerate(records_sorted):
            date = rec.get("date", "未知日期")
            cpl = rec.get("complaint", "无主诉")
            zheng = rec.get("zhenghou", "")
            tongue = rec.get("tongue", "")
            pulse = rec.get("pulse", "")
            doctor = rec.get("doctor", "")
            herbs = rec.get("herbs", [])

            if herbs:
                herbs_short = "、".join([h["name"] for h in herbs[:5]])
                if len(herbs) > 5:
                    herbs_short += "…"
            else:
                herbs_short = "—"

            html += f"""
            <p><b>🕒 {date}</b></p>
            <p>😷 <b>主诉：</b>{cpl}</p>
            <p>👅 舌：{tongue or '—'}　🫀 脉：{pulse or '—'}</p>
            <p>🧭 证候：{zheng or '—'}</p>
            <p>🧪 方药：{herbs_short}</p>
            <p>👨‍⚕️ 医师：{doctor or '—'}</p>
            <p><a href="{idx}">👉 查看详细</a></p>
            <hr>
            """

        self.timeline.setHtml(html)

    # ---------------------------------------------
    # 点击 timeline → 展示完整病案
    # ---------------------------------------------
    def on_timeline_clicked(self, url):
        try:
            idx = int(url.toString())
            rec = self.timeline_records[idx]
        except:
            return

        detail = (
            f"🕒 就诊时间：{rec.get('date','')}\n\n"
            f"😷 主诉：{rec.get('complaint','')}\n\n"
            f"🔍 症状：\n{rec.get('symptoms','')}\n\n"
            f"👅 舌象：{rec.get('tongue','')}\n"
            f"🫀 脉象：{rec.get('pulse','')}\n\n"
            f"🧭 诊断：{rec.get('diagnosis_clinic','')}\n"
            f"🏷 证候：{rec.get('zhenghou','')}\n"
            f"📘 治法：{rec.get('zhifa','')}\n\n"
            f"🧪 处方：\n{rec.get('prescription','')}\n\n"
            f"👨‍⚕️ 医师：{rec.get('doctor','')}\n"
        )

        self.detail_box.setText(detail)

    # ---------------------------------------------
    # 搜索
    # ---------------------------------------------
    def do_search(self):
        kw = self.keyword.text().strip()
        try:
            rows = db.search_cases(kw)
        except Exception as e:
            self.timeline.setText(f"❌ 检索失败：{e}")
            return

        self.table.setRowCount(0)
        for r in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for c, v in enumerate(r):
                self.table.setItem(row, c, QTableWidgetItem(str(v)))

        self.log_console.push_message(
            f"检索完成：匹配到 {len(rows)} 条记录（关键词：{kw or '全部'}）"
        )


class PrintTab(QWidget):
    """模块2：处方编辑与打印（导入 / 相似 / 预览 / 保存 / 导出）"""
    def __init__(self, log_console: LogConsole, parent=None):
        super().__init__(parent)
        self.log_console = log_console

        layout = QVBoxLayout(self)

        # 左编辑器 + 右 PDF 预览
        splitter = QSplitter(Qt.Orientation.Horizontal)

        try:
            self.editor = PrescriptionEditor()
        except Exception as e:
            self.log_console.push_message(f"❌ 载入编辑器失败：{e}")
            self.editor = QWidget()

        self.preview = PdfPreview()

        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([700, 400])

        # 按钮栏
        toolbar = QHBoxLayout()
        btn_load = QPushButton("导入Word医案")
        btn_sim = QPushButton("相似病案计算")
        btn_preview = QPushButton("预览PDF")
        btn_save = QPushButton("保存到数据库")
        btn_export = QPushButton("导出并打印")

        btn_load.clicked.connect(self.load_docx)
        btn_sim.clicked.connect(self.calc_similarity)
        btn_preview.clicked.connect(self.make_preview)
        btn_save.clicked.connect(self.save_to_db)
        btn_export.clicked.connect(self.export_and_print)

        toolbar.addWidget(btn_load)
        toolbar.addWidget(btn_sim)
        toolbar.addStretch()
        toolbar.addWidget(btn_preview)
        toolbar.addWidget(btn_save)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)
        layout.addWidget(splitter)

    # ============================================================
    # 导入 Word 医案
    # ============================================================
    def load_docx(self):
        """支持一个 Word 中包含多个就诊记录"""
        try:
            file, _ = QFileDialog.getOpenFileName(
                self, "选择 Word 医案", str(SAMPLES_DIR), "Word 文件 (*.docx *.doc)"
            )
            if not file:
                return

            self.log_console.push_message(f"📄 开始导入：{os.path.basename(file)}")

            # ---- 使用新版多就诊解析 ----
            cases = parse_word_case_multi(file)

            if not cases:
                self.log_console.push_message("⚠️ 未检测到任何就诊记录")
                return

            # ---- 如果只有一条记录：直接导入 ----
            if len(cases) == 1:
                data = cases[0]

                if hasattr(self.editor, "load_from_dict"):
                    self.editor.load_from_dict(data)

                cid = db.save_prescription(data)
                self.log_console.push_message(f"✅ 已保存到数据库（ID={cid}）")
                return

            # ---- 多次就诊，弹出对话框选择 ----
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel

            dlg = QDialog(self)
            dlg.setWindowTitle("选择要导入的就诊记录")
            layout = QVBoxLayout(dlg)

            cb_list = []
            for c in cases:
                cb = QCheckBox(c["date"])
                layout.addWidget(cb)
                cb_list.append(cb)

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
                selected_cases = cases
                dlg.accept()

            def import_selected():
                nonlocal selected_cases
                selected_cases = [ cases[i] for i, cb in enumerate(cb_list) if cb.isChecked() ]
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

            # ---- 导入所有选中记录 ----
            for data in selected_cases:
                cid = db.save_prescription(data)
                self.log_console.push_message(f"✅ {data['date']} 已导入（ID={cid}）")

            # 默认把最后一条加载到编辑器方便修改
            if hasattr(self.editor, "load_from_dict"):
                self.editor.load_from_dict(selected_cases[-1])

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 导入失败：{e}\n{tb}")

    # ============================================================
    # 相似病例计算
    # ============================================================
    def calc_similarity(self):
        try:
            data = self.editor.to_dict()
            text = (data.get("diagnosis", "") + "\n" + data.get("prescription", "")).strip()

            if not text:
                self.log_console.info("无比对文本（诊断或处方为空）")
                return

            results = find_similar_cases(text, topk=5)
            if not results:
                self.log_console.info("未找到相似病例")
                return

            for r in results:
                name = r.get("name", "未知患者")
                score = r.get("similarity", 0)
                self.log_console.info(f"🔍 {name} | 相似度 {score:.3f}")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.error(f"相似计算异常：{e}\n{tb}")

    # ============================================================
    # PDF 预览
    # ============================================================
    def make_preview(self):
        try:
            data = self.editor.to_dict()
            if not data.get("patient_name"):
                QMessageBox.information(self, "提示", "请先填写患者信息")
                return

            out_path = OUTPUT_DIR / "prescription_preview.pdf"
            generate_prescription_pdf(data, str(out_path), paper="C6")

            self.preview.load_pdf(str(out_path))

            self.log_console.push_message(f"📄 PDF 预览已生成：{out_path}")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 预览生成失败：{e}\n{tb}")

    # ============================================================
    # 保存处方到数据库
    # ============================================================
    def save_to_db(self):
        try:
            data = self.editor.to_dict()
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
            data = self.editor.to_dict()
            if not data.get("patient_name"):
                QMessageBox.information(self, "提示", "请先填写患者信息与处方内容")
                return

            fn, _ = QFileDialog.getSaveFileName(
                self, "导出处方 PDF", str(OUTPUT_DIR / "prescription.pdf"), "PDF 文件 (*.pdf)"
            )
            if not fn:
                return

            generate_prescription_pdf(data, fn, paper="C6")
            self.preview.load_pdf(fn)

            self.log_console.push_message(f"📁 已导出 PDF：{fn}")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 导出失败：{e}\n{tb}")


class StatsTab(QWidget):
    """模块3：数据统计分析（占位版，留出数据可视化挂点）"""
    def __init__(self, sim_strip: SimilarityStrip, parent=None):
        super().__init__(parent)
        self.log_console = sim_strip
        layout = QFormLayout(self)
        self.input_start = QLineEdit()
        self.input_end = QLineEdit()
        btn = QPushButton("统计")
        btn.clicked.connect(self.run_stats)
        layout.addRow("起始日期(YYYY-MM-DD)：", self.input_start)
        layout.addRow("结束日期(YYYY-MM-DD)：", self.input_end)
        layout.addRow(btn)

    def run_stats(self):
        start = self.input_start.text().strip()
        end = self.input_end.text().strip()
        cnt, top_herbs = db.stat_cases(start, end)
        self.log_console.push_message(f"区间病例数：{cnt}；高频药材：{', '.join(top_herbs[:5]) if top_herbs else '无'}")

class HerbCloudTab(QWidget):
    """模块4：方药高频词云（独立于模块3）"""
    def __init__(self, log_console, parent=None):
        super().__init__(parent)
        self.log_console = log_console

        layout = QVBoxLayout(self)

        btn_cloud = QPushButton("生成方药高频词云")
        btn_cloud.clicked.connect(self.make_cloud)
        layout.addWidget(btn_cloud)

        self.info = QLabel("点击上方按钮生成方药词云")
        layout.addWidget(self.info)

    # ------------------------------- 生成词云 -------------------------------
    def make_cloud(self):
        try:
            all_cases = db.get_all_cases()

            freq = {}
            for c in all_cases:
                herbs = c.get("herbs", [])
                for h in herbs:
                    name = h["name"].strip()
                    if not name:
                        continue
                    freq[name] = freq.get(name, 0) + 1

            if not freq:
                QMessageBox.information(self, "提示", "数据库中无可统计方药")
                return

            wc = WordCloud(
                font_path="C:/Windows/Fonts/simhei.ttf",  # 支持中文
                background_color="white",
                width=1000,
                height=600
            ).generate_from_frequencies(freq)

            out = OUTPUT_DIR / "herb_cloud.png"
            wc.to_file(out)

            self.info.setText(f"词云已生成：{out}")
            self.log_console.push_message(f"🌟 已生成方药词云：{out}")

        except Exception as e:
            tb = traceback.format_exc()
            self.log_console.push_message(f"❌ 生成词云失败：{e}\n{tb}")


class SettingsTab(QWidget):
    """模块5：系统设置 / 模板管理"""
    def __init__(self, sim_strip: SimilarityStrip, parent=None):
        super().__init__(parent)
        self.log_console = sim_strip
        layout = QFormLayout(self)
        self.clinic_name = QLineEdit()
        self.doctor_name = QLineEdit()
        self.template_note = QLineEdit()
        btn_save = QPushButton("保存设置")
        btn_save.clicked.connect(self.save)
        layout.addRow("门诊名称：", self.clinic_name)
        layout.addRow("默认医师：", self.doctor_name)
        layout.addRow("模板备注：", self.template_note)
        layout.addRow(btn_save)

    def save(self):
        ok = db.save_settings({
            "clinic_name": self.clinic_name.text(),
            "doctor_name": self.doctor_name.text(),
            "template_note": self.template_note.text()
        })
        if ok:
            self.log_console.push_message("系统设置已保存")
        else:
            QMessageBox.warning(self, "失败", "无法保存设置")

from logger import get_logger, QTextEditHandler

class MainWindow(QMainWindow):
    """主窗口（整理版：无重复、结构清晰、保留全部功能）"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("李玉贤名医工作室电子病案系统")
        self.resize(1200, 800)

        # ======================================================
        #  日志输出区域
        # ======================================================
        self.log_console = LogConsole()
        self.log_console.set_fixed_4_rows()
        self.log_console.push_message("系统启动成功")

        # 绑定 logging → GUI
        self.log = get_logger()
        if not any(isinstance(h, QTextEditHandler) for h in self.log.handlers):
            h = QTextEditHandler(self.log_console)
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
            h.setFormatter(fmt)
            self.log.addHandler(h)
            self.log.setLevel(logging.INFO)

        # ======================================================
        #  构建 Tabs
        # ======================================================
        self.tabs = QTabWidget()

        # 模块 1：医案检索 + 时间线
        self.tab_query = QueryTab(self.log_console)
        # 模块 2：处方编辑与打印
        self.tab_print = PrintTab(self.log_console)
        # 模块 3：占位版统计页（保留）
        self.tab_stats = StatsTab(self.log_console)
        # 模块 4：方药词云
        self.tab_cloud = HerbCloudTab(self.log_console)
        # 模块 5：系统设置
        self.tab_settings = SettingsTab(self.log_console)

        self.tabs.addTab(self.tab_query, "医案查询检索")
        self.tabs.addTab(self.tab_print, "处方编辑与打印")
        self.tabs.addTab(self.tab_stats, "数据统计分析（占位版）")
        self.tabs.addTab(self.tab_cloud, "方药词云分析")
        self.tabs.addTab(self.tab_settings, "系统设置")

        # ======================================================
        #  进度条
        # ======================================================
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        # ======================================================
        #  主布局
        # ======================================================
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.log_console)
        layout.addWidget(self.tabs)
        layout.addWidget(self.progress)
        self.setCentralWidget(central)

        # ======================================================
        #  菜单栏
        # ======================================================
        self._build_menu()

        # ======================================================
        #  全局异常捕获
        # ======================================================
        def hook(t, v, tb):
            txt = "".join(traceback.format_exception(t, v, tb))
            self.log_console.sig_log.emit("ERROR", txt)
        sys.excepthook = hook

        self.log.info("主窗口初始化完成")

    # ==========================================================
    #  构建菜单
    # ==========================================================
    def _build_menu(self):
        bar = self.menuBar()
        menu_file = bar.addMenu("文件")

        act_import = QAction("批量导入病例", self)
        act_import.triggered.connect(self.do_import_cases)
        menu_file.addAction(act_import)

        act_exit = QAction("退出", self)
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

    # ==========================================================
    #  批量导入（线程执行）
    # ==========================================================
    def do_import_cases(self):
        folder = QFileDialog.getExistingDirectory(self, "选择医案文件夹", str(DATA_DIR))
        if not folder:
            return

        self.progress.setValue(0)
        self.log_console.push_message(f"准备导入目录：{folder}")

        self.worker = ImportWorker(folder)
        self.worker.message_signal.connect(self.log_console.push_message)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.import_finished)
        self.worker.start()

    def update_progress(self, cur, tot):
        pct = int(cur / tot * 100)
        self.progress.setValue(pct)

    def import_finished(self, success, fail):
        self.log_console.push_message(f"📊 批量导入完成：成功 {success} 份，失败 {fail} 份。")
        self.progress.setValue(100)

        # 自动刷新查询页
        if hasattr(self.tab_query, "do_search"):
            try:
                self.tab_query.do_search()
            except:
                pass

    # ==========================================================
    #  安全关闭（彻底修复 QTextEditHandler 被销毁错误）
    # ==========================================================
    def closeEvent(self, event):
        try:
            logging.shutdown = lambda *a, **k: None
            for h in list(self.log.handlers):
                try:
                    h.close()
                except:
                    pass
                self.log.removeHandler(h)

            self.log.handlers.clear()
            self.log.info("日志系统已安全关闭。")

        except Exception as e:
            print(f"[警告] 在关闭日志处理器时出错：{e}")

        super().closeEvent(event)

if __name__ == "__main__":
    main()
