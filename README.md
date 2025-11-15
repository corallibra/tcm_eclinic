# TCM_eclinic

[![License](https://img.shields.io/badge/License-Custom-blue.svg)](LICENSE.txt)
[![Python](https://img.shields.io/badge/Python-3.12-green.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.x-orange.svg)](https://riverbankcomputing.com/software/pyqt/intro)
[![Last Commit](https://img.shields.io/github/last-commit/<你的用户名>/TCM_eclinic?color=green)](https://github.com/<你的用户名>/TCM_eclinic/commits/main)
[![GitHub Release](https://img.shields.io/github/v/release/<你的用户名>/TCM_eclinic?color=blue)](https://github.com/<你的用户名>/TCM_eclinic/releases)

---

## ⚠️ 注意 / Warning

**本项目禁止商用，允许阅读和个人修改，任何使用需获得作者授权！**  
**This project is strictly non-commercial. Reading and personal modifications are allowed only. Any use requires author authorization!**

---

## 项目简介 / Project Overview

**TCM_eclinic** 是一个面向中医医案研究与数字化管理的 Python + PyQt6 桌面应用。  
**TCM_eclinic** is a Python + PyQt6 desktop application for digital management and research of TCM (Traditional Chinese Medicine) medical cases.

**目标 / Goals:**

- 数字化整理和分析中医医案数据 / Digitally organize and analyze TCM medical case data  
- 支持医案文本解析、相似度检索与统计分析 / Support text parsing, similarity search, and statistical analysis  
- 提供直观的图形界面操作 / Provide intuitive GUI operation  
- 实现医案数据的导入、导出、打印模板管理 / Enable import/export and template-based printing of cases  
- 辅助中医科研人员快速处理与查阅医案 / Assist TCM researchers in quickly processing and reviewing cases  

---

## 核心功能 / Features

### 1. 完整医案数据管理 / Full Case Data Management
- 支持 docx 文档解析 / Parse docx documents  
- 自动生成数据库并支持检索 / Auto-generate DB and support query  

### 2. 智能相似度分析 / Intelligent Similarity Analysis
- TF-IDF + jieba 算法 / TF-IDF + jieba algorithm  
- 快速匹配相似医案 / Quickly find similar cases  

### 3. GUI 可视化操作 / GUI Visualization
- PyQt6 构建 / Built with PyQt6  
- 医案浏览、编辑、打印和日志模块 / Case browsing, editing, printing, and logging  

### 4. 打印模板管理 / Print Template Management
- PDF / 文档模板统一管理 / Unified management of PDF/document templates  
- 自定义医案打印格式 / Customizable print format  

### 5. 安全与日志 / Security and Logging
- 日志记录操作历史 / Record operation logs  
- 自动处理缓存和备份文件 / Auto-handle cache and backup files  

---

## 项目截图 / Screenshots


![主界面](docs/screenshot_main.png)
![分析模块](docs/screenshot_analysis.png)
![打印模板](docs/screenshot_print.png)

---

## 使用规则 / Usage Rules

| 行为 / Action | 是否允许 / Allowed |
|----------------|------------------|
| 阅读源码 / Read source code | ✅ 允许 / Allowed |
| 本地修改 / Local modification | ✅ 允许 / Allowed |
| 发布修改版 / Publish modifications | ❌ 禁止 / Forbidden |
| 商业使用 / Commercial use | ❌ 禁止 / Forbidden |
| 复制/转载/分发 / Copy & redistribute | ✅ 允许 / Allowed |
| 使用需授权 / Requires permission | ✅ 必须 / Required |

> 详细授权条款请参阅 [LICENSE.txt](LICENSE.txt) / See [LICENSE.txt](LICENSE.txt) for detailed terms.

---

## 联系方式 / Contact

**Michael Lee**  
Email: `corallibra@qq.com`  
GitHub: [https://github.com/corallibra](https://github.com/corallibra)

---

## 快速开始 / Quick Start

1. 克隆仓库 / Clone the repository:  
```bash
git clone https://github.com/corallibra/TCM_eclinic.git
