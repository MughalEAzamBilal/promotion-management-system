import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

PUNJAB_GREEN = colors.HexColor('#0B6B3A')
PUNJAB_DARK = colors.HexColor('#064E2A')
PUNJAB_GOLD = colors.HexColor('#D4A72C')
LIGHT_GREY = colors.HexColor('#F8F9FA')
TABLE_HEADER_BG = colors.HexColor('#E5E7EB')
BORDER_COLOR = colors.HexColor('#CCCCCC')
TEXT_BLACK = colors.black

def build_pdf_styles():
    styles = getSampleStyleSheet()
    # Authority / Department Header - Page aligned text center, color black
    styles.add(ParagraphStyle(
        name='GovHeader',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=TEXT_BLACK,
        alignment=1 # Center
    ))
    # Sub-Header / Wing - Page aligned text center, color black
    styles.add(ParagraphStyle(
        name='GovSubHeader',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=TEXT_BLACK,
        alignment=1 # Center
    ))
    # Portal Title Banner - Page aligned text center
    styles.add(ParagraphStyle(
        name='PortalBanner',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=TEXT_BLACK,
        alignment=1 # Center
    ))
    # Other remaining text - Aligned text left
    styles.add(ParagraphStyle(
        name='MetaLeft',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=TEXT_BLACK,
        alignment=0 # Left
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=TEXT_BLACK,
        spaceAfter=6,
        alignment=0
    ))
    styles.add(ParagraphStyle(
        name='BodySmall',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#222222'),
        alignment=0
    ))
    styles.add(ParagraphStyle(
        name='BodySmallBold',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=TEXT_BLACK,
        alignment=0
    ))
    # Table header bold black text
    styles.add(ParagraphStyle(
        name='TableHeaderBold',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=TEXT_BLACK,
        alignment=0
    ))
    styles.add(ParagraphStyle(
        name='DisclaimerText',
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#444444'),
        alignment=0
    ))
    return styles

def get_pdf_settings():
    """Retrieves active PDF settings or returns statutory defaults."""
    try:
        from app.models.pdf_setting import PdfSetting
        from app import db_session
        s = db_session.query(PdfSetting).first()
        if s:
            return s
    except Exception:
        pass
    class DefaultSetting:
        gov_header = 'GOVERNMENT OF THE PUNJAB'
        dept_header = 'SCHOOL EDUCATION DEPARTMENT'
        portal_title = 'TEACHER PROMOTION PORTAL'
        is_stamp_enabled = True
        stamp_text = 'OFFICIAL SEAL * DISTRICT EDUCATION AUTHORITY'
        stamp_shape = 'Round'
        stamp_color = '#0B6B3A'
        authority_1_title = 'Member 1 / DEO (SE/EE)'
        authority_1_dept = 'District Promotion Committee'
        authority_2_title = 'Member 2 / Deputy Director'
        authority_2_dept = 'School Education Department'
        authority_3_title = 'Chairman / Chief Executive Officer'
        authority_3_dept = 'District Education Authority (DEA)'
        signatories = [
            {"title": "Member 1 / DEO (SE/EE)", "dept": "District Promotion Committee", "name": ""},
            {"title": "Member 2 / Deputy Director", "dept": "School Education Department", "name": ""},
            {"title": "Chairman / Chief Executive Officer", "dept": "District Education Authority (DEA)", "name": ""}
        ]
        legal_disclaimer = 'Issued under the School Education Department Service Rules 2014 as amended. Certified official record.'
    return DefaultSetting()

def build_official_signatures_block(styles, landscape_mode=True):
    """Constructs dynamic customizable signatories block and optional authentic stamp seal."""
    setting = get_pdf_settings()
    total_w = 780 if landscape_mode else 520
    is_stamp_enabled = getattr(setting, 'is_stamp_enabled', True)
    shape = getattr(setting, 'stamp_shape', 'Round')
    color = getattr(setting, 'stamp_color', '#0B6B3A')
    seal_txt = getattr(setting, 'stamp_text', 'OFFICIAL SEAL')
    
    # Get customizable signatories list
    signatories = getattr(setting, 'signatories', None)
    if not signatories or not isinstance(signatories, list):
        signatories = [
            {"title": getattr(setting, 'authority_1_title', 'Member 1 / DEO'), "dept": getattr(setting, 'authority_1_dept', 'District Promotion Committee'), "name": ""},
            {"title": getattr(setting, 'authority_2_title', 'Member 2 / Deputy Director'), "dept": getattr(setting, 'authority_2_dept', 'School Education Department'), "name": ""},
            {"title": getattr(setting, 'authority_3_title', 'Chairman / CEO (DEA)'), "dept": getattr(setting, 'authority_3_dept', 'District Education Authority'), "name": ""}
        ]

    shape_tag = f"({shape.upper()} STAMP)" if shape == 'Round' else (f"<{shape.upper()} STAMP>" if shape == 'Oval' else f"[{shape.upper()} STAMP]")
    
    stamp_cell = None
    if is_stamp_enabled:
        stamp_cell = Paragraph(
            f"<font size=7 color='{color}'><b>{shape_tag}</b><br/>"
            f"<b>{seal_txt}</b><br/>"
            f"School Education Department<br/>"
            f"Official Document Verification &bull; Certified Authenticated</font>",
            styles['BodySmall']
        )

    # Build signature columns
    sig_cells = []
    for s in signatories:
        title = s.get('title', 'Member')
        dept = s.get('dept', '')
        name = s.get('name', '')
        name_str = f"<b>{name}</b><br/>" if name else ""
        cell = Paragraph(
            f"____________________________<br/>"
            f"{name_str}<b>{title}</b><br/>"
            f"<font size=7 color='#555555'>{dept}</font>",
            styles['BodySmall']
        )
        sig_cells.append(cell)

    # Determine table columns
    row = []
    col_widths = []
    
    if is_stamp_enabled and stamp_cell:
        # Place stamp in middle
        mid = len(sig_cells) // 2
        for idx, sc in enumerate(sig_cells):
            if idx == mid:
                row.append(stamp_cell)
            row.append(sc)
        if len(sig_cells) == 0:
            row.append(stamp_cell)
            
        num_cols = len(row)
        stamp_idx = row.index(stamp_cell)
        stamp_w = total_w * 0.24
        member_w = (total_w - stamp_w) / max(1, num_cols - 1)
        for i in range(num_cols):
            col_widths.append(stamp_w if i == stamp_idx else member_w)
    else:
        row = sig_cells
        num_cols = max(1, len(row))
        w = total_w / num_cols
        col_widths = [w] * num_cols

    t_sig = Table([row], colWidths=col_widths)
    table_styles = [
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]
    if is_stamp_enabled and stamp_cell:
        s_idx = row.index(stamp_cell)
        table_styles.append(('BOX', (s_idx, 0), (s_idx, 0), 1.2, colors.HexColor(color)))
        table_styles.append(('BACKGROUND', (s_idx, 0), (s_idx, 0), colors.HexColor('#F4FBF7')))

    t_sig.setStyle(TableStyle(table_styles))
    return t_sig

def generate_teacher_dossier_pdf(teacher):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = build_pdf_styles()
    story = []

    # Header - Authority (Center, Black), Sub-Header (Center, Black), Portal Title Banner (Center, Black)
    setting = get_pdf_settings()
    story.append(Paragraph(setting.gov_header, styles['GovHeader']))
    story.append(Paragraph(setting.dept_header, styles['GovSubHeader']))
    story.append(Paragraph(f"{setting.portal_title} &bull; TEACHER OFFICIAL SERVICE & PROMOTION DOSSIER", styles['PortalBanner']))
    meta_text = f"<b>Teacher:</b> {teacher.full_name} &bull; <b>CNIC:</b> {teacher.cnic} &bull; <b>District:</b> {teacher.district} &bull; <b>Generated:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    story.append(Paragraph(meta_text, styles['MetaLeft']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#333333'), spaceBefore=4, spaceAfter=10))

    # Basic Info Table
    story.append(Paragraph("1. PERSONAL & DEMOGRAPHIC PROFILE", styles['SectionTitle']))
    personal_data = [
        [Paragraph("<b>Full Name:</b>", styles['BodySmall']), Paragraph(teacher.full_name, styles['BodySmall']),
         Paragraph("<b>Father Name:</b>", styles['BodySmall']), Paragraph(teacher.father_name, styles['BodySmall'])],
        [Paragraph("<b>CNIC:</b>", styles['BodySmall']), Paragraph(teacher.cnic, styles['BodySmall']),
         Paragraph("<b>Personnel No:</b>", styles['BodySmall']), Paragraph(teacher.personnel_no, styles['BodySmall'])],
        [Paragraph("<b>Gender:</b>", styles['BodySmall']), Paragraph(teacher.gender, styles['BodySmall']),
         Paragraph("<b>Date of Birth:</b>", styles['BodySmall']), Paragraph(teacher.date_of_birth.strftime('%d-%m-%Y') if teacher.date_of_birth else 'N/A', styles['BodySmall'])],
        [Paragraph("<b>Mobile:</b>", styles['BodySmall']), Paragraph(teacher.mobile or 'N/A', styles['BodySmall']),
         Paragraph("<b>Email:</b>", styles['BodySmall']), Paragraph(teacher.email or 'N/A', styles['BodySmall'])],
        [Paragraph("<b>District:</b>", styles['BodySmall']), Paragraph(teacher.district, styles['BodySmall']),
         Paragraph("<b>Tehsil:</b>", styles['BodySmall']), Paragraph(teacher.tehsil, styles['BodySmall'])],
        [Paragraph("<b>School:</b>", styles['BodySmall']), Paragraph(teacher.school_name, styles['BodySmall']),
         Paragraph("<b>EMIS Code:</b>", styles['BodySmall']), Paragraph(teacher.school_emis_code or 'N/A', styles['BodySmall'])]
    ]
    t_personal = Table(personal_data, colWidths=[110, 150, 110, 150])
    t_personal.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_GREY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_personal)
    story.append(Spacer(1, 14))

    # Current Posting & Seniority
    story.append(Paragraph("2. OFFICIAL POSTING & SENIORITY STATUS", styles['SectionTitle']))
    posting_data = [
        [Paragraph("<b>Current Designation:</b>", styles['BodySmall']), Paragraph(f"{teacher.current_designation} (BS-{teacher.current_bs})", styles['BodySmall']),
         Paragraph("<b>Cadre Category:</b>", styles['BodySmall']), Paragraph(teacher.current_category or 'General', styles['BodySmall'])],
        [Paragraph("<b>Govt Entry Date:</b>", styles['BodySmall']), Paragraph(teacher.appointment_date.strftime('%d-%m-%Y') if teacher.appointment_date else 'N/A', styles['BodySmall']),
         Paragraph("<b>Regularization Date:</b>", styles['BodySmall']), Paragraph(teacher.regularization_date.strftime('%d-%m-%Y') if teacher.regularization_date else 'N/A', styles['BodySmall'])],
        [Paragraph("<b>Current Post Date:</b>", styles['BodySmall']), Paragraph(teacher.current_post_date.strftime('%d-%m-%Y') if teacher.current_post_date else 'N/A', styles['BodySmall']),
         Paragraph("<b>Seniority Rank:</b>", styles['BodySmall']), Paragraph(f"#{teacher.seniority_no}" if teacher.seniority_no else 'Unassigned', styles['BodySmall'])],
        [Paragraph("<b>Profile Verification:</b>", styles['BodySmall']), Paragraph(f"<b>{teacher.verification_status}</b>", styles['BodySmall']),
         Paragraph("<b>Feeder Seniority:</b>", styles['BodySmall']), Paragraph(f"#{teacher.previous_seniority_no} ({teacher.previous_designation})" if teacher.previous_seniority_no else 'N/A (Direct/Initial Cadre)', styles['BodySmall'])],
        [Paragraph("<b>Disciplinary Status:</b>", styles['BodySmall']), Paragraph("Clear" if not teacher.disciplinary_inquiry_pending else "Inquiry Pending", styles['BodySmall']),
         Paragraph("<b>Cadre Status:</b>", styles['BodySmall']), Paragraph("Promoted Cadre (Max + 1)" if teacher.previous_seniority_no else "Regular Cadre", styles['BodySmall'])]
    ]
    t_posting = Table(posting_data, colWidths=[110, 150, 110, 150])
    t_posting.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_posting)
    story.append(Spacer(1, 14))

    # Qualifications Table
    story.append(Paragraph("3. RECORDED EDUCATIONAL & PROFESSIONAL QUALIFICATIONS", styles['SectionTitle']))
    qual_rows = [
        [Paragraph("<b>Degree</b>", styles['TableHeaderBold']),
         Paragraph("<b>Level</b>", styles['TableHeaderBold']),
         Paragraph("<b>Subject / Major</b>", styles['TableHeaderBold']),
         Paragraph("<b>Passing Year</b>", styles['TableHeaderBold']),
         Paragraph("<b>Board / University</b>", styles['TableHeaderBold']),
         Paragraph("<b>Status</b>", styles['TableHeaderBold'])]
    ]
    for q in (teacher.qualifications or []):
        qual_rows.append([
            Paragraph(q.degree_name, styles['BodySmall']),
            Paragraph(q.degree_level, styles['BodySmall']),
            Paragraph(f"{q.subject} ({q.division or 'Div'})", styles['BodySmall']),
            Paragraph(str(q.passing_year), styles['BodySmall']),
            Paragraph(q.board_university, styles['BodySmall']),
            Paragraph(q.verification_status, styles['BodySmall'])
        ])
    if len(qual_rows) == 1:
        qual_rows.append([Paragraph("No qualifications recorded yet.", styles['BodySmall']), "", "", "", "", ""])

    t_qual = Table(qual_rows, colWidths=[80, 80, 130, 60, 110, 60])
    t_qual.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0,0), (-1,0), TEXT_BLACK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_qual)
    story.append(Spacer(1, 16))

    # Official Disclaimer & Signature Block
    story.append(Paragraph("<b>OFFICIAL DECLARATION & DISCLAIMER:</b>", styles['BodySmallBold']))
    story.append(Paragraph(
        "This dossier has been generated from the official School Education Department Service, "
        "Seniority & Promotion Management System for record and promotion assessment purposes. "
        "All qualifications and service tenures are subject to departmental physical verification against original gazettes and service books.",
        styles['DisclaimerText']
    ))
    story.append(Spacer(1, 25))

    sig_data = [
        [Paragraph("____________________________<br/><b>Teacher's Signature</b>", styles['BodySmall']),
         Paragraph(f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles['BodySmall']),
         Paragraph("____________________________<br/><b>DEO / Authorized Officer</b>", styles['BodySmall'])]
    ]
    t_sig = Table(sig_data, colWidths=[170, 180, 170])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_sig)

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_eligibility_report_pdf(assessment):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = build_pdf_styles()
    story = []

    # Header - Authority (Center, Black), Sub-Header (Center, Black), Portal Title Banner (Center, Black)
    setting = get_pdf_settings()
    story.append(Paragraph(setting.gov_header, styles['GovHeader']))
    story.append(Paragraph(setting.dept_header, styles['GovSubHeader']))
    story.append(Paragraph(f"{setting.portal_title} &bull; PROMOTION ELIGIBILITY ASSESSMENT SHEET", styles['PortalBanner']))
    meta_text = f"<b>Candidate:</b> {assessment['teacher_name']} &bull; <b>Target Post:</b> {assessment['target_post']} &bull; <b>Evaluation Date:</b> {assessment['as_of_date']}"
    story.append(Paragraph(meta_text, styles['MetaLeft']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#333333'), spaceBefore=4, spaceAfter=8))

    # Candidate & Post Target Box
    status_color = PUNJAB_GREEN if assessment['overall_status'] == 'Eligible for Consideration' else (colors.HexColor('#F59E0B') if assessment['overall_status'] == 'Pending Verification' else colors.HexColor('#DC3545'))

    summary_data = [
        [Paragraph("<b>Candidate Name:</b>", styles['BodySmall']), Paragraph(assessment['teacher_name'], styles['BodySmall']),
         Paragraph("<b>Personnel / CNIC:</b>", styles['BodySmall']), Paragraph(f"{assessment['personnel_no']} / {assessment['cnic']}", styles['BodySmall'])],
        [Paragraph("<b>Feeder Post:</b>", styles['BodySmall']), Paragraph(assessment['current_post'], styles['BodySmall']),
         Paragraph("<b>Target Post:</b>", styles['BodySmall']), Paragraph(f"<b>{assessment['target_post']}</b>", styles['BodySmall'])],
        [Paragraph("<b>Rule Reference:</b>", styles['BodySmall']), Paragraph(f"{assessment['source_title']} ({assessment['notification_no']})", styles['BodySmall']),
         Paragraph("<b>Evaluation Date:</b>", styles['BodySmall']), Paragraph(assessment['as_of_date'], styles['BodySmall'])],
        [Paragraph("<b>OVERALL STATUS:</b>", styles['BodySmallBold']), Paragraph(f"<b>{assessment['overall_status'].upper()}</b>", styles['BodySmallBold']),
         Paragraph("<b>Service Years:</b>", styles['BodySmall']), Paragraph(f"{assessment['service_actual_years']} yrs (Req: {assessment['service_required_years']} yrs)", styles['BodySmall'])]
    ]
    t_summary = Table(summary_data, colWidths=[110, 160, 110, 140])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_GREY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TEXTCOLOR', (1,3), (1,3), status_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 14))

    # Condition by Condition Breakdown
    story.append(Paragraph("RULE CONDITIONS EVALUATION BREAKDOWN", styles['SectionTitle']))
    cond_rows = [
        [Paragraph("<b>Condition / Requirement</b>", styles['TableHeaderBold']),
         Paragraph("<b>Prescribed Rule</b>", styles['TableHeaderBold']),
         Paragraph("<b>Teacher's Recorded Record</b>", styles['TableHeaderBold']),
         Paragraph("<b>Status</b>", styles['TableHeaderBold'])]
    ]
    for c in assessment['conditions']:
        cond_rows.append([
            Paragraph(f"<b>{c['name']}</b><br/><font size=7 color='#666666'>{c['remarks']}</font>", styles['BodySmall']),
            Paragraph(c['required'], styles['BodySmall']),
            Paragraph(c['actual'], styles['BodySmall']),
            Paragraph(f"<b>{c['status']}</b>", styles['BodySmallBold'])
        ])

    t_cond = Table(cond_rows, colWidths=[150, 140, 150, 80])
    t_cond.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0,0), (-1,0), TEXT_BLACK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_cond)
    story.append(Spacer(1, 16))

    # Mandatory Legal Disclaimer
    story.append(Paragraph("<b>LEGAL DISCLAIMER & STATUTORY NOTICE:</b>", styles['BodySmallBold']))
    story.append(Paragraph(assessment['disclaimer'], styles['DisclaimerText']))
    story.append(Spacer(1, 25))

    # Sign-off
    story.append(KeepTogether([build_official_signatures_block(styles, landscape_mode=False)]))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_seniority_list_pdf(teachers, district, designation, bs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28
    )
    styles = build_pdf_styles()
    story = []

    # Header - Authority (Center, Black), Sub-Header (Center, Black), Portal Title Banner (Center, Black)
    setting = get_pdf_settings()
    story.append(Paragraph(setting.gov_header, styles['GovHeader']))
    story.append(Paragraph(setting.dept_header, styles['GovSubHeader']))
    story.append(Paragraph(f"{setting.portal_title} &bull; OFFICIAL SENIORITY LIST: {designation} (BS-{bs}) - DISTRICT {district.upper()}", styles['PortalBanner']))
    meta_text = f"<b>Published Date:</b> {datetime.now().strftime('%d-%m-%Y')} &bull; <b>Status:</b> Statutory Verified &bull; <b>Total Teachers:</b> {len(teachers)}"
    story.append(Paragraph(meta_text, styles['MetaLeft']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#333333'), spaceBefore=4, spaceAfter=8))

    rows = [
        [Paragraph("<b>Sr.#</b>", styles['TableHeaderBold']),
         Paragraph("<b>Personnel No</b>", styles['TableHeaderBold']),
         Paragraph("<b>Teacher Name & Father Name</b>", styles['TableHeaderBold']),
         Paragraph("<b>School Name & Tehsil</b>", styles['TableHeaderBold']),
         Paragraph("<b>DOB</b>", styles['TableHeaderBold']),
         Paragraph("<b>Regular Date</b>", styles['TableHeaderBold']),
         Paragraph("<b>Status</b>", styles['TableHeaderBold'])]
    ]

    for idx, t in enumerate(teachers, start=1):
        rows.append([
            Paragraph(f"<b>#{t.seniority_no or idx}</b>", styles['BodySmall']),
            Paragraph(t.personnel_no, styles['BodySmall']),
            Paragraph(f"<b>{t.full_name}</b><br/><font size=7 color='#555555'>S/O {t.father_name}</font>", styles['BodySmall']),
            Paragraph(f"{t.school_name}<br/><font size=7 color='#555555'>{t.tehsil}</font>", styles['BodySmall']),
            Paragraph(t.date_of_birth.strftime('%d-%m-%Y') if t.date_of_birth else '', styles['BodySmall']),
            Paragraph(t.regularization_date.strftime('%d-%m-%Y') if t.regularization_date else '', styles['BodySmall']),
            Paragraph(t.verification_status, styles['BodySmall'])
        ])

    t_list = Table(rows, colWidths=[40, 75, 140, 150, 65, 65, 65])
    t_list.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0,0), (-1,0), TEXT_BLACK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_list)
    story.append(Spacer(1, 15))
    story.append(KeepTogether([build_official_signatures_block(styles, landscape_mode=False)]))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_promotion_list_pdf(candidates_data, rule, district='Lahore'):
    """
    Generates an official Landscape Gazette PDF roll of candidates evaluated
    for promotion under a specific target promotion post and statutory rule.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24
    )
    styles = build_pdf_styles()
    setting = get_pdf_settings()
    story = []

    # Official Header - Authority (Center, Black), Sub-Header (Center, Black), Portal Title Banner (Center, Black)
    story.append(Paragraph(setting.gov_header, styles['GovHeader']))
    story.append(Paragraph(setting.dept_header, styles['GovSubHeader']))
    story.append(Paragraph(
        f"{setting.portal_title} &bull; OFFICIAL PROMOTION ELIGIBILITY & SELECTION ROLL: {rule.target_designation} (BS-{rule.target_bs}) - DISTRICT {district.upper()}",
        styles['PortalBanner']
    ))
    
    rule_source_name = rule.source.notification_no if rule.source else 'SOR-III(S&GAD)1-19/2004(P)'
    meta_text = (
        f"<b>Statutory Rule:</b> {rule.rule_name} &bull; "
        f"<b>Feeder Cadre:</b> {rule.source_designation} (BS-{rule.source_bs}) &bull; "
        f"<b>Quota:</b> {rule.quota_percentage}% Promotion &bull; "
        f"<b>Reference:</b> {rule_source_name} &bull; "
        f"<b>Date:</b> {datetime.now().strftime('%d-%m-%Y')}"
    )
    story.append(Paragraph(meta_text, styles['MetaLeft']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#333333'), spaceBefore=4, spaceAfter=8))

    # Table Header
    rows = [
        [
            Paragraph("<b>Sr/Sen#</b>", styles['TableHeaderBold']),
            Paragraph("<b>Teacher & CNIC</b>", styles['TableHeaderBold']),
            Paragraph("<b>School & Tehsil</b>", styles['TableHeaderBold']),
            Paragraph("<b>Regular Service</b>", styles['TableHeaderBold']),
            Paragraph("<b>Academic Degree & Subject</b>", styles['TableHeaderBold']),
            Paragraph("<b>Professional Qualification</b>", styles['TableHeaderBold']),
            Paragraph("<b>Engine Status</b>", styles['TableHeaderBold']),
            Paragraph("<b>Committee Decision</b>", styles['TableHeaderBold']),
            Paragraph("<b>Statutory Reason & Reference</b>", styles['TableHeaderBold'])
        ]
    ]

    for idx, c in enumerate(candidates_data, start=1):
        dec = c.get('committee_decision', 'Pending Review')
        if dec == 'Promoted':
            dec_html = f"<font color='#0B6B3A'><b>PROMOTED</b></font>"
        elif dec == 'Rejected':
            dec_html = f"<font color='#C0392B'><b>REJECTED</b></font>"
        elif dec == 'Deferred':
            dec_html = f"<font color='#D4AC0D'><b>DEFERRED</b></font>"
        else:
            dec_html = f"<font color='#7F8C8D'><b>Pending Review</b></font>"

        eng_status = c.get('overall_status', 'Pending')
        if eng_status == 'Eligible for Consideration':
            eng_html = "<font color='#0B6B3A'><b>Eligible</b></font>"
        elif eng_status == 'Ineligible':
            eng_html = "<font color='#C0392B'><b>Ineligible</b></font>"
        else:
            eng_html = "<font color='#E67E22'><b>Pending Scrutiny</b></font>"

        reason_text = c.get('decision_reason', '') or c.get('default_reason', '')
        ref_text = c.get('statutory_reference', '')
        combined_reason = f"<font size=7>{reason_text}<br/><b>Ref:</b> {ref_text}</font>"

        rows.append([
            Paragraph(f"<b>#{c.get('seniority_no') or idx}</b>", styles['BodySmall']),
            Paragraph(f"<b>{c.get('teacher_name')}</b><br/><font size=7 color='#555555'>{c.get('cnic')}<br/>Pers: {c.get('personnel_no')}</font>", styles['BodySmall']),
            Paragraph(f"<font size=8>{c.get('school_name', '')}</font>", styles['BodySmall']),
            Paragraph(f"<b>{c.get('service_actual_years', 0.0)} yrs</b><br/><font size=7 color='#555555'>Req: {c.get('service_required_years')}y</font>", styles['BodySmall']),
            Paragraph(f"<font size=8>{c.get('matched_academic_degree', 'N/A')}</font>", styles['BodySmall']),
            Paragraph(f"<font size=8>{c.get('matched_professional_degree', 'N/A')}</font>", styles['BodySmall']),
            Paragraph(eng_html, styles['BodySmall']),
            Paragraph(dec_html, styles['BodySmall']),
            Paragraph(combined_reason, styles['BodySmall'])
        ])

    col_widths = [45, 95, 100, 55, 110, 85, 75, 75, 155]
    t_roll = Table(rows, colWidths=col_widths, repeatRows=1)
    t_roll.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0,0), (-1,0), TEXT_BLACK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_roll)

    # Official Dynamic Signatures & Stamp Footer
    story.append(Spacer(1, 15))
    story.append(KeepTogether([build_official_signatures_block(styles, landscape_mode=True)]))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_retiring_teachers_pdf(teachers, dpc_meeting=None):
    """
    Generates an official Landscape Gazette PDF roll of teachers reaching
    statutory superannuation age (60 years) or officially retired.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24
    )
    styles = build_pdf_styles()
    setting = get_pdf_settings()
    story = []

    story.append(Paragraph(setting.gov_header, styles['GovHeader']))
    story.append(Paragraph(setting.dept_header, styles['GovSubHeader']))
    cutoff_text = f"AS OF DPC CUTOFF DATE: {dpc_meeting.meeting_date.strftime('%d-%m-%Y')}" if dpc_meeting else f"AS OF {datetime.now().strftime('%d-%m-%Y')}"
    story.append(Paragraph(
        f"{setting.portal_title} &bull; STATUTORY SUPERANNUATION & RETIRING TEACHERS ROLL ({cutoff_text})",
        styles['PortalBanner']
    ))
    meta_text = (
        f"<b>Statutory Basis:</b> Punjab Civil Servants Act 1974 Section 12 (Retirement on Superannuation at 60 Years) &bull; "
        f"<b>Total Count:</b> {len(teachers)} Teachers &bull; "
        f"<b>Generated:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    )
    story.append(Paragraph(meta_text, styles['MetaLeft']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#333333'), spaceBefore=4, spaceAfter=8))

    rows = [
        [
            Paragraph("<b>Sr.#</b>", styles['TableHeaderBold']),
            Paragraph("<b>Personnel & CNIC</b>", styles['TableHeaderBold']),
            Paragraph("<b>Teacher & Father Name</b>", styles['TableHeaderBold']),
            Paragraph("<b>Cadre & BS</b>", styles['TableHeaderBold']),
            Paragraph("<b>School & District</b>", styles['TableHeaderBold']),
            Paragraph("<b>Date of Birth</b>", styles['TableHeaderBold']),
            Paragraph("<b>Age (Yrs)</b>", styles['TableHeaderBold']),
            Paragraph("<b>Superannuation Date</b>", styles['TableHeaderBold']),
            Paragraph("<b>Status & Retirement Order</b>", styles['TableHeaderBold'])
        ]
    ]

    for idx, t in enumerate(teachers, start=1):
        sup_str = t.superannuation_date.strftime('%d-%m-%Y') if t.superannuation_date else 'N/A'
        order_str = t.retirement_order_no or (t.promotion_disable_reason or 'Superannuation Due')
        status_badge = "<font color='#C0392B'><b>Retired</b></font>" if t.account_status == 'Retired' else "<font color='#D4AC0D'><b>Age 60+ (Review)</b></font>"

        rows.append([
            Paragraph(f"<b>#{idx}</b>", styles['BodySmall']),
            Paragraph(f"<b>{t.personnel_no}</b><br/><font size=7 color='#555555'>{t.cnic}</font>", styles['BodySmall']),
            Paragraph(f"<b>{t.full_name}</b><br/><font size=7 color='#555555'>S/O {t.father_name}</font>", styles['BodySmall']),
            Paragraph(f"<b>{t.current_designation}</b><br/><font size=7 color='#555555'>BS-{t.current_bs}</font>", styles['BodySmall']),
            Paragraph(f"{t.school_name}<br/><font size=7 color='#555555'>{t.tehsil}, {t.district}</font>", styles['BodySmall']),
            Paragraph(t.date_of_birth.strftime('%d-%m-%Y') if t.date_of_birth else 'N/A', styles['BodySmall']),
            Paragraph(f"<b>{t.age} yrs</b>", styles['BodySmallBold']),
            Paragraph(f"<font color='#C0392B'><b>{sup_str}</b></font>", styles['BodySmall']),
            Paragraph(f"{status_badge}<br/><font size=7>{order_str}</font>", styles['BodySmall'])
        ])

    col_widths = [35, 95, 125, 95, 130, 65, 55, 80, 110]
    t_retire = Table(rows, colWidths=col_widths, repeatRows=1)
    t_retire.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0,0), (-1,0), TEXT_BLACK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_retire)

    # Official Dynamic Signatures & Stamp Footer
    story.append(Spacer(1, 15))
    story.append(KeepTogether([build_official_signatures_block(styles, landscape_mode=True)]))

    doc.build(story)
    buffer.seek(0)
    return buffer

