from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .user import Base

class RuleSource(Base):
    __tablename__ = 'rule_sources'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False) # e.g. SED Service Rules 2014
    notification_no = Column(String(150), nullable=False) # e.g. SOR-III(S&GAD)1-19/2004(P)
    notification_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=False)
    version = Column(String(20), default='1.0') # e.g. '1.0', '1.1'
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True) # Null for currently active version
    amendment_notes = Column(Text, nullable=True)
    issuing_authority = Column(String(200), default='S&GAD / SED')
    document_summary = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rules = relationship('PromotionRule', backref='source', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<RuleSource {self.notification_no} - {self.title}>'

class PromotionRule(Base):
    __tablename__ = 'promotion_rules'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('rule_sources.id'), nullable=False, index=True)
    
    rule_code = Column(String(80), unique=True, nullable=False) # e.g. PST_TO_EST_SCI
    rule_name = Column(String(200), nullable=False)
    
    source_designation = Column(String(80), nullable=False) # PST
    source_bs = Column(Integer, nullable=False)             # 14
    target_designation = Column(String(80), nullable=False) # EST (Science)
    target_bs = Column(Integer, nullable=False)             # 15
    promotion_category = Column(String(80), nullable=False) # Science, Arts, English, etc.
    
    min_regular_service_years = Column(Float, default=3.0)  # Regular service in source grade
    min_total_service_years = Column(Float, default=3.0)
    
    # Qualification requirements
    required_degree_level = Column(String(80), nullable=False) # Bachelor, Master, BS-4Years
    required_degree_names = Column(String(255), nullable=False) # e.g. B.Sc, B.S, B.A
    required_subjects = Column(String(255), nullable=False)    # e.g. Physics, Chemistry, Mathematics
    required_professional_degree = Column(String(255), default='B.Ed,B.S.Ed,ADE') # Professional requirement
    
    quota_percentage = Column(Float, default=50.0)             # e.g. 50% for promotion channel
    min_acr_score = Column(Float, default=60.0)
    requires_inquiry_clearance = Column(Boolean, default=True)
    
    version = Column(String(20), default='1.0') # e.g. '1.0', '1.1'
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True) # Null for currently active version
    amendment_notes = Column(Text, nullable=True)
    predecessor_rule_id = Column(Integer, ForeignKey('promotion_rules.id'), nullable=True)
    
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessments = relationship('PromotionAssessment', backref='rule')

    @property
    def promotion_quota_percent(self):
        return self.quota_percentage or 50.0

    @property
    def feeder_cadre_percentage(self):
        return self.quota_percentage or 50.0

    def __repr__(self):
        return f'<PromotionRule {self.rule_code}: {self.source_designation} -> {self.target_designation}>'
