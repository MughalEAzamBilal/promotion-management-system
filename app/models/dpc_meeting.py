from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, Text
from .user import Base

class DpcMeeting(Base):
    __tablename__ = 'dpc_meetings'

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False, index=True)
    meeting_no = Column(String(50), nullable=False)           # e.g., 'DPC Meeting #1/2026'
    title = Column(String(150), nullable=False)                # e.g., 'Annual Elementary & Secondary Promotion Board'
    meeting_date = Column(Date, nullable=False, index=True)    # Statutory start/evaluation cutoff date
    end_date = Column(Date, nullable=True)                     # End date of DPC proceedings
    district = Column(String(80), nullable=True, default='All Districts')
    target_cadres = Column(String(200), default='PST, EST, SST')
    status = Column(String(30), default='Scheduled')           # Scheduled, In Progress, Completed, Postponed
    agenda_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def effective_end_date(self):
        """Returns end_date if specified, else defaults to meeting_date."""
        return self.end_date or self.meeting_date

    @property
    def is_editable(self):
        """
        DPC Annual Schedule is editable before or on its scheduled end date.
        """
        if not self.effective_end_date:
            return True
        return date.today() <= self.effective_end_date

    def get_retiring_summary(self, session=None):
        """
        Calculates total and cadre-wise count of teachers who have attained age 60 (superannuation)
        on or before this meeting's date.
        """
        from app.models.teacher import Teacher
        if session is not None:
            s = session
        else:
            from app import db_session
            s = db_session
        query = s.query(Teacher).filter(
            Teacher.is_deleted == False,
            Teacher.date_of_birth.isnot(None)
        )
        if self.district and self.district != 'All Districts':
            query = query.filter(Teacher.district == self.district)

        teachers = query.all()
        retiring_teachers = []
        cadre_counts = {}

        for t in teachers:
            # Check superannuation as of this meeting date
            if t.is_superannuated_as_of(self.meeting_date):
                retiring_teachers.append(t)
                cadre = (t.current_designation or 'General').strip()
                # Clean cadre abbreviation (e.g. PST, EST, SST)
                if 'PST' in cadre.upper() or 'PRIMARY' in cadre.upper():
                    group = 'PST'
                elif 'EST' in cadre.upper() or 'ELEMENTARY' in cadre.upper():
                    group = 'EST'
                elif 'SST' in cadre.upper() or 'SECONDARY' in cadre.upper():
                    group = 'SST'
                elif 'SS' in cadre.upper() or 'SUBJECT SPECIALIST' in cadre.upper():
                    group = 'SS'
                elif 'HEAD' in cadre.upper() or 'HM' in cadre.upper():
                    group = 'HM/Principal'
                else:
                    group = cadre.split('(')[0].strip() or 'Other'
                
                cadre_counts[group] = cadre_counts.get(group, 0) + 1

        return {
            'total_retiring': len(retiring_teachers),
            'cadre_counts': cadre_counts,
            'teachers': retiring_teachers
        }

    def __repr__(self):
        return f'<DpcMeeting {self.meeting_no} ({self.meeting_date}) - {self.status}>'
