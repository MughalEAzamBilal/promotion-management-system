from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text
from .user import Base

class SeniorityRecord(Base):
    __tablename__ = 'seniority_records'

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    
    seniority_no = Column(Integer, nullable=False)
    seniority_date = Column(Date, nullable=False)
    
    designation = Column(String(80), nullable=False)
    bs = Column(Integer, nullable=False)
    category = Column(String(80), nullable=True) # Science, Arts, General
    district = Column(String(80), nullable=False)
    
    seniority_list_reference = Column(String(150), nullable=False) # Order/Notification reference
    seniority_list_date = Column(Date, nullable=False)
    
    is_official = Column(Boolean, default=True)
    verified = Column(Boolean, default=True)
    verified_by = Column(String(80), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SeniorityRecord No.{self.seniority_no} ({self.designation} - {self.district})>'
