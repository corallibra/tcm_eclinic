-- ============================================================================
-- 中医药诊所系统 - SQLite DDL (开发环境)
-- 支持：百万级处方、复合索引、全文搜索（FTS5）
-- Author: TCM_eclinic Team
-- ============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;  -- 64MB 缓存
PRAGMA temp_store = MEMORY;

-- ---------------------------------------------------------------------------
-- 1. 用户管理表
--------------------------------------------------------------------------

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'doctor',
    language VARCHAR(10) DEFAULT 'zh_CN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 用于全文搜索（FTS5）
    search_tokens TEXT  -- "admin,administrator"
);

-- ---------------------------------------------------------------------------
-- 2. 患者表
--------------------------------------------------------------------------

CREATE TABLE patients (
    id TEXT PRIMARY KEY DEFAULT ('patient_' || to_char(CURRENT_DATE, 'YYYYMMDDHH24MISS') || '_' || substr(randomblob(6),1,6)),
    patient_code VARCHAR(50) UNIQUE NOT NULL,
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

    privacy_level VARCHAR(20) DEFAULT 'private' CHECK (privacy_level IN ('public', 'doctor_only', 'patient_only', 'private')),
    created_by TEXT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化（覆盖常用查询 + FTS）
CREATE INDEX idx_patients_name_fts ON patients((name || ' ' || name_en || ' ' || name_ja));

-- ---------------------------------------------------------------------------
-- 3. 医师表
--------------------------------------------------------------------------

CREATE TABLE doctors (
    id TEXT PRIMARY KEY DEFAULT ('doctor_' || to_char(CURRENT_DATE, 'YYYYMMDDHH24MISS') || '_' || substr(randomblob(6),1,6)),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    name_en TEXT,
    name_ja TEXT,
    title TEXT,
    department TEXT,
    specialization TEXT,
    phone TEXT,
    email TEXT,
    bio TEXT,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_doctors_name ON doctors((name || ' ' || name_en));

-- ---------------------------------------------------------------------------
-- 4. 处方主表（核心优化）
--------------------------------------------------------------------------

CREATE TABLE prescriptions (
    id TEXT PRIMARY KEY DEFAULT ('prescription_' || to_char(CURRENT_DATE, 'YYYYMMDDHH24MISS') || '_' || substr(randomblob(6),1,6)),
    prescription_code VARCHAR(50) UNIQUE NOT NULL CHECK(length(prescription_code) = 18),

    patient_id TEXT REFERENCES patients(id),
    doctor_id TEXT REFERENCES doctors(id),
    created_by TEXT REFERENCES users(id),

    diagnosis TEXT,
    diagnosis_en TEXT,
    diagnosis_ja TEXT,

    syndrome TEXT DEFAULT '',
    syndrome_en TEXT DEFAULT '',
    syndrome_ja TEXT DEFAULT '',

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

    treatment_method TEXT DEFAULT '',
    treatment_method_en TEXT,
    treatment_method_ja TEXT,
    prescription_notes TEXT,

    status VARCHAR(20) DEFAULT 'active' CHECK(status IN ('draft', 'active', 'completed', 'cancelled')),
    privacy_level VARCHAR(20) DEFAULT 'doctor_only',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 时间字段优化（避免函数）
    visit_yymm CHAR(7),           -- YYYY-MM（用于月度分区策略）
    visit_date DATE
);

-- FTS5 全文搜索索引（SQLite 原生支持中文）
CREATE VIRTUAL TABLE prescriptions_fts USING fts5(
    diagnosis,
    syndrome,
    chief_complaint,
    symptoms,
    tongue,
    pulse,
    treatment_method,
    content=prescriptions, content_rowid=id
);

-- 触发器：同步 FTS 索引（每次新增/修改处方时）
CREATE TRIGGER prescriptions_insert_fts AFTER INSERT ON prescriptions BEGIN
    INSERT INTO prescriptions_fts (rowid, diagnosis, syndrome, chief_complaint, symptoms, tongue, pulse, treatment_method)
    VALUES (new.id, COALESCE(new.diagnosis,''), COALESCE(new.syndrome,''), COALESCE(new.chief_complaint,''), COALESCE(new.symptoms,''), COALESCE(new.tongue,''), COALESCE(new.pulse,''), COALESCE(new.treatment_method,''));
END;

CREATE TRIGGER prescriptions_delete_fts AFTER DELETE ON prescriptions BEGIN
    DELETE FROM prescriptions_fts WHERE rowid = old.id;
END;

CREATE TRIGGER prescriptions_update_fts AFTER UPDATE ON prescriptions BEGIN
    UPDATE prescriptions_fts SET diagnosis=COALESCE(new.diagnosis,''), syndrome=COALESCE(new.syndrome,''), chief_complaint=COALESCE(new.chief_complaint,''), symptoms=COALESCE(new.symptoms,''), tongue=COALESCE(new.tongue,''), pulse=COALESCE(new.pulse,''), treatment_method=COALESCE(new.treatment_method,'')
    WHERE rowid = new.id;
END;

-- 复合索引（高频查询 + 覆盖查询）
CREATE INDEX idx_prescriptions_patient_date
    ON prescriptions(patient_id, visit_yymm DESC, id);

CREATE INDEX idx_prescriptions_diagnosis_fts
    ON prescriptions(diagnosis, diagnosis_en, diagnosis_ja) WHERE length(coalesce(diagnosis,'')) > 0;

-- ---------------------------------------------------------------------------
-- 5. 处方药物明细表
--------------------------------------------------------------------------

CREATE TABLE prescription_herbs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id TEXT REFERENCES prescriptions(id) ON DELETE CASCADE,

    -- 药材标准化（核心字段）
    herb_std_name VARCHAR(100) NOT NULL,      -- "当归"
    herb_alternative_names TEXT,               -- "白归，干归，秦归"
    herb_pinyin_initial VARCHAR(4),            -- "dg"

    dose REAL NOT NULL DEFAULT 10.0 CHECK (dose > 0 AND dose <= 1000),
    dose_unit TEXT DEFAULT 'g',

    processing VARCHAR(50) DEFAULT '',         -- "先煎，后下，包煎"
    usage TEXT,

    -- GMP 溯源信息
    source_batch_no VARCHAR(100),
    quality_grade VARCHAR(20) DEFAULT 'good' CHECK (quality_grade IN ('premium', 'excellent', 'good', 'fair')),

    sort_order INTEGER DEFAULT 0 NOT NULL CHECK(sort_order >= 0 AND sort_order <= 99),
    notes TEXT

);

-- 索引优化（覆盖查询 + 外键索引）
CREATE INDEX idx_herbs_prescription_std_name
    ON prescription_herbs(prescription_id, herb_std_name);

CREATE INDEX idx_herbs_pinyin_initial ON prescription_herbs(herb_pinyin_initial);

-- ---------------------------------------------------------------------------
-- 6. 药材库表
--------------------------------------------------------------------------

CREATE TABLE herbs (
    id TEXT PRIMARY KEY DEFAULT ('herb_' || to_char(CURRENT_DATE) || '_' || to_char(random(), '%03d')),

    name_zh CHAR(4) NOT NULL CHECK(length(name_zh) = 4),        -- "当归"
    name_en VARCHAR(255),
    name_ja VARCHAR(255),
    latin_name TEXT,

    pinyin_full VARCHAR(100),                          -- "danggui"
    pinyin_initial CHAR(4),                            -- "dg"（拼音首字母）

    family TEXT,
    category VARCHAR(50) DEFAULT 'common',

    properties TEXT,
    flavor TEXT,
    channel_entrance TEXT,

    functions TEXT DEFAULT '',
    indications TEXT,
    dosage TEXT,
    contraindications TEXT,

    image_url TEXT,
    video_url TEXT,       -- 药材采集视频（未来 AI 语音识别）
    audio_sample_url TEXT, -- 煎煮声音采样（多模态数据输入）

    barcode VARCHAR(100),
    gmp_cert_no VARCHAR(50),

    status VARCHAR(20) DEFAULT 'active' CHECK(status IN ('draft', 'active', 'deprecated', 'banned'))
);

CREATE INDEX idx_herbs_std_name ON herbs((name_zh || ' ' || name_en));
CREATE INDEX idx_herbs_master_pinyin_initial ON herbs(pinyin_initial);

-- ---------------------------------------------------------------------------
-- 7. 社区帖子表
--------------------------------------------------------------------------

CREATE TABLE community_posts (
    id TEXT PRIMARY KEY DEFAULT ('post_' || to_char(CURRENT_DATE, 'YYYYMMDDHH24MISS') || '_' || substr(randomblob(6),1,6)),

    author_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL CHECK(length(content) > 0),

    is_pinned INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,

    privacy_level VARCHAR(20) DEFAULT 'public' CHECK (privacy_level IN ('public', 'doctor_only')),
    status VARCHAR(20) DEFAULT 'published' CHECK (status IN ('draft', 'scheduled', 'published', 'archived')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 8. 插入默认管理员账户
--------------------------------------------------------------------------

INSERT INTO users (id, username, password_hash, email, role, language) VALUES
('user_20260522_01', 'admin', '$2b$12$EIXbb5wBZ5X8c0M6sYjJf.JkLxK9e8r7t3y5u4i3o2p1a0z9y8x', 'admin@example.com', 'admin', 'zh_CN');

-- ---------------------------------------------------------------------------
-- 性能监控视图（预计算词云数据）
--------------------------------------------------------------------------

CREATE VIEW v_herb_frequency AS SELECT herb_std_name, date(visit_date) as stat_date, COUNT(*) as freq FROM prescription_herbs WHERE herb_std_name IS NOT NULL AND length(herb_std_name) > 0 GROUP BY herb_std_name, date(visit_date);

-- ---------------------------------------------------------------------------
-- 注释：冷热数据分离策略（每月底执行）
--------------------------------------------------------------------------
/*
INSERT INTO prescriptions_archive SELECT * FROM prescriptions WHERE visit_yymm = '2023-xx';
DROP INDEX idx_prescriptions_patient_date;  -- 归档后需要重建索引（缩小活跃表到<10GB）

-- 查询路由：主应用仅访问 active 表，历史数据用于统计分析
SELECT * FROM prescriptions_active WHERE patient_id = ? ...
UNION ALL
SELECT * FROM prescriptions_archive WHERE visit_date < date('now', '-365 days') AND patient_id = ? ...
*/
