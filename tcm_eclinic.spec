# -*- coding: utf-8 -*-
# PyInstaller spec for TCM eClinic — Windows 11 single-file executable
# Build: pyinstaller tcm_eclinic.spec

import os
import sys
from pathlib import Path

try:
    PROJECT_ROOT = Path(SPECPATH)
except NameError:
    PROJECT_ROOT = Path('.').resolve()

block_cipher = None

# ── jieba 词典 ──────────────────────────────────────
import jieba
jieba_dict = os.path.join(os.path.dirname(jieba.__file__), 'dict.txt')

# ── 附属数据文件（存在才打包） ──────────────────────
added_files = []
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    added_files.append((str(env_path), '.'))
added_files.append((jieba_dict, 'jieba'))
ddl_pg = PROJECT_ROOT / 'data' / 'schema_postgres.sql'
if ddl_pg.exists():
    added_files.append((str(ddl_pg), 'data'))
ddl_sqlite = PROJECT_ROOT / 'src' / 'core' / 'database_sqlite.sql'
if ddl_sqlite.exists():
    added_files.append((str(ddl_sqlite), 'src/core'))

# ── Analysis ────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        # PyQt6 — UI 核心
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
        # reportlab — PDF 生成
        'reportlab', 'reportlab.graphics',
        'reportlab.pdfgen', 'reportlab.platypus',
        # sklearn — 相似病例匹配
        'sklearn.feature_extraction.text',
        'sklearn.metrics.pairwise',
        # jieba — 中文分词
        'jieba', 'jieba.posseg',
        # lunar_python — 农历/五运六气
        'lunar_python',
        # Word解析
        'docx', 'mammoth',
        # WordCloud — 方药词云
        'wordcloud',
        # 项目内部模块
        'config', 'logger', 'patch',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test',
        'pkg_resources', 'setuptools', 'pip',
        'IPython', 'jupyter',
        'scipy', 'tensorflow', 'torch',
        # Win-only: 排除 macOS 专用捆绑
        'PyQt6.QtMacExtras',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── 单文件 EXE (Windows GUI, 无控制台) ─────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='tcm_eclinic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
