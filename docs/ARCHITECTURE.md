# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 项目架构与模块说明
========================================

项目概述
--------
本项目是一款功能完善的多语种中医药门诊处方处理平台，支持中文、英文、日语三种主流语言。
平台采用现代化的架构设计，支持大数据量存储，适用于医院、诊所、科研机构等场景。

核心特性
--------
1. 多语言支持：中/英/日三国语言无缝切换
2. 大数据支持：PostgreSQL + SQLite双数据库支持
3. 处方管理：完整的处方录入、编辑、导入、导出功能
4. 高级检索：支持病种、姓名、症状、药味、时间等多维度检索
5. 数据统计：方剂云、药物高频云、诊断分布等可视化统计
6. 时间追踪：处方时间变化规律追踪、病程进展分析
7. 用户管理：完整的用户认证、权限管理、角色控制
8. 数据整合：患者档案、医师档案、科研数据整合

技术架构
--------
┌─────────────────────────────────────────────────────────────┐
│                    表现层 (UI Layer)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   PyQt6 GUI  │  │   Web API    │  │  Command CLI │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────────┤
│                    业务逻辑层 (Business Layer)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   处方管理   │  │   用户管理   │  │   统计分析   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   检索引擎   │  │   时间追踪   │  │   数据整合   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────────┤
│                    数据访问层 (Data Access Layer)            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              DatabaseManager (数据库管理器)          │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    数据存储层 (Data Storage Layer)          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   PostgreSQL │  │    SQLite    │  │    Redis     │     │
│  │  (大数据量)   │  │  (轻量级)   │  │   (缓存)     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘

目录结构
--------
tcm_eclinic/
├── config.py                    # 全局配置
├── main.py                     # 主程序入口
├── requirements.txt             # 依赖包列表
├── logger.py                   # 日志管理
├── src/
│   ├── core/                   # 核心业务模块
│   │   ├── database.py         # 数据库管理（支持PostgreSQL/SQLite）
│   │   ├── i18n.py             # 多语言国际化
│   │   ├── prescription_editor.py  # 多语言处方编辑器
│   │   ├── search_engine.py    # 高级搜索引擎
│   │   ├── statistics.py       # 统计分析引擎
│   │   ├── time_tracking.py    # 时间追踪引擎
│   │   ├── user_manager.py     # 用户管理
│   │   ├── data_integration.py # 数据整合
│   │   ├── parse_docx.py       # Word文档解析
│   │   └── similarity_engine.py # 相似度计算
│   ├── ui/                     # PyQt6图形界面
│   │   ├── gui_main.py         # 主窗口
│   │   ├── prescription_editor.py  # 处方编辑器UI
│   │   ├── similarity_strip.py    # 相似度工具条
│   │   └── log_console.py      # 日志控制台
│   ├── printing/               # 打印输出模块
│   │   ├── pdf_template.py     # PDF模板
│   │   └── print_template.py   # 打印模板
│   └── utils/                  # 工具函数
├── data/                       # 数据目录
│   ├── eclinic.db             # SQLite数据库
│   └── samples/               # 示例文件
├── output/                     # 输出目录
│   ├── logs/                  # 日志文件
│   └── reports/               # 报告输出
└── docs/                      # 文档目录

核心模块详解
============

1. 数据库模块 (database.py)
-----------------------------
功能特性：
- 支持PostgreSQL和SQLite两种数据库
- 自动创建数据表和索引
- 支持数据分页和批量操作
- 内置处方、患者、医师等数据模型

主要类：
- DatabaseManager: 数据库管理器，负责数据库连接和操作
- PrescriptionModel: 处方数据模型
- PatientModel: 患者数据模型
- CommunityModel: 社区数据模型（已移除）

使用示例：
```python
from src.core.database import db_manager, prescription_model

# 保存处方
data = {
    'patient_id': 'PT001',
    'diagnosis': '感冒',
    'diagnosis_en': 'Common Cold',
    'diagnosis_ja': '風邪',
    'chief_complaint': '发热咳嗽3天',
}
herbs = [
    {'name': '金银花', 'dose': 10, 'dose_unit': 'g'},
    {'name': '连翘', 'dose': 10, 'dose_unit': 'g'},
]
prescription_id = prescription_model.save_prescription(data, herbs)

# 搜索处方
results, total, metadata = prescription_model.search_prescriptions(
    keyword='感冒',
    language='zh_CN'
)
```

2. 多语言国际化 (i18n.py)
-------------------------
功能特性：
- 支持中/英/日三国语言
- 动态语言切换
- 统一的翻译文本管理

主要类：
- Language: 语言枚举
- I18nManager: 国际化管理器

使用示例：
```python
from src.core.i18n import Language, i18n, get_text

# 设置语言
i18n.set_language(Language.EN_US)

# 获取翻译
print(get_text('app_name'))  # "TCM Clinic Prescription Management System"
print(get_text('btn_save'))   # "Save"
```

3. 处方编辑器 (prescription_editor.py)
---------------------------------------
功能特性：
- 多语言处方录入
- 药物明细管理
- 处方验证和保存
- Word格式导出

主要类：
- MultiLanguagePrescriptionEditor: 多语言处方编辑器
- HerbItem: 药物明细项

使用示例：
```python
from src.core.prescription_editor import MultiLanguagePrescriptionEditor, HerbItem

editor = MultiLanguagePrescriptionEditor(language=Language.ZH_CN)
editor.patient_name = "张三"
editor.diagnosis = "感冒"
editor.add_herb(HerbItem(name="金银花", dose=10))
editor.add_herb(HerbItem(name="连翘", dose=10))

# 保存处方
success, result = editor.save()
if success:
    print(f"处方保存成功: {result}")
```

4. 搜索引擎 (search_engine.py)
-------------------------------
功能特性：
- 多维度高级搜索
- 自动补全建议
- 搜索历史管理
- 结果导出（JSON/CSV）

主要类：
- AdvancedSearchEngine: 高级搜索引擎
- SearchQuery: 搜索查询
- SearchCondition: 搜索条件

使用示例：
```python
from src.core.search_engine import AdvancedSearchEngine, SearchField, TimeRange

engine = AdvancedSearchEngine(language=Language.ZH_CN)
query = SearchQuery(
    keyword="感冒",
    time_range=TimeRange.LAST_30_DAYS,
    sort_by="visit_date",
    sort_order="desc"
)

results, total, metadata = engine.search(query)
print(f"找到 {total} 条记录")
```

5. 统计分析 (statistics.py)
-----------------------------
功能特性：
- 高频药材统计
- 诊断分布统计
- 时间趋势分析
- 患者统计分析
- 医师工作量统计
- 词云图表生成

主要类：
- StatisticsEngine: 统计引擎
- CloudChartGenerator: 词云图表生成器

使用示例：
```python
from src.core.statistics import statistics_engine, cloud_generator

# 获取完整统计报告
report = statistics_engine.get_full_statistics_report(
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 生成药材词云数据
herb_cloud = cloud_generator.generate_herb_cloud_data(
    report['herb_frequency']
)
```

6. 时间追踪 (time_tracking.py)
-------------------------------
功能特性：
- 患者就诊时间线
- 处方变更检测
- 病程进展分析
- 治疗方案演变追踪
- 时期对比分析

主要类：
- TimeTrackingEngine: 时间追踪引擎
- PatientTimeline: 患者时间线
- PrescriptionChange: 处方变更

使用示例：
```python
from src.core.time_tracking import time_tracking_engine

# 获取患者完整时间线
timeline = time_tracking_engine.get_patient_timeline(
    patient_id='PT001',
    start_date='2024-01-01'
)

# 分析病程进展
progression = time_tracking_engine.analyze_disease_progression(
    patient_id='PT001'
)

# 获取治疗总结
summary = time_tracking_engine.get_treatment_summary(
    patient_id='PT001'
)
```

7. 用户管理 (user_manager.py)
-------------------------------
功能特性：
- 用户注册和认证
- 密码哈希和安全
- 角色权限管理
- 用户检索和统计

主要类：
- UserManager: 用户管理器
- DoctorManager: 医师管理器
- User: 用户数据模型
- UserRole: 用户角色枚举

使用示例：
```python
from src.core.user_manager import user_manager, UserRole

# 创建用户
success, msg, user_id = user_manager.create_user(
    username='doctor1',
    password='password123',
    email='doctor@example.com',
    role='doctor',
    name='张医生'
)

# 用户登录
success, msg, user = user_manager.authenticate('doctor1', 'password123')
if success:
    print(f"欢迎, {user.name}")
```

8. 数据整合 (data_integration.py)
----------------------------------
功能特性：
- 患者完整档案整合
- 医师档案整合
- 机构统计摘要
- 科研数据导出
- 患者相似度分析
- 数据清洗工具

主要类：
- DataIntegrationEngine: 数据整合引擎
- DataCleaning: 数据清洗工具

使用示例：
```python
from src.core.data_integration import data_integration_engine

# 获取患者完整档案
patient_profile = data_integration_engine.get_patient_profile('PT001')

# 获取机构统计摘要
summary = data_integration_engine.get_institution_summary()

# 导出患者数据
data_json = data_integration_engine.export_patient_data(
    patient_id='PT001',
    format='json'
)
```

数据库设计
=========

主要数据表
----------

1. users (用户表)
   - id: 用户ID
   - username: 用户名
   - password_hash: 密码哈希
   - email: 邮箱
   - role: 角色
   - language: 语言偏好
   - name: 姓名（多语言）
   - department: 科室

2. patients (患者表)
   - id: 患者ID
   - patient_code: 患者编号
   - name: 姓名（中/英/日）
   - gender: 性别
   - age: 年龄
   - phone: 电话
   - medical_history: 病史
   - privacy_level: 隐私级别

3. prescriptions (处方主表)
   - id: 处方ID
   - prescription_code: 处方编号
   - patient_id: 患者ID
   - doctor_id: 医师ID
   - visit_date: 就诊日期
   - diagnosis: 诊断（中/英/日）
   - syndrome: 证候（中/英/日）
   - chief_complaint: 主诉（中/英/日）
   - tongue: 舌象
   - pulse: 脉象
   - treatment_method: 治法（中/英/日）
   - privacy_level: 隐私级别

4. prescription_herbs (处方药物明细表)
   - id: 记录ID
   - prescription_id: 处方ID
   - herb_name: 药材名称（中/英/日）
   - dose: 剂量
   - dose_unit: 单位
   - usage: 用法
   - processing: 炮制

5. doctors (医师表)
   - id: 医师ID
   - name: 姓名（多语言）
   - title: 职称
   - department: 科室
   - specialization: 专业特长

索引设计
--------
- idx_patients_name: 患者姓名索引
- idx_prescriptions_patient: 处方-患者索引
- idx_prescriptions_date: 处方-日期索引
- idx_prescriptions_diagnosis: 处方-诊断索引
- idx_herbs_prescription: 药物-处方索引
- idx_prescriptions_fts: 处方全文搜索索引

安装和配置
==========

环境要求
--------
- Python 3.8+
- PostgreSQL 12+ (可选，用于大数据量)
- PyQt6 6.5+

安装步骤
--------

1. 克隆项目
```bash
git clone https://github.com/corallibra/TCM_eclinic.git
cd TCM_eclinic
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置数据库
```python
# 编辑 config.py
DATABASE_CONFIG = {
    'type': 'postgresql',  # 或 'sqlite'
    'host': 'localhost',
    'port': 5432,
    'database': 'tcm_eclinic',
    'user': 'postgres',
    'password': 'your_password',
}
```

4. 运行程序
```bash
python main.py
```

依赖包列表
----------
```
python-docx>=0.8.11
mammoth>=1.6.0
pandas>=2.0.0
sqlalchemy>=2.0.0
PyQt6>=6.5.0
reportlab>=4.0.0
scikit-learn>=1.3.0
jieba>=0.42.1
psycopg2-binary>=2.9.0  # PostgreSQL驱动
```

使用指南
========

1. 处方录入
-----------
1. 打开"处方管理"模块
2. 点击"新建处方"
3. 填写患者信息和诊断信息
4. 添加药物明细
5. 点击"保存"

2. Word导入
-----------
1. 点击"导入Word医案"
2. 选择Word文档（支持.doc和.docx）
3. 系统自动解析文档内容
4. 确认并保存

3. 高级检索
-----------
1. 在搜索框输入关键词
2. 选择搜索范围（病种、姓名、症状等）
3. 设置时间范围
4. 点击"搜索"

4. 数据统计
-----------
1. 进入"统计分析"模块
2. 选择时间范围
3. 查看方剂云、药物高频云等图表

5. 时间追踪
-----------
1. 选择患者
2. 查看就诊时间线
3. 分析病程进展
4. 对比治疗方案变化

性能优化建议
============

1. 数据库优化
   - 使用PostgreSQL处理大数据量
   - 定期创建数据库索引
   - 使用分页查询避免大结果集

2. 查询优化
   - 使用缓存减少数据库查询
   - 批量操作代替循环单条操作
   - 合理使用索引字段查询

3. 内存优化
   - 大数据导出时分批处理
   - 及时释放数据库连接
   - 使用生成器处理大列表

安全建议
========

1. 密码安全
   - 使用PBKDF2哈希算法
   - 定期更换密码
   - 不使用弱密码

2. 数据隐私
   - 设置合理的隐私级别
   - 启用数据加密存储
   - 定期备份数据

3. 访问控制
   - 启用用户认证
   - 合理分配用户角色
   - 审计日志记录

扩展开发
========

添加新的数据模型
----------------

```python
from src.core.database import DatabaseManager

class MyModel:
    def __init__(self):
        self.db = DatabaseManager()
    
    def create_table(self):
        sql = """
            CREATE TABLE IF NOT EXISTS my_table (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.db.execute_update(sql)
```

添加新的API接口
---------------

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/prescriptions', methods=['GET'])
def get_prescriptions():
    from src.core.database import prescription_model
    results, total, _ = prescription_model.search_prescriptions()
    return jsonify({'data': results, 'total': total})
```

许可证和版权
============

本项目遵循自定义许可证，禁止商业使用，允许阅读和个人修改。
详细许可证条款请参阅 LICENSE.txt 文件。

联系方式
========

作者：Michael Lee
邮箱：corallibra@qq.com
GitHub：https://github.com/corallibra

更新日志
========

v2.0 (2024-01-01)
-----------------
- 新增多语言支持（中/英/日）
- 升级数据库架构支持大数据量
- 重构项目结构，模块化设计
- 新增高级搜索和统计分析功能
- 新增时间追踪和病程分析功能
- 新增用户管理和权限控制
- 移除社区交流系统

v1.0 (2023-01-01)
-----------------
- 初始版本
- 基本处方管理功能
- Word文档导入
- SQLite数据库支持
