# -*- coding: utf-8 -*-
"""
中医药门诊处方处理平台 - 用户管理模块
支持用户认证、权限管理、用户检索等功能
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets
import json
import re

try:
    from src.core.database import db_manager
except ImportError:
    db_manager = None
from src.core.i18n import Language, i18n, get_text


class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RESEARCHER = "researcher"
    PATIENT = "patient"
    GUEST = "guest"


class PrivacyLevel(Enum):
    """隐私级别枚举"""
    PUBLIC = "public"
    PRIVATE = "private"
    DOCTOR_ONLY = "doctor_only"
    SELF_ONLY = "self_only"


class UserStatus(Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


@dataclass
class User:
    """用户数据模型"""
    id: Optional[str] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: str = "doctor"
    language: str = "zh_CN"
    
    # 基本信息（多语言）
    name: str = ""
    name_en: str = ""
    name_ja: str = ""
    phone: str = ""
    avatar: str = ""
    
    # 医师信息
    title: str = ""  # 职称：主任医师、副主任医师等
    title_en: str = ""
    title_ja: str = ""
    department: str = ""  # 科室
    department_en: str = ""
    department_ja: str = ""
    specialization: str = ""  # 专业特长
    bio: str = ""  # 个人简介
    
    # 权限设置
    permissions: List[str] = field(default_factory=list)
    privacy_level: str = "private"
    
    # 状态
    status: str = "active"
    last_login: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserManager:
    """用户管理器"""
    
    def __init__(self):
        self.current_user: Optional[User] = None
        self.session_token: Optional[str] = None
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """密码哈希"""
        if not salt:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        
        return password_hash, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == password_hash
    
    def generate_user_id(self) -> str:
        """生成用户ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:6]
        return f"USER{timestamp}{random_str}"
    
    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        role: str = "doctor",
        name: str = "",
        name_en: str = "",
        name_ja: str = "",
        phone: str = "",
        **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        """
        创建新用户
        
        Returns:
            Tuple of (success, message, user_id)
        """
        # 检查用户名是否存在
        check_sql = "SELECT id FROM users WHERE username = ?"
        existing = db_manager.execute_query(check_sql, (username,))
        if existing:
            return False, "用户名已存在", None
        
        # 检查邮箱是否存在
        if email:
            check_email_sql = "SELECT id FROM users WHERE email = ?"
            existing_email = db_manager.execute_query(check_email_sql, (email,))
            if existing_email:
                return False, "邮箱已被注册", None
        
        # 生成用户ID
        user_id = self.generate_user_id()
        
        # 哈希密码
        password_hash, salt = self._hash_password(password)
        
        # 构建用户数据
        user_data = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': f"{password_hash}:{salt}",
            'role': role,
            'language': kwargs.get('language', 'zh_CN'),
            'name': name or username,
            'name_en': name_en,
            'name_ja': name_ja,
            'phone': phone,
            'title': kwargs.get('title', ''),
            'title_en': kwargs.get('title_en', ''),
            'title_ja': kwargs.get('title_ja', ''),
            'department': kwargs.get('department', ''),
            'department_en': kwargs.get('department_en', ''),
            'department_ja': kwargs.get('department_ja', ''),
            'specialization': kwargs.get('specialization', ''),
            'bio': kwargs.get('bio', ''),
            'privacy_level': kwargs.get('privacy_level', 'private'),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        
        # 插入数据库
        columns = ', '.join(user_data.keys())
        placeholders = ', '.join(['?'] * len(user_data))
        sql = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
        
        try:
            db_manager.execute_update(sql, tuple(user_data.values()))
            return True, "用户创建成功", user_id
        except Exception as e:
            return False, f"创建用户失败: {str(e)}", None
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        用户认证
        
        Returns:
            Tuple of (success, message, user)
        """
        sql = "SELECT * FROM users WHERE username = ? OR email = ?"
        results = db_manager.execute_query(sql, (username, username))
        
        if not results:
            return False, "用户不存在", None
        
        user_data = results[0]
        
        # 检查用户状态
        if user_data.get('status') != 'active':
            return False, "用户账户已被禁用", None
        
        # 验证密码
        password_hash = user_data.get('password_hash', '')
        if ':' in password_hash:
            hash_part, salt = password_hash.split(':', 1)
        else:
            return False, "密码格式错误", None
        
        if not self._verify_password(password, hash_part, salt):
            return False, "密码错误", None
        
        # 更新最后登录时间
        update_sql = "UPDATE users SET last_login = ? WHERE id = ?"
        db_manager.execute_update(update_sql, (datetime.now().isoformat(), user_data['id']))
        
        # 创建用户对象
        user = User(**{
            k: v for k, v in user_data.items()
            if k in User.__dataclass_fields__.keys()
        })
        user.id = user_data['id']
        user.password_hash = ""  # 不返回密码
        
        # 设置当前用户
        self.current_user = user
        self.session_token = secrets.token_urlsafe(32)
        
        return True, "登录成功", user
    
    def logout(self):
        """用户登出"""
        self.current_user = None
        self.session_token = None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        sql = "SELECT * FROM users WHERE id = ?"
        results = db_manager.execute_query(sql, (user_id,))
        
        if not results:
            return None
        
        user_data = results[0]
        user = User(**{
            k: v for k, v in user_data.items()
            if k in User.__dataclass_fields__.keys()
        })
        user.id = user_data['id']
        user.password_hash = ""
        
        return user
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        sql = "SELECT * FROM users WHERE username = ?"
        results = db_manager.execute_query(sql, (username,))
        
        if not results:
            return None
        
        user_data = results[0]
        user = User(**{
            k: v for k, v in user_data.items()
            if k in User.__dataclass_fields__.keys()
        })
        user.id = user_data['id']
        user.password_hash = ""
        
        return user
    
    def update_user(self, user_id: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        """更新用户信息"""
        # 过滤可更新的字段
        allowed_fields = [
            'email', 'name', 'name_en', 'name_ja', 'phone', 'avatar',
            'title', 'title_en', 'title_ja', 'department', 'department_en', 
            'department_ja', 'specialization', 'bio', 'language',
            'privacy_level', 'status', 'updated_at'
        ]
        
        update_data = {}
        for key in allowed_fields:
            if key in data:
                update_data[key] = data[key]
        
        if not update_data:
            return False, "没有需要更新的字段"
        
        update_data['updated_at'] = datetime.now().isoformat()
        
        # 构建更新SQL
        set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
        sql = f"UPDATE users SET {set_clause} WHERE id = ?"
        params = tuple(update_data.values()) + (user_id,)
        
        try:
            rows = db_manager.execute_update(sql, params)
            if rows > 0:
                return True, "用户信息更新成功"
            return False, "用户不存在"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
    
    def change_password(
        self, 
        user_id: str, 
        old_password: str, 
        new_password: str
    ) -> Tuple[bool, str]:
        """修改密码"""
        # 获取当前密码
        sql = "SELECT password_hash FROM users WHERE id = ?"
        results = db_manager.execute_query(sql, (user_id,))
        
        if not results:
            return False, "用户不存在"
        
        password_hash = results[0].get('password_hash', '')
        if ':' in password_hash:
            hash_part, salt = password_hash.split(':', 1)
        else:
            return False, "密码格式错误"
        
        # 验证旧密码
        if not self._verify_password(old_password, hash_part, salt):
            return False, "旧密码错误"
        
        # 生成新密码哈希
        new_hash, new_salt = self._hash_password(new_password)
        
        # 更新密码
        update_sql = "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?"
        try:
            db_manager.execute_update(
                update_sql, 
                (f"{new_hash}:{new_salt}", datetime.now().isoformat(), user_id)
            )
            return True, "密码修改成功"
        except Exception as e:
            return False, f"密码修改失败: {str(e)}"
    
    def reset_password(self, user_id: str, new_password: str) -> Tuple[bool, str]:
        """重置密码（管理员用）"""
        # 生成新密码哈希
        new_hash, new_salt = self._hash_password(new_password)
        
        # 更新密码
        update_sql = "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?"
        try:
            db_manager.execute_update(
                update_sql, 
                (f"{new_hash}:{new_salt}", datetime.now().isoformat(), user_id)
            )
            return True, "密码重置成功"
        except Exception as e:
            return False, f"密码重置失败: {str(e)}"
    
    def search_users(
        self,
        keyword: str = None,
        role: str = None,
        status: str = None,
        department: str = None,
        language: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[User], int, Dict]:
        """
        搜索用户
        
        Returns:
            Tuple of (users, total, metadata)
        """
        conditions = []
        params = []
        
        if keyword:
            conditions.append("(username LIKE ? OR name LIKE ? OR name_en LIKE ? OR email LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw, kw])
        
        if role:
            conditions.append("role = ?")
            params.append(role)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if department:
            conditions.append("(department LIKE ? OR department_en LIKE ?)")
            dept = f"%{department}%"
            params.extend([dept, dept])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 统计总数
        count_sql = f"SELECT COUNT(*) as total FROM users WHERE {where_clause}"
        count_result = db_manager.execute_query(count_sql, tuple(params))
        total = count_result[0]['total'] if count_result else 0
        
        # 分页查询
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM users 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        
        results = db_manager.execute_query(sql, tuple(params))
        
        users = []
        for user_data in results:
            user = User(**{
                k: v for k, v in user_data.items()
                if k in User.__dataclass_fields__.keys()
            })
            user.id = user_data['id']
            user.password_hash = ""
            users.append(user)
        
        metadata = {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size,
        }
        
        return users, total, metadata
    
    def delete_user(self, user_id: str) -> Tuple[bool, str]:
        """删除用户"""
        # 不能删除自己
        if self.current_user and self.current_user.id == user_id:
            return False, "不能删除当前登录用户"
        
        # 不能删除管理员
        user = self.get_user(user_id)
        if user and user.role == 'admin':
            return False, "不能删除管理员账户"
        
        sql = "DELETE FROM users WHERE id = ?"
        try:
            rows = db_manager.execute_update(sql, (user_id,))
            if rows > 0:
                return True, "用户删除成功"
            return False, "用户不存在"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
    
    def suspend_user(self, user_id: str) -> Tuple[bool, str]:
        """暂停用户账户"""
        return self.update_user(user_id, {'status': 'suspended'})
    
    def activate_user(self, user_id: str) -> Tuple[bool, str]:
        """激活用户账户"""
        return self.update_user(user_id, {'status': 'active'})
    
    def check_permission(
        self, 
        user_id: str, 
        permission: str
    ) -> bool:
        """检查用户权限"""
        if not self.current_user or self.current_user.id != user_id:
            return False
        
        # 管理员拥有所有权限
        if self.current_user.role == 'admin':
            return True
        
        # 检查用户权限列表
        user_permissions = self.current_user.permissions or []
        return permission in user_permissions
    
    def has_role(self, user_id: str, role: str) -> bool:
        """检查用户角色"""
        user = self.get_user(user_id)
        if not user:
            return False
        return user.role == role
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.current_user is not None
    
    def is_admin(self) -> bool:
        """检查是否是管理员"""
        return self.current_user and self.current_user.role == 'admin'
    
    def is_doctor(self) -> bool:
        """检查是否是医生"""
        return self.current_user and self.current_user.role == 'doctor'


class DoctorManager:
    """医师管理器（专门处理医师相关业务）"""
    
    def __init__(self):
        self.user_manager = UserManager()
    
    def create_doctor_profile(
        self,
        user_id: str,
        title: str,
        title_en: str = "",
        title_ja: str = "",
        department: str = "",
        department_en: str = "",
        department_ja: str = "",
        specialization: str = "",
        bio: str = ""
    ) -> Tuple[bool, str]:
        """创建医师档案"""
        # 先创建医师记录
        doctor_id = self.user_manager.generate_user_id()
        
        doctor_data = {
            'id': doctor_id,
            'user_id': user_id,
            'title': title,
            'title_en': title_en,
            'title_ja': title_ja,
            'department': department,
            'department_en': department_en,
            'department_ja': department_ja,
            'specialization': specialization,
            'bio': bio,
            'created_at': datetime.now().isoformat(),
        }
        
        # 如果存在doctors表，则插入
        try:
            columns = ', '.join(doctor_data.keys())
            placeholders = ', '.join(['?'] * len(doctor_data))
            sql = f"INSERT INTO doctors ({columns}) VALUES ({placeholders})"
            db_manager.execute_update(sql, tuple(doctor_data.values()))
            return True, doctor_id
        except Exception as e:
            # 如果doctors表不存在，直接更新users表
            return self.user_manager.update_user(user_id, doctor_data)
    
    def get_doctor_profile(self, user_id: str) -> Optional[Dict]:
        """获取医师档案"""
        # 尝试从doctors表获取
        sql = "SELECT * FROM doctors WHERE user_id = ?"
        results = db_manager.execute_query(sql, (user_id,))
        
        if results:
            return results[0]
        
        # 从users表获取
        return self.user_manager.get_user(user_id)
    
    def search_doctors(
        self,
        keyword: str = None,
        department: str = None,
        specialization: str = None,
        language: str = "zh_CN",
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict], int, Dict]:
        """搜索医师"""
        conditions = []
        params = []
        
        if keyword:
            if language == 'zh_CN':
                conditions.append("(d.name LIKE ? OR d.specialization LIKE ? OR d.department LIKE ?)")
            elif language == 'en_US':
                conditions.append("(d.name_en LIKE ? OR d.specialization LIKE ? OR d.department_en LIKE ?)")
            else:
                conditions.append("(d.name_ja LIKE ? OR d.specialization LIKE ? OR d.department_ja LIKE ?)")
            
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        
        if department:
            if language == 'zh_CN':
                conditions.append("d.department LIKE ?")
            elif language == 'en_US':
                conditions.append("d.department_en LIKE ?")
            else:
                conditions.append("d.department_ja LIKE ?")
            params.append(f"%{department}%")
        
        if specialization:
            conditions.append("d.specialization LIKE ?")
            params.append(f"%{specialization}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 统计
        count_sql = f"SELECT COUNT(*) as total FROM doctors d WHERE {where_clause}"
        count_result = db_manager.execute_query(count_sql, tuple(params))
        total = count_result[0]['total'] if count_result else 0
        
        # 分页查询
        offset = (page - 1) * page_size
        sql = f"""
            SELECT d.*, u.username, u.email, u.status
            FROM doctors d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE {where_clause}
            ORDER BY d.name
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        
        results = db_manager.execute_query(sql, tuple(params))
        
        metadata = {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size,
        }
        
        return results, total, metadata


# 创建全局用户管理器实例
user_manager = UserManager()
doctor_manager = DoctorManager()
