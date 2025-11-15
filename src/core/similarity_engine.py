# src/core/similarity_engine.py
# -*- coding: utf-8 -*-

import os
import sqlite3
import jieba
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "eclinic.db")

_cache = {
    "db_mtime": None,
    "ids": [],
    "names": [],
    "zhenghous": [],
    "prescriptions": [],
    "corpus": [],
    "vectorizer": None,
    "tfidf": None,
}

def _load_cases():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id,name,zhenghou,prescription FROM cases")
    rows = cur.fetchall()
    conn.close()
    return rows

def _rebuild():
    rows = _load_cases()

    ids, names, zs, pres = [], [], [], []
    corpus = []

    for r in rows:
        cid, name, zhenghou, prescription = r
        ids.append(cid)
        names.append(name or "")
        zs.append(zhenghou or "")
        pres.append(prescription or "")
        corpus.append(f"{zhenghou} {prescription}".strip())

    def jieba_cut(x): return jieba.lcut(x)

    if corpus:
        v = TfidfVectorizer(tokenizer=jieba_cut, token_pattern=None)
        tfidf = v.fit_transform(corpus)
    else:
        v = None
        tfidf = None

    _cache.update({
        "ids": ids,
        "names": names,
        "zhenghous": zs,
        "prescriptions": pres,
        "corpus": corpus,
        "vectorizer": v,
        "tfidf": tfidf,
        "db_mtime": os.path.getmtime(DB_PATH),
    })

def _ensure():
    if not os.path.exists(DB_PATH):
        return
    mtime = os.path.getmtime(DB_PATH)
    if _cache["db_mtime"] != mtime:
        _rebuild()

def find_similar_cases(text: str, topk: int = 5) -> List[Dict]:
    _ensure()

    v = _cache["vectorizer"]
    tfidf = _cache["tfidf"]
    corpus = _cache["corpus"]

    if not v or not tfidf or not corpus:
        return []

    q = v.transform([text])
    sims = cosine_similarity(q, tfidf).flatten()

    import numpy as np
    idx = np.argsort(sims)[::-1]

    results = []
    for i in idx:
        if sims[i] <= 0:
            break
        results.append({
            "id": _cache["ids"][i],
            "name": _cache["names"][i],
            "zhenghou": _cache["zhenghous"][i],
            "prescription": _cache["prescriptions"][i],
            "similarity": float(sims[i]),
        })
        if len(results) >= topk:
            break

    return results
