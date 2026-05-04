# 中医药门诊处方处理平台

[![License](https://img.shields.io/badge/License-Custom-blue.svg)](LICENSE.txt)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.x-orange.svg)](https://riverbankcomputing.com/software/pyqt/intro)

---

## ⚠️ 重要声明

**本项目禁止商用，允许阅读和个人修改，任何使用需获得作者授权！**  
**This project is strictly non-commercial. Reading and personal modifications are allowed only. Any use requires author authorization!**

---

## 📋 项目简介

**TCM_eclinic** 是一款功能完善的**多语种中医药门诊处方处理平台**，采用现代化的 Python + PyQt6 技术栈开发。系统支持**中文、英文、日语**三种主流语言，适用于医院中医门诊、诊所、科研机构等场景。

### 核心特点

✨ **多语言支持** - 中/英/日三国语言无缝切换，满足国际化需求  
🚀 **大数据支持** - PostgreSQL + SQLite 双数据库架构，轻松应对大数据量  
📊 **智能统计** - 方剂云、药物高频云、诊断分布等可视化分析  
🔍 **高级检索** - 病种、姓名、症状、药味、时间等多维度精准检索  
⏱️ **时间追踪** - 处方时间变化规律追踪，病程进展一目了然  
👥 **用户管理** - 完整的用户认证、权限管理、角色控制  
📄 **数据整合** - 患者档案、医师档案、科研数据一站式整合  

---

## 🎯 核心功能

### 1. 处方管理
- ✅ 支持多语言处方录入（中/英/日）
- ✅ 历史 Word 处方智能导入
- ✅ 处方编辑、修改、删除
- ✅ 处方 PDF 导出与打印
- ✅ 药物剂量自动校验

### 2. 高级检索
- ✅ 按病种检索
- ✅ 按患者姓名检索
- ✅ 按症状检索
- ✅ 按药味检索
- ✅ 按时间范围检索
- ✅ 多条件组合检索
- ✅ 自动补全建议
- ✅ 搜索历史管理

### 3. 数据统计
- 📈 **中药方剂云** - 可视化展示常用方剂
- 📈 **中药高频药物云** - 高频使用药材统计
- 📈 **诊断分布图** - 病种分布统计
- 📈 **时间趋势分析** - 处方数量随时间变化
- 📈 **患者统计分析** - 患者性别、年龄分布
- 📈 **医师工作量统计** - 各医师接诊情况

### 4. 时间追踪
- 📅 患者就诊时间线
- 🔄 处方变更自动检测
- 📊 病程进展分析
- 💊 治疗方案演变追踪
- ⚖️ 治疗时期对比分析
- 📋 治疗总结报告生成

### 5. 用户管理
- 👤 用户注册与认证
- 🔐 密码安全（PBKDF2 哈希）
- 🎭 角色权限控制（管理员/医师/护士/研究员）
- 👨‍⚕️ 医师档案管理
- 📊 用户检索与统计

### 6. 数据整合
- 📁 患者完整档案
- 👨‍⚕️ 医师完整档案
- 🏥 机构统计摘要
- 📊 科研数据导出
- 🔗 患者相似度分析
- 🧹 数据清洗工具

---

## 🏗️ 技术架构

### 系统架构图

```
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
```

### 核心技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| **表现层** | PyQt6 | 跨平台桌面应用框架 |
| **业务层** | Python 3.8+ | 核心业务逻辑处理 |
| **数据层** | SQLAlchemy | ORM 数据库抽象 |
| **存储层** | PostgreSQL/SQLite | 关系型数据库 |
| **工具** | pandas, numpy | 数据处理与分析 |
| **可视化** | matplotlib, wordcloud | 图表与词云生成 |

---

## 📦 安装部署

### 环境要求

- 🐍 Python 3.8 或更高版本
- 🖥️ Windows / macOS / Linux
- 💾 PostgreSQL 12+ (可选，用于大数据量)
- 🖼️ PyQt6 6.5+

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/corallibra/TCM_eclinic.git
cd TCM_eclinic
```

#### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置数据库

编辑 `config.py` 文件：

```python
# 数据库配置
DATABASE_CONFIG = {
    'type': 'postgresql',  # 或 'sqlite'
    'sqlite_path': 'data/eclinic.db',
    
    # PostgreSQL 配置（大数据量时使用）
    'pg_host': 'localhost',
    'pg_port': 5432,
    'pg_database': 'tcm_eclinic',
    'pg_user': 'postgres',
    'pg_password': 'your_password',
}
```

#### 5. 运行程序

```bash
python main.py
```

### Docker 部署（可选）

```bash
# 构建镜像
docker build -t tcm-eclinic .

# 运行容器
docker run -d -p 5000:5000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/tcm \
  tcm-eclinic
```

---

## 📖 使用指南

### 1. 处方录入

#### 手动录入
1. 打开"处方管理"模块
2. 点击"新建处方"按钮
3. 填写患者基本信息
4. 选择语言（中文/英文/日文）
5. 填写诊断、证候、主诉等信息
6. 添加药物明细（名称、剂量、单位）
7. 点击"保存"

#### Word 导入
1. 点击"导入 Word 医案"
2. 选择 Word 文档（支持 .doc 和 .docx）
3. 系统自动解析文档内容
4. 预览并确认解析结果
5. 批量导入或选择部分记录

### 2. 高级检索

1. 在搜索框输入关键词
2. 选择搜索范围：
   - 📋 按病种
   - 👤 按姓名
   - 🤒 按症状
   - 🌿 按药味
   - 📅 按时间
3. 设置时间范围（今天/本周/本月/自定义）
4. 点击"搜索"
5. 查看搜索结果

### 3. 数据统计

1. 进入"统计分析"模块
2. 选择时间范围
3. 查看各类统计图表：
   - 📊 中药方剂云
   - 🌿 中药高频药物云
   - 🏥 病种分布图
   - 📈 时间趋势图
4. 导出统计报告

### 4. 时间追踪

1. 选择患者
2. 查看就诊时间线
3. 分析病程进展
4. 查看治疗方案变化
5. 生成治疗总结报告

### 5. 用户管理

#### 创建用户
1. 进入"用户管理"模块
2. 点击"新建用户"
3. 填写用户名、密码、邮箱
4. 选择用户角色
5. 填写个人信息
6. 点击"创建"

#### 权限设置
- 🔧 **管理员**：系统管理、用户管理、数据管理
- 👨‍⚕️ **医师**：处方管理、患者管理、统计查看
- 👩‍⚕️ **护士**：处方录入、打印
- 🔬 **研究员**：数据查看、导出、分析

---

## 📂 项目结构

```
tcm_eclinic/
├── config.py                    # 全局配置文件
├── main.py                     # 主程序入口
├── requirements.txt             # 依赖包列表
├── logger.py                   # 日志管理模块
├── README.md                   # 项目说明文档
├── LICENSE.txt                 # 许可证文件
│
├── src/                        # 源代码目录
│   ├── core/                   # 核心业务模块
│   │   ├── __init__.py
│   │   ├── database.py         # 数据库管理（PostgreSQL/SQLite）
│   │   ├── i18n.py             # 多语言国际化（中/英/日）
│   │   ├── prescription_editor.py  # 多语言处方编辑器
│   │   ├── search_engine.py    # 高级搜索引擎
│   │   ├── statistics.py       # 统计分析引擎
│   │   ├── time_tracking.py    # 时间追踪引擎
│   │   ├── user_manager.py     # 用户管理模块
│   │   ├── data_integration.py # 数据整合模块
│   │   ├── parse_docx.py       # Word 文档解析
│   │   └── similarity_engine.py # 相似度计算
│   │
│   ├── ui/                     # PyQt6 图形界面
│   │   ├── __init__.py
│   │   ├── gui_main.py         # 主窗口
│   │   ├── prescription_editor.py  # 处方编辑器 UI
│   │   ├── similarity_strip.py    # 相似度工具条
│   │   └── log_console.py      # 日志控制台
│   │
│   ├── printing/               # 打印输出模块
│   │   ├── __init__.py
│   │   ├── pdf_template.py     # PDF 模板
│   │   └── print_template.py   # 打印模板
│   │
│   └── utils/                  # 工具函数
│       └── __init__.py
│
├── data/                       # 数据目录
│   ├── eclinic.db              # SQLite 数据库
│   └── samples/                # 示例文件
│
├── output/                     # 输出目录
│   ├── logs/                   # 日志文件
│   └── reports/                # 报告输出
│
└── docs/                       # 文档目录
    └── ARCHITECTURE.md         # 架构详细文档
```

---

## 🗄️ 数据库设计

### 主要数据表

#### 1. users（用户表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 用户ID（主键） |
| username | VARCHAR(100) | 用户名（唯一） |
| password_hash | VARCHAR(255) | 密码哈希 |
| email | VARCHAR(255) | 邮箱 |
| role | VARCHAR(50) | 角色 |
| language | VARCHAR(10) | 语言偏好 |
| name | VARCHAR(100) | 姓名（中文） |
| name_en | VARCHAR(100) | 姓名（英文） |
| name_ja | VARCHAR(100) | 姓名（日文） |
| department | VARCHAR(100) | 科室 |
| created_at | TIMESTAMP | 创建时间 |

#### 2. patients（患者表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 患者ID（主键） |
| patient_code | VARCHAR(50) | 患者编号（唯一） |
| name | VARCHAR(100) | 姓名 |
| name_en | VARCHAR(100) | 英文名 |
| name_ja | VARCHAR(100) | 日文名 |
| gender | VARCHAR(10) | 性别 |
| age | INTEGER | 年龄 |
| phone | VARCHAR(50) | 电话 |
| medical_history | TEXT | 病史 |
| allergies | TEXT | 过敏史 |
| privacy_level | VARCHAR(20) | 隐私级别 |

#### 3. prescriptions（处方主表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 处方ID（主键） |
| prescription_code | VARCHAR(50) | 处方编号（唯一） |
| patient_id | VARCHAR(50) | 患者ID（外键） |
| doctor_id | VARCHAR(50) | 医师ID（外键） |
| visit_date | TIMESTAMP | 就诊日期 |
| diagnosis | TEXT | 诊断（中文） |
| diagnosis_en | TEXT | 诊断（英文） |
| diagnosis_ja | TEXT | 诊断（日文） |
| syndrome | TEXT | 证候（中文） |
| syndrome_en | TEXT | 证候（英文） |
| syndrome_ja | TEXT | 证候（日文） |
| chief_complaint | TEXT | 主诉（中文） |
| tongue | VARCHAR(100) | 舌象 |
| pulse | VARCHAR(100) | 脉象 |
| treatment_method | TEXT | 治法 |
| privacy_level | VARCHAR(20) | 隐私级别 |

#### 4. prescription_herbs（处方药物明细表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 记录ID（主键） |
| prescription_id | VARCHAR(50) | 处方ID（外键） |
| herb_name | VARCHAR(100) | 药材名称（中文） |
| herb_name_en | VARCHAR(100) | 药材名称（英文） |
| herb_name_ja | VARCHAR(100) | 药材名称（日文） |
| dose | REAL | 剂量 |
| dose_unit | VARCHAR(20) | 单位 |
| usage | TEXT | 用法 |
| processing | VARCHAR(50) | 炮制 |
| sort_order | INTEGER | 排序 |

#### 5. doctors（医师表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 医师ID（主键） |
| name | VARCHAR(100) | 姓名 |
| title | VARCHAR(50) | 职称 |
| department | VARCHAR(100) | 科室 |
| specialization | TEXT | 专业特长 |
| bio | TEXT | 个人简介 |

### 索引设计

```sql
-- 患者姓名索引
CREATE INDEX idx_patients_name ON patients(name);

-- 处方-患者索引
CREATE INDEX idx_prescriptions_patient ON prescriptions(patient_id);

-- 处方-日期索引
CREATE INDEX idx_prescriptions_date ON prescriptions(visit_date);

-- 处方-诊断索引
CREATE INDEX idx_prescriptions_diagnosis ON prescriptions(diagnosis);

-- 药物-处方索引
CREATE INDEX idx_herbs_prescription ON prescription_herbs(prescription_id);

-- 处方全文搜索索引
CREATE INDEX idx_prescriptions_fts ON prescriptions(diagnosis, syndrome);
```

---

## 🔧 配置说明

### 数据库配置

编辑 `config.py` 文件：

```python
# 数据库类型：'sqlite' 或 'postgresql'
DATABASE_TYPE = 'sqlite'

# SQLite 配置
SQLITE_PATH = 'data/eclinic.db'

# PostgreSQL 配置（大数据量时使用）
POSTGRESQL_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'tcm_eclinic',
    'user': 'postgres',
    'password': 'your_password',
    'pool_size': 10,
    'max_overflow': 20,
}
```

### 语言配置

```python
# 默认语言：'zh_CN' / 'en_US' / 'ja_JP'
DEFAULT_LANGUAGE = 'zh_CN'
```

### 日志配置

```python
# 日志级别：DEBUG / INFO / WARNING / ERROR
LOG_LEVEL = 'INFO'

# 日志文件路径
LOG_FILE = 'output/logs/app.log'

# 日志保留天数
LOG_RETENTION_DAYS = 30
```

---

## 📊 API 接口

系统提供 RESTful API 接口，支持二次开发和系统集成。

### 基础信息

- 基础 URL：`http://localhost:5000/api`
- 数据格式：JSON
- 认证方式：Bearer Token

### 主要接口

#### 处方管理

```
GET    /api/prescriptions          # 获取处方列表
GET    /api/prescriptions/:id      # 获取单个处方
POST   /api/prescriptions          # 创建处方
PUT    /api/prescriptions/:id      # 更新处方
DELETE /api/prescriptions/:id      # 删除处方
GET    /api/prescriptions/search  # 搜索处方
```

#### 患者管理

```
GET    /api/patients               # 获取患者列表
GET    /api/patients/:id           # 获取单个患者
POST   /api/patients               # 创建患者
PUT    /api/patients/:id           # 更新患者
DELETE /api/patients/:id           # 删除患者
GET    /api/patients/:id/profile  # 获取患者档案
```

#### 统计分析

```
GET    /api/stats/summary          # 统计摘要
GET    /api/stats/herbs            # 药物统计
GET    /api/stats/diagnoses        # 诊断统计
GET    /api/stats/timeline         # 时间趋势
```

#### 用户管理

```
POST   /api/auth/login             # 用户登录
POST   /api/auth/logout            # 用户登出
GET    /api/users                  # 获取用户列表
GET    /api/users/:id              # 获取用户信息
POST   /api/users                  # 创建用户
PUT    /api/users/:id              # 更新用户
```

### 调用示例

```bash
# 登录
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "doctor1", "password": "password123"}'

# 获取处方列表
curl http://localhost:5000/api/prescriptions \
  -H "Authorization: Bearer <token>"

# 创建处方
curl -X POST http://localhost:5000/api/prescriptions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PT001",
    "diagnosis": "感冒",
    "diagnosis_en": "Common Cold",
    "diagnosis_ja": "風邪",
    "chief_complaint": "发热咳嗽3天"
  }'
```

---

## 🧪 开发指南

### 添加新的数据模型

```python
# src/core/new_model.py
from src.core.database import DatabaseManager

class NewModel:
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
    
    def save(self, data):
        # 保存数据
        pass
```

### 添加新的 API 接口

```python
# api/new_api.py
from flask import Blueprint, jsonify
from src.core.database import prescription_model

new_api = Blueprint('new_api', __name__)

@new_api.route('/api/new_endpoint', methods=['GET'])
def get_data():
    results = prescription_model.search_prescriptions()
    return jsonify({'data': results})
```

### 添加新的 UI 组件

```python
# src/ui/new_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class NewWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("New Component"))
        self.setLayout(layout)
```

---

## ⚡ 性能优化

### 数据库优化

1. **使用 PostgreSQL 处理大数据量**
   ```python
   DATABASE_TYPE = 'postgresql'
   POSTGRESQL_CONFIG = {
       'pool_size': 20,
       'max_overflow': 40,
   }
   ```

2. **定期创建索引**
   ```sql
   ANALYZE;
   REINDEX;
   ```

3. **使用分页查询**
   ```python
   # 避免大结果集
   results = model.search(query, limit=100, offset=0)
   ```

### 查询优化

1. **使用缓存**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_stats():
       return statistics_engine.get_full_statistics_report()
   ```

2. **批量操作**
   ```python
   # ❌ 低效
   for item in items:
       model.save(item)
   
   # ✅ 高效
   model.batch_save(items)
   ```

### 内存优化

1. **大数据导出分批处理**
   ```python
   for batch in batches:
       export_batch(batch)
   ```

2. **及时释放资源**
   ```python
   conn.close()
   del large_data
   ```

---

## 🔒 安全建议

### 密码安全

- ✅ 使用 PBKDF2 哈希算法
- ✅ 定期更换密码
- ✅ 不使用弱密码（长度≥8位，包含字母和数字）

### 数据隐私

- ✅ 设置合理的隐私级别（public/private/doctor_only）
- ✅ 启用数据加密存储
- ✅ 定期备份数据

### 访问控制

- ✅ 启用用户认证
- ✅ 合理分配用户角色
- ✅ 审计日志记录

---

## 📝 更新日志

### v2.0 (2024-01-01)

✨ **新功能**
- 新增多语言支持（中/英/日）
- 升级数据库架构支持大数据量（PostgreSQL）
- 重构项目结构，模块化设计
- 新增高级搜索和统计分析功能
- 新增时间追踪和病程分析功能
- 新增用户管理和权限控制
- 新增数据整合和科研支持
- 新增 RESTful API 接口

🔧 **改进**
- 优化数据库索引设计
- 改进处方解析算法
- 增强数据验证和校验
- 提升系统安全性能

⚠️ **移除**
- 移除社区交流系统

### v1.0 (2023-01-01)

- ✅ 初始版本发布
- ✅ 基本处方管理功能
- ✅ Word 文档导入
- ✅ SQLite 数据库支持
- ✅ PyQt6 图形界面

---

## 📄 许可证

本项目遵循**自定义许可证**：

| 行为 | 是否允许 |
|------|----------|
| 阅读源码 | ✅ 允许 |
| 本地修改 | ✅ 允许 |
| 发布修改版 | ❌ 禁止 |
| 商业使用 | ❌ 禁止 |
| 复制/转载/分发 | ✅ 允许 |
| 使用需授权 | ✅ 必须 |

详细许可证条款请参阅 [LICENSE.txt](LICENSE.txt) 文件。

---

## 📧 联系方式

**作者：Michael Lee**  
**邮箱：corallibra@qq.com**  
**GitHub：https://github.com/corallibra**

---

## 🙏 致谢

感谢所有为项目做出贡献的开发者！

- 使用 [PyQt6](https://riverbankcomputing.com/software/pyqt/intro) 构建 GUI
- 使用 [SQLAlchemy](https://www.sqlalchemy.org/) 实现 ORM
- 使用 [jieba](https://github.com/fxsjy/jieba) 实现中文分词
- 使用 [scikit-learn](https://scikit-learn.org/) 实现相似度计算
- 使用 [pandas](https://pandas.pydata.org/) 处理数据
- 使用 [matplotlib](https://matplotlib.org/) 生成图表

---

## ⭐ 支持项目

如果这个项目对您有帮助，请给我们一个 ⭐！

```bash
git clone https://github.com/corallibra/TCM_eclinic.git
cd TCM_eclinic
git star
```

---

**© 2024 Michael Lee. All rights reserved.**
