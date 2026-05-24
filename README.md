# 中医门诊处方处理平台 / TCM EClinic Platform / 中医外来処方処理プラットフォーム

[![License](https://img.shields.io/badge/License-Custom-blue.svg)](LICENSE.txt)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.x-orange.svg)](https://riverbankcomputing.com/software/pyqt/intro)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)

---

## 重要声明 / Disclaimer / 重要声明

**中文**：本项目禁止商用。允许阅读和个人修改，任何使用需获得作者授权。

**English**：This project is strictly non-commercial. Reading and personal modifications are allowed only. Any use requires author authorization.

**日本語**：本プロジェクトの商用利用を禁止します。閲覧および個人的な改変は許可されます。使用には著作者の許可が必要です。

---

## 项目简介 / Overview / 概要

**中文**：TCM_eclinic 是一款中医药门诊处方处理桌面应用，基于 Python + PyQt6 构建，支持 PostgreSQL / SQLite 双数据库架构，内置多语言处方录入、Word 智能导入、高级检索、数据统计、五运六气等功能。

**English**：TCM_eclinic is a desktop application for TCM outpatient prescription management, built with Python + PyQt6, featuring PostgreSQL / SQLite dual-database architecture, multi-language prescription entry, intelligent Word import, advanced search, statistics, and traditional Chinese medicine chronology (Wuyun Liuqi).

**日本語**：TCM_eclinic は、Python + PyQt6 で構築された中医外来処方管理デスクトップアプリケーションです。PostgreSQL / SQLite のデュアルデータベース、多言語処方入力、Word インポート、高度な検索、統計分析、五運六気などの機能を備えています。

### 核心功能 / Key Features / 主な機能

| 功能 Feature 機能 | 说明 Description 説明 |
|---|---|
| 处方管理 Prescription Mgmt 処方管理 | 多语言录入（中/英/日）、Word 智能导入、PDF 导出打印 |
| 高级检索 Advanced Search 高度検索 | 按病种/姓名/症状/药味/时间多维度组合检索 |
| 数据统计 Statistics 統計 | 方剂词云、高频药物统计、诊断分布、时间趋势 |
| 时间追踪 Timeline タイムライン | 患者就诊时间线、病程进展、治疗方案演变追踪 |
| 五运六气 Wuyun Liuqi 五運六気 | 节气、司天、在泉、主运、主气自动推算 |
| 数据整合 Data Integration データ統合 | 患者档案、医师档案、相似病例匹配 |

---

## 快速开始 / Quick Start / クイックスタート

### 环境要求 / Requirements / 要件

| | |
|---|---|
| Python | 3.10+ |
| OS | Windows / macOS / Linux |
| DB | PostgreSQL 16（可选 / optional / 任意） 或 SQLite |

### 一键安装 / One-Click Setup / ワンクリックセットアップ

```bash
git clone https://github.com/corallibra/TCM_eclinic.git
cd TCM_eclinic
./setup.sh
source venv/bin/activate
python main.py
```

`setup.sh` 提供三种数据库模式 / Three DB modes / 3つのDBモード：

| 模式 Mode モード | 说明 Description 説明 |
|---|---|
| Docker PostgreSQL | 自动拉取 postgres:16-alpine，全平台通用 |
| 本地 PostgreSQL | 使用系统已安装的 PostgreSQL |
| SQLite | 零外部依赖，数据存储在 `data/eclinic.db` |

### 手动安装 / Manual Setup / 手動セットアップ

```bash
# 1. 创建虚拟环境 / Create venv / 仮想環境を作成
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows

# 2. 安装依赖 / Install dependencies / 依存関係をインストール
pip install -r requirements.txt

# 3. 配置 / Configure / 設定
cp .env.example .env
# 编辑 .env 设置数据库连接参数

# 4. 启动数据库（仅 PostgreSQL 模式）
# Option A: Docker
docker compose up -d
# Option B: 本地安装 / Local install
brew install postgresql@16 && brew services start postgresql@16
createdb tcm_eclinic_db
psql -U postgres -d tcm_eclinic_db -f data/schema_postgres.sql

# 5. 运行 / Run / 実行
python main.py
```

### 配置参考 / Config Reference / 設定リファレンス

```bash
# .env
DB_TYPE=postgres              # postgres | sqlite
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=tcm_eclinic_db
PG_USER=postgres
PG_PASSWORD=
```

---

## 项目结构 / Project Structure / プロジェクト構造

```
tcm_eclinic/
├── main.py                    # 主入口 / Entry point / エントリポイント
├── config.py                  # 全局配置 / Global config / 全体設定
├── logger.py                  # 日志模块 / Logging / ログモジュール
├── setup.sh                   # 一键安装脚本 / Setup script / セットアップ
├── requirements.txt           # 依赖清单 / Dependencies / 依存関係
├── Dockerfile                 # CLI 工具镜像 / CLI image / CLIイメージ
├── docker-compose.yml         # PostgreSQL 容器 / PG container / PGコンテナ
│
├── src/
│   ├── core/                  # 业务逻辑 / Business logic / ビジネスロジック
│   │   ├── database.py        #   PostgreSQL/SQLite 数据库管理
│   │   ├── db.py              #   SQLite 快速接口
│   │   ├── parse_docx.py      #   Word 文档解析
│   │   ├── similarity_engine.py  # 相似病例匹配
│   │   ├── backup_manager.py  #   自动备份
│   │   └── ...                #   检索引擎、统计、用户管理等
│   │
│   ├── ui/                    # PyQt6 界面 / GUI / GUI
│   │   ├── gui_main.py        #   主窗口
│   │   ├── prescription_editor.py  # 处方编辑器
│   │   ├── print_tab.py       #   打印与预览
│   │   ├── similarity_strip.py    # 相似病例条
│   │   └── log_console.py     #   日志控制台
│   │
│   └── printing/              # PDF 生成 / PDF output / PDF出力
│       ├── pdf_template.py
│       └── print_template.py
│
├── data/
│   ├── schema_postgres.sql    # PostgreSQL DDL
│   └── init_postgres_docker.sql  # Docker 初始化 SQL
│
└── output/                    # 日志与导出 / Logs & exports / ログと出力
```

---

## 使用说明 / Usage / 使い方

### 处方录入 / Prescription Entry / 処方入力

1. 切换到「处方编辑与打印」标签页
2. 填写处方基本信息：姓名、性别、年龄、电话、地址
3. 选择剂型（颗粒剂/饮片）和煎药方式
4. 填写诊断、证候、主诉、舌象、脉象等
5. 在中药处方表中录入药名和剂量
6. 右侧实时预览，确认后打印或保存

### Word 导入 / Word Import / Word インポート

1. 点击「导入 Word 医案」
2. 选择 .docx 或 .doc 文件（支持批量）
3. 系统自动解析患者信息、诊断、药物明细
4. 预览确认后导入数据库

### 检索查询 / Search / 検索

1. 切换到「医案查询检索」标签页
2. 输入关键词（姓名/病种/症状/药味）
3. 选择时间范围
4. 在结果列表中查看匹配处方，点击查看详情

---

## 许可证 / License / ライセンス

本项目遵循自定义许可证，详见 [LICENSE.txt](LICENSE.txt)。

**中文**：允许阅读源码和个人修改。禁止商业使用，禁止发布修改版。任何使用需作者授权。

**English**：Source code reading and personal modifications allowed. Commercial use and redistribution of modified versions are prohibited. Any use requires author authorization.

**日本語**：ソースコードの閲覧と個人的な改変は許可されます。商用利用および修正版の再配布は禁止します。使用には著作者の許可が必要です。

---

## 联系方式 / Contact / 連絡先

- **作者 / Author / 著者**：Michael Lee（李玉贤工作室）
- **邮箱 / Email / メール**：corallibra@qq.com
- **GitHub**：https://github.com/corallibra

---

**© 2024 Michael Lee. All rights reserved.**
