from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from .user import Base

class Qualification(Base):
    __tablename__ = 'qualifications'

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    
    degree_level = Column(String(50), nullable=False)   # Matric, Intermediate, Bachelor, Master, BS-4Years, M.Phil, PhD
    degree_name = Column(String(100), nullable=False)   # SSC, HSSC, B.Sc, B.A, B.S, M.Sc, M.A, B.Ed, M.Ed, ADE
    subject = Column(String(100), nullable=False)       # Science, Mathematics, Physics, English, Urdu, Arts
    major_subject = Column(String(100), nullable=True)
    minor_subject = Column(String(100), nullable=True)
    
    division = Column(String(20), nullable=True)        # First, Second, Third
    marks_obtained = Column(Float, nullable=True)
    total_marks = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    cgpa = Column(Float, nullable=True)
    
    passing_year = Column(Integer, nullable=False)
    board_university = Column(String(150), nullable=False) # BISE Lahore, Univ of Punjab, AIOU, etc.
    
    professional_qualification = Column(Boolean, default=False) # True for B.Ed, M.Ed, ADE, B.S.Ed
    registration_number = Column(String(80), nullable=True)
    
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
        """Returns list of missing data values for this qualification record."""
        missing = []
        if not self.division or str(self.division).strip() in ['', 'Division N/A', 'N/A', 'None']:
            missing.append('Division / Grade')
        if not self.board_university or str(self.board_university).strip() in ['', 'N/A']:
            missing.append('Board / University')
        if not self.passing_year:
            missing.append('Passing Year')
        if not self.major_subject or str(self.major_subject).strip() in ['', 'N/A']:
            missing.append('Major Subject')
        if not self.registration_number or str(self.registration_number).strip() in ['', 'N/A']:
            missing.append('Roll / Reg No')
        if self.marks_obtained is None and not self.cgpa:
            missing.append('Marks Obtained')
        if self.total_marks is None and not self.cgpa:
            missing.append('Total Marks')
        return missing

    def __repr__(self):
        return f'<Qualification {self.degree_name} ({self.subject}) - {self.passing_year}>'
