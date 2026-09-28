import os
from datetime import date, datetime
from app.models.user import User
from app.models.teacher import Teacher
from app.models.qualification import Qualification
from app.models.service import ServiceHistory
from app.models.seniority import SeniorityRecord

def get_100_teachers_data():
    """
    Returns a comprehensive dataset of 100 realistic Punjab School Education Department teachers.
    Covers:
    - 45 PSTs (BS-14)
    - 35 ESTs (BS-15: Science, Arts, English, Computer Science)
    - 20 SSTs (BS-16: Science, Arts, Computer Science)
    Across districts: Lahore, Rawalpindi, Faisalabad, Multan, Gujranwala.
    Scenarios include:
    - Equal eligibility with sequential seniority (#120 vs #121)
    - Exact seniority tie (#45 vs #45) with Date of Birth / Age precedence
    - Multi-category qualifications (B.Sc + B.A + B.Ed, BSCS + B.Ed, M.Sc + M.A + M.Ed)
    - Missing professional degree (B.Ed/ADE missing) -> Ineligible
    - Degree subject mismatch (B.Com/Sociology applying for Science) -> Ineligible
    - Pending disciplinary inquiry under PEEDA Act 2006 -> Ineligible/Deferred
    - Unsatisfactory ACR/PER evaluation metric (< 60%) -> Ineligible
    - Service shortfall for SST -> BS-17 (min 2.0 yrs regular service required)
    - Pending profile / document verification
    """
    first_names_m = [
        "Muhammad", "Tariq", "Bilal", "Rashid", "Khalid", "Farooq", "Usman", "Shahbaz",
        "Babar", "Naveed", "Salman", "Haris", "Zahid", "Akram", "Hamza", "Asif",
        "Imran", "Shahid", "Waseem", "Faisal", "Khurram", "Arslan", "Kamran", "Rizwan",
        "Adeel", "Sohail", "Nadeem", "Javed", "Irfan", "Nasir", "Tanveer", "Sajid",
        "Amjad", "Mansoor", "Waqas", "Adnan", "Zubair", "Atif", "Kashif", "Umair",
        "Saqib", "Mubeen", "Junaid", "Rehan", "Qasim", "Shoaib", "Noman", "Asad"
    ]
    first_names_f = [
        "Ayesha", "Saima", "Fatima", "Zainab", "Bushra", "Noreen", "Maryam", "Sadia",
        "Tahira", "Rukhsana", "Samina", "Shazia", "Kalsoom", "Farzana", "Nasreen", "Parveen",
        "Rabia", "Shaheen", "Humaira", "Uzma", "Asma", "Hina", "Saba", "Fariha"
    ]
    father_names = [
        "Abdul Majeed", "Muhammad Rafiq", "Karamat Ali", "Muhammad Akram", "Bashir Ahmed",
        "Abdul Rehman", "Nazir Hussain", "Ghulam Nabi", "Allah Ditta", "Muhammad Aslam",
        "Sultan Mehmood", "Muhammad Sharif", "Noor Muhammad", "Ghulam Qadir", "Abdul Sattar",
        "Muhammad Yousaf", "Riaz Ahmed", "Liaqat Ali", "Inayat Ullah", "Muhammad Siddique"
    ]
    districts_info = [
        ("Lahore", ["City", "Model Town", "Cantonment", "Shalimar", "Raiwind"]),
        ("Rawalpindi", ["Rawalpindi", "Gujar Khan", "Taxila", "Kahuta"]),
        ("Faisalabad", ["City", "Saddar", "Jaranwala", "Samundri"]),
        ("Multan", ["City", "Saddar", "Shujabad"]),
        ("Gujranwala", ["City", "Saddar", "Kamoke", "Wazirabad"])
    ]

    teachers = []

    # =========================================================================
    # 1 to 45: Primary School Teachers - PST (BS-14)
    # =========================================================================

    # T1: Seniority-cum-Fitness Test Candidate A (#120)
    teachers.append({
        'p_no': '30100001', 'cnic': '35201-1100001-1', 'name': 'Muhammad Tariq', 'fname': 'Abdul Majeed',
        'gender': 'Male', 'dob': date(1985, 4, 12), 'mobile': '03001100001', 'email': 'tariq.120@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Model Town', 'school': 'Govt Primary School Model Town Lahore', 'emis': '35210101',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2014, 3, 1), 'reg_date': date(2017, 3, 1),
        'cur_date': date(2017, 3, 1), 'sen_no': 120, 'verif': 'Verified', 'inquiry': False, 'acr': 86.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2001, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', 2003, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Physics, Chemistry, Mathematics', 'First', 2006, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Secondary Teacher Education', 'First', 2009, 'University of Education (UE), Lahore', True)
        ]
    })

    # T2: Seniority-cum-Fitness Test Candidate B (#121)
    teachers.append({
        'p_no': '30100002', 'cnic': '35201-1100002-1', 'name': 'Bilal Ahmed', 'fname': 'Muhammad Rafiq',
        'gender': 'Male', 'dob': date(1987, 8, 20), 'mobile': '03001100002', 'email': 'bilal.121@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Model Town', 'school': 'Govt Primary School Township Lahore', 'emis': '35210102',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2015, 9, 1), 'reg_date': date(2018, 9, 1),
        'cur_date': date(2018, 9, 1), 'sen_no': 121, 'verif': 'Verified', 'inquiry': False, 'acr': 88.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2003, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', 2005, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Physics, Mathematics', 'First', 2008, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Science Education', 'First', 2011, 'Allama Iqbal Open University (AIOU), Islamabad', True)
        ]
    })

    # T3: Exact Seniority Tie Candidate A (#45 - Older, DOB 1982)
    teachers.append({
        'p_no': '30100003', 'cnic': '35201-1100003-1', 'name': 'Rashid Minhas', 'fname': 'Karamat Ali',
        'gender': 'Male', 'dob': date(1982, 4, 15), 'mobile': '03001100003', 'email': 'rashid.tie45@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'City', 'school': 'Govt Primary School Mozang Lahore', 'emis': '35210103',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2013, 2, 1), 'reg_date': date(2016, 2, 1),
        'cur_date': date(2016, 2, 1), 'sen_no': 45, 'verif': 'Verified', 'inquiry': False, 'acr': 84.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 1998, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Medical', 'First', 2000, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Botany, Zoology, Chemistry', 'First', 2003, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'General Pedagogy', 'First', 2006, 'University of Education (UE), Lahore', True)
        ]
    })

    # T4: Exact Seniority Tie Candidate B (#45 - Younger, DOB 1988)
    teachers.append({
        'p_no': '30100004', 'cnic': '35201-1100004-1', 'name': 'Khalid Mehmood', 'fname': 'Muhammad Akram',
        'gender': 'Male', 'dob': date(1988, 11, 20), 'mobile': '03001100004', 'email': 'khalid.tie45@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'City', 'school': 'Govt Primary School Krishan Nagar Lahore', 'emis': '35210104',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2013, 2, 1), 'reg_date': date(2016, 2, 1),
        'cur_date': date(2016, 2, 1), 'sen_no': 45, 'verif': 'Verified', 'inquiry': False, 'acr': 85.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2004, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', 2006, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Physics, Mathematics', 'First', 2009, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Science Education', 'First', 2012, 'University of Education (UE), Lahore', True)
        ]
    })

    # T5: Multi-Category Eligible (B.Sc Science + B.A English + B.Ed -> Eligible for EST Science & EST English)
    teachers.append({
        'p_no': '30100005', 'cnic': '35201-1100005-1', 'name': 'Farooq Azam', 'fname': 'Bashir Ahmed',
        'gender': 'Male', 'dob': date(1986, 7, 10), 'mobile': '03001100005', 'email': 'farooq.multi@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Model Town', 'school': 'Govt Primary School Green Town Lahore', 'emis': '35210105',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2012, 1, 10), 'reg_date': date(2015, 1, 10),
        'cur_date': date(2015, 1, 10), 'sen_no': 3, 'verif': 'Verified', 'inquiry': False, 'acr': 90.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2002, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', 2004, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Physics, Chemistry, Mathematics', 'First', 2007, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.A', 'English, English Literature, Urdu', 'First', 2010, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Secondary Teacher Education', 'First', 2012, 'University of Education (UE), Lahore', True)
        ]
    })

    # T6: Multi-Category Eligible (BS Computer Science + B.Ed -> Eligible for EST CS & EST Science)
    teachers.append({
        'p_no': '30100006', 'cnic': '35201-1100006-1', 'name': 'Usman Ghani', 'fname': 'Abdul Rehman',
        'gender': 'Male', 'dob': date(1990, 3, 14), 'mobile': '03001100006', 'email': 'usman.cs@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Cantonment', 'school': 'Govt Primary School Cantt Lahore', 'emis': '35210106',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2016, 8, 1), 'reg_date': date(2019, 8, 1),
        'cur_date': date(2019, 8, 1), 'sen_no': 4, 'verif': 'Verified', 'inquiry': False, 'acr': 88.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2006, 'BISE Lahore', False),
            ('Intermediate', 'ICS', 'Computer Science, Physics, Math', 'First', 2008, 'BISE Lahore', False),
            ('BS-4Years', 'BSCS', 'Computer Science, Mathematics, Physics', 'First', 2012, 'University of Engineering & Technology (UET), Lahore', False),
            ('Bachelor', 'B.Ed', 'Teaching of Science & Computer', 'First', 2014, 'University of Education (UE), Lahore', True)
        ]
    })

    # T7: Ineligible - Missing Professional Qualification (Has B.Sc Science, but NO B.Ed/ADE)
    teachers.append({
        'p_no': '30100007', 'cnic': '35201-1100007-1', 'name': 'Shahbaz Ali', 'fname': 'Nazir Hussain',
        'gender': 'Male', 'dob': date(1991, 5, 18), 'mobile': '03001100007', 'email': 'shahbaz.noped@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Shalimar', 'school': 'Govt Primary School Baghbanpura Lahore', 'emis': '35210107',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2017, 4, 1), 'reg_date': date(2020, 4, 1),
        'cur_date': date(2020, 4, 1), 'sen_no': 5, 'verif': 'Verified', 'inquiry': False, 'acr': 82.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2007, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', 2009, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Physics, Chemistry, Mathematics', 'First', 2012, 'University of the Punjab (PU), Lahore', False)
        ]
    })

    # T8: Ineligible - Degree Subject Mismatch (Has B.Com Commerce, applying for EST Science)
    teachers.append({
        'p_no': '30100008', 'cnic': '35201-1100008-1', 'name': 'Babar Azam', 'fname': 'Ghulam Nabi',
        'gender': 'Male', 'dob': date(1989, 9, 25), 'mobile': '03001100008', 'email': 'babar.bcom@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Raiwind', 'school': 'Govt Primary School Manga Mandi Lahore', 'emis': '35210108',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2015, 6, 1), 'reg_date': date(2018, 6, 1),
        'cur_date': date(2018, 6, 1), 'sen_no': 6, 'verif': 'Verified', 'inquiry': False, 'acr': 80.0,
        'quals': [
            ('Matric', 'SSC', 'Arts', 'Second', 2005, 'BISE Lahore', False),
            ('Intermediate', 'I.Com', 'Commerce, Accounting', 'First', 2007, 'BISE Lahore', False),
            ('Bachelor', 'B.Com', 'Commerce, Financial Accounting, Cost Accounting', 'First', 2010, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'General Pedagogy', 'First', 2013, 'University of Education (UE), Lahore', True)
        ]
    })

    # T9: Ineligible - Pending Disciplinary Inquiry under PEEDA Act 2006
    teachers.append({
        'p_no': '30100009', 'cnic': '35201-1100009-1', 'name': 'Naveed Akhtar', 'fname': 'Allah Ditta',
        'gender': 'Male', 'dob': date(1984, 12, 5), 'mobile': '03001100009', 'email': 'naveed.peeda@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'City', 'school': 'Govt Primary School Shadbagh Lahore', 'emis': '35210109',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2011, 4, 1), 'reg_date': date(2014, 4, 1),
        'cur_date': date(2014, 4, 1), 'sen_no': 7, 'verif': 'Verified', 'inquiry': True, 'acr': 84.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2000, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', 2002, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Physics, Chemistry, Mathematics', 'First', 2005, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Science Pedagogy', 'First', 2008, 'University of Education (UE), Lahore', True)
        ]
    })

    # T10: Ineligible - Unsatisfactory ACR Performance (< 60.0%)
    teachers.append({
        'p_no': '30100010', 'cnic': '35201-1100010-1', 'name': 'Salman Butt', 'fname': 'Muhammad Aslam',
        'gender': 'Male', 'dob': date(1987, 6, 30), 'mobile': '03001100010', 'email': 'salman.lowacr@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Model Town', 'school': 'Govt Primary School Kahna Nau Lahore', 'emis': '35210110',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2013, 8, 15), 'reg_date': date(2016, 8, 15),
        'cur_date': date(2016, 8, 15), 'sen_no': 8, 'verif': 'Verified', 'inquiry': False, 'acr': 52.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'Second', 2003, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Medical', 'Second', 2005, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Botany, Zoology, Chemistry', 'Second', 2008, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Biological Sciences Pedagogy', 'Second', 2011, 'Allama Iqbal Open University (AIOU), Islamabad', True)
        ]
    })

    # T11: Pending Verification
    teachers.append({
        'p_no': '30100011', 'cnic': '35201-1100011-1', 'name': 'Haris Rauf', 'fname': 'Sultan Mehmood',
        'gender': 'Male', 'dob': date(1992, 10, 8), 'mobile': '03001100011', 'email': 'haris.pending@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Cantonment', 'school': 'Govt Primary School Sadar Cantt Lahore', 'emis': '35210111',
        'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': date(2018, 9, 1), 'reg_date': date(2021, 9, 1),
        'cur_date': date(2021, 9, 1), 'sen_no': 9, 'verif': 'Pending', 'inquiry': False, 'acr': 80.0,
        'quals': [
            ('Matric', 'SSC', 'Science', 'First', 2008, 'BISE Lahore', False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', 2010, 'BISE Lahore', False),
            ('Bachelor', 'B.Sc', 'Physics, Mathematics', 'First', 2013, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Science Pedagogy', 'First', 2016, 'University of Education (UE), Lahore', True)
        ]
    })

    # T12 to T45: Diverse PSTs across Punjab (Arts, Science, CS, English, Arabic eligible)
    pst_templates = [
        ("Science", "B.Sc", "Physics, Chemistry, Mathematics", "B.Ed", "Science Education"),
        ("Arts", "B.A", "English, Urdu, Pakistan Studies, Islamic Studies", "B.Ed", "General Pedagogy"),
        ("Arabic", "M.A", "Arabic Literature, Classical Texts, Arabic Linguistics", "B.Ed", "Teaching of Arabic"),
        ("English", "B.A", "English, English Literature, Linguistics", "B.Ed", "Teaching of English"),
        ("Computer Science", "BSCS", "Computer Science, Software Engineering, IT", "B.Ed", "Computer Education"),
        ("Arabic", "Shahadat-ul-Almia", "Higher Arabic, Quranic Sciences, Hadith Sciences", "B.Ed", "Secondary Teacher Education"),
        ("Science", "B.Sc", "Botany, Zoology, Chemistry, Biology", "ADE", "Associate Degree in Education - 2 Years"),
    ]

    for idx in range(12, 46):
        p_no = f"301000{idx:02d}"
        d_idx = (idx - 12) % len(districts_info)
        dist, tehs = districts_info[d_idx]
        teh = tehs[(idx) % len(tehs)]
        tmpl = pst_templates[(idx) % len(pst_templates)]
        gender = "Female" if idx % 3 == 0 else "Male"
        name = first_names_f[(idx) % len(first_names_f)] if gender == "Female" else first_names_m[(idx) % len(first_names_m)]
        fname = father_names[(idx) % len(father_names)]
        
        # Districts CNIC prefix
        prefix_map = {"Lahore": "35201", "Rawalpindi": "37405", "Faisalabad": "33100", "Multan": "36302", "Gujranwala": "34101"}
        cnic_prefix = prefix_map.get(dist, "35201")
        cnic = f"{cnic_prefix}-11000{idx:02d}-{1 if gender == 'Male' else 2}"
        
        y_dob = 1980 + (idx % 15)
        dob = date(y_dob, (idx % 12) + 1, (idx % 27) + 1)
        app_y = 2010 + (idx % 10)
        app_d = date(app_y, 4, 15)
        reg_d = date(app_y + 3, 4, 15)
        
        deg_lvl = 'Master' if tmpl[1] in ('M.A', 'Shahadat-ul-Almia') else ('BS-4Years' if tmpl[1] == 'BSCS' else 'Bachelor')
        teachers.append({
            'p_no': p_no, 'cnic': cnic, 'name': f"{name} Bibi" if gender == "Female" else f"{name} Khan",
            'fname': fname, 'gender': gender, 'dob': dob, 'mobile': f"0300{p_no[1:]}", 'email': f"pst.{idx}@{dist.lower()}.sed.edu.pk",
            'dist': dist, 'teh': teh, 'school': f"Govt Primary School {teh} {dist}", 'emis': f"{cnic_prefix[:4]}{idx:04d}",
            'desig': 'PST', 'bs': 14, 'cat': 'General', 'app_date': app_d, 'reg_date': reg_d, 'cur_date': reg_d,
            'sen_no': 10 + idx, 'verif': 'Verified' if idx % 8 != 0 else 'Pending',
            'inquiry': (idx % 17 == 0), 'acr': 75.0 + (idx % 20),
            'quals': [
                ('Matric', 'SSC', 'Science', 'First', y_dob + 16, f"BISE {dist}", False),
                ('Intermediate', 'F.Sc' if 'Science' in tmpl[0] else 'F.A', 'General Group', 'First', y_dob + 18, f"BISE {dist}", False),
                (deg_lvl, tmpl[1], tmpl[2], 'First', y_dob + 22, f"University of the Punjab (PU), Lahore", False),
                ('Bachelor' if tmpl[3] == 'B.Ed' else 'Professional Teaching', tmpl[3], tmpl[4], 'First', y_dob + 24, "University of Education (UE), Lahore", True)
            ]
        })

    # =========================================================================
    # 46 to 80: Elementary School Teachers - EST (BS-15)
    # =========================================================================

    # T46: EST Science Eligible for SST Science (M.Sc Physics + B.Ed)
    teachers.append({
        'p_no': '30100046', 'cnic': '35201-1200046-2', 'name': 'Ayesha Bibi', 'fname': 'Muhammad Rafiq',
        'gender': 'Female', 'dob': date(1987, 8, 24), 'mobile': '03211200046', 'email': 'ayesha.est@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Model Town', 'school': 'Govt Girls High School Township Lahore', 'emis': '35210146',
        'desig': 'EST (Science)', 'bs': 15, 'cat': 'Science', 'app_date': date(2013, 9, 1), 'reg_date': date(2016, 9, 1),
        'cur_date': date(2016, 9, 1), 'sen_no': 1, 'verif': 'Verified', 'inquiry': False, 'acr': 89.0,
        'quals': [
            ('Bachelor', 'B.Sc', 'Physics, Mathematics', 'First', 2008, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Sc', 'Physics', 'First', 2011, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Science Education', 'First', 2012, 'University of Education (UE), Lahore', True)
        ]
    })

    # T47: EST Science Eligible for SST Science (B.Sc Double Math Physics + B.Ed)
    teachers.append({
        'p_no': '30100047', 'cnic': '35201-1200047-2', 'name': 'Saima Noreen', 'fname': 'Karamat Ali',
        'gender': 'Female', 'dob': date(1989, 2, 14), 'mobile': '03211200047', 'email': 'saima.est@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'City', 'school': 'Govt Girls Middle School Ravi Road Lahore', 'emis': '35210147',
        'desig': 'EST (Science)', 'bs': 15, 'cat': 'Science', 'app_date': date(2014, 3, 1), 'reg_date': date(2017, 3, 1),
        'cur_date': date(2017, 3, 1), 'sen_no': 2, 'verif': 'Verified', 'inquiry': False, 'acr': 87.0,
        'quals': [
            ('Bachelor', 'B.Sc', 'Physics, Chemistry, Mathematics', 'First', 2010, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Mathematics Teaching', 'First', 2012, 'University of Education (UE), Lahore', True)
        ]
    })

    # T48: Multi-Category Eligible EST (M.Sc Mathematics + M.A English + M.Ed -> Eligible for SST Science & SST Arts)
    teachers.append({
        'p_no': '30100048', 'cnic': '35201-1200048-1', 'name': 'Noman Ali', 'fname': 'Muhammad Akram',
        'gender': 'Male', 'dob': date(1984, 11, 10), 'mobile': '03211200048', 'email': 'noman.estmulti@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Model Town', 'school': 'Govt Middle School Model Town Lahore', 'emis': '35210148',
        'desig': 'EST (Science)', 'bs': 15, 'cat': 'Science', 'app_date': date(2011, 4, 10), 'reg_date': date(2014, 4, 10),
        'cur_date': date(2014, 4, 10), 'sen_no': 3, 'verif': 'Verified', 'inquiry': False, 'acr': 92.0,
        'quals': [
            ('Bachelor', 'B.Sc', 'Mathematics, Physics', 'First', 2005, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Sc', 'Mathematics', 'First', 2008, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.A', 'English, English Literature', 'First', 2011, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Ed', 'Teacher Education & Administration', 'First', 2013, 'University of Education (UE), Lahore', True)
        ]
    })

    # T49: Multi-Category Eligible EST (BSCS + M.Ed -> Eligible for SST CS & SST Science)
    teachers.append({
        'p_no': '30100049', 'cnic': '35201-1200049-1', 'name': 'Asad Shafiq', 'fname': 'Bashir Ahmed',
        'gender': 'Male', 'dob': date(1988, 5, 20), 'mobile': '03211200049', 'email': 'asad.cs@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Cantonment', 'school': 'Govt High School Cantt Lahore', 'emis': '35210149',
        'desig': 'EST (Computer Science)', 'bs': 15, 'cat': 'Computer Science', 'app_date': date(2015, 8, 1), 'reg_date': date(2018, 8, 1),
        'cur_date': date(2018, 8, 1), 'sen_no': 4, 'verif': 'Verified', 'inquiry': False, 'acr': 86.0,
        'quals': [
            ('BS-4Years', 'BSCS', 'Computer Science, Mathematics, Physics', 'First', 2010, 'University of Engineering & Technology (UET), Lahore', False),
            ('Master', 'MCS', 'Computer Science, Software Engineering', 'First', 2013, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Ed', 'Science & Technology Education', 'First', 2015, 'University of Education (UE), Lahore', True)
        ]
    })

    # T50 to T80: Varied ESTs across Punjab (Science, Arts, English, CS)
    est_categories = [
        ('EST (Science)', 'Science', 'B.Sc', 'Physics, Chemistry, Mathematics', 'B.Ed', 'Science Pedagogy'),
        ('EST (Arts)', 'Arts', 'B.A', 'English, Urdu, Pakistan Studies', 'B.Ed', 'Humanities Pedagogy'),
        ('EST (English)', 'English', 'M.A', 'English Literature, Linguistics', 'B.Ed', 'Teaching of English'),
        ('EST (Computer Science)', 'Computer Science', 'BSCS', 'Computer Science, Information Technology', 'B.Ed', 'Computer Pedagogy'),
        ('EST (General)', 'General', 'B.A', 'History, Civics, Islamiyat', 'ADE', 'Elementary Teacher Education')
    ]

    for idx in range(50, 81):
        p_no = f"301000{idx:02d}"
        d_idx = (idx - 50) % len(districts_info)
        dist, tehs = districts_info[d_idx]
        teh = tehs[(idx) % len(tehs)]
        tmpl = est_categories[(idx) % len(est_categories)]
        gender = "Female" if idx % 2 == 0 else "Male"
        name = first_names_f[(idx) % len(first_names_f)] if gender == "Female" else first_names_m[(idx) % len(first_names_m)]
        fname = father_names[(idx) % len(father_names)]
        prefix_map = {"Lahore": "35201", "Rawalpindi": "37405", "Faisalabad": "33100", "Multan": "36302", "Gujranwala": "34101"}
        cnic_prefix = prefix_map.get(dist, "35201")
        cnic = f"{cnic_prefix}-12000{idx:02d}-{1 if gender == 'Male' else 2}"
        
        y_dob = 1978 + (idx % 14)
        dob = date(y_dob, (idx % 12) + 1, (idx % 26) + 1)
        app_y = 2008 + (idx % 12)
        app_d = date(app_y, 3, 10)
        reg_d = date(app_y + 3, 3, 10)

        # Diverse statuses
        has_bed = (idx % 9 != 0)  # Some missing professional
        inquiry = (idx % 19 == 0)
        acr = 50.0 if (idx % 23 == 0) else (78.0 + (idx % 18))
        verif = 'Pending' if (idx % 11 == 0) else 'Verified'

        quals = [
            ('Matric', 'SSC', 'Science', 'First', y_dob + 16, f"BISE {dist}", False),
            ('Intermediate', 'F.Sc' if 'Science' in tmpl[1] else 'F.A', 'General Group', 'First', y_dob + 18, f"BISE {dist}", False),
            ('Bachelor' if tmpl[2] in ('B.Sc', 'B.A') else ('BS-4Years' if tmpl[2] == 'BSCS' else 'Master'), tmpl[2], tmpl[3], 'First', y_dob + 22, "University of the Punjab (PU), Lahore", False)
        ]
        if has_bed:
            quals.append(('Bachelor' if tmpl[4] == 'B.Ed' else 'Professional Teaching', tmpl[4], tmpl[5], 'First', y_dob + 24, "University of Education (UE), Lahore", True))

        teachers.append({
            'p_no': p_no, 'cnic': cnic, 'name': f"{name} Bibi" if gender == "Female" else f"{name} Mehmood",
            'fname': fname, 'gender': gender, 'dob': dob, 'mobile': f"0312{p_no[1:]}", 'email': f"est.{idx}@{dist.lower()}.sed.edu.pk",
            'dist': dist, 'teh': teh, 'school': f"Govt High School {teh} {dist}", 'emis': f"{cnic_prefix[:4]}{idx:04d}",
            'desig': tmpl[0], 'bs': 15, 'cat': tmpl[1], 'app_date': app_d, 'reg_date': reg_d, 'cur_date': reg_d,
            'sen_no': 5 + idx, 'verif': verif, 'inquiry': inquiry, 'acr': acr,
            'quals': quals
        })

    # =========================================================================
    # 81 to 100: Secondary School Teachers - SST (BS-16)
    # =========================================================================

    # T81: SST Eligible for Headmaster BS-17 & Subject Specialist BS-17 (> 2 yrs service)
    teachers.append({
        'p_no': '30100081', 'cnic': '35201-1300081-1', 'name': 'Zahid Mehmood', 'fname': 'Karamat Ali',
        'gender': 'Male', 'dob': date(1980, 11, 15), 'mobile': '03331300081', 'email': 'zahid.sst@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'City', 'school': 'Govt Central Model School Lower Mall Lahore', 'emis': '35210181',
        'desig': 'SST (Science)', 'bs': 16, 'cat': 'Science', 'app_date': date(2008, 3, 1), 'reg_date': date(2011, 3, 1),
        'cur_date': date(2014, 5, 1), 'sen_no': 1, 'verif': 'Verified', 'inquiry': False, 'acr': 92.0,
        'quals': [
            ('Bachelor', 'B.Sc', 'Mathematics, Physics', 'First', 2001, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Sc', 'Mathematics', 'First', 2004, 'University of the Punjab (PU), Lahore', False),
            ('Bachelor', 'B.Ed', 'Mathematics Teaching', 'First', 2006, 'University of Education (UE), Lahore', True),
            ('Master', 'M.Ed', 'Educational Administration', 'First', 2008, 'University of Education (UE), Lahore', True)
        ]
    })

    # T82: SST Eligible for SS Physics & Headmaster BS-17
    teachers.append({
        'p_no': '30100082', 'cnic': '35201-1300082-1', 'name': 'Muhammad Akram', 'fname': 'Abdul Rehman',
        'gender': 'Male', 'dob': date(1982, 3, 22), 'mobile': '03331300082', 'email': 'akram.sst@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Model Town', 'school': 'Govt Comprehensive High School Model Town Lahore', 'emis': '35210182',
        'desig': 'SST (Science)', 'bs': 16, 'cat': 'Science', 'app_date': date(2010, 4, 1), 'reg_date': date(2013, 4, 1),
        'cur_date': date(2016, 8, 1), 'sen_no': 2, 'verif': 'Verified', 'inquiry': False, 'acr': 88.0,
        'quals': [
            ('Bachelor', 'B.Sc', 'Physics, Chemistry, Mathematics', 'First', 2003, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Sc', 'Physics', 'First', 2006, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Ed', 'Secondary Education', 'First', 2009, 'University of Education (UE), Lahore', True)
        ]
    })

    # T83: Ineligible SST for BS-17 due to Service Shortfall (Has < 2.0 years regular service as SST)
    teachers.append({
        'p_no': '30100083', 'cnic': '35201-1300083-1', 'name': 'Hamza Tariq', 'fname': 'Nazir Hussain',
        'gender': 'Male', 'dob': date(1993, 1, 10), 'mobile': '03331300083', 'email': 'hamza.shortfall@sed.punjab.gov.pk',
        'dist': 'Lahore', 'teh': 'Cantonment', 'school': 'Govt High School Sarwar Road Cantt Lahore', 'emis': '35210183',
        'desig': 'SST (Science)', 'bs': 16, 'cat': 'Science', 'app_date': date(2025, 1, 15), 'reg_date': date(2025, 7, 15),
        'cur_date': date(2025, 7, 15), 'sen_no': 15, 'verif': 'Verified', 'inquiry': False, 'acr': 85.0,
        'quals': [
            ('Bachelor', 'B.Sc', 'Physics, Mathematics', 'First', 2014, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Sc', 'Physics', 'First', 2017, 'University of the Punjab (PU), Lahore', False),
            ('Master', 'M.Ed', 'Science Education', 'First', 2019, 'University of Education (UE), Lahore', True)
        ]
    })

    # T84 to T100: Varied SSTs across Punjab (Science, Arts, CS) with M.Phil & Ph.D
    sst_categories = [
        ('SST (Science)', 'Science', 'M.Sc', 'Physics, Chemistry, Mathematics', 'M.Ed', 'Science Education'),
        ('SST (Arts)', 'Arts', 'M.A', 'English, Urdu, Education', 'M.Ed', 'Educational Leadership'),
        ('SST (Computer Science)', 'Computer Science', 'MCS', 'Computer Science, IT, Artificial Intelligence', 'B.Ed', 'Computer Education'),
        ('SST (Science)', 'Science', 'M.Phil', 'Mathematics, Fluid Dynamics', 'M.Ed', 'Curriculum Design'),
        ('SST (Computer Science)', 'Computer Science', 'Ph.D', 'Ph.D in Computer Science / IT', 'M.Ed', 'Doctoral Education Studies')
    ]

    for idx in range(84, 101):
        p_no = f"301000{idx:02d}"
        d_idx = (idx - 84) % len(districts_info)
        dist, tehs = districts_info[d_idx]
        teh = tehs[(idx) % len(tehs)]
        tmpl = sst_categories[(idx) % len(sst_categories)]
        gender = "Female" if idx % 2 == 0 else "Male"
        name = first_names_f[(idx) % len(first_names_f)] if gender == "Female" else first_names_m[(idx) % len(first_names_m)]
        fname = father_names[(idx) % len(father_names)]
        prefix_map = {"Lahore": "35201", "Rawalpindi": "37405", "Faisalabad": "33100", "Multan": "36302", "Gujranwala": "34101"}
        cnic_prefix = prefix_map.get(dist, "35201")
        cnic = f"{cnic_prefix}-13000{idx:02d}-{1 if gender == 'Male' else 2}"
        
        y_dob = 1974 + (idx % 15)
        dob = date(y_dob, (idx % 12) + 1, (idx % 25) + 1)
        app_y = 2004 + (idx % 12)
        app_d = date(app_y, 2, 1)
        reg_d = date(app_y + 3, 2, 1)
        cur_d = date(app_y + 4, 2, 1)

        has_prof = (idx != 95)  # T95 missing professional degree
        inquiry = (idx == 98)   # T98 has inquiry
        acr = 54.0 if (idx == 99) else (80.0 + (idx % 18))
        verif = 'Pending' if (idx == 100) else 'Verified'

        quals = [
            ('Matric', 'SSC', 'Science', 'First', y_dob + 16, f"BISE {dist}", False),
            ('Intermediate', 'F.Sc', 'Pre-Engineering', 'First', y_dob + 18, f"BISE {dist}", False),
            ('Bachelor', 'B.Sc' if 'Science' in tmpl[1] else 'B.A', 'Physics, Chemistry, Math', 'First', y_dob + 22, "University of the Punjab (PU), Lahore", False),
            ('Master' if tmpl[2] in ('M.Sc', 'M.A', 'MCS') else tmpl[2], tmpl[2], tmpl[3], 'First', y_dob + 24, "University of the Punjab (PU), Lahore", False)
        ]
        if has_prof:
            quals.append(('Master' if tmpl[4] == 'M.Ed' else 'Bachelor', tmpl[4], tmpl[5], 'First', y_dob + 26, "University of Education (UE), Lahore", True))

        teachers.append({
            'p_no': p_no, 'cnic': cnic, 'name': f"{name} Bibi" if gender == "Female" else f"{name} Hussain",
            'fname': fname, 'gender': gender, 'dob': dob, 'mobile': f"0333{p_no[1:]}", 'email': f"sst.{idx}@{dist.lower()}.sed.edu.pk",
            'dist': dist, 'teh': teh, 'school': f"Govt Comprehensive Model High School {teh} {dist}", 'emis': f"{cnic_prefix[:4]}{idx:04d}",
            'desig': tmpl[0], 'bs': 16, 'cat': tmpl[1], 'app_date': app_d, 'reg_date': reg_d, 'cur_date': cur_d,
            'sen_no': 2 + (idx - 80), 'verif': verif, 'inquiry': inquiry, 'acr': acr,
            'quals': quals
        })

    return teachers

def seed_100_teachers(db):
    """
    Seeds exactly 100 realistic teachers into the database along with:
    - User login credentials (username = cnic, password = Teacher@123)
    - Full academic and professional qualifications
    - Service history
    - Seniority records
    """
    teachers_list = get_100_teachers_data()
    print(f"--- Seeding {len(teachers_list)} Realistic Teachers across Punjab ---")

    count_added = 0
    count_updated = 0

    for td in teachers_list:
        t = db.query(Teacher).filter(Teacher.cnic == td['cnic']).first()
        if not t:
            t = Teacher(
                personnel_no=td['p_no'],
                cnic=td['cnic'],
                full_name=td['name'],
                father_name=td['fname'],
                gender=td['gender'],
                date_of_birth=td['dob'],
                mobile=td['mobile'],
                email=td['email'],
                address=f"{td['teh']}, {td['dist']}, Punjab, Pakistan",
                district=td['dist'],
                tehsil=td['teh'],
                school_name=td['school'],
                school_emis_code=td['emis'],
                current_designation=td['desig'],
                current_bs=td['bs'],
                current_category=td['cat'],
                appointment_date=td['app_date'],
                joining_date=td['app_date'],
                regularization_date=td['reg_date'],
                current_post_date=td['cur_date'],
                seniority_no=td['sen_no'],
                seniority_date=td['cur_date'],
                verification_status=td['verif'],
                disciplinary_inquiry_pending=td['inquiry'],
                acr_score_average=td['acr']
            )
            db.add(t)
            db.flush()
            count_added += 1
        else:
            t.personnel_no = td['p_no']
            t.full_name = td['name']
            t.father_name = td['fname']
            t.gender = td['gender']
            t.date_of_birth = td['dob']
            t.mobile = td['mobile']
            t.email = td['email']
            t.district = td['dist']
            t.tehsil = td['teh']
            t.school_name = td['school']
            t.current_designation = td['desig']
            t.current_bs = td['bs']
            t.current_category = td['cat']
            t.appointment_date = td['app_date']
            t.regularization_date = td['reg_date']
            t.current_post_date = td['cur_date']
            t.seniority_no = td['sen_no']
            t.seniority_date = td['cur_date']
            t.verification_status = td['verif']
            t.disciplinary_inquiry_pending = td['inquiry']
            t.acr_score_average = td['acr']
            count_updated += 1

        # 1. User login credentials
        u = db.query(User).filter(User.username == t.cnic).first()
        if not u:
            u = User(
                teacher_id=t.id,
                username=t.cnic,
                role='TEACHER',
                full_name=t.full_name,
                email=t.email,
                phone=t.mobile,
                is_active=True,
                is_first_login=False
            )
            u.set_password('Teacher@123')
            db.add(u)
        else:
            u.teacher_id = t.id
            u.full_name = t.full_name
            u.email = t.email
            u.set_password('Teacher@123')

        # 2. Qualifications
        existing_quals = db.query(Qualification).filter(Qualification.teacher_id == t.id).all()
        existing_keys = {(q.degree_level, q.degree_name, q.subject) for q in existing_quals}

        for q_level, q_name, q_subj, q_div, q_yr, q_uni, q_prof in td['quals']:
            if (q_level, q_name, q_subj) not in existing_keys:
                q = Qualification(
                    teacher_id=t.id,
                    degree_level=q_level,
                    degree_name=q_name,
                    subject=q_subj,
                    division=q_div,
                    passing_year=q_yr,
                    board_university=q_uni,
                    professional_qualification=q_prof,
                    verification_status='Verified' if t.verification_status == 'Verified' else 'Pending',
                    verified_by='admin_lahore' if t.verification_status == 'Verified' else None,
                    verified_at=datetime.utcnow() if t.verification_status == 'Verified' else None
                )
                db.add(q)

        # 3. Service History
        sh = db.query(ServiceHistory).filter(
            ServiceHistory.teacher_id == t.id,
            ServiceHistory.is_current_post == True
        ).first()
        if not sh:
            sh = ServiceHistory(
                teacher_id=t.id,
                designation=t.current_designation,
                bs=t.current_bs,
                school_name=t.school_name,
                district=t.district,
                tehsil=t.tehsil,
                from_date=t.current_post_date,
                is_current_post=True,
                appointment_type='Regular',
                verification_status=t.verification_status
            )
            db.add(sh)
        else:
            sh.designation = t.current_designation
            sh.bs = t.current_bs
            sh.school_name = t.school_name
            sh.district = t.district
            sh.tehsil = t.tehsil

        # 4. Seniority Record
        sen = db.query(SeniorityRecord).filter(
            SeniorityRecord.teacher_id == t.id,
            SeniorityRecord.designation == t.current_designation,
            SeniorityRecord.district == t.district
        ).first()
        if not sen:
            sen = SeniorityRecord(
                teacher_id=t.id,
                seniority_no=t.seniority_no,
                seniority_date=t.current_post_date,
                designation=t.current_designation,
                bs=t.current_bs,
                district=t.district,
                seniority_list_reference=f"DEO/SEN/{t.district.upper()}/2026/01",
                seniority_list_date=date(2026, 1, 1),
                is_official=True,
                verified=(t.verification_status == 'Verified')
            )
            db.add(sen)
        else:
            sen.seniority_no = t.seniority_no

    db.commit()
    print(f"--- Seeding 100 Teachers Complete: {count_added} added, {count_updated} refreshed. ---")
