from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from .user import Base

class CorrectionRequest(Base):
    __tablename__ = 'correction_requests'

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    
    # Target Category & Entity Mapping
    record_type = Column(String(50), default='PERSONAL', index=True) # 'PERSONAL', 'QUALIFICATION', 'SERVICE'
    record_id = Column(Integer, nullable=True) # Foreign key ID of Qualification or ServiceHistory
    target_attribute = Column(String(100), nullable=True) # Underlying DB model attribute, e.g. father_name, major_subject
    batch_id = Column(String(50), nullable=True, index=True) # Submission batch identifier

    field_name = Column(String(100), nullable=False) # e.g. Seniority No, DOB, Father Name, Joining Date
    current_value = Column(String(255), nullable=True)
    requested_value = Column(String(255), nullable=False)
    
    reason = Column(Text, nullable=False)
    supporting_document_name = Column(String(200), nullable=True)
    
    # Status: 'Pending', 'Approved', 'Rejected', 'More Info Required'
    status = Column(String(30), default='Pending', index=True)
    admin_remarks = Column(Text, nullable=True)
    reviewed_by = Column(String(80), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CorrectionRequest {self.teacher_id} for {self.field_name}: {self.status}>'
