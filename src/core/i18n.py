# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 多语言国际化配置
支持中文、英文、日语三种主流语言
"""

from enum import Enum
from typing import Dict, Optional
import gettext
import os

class Language(Enum):
    """支持的语种枚举"""
    ZH_CN = "zh_CN"  # 简体中文
    EN_US = "en_US"  # 美国英语
    JA_JP = "ja_JP"  # 日语

class I18nManager:
    """国际化管理器"""
    
    def __init__(self, lang: Language = Language.ZH_CN):
        self.current_lang = lang
        self._translations: Dict[str, gettext.GNUTranslations] = {}
        self._init_translations()
    
    def _init_translations(self):
        """初始化翻译对象"""
        # 创建简单的翻译映射表
        self._messages = {
            Language.ZH_CN: self._get_chinese_messages(),
            Language.EN_US: self._get_english_messages(),
            Language.JA_JP: self._get_japanese_messages(),
        }
    
    def _get_chinese_messages(self) -> Dict[str, str]:
        """中文翻译"""
        return {
            # 基础信息
            "app_name": "中医门诊处方管理系统",
            "version": "版本",
            
            # 菜单和标签
            "menu_file": "文件",
            "menu_edit": "编辑",
            "menu_view": "视图",
            "menu_help": "帮助",
            "menu_community": "社区",
            
            # 功能模块
            "module_prescription": "处方管理",
            "module_search": "处方检索",
            "module_statistics": "数据统计",
            "module_timeline": "时间追踪",
            "module_user": "用户管理",
            "module_community": "社区交流",
            "module_settings": "系统设置",
            
            # 处方相关
            "prescription_id": "处方编号",
            "patient_name": "患者姓名",
            "patient_gender": "性别",
            "patient_age": "年龄",
            "prescription_date": "就诊日期",
            "prescription_doctor": "主治医师",
            "prescription_diagnosis": "诊断",
            "prescription_symptoms": "症状",
            "prescription_tongue": "舌象",
            "prescription_pulse": "脉象",
            "prescription_zhenghou": "证候",
            "prescription_zhifa": "治法",
            "prescription_herbs": "方药",
            "prescription_complaint": "主诉",
            
            # 药物相关
            "herb_name": "药材名称",
            "herb_dose": "剂量",
            "herb_unit": "单位",
            "herb_usage": "用法",
            
            # 操作按钮
            "btn_import": "导入",
            "btn_export": "导出",
            "btn_save": "保存",
            "btn_delete": "删除",
            "btn_search": "搜索",
            "btn_print": "打印",
            "btn_preview": "预览",
            "btn_new": "新建",
            "btn_edit": "编辑",
            "btn_cancel": "取消",
            "btn_confirm": "确认",
            
            # 统计模块
            "stats_title": "数据统计分析",
            "stats_herb_frequency": "高频药材统计",
            "stats_prescription_cloud": "中药方剂云",
            "stats_herb_cloud": "中药高频药物云",
            "stats_diagnosis_distribution": "病种分布",
            "stats_time_trend": "时间趋势",
            "stats_patient_trend": "患者趋势",
            
            # 搜索模块
            "search_placeholder": "搜索：病种、姓名、症状、药味、时间...",
            "search_by_disease": "按病种搜索",
            "search_by_name": "按姓名搜索",
            "search_by_symptom": "按症状搜索",
            "search_by_herb": "按药味搜索",
            "search_by_date": "按时间搜索",
            "search_advanced": "高级搜索",
            
            # 时间追踪
            "timeline_title": "处方时间变化规律追踪",
            "timeline_patient_history": "患者就诊历史",
            "timeline_disease_progression": "病程进展",
            "timeline_treatment_changes": "治疗方案变化",
            
            # 用户管理
            "user_management": "用户管理",
            "user_login": "登录",
            "user_logout": "退出登录",
            "user_register": "注册",
            "user_profile": "个人资料",
            "user_permissions": "权限设置",
            
            # 社区模块
            "community_title": "中医药专业社区",
            "community_posts": "帖子",
            "community_discussions": "讨论",
            "community_experiences": "经验分享",
            "community_questions": "问答",
            "community_announcements": "公告",
            
            # 隐私设置
            "privacy_settings": "隐私设置",
            "privacy_public": "公开",
            "privacy_private": "私有",
            "privacy_doctor_only": "仅医师可见",
            
            # 系统消息
            "msg_save_success": "保存成功",
            "msg_save_failed": "保存失败",
            "msg_delete_success": "删除成功",
            "msg_delete_failed": "删除失败",
            "msg_import_success": "导入成功",
            "msg_import_failed": "导入失败",
            "msg_export_success": "导出成功",
            "msg_export_failed": "导出失败",
            "msg_no_data": "暂无数据",
            "msg_loading": "加载中...",
            "msg_error": "错误",
            "msg_warning": "警告",
            "msg_info": "提示",
            "msg_confirm": "确认",
            
            # 性别
            "gender_male": "男",
            "gender_female": "女",
            "gender_other": "其他",
            
            # 时间
            "time_today": "今天",
            "time_yesterday": "昨天",
            "time_this_week": "本周",
            "time_this_month": "本月",
            "time_this_year": "今年",
            "time_custom": "自定义",
        }
    
    def _get_english_messages(self) -> Dict[str, str]:
        """英文翻译"""
        return {
            # 基础信息
            "app_name": "TCM Clinic Prescription Management System",
            "version": "Version",
            
            # 菜单和标签
            "menu_file": "File",
            "menu_edit": "Edit",
            "menu_view": "View",
            "menu_help": "Help",
            "menu_community": "Community",
            
            # 功能模块
            "module_prescription": "Prescription Management",
            "module_search": "Prescription Search",
            "module_statistics": "Data Statistics",
            "module_timeline": "Time Tracking",
            "module_user": "User Management",
            "module_community": "Community",
            "module_settings": "Settings",
            
            # 处方相关
            "prescription_id": "Prescription ID",
            "patient_name": "Patient Name",
            "patient_gender": "Gender",
            "patient_age": "Age",
            "prescription_date": "Visit Date",
            "prescription_doctor": "Attending Physician",
            "prescription_diagnosis": "Diagnosis",
            "prescription_symptoms": "Symptoms",
            "prescription_tongue": "Tongue",
            "prescription_pulse": "Pulse",
            "prescription_zhenghou": "Syndrome",
            "prescription_zhifa": "Treatment Method",
            "prescription_herbs": "Prescription",
            "prescription_complaint": "Chief Complaint",
            
            # 药物相关
            "herb_name": "Herb Name",
            "herb_dose": "Dose",
            "herb_unit": "Unit",
            "herb_usage": "Usage",
            
            # 操作按钮
            "btn_import": "Import",
            "btn_export": "Export",
            "btn_save": "Save",
            "btn_delete": "Delete",
            "btn_search": "Search",
            "btn_print": "Print",
            "btn_preview": "Preview",
            "btn_new": "New",
            "btn_edit": "Edit",
            "btn_cancel": "Cancel",
            "btn_confirm": "Confirm",
            
            # 统计模块
            "stats_title": "Data Statistics Analysis",
            "stats_herb_frequency": "High-Frequency Herbs",
            "stats_prescription_cloud": "Prescription Cloud",
            "stats_herb_cloud": "Herb Frequency Cloud",
            "stats_diagnosis_distribution": "Disease Distribution",
            "stats_time_trend": "Time Trend",
            "stats_patient_trend": "Patient Trend",
            
            # 搜索模块
            "search_placeholder": "Search: disease, name, symptoms, herbs, date...",
            "search_by_disease": "Search by Disease",
            "search_by_name": "Search by Name",
            "search_by_symptom": "Search by Symptom",
            "search_by_herb": "Search by Herb",
            "search_by_date": "Search by Date",
            "search_advanced": "Advanced Search",
            
            # 时间追踪
            "timeline_title": "Prescription Time Change Tracking",
            "timeline_patient_history": "Patient Visit History",
            "timeline_disease_progression": "Disease Progression",
            "timeline_treatment_changes": "Treatment Changes",
            
            # 用户管理
            "user_management": "User Management",
            "user_login": "Login",
            "user_logout": "Logout",
            "user_register": "Register",
            "user_profile": "Profile",
            "user_permissions": "Permissions",
            
            # 社区模块
            "community_title": "TCM Professional Community",
            "community_posts": "Posts",
            "community_discussions": "Discussions",
            "community_experiences": "Experience Sharing",
            "community_questions": "Q&A",
            "community_announcements": "Announcements",
            
            # 隐私设置
            "privacy_settings": "Privacy Settings",
            "privacy_public": "Public",
            "privacy_private": "Private",
            "privacy_doctor_only": "Doctor Only",
            
            # 系统消息
            "msg_save_success": "Save successful",
            "msg_save_failed": "Save failed",
            "msg_delete_success": "Delete successful",
            "msg_delete_failed": "Delete failed",
            "msg_import_success": "Import successful",
            "msg_import_failed": "Import failed",
            "msg_export_success": "Export successful",
            "msg_export_failed": "Export failed",
            "msg_no_data": "No data available",
            "msg_loading": "Loading...",
            "msg_error": "Error",
            "msg_warning": "Warning",
            "msg_info": "Information",
            "msg_confirm": "Confirm",
            
            # 性别
            "gender_male": "Male",
            "gender_female": "Female",
            "gender_other": "Other",
            
            # 时间
            "time_today": "Today",
            "time_yesterday": "Yesterday",
            "time_this_week": "This Week",
            "time_this_month": "This Month",
            "time_this_year": "This Year",
            "time_custom": "Custom",
        }
    
    def _get_japanese_messages(self) -> Dict[str, str]:
        """日语翻译"""
        return {
            # 基础信息
            "app_name": "中医医院処方管理系统",
            "version": "バージョン",
            
            # 菜单和标签
            "menu_file": "ファイル",
            "menu_edit": "編集",
            "menu_view": "表示",
            "menu_help": "ヘルプ",
            "menu_community": "コミュニティ",
            
            # 功能模块
            "module_prescription": "処方管理",
            "module_search": "処方検索",
            "module_statistics": "データ統計",
            "module_timeline": "時間追跡",
            "module_user": "ユーザー管理",
            "module_community": "コミュニティ",
            "module_settings": "設定",
            
            # 处方相关
            "prescription_id": "処方ID",
            "patient_name": "患者名",
            "patient_gender": "性別",
            "patient_age": "年齢",
            "prescription_date": "受診日",
            "prescription_doctor": "主治医",
            "prescription_diagnosis": "診断",
            "prescription_symptoms": "症状",
            "prescription_tongue": "舌診",
            "prescription_pulse": "脈診",
            "prescription_zhenghou": "証候",
            "prescription_zhifa": "治療法",
            "prescription_herbs": "処方",
            "prescription_complaint": "主訴",
            
            # 药物相关
            "herb_name": "药材名",
            "herb_dose": "用量",
            "herb_unit": "単位",
            "herb_usage": "用法",
            
            # 操作按钮
            "btn_import": "インポート",
            "btn_export": "エクスポート",
            "btn_save": "保存",
            "btn_delete": "削除",
            "btn_search": "検索",
            "btn_print": "印刷",
            "btn_preview": "プレビュー",
            "btn_new": "新規",
            "btn_edit": "編集",
            "btn_cancel": "キャンセル",
            "btn_confirm": "確認",
            
            # 统计模块
            "stats_title": "データ統計分析",
            "stats_herb_frequency": "高频薬材",
            "stats_prescription_cloud": "処方クラウド",
            "stats_herb_cloud": "薬材使用頻度クラウド",
            "stats_diagnosis_distribution": "疾患分布",
            "stats_time_trend": "時間趨勢",
            "stats_patient_trend": "患者趨勢",
            
            # 搜索模块
            "search_placeholder": "検索：疾患、名前、症状、药材、日付...",
            "search_by_disease": "疾患で検索",
            "search_by_name": "名前で検索",
            "search_by_symptom": "症状で検索",
            "search_by_herb": "药材で検索",
            "search_by_date": "日付で検索",
            "search_advanced": "詳細検索",
            
            # 时间追踪
            "timeline_title": "処方時間変化追跡",
            "timeline_patient_history": "患者受診履歴",
            "timeline_disease_progression": "疾患進行",
            "timeline_treatment_changes": "治療計画変更",
            
            # 用户管理
            "user_management": "ユーザー管理",
            "user_login": "ログイン",
            "user_logout": "ログアウト",
            "user_register": "登録",
            "user_profile": "プロフィール",
            "user_permissions": "権限設定",
            
            # 社区模块
            "community_title": "中医専門コミュニティ",
            "community_posts": "投稿",
            "community_discussions": "議論",
            "community_experiences": "経験分享",
            "community_questions": "質問",
            "community_announcements": "お知らせ",
            
            # 隐私设置
            "privacy_settings": "プライバシー設定",
            "privacy_public": "公開",
            "privacy_private": "非公開",
            "privacy_doctor_only": "医師のみ",
            
            # 系统消息
            "msg_save_success": "保存成功",
            "msg_save_failed": "保存失敗",
            "msg_delete_success": "削除成功",
            "msg_delete_failed": "削除失敗",
            "msg_import_success": "インポート成功",
            "msg_import_failed": "インポート失敗",
            "msg_export_success": "エクスポート成功",
            "msg_export_failed": "エクスポート失敗",
            "msg_no_data": "データなし",
            "msg_loading": "読み込み中...",
            "msg_error": "エラー",
            "msg_warning": "警告",
            "msg_info": "情報",
            "msg_confirm": "確認",
            
            # 性别
            "gender_male": "男性",
            "gender_female": "女性",
            "gender_other": "その他",
            
            # 时间
            "time_today": "今日",
            "time_yesterday": "昨日",
            "time_this_week": "今週",
            "time_this_month": "今月",
            "time_this_year": "今年",
            "time_custom": "カスタム",
        }
    
    def get(self, key: str, lang: Optional[Language] = None) -> str:
        """获取翻译文本"""
        target_lang = lang or self.current_lang
        return self._messages.get(target_lang, {}).get(key, key)
    
    def set_language(self, lang: Language):
        """设置当前语言"""
        self.current_lang = lang
    
    def get_current_language(self) -> Language:
        """获取当前语言"""
        return self.current_lang
    
    def get_all_translations(self, key: str) -> Dict[Language, str]:
        """获取某个键的所有语言翻译"""
        return {
            lang: messages.get(key, key)
            for lang, messages in self._messages.items()
        }


# 全局国际化实例
i18n = I18nManager()

def get_text(key: str) -> str:
    """快速获取翻译文本的函数"""
    return i18n.get(key)

def set_language(lang: Language):
    """设置全局语言"""
    i18n.set_language(lang)
