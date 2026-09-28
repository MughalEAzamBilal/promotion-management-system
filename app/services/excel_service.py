import io
from datetime import datetime, date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import pandas as pd
from app.models.teacher import Teacher
from app.models.user import User
from app.models.service import ServiceHistory
from app.models.seniority import SeniorityRecord
from app.models.qualification import Qualification
from app.models.post import TeachingPost
from app.services.audit_service import log_audit
from app.services.qualifications_catalog import (
    QUALIFICATIONS_CATALOG,
    get_predefined_degrees_flat,
    is_degree_professional
)

GREEN_HEADER_FILL = PatternFill(start_color="0B6B3A", end_color="0B6B3A", fill_type="solid")
GOLD_HEADER_FILL = PatternFill(start_color="D4A72C", end_color="D4A72C", fill_type="solid")
WHITE_BOLD_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
DARK_BOLD_FONT = Font(name="Calibri", size=11, bold=True, color="17202A")
THIN_BORDER = Border(
    left=Side(style='thin', color='D3D3D3'),
    right=Side(style='thin', color='D3D3D3'),
    top=Side(style='thin', color='D3D3D3'),
    bottom=Side(style='thin', color='D3D3D3')
)

TEMPLATE_COLUMNS = [
    'Personnel_No', 'CNIC', 'Full_Name', 'Father_Name', 'Gender',
    'Date_of_Birth', 'Mobile', 'Email', 'District', 'Tehsil',
    'School_Name', 'School_EMIS', 'Current_Designation', 'Current_BS',
    'Current_Category', 'Appointment_Date', 'Joining_Date',
    'Regularization_Date', 'Current_Post_Date', 'Seniority_No'
]

SAMPLE_TEACHERS = [
    [
        '30987654', '35201-1234567-9', 'Muhammad Ahmad', 'Abdul Rehman', 'Male',
        '1985-04-15', '03001234567', 'ahmad@example.com', 'Lahore', 'Model Town',
        'Govt Central Model High School', '35210101', 'EST (Science)', '15',
        'Science', '2012-09-01', '2012-09-01', '2015-09-01', '2018-03-01', '142'
    ],
    [
        '30987655', '35201-7654321-1', 'Zahid Hussain', 'Ghulam Qadir', 'Male',
        '1988-11-20', '03007654321', 'zahid@example.com', 'Lahore', 'City',
        'Govt Muslim Model High School', '35210102', 'EST (Computer)', '15',
        'Computer', '2015-03-01', '2015-03-01', '2018-03-01', '2020-09-01', '158'
    ],
    [
        '30987656', '35202-9876543-3', 'Tahira Parveen', 'Muhammad Sharif', 'Female',
        '1982-08-10', '03009876543', 'tahira@example.com', 'Lahore', 'Cantt',
        'Govt Girls High School Cantt', '35210103', 'EST (English)', '15',
        'Arts', '2010-02-15', '2010-02-15', '2013-02-15', '2016-08-01', '125'
    ]
]

QUAL_COLUMNS = [
    'CNIC', 'Teacher_Name_Optional', 'Degree_Level', 'Degree_Name', 'Subject',
    'Major_Subject', 'Minor_Subject', 'Passing_Year', 'Marks_Obtained',
    'Total_Marks', 'Percentage', 'CGPA', 'Division', 'Board_University',
    'Is_Professional', 'Registration_No'
]

SAMPLE_QUALIFICATIONS = [
    # Teacher 1 (Muhammad Ahmad - Science)
    ['35201-1234567-9', 'Muhammad Ahmad', 'Matric', 'SSC (Science - Biology)', 'Biology', 'Biology', 'Physics', 2002, 790, 1050, 75.2, '', 'First', 'BISE Lahore', 'No', 'LHR-02-8871'],
    ['35201-1234567-9', 'Muhammad Ahmad', 'Intermediate', 'F.Sc (Pre-Medical)', 'Chemistry', 'Chemistry', 'Biology', 2004, 820, 1100, 74.5, '', 'First', 'BISE Lahore', 'No', 'LHR-04-1192'],
    ['35201-1234567-9', 'Muhammad Ahmad', 'Bachelor', 'B.Sc (Botany, Zoology, Chemistry)', 'Chemistry', 'Chemistry', 'Botany', 2007, 560, 800, 70.0, '', 'First', 'University of the Punjab (PU), Lahore', 'No', '05-pu-1928'],
    ['35201-1234567-9', 'Muhammad Ahmad', 'Master', 'M.Sc Chemistry', 'Chemistry', 'Organic Chemistry', 'Physical Chemistry', 2009, 850, 1200, 70.8, '', 'First', 'University of the Punjab (PU), Lahore', 'No', '07-pu-8821'],
    ['35201-1234567-9', 'Muhammad Ahmad', 'Professional Teaching', 'B.Ed (1.5 Years)', 'Science Pedagogy', 'Teaching of Science', 'Teaching of Chemistry', 2011, 680, 900, 75.5, '', 'First', 'University of Education (UE), Lahore', 'Yes', 'UE-10-9912'],

    # Teacher 2 (Zahid Hussain - Computer Science)
    ['35201-7654321-1', 'Zahid Hussain', 'Matric', 'SSC (Science - Computer)', 'Computer Science', 'Computer Science', 'Physics', 2006, 810, 1050, 77.1, '', 'First', 'BISE Gujranwala', 'No', 'GRW-06-3381'],
    ['35201-7654321-1', 'Zahid Hussain', 'Intermediate', 'ICS (Physics, Math, Computer)', 'Computer Science', 'Computer Science', 'Mathematics', 2008, 840, 1100, 76.3, '', 'First', 'BISE Gujranwala', 'No', 'GRW-08-9921'],
    ['35201-7654321-1', 'Zahid Hussain', 'BS-4Years', 'BS Computer Science', 'Computer Science', 'Software Engineering', 'Database Systems', 2012, 3.40, 4.0, 78.0, 3.40, 'First', 'Government College University (GCU), Lahore', 'No', 'GCU-08-1120'],
    ['35201-7654321-1', 'Zahid Hussain', 'Professional Teaching', 'B.Ed (1.5 Years)', 'Computer Pedagogy', 'Teaching of Computer Science', '', 2015, 650, 900, 72.2, '', 'First', 'Allama Iqbal Open University (AIOU), Islamabad', 'Yes', 'AIOU-14-5541'],

    # Teacher 3 (Tahira Parveen - Arts / English)
    ['35202-9876543-3', 'Tahira Parveen', 'Bachelor', 'B.A (English Literature, Pol Science)', 'English', 'English Literature', 'Political Science', 2008, 520, 800, 65.0, '', 'First', 'University of Sargodha (UOS)', 'No', 'UOS-06-4412'],
    ['35202-9876543-3', 'Tahira Parveen', 'Master', 'M.A English', 'English Literature', 'Postcolonial Literature', 'Drama', 2010, 640, 1000, 64.0, '', 'First', 'University of the Punjab (PU), Lahore', 'No', '08-pu-6621'],
    ['35202-9876543-3', 'Tahira Parveen', 'Professional Teaching', 'M.Ed (Master of Education)', 'Teacher Education', 'Curriculum Design', 'Classroom Assessment', 2013, 720, 1000, 72.0, '', 'First', 'University of Education (UE), Lahore', 'Yes', 'UE-12-3312']
]

def generate_excel_template(db_session=None):
    """
    Generates a multi-sheet official Excel workbook template:
    Sheet 1: Teachers_Data (biodata & service)
    Sheet 2: Qualifications (multi-teacher academic & professional qualifications linked by CNIC)
    Sheet 3: Predefined_Qualifications (80 statutory degrees & subjects from SED Rules 2014 & HEC)
    Sheet 4: Official Teaching Posts (scale, cadre, title, category reference)
    Sheet 5: Instructions & Rules (comprehensive user guide)
    """
    wb = openpyxl.Workbook()
    
    # 1. Teachers_Data Sheet
    ws_teachers = wb.active
    ws_teachers.title = "Teachers_Data"

    for col_idx, col_name in enumerate(TEMPLATE_COLUMNS, start=1):
        cell = ws_teachers.cell(row=1, column=col_idx, value=col_name)
        cell.fill = GREEN_HEADER_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws_teachers.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 20

    for row_idx, row_data in enumerate(SAMPLE_TEACHERS, start=2):
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_teachers.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # 2. Qualifications Sheet (Multi-Teacher)
    ws_quals = wb.create_sheet(title="Qualifications")
    for col_idx, col_name in enumerate(QUAL_COLUMNS, start=1):
        cell = ws_quals.cell(row=1, column=col_idx, value=col_name)
        cell.fill = GREEN_HEADER_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        col_w = 26 if col_name in ['Board_University', 'Degree_Name'] else (18 if col_name in ['Major_Subject', 'Minor_Subject'] else 16)
        ws_quals.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = col_w

    for row_idx, q_data in enumerate(SAMPLE_QUALIFICATIONS, start=2):
        for col_idx, val in enumerate(q_data, start=1):
            cell = ws_quals.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # 3. Predefined Qualifications Catalog Sheet (SED Service Rules 2014 & HEC)
    ws_predef = wb.create_sheet(title="Predefined_Qualifications")
    predef_headers = ["Degree Level", "Statutory Degree Name", "Authorized / Core Subjects", "Is Professional Teaching Degree"]
    for c_idx, h in enumerate(predef_headers, start=1):
        cell = ws_predef.cell(row=1, column=c_idx, value=h)
        cell.fill = GOLD_HEADER_FILL
        cell.font = DARK_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_predef.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = 30 if c_idx != 3 else 60

    flat_degrees = get_predefined_degrees_flat()
    for r_idx, deg in enumerate(flat_degrees, start=2):
        ws_predef.cell(row=r_idx, column=1, value=deg["degree_level"])
        ws_predef.cell(row=r_idx, column=2, value=deg["degree_name"])
        ws_predef.cell(row=r_idx, column=3, value=deg["subjects"])
        cell_prof = ws_predef.cell(row=r_idx, column=4, value=deg["is_professional"])
        if deg["is_professional"] == "Yes":
            cell_prof.font = Font(name="Calibri", size=10, bold=True, color="0B6B3A")

    # 4. Official Teaching Posts Reference Sheet
    ws_posts = wb.create_sheet(title="Official Teaching Posts")
    post_headers = ["Basic Scale", "Cadre", "Official Post Title", "Category"]
    for c_idx, h in enumerate(post_headers, start=1):
        cell = ws_posts.cell(row=1, column=c_idx, value=h)
        cell.fill = GREEN_HEADER_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_posts.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = 25

    posts_data = []
    try:
        active_db = db_session
        if not active_db:
            try:
                from app import get_db
                active_db = get_db()
            except Exception:
                active_db = None
        if active_db:
            posts = active_db.query(TeachingPost).filter(TeachingPost.is_active == True).order_by(
                TeachingPost.basic_scale.asc(), TeachingPost.display_order.asc(), TeachingPost.post_title.asc()
            ).all()
            for p in posts:
                posts_data.append((f"BS-{p.basic_scale}", p.cadre, p.post_title, p.category))
    except Exception:
        pass

    if not posts_data:
        posts_data = [
            ("BS-14", "Primary", "Primary School Teacher (PST)", "General"),
            ("BS-15", "Elementary", "Elementary School Teacher (EST) Science", "Science"),
            ("BS-15", "Elementary", "Elementary School Teacher (EST) Arts", "Arts"),
            ("BS-15", "Elementary", "Elementary School Teacher (EST) English", "Arts"),
            ("BS-15", "Elementary", "Elementary School Teacher (EST) Mathematics", "Science"),
            ("BS-15", "Elementary", "Elementary School Teacher (EST) Computer Science", "Computer"),
            ("BS-15", "Elementary", "Elementary School Teacher (EST) Arabic", "Oriental"),
            ("BS-15", "Elementary", "Elementary School Teacher (EST) PET", "Physical"),
            ("BS-16", "Secondary", "Secondary School Teacher (SST) Science", "Science"),
            ("BS-16", "Secondary", "Secondary School Teacher (SST) Arts", "Arts"),
            ("BS-16", "Secondary", "Secondary School Teacher (SST) Computer Science", "Computer"),
            ("BS-17", "Secondary / Higher", "Headmaster / Headmistress (HM)", "Administration"),
            ("BS-17", "Higher Secondary", "Subject Specialist (SS) Physics", "Science"),
            ("BS-17", "Higher Secondary", "Subject Specialist (SS) Chemistry", "Science"),
            ("BS-17", "Higher Secondary", "Subject Specialist (SS) Biology", "Science"),
            ("BS-17", "Higher Secondary", "Subject Specialist (SS) Mathematics", "Science"),
            ("BS-17", "Higher Secondary", "Subject Specialist (SS) English", "Arts"),
            ("BS-18", "Higher Secondary", "Senior Subject Specialist (SSS)", "Teaching"),
            ("BS-18", "Secondary / Higher", "Senior Headmaster / Senior Headmistress", "Administration"),
        ]

    for r_idx, (scale, cadre, title, cat) in enumerate(posts_data, start=2):
        ws_posts.cell(row=r_idx, column=1, value=scale)
        ws_posts.cell(row=r_idx, column=2, value=cadre)
        ws_posts.cell(row=r_idx, column=3, value=title)
        ws_posts.cell(row=r_idx, column=4, value=cat)

    # 5. Instructions & Rules Sheet
    ws_guide = wb.create_sheet(title="Instructions & Rules")
    instructions = [
        ("INSTRUCTION FOR MULTI-TEACHER & QUALIFICATIONS EXCEL UPLOAD", ""),
        ("1. Multi-Sheet Support", "The workbook contains 'Teachers_Data' for teacher profiles and 'Qualifications' for academic/professional degrees."),
        ("2. Multi-Teacher Qualifications", "In the 'Qualifications' sheet, add multiple rows for each teacher. Each qualification row MUST specify the Teacher's CNIC."),
        ("3. CNIC format", "Must be 13 digits with or without dashes e.g., 35201-1234567-1. It links degrees to the correct teacher record."),
        ("4. Degree Levels", "Allowed: Matric, Intermediate, Bachelor, BS-4Years, Master, M.Phil, PhD, Professional Teaching"),
        ("5. Professional Teaching Degrees", "B.Ed (1.5 / 2.5 / 4 Years), M.Ed, ADE, B.S.Ed, M.A Education, DPE, ATTC, Drawing Master. Mark 'Is_Professional' as Yes."),
        ("6. Predefined Reference", "Check the 'Predefined_Qualifications' sheet for all 80+ statutory degrees recognized under SED Service Rules 2014."),
        ("7. Date Formats", "Use YYYY-MM-DD (e.g. 2014-03-15)."),
        ("8. Upsert Mode", "Existing teachers and qualifications are updated without creating redundant duplicates."),
        ("9. Automatic Credentials", "Login accounts are automatically created for each teacher: username = CNIC, default password = Teacher@123.")
    ]
    for row_idx, (k, v) in enumerate(instructions, start=1):
        c1 = ws_guide.cell(row=row_idx, column=1, value=k)
        c2 = ws_guide.cell(row=row_idx, column=2, value=v)
        c1.font = DARK_BOLD_FONT if row_idx == 1 else Font(bold=True)
        ws_guide.column_dimensions['A'].width = 35
        ws_guide.column_dimensions['B'].width = 85

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generate_education_excel_template(db_session=None):
    """
    Generates a dedicated Excel workbook template specifically for Bulk Updating Education & Qualifications
    for multiple teachers at once.
    Sheet 1: Qualifications (standardized headers and multi-teacher sample data)
    Sheet 2: Predefined_Qualifications (80 statutory degrees & authorized subjects from SED Rules 2014 & HEC)
    Sheet 3: Teachers_Reference (active teachers list with Personnel No, CNIC, Name, Designation, District)
    Sheet 4: Instructions & Policies (statutory guidelines on degrees & criteria)
    """
    wb = openpyxl.Workbook()

    # 1. Qualifications Sheet (Multi-Teacher)
    ws_quals = wb.active
    ws_quals.title = "Qualifications"
    for col_idx, col_name in enumerate(QUAL_COLUMNS, start=1):
        cell = ws_quals.cell(row=1, column=col_idx, value=col_name)
        cell.fill = GREEN_HEADER_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        col_w = 26 if col_name in ['Board_University', 'Degree_Name'] else (18 if col_name in ['Major_Subject', 'Minor_Subject'] else 16)
        ws_quals.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = col_w

    sample_quals_to_use = SAMPLE_QUALIFICATIONS
    active_db = db_session
    if not active_db:
        try:
            from app import get_db
            active_db = get_db()
        except Exception:
            active_db = None

    if active_db:
        try:
            db_teachers = active_db.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.id.asc()).limit(3).all()
            if len(db_teachers) >= 1:
                t0 = db_teachers[0]
                t1 = db_teachers[1] if len(db_teachers) > 1 else db_teachers[0]
                t2 = db_teachers[2] if len(db_teachers) > 2 else db_teachers[0]
                sample_quals_to_use = [
                    # Teacher 1
                    [t0.cnic, t0.full_name, 'Matric', 'SSC (Science - Biology)', 'Biology', 'Biology', 'Physics', 2002, 790, 1050, 75.2, '', 'First', 'BISE Lahore', 'No', 'LHR-02-8871'],
                    [t0.cnic, t0.full_name, 'Intermediate', 'F.Sc (Pre-Medical)', 'Chemistry', 'Chemistry', 'Biology', 2004, 820, 1100, 74.5, '', 'First', 'BISE Lahore', 'No', 'LHR-04-1192'],
                    [t0.cnic, t0.full_name, 'Bachelor', 'B.Sc (Botany, Zoology, Chemistry)', 'Chemistry', 'Chemistry', 'Botany', 2007, 560, 800, 70.0, '', 'First', 'University of the Punjab (PU), Lahore', 'No', '05-pu-1928'],
                    [t0.cnic, t0.full_name, 'Master', 'M.Sc Chemistry', 'Chemistry', 'Organic Chemistry', 'Physical Chemistry', 2009, 850, 1200, 70.8, '', 'First', 'University of the Punjab (PU), Lahore', 'No', '07-pu-8821'],
                    [t0.cnic, t0.full_name, 'Professional Teaching', 'B.Ed (1.5 Years)', 'Science Pedagogy', 'Teaching of Science', 'Teaching of Chemistry', 2011, 680, 900, 75.5, '', 'First', 'University of Education (UE), Lahore', 'Yes', 'UE-10-9912'],
                    # Teacher 2
                    [t1.cnic, t1.full_name, 'Intermediate', 'ICS (Physics, Math, Computer)', 'Computer Science', 'Computer Science', 'Mathematics', 2008, 840, 1100, 76.3, '', 'First', 'BISE Gujranwala', 'No', 'GRW-08-9921'],
                    [t1.cnic, t1.full_name, 'BS-4Years', 'BS Computer Science', 'Computer Science', 'Software Engineering', 'Database Systems', 2012, 3.40, 4.0, 78.0, 3.40, 'First', 'Government College University (GCU), Lahore', 'No', 'GCU-08-1120'],
                    [t1.cnic, t1.full_name, 'Professional Teaching', 'B.Ed (1.5 Years)', 'Computer Pedagogy', 'Teaching of Computer Science', '', 2015, 650, 900, 72.2, '', 'First', 'Allama Iqbal Open University (AIOU), Islamabad', 'Yes', 'AIOU-14-5541'],
                    # Teacher 3
                    [t2.cnic, t2.full_name, 'Bachelor', 'B.A (English Literature, Pol Science)', 'English', 'English Literature', 'Political Science', 2008, 520, 800, 65.0, '', 'First', 'University of Sargodha (UOS)', 'No', 'UOS-06-4412'],
                    [t2.cnic, t2.full_name, 'Master', 'M.A English', 'English Literature', 'Postcolonial Literature', 'Drama', 2010, 640, 1000, 64.0, '', 'First', 'University of the Punjab (PU), Lahore', 'No', '08-pu-6621'],
                    [t2.cnic, t2.full_name, 'Professional Teaching', 'M.Ed (Master of Education)', 'Teacher Education', 'Curriculum Design', 'Classroom Assessment', 2013, 720, 1000, 72.0, '', 'First', 'University of Education (UE), Lahore', 'Yes', 'UE-12-3312']
                ]
        except Exception:
            sample_quals_to_use = SAMPLE_QUALIFICATIONS

    for row_idx, q_data in enumerate(sample_quals_to_use, start=2):
        for col_idx, val in enumerate(q_data, start=1):
            cell = ws_quals.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # 2. Predefined Qualifications Catalog Sheet (SED Service Rules 2014 & HEC)
    ws_predef = wb.create_sheet(title="Predefined_Qualifications")
    predef_headers = ["Degree Level", "Statutory Degree Name", "Authorized / Core Subjects", "Is Professional Teaching Degree"]
    for c_idx, h in enumerate(predef_headers, start=1):
        cell = ws_predef.cell(row=1, column=c_idx, value=h)
        cell.fill = GOLD_HEADER_FILL
        cell.font = DARK_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_predef.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = 30 if c_idx != 3 else 60

    flat_degrees = get_predefined_degrees_flat()
    for r_idx, deg in enumerate(flat_degrees, start=2):
        ws_predef.cell(row=r_idx, column=1, value=deg["degree_level"])
        ws_predef.cell(row=r_idx, column=2, value=deg["degree_name"])
        ws_predef.cell(row=r_idx, column=3, value=deg["subjects"])
        cell_prof = ws_predef.cell(row=r_idx, column=4, value=deg["is_professional"])
        if deg["is_professional"] == "Yes":
            cell_prof.font = Font(name="Calibri", size=10, bold=True, color="0B6B3A")

    # 3. Teachers_Reference Sheet (List of active teachers to copy CNIC from)
    ws_ref = wb.create_sheet(title="Teachers_Reference")
    ref_headers = ["Personnel No", "CNIC (Use in Qualifications)", "Full Name", "Current Designation", "Current BS", "District", "School Name"]
    for c_idx, h in enumerate(ref_headers, start=1):
        cell = ws_ref.cell(row=1, column=c_idx, value=h)
        cell.fill = GREEN_HEADER_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_ref.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = 22

    teachers_ref_rows = []
    try:
        active_db = db_session
        if not active_db:
            try:
                from app import get_db
                active_db = get_db()
            except Exception:
                active_db = None
        if active_db:
            t_list = active_db.query(Teacher).filter(Teacher.is_deleted == False).order_by(
                Teacher.district.asc(), Teacher.current_designation.asc(), Teacher.full_name.asc()
            ).limit(200).all()
            for t in t_list:
                teachers_ref_rows.append((
                    t.personnel_no or '', t.cnic or '', t.full_name or '',
                    t.current_designation or '', f"BS-{t.current_bs}", t.district or '', t.school_name or ''
                ))
    except Exception:
        pass

    if not teachers_ref_rows:
        for st in SAMPLE_TEACHERS:
            teachers_ref_rows.append((st[0], st[1], st[2], st[12], f"BS-{st[13]}", st[8], st[10]))

    for r_idx, t_data in enumerate(teachers_ref_rows, start=2):
        for c_idx, val in enumerate(t_data, start=1):
            cell = ws_ref.cell(row=r_idx, column=c_idx, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # 4. Instructions & Policies Sheet
    ws_guide = wb.create_sheet(title="Instructions & Policies")
    instructions = [
        ("INSTRUCTIONS FOR BULK UPDATING EDUCATION ACROSS MULTIPLE TEACHERS", ""),
        ("1. Linking by Teacher CNIC", "Every row in the 'Qualifications' sheet must have a valid Teacher CNIC (e.g., 35201-1234567-1). The CNIC links the qualification directly to that teacher's profile."),
        ("2. Multiple Degrees Per Teacher", "You can add as many degree rows for a single teacher as needed (e.g. Matric, F.Sc, B.Sc, M.Sc, B.Ed). Simply repeat the same CNIC for each degree."),
        ("3. Predefined Degrees & Subjects", "Refer to the 'Predefined_Qualifications' sheet for the statutory names recognized under the SED Service Rules 2014 & HEC."),
        ("4. Professional Teaching Degrees", "Degrees like B.Ed (1.5, 2.5, 4 Years), M.Ed, ADE, B.S.Ed, M.A Education, DPE must have 'Is_Professional' marked as 'Yes'."),
        ("5. Upsert & Non-Duplication", "If a degree already exists for a teacher (matching teacher, degree title/level, and passing year), the system updates it instead of creating duplicates."),
        ("6. Easy CNIC Lookup", "Use the 'Teachers_Reference' sheet to easily find and copy the exact CNICs of existing teachers in the system."),
        ("7. Verification Status", "Newly uploaded qualifications are automatically queued for official administrative verification.")
    ]
    for row_idx, (k, v) in enumerate(instructions, start=1):
        c1 = ws_guide.cell(row=row_idx, column=1, value=k)
        c2 = ws_guide.cell(row=row_idx, column=2, value=v)
        c1.font = DARK_BOLD_FONT if row_idx == 1 else Font(bold=True)
        ws_guide.column_dimensions['A'].width = 35
        ws_guide.column_dimensions['B'].width = 85

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def parse_date(value):
    if not value or pd.isna(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    val_str = str(value).strip().split(' ')[0]
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
    return None

def normalize_cnic(cnic_raw):
    if not cnic_raw or pd.isna(cnic_raw):
        return None
    clean = str(cnic_raw).strip().replace('-', '').replace(' ', '')
    if len(clean) == 13 and clean.isdigit():
        return f"{clean[:5]}-{clean[5:12]}-{clean[12]}"
    return None

def get_row_val(row, aliases, default=''):
    """
    Extracts value from a pandas Series row matching any of the alias column names (case-insensitive, normalized).
    """
    for a in aliases:
        for col_name in row.index:
            clean_col = str(col_name).strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_')
            if clean_col == a.lower():
                val = row[col_name]
                if pd.notna(val):
                    val_str = str(val).strip()
                    if val_str and val_str.lower() != 'nan':
                        return val
    return default

def identify_sheets(xl):
    """
    Intelligently identifies teacher profile sheet and qualifications sheet
    based on sheet names and header column signatures.
    """
    sheet_names = [s.strip() for s in xl.sheet_names]
    teacher_sheet = None
    qual_sheet = None

    # Step 1: Check known sheet names
    for s in sheet_names:
        s_lower = s.lower()
        if s_lower in ['qualifications', 'teacher_qualifications', 'education', 'degrees', 'teacher_education']:
            qual_sheet = s
        elif 'qual' in s_lower or 'educat' in s_lower or 'degree' in s_lower:
            if not qual_sheet:
                qual_sheet = s

    for s in sheet_names:
        s_lower = s.lower()
        if s_lower in ['teachers_data', 'teachers', 'teacher_data', 'staff']:
            teacher_sheet = s
        elif 'teacher' in s_lower or 'staff' in s_lower:
            if not teacher_sheet and s != qual_sheet:
                teacher_sheet = s

    # Step 2: If sheets not uniquely identified, inspect columns of each sheet
    reference_sheets = ['Predefined_Qualifications', 'Official Teaching Posts', 'Instructions & Rules', 'Teachers_Reference', 'Instructions & Policies']
    for s in sheet_names:
        if s in reference_sheets or s == teacher_sheet or s == qual_sheet:
            continue
        try:
            df_head = xl.parse(s, nrows=1)
            cols = [str(c).strip().lower().replace(' ', '_') for c in df_head.columns]
            
            is_qual_sig = any(k in cols for k in ['degree_name', 'degree_level', 'degree', 'qualification', 'degree_certificate']) or \
                          (any(k in cols for k in ['subject', 'major_subject']) and any(k in cols for k in ['passing_year', 'marks_obtained', 'board_university', 'is_professional']))
            
            is_teacher_sig = any(k in cols for k in ['current_designation', 'current_bs', 'school_name', 'appointment_date', 'personnel_no'])

            if is_qual_sig and not is_teacher_sig and not qual_sheet:
                qual_sheet = s
            elif is_teacher_sig and not is_qual_sig and not teacher_sheet:
                teacher_sheet = s
        except Exception:
            pass

    # Step 3: If single-sheet workbook and still not detected, inspect that sheet
    non_ref_sheets = [s for s in sheet_names if s not in reference_sheets]
    if len(non_ref_sheets) == 1 and not teacher_sheet and not qual_sheet:
        s = non_ref_sheets[0]
        try:
            df_head = xl.parse(s, nrows=1)
            cols = [str(c).strip().lower().replace(' ', '_') for c in df_head.columns]
            if any(k in cols for k in ['degree_name', 'degree_level', 'degree', 'qualification', 'degree_certificate']) or 'subject' in cols:
                qual_sheet = s
            else:
                teacher_sheet = s
        except Exception:
            teacher_sheet = s

    return teacher_sheet, qual_sheet

def preview_excel_import(file_path, db_session):
    """
    Previews Excel file validation for both Teachers and Multi-Teacher Educational Qualifications.
    Supports single or multi-sheet workbooks, full import or qualifications-only import.
    """
    xl = None
    try:
        xl = pd.ExcelFile(file_path)
    except Exception as e:
        return {'success': False, 'error': f"Failed to read Excel file: {str(e)}"}

    teacher_sheet, qual_sheet = identify_sheets(xl)

    if not teacher_sheet and not qual_sheet:
        if xl:
            try:
                xl.close()
            except Exception:
                pass
        return {
            'success': False,
            'error': "No valid Teachers or Qualifications sheets found in the uploaded workbook. Please use the official template."
        }

    preview_rows = []
    errors = []
    seen_cnics = set()
    insert_count = 0
    update_count = 0
    df_teachers = None

    # Process Teachers Data
    if teacher_sheet:
        try:
            df_teachers = xl.parse(teacher_sheet)
            df_teachers.columns = [str(c).strip().replace(' ', '_') for c in df_teachers.columns]
        except Exception as e:
            errors.append(f"Error reading sheet '{teacher_sheet}': {str(e)}")

    if df_teachers is not None:
        missing_cols = [c for c in ['CNIC', 'Full_Name', 'District', 'Current_Designation', 'Current_BS'] if c not in df_teachers.columns]
        if missing_cols and not qual_sheet:
            if xl:
                try:
                    xl.close()
                except Exception:
                    pass
            return {
                'success': False,
                'error': f"Missing mandatory teacher columns in '{teacher_sheet}': {', '.join(missing_cols)}. Please use the official template."
            }

        if not missing_cols:
            for idx, row in df_teachers.iterrows():
                row_num = idx + 2
                cnic_raw = str(row.get('CNIC', '')).strip()
                pers_raw = str(row.get('Personnel_No', '')).strip()
                name = str(row.get('Full_Name', '')).strip()

                if not cnic_raw or cnic_raw.lower() == 'nan':
                    continue

                cnic_formatted = normalize_cnic(cnic_raw)
                if not cnic_formatted:
                    errors.append(f"Row {row_num} ({name}): CNIC '{cnic_raw}' is invalid (must be 13 digits).")
                    continue

                if cnic_formatted in seen_cnics:
                    errors.append(f"Row {row_num} ({name}): Duplicate CNIC '{cnic_formatted}' found within this sheet.")
                    continue
                seen_cnics.add(cnic_formatted)

                existing = db_session.query(Teacher).filter(Teacher.cnic == cnic_formatted).first()
                action = "UPDATE" if existing else "INSERT"
                if existing:
                    update_count += 1
                else:
                    insert_count += 1

                dob = parse_date(row.get('Date_of_Birth'))
                app_date = parse_date(row.get('Appointment_Date'))

                try:
                    bs = int(float(row.get('Current_BS', 14)))
                except (ValueError, TypeError):
                    bs = 14

                seniority_no = None
                try:
                    if not pd.isna(row.get('Seniority_No')):
                        seniority_no = int(float(row.get('Seniority_No')))
                except (ValueError, TypeError):
                    pass

                preview_rows.append({
                    'row_num': row_num,
                    'action': action,
                    'personnel_no': pers_raw,
                    'cnic': cnic_formatted,
                    'full_name': name,
                    'father_name': str(row.get('Father_Name', '')).strip(),
                    'district': str(row.get('District', '')).strip(),
                    'school_name': str(row.get('School_Name', '')).strip(),
                    'designation': str(row.get('Current_Designation', '')).strip(),
                    'bs': bs,
                    'appointment_date': app_date.strftime('%Y-%m-%d') if app_date else '',
                    'seniority_no': seniority_no
                })

    # 3. Process Qualifications Sheet (Multi-Teacher)
    preview_qualifications = []
    qual_insert_count = 0
    qual_update_count = 0
    total_qual_rows = 0
    teachers_with_quals_preview = set()

    if qual_sheet:
        try:
            df_qual = xl.parse(qual_sheet)
            total_qual_rows = len(df_qual)

            for idx, qrow in df_qual.iterrows():
                q_row_num = idx + 2
                q_cnic_raw = get_row_val(qrow, ['cnic', 'teacher_cnic', 'teachercnic', 't_cnic'], default='')
                if not q_cnic_raw or str(q_cnic_raw).lower() == 'nan':
                    continue

                q_cnic = normalize_cnic(q_cnic_raw)
                if not q_cnic:
                    errors.append(f"Qualifications Row {q_row_num}: Invalid CNIC '{q_cnic_raw}'.")
                    continue

                # Teacher should exist in DB or in the teachers preview
                teacher_in_db = db_session.query(Teacher).filter(Teacher.cnic == q_cnic).first()
                teacher_in_preview = q_cnic in seen_cnics

                if not teacher_in_db and not teacher_in_preview:
                    errors.append(f"Qualifications Row {q_row_num}: CNIC '{q_cnic}' is not in database or Teachers_Data sheet.")
                    continue

                deg_level = str(get_row_val(qrow, ['degree_level', 'level', 'degreelevel', 'qualification_level'], default='Bachelor')).strip()
                deg_name = str(get_row_val(qrow, ['degree_name', 'degree', 'qualification', 'degree_title', 'degree_certificate'], default='')).strip()
                subject = str(get_row_val(qrow, ['subject', 'major', 'discipline'], default='')).strip()

                if not deg_name and not subject:
                    continue

                pass_yr_raw = get_row_val(qrow, ['passing_year', 'year', 'completion_year', 'pass_year'], default=2015)
                try:
                    pass_yr = int(float(pass_yr_raw))
                except (ValueError, TypeError):
                    pass_yr = 2015

                is_prof_raw = str(get_row_val(qrow, ['is_professional', 'professional', 'is_professional_degree'], default='')).strip().lower()
                if is_prof_raw in ['yes', 'true', '1']:
                    is_prof = True
                elif is_prof_raw in ['no', 'false', '0']:
                    is_prof = False
                else:
                    is_prof = is_degree_professional(deg_name, deg_level)

                # Check if already in DB for this teacher
                existing_q = None
                if teacher_in_db:
                    existing_q = db_session.query(Qualification).filter(
                        Qualification.teacher_id == teacher_in_db.id,
                        (Qualification.degree_name == deg_name) | (Qualification.degree_level == deg_level),
                        Qualification.passing_year == pass_yr
                    ).first()

                q_action = "UPDATE" if existing_q else "INSERT"
                if existing_q:
                    qual_update_count += 1
                else:
                    qual_insert_count += 1

                teachers_with_quals_preview.add(q_cnic)

                teacher_disp_name = str(get_row_val(qrow, ['teacher_name_optional', 'teacher_name', 'name', 'full_name'], default=''))
                if not teacher_disp_name and teacher_in_db:
                    teacher_disp_name = teacher_in_db.full_name

                preview_qualifications.append({
                    'row_num': q_row_num,
                    'action': q_action,
                    'cnic': q_cnic,
                    'teacher_name': teacher_disp_name,
                    'degree_level': deg_level,
                    'degree_name': deg_name,
                    'subject': subject,
                    'passing_year': pass_yr,
                    'division': str(get_row_val(qrow, ['division', 'div', 'grade'], default='')).strip(),
                    'board_university': str(get_row_val(qrow, ['board_university', 'board', 'university', 'institute'], default='')).strip(),
                    'is_professional': is_prof
                })
        except Exception as e:
            errors.append(f"Error reading qualifications sheet: {str(e)}")

    valid_teachers = len(preview_rows)
    valid_quals = len(preview_qualifications)

    # If neither teacher rows nor qualifications rows were successfully parsed and errors exist
    if valid_teachers == 0 and valid_quals == 0 and errors:
        if xl:
            try:
                xl.close()
            except Exception:
                pass
        return {
            'success': False,
            'error': f"Validation failed: {errors[0]} (Total errors: {len(errors)})"
        }

    res = {
        'success': True,
        'total_rows': len(df_teachers) if df_teachers is not None else 0,
        'valid_count': valid_teachers,
        'insert_count': insert_count,
        'update_count': update_count,
        'error_count': len(errors),
        'errors': errors,
        'preview_rows': preview_rows[:50],

        # Qualification Specific Metrics
        'has_qualifications': bool(qual_sheet and valid_quals > 0),
        'total_qual_rows': total_qual_rows,
        'valid_qual_count': valid_quals,
        'insert_qual_count': qual_insert_count,
        'update_qual_count': qual_update_count,
        'teachers_with_quals_count': len(teachers_with_quals_preview),
        'preview_qualifications': preview_qualifications[:50]
    }
    if xl:
        try:
            xl.close()
        except Exception:
            pass
    return res

def execute_excel_import(file_path, db_session, update_existing=True, current_user=None, ip_address=None):
    """
    Executes database synchronization of both Teachers and Multi-Teacher Qualifications.
    Ensures complete relational consistency with user accounts, service histories, and seniority.
    Supports importing only qualifications or both teachers and qualifications.
    """
    xl = None
    try:
        xl = pd.ExcelFile(file_path)
    except Exception as e:
        return {'success': False, 'error': f"Failed to load Excel workbook: {str(e)}"}

    teacher_sheet, qual_sheet = identify_sheets(xl)

    imported_count = 0
    updated_count = 0
    accounts_created_count = 0
    qual_imported_count = 0
    qual_updated_count = 0
    teachers_with_quals_set = set()
    errors = []
    cnic_to_teacher_id = {}

    try:
        # 1. PROCESS TEACHERS DATA
        if teacher_sheet:
            df_teachers = xl.parse(teacher_sheet)
            df_teachers.columns = [str(c).strip().replace(' ', '_') for c in df_teachers.columns]

            for idx, row in df_teachers.iterrows():
                cnic_raw = str(row.get('CNIC', '')).strip()
                pers_raw = str(row.get('Personnel_No', '')).strip()
                name = str(row.get('Full_Name', '')).strip()

                if not cnic_raw or cnic_raw.lower() == 'nan':
                    continue

                cnic = normalize_cnic(cnic_raw)
                if not cnic:
                    continue

                dob = parse_date(row.get('Date_of_Birth')) or date(1985, 1, 1)
                app_date = parse_date(row.get('Appointment_Date'))
                if not app_date:
                    continue
                join_date = parse_date(row.get('Joining_Date')) or app_date
                reg_date = parse_date(row.get('Regularization_Date')) or join_date
                cur_post_date = parse_date(row.get('Current_Post_Date')) or join_date

                try:
                    bs = int(float(row.get('Current_BS', 14)))
                except (ValueError, TypeError):
                    bs = 14

                seniority_no = None
                try:
                    if not pd.isna(row.get('Seniority_No')):
                        seniority_no = int(float(row.get('Seniority_No')))
                except (ValueError, TypeError):
                    pass

                existing = db_session.query(Teacher).filter(Teacher.cnic == cnic).first()
                if existing:
                    cnic_to_teacher_id[cnic] = existing.id
                    if update_existing:
                        existing.personnel_no = pers_raw
                        existing.full_name = name
                        existing.father_name = str(row.get('Father_Name', existing.father_name)).strip()
                        existing.gender = str(row.get('Gender', existing.gender)).strip()
                        existing.date_of_birth = dob
                        existing.mobile = str(row.get('Mobile', existing.mobile or '')).strip()
                        existing.email = str(row.get('Email', existing.email or '')).strip()
                        existing.district = str(row.get('District', existing.district)).strip()
                        existing.tehsil = str(row.get('Tehsil', existing.tehsil)).strip()
                        existing.school_name = str(row.get('School_Name', existing.school_name)).strip()
                        existing.school_emis_code = str(row.get('School_EMIS', existing.school_emis_code or '')).strip()
                        existing.current_designation = str(row.get('Current_Designation', existing.current_designation)).strip()
                        existing.current_bs = bs
                        existing.current_category = str(row.get('Current_Category', existing.current_category or '')).strip()
                        existing.appointment_date = app_date
                        existing.joining_date = join_date
                        existing.regularization_date = reg_date
                        existing.current_post_date = cur_post_date
                        if seniority_no:
                            existing.seniority_no = seniority_no
                            existing.seniority_date = cur_post_date
                        updated_count += 1
                        teacher_obj = existing
                    else:
                        teacher_obj = existing
                else:
                    teacher_obj = Teacher(
                        personnel_no=pers_raw,
                        cnic=cnic,
                        full_name=name,
                        father_name=str(row.get('Father_Name', '')).strip(),
                        gender=str(row.get('Gender', 'Male')).strip(),
                        date_of_birth=dob,
                        mobile=str(row.get('Mobile', '')).strip(),
                        email=str(row.get('Email', '')).strip(),
                        district=str(row.get('District', '')).strip(),
                        tehsil=str(row.get('Tehsil', '')).strip(),
                        school_name=str(row.get('School_Name', '')).strip(),
                        school_emis_code=str(row.get('School_EMIS', '')).strip(),
                        current_designation=str(row.get('Current_Designation', 'PST')).strip(),
                        current_bs=bs,
                        current_category=str(row.get('Current_Category', 'General')).strip(),
                        appointment_date=app_date,
                        joining_date=join_date,
                        regularization_date=reg_date,
                        current_post_date=cur_post_date,
                        seniority_no=seniority_no,
                        seniority_date=cur_post_date if seniority_no else None,
                        verification_status='Pending'
                    )
                    db_session.add(teacher_obj)
                    db_session.flush()
                    cnic_to_teacher_id[cnic] = teacher_obj.id
                    imported_count += 1

                # Ensure User Account exists for this teacher
                user_account = db_session.query(User).filter(
                    (User.username == cnic) | (User.teacher_id == teacher_obj.id)
                ).first()
                if not user_account:
                    user_account = User(
                        teacher_id=teacher_obj.id,
                        username=cnic,
                        role='TEACHER',
                        full_name=name,
                        cnic=teacher_obj.cnic,
                        district=teacher_obj.district,
                        email=teacher_obj.email or '',
                        phone=teacher_obj.mobile or '',
                        is_active=True,
                        is_first_login=True
                    )
                    user_account.set_password('Teacher@123')
                    db_session.add(user_account)
                    accounts_created_count += 1
                else:
                    if not user_account.teacher_id:
                        user_account.teacher_id = teacher_obj.id
                    if not user_account.username:
                        user_account.username = cnic
                    if not user_account.cnic:
                        user_account.cnic = teacher_obj.cnic
                    if not user_account.district:
                        user_account.district = teacher_obj.district

                # Ensure initial ServiceHistory entry
                cur_service = db_session.query(ServiceHistory).filter(
                    ServiceHistory.teacher_id == teacher_obj.id,
                    ServiceHistory.is_current_post == True
                ).first()
                if not cur_service:
                    cur_service = ServiceHistory(
                        teacher_id=teacher_obj.id,
                        designation=teacher_obj.current_designation,
                        bs=teacher_obj.current_bs,
                        school_name=teacher_obj.school_name,
                        district=teacher_obj.district,
                        tehsil=teacher_obj.tehsil,
                        from_date=teacher_obj.current_post_date,
                        is_current_post=True,
                        appointment_type='Regular',
                        verification_status='Pending'
                    )
                    db_session.add(cur_service)

                # Ensure Seniority record if seniority_no is given
                if seniority_no:
                    sen_rec = db_session.query(SeniorityRecord).filter(
                        SeniorityRecord.teacher_id == teacher_obj.id
                    ).first()
                    if not sen_rec:
                        sen_rec = SeniorityRecord(
                            teacher_id=teacher_obj.id,
                            seniority_no=seniority_no,
                            seniority_date=teacher_obj.current_post_date,
                            designation=teacher_obj.current_designation,
                            bs=teacher_obj.current_bs,
                            district=teacher_obj.district,
                            seniority_list_reference=f"DEO/SEN/{teacher_obj.district}/2026",
                            seniority_list_date=date.today(),
                            is_official=True,
                            verified=False
                        )
                        db_session.add(sen_rec)

        # 2. PROCESS QUALIFICATIONS DATA (MULTIPLE TEACHERS AT ONCE)
        if qual_sheet:
            df_qual = xl.parse(qual_sheet)

            for idx, qrow in df_qual.iterrows():
                q_cnic_raw = get_row_val(qrow, ['cnic', 'teacher_cnic', 'teachercnic', 't_cnic'], default='')
                if not q_cnic_raw or str(q_cnic_raw).lower() == 'nan':
                    continue

                q_cnic = normalize_cnic(q_cnic_raw)
                if not q_cnic:
                    continue

                # Resolve Teacher ID
                target_teacher_id = cnic_to_teacher_id.get(q_cnic)
                if not target_teacher_id:
                    t_db = db_session.query(Teacher).filter(Teacher.cnic == q_cnic).first()
                    if t_db:
                        target_teacher_id = t_db.id
                        cnic_to_teacher_id[q_cnic] = t_db.id

                if not target_teacher_id:
                    continue

                deg_level = str(get_row_val(qrow, ['degree_level', 'level', 'degreelevel', 'qualification_level'], default='Bachelor')).strip()
                deg_name = str(get_row_val(qrow, ['degree_name', 'degree', 'qualification', 'degree_title', 'degree_certificate'], default='')).strip()
                subject = str(get_row_val(qrow, ['subject', 'major', 'discipline'], default='')).strip()
                major_subject = str(get_row_val(qrow, ['major_subject', 'major', 'specialization'], default='')).strip() or None
                minor_subject = str(get_row_val(qrow, ['minor_subject', 'minor'], default='')).strip() or None

                if not deg_name and not subject:
                    continue

                pass_yr_raw = get_row_val(qrow, ['passing_year', 'year', 'completion_year', 'pass_year'], default=2015)
                try:
                    pass_yr = int(float(pass_yr_raw))
                except (ValueError, TypeError):
                    pass_yr = 2015

                marks_obt = None
                try:
                    m_val = get_row_val(qrow, ['marks_obtained', 'obtained_marks', 'marks_obt', 'obtained', 'marks'], default=None)
                    if m_val is not None:
                        marks_obt = float(m_val)
                except (ValueError, TypeError):
                    pass

                tot_marks = None
                try:
                    tm_val = get_row_val(qrow, ['total_marks', 'max_marks', 'maximum_marks', 'totalmarks'], default=None)
                    if tm_val is not None:
                        tot_marks = float(tm_val)
                except (ValueError, TypeError):
                    pass

                pct = None
                try:
                    p_val = get_row_val(qrow, ['percentage', 'pct', 'percent', '_'], default=None)
                    if p_val is not None:
                        pct = float(p_val)
                    elif marks_obt is not None and tot_marks and tot_marks > 0:
                        pct = round((marks_obt / tot_marks) * 100, 2)
                except (ValueError, TypeError):
                    pass

                cgpa = None
                try:
                    c_val = get_row_val(qrow, ['cgpa', 'gpa'], default=None)
                    if c_val is not None:
                        cgpa = float(c_val)
                except (ValueError, TypeError):
                    pass

                division = str(get_row_val(qrow, ['division', 'div', 'grade'], default='')).strip() or None
                if not division and pct is not None:
                    if pct >= 60.0:
                        division = "First"
                    elif pct >= 45.0:
                        division = "Second"
                    else:
                        division = "Third"

                board_uni = str(get_row_val(qrow, ['board_university', 'board', 'university', 'institute', 'institution'], default='BISE / HEC Recognized')).strip()
                reg_no = str(get_row_val(qrow, ['registration_no', 'registration_number', 'reg_no', 'roll_no'], default='')).strip() or None

                is_prof_raw = str(get_row_val(qrow, ['is_professional', 'professional', 'is_professional_degree'], default='')).strip().lower()
                if is_prof_raw in ['yes', 'true', '1']:
                    is_prof = True
                elif is_prof_raw in ['no', 'false', '0']:
                    is_prof = False
                else:
                    is_prof = is_degree_professional(deg_name, deg_level)

                # Deduplication / Upsert by teacher_id + degree_name + passing_year
                existing_q = db_session.query(Qualification).filter(
                    Qualification.teacher_id == target_teacher_id,
                    (Qualification.degree_name == deg_name) | (Qualification.degree_level == deg_level),
                    Qualification.passing_year == pass_yr
                ).first()

                if existing_q:
                    if update_existing:
                        existing_q.degree_level = deg_level
                        existing_q.degree_name = deg_name
                        existing_q.subject = subject
                        if major_subject: existing_q.major_subject = major_subject
                        if minor_subject: existing_q.minor_subject = minor_subject
                        if marks_obt is not None: existing_q.marks_obtained = marks_obt
                        if tot_marks is not None: existing_q.total_marks = tot_marks
                        if pct is not None: existing_q.percentage = pct
                        if cgpa is not None: existing_q.cgpa = cgpa
                        if division: existing_q.division = division
                        existing_q.board_university = board_uni
                        existing_q.professional_qualification = is_prof
                        if reg_no: existing_q.registration_number = reg_no
                        existing_q.updated_at = datetime.utcnow()
                        qual_updated_count += 1
                        teachers_with_quals_set.add(target_teacher_id)
                else:
                    new_q = Qualification(
                        teacher_id=target_teacher_id,
                        degree_level=deg_level,
                        degree_name=deg_name,
                        subject=subject,
                        major_subject=major_subject,
                        minor_subject=minor_subject,
                        division=division,
                        marks_obtained=marks_obt,
                        total_marks=tot_marks,
                        percentage=pct,
                        cgpa=cgpa,
                        passing_year=pass_yr,
                        board_university=board_uni,
                        professional_qualification=is_prof,
                        registration_number=reg_no,
                        verification_status='Pending'
                    )
                    db_session.add(new_q)
                    qual_imported_count += 1
                    teachers_with_quals_set.add(target_teacher_id)

        db_session.commit()

        details_msg = f"Imported {imported_count} new teachers, updated {updated_count} teachers."
        if qual_imported_count or qual_updated_count:
            details_msg += f" Synchronized {qual_imported_count + qual_updated_count} qualifications across {len(teachers_with_quals_set)} teachers."

        log_audit(
            db_session, current_user, 'EXCEL_IMPORT',
            entity_type='Teacher',
            details=details_msg,
            ip_address=ip_address
        )

        return {
            'success': True,
            'imported': imported_count,
            'updated': updated_count,
            'accounts_created': accounts_created_count,
            'qualifications_imported': qual_imported_count,
            'qualifications_updated': qual_updated_count,
            'teachers_with_quals': len(teachers_with_quals_set),
            'errors': errors
        }
    except Exception as e:
        db_session.rollback()
        return {'success': False, 'error': f"Transaction aborted due to error: {str(e)}"}
    finally:
        if xl:
            try:
                xl.close()
            except Exception:
                pass

def export_teachers_to_excel(teachers):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Teachers_Directory"

    headers = [
        'Sr.', 'Personnel No', 'CNIC', 'Full Name', 'Father Name', 'Gender',
        'DOB', 'District', 'Tehsil', 'School Name', 'Designation', 'BS',
        'Appointment Date', 'Regularization Date', 'Seniority Rank', 'Verification Status'
    ]

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill = GREEN_HEADER_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 18

    for row_idx, t in enumerate(teachers, start=2):
        row_vals = [
            row_idx - 1,
            t.personnel_no,
            t.cnic,
            t.full_name,
            t.father_name,
            t.gender,
            t.date_of_birth.strftime('%Y-%m-%d') if t.date_of_birth else '',
            t.district,
            t.tehsil,
            t.school_name,
            t.current_designation,
            t.current_bs,
            t.appointment_date.strftime('%Y-%m-%d') if t.appointment_date else '',
            t.regularization_date.strftime('%Y-%m-%d') if t.regularization_date else '',
            t.seniority_no or 'N/A',
            t.verification_status
        ]
        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="left" if col_idx not in (1, 12, 15) else "center")

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def export_promotion_list_to_excel(candidates_data, rule, district='Lahore'):
    """
    Exports a styled Excel spreadsheet containing all evaluated promotion candidates
    for a specific Target Promotion Post & Rule.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Promotion_{rule.target_designation[:15].replace(' ', '_')}"

    # Row 1: Main Title
    ws.merge_cells("A1:P1")
    t1 = ws.cell(row=1, column=1, value="SCHOOL EDUCATION DEPARTMENT")
    t1.fill = GREEN_HEADER_FILL
    t1.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    t1.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Row 2: Subtitle
    ws.merge_cells("A2:P2")
    t2 = ws.cell(row=2, column=1, value=f"OFFICIAL PROMOTION ELIGIBILITY & SELECTION ROLL: {rule.target_designation} (BS-{rule.target_bs}) - DISTRICT {district.upper()}")
    t2.fill = GOLD_HEADER_FILL
    t2.font = Font(name="Calibri", size=11, bold=True, color="17202A")
    t2.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    # Row 3: Rule Metadata
    ws.merge_cells("A3:P3")
    rule_source_name = rule.source.notification_no if rule.source else 'SOR-III(S&GAD)1-19/2004(P)'
    meta_str = f"Statutory Rule: {rule.rule_name} | Feeder: {rule.source_designation} (BS-{rule.source_bs}) | Quota: {rule.quota_percentage}% | Ref: {rule_source_name} | Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    t3 = ws.cell(row=3, column=1, value=meta_str)
    t3.font = Font(name="Calibri", size=9, italic=True, color="555555")
    t3.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 18

    # Row 5: Column Headers
    headers = [
        'Sen #', 'Personnel No', 'CNIC', 'Teacher Name', 'Father Name',
        'School Name', 'District', 'Current Post', 'Regular Service (Yrs)',
        'Academic Qualification', 'Professional Qualification',
        'Engine Status', 'Committee Decision', 'Official Reason',
        'Statutory Rule Reference', 'Decided By / Date'
    ]

    ws.row_dimensions[5].height = 24
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=5, column=col_idx, value=h)
        cell.fill = GREEN_HEADER_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER

    # Column widths
    col_widths = {
        1: 8, 2: 14, 3: 18, 4: 22, 5: 20,
        6: 28, 7: 12, 8: 16, 9: 14,
        10: 25, 11: 20, 12: 18, 13: 16,
        14: 35, 15: 35, 16: 18
    }
    for c_idx, width in col_widths.items():
        ws.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = width

    # Data Rows
    for row_idx, c in enumerate(candidates_data, start=6):
        ws.row_dimensions[row_idx].height = 22
        dec = c.get('committee_decision', 'Pending Review')
        eng_stat = c.get('overall_status', 'Pending')
        dec_by_date = f"{c.get('decided_by') or ''} {c.get('decided_at') or ''}".strip()

        row_vals = [
            c.get('seniority_no') or (row_idx - 5),
            c.get('personnel_no'),
            c.get('cnic'),
            c.get('teacher_name'),
            c.get('father_name', ''),
            c.get('school_name', ''),
            c.get('district', district),
            c.get('current_post', ''),
            c.get('service_actual_years', 0.0),
            c.get('matched_academic_degree', 'N/A'),
            c.get('matched_professional_degree', 'N/A'),
            eng_stat,
            dec,
            c.get('decision_reason', '') or c.get('default_reason', ''),
            c.get('statutory_reference', ''),
            dec_by_date
        ]

        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER
            
            # Format and styling
            if col_idx in (1, 2, 3, 7, 9, 12, 13):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            # Highlight decision
            if col_idx == 13:
                if val == 'Promoted':
                    cell.font = Font(name="Calibri", size=10, bold=True, color="0B6B3A")
                elif val == 'Rejected':
                    cell.font = Font(name="Calibri", size=10, bold=True, color="C0392B")
                elif val == 'Deferred':
                    cell.font = Font(name="Calibri", size=10, bold=True, color="D4AC0D")

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

