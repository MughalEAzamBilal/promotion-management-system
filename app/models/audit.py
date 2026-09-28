from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from .user import Base

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(80), nullable=False)
    role = Column(String(30), nullable=False)
    action = Column(String(100), nullable=False)       # 'CREATE_TEACHER', 'VERIFY_TEACHER', 'UPDATE_SENIORITY', 'APPROVE_CORRECTION', etc.
    entity_type = Column(String(50), nullable=True)   # 'Teacher', 'Seniority', 'Rule', 'System'
    entity_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<AuditLog [{self.created_at.strftime("%Y-%m-%d %H:%M")}] {self.username} -> {self.action}>'

class SystemSetting(Base):
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(80), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    setting_type = Column(String(30), default='string') # 'string', 'boolean', 'json', 'integer'
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemSetting {self.setting_key}={self.setting_value}>'
