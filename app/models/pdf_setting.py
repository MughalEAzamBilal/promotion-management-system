import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from .user import Base

class PdfSetting(Base):
    __tablename__ = 'pdf_settings'

    id = Column(Integer, primary_key=True)
    gov_header = Column(String(150), default='SCHOOL EDUCATION DEPARTMENT')
    dept_header = Column(String(150), default='TEACHER PROMOTION MANAGEMENT')
    portal_title = Column(String(150), default='TEACHER PROMOTION PORTAL')
    
    # Official Authority Stamps Customization
    is_stamp_enabled = Column(Boolean, default=True)
    stamp_text = Column(String(150), default='OFFICIAL SEAL * DISTRICT EDUCATION AUTHORITY')
    stamp_shape = Column(String(30), default='Round')   # Round, Oval, Rectangular
    stamp_color = Column(String(30), default='#0B6B3A') # Hex color
    
    # Customizable District Promotion Committee Signatories / Members
    signatories_json = Column(Text, nullable=True)
    
    # Backwards-compatible legacy signature columns
    authority_1_title = Column(String(100), default='Member 1 / DEO (SE/EE)')
    authority_1_dept = Column(String(100), default='District Promotion Committee')
    
    authority_2_title = Column(String(100), default='Member 2 / Deputy Director')
    authority_2_dept = Column(String(100), default='School Education Department')
    
    authority_3_title = Column(String(100), default='Chairman / Chief Executive Officer')
    authority_3_dept = Column(String(100), default='District Education Authority (DEA)')
    
    legal_disclaimer = Column(
        Text,
        default='Issued under the School Education Department Service Rules 2014 as amended. Certified official record of the District Promotion Committee.'
    )
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def signatories(self):
        """Returns list of customized signatories [{'title': ..., 'dept': ..., 'name': ...}, ...]"""
        if self.signatories_json:
            try:
                data = json.loads(self.signatories_json)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception:
                pass
        # Default fallback to legacy 3 members
        return [
            {"title": self.authority_1_title or "Member 1 / DEO (SE/EE)", "dept": self.authority_1_dept or "District Promotion Committee", "name": ""},
            {"title": self.authority_2_title or "Member 2 / Deputy Director", "dept": self.authority_2_dept or "School Education Department", "name": ""},
            {"title": self.authority_3_title or "Chairman / Chief Executive Officer", "dept": self.authority_3_dept or "District Education Authority (DEA)", "name": ""}
        ]

    def set_signatories(self, members_list):
        """Sets signatories JSON from a list of dicts."""
        self.signatories_json = json.dumps(members_list)

    @classmethod
    def get_active_settings(cls, session=None):
        """Fetches the singleton active setting or initializes defaults."""
        if session is not None:
            s = session
        else:
            from app import db_session
            s = db_session
        settings = s.query(cls).first()
        if not settings:
            settings = cls()
            s.add(settings)
            s.commit()
        return settings

    def __repr__(self):
        return f'<PdfSetting shape={self.stamp_shape} enabled={self.is_stamp_enabled} header={self.dept_header}>'

