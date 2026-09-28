from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.models.user import Base

class PasswordResetRequest(Base):
    __tablename__ = 'password_reset_requests'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=True)
    cnic = Column(String(20), nullable=False, index=True)
    personnel_no = Column(String(50), nullable=True, index=True)
    district = Column(String(100), nullable=True)
    phone = Column(String(30), nullable=False)
    email = Column(String(120), nullable=False)
    account_username = Column(String(80), nullable=True)
    account_role = Column(String(20), nullable=True)  # 'TEACHER', 'ADMIN', 'SUPERADMIN'
    user_full_name = Column(String(150), nullable=True)
    user_notes = Column(Text, nullable=True)
    
    # Status: 'Pending', 'Processed', 'Rejected'
    status = Column(String(20), default='Pending', nullable=False, index=True)
    admin_response_notes = Column(Text, nullable=True)
    temporary_password_set = Column(String(100), nullable=True)
    dispatch_channel = Column(String(50), nullable=True)  # 'Phone / SMS', 'Official Email', 'Both Phone & Email'
    processed_by = Column(String(80), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<PasswordResetRequest #{self.id} {self.cnic} ({self.status})>'
