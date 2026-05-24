# -*- coding: utf-8 -*-
"""TCM_eclinic 核心模块包（v2.0 PostgreSQL）

模块列表：
1. database.py      - PostgreSQL + SQLite 数据库管理器 (新架构)
2. parse_docx.py    - Word 处方解析器
3. prescription_editor.py - 处方编辑器
4. search_engine.py - 语义相似度搜索
5. similarity_engine.py - TCM 证候相似案例推荐

新增模块:
- herb_dose_rules.py       - 药材剂量验证规则 (防止超量)
- import_words_to_postgres.py - Word → PostgreSQL 批量导入工具
- backup_manager.py        - 数据库自动备份管理
"""

# 当前版本
__version__ = "2.0.0-postgres-ready"
