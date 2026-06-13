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
from PyQt6.QtGui import QAction, QIcon, QFont, QTextOption, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextBrowser, QTextEdit, QTabWidget, QFileDialog, QMessageBox, QLineEdit, QPushButton,
    QLabel, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QProgressBar, QMenu
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
from src.ui.print_tab import PrintTab

# ---- 业务逻辑层 ----
from src.core import db, parse_docx
from src.core.parse_docx import parse_word_case, parse_word_case_multi, import_cases_from_folder

# ---- 日志模块 ----
from logger import get_logger, QTextEditHandler

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

class MainWindow(QMainWindow):
    """主窗口（支持数据库管理器 + 应用配置）"""

    def __init__(self, db=None, app_config: dict = None):
        # db: DatabaseManager 或类似对象（可选，用于 Word 导入功能扩展）
        # app_config: 应用配置字典（可选，仅保留向后兼容）
        super().__init__()

        # 保存传入的参数供外部使用
        self.db_manager = db      # 数据库管理器实例
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

        self.tabs.addTab(self.tab_print, "处方编辑与打印")
        self.tabs.addTab(self.tab_query, "医案查询检索")
        self.tabs.addTab(self.tab_stats, "数据统计分析")
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

        # ── 文件 ──
        menu_file = bar.addMenu("文件(&F)")

        act_new = QAction("新建处方(&N)", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._menu_file_new)
        menu_file.addAction(act_new)

        act_open = QAction("打开处方(&O)", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._menu_file_open)
        menu_file.addAction(act_open)

        # 打开最近（预留）
        self.menu_recent = QMenu("打开最近(&R)", self)
        self.menu_recent.setEnabled(False)  # 暂无最近文件功能
        menu_file.addMenu(self.menu_recent)

        menu_file.addSeparator()

        act_save = QAction("保存(&S)", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._menu_file_save)
        menu_file.addAction(act_save)

        act_save_as = QAction("另存为/导出PDF(&E)", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._menu_file_export)
        menu_file.addAction(act_save_as)

        menu_file.addSeparator()

        act_import_word = QAction("导入Word医案...", self)
        act_import_word.triggered.connect(self._menu_file_import_word)
        menu_file.addAction(act_import_word)

        act_import_batch = QAction("批量导入病例...", self)
        act_import_batch.setShortcut(QKeySequence("Ctrl+Shift+I"))
        act_import_batch.triggered.connect(self.do_import_cases)
        menu_file.addAction(act_import_batch)

        menu_file.addSeparator()

        act_print = QAction("打印预览(&P)", self)
        act_print.setShortcut(QKeySequence.StandardKey.Print)
        act_print.triggered.connect(self._menu_file_print)
        menu_file.addAction(act_print)

        menu_file.addSeparator()

        act_exit = QAction("退出(&Q)", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # ── 编辑 ──
        menu_edit = bar.addMenu("编辑(&E)")

        self._act_undo = QAction("撤销(&U)", self)
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.setEnabled(False)  # 预留
        menu_edit.addAction(self._act_undo)

        self._act_redo = QAction("重做(&R)", self)
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.setEnabled(False)  # 预留
        menu_edit.addAction(self._act_redo)

        menu_edit.addSeparator()

        self._act_select_all = QAction("全选(&A)", self)
        self._act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self._act_select_all.setEnabled(False)  # 预留
        menu_edit.addAction(self._act_select_all)

        self._act_find = QAction("查找/替换(&F)...", self)
        self._act_find.setShortcut(QKeySequence.StandardKey.Find)
        self._act_find.setEnabled(False)  # 预留
        menu_edit.addAction(self._act_find)

        # ── 视图 ──
        menu_view = bar.addMenu("视图(&V)")

        act_toggle_log = QAction("显示/隐藏日志控制台", self)
        act_toggle_log.setCheckable(True)
        act_toggle_log.setChecked(True)
        act_toggle_log.triggered.connect(self._menu_view_toggle_log)
        menu_view.addAction(act_toggle_log)

        menu_view.addSeparator()

        tab_labels = [
            ("处方编辑与打印", 0),
            ("医案查询检索", 1),
            ("数据统计分析", 2),
            ("方药词云分析", 3),
            ("系统设置", 4),
        ]
        for label, idx in tab_labels:
            act = QAction(label, self)
            act.triggered.connect(lambda checked, i=idx: self.tabs.setCurrentIndex(i))
            menu_view.addAction(act)

        # ── 工具 ──
        menu_tools = bar.addMenu("工具(&T)")

        act_similar = QAction("相似病案计算", self)
        act_similar.triggered.connect(self._menu_tools_similar)
        menu_tools.addAction(act_similar)

        act_cloud = QAction("生成方药词云", self)
        act_cloud.triggered.connect(self._menu_tools_cloud)
        menu_tools.addAction(act_cloud)

        menu_tools.addSeparator()

        act_backup = QAction("数据库备份...", self)
        act_backup.setEnabled(False)  # 预留
        menu_tools.addAction(act_backup)

        menu_tools.addSeparator()

        act_settings = QAction("系统设置", self)
        act_settings.triggered.connect(lambda: self.tabs.setCurrentIndex(4))
        menu_tools.addAction(act_settings)

        # ── 帮助 ──
        menu_help = bar.addMenu("帮助(&H)")

        act_manual = QAction("用户手册", self)
        act_manual.setEnabled(False)  # 预留
        menu_help.addAction(act_manual)

        act_about = QAction("关于", self)
        act_about.triggered.connect(self._menu_help_about)
        menu_help.addAction(act_about)

    # ── 菜单动作实现 ──

    def _get_print_tab(self):
        """获取处方编辑标签页"""
        return self.tab_print

    def _menu_file_new(self):
        """新建处方：清空编辑器"""
        self.tabs.setCurrentIndex(0)
        editor = self._get_print_tab().editor
        editor.load_from_dict({})
        self.log_console.push_message("已新建空白处方")

    def _menu_file_open(self):
        """打开处方：切换到查询页让用户搜索后选择"""
        self.tabs.setCurrentIndex(1)
        self.log_console.push_message("请在医案查询检索页搜索并选择患者")

    def _menu_file_save(self):
        """保存处方到数据库"""
        self.tabs.setCurrentIndex(0)
        try:
            data = self._get_print_tab().get_prescription_data()
            if not data.get("patient_name"):
                QMessageBox.information(self, "提示", "请先填写患者信息")
                return
            cid = db.save_prescription(data)
            self.log_console.push_message(f"已保存处方（ID={cid}）")
        except Exception as e:
            self.log_console.push_message(f"保存失败：{e}")

    def _menu_file_export(self):
        """导出处方为PDF"""
        self.tabs.setCurrentIndex(0)
        self._get_print_tab().export_and_print()

    def _menu_file_import_word(self):
        """导入单个Word医案"""
        self.tabs.setCurrentIndex(0)
        self._get_print_tab().load_docx()

    def _menu_file_print(self):
        """打印预览"""
        self.tabs.setCurrentIndex(0)
        self._get_print_tab().make_preview()

    def _menu_view_toggle_log(self, visible):
        """显示/隐藏日志控制台"""
        self.log_console.setVisible(visible)

    def _menu_tools_similar(self):
        """相似病案计算"""
        self.tabs.setCurrentIndex(0)
        self._get_print_tab().calc_similarity()

    def _menu_tools_cloud(self):
        """生成方药词云"""
        self.tabs.setCurrentIndex(3)
        if hasattr(self.tab_cloud, "make_cloud"):
            self.tab_cloud.make_cloud()

    @staticmethod
    def _menu_help_about():
        """关于对话框"""
        QMessageBox.about(
            None,
            "关于 TCM eClinic",
            "<h3>TCM eClinic v2.0</h3>"
            "<p>中医门诊处方处理平台</p>"
            "<p>功能：处方编辑、医案检索、数据统计、方药词云</p>"
            "<hr>"
            "<p>Powered by PyQt6</p>"
        )

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
