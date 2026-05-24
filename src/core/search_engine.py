# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 高级搜索模块
支持多维度检索：病种、姓名、症状、药味、时间等
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import re

try:
    from src.core.database import db_manager, prescription_model, patient_model
except ImportError:
    db_manager = None
    prescription_model = None
    patient_model = None
from src.core.i18n import Language, i18n, get_text


class SearchField(Enum):
    """搜索字段枚举"""
    PRESCRIPTION_CODE = "prescription_code"
    PATIENT_NAME = "patient_name"
    PATIENT_NAME_EN = "patient_name_en"
    PATIENT_NAME_JA = "patient_name_ja"
    DIAGNOSIS = "diagnosis"
    DIAGNOSIS_EN = "diagnosis_en"
    DIAGNOSIS_JA = "diagnosis_ja"
    SYNDROME = "syndrome"
    SYNDROME_EN = "syndrome_en"
    SYNDROME_JA = "syndrome_ja"
    CHIEF_COMPLAINT = "chief_complaint"
    SYMPTOMS = "symptoms"
    HERB_NAME = "herb_name"
    DOCTOR_NAME = "doctor_name"
    VISIT_DATE = "visit_date"
    ALL = "all"


class TimeRange(Enum):
    """时间范围枚举"""
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    THIS_QUARTER = "this_quarter"
    THIS_YEAR = "this_year"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    CUSTOM = "custom"


@dataclass
class SearchCondition:
    """搜索条件"""
    field: SearchField = SearchField.ALL
    value: str = ""
    operator: str = "like"  # like, exact, gt, lt, gte, lte, in
    enabled: bool = True


@dataclass
class SearchQuery:
    """搜索查询"""
    keyword: str = ""
    conditions: List[SearchCondition] = field(default_factory=list)
    time_range: Optional[TimeRange] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    language: Language = Language.ZH_CN
    sort_by: str = "visit_date"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 50


class AdvancedSearchEngine:
    """高级搜索引擎"""
    
    def __init__(self, language: Language = Language.ZH_CN):
        self.language = language
        self.search_history: List[Dict] = []
        self.favorites: List[Dict] = []
    
    def set_language(self, language: Language):
        """设置搜索语言"""
        self.language = language
        i18n.set_language(language)
    
    def _get_time_range(self, time_range: TimeRange) -> Tuple[str, str]:
        """获取时间范围"""
        today = datetime.now().date()
        
        ranges = {
            TimeRange.TODAY: (today.isoformat(), today.isoformat()),
            TimeRange.YESTERDAY: ((today - timedelta(days=1)).isoformat(), (today - timedelta(days=1)).isoformat()),
            TimeRange.THIS_WEEK: ((today - timedelta(days=today.weekday())).isoformat(), today.isoformat()),
            TimeRange.THIS_MONTH: ((today.replace(day=1)).isoformat(), today.isoformat()),
            TimeRange.THIS_QUARTER: ((today - timedelta(days=today.timetuple().tm_yday % 90)).isoformat(), today.isoformat()),
            TimeRange.THIS_YEAR: ((today.replace(month=1, day=1)).isoformat(), today.isoformat()),
            TimeRange.LAST_7_DAYS: ((today - timedelta(days=7)).isoformat(), today.isoformat()),
            TimeRange.LAST_30_DAYS: ((today - timedelta(days=30)).isoformat(), today.isoformat()),
            TimeRange.LAST_90_DAYS: ((today - timedelta(days=90)).isoformat(), today.isoformat()),
        }
        
        return ranges.get(time_range, (None, None))
    
    def _build_query_conditions(self, query: SearchQuery) -> Tuple[str, List]:
        """构建查询条件"""
        conditions = []
        params = []
        
        # 关键词搜索
        if query.keyword:
            kw = f"%{query.keyword}%"
            if self.language == Language.ZH_CN:
                conditions.append("""
                    (p.diagnosis LIKE ? OR p.syndrome LIKE ? OR 
                     p.chief_complaint LIKE ? OR p.symptoms LIKE ? OR
                     pt.name LIKE ?)
                """)
            elif self.language == Language.EN_US:
                conditions.append("""
                    (p.diagnosis_en LIKE ? OR p.syndrome_en LIKE ? OR 
                     p.chief_complaint_en LIKE ? OR p.symptoms_en LIKE ? OR
                     pt.name_en LIKE ?)
                """)
            else:  # JA_JP
                conditions.append("""
                    (p.diagnosis_ja LIKE ? OR p.syndrome_ja LIKE ? OR 
                     p.chief_complaint_ja LIKE ? OR p.symptoms_ja LIKE ? OR
                     pt.name_ja LIKE ?)
                """)
            
            params.extend([kw] * 5)
        
        # 自定义条件
        for cond in query.conditions:
            if not cond.enabled or not cond.value:
                continue
            
            if cond.field == SearchField.PATIENT_NAME:
                conditions.append("pt.name LIKE ?")
                params.append(f"%{cond.value}%")
            elif cond.field == SearchField.DIAGNOSIS:
                conditions.append("p.diagnosis LIKE ?")
                params.append(f"%{cond.value}%")
            elif cond.field == SearchField.SYNDROME:
                conditions.append("p.syndrome LIKE ?")
                params.append(f"%{cond.value}%")
            elif cond.field == SearchField.HERB_NAME:
                # 特殊处理：需要关联查询
                conditions.append("EXISTS (SELECT 1 FROM prescription_herbs ph WHERE ph.prescription_id = p.id AND ph.herb_name LIKE ?)")
                params.append(f"%{cond.value}%")
            elif cond.field == SearchField.VISIT_DATE:
                if cond.operator == "gte":
                    conditions.append("p.visit_date >= ?")
                elif cond.operator == "lte":
                    conditions.append("p.visit_date <= ?")
                else:
                    conditions.append("DATE(p.visit_date) = ?")
                params.append(cond.value)
        
        # 时间范围
        if query.time_range and query.time_range != TimeRange.CUSTOM:
            start, end = self._get_time_range(query.time_range)
            if start:
                conditions.append("p.visit_date >= ?")
                params.append(start)
            if end:
                conditions.append("p.visit_date <= ?")
                params.append(end)
        elif query.start_date:
            conditions.append("p.visit_date >= ?")
            params.append(query.start_date)
        if query.end_date:
            conditions.append("p.visit_date <= ?")
            params.append(query.end_date)
        
        # 患者ID
        if query.patient_id:
            conditions.append("p.patient_id = ?")
            params.append(query.patient_id)
        
        # 医生ID
        if query.doctor_id:
            conditions.append("p.doctor_id = ?")
            params.append(query.doctor_id)
        
        return " AND ".join(conditions) if conditions else "1=1", params
    
    def search(self, query: SearchQuery) -> Tuple[List[Dict], int, Dict]:
        """
        执行高级搜索
        
        Returns:
            Tuple of (results, total_count, metadata)
        """
        # 构建基础查询
        where_clause, params = self._build_query_conditions(query)
        
        # 排序
        sort_mapping = {
            "visit_date": "p.visit_date",
            "created_at": "p.created_at",
            "diagnosis": "p.diagnosis",
            "patient_name": "pt.name",
        }
        sort_field = sort_mapping.get(query.sort_by, "p.visit_date")
        sort_order = "DESC" if query.sort_order.lower() == "desc" else "ASC"
        
        # 统计总数
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM prescriptions p
            LEFT JOIN patients pt ON p.patient_id = pt.id
            WHERE {where_clause}
        """
        
        try:
            count_result = db_manager.execute_query(count_sql, tuple(params))
            total = count_result[0]['total'] if count_result else 0
        except:
            total = 0
        
        # 分页
        offset = (query.page - 1) * query.page_size
        
        # 查询数据
        sql = f"""
            SELECT 
                p.*,
                pt.name as patient_name,
                pt.name_en as patient_name_en,
                pt.name_ja as patient_name_ja,
                pt.gender as patient_gender,
                pt.age as patient_age,
                d.name as doctor_name
            FROM prescriptions p
            LEFT JOIN patients pt ON p.patient_id = pt.id
            LEFT JOIN doctors d ON p.doctor_id = d.id
            WHERE {where_clause}
            ORDER BY {sort_field} {sort_order}
            LIMIT ? OFFSET ?
        """
        
        params.extend([query.page_size, offset])
        
        try:
            results = db_manager.execute_query(sql, tuple(params))
            
            # 获取每个处方的药物明细
            for result in results:
                herbs_sql = """
                    SELECT herb_name, herb_name_en, herb_name_ja, dose, dose_unit, processing
                    FROM prescription_herbs
                    WHERE prescription_id = ?
                    ORDER BY sort_order
                """
                herbs = db_manager.execute_query(herbs_sql, (result['id'],))
                result['herbs'] = herbs
        except Exception as e:
            print(f"查询失败: {e}")
            results = []
        
        # 保存搜索历史
        self._save_search_history(query, total)
        
        # 构建元数据
        metadata = {
            'page': query.page,
            'page_size': query.page_size,
            'total': total,
            'total_pages': (total + query.page_size - 1) // query.page_size if query.page_size > 0 else 0,
            'has_next': offset + query.page_size < total,
            'has_prev': query.page > 1,
        }
        
        return results, total, metadata
    
    def _save_search_history(self, query: SearchQuery, result_count: int):
        """保存搜索历史"""
        history_item = {
            'keyword': query.keyword,
            'time_range': query.time_range.value if query.time_range else None,
            'start_date': query.start_date,
            'end_date': query.end_date,
            'result_count': result_count,
            'timestamp': datetime.now().isoformat(),
            'language': self.language.value,
        }
        
        self.search_history.insert(0, history_item)
        
        # 只保留最近100条历史
        if len(self.search_history) > 100:
            self.search_history = self.search_history[:100]
    
    def get_search_history(self, limit: int = 20) -> List[Dict]:
        """获取搜索历史"""
        return self.search_history[:limit]
    
    def clear_search_history(self):
        """清除搜索历史"""
        self.search_history = []
    
    def add_favorite(self, query: SearchQuery, name: str):
        """添加收藏的搜索"""
        favorite = {
            'name': name,
            'keyword': query.keyword,
            'conditions': [{'field': c.field.value, 'value': c.value, 'operator': c.operator} 
                         for c in query.conditions if c.enabled],
            'time_range': query.time_range.value if query.time_range else None,
            'language': self.language.value,
            'created_at': datetime.now().isoformat(),
        }
        
        self.favorites.append(favorite)
    
    def get_favorites(self) -> List[Dict]:
        """获取收藏的搜索"""
        return self.favorites
    
    def remove_favorite(self, index: int):
        """删除收藏"""
        if 0 <= index < len(self.favorites):
            self.favorites.pop(index)
    
    def get_suggestions(self, prefix: str, field: SearchField = SearchField.ALL) -> List[str]:
        """获取搜索建议（自动补全）"""
        suggestions = set()
        prefix_lower = prefix.lower()
        
        if field in [SearchField.ALL, SearchField.DIAGNOSIS]:
            # 从诊断中提取建议
            sql = """
                SELECT DISTINCT diagnosis FROM prescriptions 
                WHERE diagnosis IS NOT NULL AND diagnosis LIKE ?
                LIMIT 10
            """
            results = db_manager.execute_query(sql, (f"%{prefix}%",))
            for r in results:
                if r['diagnosis']:
                    suggestions.add(r['diagnosis'])
        
        if field in [SearchField.ALL, SearchField.SYNDROME]:
            # 从证候中提取建议
            sql = """
                SELECT DISTINCT syndrome FROM prescriptions 
                WHERE syndrome IS NOT NULL AND syndrome LIKE ?
                LIMIT 10
            """
            results = db_manager.execute_query(sql, (f"%{prefix}%",))
            for r in results:
                if r['syndrome']:
                    suggestions.add(r['syndrome'])
        
        if field in [SearchField.ALL, SearchField.HERB_NAME]:
            # 从药物中提取建议
            sql = """
                SELECT DISTINCT herb_name FROM prescription_herbs 
                WHERE herb_name LIKE ?
                LIMIT 10
            """
            results = db_manager.execute_query(sql, (f"%{prefix}%",))
            for r in results:
                if r['herb_name']:
                    suggestions.add(r['herb_name'])
        
        if field in [SearchField.ALL, SearchField.PATIENT_NAME]:
            # 从患者姓名中提取建议
            sql = """
                SELECT DISTINCT name FROM patients 
                WHERE name LIKE ?
                LIMIT 10
            """
            results = db_manager.execute_query(sql, (f"%{prefix}%",))
            for r in results:
                if r['name']:
                    suggestions.add(r['name'])
        
        # 过滤并返回
        return [s for s in suggestions if prefix_lower in s.lower()][:10]
    
    def export_results(self, results: List[Dict], format: str = 'json') -> str:
        """导出搜索结果"""
        if format == 'json':
            return json.dumps(results, ensure_ascii=False, indent=2, default=str)
        elif format == 'csv':
            if not results:
                return ""
            
            headers = ['处方编号', '患者姓名', '就诊日期', '诊断', '证候', '药物', '医生']
            rows = []
            
            for r in results:
                herbs = [h['herb_name'] for h in r.get('herbs', [])]
                rows.append([
                    r.get('prescription_code', ''),
                    r.get('patient_name', ''),
                    r.get('visit_date', ''),
                    r.get('diagnosis', ''),
                    r.get('syndrome', ''),
                    ', '.join(herbs),
                    r.get('doctor_name', ''),
                ])
            
            lines = [','.join(headers)]
            for row in rows:
                lines.append(','.join([f'"{v}"' for v in row]))
            
            return '\n'.join(lines)
        
        return ""


class SearchFilterBuilder:
    """搜索过滤器构建器"""
    
    @staticmethod
    def build_prescription_filter(
        disease: str = None,
        symptom: str = None,
        herb: str = None,
        patient_name: str = None,
        start_date: str = None,
        end_date: str = None,
        language: str = 'zh_CN'
    ) -> SearchQuery:
        """构建处方搜索过滤器"""
        query = SearchQuery(language=Language(language) if language else Language.ZH_CN)
        
        if disease:
            query.conditions.append(SearchCondition(
                field=SearchField.DIAGNOSIS,
                value=disease
            ))
        
        if symptom:
            query.conditions.append(SearchCondition(
                field=SearchField.SYMPTOMS,
                value=symptom
            ))
        
        if herb:
            query.conditions.append(SearchCondition(
                field=SearchField.HERB_NAME,
                value=herb
            ))
        
        if patient_name:
            query.conditions.append(SearchCondition(
                field=SearchField.PATIENT_NAME,
                value=patient_name
            ))
        
        query.start_date = start_date
        query.end_date = end_date
        
        return query
    
    @staticmethod
    def build_patient_filter(
        name: str = None,
        gender: str = None,
        age_min: int = None,
        age_max: int = None,
        language: str = 'zh_CN'
    ) -> Dict:
        """构建患者搜索过滤器"""
        return {
            'name': name,
            'gender': gender,
            'age_min': age_min,
            'age_max': age_max,
            'language': language,
        }


class SearchStatistics:
    """搜索统计分析"""
    
    @staticmethod
    def get_hot_searches(limit: int = 10) -> List[Dict]:
        """获取热门搜索词"""
        # 简化实现，实际可以从数据库或缓存中获取
        return []
    
    @staticmethod
    def get_search_trend(days: int = 30) -> List[Dict]:
        """获取搜索趋势"""
        return []


# 创建全局搜索实例
search_engine = AdvancedSearchEngine()
