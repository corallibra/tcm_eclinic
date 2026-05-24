# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 多语言处方编辑器
支持中文、英文、日语三国语言的处方录入和编辑
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import json

from src.core.i18n import Language, i18n, get_text
try:
    from src.core.database import prescription_model, patient_model
except ImportError:
    prescription_model = None
    patient_model = None


@dataclass
class HerbItem:
    """药物明细项"""
    name: str = ""
    name_en: str = ""
    name_ja: str = ""
    dose: float = 0.0
    dose_unit: str = "g"
    dose_unit_en: str = "g"
    dose_unit_ja: str = "g"
    usage: str = ""
    usage_en: str = ""
    usage_ja: str = ""
    processing: str = ""
    processing_en: str = ""
    processing_ja: str = ""
    notes: str = ""


class MultiLanguagePrescriptionEditor:
    """多语言处方编辑器"""
    
    def __init__(self, language: Language = Language.ZH_CN):
        self.language = language
        self.prescription_id: Optional[str] = None
        self.prescription_code: Optional[str] = None
        
        # 患者信息
        self.patient_id: Optional[str] = None
        self.patient_name: str = ""
        self.patient_name_en: str = ""
        self.patient_name_ja: str = ""
        self.patient_gender: str = ""
        self.patient_age: int = 0
        
        # 处方信息
        self.visit_date: str = datetime.now().strftime("%Y-%m-%d")
        self.doctor_id: Optional[str] = None
        self.doctor_name: str = ""
        
        # 诊断信息（多语言）
        self.diagnosis: str = ""
        self.diagnosis_en: str = ""
        self.diagnosis_ja: str = ""
        
        # 证候信息（多语言）
        self.syndrome: str = ""
        self.syndrome_en: str = ""
        self.syndrome_ja: str = ""
        
        # 主诉（多语言）
        self.chief_complaint: str = ""
        self.chief_complaint_en: str = ""
        self.chief_complaint_ja: str = ""
        
        # 症状（多语言）
        self.symptoms: str = ""
        self.symptoms_en: str = ""
        self.symptoms_ja: str = ""
        
        # 舌脉（多语言）
        self.tongue: str = ""
        self.tongue_en: str = ""
        self.tongue_ja: str = ""
        
        self.pulse: str = ""
        self.pulse_en: str = ""
        self.pulse_ja: str = ""
        
        # 治法（多语言）
        self.treatment_method: str = ""
        self.treatment_method_en: str = ""
        self.treatment_method_ja: str = ""
        
        # 处方药物明细
        self.herbs: List[HerbItem] = []
        
        # 其他信息
        self.notes: str = ""
        self.privacy_level: str = "doctor_only"
        self.created_by: Optional[str] = None
    
    def set_language(self, language: Language):
        """设置编辑器语言"""
        self.language = language
        i18n.set_language(language)
    
    def get_current_text(self, field: str) -> str:
        """根据当前语言获取字段值"""
        lang_suffix = {
            Language.ZH_CN: "",
            Language.EN_US: "_en",
            Language.JA_JP: "_ja"
        }.get(self.language, "")
        
        return getattr(self, f"{field}{lang_suffix}", "")
    
    def set_current_text(self, field: str, value: str):
        """根据当前语言设置字段值"""
        lang_suffix = {
            Language.ZH_CN: "",
            Language.EN_US: "_en",
            Language.JA_JP: "_ja"
        }.get(self.language, "")
        
        setattr(self, f"{field}{lang_suffix}", value)
    
    def add_herb(self, herb: HerbItem):
        """添加药物"""
        self.herbs.append(herb)
    
    def remove_herb(self, index: int):
        """删除药物"""
        if 0 <= index < len(self.herbs):
            self.herbs.pop(index)
    
    def update_herb(self, index: int, herb: HerbItem):
        """更新药物"""
        if 0 <= index < len(self.herbs):
            self.herbs[index] = herb
    
    def move_herb(self, from_index: int, to_index: int):
        """移动药物顺序"""
        if 0 <= from_index < len(self.herbs) and 0 <= to_index < len(self.herbs):
            herb = self.herbs.pop(from_index)
            self.herbs.insert(to_index, herb)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.prescription_id,
            'prescription_code': self.prescription_code,
            'patient_id': self.patient_id,
            'patient_name': self.patient_name,
            'patient_name_en': self.patient_name_en,
            'patient_name_ja': self.patient_name_ja,
            'patient_gender': self.patient_gender,
            'patient_age': self.patient_age,
            'visit_date': self.visit_date,
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor_name,
            'diagnosis': self.diagnosis,
            'diagnosis_en': self.diagnosis_en,
            'diagnosis_ja': self.diagnosis_ja,
            'syndrome': self.syndrome,
            'syndrome_en': self.syndrome_en,
            'syndrome_ja': self.syndrome_ja,
            'chief_complaint': self.chief_complaint,
            'chief_complaint_en': self.chief_complaint_en,
            'chief_complaint_ja': self.chief_complaint_ja,
            'symptoms': self.symptoms,
            'symptoms_en': self.symptoms_en,
            'symptoms_ja': self.symptoms_ja,
            'tongue': self.tongue,
            'tongue_en': self.tongue_en,
            'tongue_ja': self.tongue_ja,
            'pulse': self.pulse,
            'pulse_en': self.pulse_en,
            'pulse_ja': self.pulse_ja,
            'treatment_method': self.treatment_method,
            'treatment_method_en': self.treatment_method_en,
            'treatment_method_ja': self.treatment_method_ja,
            'herbs': [asdict(h) for h in self.herbs],
            'notes': self.notes,
            'privacy_level': self.privacy_level,
            'created_by': self.created_by,
            'language': self.language.value
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """从字典加载"""
        self.prescription_id = data.get('id')
        self.prescription_code = data.get('prescription_code')
        self.patient_id = data.get('patient_id')
        self.patient_name = data.get('patient_name', '')
        self.patient_name_en = data.get('patient_name_en', '')
        self.patient_name_ja = data.get('patient_name_ja', '')
        self.patient_gender = data.get('patient_gender', '')
        self.patient_age = data.get('patient_age', 0)
        self.visit_date = data.get('visit_date', datetime.now().strftime("%Y-%m-%d"))
        self.doctor_id = data.get('doctor_id')
        self.doctor_name = data.get('doctor_name', '')
        
        self.diagnosis = data.get('diagnosis', '')
        self.diagnosis_en = data.get('diagnosis_en', '')
        self.diagnosis_ja = data.get('diagnosis_ja', '')
        
        self.syndrome = data.get('syndrome', '')
        self.syndrome_en = data.get('syndrome_en', '')
        self.syndrome_ja = data.get('syndrome_ja', '')
        
        self.chief_complaint = data.get('chief_complaint', '')
        self.chief_complaint_en = data.get('chief_complaint_en', '')
        self.chief_complaint_ja = data.get('chief_complaint_ja', '')
        
        self.symptoms = data.get('symptoms', '')
        self.symptoms_en = data.get('symptoms_en', '')
        self.symptoms_ja = data.get('symptoms_ja', '')
        
        self.tongue = data.get('tongue', '')
        self.tongue_en = data.get('tongue_en', '')
        self.tongue_ja = data.get('tongue_ja', '')
        
        self.pulse = data.get('pulse', '')
        self.pulse_en = data.get('pulse_en', '')
        self.pulse_ja = data.get('pulse_ja', '')
        
        self.treatment_method = data.get('treatment_method', '')
        self.treatment_method_en = data.get('treatment_method_en', '')
        self.treatment_method_ja = data.get('treatment_method_ja', '')
        
        self.notes = data.get('notes', '')
        self.privacy_level = data.get('privacy_level', 'doctor_only')
        self.created_by = data.get('created_by')
        
        # 加载药物明细
        self.herbs = []
        herbs_data = data.get('herbs', [])
        if isinstance(herbs_data, list):
            for h in herbs_data:
                if isinstance(h, dict):
                    self.herbs.append(HerbItem(**h))
                elif isinstance(h, HerbItem):
                    self.herbs.append(h)
        
        # 设置语言
        lang_value = data.get('language', 'zh_CN')
        for lang in Language:
            if lang.value == lang_value:
                self.language = lang
                break
    
    def validate(self) -> tuple[bool, str]:
        """验证处方数据"""
        if not self.patient_id and not self.patient_name:
            return False, get_text("msg_error") + ": 患者信息不能为空"
        
        if not self.visit_date:
            return False, get_text("msg_error") + ": 就诊日期不能为空"
        
        if not self.herbs:
            return False, get_text("msg_error") + ": 处方药物不能为空"
        
        for idx, herb in enumerate(self.herbs):
            if not herb.name:
                return False, f"{get_text('msg_error')}: 第{idx+1}味药物名称不能为空"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """保存处方"""
        is_valid, error_msg = self.validate()
        if not is_valid:
            return False, error_msg
        
        try:
            prescription_data = self.to_dict()
            herbs_data = [asdict(h) for h in self.herbs]
            
            prescription_id = prescription_model.save_prescription(prescription_data, herbs_data)
            self.prescription_id = prescription_id
            
            return True, prescription_id
        except Exception as e:
            return False, str(e)
    
    def load(self, prescription_id: str) -> bool:
        """加载处方"""
        try:
            data = prescription_model.get_prescription(prescription_id)
            if data:
                self.from_dict(data)
                return True
            return False
        except Exception as e:
            print(f"加载处方失败: {e}")
            return False
    
    def export_to_word_format(self) -> str:
        """导出为Word兼容格式"""
        lines = []
        lines.append(f"处方编号: {self.prescription_code or '新处方'}")
        lines.append(f"就诊日期: {self.visit_date}")
        lines.append("")
        
        lines.append(f"患者: {self.patient_name}")
        if self.patient_name_en:
            lines.append(f"Patient: {self.patient_name_en}")
        if self.patient_name_ja:
            lines.append(f"患者: {self.patient_name_ja}")
        lines.append(f"性别: {self.patient_gender}  年龄: {self.patient_age}")
        lines.append("")
        
        lines.append(f"主诉: {self.chief_complaint}")
        if self.chief_complaint_en:
            lines.append(f"Chief Complaint: {self.chief_complaint_en}")
        lines.append("")
        
        lines.append(f"诊断: {self.diagnosis}")
        if self.diagnosis_en:
            lines.append(f"Diagnosis: {self.diagnosis_en}")
        lines.append("")
        
        lines.append(f"证候: {self.syndrome}")
        if self.syndrome_en:
            lines.append(f"Syndrome: {self.syndrome_en}")
        lines.append("")
        
        lines.append(f"舌: {self.tongue}  脉: {self.pulse}")
        if self.tongue_en or self.pulse_en:
            lines.append(f"Tongue: {self.tongue_en}  Pulse: {self.pulse_en}")
        lines.append("")
        
        lines.append(f"治法: {self.treatment_method}")
        if self.treatment_method_en:
            lines.append(f"Treatment: {self.treatment_method_en}")
        lines.append("")
        
        lines.append("-" * 50)
        lines.append("处方 / Prescription / 処方:")
        lines.append("-" * 50)
        
        for idx, herb in enumerate(self.herbs, 1):
            dose_str = f"{herb.dose}{herb.dose_unit}"
            line = f"{idx}. {herb.name} {dose_str}"
            if herb.processing:
                line += f" ({herb.processing})"
            lines.append(line)
            
            if herb.name_en or herb.name_ja:
                details = []
                if herb.name_en:
                    details.append(f"{herb.name_en}")
                if herb.dose_unit_en:
                    details.append(f"{herb.dose}{herb.dose_unit_en}")
                lines.append(f"   {', '.join(details)}")
        
        lines.append("")
        
        if self.notes:
            lines.append(f"备注: {self.notes}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> str:
        """获取处方摘要"""
        herb_names = [h.name for h in self.herbs[:5]]
        summary = f"{self.patient_name} - {self.diagnosis or '待诊断'} - {', '.join(herb_names)}"
        if len(self.herbs) > 5:
            summary += f" 等{len(self.herbs)}味药"
        return summary


def asdict(obj):
    """将对象转换为字典"""
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for name, field in obj.__dataclass_fields__.items():
            value = getattr(obj, name)
            if hasattr(value, '__dataclass_fields__'):
                result[name] = asdict(value)
            elif isinstance(value, list) and value and hasattr(value[0], '__dataclass_fields__'):
                result[name] = [asdict(v) for v in value]
            else:
                result[name] = value
        return result
    return obj
