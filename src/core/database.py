# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 数据库模块
支持SQLite和PostgreSQL，适合大数据量存储
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib

# -------------------------------
# 配置管理
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

SQLITE_PATH = os.path.join(DATA_DIR, "eclinic.db")

class DatabaseType(Enum):
    """数据库类型枚举"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

@dataclass
class DatabaseConfig:
    """数据库配置"""
    db_type: DatabaseType = DatabaseType.SQLITE
    sqlite_path: str = SQLITE_PATH
    
    # PostgreSQL配置
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "tcm_eclinic"
    pg_user: str = "postgres"
    pg_password: str = ""
    
    # 连接池配置
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._connection = None
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        if self.config.db_type == DatabaseType.SQLITE:
            self._init_sqlite()
        elif self.config.db_type == DatabaseType.POSTGRESQL:
            self._init_postgresql()
    
    def _get_sqlite_connection(self):
        """获取SQLite连接"""
        conn = sqlite3.connect(self.config.sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB缓存
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn
    
    def _init_sqlite(self):
        """初始化SQLite数据库"""
        conn = self._get_sqlite_connection()
        
        # 用户表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'doctor',
                language TEXT DEFAULT 'zh_CN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 患者表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                patient_code TEXT UNIQUE,
                name TEXT NOT NULL,
                name_en TEXT,
                name_ja TEXT,
                gender TEXT,
                age INTEGER,
                phone TEXT,
                email TEXT,
                address TEXT,
                medical_history TEXT,
                allergies TEXT,
                notes TEXT,
                privacy_level TEXT DEFAULT 'private',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # 医师表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_en TEXT,
                name_ja TEXT,
                title TEXT,
                department TEXT,
                specialization TEXT,
                phone TEXT,
                email TEXT,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 处方主表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                id TEXT PRIMARY KEY,
                prescription_code TEXT UNIQUE NOT NULL,
                patient_id TEXT NOT NULL,
                doctor_id TEXT,
                visit_date TIMESTAMP NOT NULL,
                diagnosis TEXT,
                diagnosis_en TEXT,
                diagnosis_ja TEXT,
                syndrome TEXT,
                syndrome_en TEXT,
                syndrome_ja TEXT,
                chief_complaint TEXT,
                chief_complaint_en TEXT,
                chief_complaint_ja TEXT,
                symptoms TEXT,
                symptoms_en TEXT,
                symptoms_ja TEXT,
                tongue TEXT,
                tongue_en TEXT,
                tongue_ja TEXT,
                pulse TEXT,
                pulse_en TEXT,
                pulse_ja TEXT,
                treatment_method TEXT,
                treatment_method_en TEXT,
                treatment_method_ja TEXT,
                notes TEXT,
                status TEXT DEFAULT 'active',
                privacy_level TEXT DEFAULT 'doctor_only',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # 处方药物明细表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prescription_herbs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prescription_id TEXT NOT NULL,
                herb_id TEXT,
                herb_name TEXT NOT NULL,
                herb_name_en TEXT,
                herb_name_ja TEXT,
                dose REAL NOT NULL,
                dose_unit TEXT DEFAULT 'g',
                dose_unit_en TEXT DEFAULT 'g',
                dose_unit_ja TEXT DEFAULT 'g',
                usage TEXT,
                usage_en TEXT,
                usage_ja TEXT,
                processing TEXT,
                processing_en TEXT,
                processing_ja TEXT,
                source TEXT,
                barcode TEXT,
                manufacturer TEXT,
                quality_grade TEXT,
                price REAL,
                currency TEXT DEFAULT 'CNY',
                sort_order INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE
            )
        """)
        
        # 药材数据库表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS herbs (
                id TEXT PRIMARY KEY,
                name_zh TEXT NOT NULL,
                name_en TEXT,
                name_ja TEXT,
                latin_name TEXT,
                pinyin TEXT,
                pinyin_initial TEXT,
                category TEXT,
                properties TEXT,
                flavor TEXT,
                channel_entrance TEXT,
                functions TEXT,
                indications TEXT,
                dosage TEXT,
                contraindications TEXT,
                warnings TEXT,
                storage TEXT,
                image_url TEXT,
                barcode TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 病种分类表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS diseases (
                id TEXT PRIMARY KEY,
                name_zh TEXT NOT NULL,
                name_en TEXT,
                name_ja TEXT,
                icd_code TEXT,
                category TEXT,
                tcm_category TEXT,
                description TEXT,
                symptoms TEXT,
                pathogenesis TEXT,
                treatment_principles TEXT,
                common_herbs TEXT,
                prognosis TEXT,
                references TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 社区帖子表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS community_posts (
                id TEXT PRIMARY KEY,
                author_id TEXT NOT NULL,
                title TEXT NOT NULL,
                title_en TEXT,
                title_ja TEXT,
                content TEXT NOT NULL,
                content_en TEXT,
                content_ja TEXT,
                category TEXT,
                tags TEXT,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                is_pinned INTEGER DEFAULT 0,
                is_anonymous INTEGER DEFAULT 0,
                privacy_level TEXT DEFAULT 'public',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_id) REFERENCES users(id)
            )
        """)
        
        # 社区评论表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS community_comments (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                author_id TEXT NOT NULL,
                content TEXT NOT NULL,
                content_en TEXT,
                content_ja TEXT,
                parent_id TEXT,
                like_count INTEGER DEFAULT 0,
                is_anonymous INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users(id),
                FOREIGN KEY (parent_id) REFERENCES community_comments(id)
            )
        """)
        
        # 创建索引
        self._create_indexes(conn)
        
        conn.commit()
        conn.close()
    
    def _create_indexes(self, conn):
        """创建数据库索引以优化查询"""
        # 患者索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_patients_code ON patients(patient_code)")
        
        # 处方索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor ON prescriptions(doctor_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_date ON prescriptions(visit_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_diagnosis ON prescriptions(diagnosis)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_syndrome ON prescriptions(syndrome)")
        
        # 药物索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_herbs_prescription ON prescription_herbs(prescription_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_herbs_name ON prescription_herbs(herb_name)")
        
        # 社区索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_author ON community_posts(author_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_category ON community_posts(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON community_posts(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_post ON community_comments(post_id)")
        
        # 全文搜索索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prescriptions_diagnosis_fts 
            ON prescriptions(diagnosis, diagnosis_en, diagnosis_ja)
        """)
    
    def _init_postgresql(self):
        """初始化PostgreSQL数据库"""
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            
            # 连接PostgreSQL服务器
            conn = psycopg2.connect(
                host=self.config.pg_host,
                port=self.config.pg_port,
                user=self.config.pg_user,
                password=self.config.pg_password
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            # 创建数据库
            cur = conn.cursor()
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.config.pg_database}'")
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {self.config.pg_database}")
            
            cur.close()
            conn.close()
            
            # 连接目标数据库
            conn = psycopg2.connect(
                host=self.config.pg_host,
                port=self.config.pg_port,
                database=self.config.pg_database,
                user=self.config.pg_user,
                password=self.config.pg_password
            )
            
            # 创建表结构（PostgreSQL版本）
            cur = conn.cursor()
            
            # 用户表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(50) PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    role VARCHAR(50) DEFAULT 'doctor',
                    language VARCHAR(10) DEFAULT 'zh_CN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 患者表（包含多语言字段）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id VARCHAR(50) PRIMARY KEY,
                    patient_code VARCHAR(50) UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    name_en VARCHAR(100),
                    name_ja VARCHAR(100),
                    gender VARCHAR(10),
                    age INTEGER,
                    phone VARCHAR(50),
                    email VARCHAR(255),
                    address TEXT,
                    medical_history TEXT,
                    allergies TEXT,
                    notes TEXT,
                    privacy_level VARCHAR(20) DEFAULT 'private',
                    created_by VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 处方主表（包含多语言字段）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prescriptions (
                    id VARCHAR(50) PRIMARY KEY,
                    prescription_code VARCHAR(50) UNIQUE NOT NULL,
                    patient_id VARCHAR(50) NOT NULL,
                    doctor_id VARCHAR(50),
                    visit_date TIMESTAMP NOT NULL,
                    diagnosis TEXT,
                    diagnosis_en TEXT,
                    diagnosis_ja TEXT,
                    syndrome TEXT,
                    syndrome_en TEXT,
                    syndrome_ja TEXT,
                    chief_complaint TEXT,
                    chief_complaint_en TEXT,
                    chief_complaint_ja TEXT,
                    symptoms TEXT,
                    symptoms_en TEXT,
                    symptoms_ja TEXT,
                    tongue TEXT,
                    tongue_en TEXT,
                    tongue_ja TEXT,
                    pulse TEXT,
                    pulse_en TEXT,
                    pulse_ja TEXT,
                    treatment_method TEXT,
                    treatment_method_en TEXT,
                    treatment_method_ja TEXT,
                    notes TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    privacy_level VARCHAR(20) DEFAULT 'doctor_only',
                    created_by VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 药物明细表（包含多语言字段）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prescription_herbs (
                    id SERIAL PRIMARY KEY,
                    prescription_id VARCHAR(50) NOT NULL,
                    herb_id VARCHAR(50),
                    herb_name VARCHAR(100) NOT NULL,
                    herb_name_en VARCHAR(100),
                    herb_name_ja VARCHAR(100),
                    dose REAL NOT NULL,
                    dose_unit VARCHAR(20) DEFAULT 'g',
                    dose_unit_en VARCHAR(20) DEFAULT 'g',
                    dose_unit_ja VARCHAR(20) DEFAULT 'g',
                    usage TEXT,
                    usage_en TEXT,
                    usage_ja TEXT,
                    processing TEXT,
                    processing_en TEXT,
                    processing_ja TEXT,
                    sort_order INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 社区帖子表（包含多语言字段）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS community_posts (
                    id VARCHAR(50) PRIMARY KEY,
                    author_id VARCHAR(50) NOT NULL,
                    title TEXT NOT NULL,
                    title_en TEXT,
                    title_ja TEXT,
                    content TEXT NOT NULL,
                    content_en TEXT,
                    content_ja TEXT,
                    category VARCHAR(50),
                    tags TEXT,
                    view_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0,
                    is_pinned INTEGER DEFAULT 0,
                    is_anonymous INTEGER DEFAULT 0,
                    privacy_level VARCHAR(20) DEFAULT 'public',
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建PostgreSQL索引
            cur.execute("CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_date ON prescriptions(visit_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_herbs_prescription ON prescription_herbs(prescription_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_author ON community_posts(author_id)")
            
            # 创建全文搜索索引
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_prescriptions_fts 
                ON prescriptions USING gin(to_tsvector('chinese', diagnosis || ' ' || syndrome || ' ' || chief_complaint))
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            
        except ImportError:
            print("警告：PostgreSQL驱动未安装，将使用SQLite")
            self.config.db_type = DatabaseType.SQLITE
            self._init_sqlite()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if self.config.db_type == DatabaseType.SQLITE:
            conn = self._get_sqlite_connection()
            try:
                yield conn
            finally:
                conn.close()
        else:
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=self.config.pg_host,
                    port=self.config.pg_port,
                    database=self.config.pg_database,
                    user=self.config.pg_user,
                    password=self.config.pg_password
                )
                try:
                    yield conn
                finally:
                    conn.close()
            except ImportError:
                raise Exception("PostgreSQL驱动未安装")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            if self.config.db_type == DatabaseType.SQLITE:
                cur = conn.cursor()
                cur.execute(query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description] if cur.description else []
                return [dict(zip(columns, row)) for row in rows]
            else:
                cur = conn.cursor()
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新操作并返回影响的行数"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return cur.rowcount


class PrescriptionModel:
    """处方数据模型"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def generate_id(self) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:6]
        return f"PR{timestamp}{random_str}"
    
    def generate_prescription_code(self, conn=None) -> str:
        """生成处方编号"""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"RX{today}"
        
        query = "SELECT prescription_code FROM prescriptions WHERE prescription_code LIKE ? ORDER BY prescription_code DESC LIMIT 1"
        result = self.db.execute_query(query, (f"{prefix}%",))
        
        if result:
            last_code = result[0]['prescription_code']
            seq = int(last_code[-4:]) + 1
        else:
            seq = 1
        
        return f"{prefix}{seq:04d}"
    
    def save_prescription(self, data: Dict[str, Any], herbs: List[Dict[str, Any]] = None) -> str:
        """保存处方及其药物明细"""
        prescription_id = self.generate_id()
        prescription_code = self.generate_prescription_code()
        
        # 根据语言字段映射
        lang = data.get('language', 'zh_CN')
        
        # 准备处方数据
        prescription_data = {
            'id': prescription_id,
            'prescription_code': prescription_code,
            'patient_id': data.get('patient_id'),
            'doctor_id': data.get('doctor_id'),
            'visit_date': data.get('visit_date', datetime.now().isoformat()),
            'diagnosis': data.get('diagnosis') or data.get('diagnosis_zh'),
            'diagnosis_en': data.get('diagnosis_en'),
            'diagnosis_ja': data.get('diagnosis_ja'),
            'syndrome': data.get('syndrome') or data.get('zhenghou'),
            'syndrome_en': data.get('syndrome_en'),
            'syndrome_ja': data.get('syndrome_ja'),
            'chief_complaint': data.get('chief_complaint') or data.get('complaint'),
            'chief_complaint_en': data.get('chief_complaint_en'),
            'chief_complaint_ja': data.get('chief_complaint_ja'),
            'symptoms': data.get('symptoms'),
            'symptoms_en': data.get('symptoms_en'),
            'symptoms_ja': data.get('symptoms_ja'),
            'tongue': data.get('tongue'),
            'tongue_en': data.get('tongue_en'),
            'tongue_ja': data.get('tongue_ja'),
            'pulse': data.get('pulse'),
            'pulse_en': data.get('pulse_en'),
            'pulse_ja': data.get('pulse_ja'),
            'treatment_method': data.get('treatment_method') or data.get('zhifa'),
            'treatment_method_en': data.get('treatment_method_en'),
            'treatment_method_ja': data.get('treatment_method_ja'),
            'notes': data.get('notes'),
            'status': 'active',
            'privacy_level': data.get('privacy_level', 'doctor_only'),
            'created_by': data.get('created_by'),
        }
        
        # 插入处方记录
        query = """
            INSERT INTO prescriptions (
                id, prescription_code, patient_id, doctor_id, visit_date,
                diagnosis, diagnosis_en, diagnosis_ja,
                syndrome, syndrome_en, syndrome_ja,
                chief_complaint, chief_complaint_en, chief_complaint_ja,
                symptoms, symptoms_en, symptoms_ja,
                tongue, tongue_en, tongue_ja,
                pulse, pulse_en, pulse_ja,
                treatment_method, treatment_method_en, treatment_method_ja,
                notes, status, privacy_level, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = tuple(prescription_data.get(key) for key in [
            'id', 'prescription_code', 'patient_id', 'doctor_id', 'visit_date',
            'diagnosis', 'diagnosis_en', 'diagnosis_ja',
            'syndrome', 'syndrome_en', 'syndrome_ja',
            'chief_complaint', 'chief_complaint_en', 'chief_complaint_ja',
            'symptoms', 'symptoms_en', 'symptoms_ja',
            'tongue', 'tongue_en', 'tongue_ja',
            'pulse', 'pulse_en', 'pulse_ja',
            'treatment_method', 'treatment_method_en', 'treatment_method_ja',
            'notes', 'status', 'privacy_level', 'created_by'
        ])
        
        self.db.execute_update(query, params)
        
        # 保存药物明细
        if herbs:
            for idx, herb in enumerate(herbs):
                herb_query = """
                    INSERT INTO prescription_herbs (
                        prescription_id, herb_id, herb_name, herb_name_en, herb_name_ja,
                        dose, dose_unit, dose_unit_en, dose_unit_ja,
                        usage, usage_en, usage_ja,
                        processing, processing_en, processing_ja,
                        sort_order, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                herb_params = (
                    prescription_id,
                    herb.get('herb_id'),
                    herb.get('name') or herb.get('herb_name'),
                    herb.get('name_en') or herb.get('herb_name_en'),
                    herb.get('name_ja') or herb.get('herb_name_ja'),
                    herb.get('dose'),
                    herb.get('dose_unit', 'g'),
                    herb.get('dose_unit_en', 'g'),
                    herb.get('dose_unit_ja', 'g'),
                    herb.get('usage'),
                    herb.get('usage_en'),
                    herb.get('usage_ja'),
                    herb.get('processing'),
                    herb.get('processing_en'),
                    herb.get('processing_ja'),
                    idx,
                    herb.get('notes')
                )
                
                self.db.execute_update(herb_query, herb_params)
        
        return prescription_id
    
    def get_prescription(self, prescription_id: str) -> Optional[Dict]:
        """获取单个处方详情"""
        query = "SELECT * FROM prescriptions WHERE id = ?"
        results = self.db.execute_query(query, (prescription_id,))
        
        if not results:
            return None
        
        prescription = results[0]
        
        # 获取药物明细
        herbs_query = "SELECT * FROM prescription_herbs WHERE prescription_id = ? ORDER BY sort_order"
        herbs = self.db.execute_query(herbs_query, (prescription_id,))
        prescription['herbs'] = herbs
        
        return prescription
    
    def search_prescriptions(
        self,
        keyword: str = None,
        patient_id: str = None,
        doctor_id: str = None,
        diagnosis: str = None,
        syndrome: str = None,
        herb_name: str = None,
        start_date: str = None,
        end_date: str = None,
        language: str = 'zh_CN',
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """高级搜索处方"""
        conditions = []
        params = []
        
        if keyword:
            conditions.append(f"(diagnosis LIKE ? OR syndrome LIKE ? OR chief_complaint LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        
        if patient_id:
            conditions.append("patient_id = ?")
            params.append(patient_id)
        
        if doctor_id:
            conditions.append("doctor_id = ?")
            params.append(doctor_id)
        
        if diagnosis:
            conditions.append("diagnosis LIKE ?")
            params.append(f"%{diagnosis}%")
        
        if syndrome:
            conditions.append("syndrome LIKE ?")
            params.append(f"%{syndrome}%")
        
        if start_date:
            conditions.append("visit_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("visit_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 统计总数
        count_query = f"SELECT COUNT(*) as total FROM prescriptions WHERE {where_clause}"
        count_result = self.db.execute_query(count_query, tuple(params))
        total = count_result[0]['total'] if count_result else 0
        
        # 分页查询
        query = f"""
            SELECT * FROM prescriptions 
            WHERE {where_clause}
            ORDER BY visit_date DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        prescriptions = self.db.execute_query(query, tuple(params))
        
        # 如果按药味搜索，需要过滤
        if herb_name:
            herb_pattern = f"%{herb_name}%"
            filtered = []
            for p in prescriptions:
                herbs_query = "SELECT 1 FROM prescription_herbs WHERE prescription_id = ? AND herb_name LIKE ?"
                herb_results = self.db.execute_query(herbs_query, (p['id'], herb_pattern))
                if herb_results:
                    filtered.append(p)
            prescriptions = filtered
        
        return prescriptions, total
    
    def get_patient_prescriptions(self, patient_id: str, limit: int = None) -> List[Dict]:
        """获取患者的所有处方（用于时间线追踪）"""
        query = """
            SELECT * FROM prescriptions 
            WHERE patient_id = ?
            ORDER BY visit_date ASC, created_at ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        return self.db.execute_query(query, (patient_id,))
    
    def get_prescription_statistics(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """获取处方统计数据"""
        conditions = []
        params = []
        
        if start_date:
            conditions.append("visit_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("visit_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 处方总数
        total_query = f"SELECT COUNT(*) as total FROM prescriptions WHERE {where_clause}"
        total_result = self.db.execute_query(total_query, tuple(params))
        total_prescriptions = total_result[0]['total'] if total_result else 0
        
        # 高频药材统计
        herb_query = f"""
            SELECT ph.herb_name, COUNT(*) as frequency
            FROM prescription_herbs ph
            JOIN prescriptions p ON ph.prescription_id = p.id
            WHERE {' AND '.join([f"p.{c.split('=')[0].strip()}" for c in conditions]) if conditions else '1=1'}
            GROUP BY ph.herb_name
            ORDER BY frequency DESC
            LIMIT 50
        """
        herb_stats = self.db.execute_query(herb_query, tuple(params))
        
        # 高频诊断统计
        diagnosis_query = f"""
            SELECT diagnosis, COUNT(*) as frequency
            FROM prescriptions
            WHERE {where_clause} AND diagnosis IS NOT NULL AND diagnosis != ''
            GROUP BY diagnosis
            ORDER BY frequency DESC
            LIMIT 30
        """
        diagnosis_stats = self.db.execute_query(diagnosis_query, tuple(params))
        
        # 月度趋势
        monthly_query = f"""
            SELECT strftime('%Y-%m', visit_date) as month, COUNT(*) as count
            FROM prescriptions
            WHERE {where_clause}
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """
        monthly_stats = self.db.execute_query(monthly_query, tuple(params))
        
        return {
            'total_prescriptions': total_prescriptions,
            'herb_frequency': herb_stats,
            'diagnosis_distribution': diagnosis_stats,
            'monthly_trend': monthly_stats
        }


class PatientModel:
    """患者数据模型"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def generate_id(self) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:6]
        return f"PT{timestamp}{random_str}"
    
    def generate_patient_code(self) -> str:
        """生成患者编号"""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"PT{today}"
        
        query = "SELECT patient_code FROM patients WHERE patient_code LIKE ? ORDER BY patient_code DESC LIMIT 1"
        result = self.db.execute_query(query, (f"{prefix}%",))
        
        if result:
            last_code = result[0]['patient_code']
            seq = int(last_code[-4:]) + 1
        else:
            seq = 1
        
        return f"{prefix}{seq:04d}"
    
    def save_patient(self, data: Dict[str, Any]) -> str:
        """保存患者信息"""
        patient_id = self.generate_id()
        patient_code = self.generate_patient_code()
        
        query = """
            INSERT INTO patients (
                id, patient_code, name, name_en, name_ja,
                gender, age, phone, email, address,
                medical_history, allergies, notes, privacy_level, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            patient_id,
            patient_code,
            data.get('name'),
            data.get('name_en'),
            data.get('name_ja'),
            data.get('gender'),
            data.get('age'),
            data.get('phone'),
            data.get('email'),
            data.get('address'),
            data.get('medical_history'),
            data.get('allergies'),
            data.get('notes'),
            data.get('privacy_level', 'private'),
            data.get('created_by')
        )
        
        self.db.execute_update(query, params)
        return patient_id
    
    def get_patient(self, patient_id: str) -> Optional[Dict]:
        """获取患者详情"""
        query = "SELECT * FROM patients WHERE id = ?"
        results = self.db.execute_query(query, (patient_id,))
        return results[0] if results else None
    
    def search_patients(self, keyword: str = None, limit: int = 100) -> List[Dict]:
        """搜索患者"""
        if keyword:
            query = """
                SELECT * FROM patients 
                WHERE name LIKE ? OR name_en LIKE ? OR name_ja LIKE ? OR patient_code LIKE ?
                ORDER BY name
                LIMIT ?
            """
            kw = f"%{keyword}%"
            return self.db.execute_query(query, (kw, kw, kw, kw, limit))
        else:
            query = "SELECT * FROM patients ORDER BY name LIMIT ?"
            return self.db.execute_query(query, (limit,))


class CommunityModel:
    """社区数据模型"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def generate_id(self) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:6]
        return f"POST{timestamp}{random_str}"
    
    def create_post(self, data: Dict[str, Any]) -> str:
        """创建社区帖子"""
        post_id = self.generate_id()
        
        query = """
            INSERT INTO community_posts (
                id, author_id, title, title_en, title_ja,
                content, content_en, content_ja,
                category, tags, is_anonymous, privacy_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            post_id,
            data.get('author_id'),
            data.get('title'),
            data.get('title_en'),
            data.get('title_ja'),
            data.get('content'),
            data.get('content_en'),
            data.get('content_ja'),
            data.get('category'),
            data.get('tags'),
            data.get('is_anonymous', 0),
            data.get('privacy_level', 'public')
        )
        
        self.db.execute_update(query, params)
        return post_id
    
    def get_posts(
        self,
        category: str = None,
        keyword: str = None,
        author_id: str = None,
        privacy: str = 'public',
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """获取社区帖子列表"""
        conditions = ["privacy_level <= ?"]
        params = [privacy]
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if keyword:
            conditions.append("(title LIKE ? OR content LIKE ? OR title_en LIKE ? OR title_ja LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw, kw])
        
        if author_id:
            conditions.append("author_id = ?")
            params.append(author_id)
        
        where_clause = " AND ".join(conditions)
        
        # 统计总数
        count_query = f"SELECT COUNT(*) as total FROM community_posts WHERE {where_clause}"
        count_result = self.db.execute_query(count_query, tuple(params))
        total = count_result[0]['total'] if count_result else 0
        
        # 分页查询
        query = f"""
            SELECT * FROM community_posts 
            WHERE {where_clause}
            ORDER BY is_pinned DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        posts = self.db.execute_query(query, tuple(params))
        
        return posts, total
    
    def add_comment(self, post_id: str, author_id: str, content: str, parent_id: str = None) -> str:
        """添加评论"""
        comment_id = self.generate_id() + "CM"
        
        query = """
            INSERT INTO community_comments (
                id, post_id, author_id, content, content_en, content_ja, parent_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute_update(query, (comment_id, post_id, author_id, content, None, None, parent_id))
        
        # 更新评论数
        update_query = """
            UPDATE community_posts 
            SET comment_count = comment_count + 1 
            WHERE id = ?
        """
        self.db.execute_update(update_query, (post_id,))
        
        return comment_id


# 创建全局数据库实例
db_manager = DatabaseManager()
prescription_model = PrescriptionModel(db_manager)
patient_model = PatientModel(db_manager)
community_model = CommunityModel(db_manager)
