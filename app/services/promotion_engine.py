from datetime import date, datetime
import json
from app.models.rule import PromotionRule, RuleSource
from app.models.qualification import Qualification
from app.models.vacancy import Vacancy
from app.models.teacher import Teacher
from app.models.assessment import PromotionAssessment

DEGREE_HIERARCHY = {
    'Matric': 1,
    'Intermediate': 2,
    'Bachelor': 3,
    'BS-4Years': 4,
    'Master': 4,
    'M.Phil': 5,
    'PhD': 6
}

OFFICIAL_DISCLAIMER = (
    "This assessment is an informational eligibility evaluation based on official service rules "
    "(Punjab School Education Department Service Rules 2014 as amended). "
    "It does not constitute a promotion order or confer an automatic right of promotion, "
    "which remains subject to seniority, vacancy, fitness, and competent authority approval."
)

def calculate_service_years(from_date, as_of_date):
    """
    Calculates exact service years between two dates taking leap years into account.
    """
    if not from_date or not as_of_date or from_date > as_of_date:
        return 0.0
    
    # Calculate difference in days
    days = (as_of_date - from_date).days
    years = days / 365.25
    return round(years, 2)

def evaluate_eligibility(teacher, rule, as_of_date=None, db_session=None):
    """
    Evaluates a teacher's eligibility for promotion under a specific PromotionRule.
    Returns a comprehensive diagnostic dictionary with condition-by-condition breakdown.
    """
    if as_of_date is None:
        as_of_date = date.today()
    elif isinstance(as_of_date, str):
        as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

    conditions = []
    hard_failures = 0
    pending_items = 0
    warnings = 0

    # 0. Administrative Promotion Consideration Status & Statutory Superannuation (Age 60+)
    is_superannuated = False
    teacher_age_at_cutoff = 0
    if getattr(teacher, 'date_of_birth', None):
        dob = teacher.date_of_birth
        teacher_age_at_cutoff = as_of_date.year - dob.year - ((as_of_date.month, as_of_date.day) < (dob.month, dob.day))
        if teacher_age_at_cutoff >= 60:
            is_superannuated = True

    if getattr(teacher, 'account_status', '') == 'Retired':
        is_superannuated = True

    if getattr(teacher, 'is_promotion_disabled', False):
        hard_failures += 1
        conditions.append({
            'name': 'Promotion Consideration Status',
            'required': 'Active in Service (Eligible for Consideration)',
            'actual': f"Disabled: {teacher.promotion_disable_reason or 'Administrative Order'}",
            'status': 'FAIL',
            'remarks': f"Excluded from promotion consideration ({teacher.promotion_disable_reason or 'Administrative Exclusion'}). Remarks: {teacher.promotion_disable_remarks or 'None'}."
        })
    elif is_superannuated:
        hard_failures += 1
        conditions.append({
            'name': 'Statutory Superannuation / Age Limit',
            'required': 'Below Superannuation Age (< 60 Years as of DPC Date)',
            'actual': f"Superannuated: Age {teacher_age_at_cutoff} Years (>= 60 Years)",
            'status': 'FAIL',
            'remarks': f"Teacher attained age 60 (superannuation) on or before DPC cutoff date ({as_of_date.strftime('%d-%m-%Y')}). Ineligible for promotion under Punjab Civil Servants Act 1974 Section 12."
        })
    else:
        conditions.append({
            'name': 'Promotion Consideration Status',
            'required': 'Active in Service (Eligible for Consideration)',
            'actual': 'Active for Consideration',
            'status': 'PASS',
            'remarks': 'Teacher is active and eligible for departmental promotion scrutiny.'
        })

    # 1. Designation & Pay Scale Match
    src_designation = rule.source_designation.strip().upper()
    teacher_designation = (teacher.current_designation or '').strip().upper()
    
    # Check if teacher designation matches rule source
    designation_match = (src_designation in teacher_designation or teacher_designation in src_designation)
    scale_match = (teacher.current_bs == rule.source_bs)

    if designation_match and scale_match:
        conditions.append({
            'name': 'Source Designation & Pay Scale',
            'required': f"{rule.source_designation} (BS-{rule.source_bs})",
            'actual': f"{teacher.current_designation} (BS-{teacher.current_bs})",
            'status': 'PASS',
            'remarks': 'Teacher is currently serving in the feeder post for this promotion channel.'
        })
    else:
        hard_failures += 1
        conditions.append({
            'name': 'Source Designation & Pay Scale',
            'required': f"{rule.source_designation} (BS-{rule.source_bs})",
            'actual': f"{teacher.current_designation} (BS-{teacher.current_bs})",
            'status': 'FAIL',
            'remarks': 'Teacher current post does not match the feeder post required by this rule.'
        })

    # 2. Regular Service Length Calculation
    calc_start_date = teacher.regularization_date or teacher.current_post_date or teacher.appointment_date
    actual_service_years = calculate_service_years(calc_start_date, as_of_date)
    required_service_years = rule.min_regular_service_years or 0.0

    if required_service_years <= 0.0:
        conditions.append({
            'name': 'Regular Service in Present Cadre',
            'required': 'No specific minimum length prescribed (Seniority-cum-Fitness)',
            'actual': f"{actual_service_years} years regular service (since {calc_start_date.strftime('%d-%m-%Y') if calc_start_date else 'N/A'})",
            'status': 'PASS',
            'remarks': 'No specific minimum service prescribed under Service Rules 2014; promotion on Seniority-cum-Fitness basis.'
        })
    elif actual_service_years >= required_service_years:
        conditions.append({
            'name': 'Regular Service in Present Cadre',
            'required': f"{required_service_years} years regular service",
            'actual': f"{actual_service_years} years (since {calc_start_date.strftime('%d-%m-%Y') if calc_start_date else 'N/A'})",
            'status': 'PASS',
            'remarks': 'Teacher fulfills the minimum required regular service length.'
        })
    else:
        hard_failures += 1
        shortfall = round(required_service_years - actual_service_years, 2)
        conditions.append({
            'name': 'Regular Service in Present Cadre',
            'required': f"{required_service_years} years regular service",
            'actual': f"{actual_service_years} years (since {calc_start_date.strftime('%d-%m-%Y') if calc_start_date else 'N/A'})",
            'status': 'FAIL',
            'remarks': f"Service shortfall of {shortfall} years as of {as_of_date.strftime('%d-%m-%Y')}."
        })

    # 3. Academic Qualifications Check
    qualifications = teacher.qualifications or []
    req_level = rule.required_degree_level.strip()
    req_level_weight = DEGREE_HIERARCHY.get(req_level, 3)
    allowed_degrees = [d.strip().lower().replace('.', '') for d in rule.required_degree_names.split(',') if d.strip()]
    req_subjects = [s.strip().lower() for s in rule.required_subjects.split(',') if s.strip()]

    matched_academic = None
    for q in qualifications:
        if q.professional_qualification:
            continue
        q_weight = DEGREE_HIERARCHY.get(q.degree_level, 0)
        # Check level
        if q_weight >= req_level_weight:
            # Check degree name or general level equivalence
            deg_name_clean = q.degree_name.lower().replace('.', '')
            deg_matched = any(deg in deg_name_clean or deg_name_clean in deg for deg in allowed_degrees) or (len(allowed_degrees) == 0)
            
            # Check subject if specified
            subj_clean = (q.subject or '').lower()
            subj_matched = any(sub in subj_clean for sub in req_subjects) if req_subjects else True
            if req_subjects:
                is_match = deg_matched and subj_matched
            else:
                is_match = deg_matched
            
            if is_match:
                matched_academic = q
                break

    if matched_academic:
        is_verified = (matched_academic.verification_status == 'Verified')
        conditions.append({
            'name': 'Academic Qualification & Subject Match',
            'required': f"{rule.required_degree_level} ({rule.required_degree_names}) in {rule.required_subjects}",
            'actual': f"{matched_academic.degree_name} in {matched_academic.subject} ({matched_academic.passing_year}) - [{matched_academic.verification_status}]",
            'status': 'PASS' if is_verified else 'PENDING',
            'remarks': 'Relevant degree requirements satisfied.' if is_verified else 'Qualification matches rule but pending document verification by Admin.'
        })
        if not is_verified:
            pending_items += 1
    else:
        hard_failures += 1
        conditions.append({
            'name': 'Academic Qualification & Subject Match',
            'required': f"{rule.required_degree_level} ({rule.required_degree_names}) in {rule.required_subjects}",
            'actual': 'No matching academic qualification recorded',
            'status': 'FAIL',
            'remarks': f"Teacher records do not show the prescribed degree in {rule.required_subjects}."
        })

    # 4. Professional Qualification Check (B.Ed, M.Ed, ADE)
    req_prof = rule.required_professional_degree.strip()
    if req_prof and req_prof.upper() != 'NONE':
        allowed_profs = [p.strip().lower().replace('.', '') for p in req_prof.split(',') if p.strip()]
        matched_prof = None
        for q in qualifications:
            if q.professional_qualification or any(p in q.degree_name.lower().replace('.', '') for p in ['bed', 'med', 'ade', 'bsed']):
                matched_prof = q
                break

        if matched_prof:
            is_verified = (matched_prof.verification_status == 'Verified')
            conditions.append({
                'name': 'Professional Qualification',
                'required': rule.required_professional_degree,
                'actual': f"{matched_prof.degree_name} ({matched_prof.passing_year}) - [{matched_prof.verification_status}]",
                'status': 'PASS' if is_verified else 'PENDING',
                'remarks': 'Prescribed professional teaching degree present.' if is_verified else 'Professional qualification recorded but pending verification.'
            })
            if not is_verified:
                pending_items += 1
        else:
            hard_failures += 1
            conditions.append({
                'name': 'Professional Qualification',
                'required': rule.required_professional_degree,
                'actual': 'Not found in teacher profile',
                'status': 'FAIL',
                'remarks': f"Mandatory professional qualification ({rule.required_professional_degree}) missing."
            })
    else:
        conditions.append({
            'name': 'Professional Qualification',
            'required': 'None required',
            'actual': 'Exempt',
            'status': 'PASS',
            'remarks': 'No professional degree required for this category.'
        })

    # 5. Teacher Verification Status Check
    if teacher.verification_status == 'Verified':
        conditions.append({
            'name': 'Teacher Profile Verification',
            'required': 'Verified by Department Admin',
            'actual': 'Profile Verified',
            'status': 'PASS',
            'remarks': 'Teacher basic information and appointment orders verified.'
        })
    else:
        pending_items += 1
        conditions.append({
            'name': 'Teacher Profile Verification',
            'required': 'Verified by Department Admin',
            'actual': f"Status: {teacher.verification_status}",
            'status': 'PENDING',
            'remarks': 'Official profile is pending departmental administrative verification.'
        })

    # 6. Disciplinary Inquiry / Disqualification Check
    if teacher.disciplinary_inquiry_pending:
        hard_failures += 1
        conditions.append({
            'name': 'Disciplinary Inquiry / Clearance',
            'required': 'No disciplinary proceedings under PEEDA Act 2006',
            'actual': 'Disciplinary inquiry reported pending',
            'status': 'FAIL',
            'remarks': 'Promotion consideration deferred during pendency of formal disciplinary proceedings.'
        })
    else:
        conditions.append({
            'name': 'Disciplinary Inquiry / Clearance',
            'required': 'Clearance certificate / No inquiry pending',
            'actual': 'No disciplinary inquiry pending',
            'status': 'PASS',
            'remarks': 'Record is clear of disciplinary impediments.'
        })

    # 7. ACR / PER Performance Evaluation Check
    min_acr = rule.min_acr_score or 60.0
    actual_acr = teacher.acr_score_average or 0.0
    if actual_acr >= min_acr:
        conditions.append({
            'name': 'ACR / PER Performance Metric',
            'required': f"Minimum {min_acr}% satisfactory evaluations",
            'actual': f"{actual_acr}% score",
            'status': 'PASS',
            'remarks': 'Annual performance evaluation reports meet required threshold.'
        })
    else:
        hard_failures += 1
        conditions.append({
            'name': 'ACR / PER Performance Metric',
            'required': f"Minimum {min_acr}% satisfactory evaluations",
            'actual': f"{actual_acr}% score",
            'status': 'FAIL',
            'remarks': 'Performance evaluation reports fall below minimum prescribed benchmark.'
        })

    # 8. Vacancy & Promotion Quota Check (Informational / Seniority Zone)
    vacancy_info = "Not checked"
    if db_session:
        vac = db_session.query(Vacancy).filter(
            Vacancy.district == teacher.district,
            Vacancy.designation == rule.target_designation
        ).first()
        if vac:
            vac.calculate_vacancies()
            if vac.promotion_quota_posts > 0:
                is_in_zone = (teacher.seniority_no and teacher.seniority_no <= vac.promotion_quota_posts)
                conditions.append({
                    'name': 'District Promotion Vacancy & Seniority Zone',
                    'required': f"Available Quota Posts: {vac.promotion_quota_posts} in {teacher.district}",
                    'actual': f"Seniority Rank #{teacher.seniority_no or 'Unassigned'}",
                    'status': 'PASS' if is_in_zone else 'WARNING',
                    'remarks': 'Teacher is within the current seniority zone of promotion posts.' if is_in_zone else f"Teacher rank exceeds current promotional vacancies ({vac.promotion_quota_posts} posts)."
                })
                if not is_in_zone:
                    warnings += 1
            else:
                warnings += 1
                conditions.append({
                    'name': 'District Promotion Vacancy & Seniority Zone',
                    'required': f"Promotion quota posts in {teacher.district}",
                    'actual': '0 vacant promotion quota posts',
                    'status': 'WARNING',
                    'remarks': 'No sanctioned promotional vacancies currently available in district.'
                })

    # Determine Overall Official Status
    if hard_failures > 0:
        overall_status = 'Ineligible'
    elif pending_items > 0:
        overall_status = 'Pending Verification'
    else:
        overall_status = 'Eligible for Consideration'

    source_title = rule.source.title if rule.source else 'SED Service Rules 2014'
    notification_no = rule.source.notification_no if rule.source else 'SOR-III(S&GAD)1-19/2004(P)'
    notification_date = rule.source.notification_date.strftime('%d-%m-%Y') if (rule.source and rule.source.notification_date) else '14-03-2014'

    # Build default reason and statutory reference
    prof_deg_str = matched_prof.degree_name if ('matched_prof' in locals() and matched_prof) else 'B.Ed/ADE'
    if overall_status == 'Eligible for Consideration':
        service_text = f"Completed {actual_service_years} years regular service (min {required_service_years} req.)" if required_service_years > 0 else f"{actual_service_years} years regular service (No minimum service prescribed under Service Rules 2014; Seniority-cum-Fitness)"
        default_reason = (
            f"Eligible: {service_text}. "
            f"Holds verified {matched_academic.degree_name if matched_academic else 'degree'}, "
            f"verified professional qualification ({prof_deg_str}), "
            f"satisfactory ACR metric ({teacher.acr_score_average}%), and no disciplinary inquiries pending."
        )
    elif overall_status == 'Ineligible':
        fail_reasons = [c['remarks'] for c in conditions if c['status'] == 'FAIL']
        default_reason = "Ineligible: " + ("; ".join(fail_reasons) if fail_reasons else "Does not meet feeder cadre requirements.")
    else:
        pending_reasons = [c['remarks'] for c in conditions if c['status'] == 'PENDING']
        default_reason = "Pending Verification: " + ("; ".join(pending_reasons) if pending_reasons else "Record pending administrative scrutiny.")

    statutory_ref = f"{source_title}, Notification No. {notification_no} dated {notification_date}, Schedule II for post of {rule.target_designation} (BS-{rule.target_bs})."

    return {
        'teacher_id': teacher.id,
        'personnel_no': teacher.personnel_no,
        'teacher_name': teacher.full_name,
        'father_name': teacher.father_name,
        'cnic': teacher.cnic,
        'dob': teacher.date_of_birth.strftime('%d-%m-%Y') if teacher.date_of_birth else 'N/A',
        'district': teacher.district,
        'seniority_no': teacher.seniority_no,
        'school_name': teacher.school_name,
        'current_post': f"{teacher.current_designation} (BS-{teacher.current_bs})",
        'target_post': f"{rule.target_designation} (BS-{rule.target_bs})",
        'promotion_category': rule.promotion_category,
        'rule_id': rule.id,
        'rule_code': rule.rule_code,
        'rule_name': rule.rule_name,
        'source_title': source_title,
        'notification_no': notification_no,
        'notification_date': notification_date,
        'as_of_date': as_of_date.strftime('%d-%m-%Y'),
        'service_actual_years': actual_service_years,
        'service_required_years': required_service_years,
        'matched_academic_degree': f"{matched_academic.degree_name} in {matched_academic.subject} ({matched_academic.passing_year})" if matched_academic else "None",
        'matched_professional_degree': f"{matched_prof.degree_name} ({matched_prof.passing_year})" if ('matched_prof' in locals() and matched_prof) else ("Exempt" if (not rule.required_professional_degree or rule.required_professional_degree.upper() == 'NONE') else "Missing"),
        'hard_failures': hard_failures,
        'pending_items': pending_items,
        'warnings': warnings,
        'overall_status': overall_status,
        'default_reason': default_reason,
        'statutory_reference': statutory_ref,
        'is_promotion_disabled': getattr(teacher, 'is_promotion_disabled', False),
        'promotion_disable_reason': getattr(teacher, 'promotion_disable_reason', None),
        'promotion_disable_remarks': getattr(teacher, 'promotion_disable_remarks', None),
        'promotion_disabled_at': teacher.promotion_disabled_at.strftime('%d-%m-%Y %H:%M') if getattr(teacher, 'promotion_disabled_at', None) else None,
        'promotion_disabled_by': getattr(teacher, 'promotion_disabled_by', None),
        'disclaimer': OFFICIAL_DISCLAIMER,
        'conditions': conditions
    }

def evaluate_cadre_for_rule(db_session, rule, district=None, status_filter='all', as_of_date=None):
    """
    Evaluates all feeder cadre teachers for a given PromotionRule.
    Checks existing committee decisions if already assessed and saved.
    Ranks candidates strictly by Seniority-cum-Fitness (Official Seniority Number,
    with Date of Birth / greater age breaking exact ties).
    Evaluates statutory 2:1 DPC consideration panel zone.
    """
    if as_of_date is None:
        as_of_date = date.today()
    elif isinstance(as_of_date, str):
        as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

    query = db_session.query(Teacher).filter(
        Teacher.current_bs == rule.source_bs,
        Teacher.is_deleted == False
    )

    if district and district.lower() != 'all':
        query = query.filter(Teacher.district == district)

    # Order strictly by official civil service seniority, then age (DOB)
    teachers = query.order_by(
        Teacher.seniority_no.asc().nullslast(),
        Teacher.date_of_birth.asc()
    ).all()

    # Fetch district vacancies to calculate 2:1 consideration panel ratio
    vac = None
    if district and district.lower() != 'all':
        vac = db_session.query(Vacancy).filter(
            Vacancy.district == district,
            Vacancy.designation == rule.target_designation
        ).first()
        if vac:
            vac.calculate_vacancies()

    # Detect duplicate seniority numbers for tie annotations
    sen_counts = {}
    for t in teachers:
        if t.seniority_no is not None:
            sen_counts[t.seniority_no] = sen_counts.get(t.seniority_no, 0) + 1

    candidates = []
    for rank_idx, teacher in enumerate(teachers, 1):
        eval_res = evaluate_eligibility(teacher, rule, as_of_date=as_of_date, db_session=db_session)
        
        # Check for saved assessment / committee decision
        saved_ass = db_session.query(PromotionAssessment).filter(
            PromotionAssessment.teacher_id == teacher.id,
            PromotionAssessment.rule_id == rule.id
        ).order_by(PromotionAssessment.id.desc()).first()

        if saved_ass and saved_ass.committee_decision:
            committee_decision = saved_ass.committee_decision
            decision_reason = saved_ass.decision_reason or eval_res['default_reason']
            statutory_ref = saved_ass.statutory_reference or eval_res['statutory_reference']
            decided_by = saved_ass.decided_by or 'DPC'
            decided_at = saved_ass.decided_at.strftime('%d-%m-%Y %H:%M') if saved_ass.decided_at else None
            assessment_id = saved_ass.id
        else:
            committee_decision = 'Pending Review'
            decision_reason = eval_res['default_reason']
            statutory_ref = eval_res['statutory_reference']
            decided_by = None
            decided_at = None
            assessment_id = None

        # Seniority-cum-Fitness precedence & tie diagnostics
        is_tied = (teacher.seniority_no is not None and sen_counts.get(teacher.seniority_no, 0) > 1)
        if is_tied:
            seniority_note = (
                f"Seniority #{teacher.seniority_no} (Tie): Prioritized by Date of Birth / Greater Age "
                f"(Born {teacher.date_of_birth.strftime('%d-%m-%Y') if teacher.date_of_birth else 'N/A'}) per civil service practice."
            )
        else:
            seniority_note = (
                f"Seniority-cum-Fitness Rank #{rank_idx} (Seniority #{teacher.seniority_no or 'Unassigned'}): "
                f"Considered in strict order of seniority, subject to fitness and DPC recommendation."
            )

        # Statutory 2:1 consideration panel ratio zone calculation
        if vac and vac.promotion_quota_posts > 0:
            quota_posts = vac.promotion_quota_posts
            panel_limit = quota_posts * 2  # 2:1 ratio statutory panel
            if rank_idx <= quota_posts:
                panel_zone_badge = 'Within Primary Quota'
                panel_zone_class = 'bg-success'
                panel_zone_note = f"Rank #{rank_idx} is within the {quota_posts} promotional vacancies for {teacher.district}."
            elif rank_idx <= panel_limit:
                panel_zone_badge = 'Within DPC Panel (2:1 Ratio)'
                panel_zone_class = 'bg-primary'
                panel_zone_note = f"Rank #{rank_idx} is within the statutory 2:1 DPC consideration panel (top {panel_limit} officers for {quota_posts} posts)."
            else:
                panel_zone_badge = 'Beyond Panel Zone'
                panel_zone_class = 'bg-secondary'
                panel_zone_note = f"Rank #{rank_idx} is beyond the active 2:1 consideration panel for {quota_posts} posts."
        else:
            panel_zone_badge = 'Quota Pending'
            panel_zone_class = 'bg-light text-dark border'
            panel_zone_note = f"Promotion vacancies for {rule.target_designation} in {teacher.district} pending notification."

        candidate_data = {
            **eval_res,
            'cadre_rank': rank_idx,
            'is_seniority_tied': is_tied,
            'seniority_precedence_note': seniority_note,
            'panel_zone_badge': panel_zone_badge,
            'panel_zone_class': panel_zone_class,
            'panel_zone_note': panel_zone_note,
            'assessment_id': assessment_id,
            'committee_decision': committee_decision,
            'decision_reason': decision_reason,
            'statutory_reference': statutory_ref,
            'decided_by': decided_by,
            'decided_at': decided_at
        }

        # Status filter check
        if status_filter == 'eligible' and eval_res['overall_status'] != 'Eligible for Consideration':
            continue
        elif status_filter == 'promoted' and committee_decision != 'Promoted':
            continue
        elif status_filter == 'rejected' and committee_decision != 'Rejected' and eval_res['overall_status'] != 'Ineligible':
            continue
        elif status_filter == 'pending' and committee_decision != 'Pending Review':
            continue

        candidates.append(candidate_data)

    return candidates
