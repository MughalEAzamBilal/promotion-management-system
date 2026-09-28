from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .user import Base

class Teacher(Base):
    __tablename__ = 'teachers'

    id = Column(Integer, primary_key=True)
    personnel_no = Column(String(30), unique=True, nullable=False, index=True)
    cnic = Column(String(25), unique=True, nullable=False, index=True)
    
    full_name = Column(String(150), nullable=False)
    father_name = Column(String(150), nullable=False)
    gender = Column(String(10), nullable=False)  # 'Male', 'Female', 'Other'
    date_of_birth = Column(Date, nullable=False)
    
    mobile = Column(String(25), nullable=True)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    
    district = Column(String(80), nullable=False)
    tehsil = Column(String(80), nullable=False)
    markaz = Column(String(80), nullable=True)
    
    school_name = Column(String(200), nullable=False)
    school_emis_code = Column(String(50), nullable=True)
    
    current_designation = Column(String(80), nullable=False)  # PST, EST (Science), etc.
    current_bs = Column(Integer, nullable=False, default=14)
    current_category = Column(String(80), nullable=True)     # Science, Arts, General, Computer
    
    appointment_date = Column(Date, nullable=False)          # First entry in govt service
    joining_date = Column(Date, nullable=False)              # Education department joining
    regularization_date = Column(Date, nullable=True)        # Regular service date
    current_post_date = Column(Date, nullable=False)         # Date joined current designation/BS
    
    seniority_no = Column(Integer, nullable=True)            # Official seniority rank in current post
    seniority_date = Column(Date, nullable=True)
    
    # Feeder cadre / Previous post particulars retained after promotion
    previous_designation = Column(String(80), nullable=True)  # Feeder post title (e.g. PST, EST)
    previous_bs = Column(Integer, nullable=True)              # Feeder basic scale (e.g. 14, 15)
    previous_seniority_no = Column(Integer, nullable=True)    # Feeder cadre seniority rank held prior to promotion
    
    appointment_order_no = Column(String(100), nullable=True)
    appointment_order_date = Column(Date, nullable=True)
    
    current_post_order_no = Column(String(100), nullable=True)
    current_post_order_date = Column(Date, nullable=True)
    
    verification_status = Column(String(30), default='Pending')  # 'Pending', 'Verified', 'Under Review', 'Rejected'
    account_status = Column(String(30), default='Active')        # 'Active', 'Suspended', 'Retired'
    
    is_data_verified_by_teacher = Column(Boolean, default=False) # True once teacher confirms self-verification
    teacher_verified_at = Column(DateTime, nullable=True)
    has_edited_records = Column(Boolean, default=False)          # Turns admin list cell BLUE
    has_new_records = Column(Boolean, default=False)             # Turns admin list cell GREEN
    
    disciplinary_inquiry_pending = Column(Boolean, default=False)
    acr_score_average = Column(Float, default=80.0)             # PER / ACR evaluation metric
    
    # Administrative Promotion Disablement (e.g., Retired, Deceased, Inquiry)
    is_promotion_disabled = Column(Boolean, default=False, index=True)
    promotion_disable_reason = Column(String(100), nullable=True)
    promotion_disable_remarks = Column(Text, nullable=True)
    promotion_disabled_at = Column(DateTime, nullable=True)
    promotion_disabled_by = Column(String(80), nullable=True)
    
    # Official Retirement Record
    retirement_order_no = Column(String(100), nullable=True)
    retirement_order_date = Column(Date, nullable=True)
    
    admin_notes = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    qualifications = relationship('Qualification', backref='teacher', cascade='all, delete-orphan', lazy='joined')
    service_history = relationship('ServiceHistory', backref='teacher', cascade='all, delete-orphan', lazy='joined')
    seniority_records = relationship('SeniorityRecord', backref='teacher', cascade='all, delete-orphan')
    assessments = relationship('PromotionAssessment', backref='teacher', cascade='all, delete-orphan')
    correction_requests = relationship('CorrectionRequest', backref='teacher', cascade='all, delete-orphan')

    @property
    def age(self):
        """Calculates current age in completed years."""
        if not self.date_of_birth:
            return 0
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def superannuation_date(self):
        """Exact date teacher attains statutory superannuation age (60 years)."""
        if not self.date_of_birth:
            return None
        try:
            return self.date_of_birth.replace(year=self.date_of_birth.year + 60)
        except ValueError:
            # Handle Feb 29 leap year
            return self.date_of_birth.replace(year=self.date_of_birth.year + 60, day=28)

    def is_superannuated_as_of(self, as_of_date=None):
        """Returns True if teacher is aged 60 or above as of the target date."""
        if not self.date_of_birth:
            return False
        cutoff = as_of_date or date.today()
        sup_dt = self.superannuation_date
        return sup_dt is not None and sup_dt <= cutoff

    @property
    def missing_fields(self):
        """Returns list of missing administrative and contact fields for this teacher."""
        missing = []
        if not self.mobile or str(self.mobile).strip() in ['', 'N/A']:
            missing.append('Mobile Number')
        if not self.email or str(self.email).strip() in ['', 'N/A']:
            missing.append('Email Address')
        if not self.address or str(self.address).strip() in ['', 'N/A']:
            missing.append('Residential Address')
        if not self.school_emis_code or str(self.school_emis_code).strip() in ['', 'N/A']:
            missing.append('School EMIS Code')
        if not self.regularization_date:
            missing.append('Regularization Date')
        return missing

    def __repr__(self):
        return f'<Teacher {self.personnel_no} - {self.full_name} ({self.current_designation})>'
