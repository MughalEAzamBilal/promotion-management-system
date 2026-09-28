from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='TEACHER')  # 'SUPERADMIN', 'ADMIN', 'TEACHER'
    full_name = Column(String(150), nullable=False)
    email = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    cnic = Column(String(20), nullable=True, index=True)
    district = Column(String(80), nullable=True)  # Applicable for Admin
    
    is_active = Column(Boolean, default=True)
    is_first_login = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self):
        return self.role == 'SUPERADMIN'

    @property
    def is_admin(self):
        return self.role in ('SUPERADMIN', 'ADMIN')

    @property
    def is_teacher(self):
        return self.role == 'TEACHER'

    def can_manage_system(self):
        return self.is_superadmin

    def can_manage_teachers(self):
        return self.is_superadmin or self.is_admin

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
