from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text
from .user import Base

class ServiceHistory(Base):
    __tablename__ = 'service_history'

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    
    designation = Column(String(80), nullable=False)   # PST, EST, SST
    bs = Column(Integer, nullable=False)               # 14, 15, 16
    school_name = Column(String(200), nullable=False)
    district = Column(String(80), nullable=False)
    tehsil = Column(String(80), nullable=False)
    
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=True)             # Nullable if currently serving here
    is_current_post = Column(Boolean, default=False)
    
    appointment_type = Column(String(50), default='Regular') # 'Regular', 'Contract', 'Ad-hoc', 'Acting Charge'
    order_no = Column(String(100), nullable=True)
    order_date = Column(Date, nullable=True)
    
    remarks = Column(Text, nullable=True)
    verification_status = Column(String(30), default='Pending') # 'Pending', 'Verified', 'Rejected'
    verified_by = Column(String(80), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    change_type = Column(String(20), default=None)  # 'new' or 'edited'
    is_edited = Column(Boolean, default=False)       # Turns cell BLUE in admin view
    is_new = Column(Boolean, default=False)          # Turns cell GREEN in admin view
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def missing_fields(self):
        """Returns list of missing data values for this service posting record."""
        missing = []
        if not self.tehsil or str(self.tehsil).strip() in ['', 'N/A']:
            missing.append('Tehsil')
        if not self.order_no or str(self.order_no).strip() in ['', 'N/A']:
            missing.append('Order No')
        if not self.order_date:
            missing.append('Order Date')
        if not self.is_current_post and not self.to_date:
            missing.append('Tenure End Date')
        if not self.remarks or str(self.remarks).strip() in ['', 'N/A']:
            missing.append('Official Remarks')
        return missing

    def __repr__(self):
        return f'<ServiceHistory {self.designation} (BS-{self.bs}) {self.from_date} to {self.to_date or "Present"}>'
