# similarity_strip.py
# -*- coding: utf-8 -*-
"""
相似病例比较 + UI 文本输出组件（SimilarityStrip）
日志输出组件（LogConsole）
基于 TF-IDF + jieba 的 find_similar_cases() 函数
"""

import os
import sqlite3
from typing import List, Dict

from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtGui import QFont, QTextOption
from PyQt6.QtCore import pyqtSignal

# --------------------------
#  jieba / sklearn 模块加载
# --------------------------
try:
    import jieba
except Exception as e:
    raise ImportError("请先安装 jieba： pip install jieba") from e

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception as e:
    raise ImportError("请先安装 scikit-learn： pip install scikit-learn") from e


# --------------------------
#  路径 / 数据库
# --------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "eclinic.db")

# --------------------------
#  缓存结构（避免重复向量化）
# --------------------------
_cache = {
    "db_mtime": None,
    "ids": None,
    "names": None,
    "zhenghous": None,
    "prescriptions": None,
    "corpus": None,
    "vectorizer": None,
    "tfidf_matrix": None,
}

# =====================================================================
#                    -------------- UI 类 --------------
# =====================================================================

class SimilarityStrip(QTextBrowser):
    """
    原有功能：显示相似病例的输出区域（顶部 4 行）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setReadOnly(True)
        self.document().setDefaultFont(QFont("Microsoft YaHei", 10))
        self.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.setOpenExternalLinks(True)

        self.setStyleSheet("""
        QTextBrowser {
            border: 1px solid #d0d7de;
            background: #fbfbfb;
            padding: 3px;
        }
        """)

    def set_fixed_4_rows(self):
        fm = self.fontMetrics()
        h = int(fm.lineSpacing() * 4 + 10)
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)

    def push_message(self, text: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.append(f"<b>[{ts}]</b> {text}")

# =====================================================================
#             ------------ 相似病例匹配核心逻辑 ------------
# =====================================================================

def _load_cases_from_db():
    """读取 DB 全部病例"""
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, zhenghou, prescription FROM cases ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows


def _build_corpus_and_vectors():
    """读取所有病例，构建 TF-IDF 模型"""
    rows = _load_cases_from_db()

    ids, names, zhenghous, prescriptions = [], [], [], []
    corpus = []

    for cid, name, zhenghou, prescription in rows:
        ids.append(cid)
        names.append(name or "")
        zhenghous.append(zhenghou or "")
        prescriptions.append(prescription or "")

        text = (zhenghou or "") + " " + (prescription or "")
        corpus.append(text.strip())

    if not corpus:
        # 空库
        _cache.update({
            "ids": ids,
            "names": names,
            "zhenghous": zhenghous,
            "prescriptions": prescriptions,
            "corpus": corpus,
            "vectorizer": None,
            "tfidf_matrix": None,
        })
        return

    def jieba_tokenizer(text):
        return jieba.lcut(text)

    vectorizer = TfidfVectorizer(
        tokenizer=jieba_tokenizer,
        token_pattern=None,
        min_df=1
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)

    _cache.update({
        "ids": ids,
        "names": names,
        "zhenghous": zhenghous,
        "prescriptions": prescriptions,
        "corpus": corpus,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
    })


def _ensure_cache_fresh():
    """如果 DB 更新则重建 TF-IDF 缓存"""
    if not os.path.exists(DB_PATH):
        _cache.update({
            "db_mtime": None,
            "ids": [],
            "names": [],
            "zhenghous": [],
            "prescriptions": [],
            "corpus": [],
            "vectorizer": None,
            "tfidf_matrix": None,
        })
        return

    mtime = os.path.getmtime(DB_PATH)
    if _cache["db_mtime"] != mtime:
        _build_corpus_and_vectors()
        _cache["db_mtime"] = mtime


def find_similar_cases(input_text: str, topk: int = 5) -> List[Dict]:
    """主函数：返回最相似的历史病例"""
    if not input_text or not input_text.strip():
        return []

    _ensure_cache_fresh()

    corpus = _cache["corpus"]
    vectorizer = _cache["vectorizer"]
    tfidf_matrix = _cache["tfidf_matrix"]

    if not corpus or tfidf_matrix is None:
        return []

    query_vec = vectorizer.transform([input_text])
    sims = cosine_similarity(query_vec, tfidf_matrix).flatten()

    import numpy as np
    idx_sorted = np.argsort(sims)[::-1]

    results = []
    for idx in idx_sorted:
        if sims[idx] <= 0:
            break
        results.append({
            "id": _cache["ids"][idx],
            "name": _cache["names"][idx],
            "zhenghou": _cache["zhenghous"][idx],
            "prescription": _cache["prescriptions"][idx],
            "similarity": float(sims[idx])
        })
        if len(results) >= topk:
            break

    return results
