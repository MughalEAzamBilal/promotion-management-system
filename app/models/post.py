from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from .user import Base

class TeachingPost(Base):
    __tablename__ = 'teaching_posts'

    id = Column(Integer, primary_key=True)
    post_code = Column(String(50), unique=True, nullable=False)
    post_title = Column(String(120), nullable=False)
    cadre = Column(String(80), nullable=False)  # Primary, Elementary, Secondary, Higher Secondary, Administrative, Educator
    basic_scale = Column(Integer, nullable=False) # 12, 14, 15, 16, 17, 18, 19, 20
    category = Column(String(80), nullable=False) # Science, Arts, General, Math, Computer Science, English, etc.
    gender = Column(String(20), default='Both')   # Male, Female, Both
    feeder_post_title = Column(String(120), nullable=True)
    min_service_years = Column(Integer, default=0)
    prescribed_qualification = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_custom = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'post_code': self.post_code,
            'post_title': self.post_title,
            'cadre': self.cadre,
            'basic_scale': self.basic_scale,
            'category': self.category,
            'gender': self.gender,
            'feeder_post_title': self.feeder_post_title,
            'min_service_years': self.min_service_years,
            'prescribed_qualification': self.prescribed_qualification,
            'is_active': self.is_active,
            'is_custom': self.is_custom,
            'display_order': self.display_order
        }

    def __repr__(self):
        return f'<TeachingPost {self.post_title} (BS-{self.basic_scale}) - {self.cadre}>'
