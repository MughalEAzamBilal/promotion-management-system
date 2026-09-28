from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from .user import Base

class AdSenseSetting(Base):
    __tablename__ = 'adsense_settings'

    id = Column(Integer, primary_key=True)
    publisher_id = Column(String(100), default='ca-pub-XXXXXXXXXXXXXXXX') # ca-pub-XXXX
    ads_enabled = Column(Boolean, default=False)
    auto_ads_enabled = Column(Boolean, default=False)
    test_mode = Column(Boolean, default=True) # Shows clean test banner placeholders when active
    header_code = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AdSenseSetting Enabled={self.ads_enabled} Pub={self.publisher_id}>'

class AdSlot(Base):
    __tablename__ = 'ad_slots'

    id = Column(Integer, primary_key=True)
    slot_name = Column(String(100), nullable=False) # e.g. Header Leaderboard, Sidebar Rectangle
    slot_id = Column(String(100), nullable=False)   # Google Ad Unit ID e.g. 1234567890
    slot_format = Column(String(50), default='responsive') # 'responsive', 'horizontal', 'rectangle'
    placement = Column(String(50), nullable=False)  # 'header', 'sidebar', 'content_top', 'content_bottom', 'footer'
    target_roles = Column(String(50), default='ALL') # 'ALL', 'TEACHER', 'ADMIN'
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AdSlot {self.slot_name} ({self.placement})>'
