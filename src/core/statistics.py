# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 数据统计模块
包含方剂云、药物高频云、诊断分布等统计功能
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter
import json
import re

try:
    from src.core.database import db_manager, prescription_model
except ImportError:
    db_manager = None
    prescription_model = None
from src.core.i18n import Language, i18n, get_text


class StatisticsEngine:
    """统计引擎"""
    
    def __init__(self, language: Language = Language.ZH_CN):
        self.language = language
    
    def set_language(self, language: Language):
        """设置语言"""
        self.language = language
        i18n.set_language(language)
    
    def _get_date_range(self, time_range: str) -> Tuple[str, str]:
        """获取日期范围"""
        today = datetime.now().date()
        
        ranges = {
            'today': (today.isoformat(), today.isoformat()),
            'yesterday': ((today - timedelta(days=1)).isoformat(), (today - timedelta(days=1)).isoformat()),
            'this_week': ((today - timedelta(days=today.weekday())).isoformat(), today.isoformat()),
            'last_week': ((today - timedelta(days=7)).isoformat(), today.isoformat()),
            'this_month': ((today.replace(day=1)).isoformat(), today.isoformat()),
            'last_month': ((today.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat(), 
                          (today.replace(day=1) - timedelta(days=1)).isoformat()),
            'this_quarter': ((today - timedelta(days=90)).isoformat(), today.isoformat()),
            'this_year': ((today.replace(month=1, day=1)).isoformat(), today.isoformat()),
            'last_7_days': ((today - timedelta(days=7)).isoformat(), today.isoformat()),
            'last_30_days': ((today - timedelta(days=30)).isoformat(), today.isoformat()),
            'last_90_days': ((today - timedelta(days=90)).isoformat(), today.isoformat()),
            'last_year': ((today - timedelta(days=365)).isoformat(), today.isoformat()),
            'all': ('1970-01-01', today.isoformat()),
        }
        
        return ranges.get(time_range, ('1970-01-01', today.isoformat()))
    
    def get_prescription_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        """获取处方统计摘要"""
        where_clause = "1=1"
        params = []
        
        if start_date:
            where_clause += " AND visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND visit_date <= ?"
            params.append(end_date)
        
        sql = f"""
            SELECT 
                COUNT(*) as total_prescriptions,
                COUNT(DISTINCT patient_id) as total_patients,
                COUNT(DISTINCT doctor_id) as total_doctors,
                COUNT(DISTINCT DATE(visit_date)) as total_days
            FROM prescriptions
            WHERE {where_clause}
        """
        
        try:
            result = db_manager.execute_query(sql, tuple(params))
            if result:
                return {
                    'total_prescriptions': result[0].get('total_prescriptions', 0),
                    'total_patients': result[0].get('total_patients', 0),
                    'total_doctors': result[0].get('total_doctors', 0),
                    'total_days': result[0].get('total_days', 0),
                    'avg_prescriptions_per_day': round(
                        result[0].get('total_prescriptions', 0) / max(result[0].get('total_days', 1), 1), 2
                    ),
                }
        except Exception as e:
            print(f"查询处方摘要失败: {e}")
        
        return {
            'total_prescriptions': 0,
            'total_patients': 0,
            'total_doctors': 0,
            'total_days': 0,
            'avg_prescriptions_per_day': 0,
        }
    
    def get_herb_frequency_stats(
        self, 
        start_date: str = None, 
        end_date: str = None, 
        top_n: int = 50
    ) -> List[Dict[str, Any]]:
        """获取高频药材统计"""
        where_clause = "1=1"
        params = []
        
        if start_date:
            where_clause += " AND p.visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND p.visit_date <= ?"
            params.append(end_date)
        
        sql = f"""
            SELECT 
                ph.herb_name,
                ph.herb_name_en,
                ph.herb_name_ja,
                COUNT(*) as frequency,
                SUM(ph.dose) as total_dose,
                AVG(ph.dose) as avg_dose,
                COUNT(DISTINCT p.patient_id) as patient_count
            FROM prescription_herbs ph
            JOIN prescriptions p ON ph.prescription_id = p.id
            WHERE {where_clause}
            GROUP BY ph.herb_name
            ORDER BY frequency DESC
            LIMIT ?
        """
        
        params.append(top_n)
        
        try:
            results = db_manager.execute_query(sql, tuple(params))
            return [
                {
                    'name': r.get('herb_name', ''),
                    'name_en': r.get('herb_name_en', ''),
                    'name_ja': r.get('herb_name_ja', ''),
                    'frequency': r.get('frequency', 0),
                    'total_dose': round(r.get('total_dose', 0), 2),
                    'avg_dose': round(r.get('avg_dose', 0), 2),
                    'patient_count': r.get('patient_count', 0),
                }
                for r in results
            ]
        except Exception as e:
            print(f"查询高频药材失败: {e}")
            return []
    
    def get_herb_pairs_stats(self, min_frequency: int = 5, top_n: int = 30) -> List[Dict]:
        """获取药对统计（经常一起使用的药物组合）"""
        # 这个查询需要更复杂的逻辑来识别药对
        # 简化实现
        sql = """
            SELECT 
                ph1.herb_name as herb1,
                ph2.herb_name as herb2,
                COUNT(*) as frequency
            FROM prescription_herbs ph1
            JOIN prescription_herbs ph2 ON ph1.prescription_id = ph2.prescription_id
                AND ph1.herb_name < ph2.herb_name
            JOIN prescriptions p ON ph1.prescription_id = p.id
            WHERE p.status = 'active'
            GROUP BY ph1.herb_name, ph2.herb_name
            HAVING COUNT(*) >= ?
            ORDER BY frequency DESC
            LIMIT ?
        """
        
        try:
            results = db_manager.execute_query(sql, (min_frequency, top_n))
            return [
                {
                    'herb1': r.get('herb1', ''),
                    'herb2': r.get('herb2', ''),
                    'frequency': r.get('frequency', 0),
                }
                for r in results
            ]
        except Exception as e:
            print(f"查询药对失败: {e}")
            return []
    
    def get_diagnosis_distribution(
        self, 
        start_date: str = None, 
        end_date: str = None, 
        top_n: int = 30
    ) -> List[Dict[str, Any]]:
        """获取诊断分布统计"""
        where_clause = "1=1"
        params = []
        
        if start_date:
            where_clause += " AND visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND visit_date <= ?"
            params.append(end_date)
        
        # 根据语言选择诊断字段
        diagnosis_field = {
            Language.ZH_CN: 'diagnosis',
            Language.EN_US: 'diagnosis_en',
            Language.JA_JP: 'diagnosis_ja',
        }.get(self.language, 'diagnosis')
        
        sql = f"""
            SELECT 
                {diagnosis_field} as diagnosis,
                COUNT(*) as frequency,
                COUNT(DISTINCT patient_id) as patient_count
            FROM prescriptions
            WHERE {where_clause}
                AND {diagnosis_field} IS NOT NULL 
                AND {diagnosis_field} != ''
            GROUP BY {diagnosis_field}
            ORDER BY frequency DESC
            LIMIT ?
        """
        
        params.append(top_n)
        
        try:
            results = db_manager.execute_query(sql, tuple(params))
            return [
                {
                    'diagnosis': r.get('diagnosis', ''),
                    'frequency': r.get('frequency', 0),
                    'patient_count': r.get('patient_count', 0),
                    'percentage': 0,  # 稍后计算
                }
                for r in results
            ]
        except Exception as e:
            print(f"查询诊断分布失败: {e}")
            return []
    
    def get_syndromes_distribution(
        self, 
        start_date: str = None, 
        end_date: str = None, 
        top_n: int = 30
    ) -> List[Dict[str, Any]]:
        """获取证候分布统计"""
        where_clause = "1=1"
        params = []
        
        if start_date:
            where_clause += " AND visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND visit_date <= ?"
            params.append(end_date)
        
        # 根据语言选择证候字段
        syndrome_field = {
            Language.ZH_CN: 'syndrome',
            Language.EN_US: 'syndrome_en',
            Language.JA_JP: 'syndrome_ja',
        }.get(self.language, 'syndrome')
        
        sql = f"""
            SELECT 
                {syndrome_field} as syndrome,
                COUNT(*) as frequency,
                COUNT(DISTINCT patient_id) as patient_count
            FROM prescriptions
            WHERE {where_clause}
                AND {syndrome_field} IS NOT NULL 
                AND {syndrome_field} != ''
            GROUP BY {syndrome_field}
            ORDER BY frequency DESC
            LIMIT ?
        """
        
        params.append(top_n)
        
        try:
            results = db_manager.execute_query(sql, tuple(params))
            return [
                {
                    'syndrome': r.get('syndrome', ''),
                    'frequency': r.get('frequency', 0),
                    'patient_count': r.get('patient_count', 0),
                }
                for r in results
            ]
        except Exception as e:
            print(f"查询证候分布失败: {e}")
            return []
    
    def get_timeline_trend(
        self, 
        start_date: str = None, 
        end_date: str = None, 
        granularity: str = 'day'
    ) -> List[Dict[str, Any]]:
        """获取时间趋势统计"""
        where_clause = "1=1"
        params = []
        
        if start_date:
            where_clause += " AND visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND visit_date <= ?"
            params.append(end_date)
        
        # 根据粒度确定日期格式
        date_format = {
            'day': '%Y-%m-%d',
            'week': '%Y-%W',
            'month': '%Y-%m',
            'quarter': '%Y-Q',
            'year': '%Y',
        }.get(granularity, '%Y-%m-%d')
        
        # SQLite日期函数
        if db_manager.config.db_type.value == 'sqlite':
            date_expr = f"strftime('{date_format}', visit_date)"
        else:
            # PostgreSQL
            date_formats = {
                'day': 'YYYY-MM-DD',
                'week': 'IYYY-IW',
                'month': 'YYYY-MM',
                'quarter': 'YYYY-Q',
                'year': 'YYYY',
            }
            date_expr = f"TO_CHAR(visit_date, '{date_formats.get(granularity, 'YYYY-MM-DD')}')"
        
        sql = f"""
            SELECT 
                {date_expr} as period,
                COUNT(*) as prescription_count,
                COUNT(DISTINCT patient_id) as patient_count,
                COUNT(DISTINCT doctor_id) as doctor_count,
                COUNT(DISTINCT diagnosis) as diagnosis_count
            FROM prescriptions
            WHERE {where_clause}
            GROUP BY period
            ORDER BY period
        """
        
        try:
            results = db_manager.execute_query(sql, tuple(params))
            return [
                {
                    'period': r.get('period', ''),
                    'prescription_count': r.get('prescription_count', 0),
                    'patient_count': r.get('patient_count', 0),
                    'doctor_count': r.get('doctor_count', 0),
                    'diagnosis_count': r.get('diagnosis_count', 0),
                }
                for r in results
            ]
        except Exception as e:
            print(f"查询时间趋势失败: {e}")
            return []
    
    def get_patient_statistics(self, start_date: str = None, end_date: str = None) -> Dict:
        """获取患者统计"""
        where_clause = "1=1"
        params = []
        
        if start_date:
            where_clause += " AND p.visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND p.visit_date <= ?"
            params.append(end_date)
        
        sql = f"""
            SELECT 
                pt.gender,
                pt.age,
                COUNT(*) as prescription_count
            FROM prescriptions p
            JOIN patients pt ON p.patient_id = pt.id
            WHERE {where_clause}
            GROUP BY pt.gender, pt.age
            ORDER BY prescription_count DESC
        """
        
        try:
            results = db_manager.execute_query(sql, tuple(params))
            
            gender_dist = {}
            age_dist = {}
            
            for r in results:
                gender = r.get('gender', 'unknown')
                age = r.get('age', 0)
                count = r.get('prescription_count', 0)
                
                gender_dist[gender] = gender_dist.get(gender, 0) + count
                
                if age:
                    age_group = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}"
                    age_dist[age_group] = age_dist.get(age_group, 0) + count
            
            return {
                'gender_distribution': gender_dist,
                'age_distribution': age_dist,
            }
        except Exception as e:
            print(f"查询患者统计失败: {e}")
            return {'gender_distribution': {}, 'age_distribution': {}}
    
    def get_doctor_statistics(self, start_date: str = None, end_date: str = None, top_n: int = 20) -> List[Dict]:
        """获取医生统计"""
        where_clause = "1=1"
        params = []
        
        if start_date:
            where_clause += " AND p.visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND p.visit_date <= ?"
            params.append(end_date)
        
        sql = f"""
            SELECT 
                d.id as doctor_id,
                d.name as doctor_name,
                d.name_en as doctor_name_en,
                d.name_ja as doctor_name_ja,
                d.title,
                d.department,
                COUNT(*) as prescription_count,
                COUNT(DISTINCT p.patient_id) as patient_count,
                COUNT(DISTINCT p.diagnosis) as diagnosis_count
            FROM prescriptions p
            LEFT JOIN doctors d ON p.doctor_id = d.id
            WHERE {where_clause}
            GROUP BY d.id
            ORDER BY prescription_count DESC
            LIMIT ?
        """
        
        params.append(top_n)
        
        try:
            results = db_manager.execute_query(sql, tuple(params))
            return [
                {
                    'doctor_id': r.get('doctor_id'),
                    'doctor_name': r.get('doctor_name', ''),
                    'doctor_name_en': r.get('doctor_name_en', ''),
                    'doctor_name_ja': r.get('doctor_name_ja', ''),
                    'title': r.get('title', ''),
                    'department': r.get('department', ''),
                    'prescription_count': r.get('prescription_count', 0),
                    'patient_count': r.get('patient_count', 0),
                    'diagnosis_count': r.get('diagnosis_count', 0),
                }
                for r in results
            ]
        except Exception as e:
            print(f"查询医生统计失败: {e}")
            return []
    
    def get_prescription_patterns(self, min_frequency: int = 3) -> List[Dict]:
        """获取处方模式（常见药物组合）"""
        # 这个需要更复杂的分析逻辑
        # 简化实现：找出常见的小处方组合（2-4味药）
        sql = """
            SELECT 
                p.id,
                p.prescription_code,
                GROUP_CONCAT(ph.herb_name, ',') as herbs,
                COUNT(ph.id) as herb_count,
                COUNT(DISTINCT p.patient_id) as patient_count
            FROM prescriptions p
            JOIN prescription_herbs ph ON p.id = ph.prescription_id
            WHERE p.status = 'active'
            GROUP BY p.id
            HAVING herb_count <= 5 AND herb_count >= 2
            ORDER BY patient_count DESC
            LIMIT 100
        """
        
        try:
            results = db_manager.execute_query(sql)
            
            # 统计相同药物组合的出现次数
            herb_combos = Counter()
            for r in results:
                herbs = r.get('herbs', '')
                if herbs:
                    herb_combos[herbs] += 1
            
            # 返回出现频率较高的组合
            patterns = []
            for herbs, freq in herb_combos.most_common(30):
                if freq >= min_frequency:
                    patterns.append({
                        'herbs': herbs.split(','),
                        'frequency': freq,
                    })
            
            return patterns
        except Exception as e:
            print(f"查询处方模式失败: {e}")
            return []
    
    def get_full_statistics_report(
        self, 
        start_date: str = None, 
        end_date: str = None
    ) -> Dict[str, Any]:
        """获取完整的统计报告"""
        return {
            'summary': self.get_prescription_summary(start_date, end_date),
            'herb_frequency': self.get_herb_frequency_stats(start_date, end_date, 50),
            'diagnosis_distribution': self.get_diagnosis_distribution(start_date, end_date, 30),
            'syndrome_distribution': self.get_syndromes_distribution(start_date, end_date, 30),
            'timeline_daily': self.get_timeline_trend(start_date, end_date, 'day'),
            'timeline_monthly': self.get_timeline_trend(start_date, end_date, 'month'),
            'patient_stats': self.get_patient_statistics(start_date, end_date),
            'doctor_stats': self.get_doctor_statistics(start_date, end_date, 20),
            'generated_at': datetime.now().isoformat(),
        }


class CloudChartGenerator:
    """词云图表生成器"""
    
    @staticmethod
    def generate_herb_cloud_data(herb_stats: List[Dict]) -> List[Dict]:
        """生成药材词云数据"""
        cloud_data = []
        
        for herb in herb_stats:
            name = herb.get('name', '')
            if not name:
                continue
            
            cloud_data.append({
                'name': name,
                'value': herb.get('frequency', 0),
                'name_en': herb.get('name_en', ''),
                'name_ja': herb.get('name_ja', ''),
            })
        
        return cloud_data
    
    @staticmethod
    def generate_diagnosis_cloud_data(diagnosis_stats: List[Dict]) -> List[Dict]:
        """生成诊断词云数据"""
        cloud_data = []
        
        for diag in diagnosis_stats:
            name = diag.get('diagnosis', '')
            if not name:
                continue
            
            cloud_data.append({
                'name': name,
                'value': diag.get('frequency', 0),
            })
        
        return cloud_data
    
    @staticmethod
    def generate_syndromes_cloud_data(syndrome_stats: List[Dict]) -> List[Dict]:
        """生成证候词云数据"""
        cloud_data = []
        
        for syn in syndrome_stats:
            name = syn.get('syndrome', '')
            if not name:
                continue
            
            cloud_data.append({
                'name': name,
                'value': syn.get('frequency', 0),
            })
        
        return cloud_data


# 创建全局统计实例
statistics_engine = StatisticsEngine()
cloud_generator = CloudChartGenerator()
