from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .user import Base

class PromotionAssessment(Base):
    __tablename__ = 'promotion_assessments'

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    rule_id = Column(Integer, ForeignKey('promotion_rules.id'), nullable=False, index=True)
    
    assessment_date = Column(DateTime, default=datetime.utcnow)
    date_as_of = Column(Date, nullable=False)
    
    target_designation = Column(String(80), nullable=False)
    target_bs = Column(Integer, nullable=False)
    promotion_category = Column(String(80), nullable=False)
    
    # Official Status: 'Eligible for Consideration', 'Ineligible', 'Pending Verification', 'Conditionally Eligible'
    overall_status = Column(String(80), nullable=False)
    
    service_check_status = Column(String(20), nullable=False)      # 'Pass', 'Fail', 'Pending'
    service_actual_years = Column(Float, nullable=False)
    service_required_years = Column(Float, nullable=False)
    
    qualification_check_status = Column(String(20), nullable=False) # 'Pass', 'Fail', 'Pending'
    professional_check_status = Column(String(20), nullable=False)  # 'Pass', 'Fail', 'Pending'
    seniority_check_status = Column(String(20), nullable=False)     # 'Pass', 'Fail', 'Pending'
    inquiry_check_status = Column(String(20), nullable=False)       # 'Pass', 'Fail', 'Pending'
    acr_check_status = Column(String(20), nullable=False)           # 'Pass', 'Fail', 'Pending'
    
    details_json = Column(Text, nullable=True) # Full structured breakdown for transparency
    assessed_by = Column(String(100), default='System')
    
    # Official Committee Decision & Statutory Reference
    committee_decision = Column(String(50), default='Pending Review') # 'Pending Review', 'Promoted', 'Rejected', 'Deferred'
    decision_reason = Column(Text, nullable=True)
    statutory_reference = Column(String(255), nullable=True)
    decided_by = Column(String(100), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PromotionAssessment {self.teacher_id} -> {self.target_designation}: {self.overall_status}>'


class PromotionRun(Base):
    """
    Official Promotion Scrutiny Run.
    Preserves audit history of every DPC roll generation and supports
    the 'Draft -> Finalized -> Locked' lifecycle freeze.
    """
    __tablename__ = 'promotion_runs'

    id = Column(Integer, primary_key=True)
    run_no = Column(String(50), nullable=False, unique=True, index=True) # e.g. RUN-2026-001
    rule_id = Column(Integer, ForeignKey('promotion_rules.id'), nullable=False, index=True)
    rule = relationship('PromotionRule', backref='promotion_runs')
    district = Column(String(80), nullable=False, index=True)
    target_designation = Column(String(80), nullable=False)
    target_bs = Column(Integer, nullable=False)
    
    cutoff_date = Column(Date, nullable=False)
    run_date = Column(DateTime, default=datetime.utcnow)
    
    sanctioned_posts = Column(Integer, default=0)
    working_strength = Column(Integer, default=0)
    vacant_posts = Column(Integer, default=0)
    quota_percent = Column(Float, default=50.0)
    quota_posts = Column(Integer, default=0)
    
    total_candidates = Column(Integer, default=0)
    eligible_count = Column(Integer, default=0)
    ineligible_count = Column(Integer, default=0)
    zone1_count = Column(Integer, default=0)
    
    # Official Roll Lifecycle: 'Draft', 'Finalized', 'Locked'
    status = Column(String(30), default='Draft')
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String(100), nullable=True)
    
    # Reopen / Revision history if locked roll is revised
    reopen_reason = Column(Text, nullable=True)
    reopened_at = Column(DateTime, nullable=True)
    reopened_by = Column(String(100), nullable=True)
    
    snapshot_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_locked(self):
        return self.status == 'Locked'

    def __repr__(self):
        return f'<PromotionRun {self.run_no}: {self.target_designation} ({self.district}) [{self.status}]>'

