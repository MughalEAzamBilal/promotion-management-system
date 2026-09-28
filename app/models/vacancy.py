from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from .user import Base

class Vacancy(Base):
    __tablename__ = 'vacancies'

    id = Column(Integer, primary_key=True)
    district = Column(String(80), nullable=False)
    tehsil = Column(String(80), nullable=True)
    designation = Column(String(80), nullable=False) # e.g. EST (Science), SST (Arts), SS (Math)
    bs = Column(Integer, nullable=False)             # 15, 16, 17, 18
    category = Column(String(80), nullable=True)     # Science, Arts, General
    
    sanctioned_posts = Column(Integer, default=0)
    filled_posts = Column(Integer, default=0)
    vacant_posts = Column(Integer, default=0)
    
    promotion_quota_percent = Column(Float, default=50.0)
    promotion_quota_posts = Column(Integer, default=0)
    direct_quota_posts = Column(Integer, default=0)
    
    year = Column(Integer, default=2026)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def working_strength(self):
        return self.filled_posts or 0

    def calculate_vacancies(self):
        self.vacant_posts = max(0, self.sanctioned_posts - self.filled_posts)
        self.promotion_quota_posts = int(round(self.vacant_posts * (self.promotion_quota_percent / 100.0)))
        self.direct_quota_posts = max(0, self.vacant_posts - self.promotion_quota_posts)

    def __repr__(self):
        return f'<Vacancy {self.district} - {self.designation} (BS-{self.bs}): {self.vacant_posts} Vacant>'
