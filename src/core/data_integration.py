# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 用户数据整合处理模块
整合中医用户的各类数据，包括患者数据、处方数据、医师数据等
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
import hashlib

try:
    from src.core.database import db_manager
except ImportError:
    db_manager = None
from src.core.user_manager import user_manager, doctor_manager
from src.core.i18n import Language, i18n, get_text


class DataIntegrationEngine:
    """数据整合引擎"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
    
    def get_patient_profile(self, patient_id: str) -> Optional[Dict]:
        """获取患者完整档案"""
        # 获取基本信息
        patient_sql = "SELECT * FROM patients WHERE id = ?"
        patient_result = db_manager.execute_query(patient_sql, (patient_id,))
        
        if not patient_result:
            return None
        
        patient = patient_result[0]
        
        # 获取就诊记录统计
        visit_sql = """
            SELECT 
                COUNT(*) as total_visits,
                COUNT(DISTINCT DATE(visit_date)) as distinct_days,
                MIN(visit_date) as first_visit,
                MAX(visit_date) as last_visit,
                COUNT(DISTINCT diagnosis) as diagnosis_count,
                COUNT(DISTINCT syndrome) as syndrome_count
            FROM prescriptions
            WHERE patient_id = ?
        """
        visit_stats = db_manager.execute_query(visit_sql, (patient_id,))
        
        # 获取主治医师信息
        doctor_sql = """
            SELECT DISTINCT d.*
            FROM doctors d
            JOIN prescriptions p ON p.doctor_id = d.id
            WHERE p.patient_id = ?
            ORDER BY p.visit_date DESC
            LIMIT 5
        """
        doctors = db_manager.execute_query(doctor_sql, (patient_id,))
        
        # 获取高频诊断
        diagnosis_sql = """
            SELECT diagnosis, COUNT(*) as frequency
            FROM prescriptions
            WHERE patient_id = ? AND diagnosis IS NOT NULL AND diagnosis != ''
            GROUP BY diagnosis
            ORDER BY frequency DESC
            LIMIT 10
        """
        diagnoses = db_manager.execute_query(diagnosis_sql, (patient_id,))
        
        # 获取常用药物
        herb_sql = """
            SELECT ph.herb_name, COUNT(*) as frequency
            FROM prescription_herbs ph
            JOIN prescriptions p ON ph.prescription_id = p.id
            WHERE p.patient_id = ?
            GROUP BY ph.herb_name
            ORDER BY frequency DESC
            LIMIT 20
        """
        herbs = db_manager.execute_query(herb_sql, (patient_id,))
        
        # 整合数据
        patient['visit_stats'] = visit_stats[0] if visit_stats else {}
        patient['primary_doctors'] = doctors
        patient['common_diagnoses'] = diagnoses
        patient['common_herbs'] = herbs
        
        return patient
    
    def get_doctor_profile(self, doctor_id: str) -> Optional[Dict]:
        """获取医师完整档案"""
        # 获取基本信息
        doctor_sql = "SELECT * FROM doctors WHERE id = ?"
        doctor_result = db_manager.execute_query(doctor_sql, (doctor_id,))
        
        if not doctor_result:
            return None
        
        doctor = doctor_result[0]
        
        # 获取接诊统计
        visit_sql = """
            SELECT 
                COUNT(*) as total_prescriptions,
                COUNT(DISTINCT patient_id) as total_patients,
                COUNT(DISTINCT diagnosis) as diagnosis_types,
                COUNT(DISTINCT syndrome) as syndrome_types,
                MIN(visit_date) as first_visit,
                MAX(visit_date) as last_visit
            FROM prescriptions
            WHERE doctor_id = ?
        """
        visit_stats = db_manager.execute_query(visit_sql, (doctor_id,))
        
        # 获取高频诊断
        diagnosis_sql = """
            SELECT diagnosis, COUNT(*) as frequency
            FROM prescriptions
            WHERE doctor_id = ? AND diagnosis IS NOT NULL AND diagnosis != ''
            GROUP BY diagnosis
            ORDER BY frequency DESC
            LIMIT 20
        """
        diagnoses = db_manager.execute_query(diagnosis_sql, (doctor_id,))
        
        # 获取高频药物
        herb_sql = """
            SELECT ph.herb_name, COUNT(*) as frequency
            FROM prescription_herbs ph
            JOIN prescriptions p ON ph.prescription_id = p.id
            WHERE p.doctor_id = ?
            GROUP BY ph.herb_name
            ORDER BY frequency DESC
            LIMIT 30
        """
        herbs = db_manager.execute_query(herb_sql, (doctor_id,))
        
        # 获取月度工作量
        monthly_sql = """
            SELECT 
                strftime('%Y-%m', visit_date) as month,
                COUNT(*) as prescription_count,
                COUNT(DISTINCT patient_id) as patient_count
            FROM prescriptions
            WHERE doctor_id = ?
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """
        monthly_stats = db_manager.execute_query(monthly_sql, (doctor_id,))
        
        # 获取典型案例
        case_sql = """
            SELECT 
                p.*,
                COUNT(ph.id) as herb_count
            FROM prescriptions p
            LEFT JOIN prescription_herbs ph ON p.id = ph.prescription_id
            WHERE p.doctor_id = ?
            GROUP BY p.id
            ORDER BY p.visit_date DESC
            LIMIT 10
        """
        recent_cases = db_manager.execute_query(case_sql, (doctor_id,))
        
        # 整合数据
        doctor['visit_stats'] = visit_stats[0] if visit_stats else {}
        doctor['common_diagnoses'] = diagnoses
        doctor['common_herbs'] = herbs
        doctor['monthly_workload'] = monthly_stats
        doctor['recent_cases'] = recent_cases
        
        return doctor
    
    def get_institution_summary(self, institution_id: str = None) -> Dict:
        """获取机构统计摘要"""
        # 医师统计
        doctor_sql = "SELECT COUNT(*) as total FROM doctors"
        doctor_count = db_manager.execute_query(doctor_sql)
        
        # 患者统计
        patient_sql = "SELECT COUNT(*) as total FROM patients"
        patient_count = db_manager.execute_query(patient_sql)
        
        # 处方统计
        prescription_sql = """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT patient_id) as patient_count,
                COUNT(DISTINCT doctor_id) as doctor_count,
                COUNT(DISTINCT diagnosis) as diagnosis_count
            FROM prescriptions
        """
        prescription_stats = db_manager.execute_query(prescription_sql)
        
        # 今日统计
        today = datetime.now().date().isoformat()
        today_sql = """
            SELECT COUNT(*) as today_prescriptions
            FROM prescriptions
            WHERE DATE(visit_date) = ?
        """
        today_stats = db_manager.execute_query(today_sql, (today,))
        
        # 高频疾病
        disease_sql = """
            SELECT 
                diagnosis,
                COUNT(*) as frequency
            FROM prescriptions
            WHERE diagnosis IS NOT NULL AND diagnosis != ''
            GROUP BY diagnosis
            ORDER BY frequency DESC
            LIMIT 15
        """
        top_diseases = db_manager.execute_query(disease_sql)
        
        # 高频药物
        herb_sql = """
            SELECT 
                ph.herb_name,
                COUNT(*) as frequency
            FROM prescription_herbs ph
            JOIN prescriptions p ON ph.prescription_id = p.id
            GROUP BY ph.herb_name
            ORDER BY frequency DESC
            LIMIT 20
        """
        top_herbs = db_manager.execute_query(herb_sql)
        
        return {
            'total_doctors': doctor_count[0]['total'] if doctor_count else 0,
            'total_patients': patient_count[0]['total'] if patient_count else 0,
            'total_prescriptions': prescription_stats[0]['total'] if prescription_stats else 0,
            'unique_patients': prescription_stats[0]['patient_count'] if prescription_stats else 0,
            'unique_doctors': prescription_stats[0]['doctor_count'] if prescription_stats else 0,
            'unique_diagnoses': prescription_stats[0]['diagnosis_count'] if prescription_stats else 0,
            'today_prescriptions': today_stats[0]['today_prescriptions'] if today_stats else 0,
            'top_diseases': top_diseases,
            'top_herbs': top_herbs,
            'generated_at': datetime.now().isoformat(),
        }
    
    def get_researcher_data(
        self,
        start_date: str = None,
        end_date: str = None,
        keywords: List[str] = None
    ) -> Dict[str, Any]:
        """获取研究者所需的数据"""
        conditions = []
        params = []
        
        if start_date:
            conditions.append("visit_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("visit_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 获取所有符合条件的处方
        prescription_sql = f"""
            SELECT 
                p.*,
                pt.name as patient_name,
                pt.age as patient_age,
                pt.gender as patient_gender,
                d.name as doctor_name
            FROM prescriptions p
            LEFT JOIN patients pt ON p.patient_id = pt.id
            LEFT JOIN doctors d ON p.doctor_id = d.id
            WHERE {where_clause}
            ORDER BY p.visit_date DESC
        """
        
        prescriptions = db_manager.execute_query(prescription_sql, tuple(params))
        
        # 按诊断分组
        diagnosis_groups = defaultdict(list)
        for p in prescriptions:
            diagnosis = p.get('diagnosis', '未知')
            if diagnosis:
                diagnosis_groups[diagnosis].append(p)
        
        # 获取每个处方的药物
        for p in prescriptions:
            herbs_sql = """
                SELECT herb_name, herb_name_en, dose, dose_unit, processing
                FROM prescription_herbs
                WHERE prescription_id = ?
                ORDER BY sort_order
            """
            herbs = db_manager.execute_query(herbs_sql, (p['id'],))
            p['herbs'] = herbs
        
        # 计算统计信息
        total_prescriptions = len(prescriptions)
        total_patients = len(set(p.get('patient_id') for p in prescriptions))
        total_doctors = len(set(p.get('doctor_id') for p in prescriptions))
        
        # 药物使用统计
        herb_counter = defaultdict(int)
        for p in prescriptions:
            for h in p.get('herbs', []):
                herb_counter[h.get('herb_name', '')] += 1
        
        # 证候统计
        syndrome_counter = defaultdict(int)
        for p in prescriptions:
            syndrome = p.get('syndrome', '')
            if syndrome:
                syndrome_counter[syndrome] += 1
        
        return {
            'summary': {
                'total_prescriptions': total_prescriptions,
                'total_patients': total_patients,
                'total_doctors': total_doctors,
                'date_range': {
                    'start': start_date,
                    'end': end_date,
                },
            },
            'prescriptions': prescriptions,
            'diagnosis_groups': dict(diagnosis_groups),
            'herb_statistics': dict(sorted(herb_counter.items(), key=lambda x: x[1], reverse=True)[:50]),
            'syndrome_statistics': dict(sorted(syndrome_counter.items(), key=lambda x: x[1], reverse=True)[:30]),
            'generated_at': datetime.now().isoformat(),
        }
    
    def export_patient_data(
        self, 
        patient_id: str, 
        format: str = 'json'
    ) -> str:
        """导出一个患者的所有数据"""
        patient_profile = self.get_patient_profile(patient_id)
        
        if not patient_profile:
            return ""
        
        # 获取所有处方
        prescriptions_sql = """
            SELECT * FROM prescriptions
            WHERE patient_id = ?
            ORDER BY visit_date ASC
        """
        prescriptions = db_manager.execute_query(prescriptions_sql, (patient_id,))
        
        # 获取每个处方的药物
        for p in prescriptions:
            herbs_sql = """
                SELECT * FROM prescription_herbs
                WHERE prescription_id = ?
                ORDER BY sort_order
            """
            herbs = db_manager.execute_query(herbs_sql, (p['id'],))
            p['herbs'] = herbs
        
        patient_profile['prescriptions'] = prescriptions
        
        if format == 'json':
            return json.dumps(patient_profile, ensure_ascii=False, indent=2, default=str)
        elif format == 'csv':
            # 简化的CSV导出
            lines = []
            lines.append("就诊日期,诊断,证候,主诉,舌象,脉象,药物")
            
            for p in prescriptions:
                herbs = ','.join([h.get('herb_name', '') for h in p.get('herbs', [])])
                line = f"{p.get('visit_date', '')},{p.get('diagnosis', '')},{p.get('syndrome', '')},{p.get('chief_complaint', '')},{p.get('tongue', '')},{p.get('pulse', '')},{herbs}"
                lines.append(line)
            
            return '\n'.join(lines)
        
        return str(patient_profile)
    
    def get_patient_similarity(
        self,
        patient_id: str,
        top_n: int = 10
    ) -> List[Dict]:
        """找出与某患者相似的其他患者"""
        # 获取目标患者的基本信息
        target_patient = self.get_patient_profile(patient_id)
        if not target_patient:
            return []
        
        # 获取目标患者的诊断和药物
        target_diagnoses = set(d.get('diagnosis') for d in target_patient.get('common_diagnoses', []))
        target_herbs = set(h.get('herb_name') for h in target_patient.get('common_herbs', []))
        
        # 获取所有患者
        patients_sql = "SELECT id, name FROM patients"
        all_patients = db_manager.execute_query(patients_sql)
        
        similarities = []
        for patient in all_patients:
            if patient['id'] == patient_id:
                continue
            
            patient_data = self.get_patient_profile(patient['id'])
            if not patient_data:
                continue
            
            # 计算相似度
            patient_diagnoses = set(d.get('diagnosis') for d in patient_data.get('common_diagnoses', []))
            patient_herbs = set(h.get('herb_name') for h in patient_data.get('common_herbs', []))
            
            # Jaccard相似度
            diagnosis_intersection = len(target_diagnoses & patient_diagnoses)
            diagnosis_union = len(target_diagnoses | patient_diagnoses)
            diagnosis_similarity = diagnosis_intersection / diagnosis_union if diagnosis_union > 0 else 0
            
            herb_intersection = len(target_herbs & patient_herbs)
            herb_union = len(target_herbs | patient_herbs)
            herb_similarity = herb_intersection / herb_union if herb_union > 0 else 0
            
            # 综合相似度
            overall_similarity = (diagnosis_similarity * 0.6 + herb_similarity * 0.4) * 100
            
            if overall_similarity > 10:  # 只返回相似度>10%的
                similarities.append({
                    'patient_id': patient['id'],
                    'patient_name': patient['name'],
                    'overall_similarity': round(overall_similarity, 2),
                    'diagnosis_similarity': round(diagnosis_similarity * 100, 2),
                    'herb_similarity': round(herb_similarity * 100, 2),
                    'common_diagnoses': list(target_diagnoses & patient_diagnoses),
                    'common_herbs': list(target_herbs & patient_herbs),
                })
        
        # 排序并返回top_n
        similarities.sort(key=lambda x: x['overall_similarity'], reverse=True)
        return similarities[:top_n]


class DataCleaning:
    """数据清洗工具"""
    
    @staticmethod
    def normalize_patient_names() -> Dict:
        """标准化患者姓名"""
        patients_sql = "SELECT id, name FROM patients WHERE name IS NOT NULL"
        patients = db_manager.execute_query(patients_sql)
        
        updated = 0
        for p in patients:
            name = p.get('name', '').strip()
            # 移除多余空格
            normalized = ' '.join(name.split())
            
            if normalized != p.get('name'):
                update_sql = "UPDATE patients SET name = ? WHERE id = ?"
                db_manager.execute_update(update_sql, (normalized, p['id']))
                updated += 1
        
        return {'total': len(patients), 'updated': updated}
    
    @staticmethod
    def normalize_herb_names() -> Dict:
        """标准化药物名称"""
        herbs_sql = """
            SELECT DISTINCT herb_name 
            FROM prescription_herbs 
            WHERE herb_name IS NOT NULL
        """
        herbs = db_manager.execute_query(herbs_sql)
        
        # 建立名称映射（简化实现）
        name_mapping = {}
        
        for h in herbs:
            name = h.get('herb_name', '').strip()
            if name and name not in name_mapping:
                update_sql = """
                    UPDATE prescription_herbs 
                    SET herb_name = ? 
                    WHERE herb_name = ?
                """
                # 这里可以实现更复杂的名称标准化逻辑
                pass
        
        return {'total': len(herbs), 'updated': 0}
    
    @staticmethod
    def fix_missing_dates() -> Dict:
        """修复缺失的就诊日期"""
        sql = """
            SELECT id FROM prescriptions 
            WHERE visit_date IS NULL OR visit_date = ''
        """
        prescriptions = db_manager.execute_query(sql)
        
        updated = 0
        for p in prescriptions:
            update_sql = """
                UPDATE prescriptions 
                SET visit_date = created_at 
                WHERE id = ?
            """
            db_manager.execute_update(update_sql, (p['id'],))
            updated += 1
        
        return {'total': len(prescriptions), 'updated': updated}


# 创建全局实例
data_integration_engine = DataIntegrationEngine()
data_cleaning = DataCleaning()
