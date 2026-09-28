from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, send_file
from app import role_required
from app.models.teacher import Teacher
from app.models.qualification import Qualification
from app.models.service import ServiceHistory
from app.models.seniority import SeniorityRecord
from app.models.rule import PromotionRule
from app.models.correction import CorrectionRequest
from app.services.audit_service import log_audit
from app.services.promotion_engine import evaluate_eligibility, calculate_service_years
from app.services.pdf_service import generate_teacher_dossier_pdf, generate_eligibility_report_pdf

teacher_bp = Blueprint('teacher', __name__)

def get_current_teacher():
    db = g.db
    if not g.user or not g.user.teacher_id:
        # Fallback: lookup by username as CNIC
        teacher = db.query(Teacher).filter(Teacher.cnic == g.user.username).first()
        if teacher:
            g.user.teacher_id = teacher.id
            db.commit()
            return teacher
        return None
    return db.query(Teacher).get(g.user.teacher_id)

@teacher_bp.route('/')
@teacher_bp.route('/dashboard')
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def dashboard():
    teacher = get_current_teacher()
    if not teacher:
        flash("No teacher profile associated with your user account.", "warning")
        return redirect(url_for('auth.login'))

    calc_start = teacher.regularization_date or teacher.current_post_date or teacher.appointment_date
    service_years = calculate_service_years(calc_start, date.today())
    pending_corrections = [c for c in (teacher.correction_requests or []) if c.status == 'Pending']
    
    # Check applicable promotion rules
    db = g.db
    applicable_rules = db.query(PromotionRule).filter(
        PromotionRule.source_bs == teacher.current_bs,
        PromotionRule.is_active == True
    ).all()

    return render_template(
        'teacher/dashboard.html',
        teacher=teacher,
        service_years=service_years,
        pending_corrections_count=len(pending_corrections),
        applicable_rules=applicable_rules
    )

@teacher_bp.route('/profile', methods=['GET', 'POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def profile():
    teacher = get_current_teacher()
    if not teacher:
        flash("Teacher record not found.", "danger")
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        # Teacher is ONLY permitted to edit contact details
        teacher.mobile = request.form.get('mobile', teacher.mobile or '').strip()
        teacher.email = request.form.get('email', teacher.email or '').strip()
        teacher.address = request.form.get('address', teacher.address or '').strip()
        
        g.db.commit()
        log_audit(g.db, g.user, 'UPDATE_OWN_CONTACT', entity_type='Teacher', entity_id=teacher.id, details="Teacher updated personal contact info", ip_address=request.remote_addr)
        flash("Contact details updated successfully.", "success")
        return redirect(url_for('teacher.profile'))

    return render_template('teacher/profile.html', teacher=teacher)

@teacher_bp.route('/qualifications', methods=['GET', 'POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def qualifications():
    teacher = get_current_teacher()
    if not teacher:
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        # New additions in educational records are ALWAYS permitted
        deg_level = request.form.get('degree_level', 'Bachelor').strip()
        deg_name = request.form.get('degree_name', '').strip()
        subject = request.form.get('subject', '').strip()
        major_subject = request.form.get('major_subject', '').strip()
        minor_subject = request.form.get('minor_subject', '').strip()
        division = request.form.get('division', 'First').strip()
        passing_year = int(request.form.get('passing_year', 2015))
        university = request.form.get('board_university', '').strip()
        is_prof = bool(request.form.get('professional_qualification'))
        reg_no = request.form.get('registration_number', '').strip()
        marks_obt_val = request.form.get('marks_obtained', '').strip()
        tot_marks_val = request.form.get('total_marks', '').strip()
        marks_obtained = float(marks_obt_val) if marks_obt_val else None
        total_marks = float(tot_marks_val) if tot_marks_val else None
        percentage = round((marks_obtained / total_marks) * 100, 2) if (marks_obtained is not None and total_marks and total_marks > 0) else None

        if deg_name and subject and university:
            new_q = Qualification(
                teacher_id=teacher.id,
                degree_level=deg_level,
                degree_name=deg_name,
                subject=subject,
                major_subject=major_subject or subject,
                minor_subject=minor_subject,
                division=division,
                marks_obtained=marks_obtained,
                total_marks=total_marks,
                percentage=percentage,
                passing_year=passing_year,
                board_university=university,
                professional_qualification=is_prof,
                registration_number=reg_no,
                change_type='new',
                is_new=True,
                verification_status='Verified' if teacher.is_data_verified_by_teacher else 'Pending'
            )
            teacher.has_new_records = True
            g.db.add(new_q)
            g.db.commit()
            log_audit(g.db, g.user, 'SUBMIT_QUALIFICATION', entity_type='Qualification', entity_id=new_q.id, details=f"Teacher added new degree {deg_name}", ip_address=request.remote_addr)
            flash(f"New qualification '{deg_name}' added successfully. Marked as newly added record.", "success")
            return redirect(url_for('teacher.qualifications'))

    return render_template('teacher/qualifications.html', teacher=teacher)

@teacher_bp.route('/qualifications/<int:qual_id>/edit', methods=['POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def edit_qualification(qual_id):
    teacher = get_current_teacher()
    if not teacher:
        return redirect(url_for('teacher.dashboard'))

    qual = g.db.query(Qualification).filter(Qualification.id == qual_id, Qualification.teacher_id == teacher.id).first()
    if not qual:
        flash("Qualification record not found.", "danger")
        return redirect(url_for('teacher.qualifications'))

    # Once teacher verified his/her data, direct changes to existing records are locked
    if teacher.is_data_verified_by_teacher:
        flash("Your official credentials have already been verified and locked. To correct or modify this qualification, please submit an official Correction Request.", "warning")
        return redirect(url_for('teacher.correction_request'))

    qual.degree_level = request.form.get('degree_level', qual.degree_level).strip()
    qual.degree_name = request.form.get('degree_name', qual.degree_name).strip()
    qual.subject = request.form.get('subject', qual.subject).strip()
    qual.major_subject = request.form.get('major_subject', qual.major_subject or '').strip()
    qual.minor_subject = request.form.get('minor_subject', qual.minor_subject or '').strip()
    qual.division = request.form.get('division', qual.division).strip()
    qual.passing_year = int(request.form.get('passing_year', qual.passing_year))
    qual.board_university = request.form.get('board_university', qual.board_university).strip()
    qual.professional_qualification = bool(request.form.get('professional_qualification'))
    qual.registration_number = request.form.get('registration_number', qual.registration_number or '').strip()

    marks_obt_val = request.form.get('marks_obtained', '').strip()
    tot_marks_val = request.form.get('total_marks', '').strip()
    if marks_obt_val:
        try:
            qual.marks_obtained = float(marks_obt_val)
        except ValueError:
            pass
    elif 'marks_obtained' in request.form and not marks_obt_val:
        qual.marks_obtained = None

    if tot_marks_val:
        try:
            qual.total_marks = float(tot_marks_val)
        except ValueError:
            pass
    elif 'total_marks' in request.form and not tot_marks_val:
        qual.total_marks = None

    if qual.marks_obtained is not None and qual.total_marks and qual.total_marks > 0:
        qual.percentage = round((qual.marks_obtained / qual.total_marks) * 100, 2)
    else:
        qual.percentage = None

    # Track edit
    qual.is_edited = True
    qual.change_type = 'edited'
    teacher.has_edited_records = True

    g.db.commit()
    log_audit(g.db, g.user, 'EDIT_QUALIFICATION', entity_type='Qualification', entity_id=qual.id, details=f"Teacher edited qualification {qual.degree_name}", ip_address=request.remote_addr)
    flash(f"Qualification '{qual.degree_name}' updated successfully.", "success")
    return redirect(url_for('teacher.qualifications'))

@teacher_bp.route('/service-history')
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def service_history():
    teacher = get_current_teacher()
    return render_template('teacher/service_history.html', teacher=teacher)

@teacher_bp.route('/service-history/add', methods=['POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def add_service_history():
    teacher = get_current_teacher()
    if not teacher:
        return redirect(url_for('teacher.dashboard'))

    # New additions in service records are ALWAYS permitted
    designation = request.form.get('designation', '').strip()
    bs = int(request.form.get('bs', teacher.current_bs))
    school_name = request.form.get('school_name', '').strip()
    district = request.form.get('district', teacher.district).strip()
    tehsil = request.form.get('tehsil', teacher.tehsil).strip()
    from_date_str = request.form.get('from_date', '').strip()
    to_date_str = request.form.get('to_date', '').strip()
    is_current = bool(request.form.get('is_current_post'))
    appointment_type = request.form.get('appointment_type', 'Regular').strip()
    order_no = request.form.get('order_no', '').strip()
    order_date_str = request.form.get('order_date', '').strip()
    remarks = request.form.get('remarks', '').strip()

    if designation and school_name and from_date_str:
        from_d = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_d = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str and not is_current else None
        ord_d = datetime.strptime(order_date_str, '%Y-%m-%d').date() if order_date_str else None

        new_sh = ServiceHistory(
            teacher_id=teacher.id,
            designation=designation,
            bs=bs,
            school_name=school_name,
            district=district,
            tehsil=tehsil,
            from_date=from_d,
            to_date=to_d,
            is_current_post=is_current,
            appointment_type=appointment_type,
            order_no=order_no,
            order_date=ord_d,
            remarks=remarks,
            change_type='new',
            is_new=True,
            verification_status='Verified' if teacher.is_data_verified_by_teacher else 'Pending'
        )
        teacher.has_new_records = True
        g.db.add(new_sh)
        g.db.commit()
        log_audit(g.db, g.user, 'ADD_SERVICE_RECORD', entity_type='ServiceHistory', entity_id=new_sh.id, details=f"Teacher added service record at {school_name}", ip_address=request.remote_addr)
        flash(f"New service posting '{designation}' at '{school_name}' added successfully.", "success")

    return redirect(url_for('teacher.service_history'))

@teacher_bp.route('/service-history/<int:service_id>/edit', methods=['POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def edit_service_history(service_id):
    teacher = get_current_teacher()
    if not teacher:
        return redirect(url_for('teacher.dashboard'))

    sh = g.db.query(ServiceHistory).filter(ServiceHistory.id == service_id, ServiceHistory.teacher_id == teacher.id).first()
    if not sh:
        flash("Service record not found.", "danger")
        return redirect(url_for('teacher.service_history'))

    # Once teacher verified his/her data, direct changes to existing records are locked
    if teacher.is_data_verified_by_teacher:
        flash("Your official credentials have already been verified and locked. To correct or modify this service posting, please submit an official Correction Request.", "warning")
        return redirect(url_for('teacher.correction_request'))

    sh.designation = request.form.get('designation', sh.designation).strip()
    sh.bs = int(request.form.get('bs', sh.bs))
    sh.school_name = request.form.get('school_name', sh.school_name).strip()
    sh.district = request.form.get('district', sh.district).strip()
    sh.tehsil = request.form.get('tehsil', sh.tehsil).strip()
    from_date_str = request.form.get('from_date', '').strip()
    to_date_str = request.form.get('to_date', '').strip()
    is_current = bool(request.form.get('is_current_post'))

    if from_date_str:
        sh.from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    sh.to_date = None if is_current else (datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None)
    sh.is_current_post = is_current
    sh.appointment_type = request.form.get('appointment_type', sh.appointment_type).strip()
    sh.order_no = request.form.get('order_no', sh.order_no or '').strip()
    ord_date_str = request.form.get('order_date', '').strip()
    if ord_date_str:
        sh.order_date = datetime.strptime(ord_date_str, '%Y-%m-%d').date()
    sh.remarks = request.form.get('remarks', sh.remarks or '').strip()

    # Track edit
    sh.is_edited = True
    sh.change_type = 'edited'
    teacher.has_edited_records = True

    g.db.commit()
    log_audit(g.db, g.user, 'EDIT_SERVICE_RECORD', entity_type='ServiceHistory', entity_id=sh.id, details=f"Teacher edited service posting {sh.designation}", ip_address=request.remote_addr)
    flash(f"Service record for '{sh.designation}' updated successfully.", "success")
    return redirect(url_for('teacher.service_history'))

@teacher_bp.route('/verify-my-data', methods=['POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def verify_my_data():
    teacher = get_current_teacher()
    if not teacher:
        flash("Teacher profile not found.", "danger")
        return redirect(url_for('teacher.dashboard'))

    # Mark teacher profile as officially verified by teacher
    teacher.is_data_verified_by_teacher = True
    teacher.teacher_verified_at = datetime.utcnow()
    teacher.verification_status = 'Verified'  # User specification: "and update teacher recode status verified"

    # Also update child qualification and service history records to Verified
    for q in teacher.qualifications:
        q.verification_status = 'Verified'
        q.verified_by = f"Teacher Self-Verification ({teacher.cnic})"
        q.verified_at = datetime.utcnow()

    for s in teacher.service_history:
        s.verification_status = 'Verified'
        s.verified_by = f"Teacher Self-Verification ({teacher.cnic})"
        s.verified_at = datetime.utcnow()

    g.db.commit()
    log_audit(
        g.db,
        g.user,
        'TEACHER_SELF_VERIFICATION',
        entity_type='Teacher',
        entity_id=teacher.id,
        details=f"Teacher {teacher.full_name} ({teacher.personnel_no}) officially confirmed and verified their educational and service data",
        ip_address=request.remote_addr
    )
    flash("Congratulations! Your educational qualifications and service history have been officially verified and locked. All future changes must be submitted via Correction Requests.", "success")

    # Redirect to whichever page triggered the action
    next_url = request.form.get('next_url') or request.referrer or url_for('teacher.profile')
    return redirect(next_url)

@teacher_bp.route('/seniority')
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def seniority_view():
    teacher = get_current_teacher()
    # Also fetch cohort teachers in same district and designation
    cohort = g.db.query(Teacher).filter(
        Teacher.district == teacher.district,
        Teacher.current_designation == teacher.current_designation,
        Teacher.is_deleted == False
    ).order_by(Teacher.seniority_no.asc().nullslast()).all()
    
    return render_template('teacher/seniority_view.html', teacher=teacher, cohort=cohort)

@teacher_bp.route('/correction-request', methods=['GET', 'POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def correction_request():
    teacher = get_current_teacher()
    if not teacher:
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        ticked_items = request.form.getlist('tick_items')
        reason = request.form.get('reason', '').strip()
        doc_info = request.form.get('supporting_document_name', '').strip()

        # Support single-item submission for backward compatibility
        if not ticked_items and request.form.get('field_name'):
            f_name = request.form.get('field_name', '').strip()
            r_val = request.form.get('requested_value', '').strip()
            if f_name and r_val and reason:
                cur_val = "N/A"
                target_attr = None
                if f_name == 'Father Name':
                    cur_val = teacher.father_name or ''
                    target_attr = 'father_name'
                elif f_name == 'Date of Birth':
                    cur_val = teacher.date_of_birth.strftime('%Y-%m-%d') if teacher.date_of_birth else ''
                    target_attr = 'date_of_birth'
                elif f_name == 'Seniority No':
                    cur_val = str(teacher.seniority_no or '')
                    target_attr = 'seniority_no'
                elif f_name == 'Joining Date':
                    cur_val = teacher.joining_date.strftime('%Y-%m-%d') if teacher.joining_date else ''
                    target_attr = 'joining_date'
                elif f_name == 'School Name':
                    cur_val = teacher.school_name or ''
                    target_attr = 'school_name'

                if str(r_val).strip().lower() == str(cur_val).strip().lower():
                    flash(f"Correction rejected: Proposed value for '{f_name}' cannot be identical to current locked record ({cur_val}).", "danger")
                    return redirect(url_for('teacher.correction_request'))

                cr = CorrectionRequest(
                    teacher_id=teacher.id,
                    record_type='PERSONAL',
                    record_id=None,
                    target_attribute=target_attr,
                    batch_id=f"CR-{teacher.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    field_name=f_name,
                    current_value=cur_val,
                    requested_value=r_val,
                    reason=reason,
                    supporting_document_name=doc_info,
                    status='Pending'
                )
                g.db.add(cr)
                g.db.commit()
                log_audit(g.db, g.user, 'SUBMIT_CORRECTION', entity_type='CorrectionRequest', entity_id=cr.id, details=f"Correction request submitted for {f_name}", ip_address=request.remote_addr)
                flash(f"Correction claim for '{f_name}' submitted successfully for departmental review.", "success")
                return redirect(url_for('teacher.correction_request'))

        if not ticked_items:
            flash("No fields were selected for correction. Please tick the checkbox next to each field you want to modify.", "warning")
            return redirect(url_for('teacher.correction_request'))

        if not reason:
            flash("Please provide a detailed reason / explanation for the requested corrections in the submission modal.", "danger")
            return redirect(url_for('teacher.correction_request'))

        batch_id = f"CR-{teacher.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        created_count = 0
        error_items = []

        for item_key in ticked_items:
            req_val = request.form.get(f'req_{item_key}', '').strip()
            label = request.form.get(f'label_{item_key}', item_key).strip()

            if not req_val:
                continue

            record_type = 'PERSONAL'
            record_id = None
            target_attr = None
            cur_val = ''

            if item_key.startswith('personal:'):
                target_attr = item_key.split(':', 1)[1]
                record_type = 'PERSONAL'
                raw_val = getattr(teacher, target_attr, '')
                if isinstance(raw_val, (datetime, date)):
                    cur_val = raw_val.strftime('%Y-%m-%d')
                else:
                    cur_val = str(raw_val or '')
            elif item_key.startswith('qual:'):
                parts = item_key.split(':')
                record_type = 'QUALIFICATION'
                record_id = int(parts[1])
                target_attr = parts[2]
                q_obj = g.db.query(Qualification).get(record_id)
                if q_obj:
                    raw_val = getattr(q_obj, target_attr, '')
                    cur_val = str(raw_val or '')
            elif item_key.startswith('svc:'):
                parts = item_key.split(':')
                record_type = 'SERVICE'
                record_id = int(parts[1])
                target_attr = parts[2]
                s_obj = g.db.query(ServiceHistory).get(record_id)
                if s_obj:
                    raw_val = getattr(s_obj, target_attr, '')
                    if isinstance(raw_val, (datetime, date)):
                        cur_val = raw_val.strftime('%Y-%m-%d')
                    else:
                        cur_val = str(raw_val or '')

            # Strict Unique Value Validation: proposed value must be different than current locked value
            if str(req_val).strip().lower() == str(cur_val).strip().lower():
                error_items.append(f"'{label}' (Proposed value matches current locked record: '{cur_val}')")
                continue

            cr = CorrectionRequest(
                teacher_id=teacher.id,
                record_type=record_type,
                record_id=record_id,
                target_attribute=target_attr,
                batch_id=batch_id,
                field_name=label,
                current_value=cur_val,
                requested_value=req_val,
                reason=reason,
                supporting_document_name=doc_info,
                status='Pending'
            )
            g.db.add(cr)
            created_count += 1

        if error_items:
            g.db.rollback()
            flash(f"Submission halted! The following field(s) have proposed values identical to current locked data: {', '.join(error_items)}. Corrected cells must have unique values.", "danger")
            return redirect(url_for('teacher.correction_request'))

        if created_count > 0:
            g.db.commit()
            log_audit(g.db, g.user, 'SUBMIT_CORRECTIONS_BATCH', entity_type='Teacher', entity_id=teacher.id, details=f"Teacher submitted {created_count} correction items under batch {batch_id}", ip_address=request.remote_addr)
            flash(f"Successfully submitted {created_count} correction claim(s) (Batch Ref: {batch_id}) for departmental scrutiny. The DEO will review each item individually.", "success")
        else:
            flash("No valid correction values provided. Please enter updated values in the ticked fields.", "warning")

        return redirect(url_for('teacher.correction_request'))

    requests_list = g.db.query(CorrectionRequest).filter(CorrectionRequest.teacher_id == teacher.id).order_by(CorrectionRequest.created_at.desc()).all()
    return render_template('teacher/correction_request.html', teacher=teacher, requests_list=requests_list)

@teacher_bp.route('/simulator', methods=['GET', 'POST'])
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def eligibility_simulator():
    teacher = get_current_teacher()
    db = g.db
    assessment_result = None
    selected_rule_id = request.args.get('rule_id') or request.form.get('rule_id')
    as_of_date_str = request.form.get('as_of_date') or datetime.now().strftime('%Y-%m-%d')

    # Available rules for teacher's current scale
    rules = db.query(PromotionRule).filter(
        PromotionRule.source_bs == teacher.current_bs,
        PromotionRule.is_active == True
    ).order_by(PromotionRule.target_bs, PromotionRule.target_designation).all()

    if selected_rule_id:
        rule = db.query(PromotionRule).get(int(selected_rule_id))
        if rule:
            as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
            assessment_result = evaluate_eligibility(teacher, rule, as_of_date=as_of_date, db_session=db)

    return render_template(
        'teacher/eligibility_simulator.html',
        teacher=teacher,
        rules=rules,
        assessment_result=assessment_result,
        selected_rule_id=int(selected_rule_id) if selected_rule_id else None,
        as_of_date_str=as_of_date_str
    )

@teacher_bp.route('/simulator/pdf/<int:rule_id>')
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def download_simulator_pdf(rule_id):
    req_teacher_id = request.args.get('teacher_id')
    if g.user.role in ('ADMIN', 'SUPERADMIN') and req_teacher_id:
        teacher = g.db.query(Teacher).get(int(req_teacher_id))
    else:
        teacher = get_current_teacher()

    if not teacher:
        flash("Teacher record not found for PDF generation.", "danger")
        return redirect(url_for('admin.promotion_assessment'))

    rule = g.db.query(PromotionRule).get(rule_id)
    if not rule:
        flash("Promotion rule not found.", "danger")
        return redirect(url_for('admin.promotion_assessment'))

    assessment_result = evaluate_eligibility(teacher, rule, as_of_date=date.today(), db_session=g.db)
    buffer = generate_eligibility_report_pdf(assessment_result)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Promotion_Eligibility_Report_{teacher.personnel_no}_{rule.rule_code}.pdf",
        mimetype="application/pdf"
    )

@teacher_bp.route('/promotion-readiness')
@role_required(['TEACHER', 'ADMIN', 'SUPERADMIN'])
def promotion_readiness():
    teacher = get_current_teacher()
    if not teacher:
        flash("Teacher record not found.", "warning")
        return redirect(url_for('teacher.dashboard'))
    
    db = g.db
    # Find promotion rules applicable to teacher's current cadre / grade
    rules = db.query(PromotionRule).filter(
        (PromotionRule.source_designation == teacher.current_designation) |
        (PromotionRule.source_bs == teacher.current_bs),
        PromotionRule.is_active == True
    ).order_by(PromotionRule.target_bs.asc(), PromotionRule.target_designation.asc()).all()

    if not rules:
        rules = db.query(PromotionRule).filter(PromotionRule.is_active == True).all()

    selected_rule_id = request.args.get('rule_id')
    selected_rule = None
    if selected_rule_id:
        try:
            selected_rule = db.query(PromotionRule).get(int(selected_rule_id))
        except Exception:
            selected_rule = None
    
    if not selected_rule and rules:
        selected_rule = rules[0]

    readiness = None
    if selected_rule:
        readiness = evaluate_eligibility(teacher, selected_rule, as_of_date=date.today(), db_session=db)

    return render_template(
        'teacher/promotion_readiness.html',
        teacher=teacher,
        rules=rules,
        selected_rule=selected_rule,
        readiness=readiness
    )

