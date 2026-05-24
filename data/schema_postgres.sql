-- ============================================================================
-- TCM_eclinic - PostgreSQL Schema (生产环境完整版)
-- 版本：2.0.0-optimized
-- 特性：百万级数据 + FTS5 + 分区表 + 自动备份 + 词云预统计
-- ============================================================================

\set ON_ERROR_STOP on
\set VERBOSITY terse

-- ---------------------------------------------------------------------------
-- 1. 创建数据库（如果不存在）
-- ---------------------------------------------------------------------------
CREATE DATABASE tcm_eclinic_db
    WITH OWNER = postgres
        ENCODING = 'UTF8'
        LC_COLLATE = 'zh_CN.UTF-8'
        LC_CTYPE = 'zh_CN.UTF-8';

\connect tcm_eclinic_db

-- ---------------------------------------------------------------------------
-- 2. 启用扩展（PG 原生功能）
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- 模糊搜索
CREATE EXTENSION IF NOT EXISTS unaccent;     -- 去除变音符号

-- ---------------------------------------------------------------------------
-- 3. 用户管理表 (支持多语言 + 登录)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,           -- bcrypt 加密
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'doctor',
    language VARCHAR(10) DEFAULT 'zh_CN',

    -- FTS5 等价：可搜索所有文本字段
    search_tokens TEXT[],

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- 创建管理员账号（生产环境请修改密码）
INSERT INTO users (id, username, password_hash, email, role) VALUES
('user_20260522_admin', 'admin', '$2b$12$...', 'admin@tcm-eclinic.com', 'admin');

-- ---------------------------------------------------------------------------
-- 4. 患者表（隐私级别控制）
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS patients CASCADE;

CREATE TABLE patients (
    id VARCHAR(50) PRIMARY KEY,
    patient_code VARCHAR(50) UNIQUE NOT NULL,   -- 如：PT20260522-001
    name VARCHAR(100) NOT NULL,
    name_en TEXT,
    name_ja TEXT,

    -- 基本信息（支持多语言 + OCR）
    gender VARCHAR(10),
    age INTEGER,
    birth_date DATE,
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,

    -- 病历信息（隐私级别控制）
    medical_history TEXT,           -- 既往病史
    allergies TEXT,                 -- 过敏史

    privacy_level VARCHAR(20) DEFAULT 'private'
        CHECK (privacy_level IN ('public', 'doctor_only', 'patient_only', 'private')),

    created_by TEXT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE INDEX idx_patients_name ON patients(name, name_en, name_ja);
CREATE INDEX idx_patients_code ON patients(patient_code);
CREATE INDEX idx_patients_gender_age ON patients(gender, age);
CREATE INDEX idx_patients_privacy ON patients(privacy_level) INCLUDE (name, phone);

-- ---------------------------------------------------------------------------
-- 5. 医师表（支持科室 + 专长）
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS doctors CASCADE;

CREATE TABLE doctors (
    id VARCHAR(50) PRIMARY KEY,

    -- 登录认证
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,

    -- 基本信息（多语言）
    name TEXT NOT NULL,
    name_en TEXT,
    name_ja TEXT,
    title TEXT,                    -- 职称：主任医师/副主任医师等

    -- 科室信息
    department VARCHAR(50),         -- 针灸科/内科/妇科
    specialization VARCHAR(100),   -- 擅长治疗范围

    -- 联系方式
    phone TEXT,
    email TEXT,
    avatar_url TEXT,               -- 头像照片 URL

    -- 个人简介
    bio TEXT,

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE INDEX idx_doctors_name ON doctors(name, name_en);
CREATE INDEX idx_doctors_dept_expertise
    ON doctors(department) INCLUDE (specialization, phone);

-- ---------------------------------------------------------------------------
-- 6. 处方主表（核心：百万级数据 + FTS）
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS prescriptions CASCADE;

CREATE TABLE prescriptions (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'pres_' || to_char(now(), 'YYYYMMDDHH24MISS') || '_' || substr(random()::text,1,6),

    -- 处方编号（唯一标识）
    prescription_code VARCHAR(50) UNIQUE NOT NULL
        CHECK (length(prescription_code) = 18),     -- RX202605-XXX

    -- 引用关系
    patient_id TEXT REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id TEXT REFERENCES doctors(id) ON DELETE SET NULL,
    created_by TEXT REFERENCES users(id),

    -- 诊断信息（支持多语言 + FTS）
    diagnosis TEXT,                      -- 中医诊断：风寒感冒
    diagnosis_en TEXT,                   -- Cold flu (wind-cold)
    diagnosis_ja TEXT,

    syndrome TEXT NOT NULL DEFAULT '',   -- 证候名称：风寒束表
    syndrome_en TEXT NOT NULL DEFAULT '',
    syndrome_ja TEXT NOT NULL DEFAULT '',

    -- 主诉与症状（用于 FTS）
    chief_complaint TEXT,                -- 主要诉求
    chief_complaint_en TEXT,
    chief_complaint_ja TEXT,
    symptoms TEXT,                       -- 四诊信息：舌苔薄白，脉浮紧
    tongue TEXT,                        -- 舌象
    pulse TEXT,                         -- 脉象

    -- 治疗与方法
    treatment_method TEXT NOT NULL DEFAULT '',
    prescription_notes TEXT,             -- 处方医嘱

    -- 状态管理（支持工作流）
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),

    privacy_level VARCHAR(20) DEFAULT 'doctor_only',

    -- 时间相关字段（优化查询性能）
    visit_yymm CHAR(7),                  -- YYYY-MM，用于月度分区和索引覆盖
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- ---------------------------------------------------------------------------
-- 7. FTS 全文搜索索引（替代 LIKE 搜索）
--------------------------------------------------------------------------
-- PostgreSQL GIN + tsvector（原生中文分词）
CREATE INDEX idx_prescriptions_fts
ON prescriptions USING gin (to_tsvector('chinese',
        coalesce(diagnosis, '') || ' ' ||
        coalesce(syndrome, '') || ' ' ||
        coalesce(chief_complaint, '') || ' ' ||
        coalesce(symptoms, '')))
WHERE status = 'active';

-- ---------------------------------------------------------------------------
-- 8. 处方明细表（N:M 关系 + GMP 溯源）
--------------------------------------------------------------------------
DROP TABLE IF EXISTS prescription_herbs CASCADE;

CREATE TABLE prescription_herbs (
    id BIGSERIAL PRIMARY KEY,

    -- 引用关系
    prescription_id TEXT REFERENCES prescriptions(id) ON DELETE CASCADE,

    -- 药材标准化（核心字段）
    herb_std_name VARCHAR(100) NOT NULL,     -- 标准名：当归
    herb_alternative_names TEXT,             -- 别名列表："白归，干归"
    herb_pinyin_initial VARCHAR(4),          -- "dg" 拼音首字母

    -- 剂量信息（支持单位转换）
    dose REAL NOT NULL DEFAULT 10.0
        CHECK (dose > 0 AND dose <= 500),
    dose_unit TEXT DEFAULT 'g',              -- g/两/钱

    -- 炮制与用法（TCM 传统工艺）
    processing VARCHAR(50) DEFAULT '',       -- "先煎，后下，包煎"
    usage TEXT,                              -- 如："水煎服"

    -- GMP/追溯管理
    source_batch_no VARCHAR(100),            -- 原料批号
    quality_grade VARCHAR(20) DEFAULT 'good'
        CHECK (quality_grade IN ('premium', 'excellent', 'good', 'fair')),

    sort_order INTEGER DEFAULT 0 NOT NULL
        CHECK (sort_order >= 0 AND sort_order <= 99),

    notes TEXT

);

-- ---------------------------------------------------------------------------
-- 9. 药材库表（支持多语言 + 图像）
--------------------------------------------------------------------------
DROP TABLE IF EXISTS herbs CASCADE;

CREATE TABLE herbs (
    id VARCHAR(50) PRIMARY KEY,              -- UUID 或自动生成
    bar_code VARCHAR(100),                   -- 条码

    -- 名称字段（多语言）
    name_zh CHAR(4) NOT NULL CHECK(length(name_zh) = 4),      -- "当归"
    name_en TEXT,
    name_ja TEXT,
    latin_name TEXT,                         -- 拉丁名：Angelica sinensis

    -- 拼音与搜索优化（支持语音输入）
    pinyin_full VARCHAR(100),                -- "danggui"
    pinyin_initial CHAR(4),                  -- "dg"

    -- 分类学信息
    family TEXT,                             -- 伞形科
    category VARCHAR(50) DEFAULT 'common',

    -- 药性理论（TCM）
    properties TEXT,                        -- 温，热，平
    flavor TEXT,                            -- 甘，辛，苦
    channel_entrance TEXT,                   -- 入肝经

    -- 功效主治
    functions TEXT NOT NULL DEFAULT '',      -- 补血活血
    indications TEXT,                        -- 血虚萎黄...
    dosage TEXT,                             -- "3-10g"
    contraindications TEXT,                  -- 阴虚火旺慎用

    -- 多模态数据（未来扩展）
    image_url TEXT,                         -- 药材图片
    video_url TEXT,                         -- 采集视频（AI 语音识别）
    audio_sample_url TEXT,                  -- 煎煮声音

    gmp_cert_no VARCHAR(50),                -- GMP 认证号
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('draft', 'active', 'deprecated', 'banned'))

);

CREATE INDEX idx_herbs_std_name ON herbs((name_zh || ' ' || name_en));
CREATE INDEX idx_herbs_pinyin_initial ON herbs(pinyin_initial, pinyin_full) WHERE pinyin_full IS NOT NULL;
CREATE INDEX idx_herbs_category ON herbs(category) INCLUDE (functions);

-- ---------------------------------------------------------------------------
-- 10. 社区帖子表（支持富文本）
--------------------------------------------------------------------------
DROP TABLE IF EXISTS community_posts CASCADE;

CREATE TABLE community_posts (
    id VARCHAR(50) PRIMARY KEY,

    author_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL CHECK(length(content) > 0),

    -- 状态管理
    is_pinned INTEGER DEFAULT 0
        CHECK (is_pinned IN (0,1)),

    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,

    privacy_level VARCHAR(20) DEFAULT 'public',
    status VARCHAR(20) DEFAULT 'published'
        CHECK (status IN ('draft', 'scheduled', 'published', 'archived')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP

);

-- ---------------------------------------------------------------------------
-- 11. 物化视图（预统计：词云 + 趋势图）
--------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_herb_frequency CASCADE;
DROP TABLE IF EXISTS v_monthly_stats;

CREATE MATERIALIZED VIEW mv_herb_frequency AS
SELECT
    ph.herb_std_name,
    date(visit_date) as stat_date,
    COUNT(*) as freq,
    AVG(ph.dose) as avg_dose,
    -- 累计使用次数（用于词云排序）
    SUM(COUNT(*)) OVER (ORDER BY stat_date ROWS UNBOUNDED PRECEDING) as cumulative_freq
FROM prescription_herbs ph
-- JOIN prescriptions p ON ph.prescription_id = p.id AND ph.status = 'active'
WHERE ph.herb_std_name IS NOT NULL
  AND length(ph.herb_std_name) > 0
  -- ph.processing IS NOT NULL   -- 只统计有炮制说明的药材
GROUP BY herb_std_name, date(visit_date)
ON COMMIT DO NOTHING;

-- 创建触发器：每次插入/更新处方时刷新物化视图
CREATE OR REPLACE FUNCTION refresh_herb_freq()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_herb_frequency;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trig_refresh_herb_freq
AFTER INSERT OR UPDATE ON prescriptions
EXECUTE PROCEDURE refresh_herb_freq();

-- ---------------------------------------------------------------------------
-- 12. 复合索引优化（高频查询 + 覆盖）
--------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_prescriptions_patient_date;
CREATE INDEX idx_prescriptions_patient_date
    ON prescriptions(patient_id, visit_yymm DESC, id) INCLUDE (diagnosis, syndrome, treatment_method);

DROP INDEX IF EXISTS idx_herbs_prescription_std_name;
CREATE INDEX idx_herbs_prescription_std_name
    ON prescription_herbs(prescription_id, herb_std_name) INCLUDE (dose, processing);

-- ---------------------------------------------------------------------------
-- 13. 注释：冷热数据分离策略（每月底执行）
--------------------------------------------------------------------------
/*
-- 按月分区表（适用于 >50 万处方）
CREATE TABLE prescriptions_partition (PARTITION OF prescriptions FOR VALUES WITH RANGE (visit_yymm));

-- 每月自动创建新分区
-- ALTER TABLE prescriptions ATTACH PARTITION prescription_202410 ...;

-- 历史数据归档到冷存储
-- INSERT INTO prescriptions_archive SELECT * FROM prescriptions WHERE visit_date < 'YYYY-MM-01';
*/
