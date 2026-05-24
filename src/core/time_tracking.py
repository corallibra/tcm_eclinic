# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 时间追踪模块
追踪处方时间变化规律、病程进展、治疗方案变化
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import json

try:
    from src.core.database import db_manager, prescription_model
except ImportError:
    db_manager = None
    prescription_model = None
from src.core.i18n import Language, i18n, get_text


@dataclass
class PrescriptionChange:
    """处方变更记录"""
    prescription_id: str
    prescription_code: str
    visit_date: str
    changes: Dict[str, Any] = field(default_factory=dict)
    herbs_added: List[str] = field(default_factory=list)
    herbs_removed: List[str] = field(default_factory=list)
    herbs_modified: List[Dict] = field(default_factory=list)


@dataclass
class PatientTimeline:
    """患者时间线"""
    patient_id: str
    patient_name: str
    prescriptions: List[Dict] = field(default_factory=list)
    timeline_events: List[Dict] = field(default_factory=list)


class TimeTrackingEngine:
    """时间追踪引擎"""
    
    def __init__(self, language: Language = Language.ZH_CN):
        self.language = language
    
    def set_language(self, language: Language):
        """设置语言"""
        self.language = language
        i18n.set_language(language)
    
    def get_patient_timeline(
        self, 
        patient_id: str, 
        start_date: str = None, 
        end_date: str = None,
        limit: int = None
    ) -> PatientTimeline:
        """获取患者完整时间线"""
        # 获取患者信息
        patient_sql = "SELECT * FROM patients WHERE id = ?"
        patient_result = db_manager.execute_query(patient_sql, (patient_id,))
        
        if not patient_result:
            return None
        
        patient = patient_result[0]
        
        # 构建查询条件
        where_clause = "patient_id = ?"
        params = [patient_id]
        
        if start_date:
            where_clause += " AND visit_date >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND visit_date <= ?"
            params.append(end_date)
        
        # 获取所有处方
        prescription_sql = f"""
            SELECT p.*, d.name as doctor_name, d.name_en as doctor_name_en, d.name_ja as doctor_name_ja
            FROM prescriptions p
            LEFT JOIN doctors d ON p.doctor_id = d.id
            WHERE {where_clause}
            ORDER BY visit_date ASC, created_at ASC
        """
        
        if limit:
            prescription_sql += f" LIMIT {limit}"
        
        prescriptions = db_manager.execute_query(prescription_sql, tuple(params))
        
        # 获取每个处方的药物明细
        for prescription in prescriptions:
            herbs_sql = """
                SELECT herb_name, herb_name_en, herb_name_ja, dose, dose_unit, processing
                FROM prescription_herbs
                WHERE prescription_id = ?
                ORDER BY sort_order
            """
            herbs = db_manager.execute_query(herbs_sql, (prescription['id'],))
            prescription['herbs'] = herbs
        
        # 生成时间线事件
        timeline_events = self._generate_timeline_events(prescriptions)
        
        return PatientTimeline(
            patient_id=patient_id,
            patient_name=patient.get('name', ''),
            prescriptions=prescriptions,
            timeline_events=timeline_events
        )
    
    def _generate_timeline_events(self, prescriptions: List[Dict]) -> List[Dict]:
        """生成时间线事件"""
        events = []
        
        for idx, prescription in enumerate(prescriptions):
            event = {
                'type': 'visit',
                'date': prescription.get('visit_date', ''),
                'prescription_id': prescription.get('id', ''),
                'prescription_code': prescription.get('prescription_code', ''),
                'doctor': prescription.get('doctor_name', ''),
                'diagnosis': prescription.get('diagnosis', ''),
                'diagnosis_en': prescription.get('diagnosis_en', ''),
                'diagnosis_ja': prescription.get('diagnosis_ja', ''),
                'syndrome': prescription.get('syndrome', ''),
                'chief_complaint': prescription.get('chief_complaint', ''),
                'herbs': prescription.get('herbs', []),
            }
            
            # 检测变更
            if idx > 0:
                prev_prescription = prescriptions[idx - 1]
                changes = self._detect_changes(prev_prescription, prescription)
                if changes:
                    event['changes'] = changes
            
            events.append(event)
        
        return events
    
    def _detect_changes(
        self, 
        prev: Dict, 
        current: Dict
    ) -> Dict[str, Any]:
        """检测两次就诊之间的变更"""
        changes = {}
        
        # 诊断变更
        if prev.get('diagnosis') != current.get('diagnosis'):
            changes['diagnosis'] = {
                'from': prev.get('diagnosis'),
                'to': current.get('diagnosis'),
            }
        
        # 证候变更
        if prev.get('syndrome') != current.get('syndrome'):
            changes['syndrome'] = {
                'from': prev.get('syndrome'),
                'to': current.get('syndrome'),
            }
        
        # 主诉变更
        if prev.get('chief_complaint') != current.get('chief_complaint'):
            changes['chief_complaint'] = {
                'from': prev.get('chief_complaint'),
                'to': current.get('chief_complaint'),
            }
        
        # 舌脉变更
        if prev.get('tongue') != current.get('tongue'):
            changes['tongue'] = {
                'from': prev.get('tongue'),
                'to': current.get('tongue'),
            }
        if prev.get('pulse') != current.get('pulse'):
            changes['pulse'] = {
                'from': prev.get('pulse'),
                'to': current.get('pulse'),
            }
        
        # 药物变更
        prev_herbs = {h['herb_name']: h for h in prev.get('herbs', [])}
        curr_herbs = {h['herb_name']: h for h in current.get('herbs', [])}
        
        herbs_added = [h for h in curr_herbs.keys() if h not in prev_herbs]
        herbs_removed = [h for h in prev_herbs.keys() if h not in curr_herbs]
        herbs_modified = []
        
        for herb_name in set(prev_herbs.keys()) & set(curr_herbs.keys()):
            prev_herb = prev_herbs[herb_name]
            curr_herb = curr_herbs[herb_name]
            
            if prev_herb.get('dose') != curr_herb.get('dose'):
                herbs_modified.append({
                    'herb_name': herb_name,
                    'prev_dose': prev_herb.get('dose'),
                    'curr_dose': curr_herb.get('dose'),
                })
        
        if herbs_added or herbs_removed or herbs_modified:
            changes['herbs'] = {
                'added': herbs_added,
                'removed': herbs_removed,
                'modified': herbs_modified,
            }
        
        return changes
    
    def get_prescription_changes(
        self, 
        patient_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> List[PrescriptionChange]:
        """获取处方变更记录"""
        # 获取患者所有处方
        prescriptions = prescription_model.get_patient_prescriptions(patient_id)
        
        if not prescriptions:
            return []
        
        # 按时间排序
        prescriptions.sort(key=lambda x: x.get('visit_date', ''))
        
        changes = []
        for idx in range(1, len(prescriptions)):
            prev = prescriptions[idx - 1]
            curr = prescriptions[idx]
            
            detected_changes = self._detect_changes(prev, curr)
            
            if detected_changes:
                change = PrescriptionChange(
                    prescription_id=curr.get('id', ''),
                    prescription_code=curr.get('prescription_code', ''),
                    visit_date=curr.get('visit_date', ''),
                    changes=detected_changes,
                )
                
                if 'herbs' in detected_changes:
                    change.herbs_added = detected_changes['herbs'].get('added', [])
                    change.herbs_removed = detected_changes['herbs'].get('removed', [])
                    change.herbs_modified = detected_changes['herbs'].get('modified', [])
                
                changes.append(change)
        
        return changes
    
    def analyze_disease_progression(
        self, 
        patient_id: str
    ) -> Dict[str, Any]:
        """分析病程进展"""
        timeline = self.get_patient_timeline(patient_id)
        
        if not timeline:
            return {}
        
        prescriptions = timeline.prescriptions
        
        # 提取所有诊断
        diagnoses = []
        for p in prescriptions:
            if p.get('diagnosis'):
                diagnoses.append({
                    'date': p.get('visit_date', ''),
                    'diagnosis': p.get('diagnosis', ''),
                })
        
        # 提取所有证候变化
        syndromes = []
        for p in prescriptions:
            if p.get('syndrome'):
                syndromes.append({
                    'date': p.get('visit_date', ''),
                    'syndrome': p.get('syndrome', ''),
                })
        
        # 提取症状变化
        symptoms = []
        for p in prescriptions:
            if p.get('chief_complaint'):
                symptoms.append({
                    'date': p.get('visit_date', ''),
                    'symptoms': p.get('chief_complaint', ''),
                })
        
        # 计算病程持续时间
        if prescriptions:
            first_date = datetime.fromisoformat(prescriptions[0].get('visit_date', datetime.now().isoformat()))
            last_date = datetime.fromisoformat(prescriptions[-1].get('visit_date', datetime.now().isoformat()))
            duration_days = (last_date - first_date).days
        else:
            duration_days = 0
        
        return {
            'patient_name': timeline.patient_name,
            'total_visits': len(prescriptions),
            'duration_days': duration_days,
            'first_visit': prescriptions[0].get('visit_date') if prescriptions else None,
            'last_visit': prescriptions[-1].get('visit_date') if prescriptions else None,
            'diagnoses': diagnoses,
            'syndromes': syndromes,
            'symptoms': symptoms,
            'prescriptions': prescriptions,
        }
    
    def analyze_treatment_evolution(
        self, 
        patient_id: str
    ) -> Dict[str, Any]:
        """分析治疗方案演变"""
        timeline = self.get_patient_timeline(patient_id)
        
        if not timeline:
            return {}
        
        prescriptions = timeline.prescriptions
        
        # 分析药物变化趋势
        herb_trends = defaultdict(list)
        total_dose_trends = []
        herb_count_trends = []
        
        for p in prescriptions:
            herbs = p.get('herbs', [])
            total_dose = sum(float(h.get('dose', 0)) for h in herbs)
            herb_count = len(herbs)
            
            total_dose_trends.append({
                'date': p.get('visit_date', ''),
                'total_dose': total_dose,
            })
            
            herb_count_trends.append({
                'date': p.get('visit_date', ''),
                'herb_count': herb_count,
            })
            
            for h in herbs:
                herb_name = h.get('herb_name', '')
                herb_trends[herb_name].append({
                    'date': p.get('visit_date', ''),
                    'dose': h.get('dose', 0),
                })
        
        # 找出核心药物（持续使用的药物）
        core_herbs = []
        for herb_name, trend in herb_trends.items():
            if len(trend) >= len(prescriptions) * 0.5:  # 超过一半的处方中都有
                core_herbs.append(herb_name)
        
        return {
            'total_dose_trends': total_dose_trends,
            'herb_count_trends': herb_count_trends,
            'herb_trends': dict(herb_trends),
            'core_herbs': core_herbs,
            'prescription_count': len(prescriptions),
        }
    
    def get_prescription_pattern_by_period(
        self,
        patient_id: str,
        period_days: int = 30
    ) -> List[Dict]:
        """按时间段分析处方模式"""
        prescriptions = prescription_model.get_patient_prescriptions(patient_id)
        
        if not prescriptions:
            return []
        
        # 按时间段分组
        periods = defaultdict(list)
        for p in prescriptions:
            visit_date = datetime.fromisoformat(p.get('visit_date', datetime.now().isoformat()))
            period_start = visit_date.replace(day=1).strftime('%Y-%m')
            periods[period_start].append(p)
        
        # 分析每个时期的药物模式
        period_analyses = []
        for period, period_prescriptions in sorted(periods.items()):
            all_herbs = []
            for p in period_prescriptions:
                herbs = p.get('herbs', [])
                all_herbs.extend([h.get('herb_name', '') for h in herbs])
            
            # 统计高频药物
            herb_freq = defaultdict(int)
            for herb in all_herbs:
                if herb:
                    herb_freq[herb] += 1
            
            # 平均剂量
            doses_by_herb = defaultdict(list)
            for p in period_prescriptions:
                for h in p.get('herbs', []):
                    dose = h.get('dose')
                    if dose:
                        doses_by_herb[h.get('herb_name', '')].append(float(dose))
            
            avg_doses = {
                herb: sum(doses) / len(doses) if doses else 0
                for herb, doses in doses_by_herb.items()
            }
            
            period_analyses.append({
                'period': period,
                'prescription_count': len(period_prescriptions),
                'top_herbs': sorted(herb_freq.items(), key=lambda x: x[1], reverse=True)[:10],
                'avg_doses': avg_doses,
                'avg_herb_count': len(all_herbs) / len(period_prescriptions) if period_prescriptions else 0,
            })
        
        return period_analyses
    
    def compare_treatment_periods(
        self,
        patient_id: str,
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str
    ) -> Dict[str, Any]:
        """比较两个治疗时期的差异"""
        def analyze_period(start, end):
            prescriptions = prescription_model.get_patient_prescriptions(patient_id)
            prescriptions = [
                p for p in prescriptions
                if start <= p.get('visit_date', '') <= end
            ]
            
            all_herbs = []
            diagnoses = set()
            syndromes = set()
            total_doses = []
            
            for p in prescriptions:
                herbs = p.get('herbs', [])
                all_herbs.extend([h.get('herb_name', '') for h in herbs])
                total_doses.append(sum(float(h.get('dose', 0)) for h in herbs))
                
                if p.get('diagnosis'):
                    diagnoses.add(p.get('diagnosis'))
                if p.get('syndrome'):
                    syndromes.add(p.get('syndrome'))
            
            herb_freq = Counter(all_herbs)
            
            return {
                'prescription_count': len(prescriptions),
                'unique_diagnoses': list(diagnoses),
                'unique_syndromes': list(syndromes),
                'top_herbs': herb_freq.most_common(10),
                'avg_herb_count': len(all_herbs) / len(prescriptions) if prescriptions else 0,
                'avg_total_dose': sum(total_doses) / len(total_doses) if total_doses else 0,
            }
        
        period1_analysis = analyze_period(period1_start, period1_end)
        period2_analysis = analyze_period(period2_start, period2_end)
        
        # 计算变化
        herbs_added = set([h[0] for h in period2_analysis['top_herbs']]) - \
                     set([h[0] for h in period1_analysis['top_herbs']])
        herbs_removed = set([h[0] for h in period1_analysis['top_herbs']]) - \
                       set([h[0] for h in period2_analysis['top_herbs']])
        
        return {
            'period1': {
                'start': period1_start,
                'end': period1_end,
                'analysis': period1_analysis,
            },
            'period2': {
                'start': period2_start,
                'end': period2_end,
                'analysis': period2_analysis,
            },
            'changes': {
                'herbs_added': list(herbs_added),
                'herbs_removed': list(herbs_removed),
                'avg_herb_count_change': period2_analysis['avg_herb_count'] - period1_analysis['avg_herb_count'],
                'avg_total_dose_change': period2_analysis['avg_total_dose'] - period1_analysis['avg_total_dose'],
            },
        }
    
    def get_treatment_summary(
        self,
        patient_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """获取治疗总结报告"""
        timeline = self.get_patient_timeline(patient_id, start_date, end_date)
        
        if not timeline:
            return {}
        
        prescriptions = timeline.prescriptions
        
        if not prescriptions:
            return {'message': '无就诊记录'}
        
        # 基本统计
        first_visit = prescriptions[0]
        last_visit = prescriptions[-1]
        total_visits = len(prescriptions)
        
        # 药物使用统计
        all_herbs = []
        for p in prescriptions:
            for h in p.get('herbs', []):
                all_herbs.append(h.get('herb_name', ''))
        
        herb_counter = Counter(all_herbs)
        
        # 诊断和证候统计
        diagnoses = [p.get('diagnosis', '') for p in prescriptions if p.get('diagnosis')]
        syndromes = [p.get('syndrome', '') for p in prescriptions if p.get('syndrome')]
        
        return {
            'patient_name': timeline.patient_name,
            'report_period': {
                'start': start_date,
                'end': end_date,
            },
            'basic_stats': {
                'total_visits': total_visits,
                'first_visit_date': first_visit.get('visit_date'),
                'last_visit_date': last_visit.get('visit_date'),
                'duration_days': (datetime.fromisoformat(last_visit.get('visit_date', datetime.now().isoformat())) - 
                                 datetime.fromisoformat(first_visit.get('visit_date', datetime.now().isoformat()))).days,
            },
            'diagnosis_stats': {
                'unique_diagnoses': len(set(diagnoses)),
                'most_common': Counter(diagnoses).most_common(5),
            },
            'syndrome_stats': {
                'unique_syndromes': len(set(syndromes)),
                'most_common': Counter(syndromes).most_common(5),
            },
            'herb_stats': {
                'total_herb_types': len(herb_counter),
                'total_herb_usages': len(all_herbs),
                'most_frequently_used': herb_counter.most_common(10),
            },
            'treatment_evolution': self.analyze_treatment_evolution(patient_id),
        }


# 创建全局时间追踪实例
time_tracking_engine = TimeTrackingEngine()
