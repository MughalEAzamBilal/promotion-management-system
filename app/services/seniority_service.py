from datetime import datetime
from app.models.teacher import Teacher
from app.models.seniority import SeniorityRecord

def recompute_cadre_seniority(db_session, district, designation, bs, current_user=None):
    """
    Computes or re-indexes seniority order for a specific cadre within a district.
    Sorting priority:
    1. Regularization Date (Earlier date is senior)
    2. Appointment Date
    3. Date of Birth (Older in age is senior - standard Punjab civil service rule)
    """
    teachers = db_session.query(Teacher).filter(
        Teacher.district == district,
        Teacher.current_designation == designation,
        Teacher.current_bs == bs,
        Teacher.is_deleted == False
    ).all()

    # Sort key function
    def seniority_sort_key(t):
        reg = t.regularization_date or t.current_post_date or t.appointment_date
        app = t.appointment_date or reg
        dob = t.date_of_birth
        return (reg, app, dob)

    sorted_teachers = sorted(teachers, key=seniority_sort_key)

    rank = 1
    for t in sorted_teachers:
        t.seniority_no = rank
        sen_date = t.seniority_date or t.regularization_date or t.current_post_date or t.appointment_date or datetime.utcnow().date()
        sen_rec = db_session.query(SeniorityRecord).filter(
            SeniorityRecord.teacher_id == t.id,
            SeniorityRecord.designation == designation,
            SeniorityRecord.bs == bs
        ).first()
        if sen_rec:
            sen_rec.seniority_no = rank
            sen_rec.district = district
            if current_user:
                sen_rec.verified_by = getattr(current_user, 'username', 'SYSTEM')
        else:
            sen_rec = SeniorityRecord(
                teacher_id=t.id,
                seniority_no=rank,
                seniority_date=sen_date,
                designation=designation,
                bs=bs,
                category=t.current_category or 'General',
                district=district,
                seniority_list_reference=f"DPC/SED/{district.upper()}/{sen_date.year}",
                seniority_list_date=sen_date,
                is_official=True,
                verified=True,
                verified_by=getattr(current_user, 'username', 'SYSTEM') if current_user else 'SYSTEM',
                verified_at=datetime.utcnow()
            )
            db_session.add(sen_rec)
        rank += 1

    db_session.commit()
    return sorted_teachers
