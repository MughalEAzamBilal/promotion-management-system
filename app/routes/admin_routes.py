import os
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, send_file, current_app, jsonify, abort
from werkzeug.utils import secure_filename
from sqlalchemy import func
from app import role_required
from app.models.user import User
from app.models.teacher import Teacher
from app.models.qualification import Qualification
from app.models.service import ServiceHistory
from app.models.seniority import SeniorityRecord
from app.models.rule import PromotionRule, RuleSource
from app.models.assessment import PromotionAssessment, PromotionRun
from app.models.vacancy import Vacancy
from app.models.correction import CorrectionRequest
from app.models.post import TeachingPost
from app.models.dpc_meeting import DpcMeeting
from app.models.pdf_setting import PdfSetting
from app.models.password_reset import PasswordResetRequest
from app.services.audit_service import log_audit
from app.services.promotion_engine import evaluate_eligibility, evaluate_cadre_for_rule
from app.services.excel_service import (
    generate_excel_template, generate_education_excel_template, preview_excel_import,
    execute_excel_import, export_teachers_to_excel, export_promotion_list_to_excel
)
from app.services.pdf_service import (
    generate_teacher_dossier_pdf, generate_eligibility_report_pdf, generate_seniority_list_pdf,
    generate_promotion_list_pdf, generate_retiring_teachers_pdf
)
from app.services.seniority_service import recompute_cadre_seniority

admin_bp = Blueprint('admin', __name__)

def get_or_404(model, ident):
    obj = g.db.query(model).get(ident)
    if not obj:
        abort(404)
    return obj


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@role_required(['ADMIN', 'SUPERADMIN'])
def dashboard():
    db = g.db
    total_teachers = db.query(Teacher).filter(Teacher.is_deleted == False).count()
    verified_teachers = db.query(Teacher).filter(Teacher.verification_status == 'Verified', Teacher.is_deleted == False).count()
    pending_teachers = db.query(Teacher).filter(Teacher.verification_status == 'Pending', Teacher.is_deleted == False).count()
    pending_corrections = db.query(CorrectionRequest).filter(CorrectionRequest.status == 'Pending').count()
    total_vacancies = db.query(Vacancy).count()
    recent_assessments = db.query(PromotionAssessment).order_by(PromotionAssessment.assessment_date.desc()).limit(5).all()

    # Work to Do Metrics
    # 1. Teachers with missing data (no qualifications or missing crucial dates)
    missing_data_teachers = db.query(Teacher).filter(
        Teacher.is_deleted == False,
        (
            (~Teacher.qualifications.any()) |
            (Teacher.regularization_date.is_(None)) |
            (Teacher.appointment_date.is_(None)) |
            (Teacher.date_of_birth.is_(None))
        )
    ).count()

    # 2. Superannuation: age 60+ pending official retirement orders
    cutoff_60 = date.today().replace(year=date.today().year - 60)
    pending_retirements = db.query(Teacher).filter(
        Teacher.is_deleted == False,
        Teacher.date_of_birth.isnot(None),
        Teacher.date_of_birth <= cutoff_60,
        Teacher.account_status != 'Retired'
    ).count()

    # 3. DPC upcoming meetings & tasks
    upcoming_dpc_meetings = db.query(DpcMeeting).filter(DpcMeeting.meeting_date >= date.today()).count()
    total_dpc_meetings = db.query(DpcMeeting).count()

    # 4. Ready promotion scrutiny rolls / runs
    ready_promotion_runs = db.query(PromotionRun).filter(PromotionRun.status.in_(['Draft', 'Finalized'])).count()
    total_promotion_runs = db.query(PromotionRun).count()

    # 5. Teacher Password Reset Requests
    resets_query = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.account_role == 'TEACHER',
        PasswordResetRequest.status == 'Pending'
    )
    admin_district = getattr(g.user, 'district', None)
    if g.user.role == 'ADMIN' and admin_district:
        resets_query = resets_query.filter(
            (PasswordResetRequest.district == admin_district) | (PasswordResetRequest.district.is_(None))
        )
    pending_teacher_resets = resets_query.count()

    # 9-Stage Operational Workflow State
    workflow_stages = [
        {
            'step': 1,
            'name': 'Data Preparation',
            'desc': 'Teacher Biodata, Qualifications & Service Records',
            'status': 'Complete' if missing_data_teachers == 0 else f'{missing_data_teachers} Missing Data',
            'badge_class': 'bg-success' if missing_data_teachers == 0 else 'bg-warning text-dark',
            'is_done': missing_data_teachers == 0,
            'url': url_for('admin.data_quality')
        },
        {
            'step': 2,
            'name': 'Teacher Verification',
            'desc': 'Departmental review of imported teacher profiles',
            'status': 'Complete' if pending_teachers == 0 else f'{pending_teachers} Pending',
            'badge_class': 'bg-success' if pending_teachers == 0 else 'bg-warning text-dark',
            'is_done': pending_teachers == 0,
            'url': url_for('admin.verifications')
        },
        {
            'step': 3,
            'name': 'Corrections',
            'desc': 'Review & one-by-one approval of teacher claims',
            'status': 'Complete' if pending_corrections == 0 else f'{pending_corrections} Pending',
            'badge_class': 'bg-success' if pending_corrections == 0 else 'bg-danger',
            'is_done': pending_corrections == 0,
            'url': url_for('admin.corrections')
        },
        {
            'step': 4,
            'name': 'Retirement Review',
            'desc': 'Age 60+ superannuation audit & bulk exclusion',
            'status': 'Complete' if pending_retirements == 0 else f'{pending_retirements} Pending',
            'badge_class': 'bg-success' if pending_retirements == 0 else 'bg-warning text-dark',
            'is_done': pending_retirements == 0,
            'url': url_for('admin.retirements_review')
        },
        {
            'step': 5,
            'name': 'Vacancies & Quotas',
            'desc': 'Sanctioned posts, working strength & 50/50 quotas',
            'status': 'Complete' if total_vacancies > 0 else 'Needs Entry',
            'badge_class': 'bg-success' if total_vacancies > 0 else 'bg-secondary',
            'is_done': total_vacancies > 0,
            'url': url_for('admin.vacancies')
        },
        {
            'step': 6,
            'name': 'DPC Schedule',
            'desc': 'Annual calendar & DPC meeting scheduling',
            'status': f'{upcoming_dpc_meetings} Upcoming' if upcoming_dpc_meetings > 0 else ('Scheduled' if total_dpc_meetings > 0 else 'Create Meeting'),
            'badge_class': 'bg-success' if upcoming_dpc_meetings > 0 or total_dpc_meetings > 0 else 'bg-info text-dark',
            'is_done': total_dpc_meetings > 0,
            'url': url_for('admin.dpc_schedule')
        },
        {
            'step': 7,
            'name': 'Promotion Scrutiny',
            'desc': 'Run statutory eligibility, seniority & quota engine',
            'status': 'Ready' if total_vacancies > 0 else 'Awaiting Vacancies',
            'badge_class': 'bg-primary' if total_vacancies > 0 else 'bg-secondary',
            'is_done': ready_promotion_runs > 0,
            'url': url_for('admin.promotion_lists')
        },
        {
            'step': 8,
            'name': 'Official Gazette',
            'desc': 'Stamps, signatories & printable official gazette',
            'status': 'Ready',
            'badge_class': 'bg-info text-dark',
            'is_done': True,
            'url': url_for('admin.pdf_management')
        },
        {
            'step': 9,
            'name': 'DPC Decisions',
            'desc': 'Promote, Defer, Supersede & atomic roll freeze',
            'status': 'Active',
            'badge_class': 'bg-success',
            'is_done': True,
            'url': url_for('admin.promotion_lists', tab='promoted')
        }
    ]

    return render_template(
        'admin/dashboard.html',
        total_teachers=total_teachers,
        verified_teachers=verified_teachers,
        pending_teachers=pending_teachers,
        pending_corrections=pending_corrections,
        total_vacancies=total_vacancies,
        missing_data_teachers=missing_data_teachers,
        pending_retirements=pending_retirements,
        upcoming_dpc_meetings=upcoming_dpc_meetings,
        ready_promotion_runs=ready_promotion_runs,
        total_promotion_runs=total_promotion_runs,
        workflow_stages=workflow_stages,
        recent_assessments=recent_assessments,
        pending_teacher_resets=pending_teacher_resets
    )

@admin_bp.route('/data-quality')
@role_required(['ADMIN', 'SUPERADMIN'])
def data_quality():
    db = g.db
    category = request.args.get('category', 'all').strip()
    district_filter = request.args.get('district', '').strip()

    base_query = db.query(Teacher).filter(Teacher.is_deleted == False)
    if district_filter:
        base_query = base_query.filter(Teacher.district == district_filter)

    total_active = base_query.count()

    # Category queries
    missing_qual_teachers = base_query.filter(~Teacher.qualifications.any()).all()
    missing_dates_teachers = base_query.filter(
        (Teacher.regularization_date.is_(None)) | (Teacher.appointment_date.is_(None))
    ).all()
    missing_bio_teachers = base_query.filter(
        (Teacher.date_of_birth.is_(None)) | (Teacher.cnic.is_(None)) | (Teacher.personnel_no.is_(None))
    ).all()
    unverified_teachers = base_query.filter(Teacher.verification_status != 'Verified').all()

    # Complete profiles
    complete_teachers_count = base_query.filter(
        Teacher.qualifications.any(),
        Teacher.regularization_date.isnot(None),
        Teacher.appointment_date.isnot(None),
        Teacher.date_of_birth.isnot(None),
        Teacher.verification_status == 'Verified'
    ).count()

    # Selected list for display
    if category == 'missing_qual':
        display_teachers = missing_qual_teachers
        active_label = 'Missing Academic & Professional Qualifications'
    elif category == 'missing_dates':
        display_teachers = missing_dates_teachers
        active_label = 'Missing Appointment or Regularization Dates'
    elif category == 'missing_bio':
        display_teachers = missing_bio_teachers
        active_label = 'Missing Personnel No, CNIC, or Date of Birth'
    elif category == 'unverified':
        display_teachers = unverified_teachers
        active_label = 'Unverified Teacher Profiles'
    else:
        seen_ids = set()
        display_teachers = []
        for t in missing_qual_teachers + missing_dates_teachers + missing_bio_teachers + unverified_teachers:
            if t.id not in seen_ids:
                seen_ids.add(t.id)
                display_teachers.append(t)
        active_label = 'All Profiles with Data Issues'

    districts = [r[0] for r in db.query(Teacher.district).distinct().all() if r[0]]

    return render_template(
        'admin/data_quality.html',
        total_active=total_active,
        complete_teachers_count=complete_teachers_count,
        missing_qual_count=len(missing_qual_teachers),
        missing_dates_count=len(missing_dates_teachers),
        missing_bio_count=len(missing_bio_teachers),
        unverified_count=len(unverified_teachers),
        display_teachers=display_teachers,
        category=category,
        active_label=active_label,
        districts=sorted(districts),
        district_filter=district_filter
    )

@admin_bp.route('/teachers')
@role_required(['ADMIN', 'SUPERADMIN'])
def teachers_list():
    db = g.db
    q = request.args.get('q', '').strip()
    district = request.args.get('district', '').strip()
    designation = request.args.get('designation', '').strip()
    status = request.args.get('status', '').strip()

    query = db.query(Teacher).filter(Teacher.is_deleted == False)

    if q:
        query = query.filter(
            (Teacher.full_name.ilike(f'%{q}%')) |
            (Teacher.cnic.ilike(f'%{q}%')) |
            (Teacher.personnel_no.ilike(f'%{q}%')) |
            (Teacher.school_name.ilike(f'%{q}%'))
        )
    if district:
        query = query.filter(Teacher.district == district)
    if designation:
        query = query.filter(Teacher.current_designation == designation)
    if status:
        query = query.filter(Teacher.verification_status == status)

    teachers = query.order_by(Teacher.seniority_no.asc().nullslast(), Teacher.appointment_date.asc()).limit(300).all()

    # Get distinct filter options
    districts = [r[0] for r in db.query(Teacher.district).distinct().all() if r[0]]
    designations = [r[0] for r in db.query(Teacher.current_designation).distinct().all() if r[0]]

    return render_template(
        'admin/teachers_list.html',
        teachers=teachers,
        districts=sorted(districts),
        designations=sorted(designations),
        selected_q=q,
        selected_district=district,
        selected_designation=designation,
        selected_status=status
    )

@admin_bp.route('/teachers/new', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def new_teacher():
    db = g.db
    if request.method == 'POST':
        personnel_no = request.form.get('personnel_no', '').strip()
        cnic = request.form.get('cnic', '').strip()
        full_name = request.form.get('full_name', '').strip()
        father_name = request.form.get('father_name', '').strip()
        gender = request.form.get('gender', 'Male')
        dob_str = request.form.get('date_of_birth')
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        district = request.form.get('district', '').strip()
        tehsil = request.form.get('tehsil', '').strip()
        school_name = request.form.get('school_name', '').strip()
        school_emis = request.form.get('school_emis_code', '').strip()
        designation = request.form.get('current_designation', 'PST').strip()
        bs = int(request.form.get('current_bs', 14))
        category = request.form.get('current_category', 'General').strip()
        app_date_str = request.form.get('appointment_date')
        reg_date_str = request.form.get('regularization_date')
        seniority_no = request.form.get('seniority_no')

        if not personnel_no or not cnic or not full_name or not app_date_str:
            flash("Personnel No, CNIC, Full Name, and Appointment Date are mandatory.", "danger")
            return render_template('admin/teacher_form.html', teacher=None)

        if db.query(Teacher).filter((Teacher.cnic == cnic) | (Teacher.personnel_no == personnel_no)).first():
            flash("A teacher with this CNIC or Personnel Number is already registered.", "danger")
            return render_template('admin/teacher_form.html', teacher=None)

        dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else date(1985, 1, 1)
        app_date = datetime.strptime(app_date_str, '%Y-%m-%d').date()
        reg_date = datetime.strptime(reg_date_str, '%Y-%m-%d').date() if reg_date_str else app_date

        teacher = Teacher(
            personnel_no=personnel_no,
            cnic=cnic,
            full_name=full_name,
            father_name=father_name,
            gender=gender,
            date_of_birth=dob,
            mobile=mobile,
            email=email,
            district=district,
            tehsil=tehsil,
            school_name=school_name,
            school_emis_code=school_emis,
            current_designation=designation,
            current_bs=bs,
            current_category=category,
            appointment_date=app_date,
            joining_date=app_date,
            regularization_date=reg_date,
            current_post_date=reg_date,
            seniority_no=int(seniority_no) if seniority_no else None,
            seniority_date=reg_date if seniority_no else None,
            verification_status='Pending'
        )
        db.add(teacher)
        db.flush()

        # Create user account for teacher self-service
        user_acc = User(
            teacher_id=teacher.id,
            username=cnic,
            role='TEACHER',
            full_name=full_name,
            cnic=cnic,
            district=district,
            email=email,
            phone=mobile,
            is_active=True,
            is_first_login=True
        )
        user_acc.set_password('Teacher@123')
        db.add(user_acc)

        # Initial service history
        service = ServiceHistory(
            teacher_id=teacher.id,
            designation=designation,
            bs=bs,
            school_name=school_name,
            district=district,
            tehsil=tehsil,
            from_date=reg_date,
            is_current_post=True,
            appointment_type='Regular',
            verification_status='Pending'
        )
        db.add(service)

        db.commit()
        log_audit(db, g.user, 'CREATE_TEACHER', entity_type='Teacher', entity_id=teacher.id, details=f"Registered teacher: {full_name} ({cnic})", ip_address=request.remote_addr)
        flash(f"Teacher '{full_name}' registered successfully! Teacher Portal Login Credentials -> Username: '{cnic}', Default Password: 'Teacher@123'.", "success")
        return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

    return render_template('admin/teacher_form.html', teacher=None)

@admin_bp.route('/teachers/<int:teacher_id>')
@role_required(['ADMIN', 'SUPERADMIN'])
def teacher_detail(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    rules = db.query(PromotionRule).filter(
        PromotionRule.source_bs == teacher.current_bs,
        PromotionRule.is_active == True
    ).all()
    user_account = db.query(User).filter(User.teacher_id == teacher.id).first()
    return render_template('admin/teacher_detail.html', teacher=teacher, applicable_rules=rules, user_account=user_account)

@admin_bp.route('/teachers/<int:teacher_id>/edit', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def edit_teacher(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    if request.method == 'POST':
        teacher.full_name = request.form.get('full_name', teacher.full_name).strip()
        teacher.father_name = request.form.get('father_name', teacher.father_name).strip()
        teacher.gender = request.form.get('gender', teacher.gender)
        dob_str = request.form.get('date_of_birth')
        if dob_str:
            teacher.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
        teacher.mobile = request.form.get('mobile', teacher.mobile).strip()
        teacher.email = request.form.get('email', teacher.email).strip()
        teacher.district = request.form.get('district', teacher.district).strip()
        teacher.tehsil = request.form.get('tehsil', teacher.tehsil).strip()
        teacher.school_name = request.form.get('school_name', teacher.school_name).strip()
        teacher.school_emis_code = request.form.get('school_emis_code', teacher.school_emis_code).strip()
        teacher.current_designation = request.form.get('current_designation', teacher.current_designation).strip()
        teacher.current_bs = int(request.form.get('current_bs', teacher.current_bs))
        teacher.current_category = request.form.get('current_category', teacher.current_category).strip()
        
        reg_str = request.form.get('regularization_date')
        if reg_str:
            teacher.regularization_date = datetime.strptime(reg_str, '%Y-%m-%d').date()

        sen_no = request.form.get('seniority_no')
        teacher.seniority_no = int(sen_no) if sen_no else None
        
        inquiry = bool(request.form.get('disciplinary_inquiry_pending'))
        teacher.disciplinary_inquiry_pending = inquiry
        
        acr_val = request.form.get('acr_score_average')
        if acr_val:
            teacher.acr_score_average = float(acr_val)

        db.commit()
        log_audit(db, g.user, 'UPDATE_TEACHER', entity_type='Teacher', entity_id=teacher.id, details=f"Admin edited teacher profile: {teacher.full_name}", ip_address=request.remote_addr)
        flash("Teacher information updated successfully.", "success")
        return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

    return render_template('admin/teacher_form.html', teacher=teacher)

@admin_bp.route('/teachers/<int:teacher_id>/verify', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def verify_teacher(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    status = request.form.get('verification_status', 'Verified')
    notes = request.form.get('admin_notes', '').strip()
    
    teacher.verification_status = status
    if notes:
        teacher.admin_notes = notes
    db.commit()
    log_audit(db, g.user, 'VERIFY_TEACHER', entity_type='Teacher', entity_id=teacher.id, details=f"Marked teacher profile as {status}", ip_address=request.remote_addr)
    flash(f"Teacher profile verification status updated to '{status}'.", "success")
    return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

@admin_bp.route('/teachers/<int:teacher_id>/toggle-promotion-status', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def toggle_promotion_status(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    action = request.form.get('action', 'disable').strip().lower()
    redirect_url = request.form.get('redirect_url') or request.referrer or url_for('admin.teachers_list')

    if action == 'disable':
        reason = request.form.get('predefined_reason', 'Other / Custom Grounds').strip()
        custom_remarks = request.form.get('custom_remarks', '').strip()
        
        teacher.is_promotion_disabled = True
        teacher.promotion_disable_reason = reason
        teacher.promotion_disable_remarks = custom_remarks
        teacher.promotion_disabled_at = datetime.utcnow()
        teacher.promotion_disabled_by = g.user.username
        
        db.commit()
        log_audit(db, g.user, 'DISABLE_PROMOTION', entity_type='Teacher', entity_id=teacher.id,
                  details=f"Disabled promotion for {teacher.full_name} ({teacher.cnic}). Reason: {reason}. Remarks: {custom_remarks}",
                  ip_address=request.remote_addr)
        flash(f"Promotion consideration disabled for {teacher.full_name} [{reason}].", "warning")
    elif action == 'enable':
        teacher.is_promotion_disabled = False
        teacher.promotion_disable_reason = None
        teacher.promotion_disable_remarks = None
        teacher.promotion_disabled_at = None
        teacher.promotion_disabled_by = None
        
        db.commit()
        log_audit(db, g.user, 'ENABLE_PROMOTION', entity_type='Teacher', entity_id=teacher.id,
                  details=f"Re-enabled promotion consideration for {teacher.full_name} ({teacher.cnic}).",
                  ip_address=request.remote_addr)
        flash(f"Promotion consideration re-enabled for {teacher.full_name}.", "success")
    else:
        flash("Invalid action specified.", "danger")

    return redirect(redirect_url)


@admin_bp.route('/teachers/<int:teacher_id>/add-qualification', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def add_qualification(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    deg_level = request.form.get('degree_level', 'Bachelor').strip()
    deg_name = request.form.get('degree_name', '').strip()
    subject = request.form.get('subject', '').strip()
    division = request.form.get('division', 'First').strip()
    passing_year = int(request.form.get('passing_year', 2015))
    university = request.form.get('board_university', '').strip()
    is_prof = bool(request.form.get('professional_qualification'))

    q = Qualification(
        teacher_id=teacher.id,
        degree_level=deg_level,
        degree_name=deg_name,
        subject=subject,
        division=division,
        passing_year=passing_year,
        board_university=university,
        professional_qualification=is_prof,
        verification_status='Verified', # Admin-added qualifications are marked verified
        verified_by=g.user.username,
        verified_at=datetime.utcnow()
    )
    db.add(q)
    db.commit()
    log_audit(db, g.user, 'ADD_QUALIFICATION', entity_type='Qualification', entity_id=q.id, details=f"Added {deg_name} for teacher {teacher.cnic}", ip_address=request.remote_addr)
    flash(f"Qualification '{deg_name}' added and verified.", "success")
    return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

@admin_bp.route('/qualifications/<int:qual_id>/verify', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def verify_qualification(qual_id):
    db = g.db
    q = get_or_404(Qualification, qual_id)
    status = request.form.get('status', 'Verified')
    q.verification_status = status
    q.verified_by = g.user.username
    q.verified_at = datetime.utcnow()
    db.commit()
    log_audit(db, g.user, 'VERIFY_QUALIFICATION', entity_type='Qualification', entity_id=q.id, details=f"Qualification marked {status}", ip_address=request.remote_addr)
    flash(f"Qualification verification updated to '{status}'.", "info")
    return redirect(url_for('admin.teacher_detail', teacher_id=q.teacher_id))

@admin_bp.route('/teachers/<int:teacher_id>/add-service', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def add_service(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    desig = request.form.get('designation', '').strip()
    bs = int(request.form.get('bs', 14))
    school = request.form.get('school_name', '').strip()
    district = request.form.get('district', '').strip()
    tehsil = request.form.get('tehsil', '').strip()
    from_date_str = request.form.get('from_date')
    to_date_str = request.form.get('to_date')
    is_current = bool(request.form.get('is_current_post'))

    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else date.today()
    to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None

    # Service Overlap Validation
    if to_date and to_date < from_date:
        flash("Service record error: 'To Date' cannot be earlier than 'From Date'.", "danger")
        return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

    existing_services = teacher.service_history or []
    for s in existing_services:
        s_end = s.to_date or date.today()
        cur_end = to_date or date.today()
        # Check if ranges overlap
        if max(s.from_date, from_date) <= min(s_end, cur_end):
            flash(f"Service record overlap detected! Selected period overlaps with recorded service ({s.from_date} to {s.to_date or 'Present'}).", "danger")
            return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

    srv = ServiceHistory(
        teacher_id=teacher.id,
        designation=desig,
        bs=bs,
        school_name=school,
        district=district,
        tehsil=tehsil,
        from_date=from_date,
        to_date=to_date,
        is_current_post=is_current,
        appointment_type=request.form.get('appointment_type', 'Regular'),
        verification_status='Verified',
        verified_by=g.user.username,
        verified_at=datetime.utcnow()
    )
    db.add(srv)
    db.commit()
    log_audit(db, g.user, 'ADD_SERVICE_RECORD', entity_type='ServiceHistory', entity_id=srv.id, details=f"Added service record {desig} for teacher {teacher.cnic}", ip_address=request.remote_addr)
    flash("Service record successfully added and verified.", "success")
    return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

@admin_bp.route('/teachers/<int:teacher_id>/reset-password', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def reset_teacher_password(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    user_account = db.query(User).filter(User.teacher_id == teacher.id).first()
    new_password = request.form.get('new_password', 'Teacher@123').strip()

    if not user_account:
        user_account = User(
            teacher_id=teacher.id,
            username=teacher.cnic,
            role='TEACHER',
            full_name=teacher.full_name,
            email=teacher.email,
            is_active=True,
            is_first_login=True
        )
        db.add(user_account)

    user_account.set_password(new_password)
    user_account.is_first_login = True
    db.commit()
    log_audit(db, g.user, 'RESET_TEACHER_PASSWORD', entity_type='User', entity_id=user_account.id, details=f"Reset password for teacher {teacher.cnic}", ip_address=request.remote_addr)
    flash(f"Password reset for {teacher.full_name}. Credentials: Username '{teacher.cnic}', Password '{new_password}'.", "success")
    return redirect(url_for('admin.teacher_detail', teacher_id=teacher.id))

@admin_bp.route('/excel-import', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def excel_import():
    db = g.db
    preview_data = None
    mode = request.args.get('mode', request.form.get('mode', 'all'))
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'preview':
            if 'excel_file' not in request.files:
                flash("Please choose an Excel file to upload.", "danger")
                return render_template('admin/excel_import.html', preview_data=None, mode=mode)
            file = request.files['excel_file']
            if file.filename == '':
                flash("No file selected.", "danger")
                return render_template('admin/excel_import.html', preview_data=None, mode=mode)
            
            filename = secure_filename(file.filename)
            temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
            file.save(temp_path)
            
            preview_result = preview_excel_import(temp_path, db)
            if not preview_result.get('success'):
                flash(preview_result.get('error', 'Error reading Excel file.'), "danger")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return render_template('admin/excel_import.html', preview_data=None, mode=mode)

            preview_data = preview_result
            preview_data['file_path'] = temp_path
            return render_template('admin/excel_import.html', preview_data=preview_data, mode=mode)

        elif action == 'commit':
            file_path = request.form.get('file_path')
            update_existing = bool(request.form.get('update_existing'))
            if not file_path or not os.path.exists(file_path):
                flash("Upload session expired. Please select file again.", "danger")
                return render_template('admin/excel_import.html', preview_data=None, mode=mode)

            result = execute_excel_import(file_path, db, update_existing=update_existing, current_user=g.user, ip_address=request.remote_addr)
            if os.path.exists(file_path):
                os.remove(file_path)

            if result.get('success'):
                msgs = []
                if result.get('imported', 0) > 0 or result.get('updated', 0) > 0:
                    msgs.append(f"Teacher Records: Added {result['imported']} new teachers and updated {result['updated']} existing records.")
                if result.get('qualifications_imported', 0) > 0 or result.get('qualifications_updated', 0) > 0:
                    total_quals = result.get('qualifications_imported', 0) + result.get('qualifications_updated', 0)
                    teachers_affected = result.get('teachers_with_quals', 0)
                    msgs.append(f"Education & Qualifications: Successfully synchronized {total_quals} qualifications across {teachers_affected} teachers (Added: {result.get('qualifications_imported', 0)}, Updated: {result.get('qualifications_updated', 0)}).")
                if result.get('accounts_created', 0) > 0:
                    msgs.append(f"Created {result['accounts_created']} teacher login accounts (Username = CNIC, Default Password = Teacher@123).")
                
                if not msgs:
                    msgs.append("Spreadsheet processed successfully with zero changes.")

                flash(" | ".join(msgs), "success")
                return redirect(url_for('admin.teachers_list'))
            else:
                flash(f"Import failed: {result.get('error')}", "danger")

    return render_template('admin/excel_import.html', preview_data=preview_data, mode=mode)

@admin_bp.route('/excel-template')
@admin_bp.route('/download-template')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_template():
    db = g.db
    buffer = generate_excel_template(db)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Punjab_SED_Teacher_Import_Template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@admin_bp.route('/download-education-template')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_education_template():
    db = g.db
    buffer = generate_education_excel_template(db)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Punjab_SED_Bulk_Education_Update_Template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@admin_bp.route('/bulk-education-import', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def bulk_education_import():
    return redirect(url_for('admin.excel_import', mode='education'))

@admin_bp.route('/teachers/export')
@role_required(['ADMIN', 'SUPERADMIN'])
def export_teachers():
    db = g.db
    teachers = db.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.district, Teacher.current_designation).all()
    buffer = export_teachers_to_excel(teachers)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Punjab_Teachers_Directory_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@admin_bp.route('/seniority')
@role_required(['ADMIN', 'SUPERADMIN'])
def seniority_list():
    db = g.db
    district = request.args.get('district', 'Lahore')
    designation = request.args.get('designation', 'EST (Science)')
    
    # Auto-resolve basic scale from post or teacher records
    post_obj = db.query(TeachingPost).filter(TeachingPost.post_title == designation).first()
    if post_obj:
        bs = post_obj.basic_scale
    else:
        sample_t = db.query(Teacher.current_bs).filter(Teacher.current_designation == designation).first()
        bs = sample_t[0] if sample_t else int(request.args.get('bs', 15))

    teachers = db.query(Teacher).filter(
        Teacher.district == district,
        Teacher.current_designation == designation,
        Teacher.is_deleted == False
    ).order_by(Teacher.seniority_no.asc().nullslast(), Teacher.regularization_date.asc()).all()

    districts = [r[0] for r in db.query(Teacher.district).distinct().all() if r[0]]
    teacher_desigs = [r[0] for r in db.query(Teacher.current_designation).distinct().all() if r[0]]
    post_desigs = [p.post_title for p in db.query(TeachingPost).filter(TeachingPost.is_active == True).all()]
    all_desigs = sorted(list(set(teacher_desigs + post_desigs)))

    return render_template(
        'admin/seniority.html',
        teachers=teachers,
        districts=sorted(districts),
        designations=all_desigs,
        selected_district=district,
        selected_designation=designation,
        selected_bs=bs
    )

@admin_bp.route('/seniority/recompute', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def recompute_seniority():
    db = g.db
    district = request.form.get('district')
    designation = request.form.get('designation')
    
    post_obj = db.query(TeachingPost).filter(TeachingPost.post_title == designation).first()
    if post_obj:
        bs = post_obj.basic_scale
    else:
        sample_t = db.query(Teacher.current_bs).filter(Teacher.current_designation == designation).first()
        bs = sample_t[0] if sample_t else int(request.form.get('bs', 15))
    
    recompute_cadre_seniority(db, district, designation, bs, current_user=g.user)
    log_audit(db, g.user, 'RECOMPUTE_SENIORITY', entity_type='Seniority', details=f"Recomputed seniority list for {designation} (BS-{bs}) in {district}", ip_address=request.remote_addr)
    flash(f"Official Seniority rankings recomputed for {designation} (BS-{bs}) in district {district}.", "success")
    return redirect(url_for('admin.seniority_list', district=district, designation=designation, bs=bs))

@admin_bp.route('/seniority/pdf')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_seniority_pdf():
    db = g.db
    district = request.args.get('district', 'Lahore')
    designation = request.args.get('designation', 'EST (Science)')
    
    post_obj = db.query(TeachingPost).filter(TeachingPost.post_title == designation).first()
    if post_obj:
        bs = post_obj.basic_scale
    else:
        sample_t = db.query(Teacher.current_bs).filter(Teacher.current_designation == designation).first()
        bs = sample_t[0] if sample_t else int(request.args.get('bs', 15))
    
    teachers = db.query(Teacher).filter(
        Teacher.district == district,
        Teacher.current_designation == designation,
        Teacher.is_deleted == False
    ).order_by(Teacher.seniority_no.asc().nullslast()).all()
    
    buffer = generate_seniority_list_pdf(teachers, district, designation, bs)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Official_Seniority_List_{district}_{designation.replace(' ', '_')}.pdf",
        mimetype="application/pdf"
    )

@admin_bp.route('/verifications')
@role_required(['ADMIN', 'SUPERADMIN'])
def verifications():
    db = g.db
    pending_teachers = db.query(Teacher).filter(Teacher.verification_status == 'Pending', Teacher.is_deleted == False).all()
    pending_quals = db.query(Qualification).filter(Qualification.verification_status == 'Pending').all()
    return render_template('admin/verifications.html', pending_teachers=pending_teachers, pending_quals=pending_quals)

@admin_bp.route('/corrections')
@role_required(['ADMIN', 'SUPERADMIN'])
def corrections():
    db = g.db
    requests_list = db.query(CorrectionRequest).order_by(CorrectionRequest.created_at.desc()).all()
    return render_template('admin/corrections.html', requests_list=requests_list)

@admin_bp.route('/corrections/<int:req_id>/review', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def review_correction(req_id):
    db = g.db
    cr = get_or_404(CorrectionRequest, req_id)
    action = request.form.get('action') # 'Approve', 'Reject', 'More Info'
    remarks = request.form.get('admin_remarks', '').strip()

    cr.admin_remarks = remarks
    cr.reviewed_by = g.user.username
    cr.reviewed_at = datetime.utcnow()

    if action == 'Approve':
        cr.status = 'Approved'
        teacher = cr.teacher
        applied_msg = f"Correction claim #{cr.id} approved."

        # 1. Personal Information Correction
        if cr.record_type == 'PERSONAL' or not cr.record_type:
            attr = cr.target_attribute
            if not attr:
                f_name = cr.field_name.lower()
                if 'father' in f_name: attr = 'father_name'
                elif 'birth' in f_name or 'dob' in f_name: attr = 'date_of_birth'
                elif 'seniority' in f_name: attr = 'seniority_no'
                elif 'mobile' in f_name or 'phone' in f_name: attr = 'mobile'
                elif 'email' in f_name: attr = 'email'
                elif 'address' in f_name: attr = 'residential_address'
                elif 'emis' in f_name: attr = 'emis_code'
                elif 'school' in f_name: attr = 'school_name'
                elif 'joining' in f_name: attr = 'joining_date'
                elif 'regular' in f_name: attr = 'regularization_date'
                elif 'tehsil' in f_name: attr = 'tehsil'
                elif 'district' in f_name: attr = 'district'
                elif 'gender' in f_name: attr = 'gender'
                elif 'name' in f_name: attr = 'full_name'

            if attr and hasattr(teacher, attr):
                if attr in ('date_of_birth', 'joining_date', 'regularization_date'):
                    try:
                        setattr(teacher, attr, datetime.strptime(cr.requested_value, '%Y-%m-%d').date())
                    except Exception:
                        pass
                elif attr in ('seniority_no', 'current_bs', 'bps'):
                    try:
                        setattr(teacher, attr, int(cr.requested_value))
                    except Exception:
                        pass
                else:
                    setattr(teacher, attr, cr.requested_value)
                applied_msg += f" Teacher profile '{attr}' updated to '{cr.requested_value}'."

        # 2. Educational Qualification Correction
        elif cr.record_type == 'QUALIFICATION' and cr.record_id:
            qual = db.query(Qualification).get(cr.record_id)
            if qual:
                attr = cr.target_attribute
                if attr and hasattr(qual, attr):
                    if attr == 'passing_year':
                        try:
                            setattr(qual, attr, int(cr.requested_value))
                        except Exception:
                            pass
                    elif attr in ('marks_obtained', 'total_marks', 'percentage'):
                        try:
                            setattr(qual, attr, float(cr.requested_value))
                        except Exception:
                            pass
                    else:
                        setattr(qual, attr, cr.requested_value)

                    # Also update subject if major_subject updated
                    if attr == 'major_subject' and not qual.subject:
                        qual.subject = cr.requested_value

                    # Recalculate percentage if marks changed
                    if qual.marks_obtained is not None and qual.total_marks and qual.total_marks > 0:
                        qual.percentage = round((qual.marks_obtained / qual.total_marks) * 100, 2)

                    applied_msg += f" Qualification '{qual.degree_name}' ({attr}) updated to '{cr.requested_value}'."

        # 3. Service History Correction
        elif cr.record_type == 'SERVICE' and cr.record_id:
            svc = db.query(ServiceHistory).get(cr.record_id)
            if svc:
                attr = cr.target_attribute
                if attr and hasattr(svc, attr):
                    if attr in ('from_date', 'to_date', 'order_date'):
                        try:
                            setattr(svc, attr, datetime.strptime(cr.requested_value, '%Y-%m-%d').date())
                        except Exception:
                            pass
                    elif attr in ('bs', 'bps'):
                        try:
                            setattr(svc, attr, int(cr.requested_value))
                        except Exception:
                            pass
                    else:
                        setattr(svc, attr, cr.requested_value)

                    applied_msg += f" Service posting '{svc.designation}' ({attr}) updated to '{cr.requested_value}'."

        flash(applied_msg, "success")
    elif action == 'Reject':
        cr.status = 'Rejected'
        flash(f"Correction claim #{cr.id} for '{cr.field_name}' rejected.", "info")
    else:
        cr.status = 'More Info Required'
        flash(f"Correction claim #{cr.id} set to 'More Info Required'.", "warning")

    db.commit()
    log_audit(db, g.user, 'REVIEW_CORRECTION', entity_type='CorrectionRequest', entity_id=cr.id, details=f"Correction {action} for {cr.field_name} (Record Type: {cr.record_type})", ip_address=request.remote_addr)
    return redirect(url_for('admin.corrections'))

@admin_bp.route('/promotion-assessment', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def promotion_assessment():
    db = g.db
    assessment_result = None
    selected_teacher_id = request.args.get('teacher_id') or request.form.get('teacher_id')
    selected_rule_id = request.args.get('rule_id') or request.form.get('rule_id')
    as_of_date_str = request.form.get('as_of_date') or datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST' and selected_teacher_id and selected_rule_id:
        teacher = get_or_404(Teacher, int(selected_teacher_id))
        rule = get_or_404(PromotionRule, int(selected_rule_id))
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()

        assessment_result = evaluate_eligibility(teacher, rule, as_of_date=as_of_date, db_session=db)

        # Save record in assessment history if requested
        if request.form.get('save_record'):
            import json
            ass_rec = PromotionAssessment(
                teacher_id=teacher.id,
                rule_id=rule.id,
                date_as_of=as_of_date,
                target_designation=rule.target_designation,
                target_bs=rule.target_bs,
                promotion_category=rule.promotion_category,
                overall_status=assessment_result['overall_status'],
                service_check_status=assessment_result['conditions'][1]['status'],
                service_actual_years=assessment_result['service_actual_years'],
                service_required_years=assessment_result['service_required_years'],
                qualification_check_status=assessment_result['conditions'][2]['status'],
                professional_check_status=assessment_result['conditions'][3]['status'],
                seniority_check_status='Pass',
                inquiry_check_status=assessment_result['conditions'][5]['status'],
                acr_check_status=assessment_result['conditions'][6]['status'],
                details_json=json.dumps(assessment_result),
                assessed_by=g.user.username
            )
            db.add(ass_rec)
            db.commit()
            log_audit(db, g.user, 'SAVE_PROMOTION_ASSESSMENT', entity_type='PromotionAssessment', entity_id=ass_rec.id, details=f"Evaluated teacher {teacher.cnic} for {rule.target_designation}: {assessment_result['overall_status']}", ip_address=request.remote_addr)
            flash("Assessment saved to permanent official record.", "success")

    teachers = db.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.full_name).all()
    rules = db.query(PromotionRule).filter(PromotionRule.is_active == True).order_by(PromotionRule.source_bs, PromotionRule.target_bs).all()

    return render_template(
        'admin/promotion_assessment.html',
        teachers=teachers,
        rules=rules,
        assessment_result=assessment_result,
        selected_teacher_id=int(selected_teacher_id) if selected_teacher_id else None,
        selected_rule_id=int(selected_rule_id) if selected_rule_id else None,
        as_of_date_str=as_of_date_str
    )

@admin_bp.route('/promotion-lists')
@role_required(['ADMIN', 'SUPERADMIN'])
def promotion_lists():
    db = g.db
    rules = db.query(PromotionRule).filter(PromotionRule.is_active == True).order_by(PromotionRule.source_bs, PromotionRule.target_bs, PromotionRule.target_designation).all()
    if not rules:
        flash("No active promotion rules defined.", "warning")
        return redirect(url_for('admin.dashboard'))

    rule_id = request.args.get('rule_id')
    selected_rule = None
    if rule_id:
        try:
            selected_rule = db.query(PromotionRule).get(int(rule_id))
        except (ValueError, TypeError):
            selected_rule = None
    if not selected_rule and rules:
        selected_rule = rules[0]

    district = request.args.get('district', 'Lahore')
    status_filter = request.args.get('status', 'all') # 'all', 'eligible', 'promoted', 'rejected', 'pending'

    # Compute stats across the complete feeder candidate pool for this cadre and district
    all_candidates = evaluate_cadre_for_rule(
        db_session=db,
        rule=selected_rule,
        district=district,
        status_filter='all'
    )

    total_candidates = len(all_candidates)
    eligible_count = sum(1 for c in all_candidates if c.get('overall_status') == 'Eligible for Consideration')
    promoted_candidates_count = sum(1 for c in all_candidates if c.get('committee_decision') == 'Promoted')
    rejected_count = sum(1 for c in all_candidates if c.get('committee_decision') == 'Rejected' or c.get('overall_status') == 'Ineligible')
    panel_zone_count = sum(1 for c in all_candidates if 'Quota' in c.get('panel_zone_badge', '') or 'Panel' in c.get('panel_zone_badge', ''))
    pending_count = sum(1 for c in all_candidates if c.get('committee_decision') == 'Pending Review' and c.get('overall_status') == 'Eligible for Consideration')

    # Query currently promoted teachers for this target post and district
    active_tab = request.args.get('tab', 'assessment')
    if status_filter == 'promoted':
        active_tab = 'promoted'

    promoted_records = []
    seen_teacher_ids = set()

    # 1. Look up from PromotionAssessment records with committee_decision == 'Promoted'
    assessments = db.query(PromotionAssessment).join(Teacher).filter(
        PromotionAssessment.rule_id == selected_rule.id,
        PromotionAssessment.committee_decision == 'Promoted',
        Teacher.district == district,
        Teacher.is_deleted == False
    ).order_by(PromotionAssessment.decided_at.desc(), Teacher.seniority_no.asc()).all()

    for ass in assessments:
        t = ass.teacher
        if t.id in seen_teacher_ids:
            continue
        seen_teacher_ids.add(t.id)

        sh = db.query(ServiceHistory).filter(
            ServiceHistory.teacher_id == t.id,
            ServiceHistory.designation == selected_rule.target_designation,
            ServiceHistory.appointment_type == 'Promotion'
        ).order_by(ServiceHistory.id.desc()).first()

        academic_str = ', '.join([q.degree_name for q in t.qualifications if not q.professional_qualification]) or 'Prescribed Academic Degree'
        prof_str = ', '.join([q.degree_name for q in t.qualifications if q.professional_qualification]) or 'B.Ed / ADE Verified'

        promoted_records.append({
            'teacher': t,
            'assessment': ass,
            'service_history': sh,
            'target_designation': selected_rule.target_designation,
            'target_bs': selected_rule.target_bs,
            'feeder_designation': t.previous_designation or selected_rule.source_designation,
            'feeder_bs': t.previous_bs or selected_rule.source_bs,
            'feeder_seniority_no': t.previous_seniority_no,
            'promoted_seniority_no': t.seniority_no,
            'academic_degrees': academic_str,
            'prof_degrees': prof_str,
            'service_years': round((date.today() - (t.regularization_date or t.appointment_date)).days / 365.25, 1) if (t.regularization_date or t.appointment_date) else 0.0,
            'promotion_order_no': (sh.order_no if sh else None) or t.current_post_order_no or f"SED/PROMO/{selected_rule.rule_code}/{ass.id}",
            'promotion_order_date': (sh.order_date if sh else None) or t.current_post_order_date or (ass.decided_at.date() if ass.decided_at else date.today()),
            'effective_date': (sh.from_date if sh else None) or t.current_post_date or date.today(),
            'decided_by': ass.decided_by or 'DPC Authority',
            'decided_at': ass.decided_at,
            'decision_reason': ass.decision_reason or f"Approved for promotion to {selected_rule.target_designation} on Seniority-cum-Fitness basis.",
            'statutory_reference': ass.statutory_reference or f"SED Service Rules 2014, Schedule II for {selected_rule.target_designation}.",
            'remarks': (sh.remarks if sh else None) or f"Promoted from {t.previous_designation or selected_rule.source_designation} to {selected_rule.target_designation} on Seniority-cum-Fitness basis."
        })

    # 2. Check for teachers in district currently in target designation with previous designation or promo ServiceHistory
    extra_teachers = db.query(Teacher).filter(
        Teacher.district == district,
        Teacher.current_designation == selected_rule.target_designation,
        Teacher.current_bs == selected_rule.target_bs,
        Teacher.is_deleted == False
    ).all()

    for t in extra_teachers:
        if t.id in seen_teacher_ids:
            continue
        sh = db.query(ServiceHistory).filter(
            ServiceHistory.teacher_id == t.id,
            ServiceHistory.appointment_type == 'Promotion'
        ).order_by(ServiceHistory.id.desc()).first()

        if t.previous_designation or sh:
            seen_teacher_ids.add(t.id)
            academic_str = ', '.join([q.degree_name for q in t.qualifications if not q.professional_qualification]) or 'Prescribed Academic Degree'
            prof_str = ', '.join([q.degree_name for q in t.qualifications if q.professional_qualification]) or 'B.Ed / ADE Verified'

            promoted_records.append({
                'teacher': t,
                'assessment': None,
                'service_history': sh,
                'target_designation': t.current_designation,
                'target_bs': t.current_bs,
                'feeder_designation': t.previous_designation or selected_rule.source_designation,
                'feeder_bs': t.previous_bs or selected_rule.source_bs,
                'feeder_seniority_no': t.previous_seniority_no,
                'promoted_seniority_no': t.seniority_no,
                'academic_degrees': academic_str,
                'prof_degrees': prof_str,
                'service_years': round((date.today() - (t.regularization_date or t.appointment_date)).days / 365.25, 1) if (t.regularization_date or t.appointment_date) else 0.0,
                'promotion_order_no': (sh.order_no if sh else None) or t.current_post_order_no or f"SED/PROMO/{t.district.upper()}/{t.id}",
                'promotion_order_date': (sh.order_date if sh else None) or t.current_post_order_date or date.today(),
                'effective_date': (sh.from_date if sh else None) or t.current_post_date or date.today(),
                'decided_by': 'Departmental Promotion Committee (DPC)',
                'decided_at': None,
                'decision_reason': f"Regular promotion to {t.current_designation} (BS-{t.current_bs}) on Seniority-cum-Fitness basis under Service Rules 2014.",
                'statutory_reference': f"SED Service Rules 2014, Schedule II for {t.current_designation}.",
                'remarks': (sh.remarks if sh else None) or f"Promoted from {t.previous_designation} to {t.current_designation}."
            })

    promoted_count = len(promoted_records)

    # Display candidates based on the status filter
    if status_filter == 'all':
        candidates = all_candidates
    else:
        candidates = evaluate_cadre_for_rule(
            db_session=db,
            rule=selected_rule,
            district=district,
            status_filter=status_filter
        )

    # Fetch district vacancies for this post
    vacancy = db.query(Vacancy).filter(
        Vacancy.district == district,
        Vacancy.designation == selected_rule.target_designation
    ).first()
    if vacancy:
        vacancy.calculate_vacancies()

    # District list for filter
    districts = [d[0] for d in db.query(Teacher.district).distinct().all() if d[0]]
    if not districts:
        districts = ['Lahore', 'Kasur', 'Sheikhupura', 'Rawalpindi', 'Multan', 'Faisalabad']

    # Group rules hierarchically for dropdown and category selection suite
    cadre_groups = [
        {
            'key': 'PST_TO_EST',
            'label': 'Primary to Elementary (PST BS-14 → EST BS-15)',
            'short_label': 'PST → EST (BS-15)',
            'feeder': 'PST (BS-14)',
            'target_scale': 'BS-15',
            'rules': [r for r in rules if r.source_bs == 14 and r.target_bs == 15]
        },
        {
            'key': 'EST_TO_SST',
            'label': 'Elementary to Secondary (EST BS-15 → SST BS-16)',
            'short_label': 'EST → SST (BS-16)',
            'feeder': 'EST (BS-15)',
            'target_scale': 'BS-16',
            'rules': [r for r in rules if r.source_bs == 15 and r.target_bs == 16]
        },
        {
            'key': 'SST_TO_BS17',
            'label': 'Secondary to Administration & Specialist (SST BS-16 → BS-17)',
            'short_label': 'SST → BS-17',
            'feeder': 'SST (BS-16)',
            'target_scale': 'BS-17',
            'rules': [r for r in rules if r.source_bs == 16 and r.target_bs == 17]
        },
        {
            'key': 'BS17_TO_BS18',
            'label': 'Senior Scale Promotions (BS-17 → BS-18)',
            'short_label': 'BS-17 → BS-18',
            'feeder': 'BS-17',
            'target_scale': 'BS-18',
            'rules': [r for r in rules if r.source_bs == 17 and r.target_bs == 18]
        }
    ]

    other_rules = [r for r in rules if not (
        (r.source_bs == 14 and r.target_bs == 15) or
        (r.source_bs == 15 and r.target_bs == 16) or
        (r.source_bs == 16 and r.target_bs == 17) or
        (r.source_bs == 17 and r.target_bs == 18)
    )]
    if other_rules:
        cadre_groups.append({
            'key': 'OTHER',
            'label': 'Other Promotional Channels',
            'short_label': 'Other Channels',
            'feeder': 'Various',
            'target_scale': 'Various',
            'rules': other_rules
        })

    active_cadre_key = 'PST_TO_EST'
    for grp in cadre_groups:
        if any(r.id == selected_rule.id for r in grp['rules']):
            active_cadre_key = grp['key']
            break

    # Statutory Pre-Flight Checklist
    chk_posts = db.query(TeachingPost).filter(TeachingPost.is_active == True).count() > 0
    chk_rule = (selected_rule is not None and selected_rule.is_active)
    chk_vacancy = (vacancy is not None and (vacancy.sanctioned_posts or 0) > 0)
    chk_quota = (selected_rule is not None and (selected_rule.promotion_quota_percent or 0) > 0)
    chk_imported = (total_candidates > 0)
    
    unverified_candidates_count = sum(1 for c in all_candidates if c.get('teacher') and c.get('teacher').verification_status != 'Verified')
    chk_verification = (unverified_candidates_count == 0)

    retiring_candidates_count = sum(1 for c in all_candidates if c.get('is_superannuated'))
    chk_retirement = (retiring_candidates_count == 0)

    cand_ids = [c['teacher'].id for c in all_candidates if c.get('teacher')]
    pending_corrections_cand = db.query(CorrectionRequest).filter(
        CorrectionRequest.teacher_id.in_(cand_ids),
        CorrectionRequest.status == 'Pending'
    ).count() if cand_ids else 0
    chk_corrections = (pending_corrections_cand == 0)

    upcoming_meeting = db.query(DpcMeeting).filter(
        DpcMeeting.meeting_date >= date.today()
    ).first()
    chk_dpc_meeting = (upcoming_meeting is not None)

    preflight_checklist = [
        {'name': 'Teaching posts configured', 'passed': chk_posts, 'fix_url': url_for('admin.teaching_posts'), 'fix_text': 'Configure Posts'},
        {'name': 'Promotion rule configured', 'passed': chk_rule, 'fix_url': url_for('superadmin.manage_rules'), 'fix_text': 'Configure Rule'},
        {'name': f'Vacancies entered for {selected_rule.target_designation}', 'passed': chk_vacancy, 'fix_url': url_for('admin.vacancies'), 'fix_text': 'Fix Vacancies'},
        {'name': f'Promotion quota configured ({selected_rule.promotion_quota_percent}%)', 'passed': chk_quota, 'fix_url': url_for('admin.vacancies'), 'fix_text': 'Set Quota'},
        {'name': 'Teacher data imported', 'passed': chk_imported, 'fix_url': url_for('admin.excel_import'), 'fix_text': 'Import Data'},
        {'name': f'Teacher verification completed ({unverified_candidates_count} pending)', 'passed': chk_verification, 'fix_url': url_for('admin.verifications'), 'fix_text': 'Review Verifications'},
        {'name': f'Retirement review completed ({retiring_candidates_count} over 60)', 'passed': chk_retirement, 'fix_url': url_for('admin.retirements_review'), 'fix_text': 'Review Retirements'},
        {'name': f'Pending corrections reviewed ({pending_corrections_cand} pending)', 'passed': chk_corrections, 'fix_url': url_for('admin.corrections'), 'fix_text': 'Review Corrections'},
        {'name': 'DPC meeting created / scheduled', 'passed': chk_dpc_meeting, 'fix_url': url_for('admin.dpc_schedule'), 'fix_text': 'Create DPC'}
    ]
    all_preflight_passed = all(item['passed'] for item in preflight_checklist)

    return render_template(
        'admin/promotion_lists.html',
        rules=rules,
        selected_rule=selected_rule,
        cadre_groups=cadre_groups,
        active_cadre_key=active_cadre_key,
        district=district,
        districts=sorted(districts),
        status_filter=status_filter,
        candidates=candidates,
        vacancy=vacancy,
        total_candidates=total_candidates,
        eligible_count=eligible_count,
        promoted_count=promoted_count,
        rejected_count=rejected_count,
        panel_zone_count=panel_zone_count,
        pending_count=pending_count,
        promoted_records=promoted_records,
        active_tab=active_tab,
        preflight_checklist=preflight_checklist,
        all_preflight_passed=all_preflight_passed
    )

@admin_bp.route('/promotion-lists/<int:rule_id>/decide', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def decide_promotion_candidate(rule_id):
    db = g.db
    rule = get_or_404(PromotionRule, rule_id)
    teacher_id = int(request.form.get('teacher_id'))
    teacher = get_or_404(Teacher, teacher_id)
    
    action = request.form.get('action') # 'Promote', 'Reject', 'Defer', 'Reset'
    custom_reason = request.form.get('decision_reason', '').strip()
    statutory_ref = request.form.get('statutory_reference', '').strip()

    decision_map = {
        'Promote': 'Promoted',
        'Reject': 'Rejected',
        'Defer': 'Deferred',
        'Reset': 'Pending Review'
    }
    committee_decision = decision_map.get(action, 'Pending Review')

    # Find or create assessment
    ass = db.query(PromotionAssessment).filter(
        PromotionAssessment.teacher_id == teacher.id,
        PromotionAssessment.rule_id == rule.id
    ).order_by(PromotionAssessment.id.desc()).first()

    eval_res = evaluate_eligibility(teacher, rule, db_session=db)
    final_reason = custom_reason or eval_res['default_reason']
    final_ref = statutory_ref or eval_res['statutory_reference']

    if not ass:
        import json
        ass = PromotionAssessment(
            teacher_id=teacher.id,
            rule_id=rule.id,
            date_as_of=date.today(),
            target_designation=rule.target_designation,
            target_bs=rule.target_bs,
            promotion_category=rule.promotion_category,
            overall_status=eval_res['overall_status'],
            service_check_status=eval_res['conditions'][1]['status'],
            service_actual_years=eval_res['service_actual_years'],
            service_required_years=eval_res['service_required_years'],
            qualification_check_status=eval_res['conditions'][2]['status'],
            professional_check_status=eval_res['conditions'][3]['status'],
            seniority_check_status='Pass',
            inquiry_check_status=eval_res['conditions'][5]['status'],
            acr_check_status=eval_res['conditions'][6]['status'],
            details_json=json.dumps(eval_res),
            assessed_by=g.user.username
        )
        db.add(ass)

    ass.committee_decision = committee_decision
    ass.decision_reason = final_reason
    ass.statutory_reference = final_ref
    ass.decided_by = g.user.username
    ass.decided_at = datetime.utcnow()

    # If action is 'Promote', promote teacher to target post and append their seniority number
    if action == 'Promote':
        # 1. Capture feeder cadre and seniority particulars prior to promotion transition
        feeder_desig = teacher.current_designation
        feeder_bs = teacher.current_bs
        feeder_category = teacher.current_category
        feeder_seniority_no = teacher.seniority_no
        feeder_seniority_date = teacher.seniority_date or teacher.current_post_date or teacher.regularization_date or date.today()
        previous_desig = f"{feeder_desig} (BS-{feeder_bs})"

        # Ensure feeder cadre seniority record exists in SeniorityRecord table
        feeder_sen_rec = db.query(SeniorityRecord).filter(
            SeniorityRecord.teacher_id == teacher.id,
            SeniorityRecord.designation == feeder_desig,
            SeniorityRecord.bs == feeder_bs
        ).first()

        if not feeder_sen_rec and feeder_seniority_no:
            feeder_sen_rec = SeniorityRecord(
                teacher_id=teacher.id,
                seniority_no=feeder_seniority_no,
                seniority_date=feeder_seniority_date,
                designation=feeder_desig,
                bs=feeder_bs,
                category=feeder_category,
                district=teacher.district,
                seniority_list_reference=f"SED/{teacher.district.upper()}/FEEDER-SENIORITY",
                seniority_list_date=feeder_seniority_date,
                is_official=True,
                verified=True,
                verified_by=g.user.username,
                verified_at=datetime.utcnow(),
                remarks=f"Feeder cadre seniority rank #{feeder_seniority_no} held in {feeder_desig} prior to DPC promotion."
            )
            db.add(feeder_sen_rec)
        elif feeder_sen_rec and "Feeder" not in (feeder_sen_rec.remarks or ''):
            feeder_sen_rec.remarks = f"Feeder cadre seniority rank #{feeder_sen_rec.seniority_no} in {feeder_desig} prior to promotion to {rule.target_designation}."

        # 2. Determine highest existing seniority number in the target cadre & district (Assign at Max + 1 increment)
        max_t_sen = db.query(func.max(Teacher.seniority_no)).filter(
            Teacher.district == teacher.district,
            Teacher.current_designation == rule.target_designation,
            Teacher.current_bs == rule.target_bs,
            Teacher.is_deleted == False
        ).scalar() or 0

        max_rec_sen = db.query(func.max(SeniorityRecord.seniority_no)).filter(
            SeniorityRecord.district == teacher.district,
            SeniorityRecord.designation == rule.target_designation,
            SeniorityRecord.bs == rule.target_bs
        ).scalar() or 0

        new_seniority_no = max(max_t_sen, max_rec_sen) + 1

        # 3. Conclude previous active ServiceHistory record
        prev_history = db.query(ServiceHistory).filter(
            ServiceHistory.teacher_id == teacher.id,
            ServiceHistory.is_current_post == True
        ).first()
        if prev_history:
            prev_history.is_current_post = False
            prev_history.to_date = date.today()

        # 4. Create new ServiceHistory record for promotional appointment
        promo_order = f"SED/PROMO/{rule.rule_code}/{datetime.now().strftime('%Y%m%d%H%M')}"
        new_history = ServiceHistory(
            teacher_id=teacher.id,
            designation=rule.target_designation,
            bs=rule.target_bs,
            school_name=teacher.school_name,
            district=teacher.district,
            tehsil=teacher.tehsil,
            from_date=date.today(),
            is_current_post=True,
            appointment_type='Promotion',
            order_no=promo_order,
            order_date=date.today(),
            remarks=f"Regular Promotion from {previous_desig} to {rule.target_designation} (BS-{rule.target_bs}) on Seniority-cum-Fitness basis.",
            verification_status='Verified',
            verified_by=g.user.username,
            verified_at=datetime.utcnow()
        )
        db.add(new_history)

        # 5. Create new SeniorityRecord in target cadre (placed at cadre maximum + 1 increment)
        new_sen_rec = SeniorityRecord(
            teacher_id=teacher.id,
            seniority_no=new_seniority_no,
            seniority_date=date.today(),
            designation=rule.target_designation,
            bs=rule.target_bs,
            category=rule.promotion_category,
            district=teacher.district,
            seniority_list_reference=f"DPC/SED/{teacher.district.upper()}/{datetime.now().year}",
            seniority_list_date=date.today(),
            is_official=True,
            verified=True,
            verified_by=g.user.username,
            verified_at=datetime.utcnow(),
            remarks=f"Appended Seniority No. #{new_seniority_no} (Assigned at Cadre Maximum + 1 upon regular DPC promotion from {previous_desig})."
        )
        db.add(new_sen_rec)

        # 6. Update Teacher record with both previous feeder seniority and new promoted seniority
        teacher.previous_designation = feeder_desig
        teacher.previous_bs = feeder_bs
        teacher.previous_seniority_no = feeder_seniority_no

        teacher.current_designation = rule.target_designation
        teacher.current_bs = rule.target_bs
        teacher.current_category = rule.promotion_category
        teacher.current_post_date = date.today()
        teacher.seniority_no = new_seniority_no
        teacher.seniority_date = date.today()
        teacher.current_post_order_no = promo_order
        teacher.current_post_order_date = date.today()

        db.commit()

        log_audit(
            db, g.user, "PROMOTION_CONFIRMED",
            entity_type='Teacher', entity_id=teacher.id,
            details=f"Promoted {teacher.full_name} ({teacher.cnic}) to {rule.target_designation} (BS-{rule.target_bs}). Assigned appended Seniority #{new_seniority_no}.",
            ip_address=request.remote_addr
        )
        flash(
            f"Promotion Confirmed! {teacher.full_name} promoted to {rule.target_designation} (BS-{rule.target_bs}). "
            f"New Seniority No. #{new_seniority_no} has been appended to the existing {teacher.district} seniority roll.",
            "success"
        )
    else:
        db.commit()
        log_audit(
            db, g.user, f"PROMOTION_{committee_decision.upper()}",
            entity_type='PromotionAssessment', entity_id=ass.id,
            details=f"DPC {committee_decision} teacher {teacher.cnic} for {rule.target_designation}. Reason: {final_reason[:60]}...",
            ip_address=request.remote_addr
        )
        flash(f"Candidate {teacher.full_name} marked as '{committee_decision}' for {rule.target_designation}.", "success")

    return redirect(url_for('admin.promotion_lists', rule_id=rule.id, district=request.form.get('district', teacher.district), status=request.form.get('status_filter', 'all')))

@admin_bp.route('/promotion-lists/<int:rule_id>/pdf')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_promotion_list_pdf(rule_id):
    db = g.db
    rule = get_or_404(PromotionRule, rule_id)
    district = request.args.get('district', 'Lahore')
    status_filter = request.args.get('status', 'all')

    candidates = evaluate_cadre_for_rule(
        db_session=db,
        rule=rule,
        district=district,
        status_filter=status_filter
    )

    buffer = generate_promotion_list_pdf(candidates, rule, district=district)
    file_name = f"Promotion_Roll_{rule.target_designation.replace(' ', '_')}_{district}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=file_name,
        mimetype="application/pdf"
    )

@admin_bp.route('/promotion-lists/<int:rule_id>/excel')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_promotion_list_excel(rule_id):
    db = g.db
    rule = get_or_404(PromotionRule, rule_id)
    district = request.args.get('district', 'Lahore')
    status_filter = request.args.get('status', 'all')

    candidates = evaluate_cadre_for_rule(
        db_session=db,
        rule=rule,
        district=district,
        status_filter=status_filter
    )

    buffer = export_promotion_list_to_excel(candidates, rule, district=district)
    file_name = f"Promotion_Roll_{rule.target_designation.replace(' ', '_')}_{district}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=file_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ==============================================================================
# OFFICIAL PROMOTION SCRUTINY RUNS & FROZEN ROLLS (DRAFT -> FINALIZED -> LOCKED)
# ==============================================================================
@admin_bp.route('/promotion-runs', methods=['GET'])
@role_required(['ADMIN', 'SUPERADMIN'])
def promotion_runs():
    db = g.db
    district_filter = request.args.get('district', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = db.query(PromotionRun)
    if district_filter:
        query = query.filter(PromotionRun.district == district_filter)
    if status_filter:
        query = query.filter(PromotionRun.status == status_filter)

    runs = query.order_by(PromotionRun.run_date.desc(), PromotionRun.id.desc()).all()
    districts = [r[0] for r in db.query(Teacher.district).distinct().all() if r[0]]

    return render_template(
        'admin/promotion_runs.html',
        runs=runs,
        districts=sorted(districts),
        district_filter=district_filter,
        status_filter=status_filter
    )


@admin_bp.route('/promotion-runs/create', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def create_promotion_run():
    import json
    db = g.db
    rule_id = request.form.get('rule_id', type=int)
    district = request.form.get('district', 'Lahore').strip()
    cutoff_date_str = request.form.get('cutoff_date', '').strip()
    notes = request.form.get('notes', '').strip()

    rule = get_or_404(PromotionRule, rule_id)
    cutoff_date = date.today()
    if cutoff_date_str:
        try:
            cutoff_date = datetime.strptime(cutoff_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Gather vacancy & quota metrics
    vac = db.query(Vacancy).filter(
        Vacancy.district == district,
        Vacancy.designation == rule.target_designation
    ).first()
    if vac:
        vac.calculate_vacancies()
        s_posts = vac.sanctioned_posts or 0
        w_strength = vac.working_strength or 0
        v_posts = vac.vacant_posts or 0
        q_pct = vac.promotion_quota_percent or rule.promotion_quota_percent or 50.0
        q_posts = vac.promotion_quota_posts or 0
    else:
        s_posts = 0
        w_strength = 0
        v_posts = 0
        q_pct = rule.promotion_quota_percent or 50.0
        q_posts = 0

    # Evaluate all candidates per rule
    all_candidates = evaluate_cadre_for_rule(
        db_session=db,
        rule=rule,
        district=district,
        status_filter='all'
    )

    total_candidates = len(all_candidates)
    eligible_count = sum(1 for c in all_candidates if c.get('overall_status') == 'Eligible for Consideration')
    ineligible_count = sum(1 for c in all_candidates if c.get('overall_status') == 'Ineligible')
    zone1_count = sum(1 for c in all_candidates if 'Quota' in c.get('panel_zone_badge', '') or 'Panel' in c.get('panel_zone_badge', ''))

    # Generate sequential Run Number: RUN-YYYY-XXX
    current_year = date.today().year
    year_prefix = f"RUN-{current_year}-"
    last_run = db.query(PromotionRun).filter(PromotionRun.run_no.like(f"{year_prefix}%")).order_by(PromotionRun.id.desc()).first()
    if last_run and last_run.run_no.startswith(year_prefix):
        try:
            last_seq = int(last_run.run_no.split('-')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = db.query(PromotionRun).count() + 1
    else:
        new_seq = 1
    run_no = f"{year_prefix}{new_seq:03d}"

    # Serialize candidate snapshot for immutable official freeze
    snapshot_items = []
    for c in all_candidates:
        t = c.get('teacher')
        snapshot_items.append({
            'teacher_id': t.id if t else None,
            'full_name': t.full_name if t else 'Unknown',
            'cnic': t.cnic if t else '',
            'personnel_no': t.personnel_no if t else '',
            'school_name': t.school_name if t else '',
            'feeder_designation': t.current_designation if t else rule.source_designation,
            'feeder_bs': t.current_bs if t else rule.source_bs,
            'seniority_no': t.seniority_no if t else None,
            'service_years': c.get('service_actual_years', 0),
            'academic_degrees': c.get('academic_degrees', ''),
            'prof_degrees': c.get('prof_degrees', ''),
            'overall_status': c.get('overall_status', ''),
            'committee_decision': c.get('committee_decision', 'Pending Review'),
            'panel_zone_badge': c.get('panel_zone_badge', ''),
            'remarks': c.get('remarks', '')
        })

    snapshot_data = {
        'run_no': run_no,
        'rule_code': rule.rule_code,
        'rule_name': rule.rule_name,
        'source_designation': rule.source_designation,
        'source_bs': rule.source_bs,
        'target_designation': rule.target_designation,
        'target_bs': rule.target_bs,
        'district': district,
        'cutoff_date': cutoff_date.strftime('%Y-%m-%d'),
        'run_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'sanctioned_posts': s_posts,
        'working_strength': w_strength,
        'vacant_posts': v_posts,
        'quota_percent': q_pct,
        'quota_posts': q_posts,
        'candidates': snapshot_items
    }

    new_run = PromotionRun(
        run_no=run_no,
        rule_id=rule.id,
        district=district,
        target_designation=rule.target_designation,
        target_bs=rule.target_bs,
        cutoff_date=cutoff_date,
        run_date=datetime.utcnow(),
        sanctioned_posts=s_posts,
        working_strength=w_strength,
        vacant_posts=v_posts,
        quota_percent=q_pct,
        quota_posts=q_posts,
        total_candidates=total_candidates,
        eligible_count=eligible_count,
        ineligible_count=ineligible_count,
        zone1_count=zone1_count,
        status='Draft',
        snapshot_json=json.dumps(snapshot_data),
        notes=notes,
        created_by=g.user.username
    )
    db.add(new_run)
    db.commit()

    log_audit(
        db, g.user, 'CREATE_PROMOTION_RUN',
        entity_type='PromotionRun', entity_id=new_run.id,
        details=f"Created Promotion Run #{run_no} for {rule.target_designation} in {district} (Candidates: {total_candidates}, Eligible: {eligible_count})",
        ip_address=request.remote_addr
    )

    flash(f"Official Promotion Run #{run_no} created successfully in Draft status.", "success")
    return redirect(url_for('admin.promotion_run_detail', run_id=new_run.id))


@admin_bp.route('/promotion-runs/<int:run_id>')
@role_required(['ADMIN', 'SUPERADMIN'])
def promotion_run_detail(run_id):
    import json
    db = g.db
    run = get_or_404(PromotionRun, run_id)
    snapshot = json.loads(run.snapshot_json) if run.snapshot_json else {}

    return render_template(
        'admin/promotion_run_detail.html',
        run=run,
        snapshot=snapshot
    )


@admin_bp.route('/promotion-runs/<int:run_id>/status', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def update_promotion_run_status(run_id):
    db = g.db
    run = get_or_404(PromotionRun, run_id)
    new_status = request.form.get('status', '').strip()
    reason = request.form.get('reason', '').strip()

    if new_status not in ['Draft', 'Finalized', 'Locked', 'Reopened']:
        flash("Invalid promotion roll status requested.", "danger")
        return redirect(url_for('admin.promotion_run_detail', run_id=run.id))

    old_status = run.status

    if new_status == 'Finalized':
        run.status = 'Finalized'
        flash(f"Promotion Roll #{run.run_no} has been Finalized for DPC consideration.", "info")
    elif new_status == 'Locked':
        run.status = 'Locked'
        run.locked_at = datetime.utcnow()
        run.locked_by = g.user.username
        flash(f"Promotion Roll #{run.run_no} is now 🔒 LOCKED. Official proceedings sealed.", "success")
    elif new_status == 'Reopened':
        if not reason:
            flash("A mandatory justification reason is required to unlock or reopen an official roll.", "danger")
            return redirect(url_for('admin.promotion_run_detail', run_id=run.id))
        run.status = 'Draft'
        run.reopen_reason = reason
        run.reopened_at = datetime.utcnow()
        run.reopened_by = g.user.username
        flash(f"Promotion Roll #{run.run_no} has been reopened with justification: '{reason}'.", "warning")

    db.commit()

    log_audit(
        db, g.user, 'UPDATE_PROMOTION_RUN_STATUS',
        entity_type='PromotionRun', entity_id=run.id,
        details=f"Promotion Run #{run.run_no} transitioned from {old_status} to {run.status}. Reason: {reason or 'Administrative workflow'}",
        ip_address=request.remote_addr
    )

    return redirect(url_for('admin.promotion_run_detail', run_id=run.id))


@admin_bp.route('/promotion-runs/<int:run_id>/pdf')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_promotion_run_pdf(run_id):
    db = g.db
    run = get_or_404(PromotionRun, run_id)
    rule = run.rule or db.query(PromotionRule).get(run.rule_id)
    candidates = evaluate_cadre_for_rule(
        db_session=db,
        rule=rule,
        district=run.district,
        status_filter='all'
    )
    buffer = generate_promotion_list_pdf(candidates, rule, district=run.district)
    file_name = f"Official_Promotion_Roll_{run.run_no}_{run.district}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=file_name,
        mimetype="application/pdf"
    )


@admin_bp.route('/vacancies', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def vacancies():
    db = g.db
    if request.method == 'POST':
        vac_id = request.form.get('vac_id')
        dist = request.form.get('district', '').strip()
        teh = request.form.get('tehsil', '').strip()
        desig = request.form.get('designation', '').strip()
        bs = int(request.form.get('bs', 15))
        sanc = int(request.form.get('sanctioned_posts', 0))
        filled = int(request.form.get('filled_posts', 0))
        quota_pct = float(request.form.get('promotion_quota_percent', 50.0))

        if vac_id:
            vac = db.query(Vacancy).get(int(vac_id))
            if vac:
                vac.district = dist
                vac.tehsil = teh
                vac.designation = desig
                vac.bs = bs
                vac.sanctioned_posts = sanc
                vac.filled_posts = filled
                vac.promotion_quota_percent = quota_pct
                vac.calculate_vacancies()
                db.commit()
                log_audit(db, g.user, 'UPDATE_VACANCY', entity_type='Vacancy', entity_id=vac.id, details=f"Updated vacancy record #{vac.id} for {desig} in {dist}", ip_address=request.remote_addr)
                flash(f"Vacancy record for '{desig}' ({dist}) updated successfully.", "success")
                return redirect(url_for('admin.vacancies'))

        vac = db.query(Vacancy).filter(Vacancy.district == dist, Vacancy.designation == desig).first()
        if not vac:
            vac = Vacancy(district=dist, tehsil=teh, designation=desig, bs=bs)
            db.add(vac)

        vac.tehsil = teh
        vac.bs = bs
        vac.sanctioned_posts = sanc
        vac.filled_posts = filled
        vac.promotion_quota_percent = quota_pct
        vac.calculate_vacancies()
        db.commit()
        log_audit(db, g.user, 'UPDATE_VACANCIES', entity_type='Vacancy', details=f"Configured vacancies for {desig} in {dist}", ip_address=request.remote_addr)
        flash(f"Vacancy record for '{desig}' ({dist}) saved successfully.", "success")
        return redirect(url_for('admin.vacancies'))

    vac_list = db.query(Vacancy).order_by(Vacancy.district, Vacancy.designation).all()
    return render_template('admin/vacancies.html', vacancies=vac_list)

@admin_bp.route('/vacancies/<int:vac_id>/delete', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def delete_vacancy(vac_id):
    db = g.db
    vac = db.query(Vacancy).get(vac_id)
    if not vac:
        flash("Vacancy record not found.", "danger")
        return redirect(url_for('admin.vacancies'))

    desig = vac.designation
    dist = vac.district
    db.delete(vac)
    db.commit()
    log_audit(db, g.user, 'DELETE_VACANCY', entity_type='Vacancy', entity_id=vac_id, details=f"Deleted vacancy record for {desig} in {dist}", ip_address=request.remote_addr)
    flash(f"Vacancy record for '{desig}' in {dist} has been removed.", "success")
    return redirect(url_for('admin.vacancies'))

@admin_bp.route('/reports')
@role_required(['ADMIN', 'SUPERADMIN'])
def reports():
    db = g.db
    districts = [r[0] for r in db.query(Teacher.district).distinct().all() if r[0]]
    teacher_desigs = [r[0] for r in db.query(Teacher.current_designation).distinct().all() if r[0]]
    post_desigs = [p.post_title for p in db.query(TeachingPost).filter(TeachingPost.is_active == True).all()]
    all_desigs = sorted(list(set(teacher_desigs + post_desigs)))
    return render_template('admin/reports.html', districts=sorted(districts), designations=all_desigs)

@admin_bp.route('/teachers/<int:teacher_id>/dossier-pdf')
@role_required(['ADMIN', 'SUPERADMIN', 'TEACHER'])
def teacher_dossier_pdf(teacher_id):
    db = g.db
    teacher = get_or_404(Teacher, teacher_id)
    # Check if teacher is viewing own profile or is admin
    if g.user.role == 'TEACHER' and g.user.teacher_id != teacher.id:
        flash("You can only download your own official dossier.", "danger")
        return redirect(url_for('teacher.dashboard'))

    buffer = generate_teacher_dossier_pdf(teacher)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Teacher_Dossier_{teacher.personnel_no}_{teacher.cnic}.pdf",
        mimetype="application/pdf"
    )

@admin_bp.route('/teaching-posts', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def teaching_posts():
    db = g.db
    if request.method == 'POST':
        post_code = request.form.get('post_code', '').strip().upper()
        post_title = request.form.get('post_title', '').strip()
        cadre = request.form.get('cadre', '').strip()
        basic_scale = request.form.get('basic_scale', type=int)
        category = request.form.get('category', '').strip()
        gender = request.form.get('gender', 'Both').strip()
        feeder_post_title = request.form.get('feeder_post_title', '').strip() or None
        min_service_years = request.form.get('min_service_years', 0, type=int)
        prescribed_qualification = request.form.get('prescribed_qualification', '').strip() or None

        if not post_code or not post_title or not cadre or not basic_scale or not category:
            flash("All mandatory fields (Post Code, Title, Cadre, Basic Scale, Category) are required.", "danger")
            return redirect(url_for('admin.teaching_posts'))

        existing = db.query(TeachingPost).filter(TeachingPost.post_code == post_code).first()
        if existing:
            flash(f"Post with code '{post_code}' already exists. Please choose a unique post code.", "danger")
            return redirect(url_for('admin.teaching_posts'))

        new_post = TeachingPost(
            post_code=post_code,
            post_title=post_title,
            cadre=cadre,
            basic_scale=basic_scale,
            category=category,
            gender=gender,
            feeder_post_title=feeder_post_title,
            min_service_years=min_service_years,
            prescribed_qualification=prescribed_qualification,
            is_active=True,
            is_custom=True
        )
        db.add(new_post)
        db.commit()
        log_audit(db, g.user, 'CREATE_TEACHING_POST', entity_type='TeachingPost', entity_id=new_post.id, details=f"Created custom teaching post {post_title} (BS-{basic_scale})", ip_address=request.remote_addr)
        flash(f"Teaching Post '{post_title}' added successfully.", "success")
        return redirect(url_for('admin.teaching_posts'))

    # GET filter handling
    cadre_filter = request.args.get('cadre', '').strip()
    bs_filter = request.args.get('bs', type=int)
    status_filter = request.args.get('status', 'all').strip()
    search_query = request.args.get('q', '').strip()

    query = db.query(TeachingPost)
    if cadre_filter:
        query = query.filter(TeachingPost.cadre == cadre_filter)
    if bs_filter:
        query = query.filter(TeachingPost.basic_scale == bs_filter)
    if status_filter == 'active':
        query = query.filter(TeachingPost.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(TeachingPost.is_active == False)
    if search_query:
        query = query.filter(
            (TeachingPost.post_title.ilike(f'%{search_query}%')) |
            (TeachingPost.post_code.ilike(f'%{search_query}%')) |
            (TeachingPost.category.ilike(f'%{search_query}%'))
        )

    posts = query.order_by(TeachingPost.basic_scale.asc(), TeachingPost.display_order.asc(), TeachingPost.post_title.asc()).all()

    # Predefined lists from DB and Service Rules for datalists & quick presets
    cadres_db = [r[0] for r in db.query(TeachingPost.cadre).distinct().all() if r[0]]
    standard_cadres = ['Primary Cadre', 'Elementary Cadre', 'Secondary Cadre', 'Higher Secondary Cadre', 'Administrative Cadre', 'Educator Cadre']
    all_cadres = sorted(list(set(cadres_db + standard_cadres)))

    categories_db = [r[0] for r in db.query(TeachingPost.category).distinct().all() if r[0]]
    standard_categories = [
        'Science', 'Arts', 'English', 'Mathematics', 'Computer Science', 'Physics', 'Chemistry',
        'Biology', 'Biology & Chemistry', 'Mathematics & Physics', 'Drawing', 'Physical Education',
        'Arabic', 'Urdu', 'Commerce', 'Agriculture', 'Home Economics', 'Technical', 'Religious Education',
        'Oriental Languages', 'Pakistan Studies', 'Economics', 'Education', 'Social Studies', 'Statistics',
        'Administration', 'Educational Administration', 'District Administration', 'Executive Leadership',
        'Senior Leadership', 'Specialized Teaching', 'General / Administration'
    ]
    all_categories = sorted(list(set(categories_db + standard_categories)))

    all_post_titles = sorted(list(set([r[0] for r in db.query(TeachingPost.post_title).distinct().all() if r[0]])))

    feeder_db = [r[0] for r in db.query(TeachingPost.feeder_post_title).distinct().all() if r[0]]
    standard_feeders = [
        'Primary School Teacher (PST)', 'Elementary School Teacher (EST)', 'Secondary School Teacher (SST)',
        'Headmaster / Headmistress (BS-17)', 'Headmaster (BS-17) / AEO', 'Subject Specialist (SS BS-17)',
        'Senior Subject Specialist / Senior Headmaster', 'Senior Headmaster / Dy. DEO / SSS (BS-18)',
        'Principal / DEO (BS-19)', 'DEO / Principal (BS-19)', 'None (Initial Direct Recruitment)'
    ]
    all_feeder_posts = sorted(list(set(feeder_db + standard_feeders)))

    all_qualifications = sorted(list(set([r[0] for r in db.query(TeachingPost.prescribed_qualification).distinct().all() if r[0]])))

    # Complete predefined post catalog objects for instant JS auto-fill
    active_posts_all = db.query(TeachingPost).filter(TeachingPost.is_active == True).order_by(TeachingPost.basic_scale.asc(), TeachingPost.post_title.asc()).all()
    predefined_catalog = [
        {
            'title': p.post_title,
            'code': p.post_code,
            'scale': p.basic_scale,
            'cadre': p.cadre,
            'category': p.category,
            'gender': p.gender,
            'feeder': p.feeder_post_title or '',
            'service': p.min_service_years,
            'qualification': p.prescribed_qualification or ''
        }
        for p in active_posts_all
    ]

    total_posts = db.query(TeachingPost).count()
    active_posts = db.query(TeachingPost).filter(TeachingPost.is_active == True).count()
    custom_posts = db.query(TeachingPost).filter(TeachingPost.is_custom == True).count()

    return render_template(
        'admin/teaching_posts.html',
        posts=posts,
        all_cadres=all_cadres,
        all_categories=all_categories,
        all_post_titles=all_post_titles,
        all_feeder_posts=all_feeder_posts,
        all_qualifications=all_qualifications,
        predefined_catalog=predefined_catalog,
        selected_cadre=cadre_filter,
        selected_bs=bs_filter,
        selected_status=status_filter,
        search_query=search_query,
        total_posts=total_posts,
        active_posts=active_posts,
        custom_posts=custom_posts
    )

@admin_bp.route('/teaching-posts/<int:post_id>/edit', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def edit_teaching_post(post_id):
    db = g.db
    post = get_or_404(TeachingPost, post_id)

    post.post_title = request.form.get('post_title', post.post_title).strip()
    post.cadre = request.form.get('cadre', post.cadre).strip()
    post.basic_scale = request.form.get('basic_scale', post.basic_scale, type=int)
    post.category = request.form.get('category', post.category).strip()
    post.gender = request.form.get('gender', post.gender).strip()
    post.feeder_post_title = request.form.get('feeder_post_title', '').strip() or None
    post.min_service_years = request.form.get('min_service_years', 0, type=int)
    post.prescribed_qualification = request.form.get('prescribed_qualification', '').strip() or None
    post.is_active = True if request.form.get('is_active') == 'on' else False

    db.commit()
    log_audit(db, g.user, 'EDIT_TEACHING_POST', entity_type='TeachingPost', entity_id=post.id, details=f"Updated post {post.post_title} (BS-{post.basic_scale})", ip_address=request.remote_addr)
    flash(f"Teaching Post '{post.post_title}' updated successfully.", "success")
    return redirect(url_for('admin.teaching_posts'))

@admin_bp.route('/teaching-posts/<int:post_id>/toggle', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def toggle_teaching_post(post_id):
    db = g.db
    post = get_or_404(TeachingPost, post_id)
    post.is_active = not post.is_active
    db.commit()
    status_str = "activated" if post.is_active else "deactivated"
    log_audit(db, g.user, 'TOGGLE_TEACHING_POST', entity_type='TeachingPost', entity_id=post.id, details=f"{status_str.title()} post {post.post_title}", ip_address=request.remote_addr)
    flash(f"Teaching Post '{post.post_title}' has been {status_str}.", "info")
    return redirect(url_for('admin.teaching_posts'))

@admin_bp.route('/rules', methods=['GET', 'POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def rules_manager():
    db = g.db
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'edit_rule':
            rule_id = int(request.form.get('rule_id'))
            rule = db.query(PromotionRule).get(rule_id)
            if rule:
                rule.rule_name = request.form.get('rule_name', '').strip()
                rule.source_designation = request.form.get('source_designation', '').strip()
                rule.source_bs = int(request.form.get('source_bs', rule.source_bs))
                rule.target_designation = request.form.get('target_designation', '').strip()
                rule.target_bs = int(request.form.get('target_bs', rule.target_bs))
                rule.promotion_category = request.form.get('promotion_category', rule.promotion_category).strip()
                rule.min_regular_service_years = float(request.form.get('min_regular_service_years', 0.0))
                rule.min_total_service_years = float(request.form.get('min_regular_service_years', 0.0))
                rule.required_degree_level = request.form.get('required_degree_level', rule.required_degree_level).strip()
                rule.required_degree_names = request.form.get('required_degree_names', '').strip()
                rule.required_subjects = request.form.get('required_subjects', '').strip()
                rule.required_professional_degree = request.form.get('required_professional_degree', '').strip()
                rule.quota_percentage = float(request.form.get('quota_percentage', 50.0))
                rule.is_active = bool(request.form.get('is_active'))
                db.commit()
                log_audit(db, g.user, 'EDIT_PROMOTION_RULE', entity_type='PromotionRule', entity_id=rule.id, details=f"Edited Rule: {rule.rule_code}", ip_address=request.remote_addr)
                flash(f"Promotion Rule '{rule.rule_code}' updated successfully.", "success")
                return redirect(url_for('admin.rules_manager'))

    sources = db.query(RuleSource).order_by(RuleSource.created_at.desc()).all()
    rules = db.query(PromotionRule).order_by(PromotionRule.source_bs, PromotionRule.target_bs).all()
    return render_template('superadmin/rules_manager.html', sources=sources, rules=rules)


# ==============================================================================
# STATUTORY SUPERANNUATION (AGE 60+) & BULK RETIREMENT MANAGEMENT
# ==============================================================================
@admin_bp.route('/retirements')
@role_required(['ADMIN', 'SUPERADMIN'])
def retirements_review():
    db = g.db
    district_filter = request.args.get('district', '').strip()
    status_filter = request.args.get('status', 'all').strip() # 'all', 'pending_order', 'retired'
    search_query = request.args.get('q', '').strip()

    # Query non-deleted teachers who have reached age 60 or approaching within 1 year
    today = date.today()
    cutoff_60 = today.replace(year=today.year - 60)
    
    query = db.query(Teacher).filter(
        Teacher.is_deleted == False,
        Teacher.date_of_birth.isnot(None),
        (Teacher.date_of_birth <= cutoff_60) | (Teacher.account_status == 'Retired')
    )

    if district_filter:
        query = query.filter(Teacher.district == district_filter)

    if status_filter == 'retired':
        query = query.filter(Teacher.account_status == 'Retired')
    elif status_filter == 'pending_order':
        query = query.filter(Teacher.account_status != 'Retired')

    if search_query:
        query = query.filter(
            (Teacher.full_name.ilike(f'%{search_query}%')) |
            (Teacher.cnic.ilike(f'%{search_query}%')) |
            (Teacher.personnel_no.ilike(f'%{search_query}%')) |
            (Teacher.current_designation.ilike(f'%{search_query}%')) |
            (Teacher.school_name.ilike(f'%{search_query}%'))
        )

    teachers = query.order_by(Teacher.date_of_birth.asc()).all()

    # Aggregate counts
    all_60_plus = db.query(Teacher).filter(
        Teacher.is_deleted == False,
        Teacher.date_of_birth.isnot(None),
        (Teacher.date_of_birth <= cutoff_60) | (Teacher.account_status == 'Retired')
    ).all()

    total_60_plus = len(all_60_plus)
    retired_count = sum(1 for t in all_60_plus if t.account_status == 'Retired')
    pending_order_count = total_60_plus - retired_count

    # Cadre breakdown of 60+ teachers
    cadre_counts = {}
    for t in all_60_plus:
        cadre = (t.current_designation or 'General').strip()
        if 'PST' in cadre.upper() or 'PRIMARY' in cadre.upper():
            c_tag = 'PST'
        elif 'EST' in cadre.upper() or 'ELEMENTARY' in cadre.upper():
            c_tag = 'EST'
        elif 'SST' in cadre.upper() or 'SECONDARY' in cadre.upper():
            c_tag = 'SST'
        elif 'SS' in cadre.upper() or 'SUBJECT SPECIALIST' in cadre.upper():
            c_tag = 'SS'
        else:
            c_tag = cadre.split('(')[0].strip() or 'Other'
        cadre_counts[c_tag] = cadre_counts.get(c_tag, 0) + 1

    return render_template(
        'admin/retirements.html',
        teachers=teachers,
        total_60_plus=total_60_plus,
        retired_count=retired_count,
        pending_order_count=pending_order_count,
        cadre_counts=cadre_counts,
        district_filter=district_filter,
        status_filter=status_filter,
        search_query=search_query
    )


@admin_bp.route('/retirements/bulk-retire', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def bulk_retire():
    db = g.db
    teacher_ids = request.form.getlist('teacher_ids')
    order_no = request.form.get('order_no', '').strip()
    order_date_str = request.form.get('order_date', '').strip()
    remarks = request.form.get('remarks', '').strip()

    if not teacher_ids:
        flash("Please select at least one teacher to mark as retired.", "warning")
        return redirect(url_for('admin.retirements_review'))

    if not order_no:
        flash("Retirement Order Number is mandatory for official superannuation records.", "danger")
        return redirect(url_for('admin.retirements_review'))

    order_date_obj = date.today()
    if order_date_str:
        try:
            order_date_obj = datetime.strptime(order_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    processed_count = 0
    teacher_names = []

    for tid_str in teacher_ids:
        try:
            tid = int(tid_str)
            t = db.query(Teacher).get(tid)
            if t:
                t.account_status = 'Retired'
                t.is_promotion_disabled = True
                t.promotion_disable_reason = 'Superannuation / Retired'
                t.promotion_disable_remarks = f"Official Retirement Order: {order_no} dated {order_date_obj.strftime('%d-%m-%Y')}. {remarks}".strip()
                t.promotion_disabled_at = datetime.utcnow()
                t.promotion_disabled_by = g.user.username
                t.retirement_order_no = order_no
                t.retirement_order_date = order_date_obj
                
                # Update corresponding user status
                u = db.query(User).filter(User.teacher_id == t.id).first()
                if u:
                    u.is_active = False
                
                processed_count += 1
                teacher_names.append(t.full_name)
        except Exception:
            continue

    db.commit()

    log_audit(
        db, g.user, 'BULK_RETIRE_TEACHERS',
        entity_type='Teacher', entity_id=None,
        details=f"Marked {processed_count} teachers as Retired under Order #{order_no}. Names: {', '.join(teacher_names[:5])}",
        ip_address=request.remote_addr
    )

    flash(f"Successfully marked {processed_count} teachers as officially Retired under Order #{order_no}.", "success")
    return redirect(url_for('admin.retirements_review'))


# ==============================================================================
# DPC MEETING SCHEDULE & CADRE-WISE RETIRING COUNTS
# ==============================================================================
@admin_bp.route('/dpc-schedule')
@role_required(['ADMIN', 'SUPERADMIN'])
def dpc_schedule():
    db = g.db
    year_filter = request.args.get('year', type=int) or date.today().year

    meetings = db.query(DpcMeeting).filter(DpcMeeting.year == year_filter).order_by(DpcMeeting.meeting_date.asc()).all()
    available_years = [r[0] for r in db.query(DpcMeeting.year).distinct().order_by(DpcMeeting.year.desc()).all()]
    if year_filter not in available_years:
        available_years.insert(0, year_filter)

    # Attach computed cadre-wise retiring summary to each meeting
    meeting_summaries = []
    for m in meetings:
        summary = m.get_retiring_summary(db)
        meeting_summaries.append({
            'meeting': m,
            'total_retiring': summary['total_retiring'],
            'cadre_counts': summary['cadre_counts'],
            'teachers': summary['teachers']
        })

    return render_template(
        'admin/dpc_schedule.html',
        meeting_summaries=meeting_summaries,
        year_filter=year_filter,
        available_years=available_years,
        total_meetings=len(meetings)
    )


@admin_bp.route('/dpc-schedule/create', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def create_dpc_meeting():
    db = g.db
    meeting_no = request.form.get('meeting_no', '').strip()
    title = request.form.get('title', '').strip()
    meeting_date_str = request.form.get('meeting_date', '').strip()
    end_date_str = request.form.get('end_date', '').strip()
    year = request.form.get('year', type=int) or date.today().year
    district = request.form.get('district', 'All Districts').strip()
    target_cadres = request.form.get('target_cadres', 'PST, EST, SST').strip()
    agenda_notes = request.form.get('agenda_notes', '').strip()

    if not meeting_no or not title or not meeting_date_str:
        flash("Meeting Number, Title, and Meeting Date are required.", "danger")
        return redirect(url_for('admin.dpc_schedule', year=year))

    try:
        meeting_date = datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid meeting date format.", "danger")
        return redirect(url_for('admin.dpc_schedule', year=year))

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = meeting_date
    else:
        end_date = meeting_date

    new_m = DpcMeeting(
        meeting_no=meeting_no,
        title=title,
        meeting_date=meeting_date,
        end_date=end_date,
        year=year,
        district=district,
        target_cadres=target_cadres,
        agenda_notes=agenda_notes,
        status='Scheduled'
    )
    db.add(new_m)
    db.commit()

    log_audit(
        db, g.user, 'CREATE_DPC_MEETING',
        entity_type='DpcMeeting', entity_id=new_m.id,
        details=f"Scheduled DPC Meeting {meeting_no} ({title}) on {meeting_date} to {end_date}",
        ip_address=request.remote_addr
    )

    flash(f"DPC Meeting '{meeting_no}' scheduled successfully for {meeting_date.strftime('%d-%m-%Y')} (Proceedings through {end_date.strftime('%d-%m-%Y')}).", "success")
    return redirect(url_for('admin.dpc_schedule', year=year))


@admin_bp.route('/dpc-schedule/<int:meeting_id>/edit', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def edit_dpc_meeting(meeting_id):
    db = g.db
    m = get_or_404(DpcMeeting, meeting_id)

    # Statutory requirement: Annual schedule is editable before its end date
    if not m.is_editable and g.user.role != 'SUPERADMIN':
        flash(f"DPC Meeting '{m.meeting_no}' schedule cannot be modified because its scheduled end date ({m.effective_end_date.strftime('%d-%m-%Y')}) has already passed.", "danger")
        return redirect(url_for('admin.dpc_schedule', year=m.year))

    m.meeting_no = request.form.get('meeting_no', m.meeting_no).strip()
    m.title = request.form.get('title', m.title).strip()
    meeting_date_str = request.form.get('meeting_date', '').strip()
    end_date_str = request.form.get('end_date', '').strip()

    if meeting_date_str:
        try:
            m.meeting_date = datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if end_date_str:
        try:
            m.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    elif not m.end_date:
        m.end_date = m.meeting_date

    m.year = request.form.get('year', m.year, type=int)
    m.district = request.form.get('district', m.district).strip()
    m.target_cadres = request.form.get('target_cadres', m.target_cadres).strip()
    m.status = request.form.get('status', m.status).strip()
    m.agenda_notes = request.form.get('agenda_notes', m.agenda_notes).strip()

    db.commit()
    log_audit(db, g.user, 'EDIT_DPC_MEETING', entity_type='DpcMeeting', entity_id=m.id, details=f"Updated DPC Meeting {m.meeting_no}", ip_address=request.remote_addr)
    flash(f"DPC Meeting '{m.meeting_no}' updated successfully.", "success")
    return redirect(url_for('admin.dpc_schedule', year=m.year))


@admin_bp.route('/dpc-schedule/<int:meeting_id>/delete', methods=['POST'])
@role_required(['SUPERADMIN'])
def delete_dpc_meeting(meeting_id):
    db = g.db
    m = get_or_404(DpcMeeting, meeting_id)
    year = m.year
    no = m.meeting_no
    db.delete(m)
    db.commit()
    log_audit(db, g.user, 'DELETE_DPC_MEETING', entity_type='DpcMeeting', entity_id=meeting_id, details=f"Deleted DPC Meeting {no}", ip_address=request.remote_addr)
    flash(f"DPC Meeting '{no}' removed from schedule.", "info")
    return redirect(url_for('admin.dpc_schedule', year=year))


@admin_bp.route('/dpc-schedule/<int:meeting_id>/download-retiring-pdf')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_dpc_retiring_pdf(meeting_id):
    db = g.db
    m = get_or_404(DpcMeeting, meeting_id)
    summary = m.get_retiring_summary(db)
    pdf_buffer = generate_retiring_teachers_pdf(summary['teachers'], dpc_meeting=m)
    filename = f"Retiring_Teachers_DPC_{m.meeting_no.replace('/', '_')}_{m.meeting_date}.pdf"
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ==============================================================================
# PDF AUTHORITY STAMPS, DEPARTMENT HEADERS & DOWNLOADABLE PDFS HUB
# ==============================================================================
@admin_bp.route('/pdf-management')
@role_required(['ADMIN', 'SUPERADMIN'])
def pdf_management():
    db = g.db
    pdf_settings = PdfSetting.get_active_settings(db)
    
    # Collect all available PDF categories and resources for the Downloadable PDFs Hub
    rules = db.query(PromotionRule).filter(PromotionRule.is_active == True).order_by(PromotionRule.target_bs.asc()).all()
    posts = db.query(TeachingPost).filter(TeachingPost.is_active == True).order_by(TeachingPost.basic_scale.asc()).all()
    dpc_meetings = db.query(DpcMeeting).order_by(DpcMeeting.meeting_date.desc()).all()
    sample_teachers = db.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.seniority_no.asc()).limit(30).all()

    return render_template(
        'admin/pdf_management.html',
        settings=pdf_settings,
        rules=rules,
        posts=posts,
        dpc_meetings=dpc_meetings,
        sample_teachers=sample_teachers
    )


@admin_bp.route('/pdf-management/update-settings', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def update_pdf_settings():
    db = g.db
    s = PdfSetting.get_active_settings(db)
    s.gov_header = request.form.get('gov_header', s.gov_header).strip()
    s.dept_header = request.form.get('dept_header', s.dept_header).strip()
    s.portal_title = request.form.get('portal_title', s.portal_title).strip()
    
    # Stamp enable/disable toggle and properties
    s.is_stamp_enabled = ('is_stamp_enabled' in request.form)
    s.stamp_text = request.form.get('stamp_text', s.stamp_text).strip()
    s.stamp_shape = request.form.get('stamp_shape', s.stamp_shape).strip()
    s.stamp_color = request.form.get('stamp_color', s.stamp_color).strip()

    # Dynamic customizable signatories
    sig_titles = request.form.getlist('sig_title[]')
    sig_depts = request.form.getlist('sig_dept[]')
    sig_names = request.form.getlist('sig_name[]')

    members = []
    for i in range(len(sig_titles)):
        title = sig_titles[i].strip()
        if title:
            dept = sig_depts[i].strip() if i < len(sig_depts) else ''
            name = sig_names[i].strip() if i < len(sig_names) else ''
            members.append({'title': title, 'dept': dept, 'name': name})

    if members:
        s.set_signatories(members)
        if len(members) >= 1:
            s.authority_1_title = members[0]['title']
            s.authority_1_dept = members[0]['dept']
        if len(members) >= 2:
            s.authority_2_title = members[1]['title']
            s.authority_2_dept = members[1]['dept']
        if len(members) >= 3:
            s.authority_3_title = members[2]['title']
            s.authority_3_dept = members[2]['dept']
    else:
        # Fallback to single inputs if list not passed
        s.authority_1_title = request.form.get('authority_1_title', s.authority_1_title).strip()
        s.authority_1_dept = request.form.get('authority_1_dept', s.authority_1_dept).strip()
        s.authority_2_title = request.form.get('authority_2_title', s.authority_2_title).strip()
        s.authority_2_dept = request.form.get('authority_2_dept', s.authority_2_dept).strip()
        s.authority_3_title = request.form.get('authority_3_title', s.authority_3_title).strip()
        s.authority_3_dept = request.form.get('authority_3_dept', s.authority_3_dept).strip()

    s.legal_disclaimer = request.form.get('legal_disclaimer', s.legal_disclaimer).strip()

    db.commit()
    log_audit(db, g.user, 'UPDATE_PDF_SETTINGS', entity_type='PdfSetting', entity_id=s.id, details=f"Updated PDF headers, {s.stamp_shape} stamp (enabled={s.is_stamp_enabled}), and {len(members) or 3} committee signatories", ip_address=request.remote_addr)
    flash("PDF Authority Stamps, Departmental Headers & Signatories updated successfully. All generated PDFs will now reflect these settings.", "success")
    return redirect(url_for('admin.pdf_management'))


@admin_bp.route('/pdf-management/download-retiring-pdf')
@role_required(['ADMIN', 'SUPERADMIN'])
def download_all_retiring_pdf():
    db = g.db
    district = request.args.get('district', '')
    cutoff_60 = date.today().replace(year=date.today().year - 60)
    query = db.query(Teacher).filter(
        Teacher.is_deleted == False,
        Teacher.date_of_birth.isnot(None),
        (Teacher.date_of_birth <= cutoff_60) | (Teacher.account_status == 'Retired')
    )
    if district:
        query = query.filter(Teacher.district == district)

    teachers = query.order_by(Teacher.date_of_birth.asc()).all()
    pdf_buffer = generate_retiring_teachers_pdf(teachers)
    filename = f"Statutory_Superannuated_Teachers_Roll_{date.today()}.pdf"
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ==============================================================================
# TEACHER CREDENTIALS & PASSWORD RESET MANAGEMENT
# ==============================================================================

@admin_bp.route('/teacher-credentials')
@role_required(['ADMIN', 'SUPERADMIN'])
def teacher_credentials():
    db = g.db
    current_tab = request.args.get('tab', '')
    status_filter = request.args.get('status', 'Pending')
    search_q = request.args.get('q', '').strip()
    selected_district = request.args.get('district', '')

    # District scoping for District Admins
    admin_district = getattr(g.user, 'district', None)
    filter_district = admin_district if (g.user.role == 'ADMIN' and admin_district) else selected_district

    # 1. Password Reset Requests Query
    ticket_query = db.query(PasswordResetRequest).filter(PasswordResetRequest.account_role == 'TEACHER')
    if filter_district:
        ticket_query = ticket_query.filter(
            (PasswordResetRequest.district == filter_district) | (PasswordResetRequest.district.is_(None))
        )
    if status_filter and status_filter != 'All':
        ticket_query = ticket_query.filter(PasswordResetRequest.status == status_filter)
    
    if search_q:
        ticket_query = ticket_query.filter(
            (PasswordResetRequest.cnic.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.personnel_no.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.user_full_name.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.phone.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.email.ilike(f"%{search_q}%"))
        )

    tickets = ticket_query.order_by(PasswordResetRequest.created_at.desc()).all()

    # Counts
    pending_base = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.account_role == 'TEACHER',
        PasswordResetRequest.status == 'Pending'
    )
    if filter_district:
        pending_base = pending_base.filter(
            (PasswordResetRequest.district == filter_district) | (PasswordResetRequest.district.is_(None))
        )
    pending_count = pending_base.count()

    processed_base = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.account_role == 'TEACHER',
        PasswordResetRequest.status == 'Processed'
    )
    if filter_district:
        processed_base = processed_base.filter(
            (PasswordResetRequest.district == filter_district) | (PasswordResetRequest.district.is_(None))
        )
    processed_count = processed_base.count()

    # Default tab: if pending tickets exist and no explicit tab, show resets tab
    if not current_tab:
        current_tab = 'resets' if pending_count > 0 else 'directory'

    # 2. Teacher Accounts & Direct Credential Editor Query
    teacher_query = db.query(Teacher).filter(Teacher.is_deleted == False)
    if filter_district:
        teacher_query = teacher_query.filter(Teacher.district == filter_district)

    if search_q:
        teacher_query = teacher_query.filter(
            (Teacher.full_name.ilike(f"%{search_q}%")) |
            (Teacher.cnic.ilike(f"%{search_q}%")) |
            (Teacher.personnel_no.ilike(f"%{search_q}%")) |
            (Teacher.school_name.ilike(f"%{search_q}%"))
        )

    # All teachers matching query without arbitrary truncation
    teachers = teacher_query.order_by(Teacher.full_name.asc()).all()

    # Preload user accounts for teachers
    teacher_ids = [t.id for t in teachers]
    users_by_teacher_id = {}
    if teacher_ids:
        users = db.query(User).filter(User.teacher_id.in_(teacher_ids)).all()
        for u in users:
            users_by_teacher_id[u.teacher_id] = u

        # Auto-ensure all active teachers have linked User accounts
        missing_teachers = [t for t in teachers if t.id not in users_by_teacher_id]
        if missing_teachers:
            for mt in missing_teachers:
                existing_u = db.query(User).filter((User.cnic == mt.cnic) | (User.username == mt.cnic)).first()
                if existing_u:
                    existing_u.teacher_id = mt.id
                    if not existing_u.cnic:
                        existing_u.cnic = mt.cnic
                    if not existing_u.district:
                        existing_u.district = mt.district
                    users_by_teacher_id[mt.id] = existing_u
                else:
                    new_u = User(
                        teacher_id=mt.id,
                        username=mt.cnic,
                        role='TEACHER',
                        full_name=mt.full_name,
                        cnic=mt.cnic,
                        district=mt.district,
                        phone=mt.mobile or '',
                        email=mt.email or '',
                        is_active=True,
                        is_first_login=True
                    )
                    new_u.set_password('Teacher@123')
                    db.add(new_u)
                    db.flush()
                    users_by_teacher_id[mt.id] = new_u
            db.commit()

    # Total counts
    total_teachers = db.query(Teacher).filter(Teacher.is_deleted == False)
    if filter_district:
        total_teachers = total_teachers.filter(Teacher.district == filter_district)
    total_teachers_count = total_teachers.count()

    designations = sorted([r[0] for r in db.query(Teacher.current_designation).distinct().all() if r[0]])

    from app import PUNJAB_DISTRICTS
    return render_template(
        'admin/teacher_credentials.html',
        current_tab=current_tab,
        status_filter=status_filter,
        search_q=search_q,
        selected_district=filter_district,
        districts=PUNJAB_DISTRICTS,
        designations=designations,
        tickets=tickets,
        pending_count=pending_count,
        processed_count=processed_count,
        teachers=teachers,
        users_by_teacher_id=users_by_teacher_id,
        total_teachers_count=total_teachers_count
    )


@admin_bp.route('/teacher-credentials/bulk-reset', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def bulk_reset_teacher_passwords():
    db = g.db
    target_district = (request.form.get('target_district') or request.form.get('district_filter') or '').strip()
    target_designation = (request.form.get('target_designation') or request.form.get('designation_filter') or '').strip()
    reset_mode = request.form.get('reset_mode', 'default').strip()  # 'uniform' or 'default'
    uniform_password = request.form.get('uniform_password', '').strip()
    force_first_login = ('force_first_login' in request.form)
    confirm_phrase = (request.form.get('confirm_phrase') or request.form.get('confirm_text') or '').strip()

    admin_district = getattr(g.user, 'district', None)
    if g.user.role == 'ADMIN' and admin_district:
        target_district = admin_district

    if confirm_phrase.upper() != 'CONFIRM':
        flash("Bulk password reset aborted: Confirmation phrase 'CONFIRM' must be entered.", "danger")
        return redirect(url_for('admin.teacher_credentials', tab='bulk', district=target_district))

    if reset_mode == 'uniform' and not uniform_password:
        flash("Please provide the uniform password to apply to all selected teachers.", "danger")
        return redirect(url_for('admin.teacher_credentials', tab='bulk', district=target_district))

    teacher_query = db.query(Teacher).filter(Teacher.is_deleted == False)
    if target_district:
        teacher_query = teacher_query.filter(Teacher.district == target_district)
    if target_designation and target_designation != 'ALL':
        teacher_query = teacher_query.filter(Teacher.current_designation == target_designation)

    teachers = teacher_query.all()
    if not teachers:
        flash("No teachers found matching the selected scope.", "warning")
        return redirect(url_for('admin.teacher_credentials', tab='bulk', district=target_district))

    updated_count = 0
    created_count = 0

    for t in teachers:
        u = db.query(User).filter(User.teacher_id == t.id).first()
        if not u:
            u = db.query(User).filter((User.cnic == t.cnic) | (User.username == t.cnic)).first()
            if u:
                u.teacher_id = t.id
                u.cnic = t.cnic
                u.district = t.district

        if not u:
            u = User(
                teacher_id=t.id,
                username=t.cnic,
                role='TEACHER',
                full_name=t.full_name,
                cnic=t.cnic,
                district=t.district,
                phone=t.mobile or '',
                email=t.email or '',
                is_active=True,
                is_first_login=force_first_login
            )
            created_count += 1
            db.add(u)

        pass_to_set = uniform_password if reset_mode == 'uniform' else 'Teacher@123'
        u.set_password(pass_to_set)
        u.failed_login_attempts = 0
        u.locked_until = None
        u.is_active = True
        if force_first_login:
            u.is_first_login = True
        updated_count += 1

    db.commit()

    scope_name = target_district or 'All Punjab'
    log_audit(
        db, g.user, 'BULK_TEACHER_PASSWORD_RESET',
        entity_type='User',
        details=f"Bulk password reset for {updated_count} teachers ({created_count} accounts provisioned). Mode: {reset_mode}. Scope: District={scope_name}, Cadre={target_designation or 'All'}",
        ip_address=request.remote_addr
    )

    flash(f"Bulk Password Operation Completed: Successfully updated credentials for {updated_count} teachers in {scope_name}! ({created_count} accounts newly created). All accounts are active.", "success")
    return redirect(url_for('admin.teacher_credentials', tab='directory', district=target_district))


@admin_bp.route('/teacher-credentials/dispatch-password', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def dispatch_teacher_password():
    db = g.db
    ticket_id = request.form.get('ticket_id') or request.form.get('request_id')
    new_password = request.form.get('new_password', '').strip()
    dispatch_channel = request.form.get('dispatch_channel', 'Phone / SMS').strip()
    admin_notes = request.form.get('admin_notes', '').strip()

    ticket = db.query(PasswordResetRequest).get(ticket_id)
    if not ticket:
        flash("Password reset ticket not found.", "danger")
        return redirect(url_for('admin.teacher_credentials', tab='resets'))

    if not new_password:
        flash("Please provide the new password to set and communicate to the teacher.", "danger")
        return redirect(url_for('admin.teacher_credentials', tab='resets'))

    # Locate or create user account for teacher
    target_user = None
    if ticket.user_id:
        target_user = db.query(User).get(ticket.user_id)
    if not target_user and ticket.teacher_id:
        target_user = db.query(User).filter(User.teacher_id == ticket.teacher_id).first()
    if not target_user and ticket.cnic:
        target_user = db.query(User).filter(
            (User.cnic == ticket.cnic) | (User.username == ticket.cnic)
        ).first()

    # If still not found, check teacher record to link user
    if not target_user:
        teacher = None
        if ticket.teacher_id:
            teacher = db.query(Teacher).get(ticket.teacher_id)
        elif ticket.cnic:
            teacher = db.query(Teacher).filter(Teacher.cnic == ticket.cnic).first()
        elif ticket.personnel_no:
            teacher = db.query(Teacher).filter(Teacher.personnel_no == ticket.personnel_no).first()

        if teacher:
            target_user = db.query(User).filter(User.teacher_id == teacher.id).first()
            if not target_user:
                # Create user account for teacher
                target_user = User(
                    username=teacher.cnic,
                    role='TEACHER',
                    full_name=teacher.full_name,
                    cnic=teacher.cnic,
                    phone=ticket.phone or teacher.contact_number,
                    email=ticket.email or teacher.email,
                    teacher_id=teacher.id,
                    district=teacher.district,
                    is_active=True
                )
                db.add(target_user)
                db.flush()

    if target_user:
        target_user.set_password(new_password)
        target_user.failed_login_attempts = 0
        target_user.locked_until = None
        target_user.is_active = True
        if ticket.phone:
            target_user.phone = ticket.phone
        if ticket.email:
            target_user.email = ticket.email
        user_info = f"Password updated on account {target_user.username}"
    else:
        user_info = "Manual verification token logged"

    ticket.status = 'Processed'
    ticket.temporary_password_set = new_password
    ticket.dispatch_channel = dispatch_channel
    ticket.admin_response_notes = f"[{dispatch_channel}] {admin_notes}".strip()
    ticket.processed_by = g.user.username
    ticket.processed_at = datetime.utcnow()
    db.commit()

    log_audit(db, g.user, 'TEACHER_PASSWORD_DISPATCHED', entity_type='PasswordResetRequest', entity_id=ticket.id,
              details=f"Dispatched password for {ticket.user_full_name} (CNIC: {ticket.cnic}, P#: {ticket.personnel_no}) via {dispatch_channel}. {user_info}",
              ip_address=request.remote_addr)

    flash(f"Password reset for {ticket.user_full_name} processed successfully! New password '{new_password}' dispatched via {dispatch_channel}.", "success")
    return redirect(url_for('admin.teacher_credentials', tab='resets'))


@admin_bp.route('/teacher-credentials/reject-ticket', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def reject_teacher_reset_ticket():
    db = g.db
    ticket_id = request.form.get('ticket_id')
    rejection_reason = request.form.get('rejection_reason', 'Discrepancy in credentials / identity verification failed').strip()

    ticket = db.query(PasswordResetRequest).get(ticket_id)
    if not ticket:
        flash("Password reset ticket not found.", "danger")
        return redirect(url_for('admin.teacher_credentials', tab='resets'))

    ticket.status = 'Rejected'
    ticket.admin_response_notes = rejection_reason
    ticket.processed_by = g.user.username
    ticket.processed_at = datetime.utcnow()
    db.commit()

    log_audit(db, g.user, 'TEACHER_PASSWORD_RESET_REJECTED', entity_type='PasswordResetRequest', entity_id=ticket.id,
              details=f"Rejected teacher reset ticket #{ticket.id} for CNIC {ticket.cnic}: {rejection_reason}",
              ip_address=request.remote_addr)

    flash(f"Reset ticket #{ticket.id} has been marked as Rejected.", "warning")
    return redirect(url_for('admin.teacher_credentials', tab='resets'))


@admin_bp.route('/teacher-credentials/update-account', methods=['POST'])
@role_required(['ADMIN', 'SUPERADMIN'])
def update_teacher_credentials():
    db = g.db
    teacher_id = request.form.get('teacher_id')
    username = request.form.get('username', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    new_password = request.form.get('new_password', '').strip()
    is_active = request.form.get('is_active') == '1'

    teacher = db.query(Teacher).get(teacher_id)
    if not teacher:
        flash("Teacher record not found.", "danger")
        return redirect(url_for('admin.teacher_credentials', tab='directory'))

    # Find or create User
    user = db.query(User).filter(User.teacher_id == teacher.id).first()
    if not user:
        user = db.query(User).filter(
            (User.cnic == teacher.cnic) | (User.username == teacher.cnic)
        ).first()

    if not user:
        user = User(
            username=username or teacher.cnic,
            role='TEACHER',
            full_name=teacher.full_name,
            cnic=teacher.cnic,
            phone=phone or teacher.contact_number,
            email=email or teacher.email,
            teacher_id=teacher.id,
            district=teacher.district,
            is_active=is_active
        )
        if new_password:
            user.set_password(new_password)
        else:
            user.set_password(teacher.cnic)
        db.add(user)
    else:
        if username:
            user.username = username
        if phone:
            user.phone = phone
            teacher.contact_number = phone
        if email:
            user.email = email
            teacher.email = email
        user.is_active = is_active
        if is_active:
            user.locked_until = None
            user.failed_login_attempts = 0
        if new_password:
            user.set_password(new_password)

    db.commit()
    log_audit(db, g.user, 'TEACHER_CREDENTIALS_UPDATED', entity_type='User', entity_id=user.id,
              details=f"Admin {g.user.username} updated credentials for teacher {teacher.full_name} (CNIC: {teacher.cnic}, Password Updated: {'Yes' if new_password else 'No'})",
              ip_address=request.remote_addr)

    flash(f"Credentials successfully updated for {teacher.full_name} (Username: {user.username}).", "success")
    return redirect(url_for('admin.teacher_credentials', tab='directory', q=teacher.cnic))


