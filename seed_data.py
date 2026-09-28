import os
from datetime import date, datetime
from app import create_app, get_db
from app.models.user import User
from app.models.teacher import Teacher
from app.models.qualification import Qualification
from app.models.service import ServiceHistory
from app.models.seniority import SeniorityRecord
from app.models.rule import RuleSource, PromotionRule
from app.models.vacancy import Vacancy
from app.models.adsense import AdSenseSetting, AdSlot
from app.models.audit import SystemSetting, AuditLog
from app.models.post import TeachingPost
from app.services.teachers_seeder import seed_100_teachers

def seed_database():
    app = create_app()
    with app.app_context():
        db = get_db()
        print("--- Initializing Database Seed ---")

        # 1. System Settings
        settings = [
            ('app_title', 'Teacher Promotion Portal', 'Official application title'),
            ('department_name', 'School Education Department', 'Department title'),
            ('announcement_banner', 'Official Promotion Scrutiny Exercise for EST and SST Cadres is now open.', 'Public notice banner'),
            ('maintenance_mode', 'false', 'Maintenance mode status')
        ]
        for k, v, desc in settings:
            s = db.query(SystemSetting).filter(SystemSetting.setting_key == k).first()
            if not s:
                db.add(SystemSetting(setting_key=k, setting_value=v, description=desc))

        # 2. AdSense Settings & Slots
        adsense = db.query(AdSenseSetting).first()
        if not adsense:
            adsense = AdSenseSetting(
                publisher_id='ca-pub-9876543210123456',
                ads_enabled=True,
                auto_ads_enabled=False,
                test_mode=True, # Active sandbox mode
                header_code='<!-- Google AdSense Official Integration -->'
            )
            db.add(adsense)
            db.flush()

        # Ad Slots
        slots = [
            ('Header Top Leaderboard', '1001', 'horizontal', 'header', 'ALL'),
            ('Content Top Banner', '1002', 'responsive', 'content_top', 'ALL'),
            ('Teacher Portal Footer Banner', '1003', 'responsive', 'footer', 'TEACHER')
        ]
        for name, slot_id, s_format, placement, target in slots:
            if not db.query(AdSlot).filter(AdSlot.slot_name == name).first():
                db.add(AdSlot(
                    slot_name=name,
                    slot_id=slot_id,
                    slot_format=s_format,
                    placement=placement,
                    target_roles=target,
                    is_active=True
                ))

        # 3. Rule Source: SED Service Rules 2014
        source_2014 = db.query(RuleSource).filter(RuleSource.notification_no == 'SOR-III(S&GAD)1-19/2004(P)').first()
        if not source_2014:
            source_2014 = RuleSource(
                title='School Education Department (School Education) Service Rules 2014',
                notification_no='SOR-III(S&GAD)1-19/2004(P)',
                notification_date=date(2014, 3, 14),
                effective_date=date(2014, 3, 14),
                issuing_authority='S&GAD (Regulations Wing) / SED',
                document_summary='Statutory rules governing terms of appointment, minimum regular service, promotion quotas, and qualification requirements for teaching cadres.',
                is_active=True
            )
            db.add(source_2014)
            db.flush()

        # 4. Promotion Rules
        rules_data = [
            {
                'rule_code': 'PST_TO_EST_SCI',
                'rule_name': 'Promotion of Primary School Teacher (PST) to Elementary School Teacher (EST Science) BS-15',
                'source_desig': 'PST',
                'source_bs': 14,
                'target_desig': 'EST (Science)',
                'target_bs': 15,
                'category': 'Science',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'B.Sc, BS',
                'req_subjects': 'Physics, Chemistry, Mathematics, Biology',
                'req_prof': 'B.Ed, ADE, B.S.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'PST_TO_EST_ARTS',
                'rule_name': 'Promotion of Primary School Teacher (PST) to Elementary School Teacher (EST Arts) BS-15',
                'source_desig': 'PST',
                'source_bs': 14,
                'target_desig': 'EST (Arts)',
                'target_bs': 15,
                'category': 'Arts',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'B.A, BS',
                'req_subjects': 'English, Urdu, History, Pakistan Studies, Islamic Studies',
                'req_prof': 'B.Ed, ADE, B.S.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'PST_TO_EST_ENG',
                'rule_name': 'Promotion of Primary School Teacher (PST) to Elementary School Teacher (EST English) BS-15',
                'source_desig': 'PST',
                'source_bs': 14,
                'target_desig': 'EST (English)',
                'target_bs': 15,
                'category': 'English',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'B.A, BS, M.A',
                'req_subjects': 'English, English Literature, Linguistics',
                'req_prof': 'B.Ed, ADE, B.S.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'PST_TO_EST_CS',
                'rule_name': 'Promotion of Primary School Teacher (PST) to Elementary School Teacher (EST Computer Science) BS-15',
                'source_desig': 'PST',
                'source_bs': 14,
                'target_desig': 'EST (Computer Science)',
                'target_bs': 15,
                'category': 'Computer Science',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'BSCS, BSIT, B.Sc, BS',
                'req_subjects': 'Computer Science, Information Technology, Software Engineering, Computer Studies',
                'req_prof': 'B.Ed, ADE, B.S.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'PST_TO_EST_ARABIC',
                'rule_name': 'Promotion of Primary School Teacher (PST) to Elementary School Teacher (EST Arabic) BS-15',
                'source_desig': 'PST',
                'source_bs': 14,
                'target_desig': 'EST (Arabic)',
                'target_bs': 15,
                'category': 'Arabic',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'B.A, BS, M.A, Shahadat-ul-Almia, Shahadat-ul-Aalamia, Master',
                'req_subjects': 'Arabic, Shahadat-ul-Almia, Higher Arabic, Islamic Studies',
                'req_prof': 'B.Ed, M.Ed, ADE, M.A Education, B.S.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'EST_TO_SST_SCI',
                'rule_name': 'Promotion of Elementary School Teacher (EST) to Secondary School Teacher (SST Science) BS-16',
                'source_desig': 'EST (Science)',
                'source_bs': 15,
                'target_desig': 'SST (Science)',
                'target_bs': 16,
                'category': 'Science',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'B.Sc, BS, M.Sc',
                'req_subjects': 'Physics, Chemistry, Mathematics',
                'req_prof': 'B.Ed, B.S.Ed, M.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'EST_TO_SST_ARTS',
                'rule_name': 'Promotion of Elementary School Teacher (EST) to Secondary School Teacher (SST Arts) BS-16',
                'source_desig': 'EST (Arts)',
                'source_bs': 15,
                'target_desig': 'SST (Arts)',
                'target_bs': 16,
                'category': 'Arts',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'B.A, BS, M.A',
                'req_subjects': 'English, Urdu, Pakistan Studies',
                'req_prof': 'B.Ed, M.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'EST_TO_SST_CS',
                'rule_name': 'Promotion of Elementary School Teacher (EST) to Secondary School Teacher (SST Computer Science) BS-16',
                'source_desig': 'EST (Computer Science)',
                'source_bs': 15,
                'target_desig': 'SST (Computer Science)',
                'target_bs': 16,
                'category': 'Computer Science',
                'min_service': 0.0,
                'req_level': 'Bachelor',
                'req_degrees': 'BSCS, BSIT, MCS, MIT, BS',
                'req_subjects': 'Computer Science, Information Technology, Software Engineering',
                'req_prof': 'B.Ed, M.Ed, B.S.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'SST_TO_HM_BS17',
                'rule_name': 'Promotion of Secondary School Teacher (SST) to Headmaster / Headmistress BS-17',
                'source_desig': 'SST (Science)',
                'source_bs': 16,
                'target_desig': 'Headmaster',
                'target_bs': 17,
                'category': 'Administration',
                'min_service': 2.0,
                'req_level': 'Master',
                'req_degrees': 'Master, M.Sc, M.A, BS-4Years',
                'req_subjects': 'Mathematics, Physics, Chemistry, English, Education',
                'req_prof': 'B.Ed, M.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'SST_TO_SS_BS17',
                'rule_name': 'Promotion of Secondary School Teacher (SST) to Subject Specialist BS-17',
                'source_desig': 'SST (Science)',
                'source_bs': 16,
                'target_desig': 'Subject Specialist',
                'target_bs': 17,
                'category': 'Science',
                'min_service': 2.0,
                'req_level': 'Master',
                'req_degrees': 'Master, M.Sc, M.A, BS-4Years',
                'req_subjects': 'Physics, Chemistry, Mathematics, Biology, English',
                'req_prof': 'B.Ed, M.Ed',
                'quota': 50.0
            },
            {
                'rule_code': 'SS_TO_SSS_BS18',
                'rule_name': 'Promotion of Subject Specialist (SS) to Senior Subject Specialist (SSS) BS-18',
                'source_desig': 'Subject Specialist',
                'source_bs': 17,
                'target_desig': 'Senior Subject Specialist',
                'target_bs': 18,
                'category': 'Teaching',
                'min_service': 5.0,
                'req_level': 'Master',
                'req_degrees': 'Master, M.Sc, M.A, M.Phil',
                'req_subjects': 'Physics, Chemistry, Mathematics, Biology, English',
                'req_prof': 'B.Ed, M.Ed',
                'quota': 100.0
            },
            {
                'rule_code': 'HM_TO_SR_HM_BS18',
                'rule_name': 'Promotion of Headmaster / Headmistress (BS-17) to Senior Headmaster / Senior Headmistress (BS-18)',
                'source_desig': 'Headmaster',
                'source_bs': 17,
                'target_desig': 'Senior Headmaster',
                'target_bs': 18,
                'category': 'Administration',
                'min_service': 5.0,
                'req_level': 'Master',
                'req_degrees': 'Master, M.Sc, M.A, M.Phil, M.Ed',
                'req_subjects': 'Education, Mathematics, Science, Humanities',
                'req_prof': 'B.Ed, M.Ed',
                'quota': 100.0
            }
        ]

        for rd in rules_data:
            existing_rule = db.query(PromotionRule).filter(PromotionRule.rule_code == rd['rule_code']).first()
            if not existing_rule:
                db.add(PromotionRule(
                    source_id=source_2014.id,
                    rule_code=rd['rule_code'],
                    rule_name=rd['rule_name'],
                    source_designation=rd['source_desig'],
                    source_bs=rd['source_bs'],
                    target_designation=rd['target_desig'],
                    target_bs=rd['target_bs'],
                    promotion_category=rd['category'],
                    min_regular_service_years=rd['min_service'],
                    min_total_service_years=rd['min_service'],
                    required_degree_level=rd['req_level'],
                    required_degree_names=rd['req_degrees'],
                    required_subjects=rd['req_subjects'],
                    required_professional_degree=rd['req_prof'],
                    quota_percentage=rd['quota'],
                    is_active=True
                ))
            else:
                existing_rule.min_regular_service_years = rd['min_service']
                existing_rule.min_total_service_years = rd['min_service']
                existing_rule.rule_name = rd['rule_name']
                existing_rule.required_subjects = rd['req_subjects']

        # 5. Vacancies
        vac_data = [
            ('Lahore', 'Model Town', 'EST (Science)', 15, 'Science', 120, 80, 50.0),
            ('Lahore', 'City', 'EST (Arts)', 15, 'Arts', 100, 75, 50.0),
            ('Lahore', 'City', 'EST (Arabic)', 15, 'Arabic', 30, 16, 50.0),
            ('Lahore', 'Model Town', 'EST (Arabic)', 15, 'Arabic', 20, 10, 50.0),
            ('Lahore', 'Model Town', 'SST (Science)', 16, 'Science', 80, 60, 50.0),
            ('Lahore', 'City', 'Headmaster', 17, 'Administration', 40, 30, 50.0),
            ('Rawalpindi', 'Rawalpindi', 'EST (Science)', 15, 'Science', 90, 65, 50.0),
            ('Rawalpindi', 'Rawalpindi', 'EST (Arabic)', 15, 'Arabic', 25, 15, 50.0)
        ]
        for dist, teh, des, bs, cat, sanc, filled, q_pct in vac_data:
            if not db.query(Vacancy).filter(Vacancy.district == dist, Vacancy.designation == des).first():
                vac = Vacancy(
                    district=dist, tehsil=teh, designation=des, bs=bs, category=cat,
                    sanctioned_posts=sanc, filled_posts=filled, promotion_quota_percent=q_pct
                )
                vac.calculate_vacancies()
                db.add(vac)

        # 6. Default Users
        # SuperAdmin
        superadmin = db.query(User).filter(User.username == 'superadmin').first()
        if not superadmin:
            superadmin = User(
                username='superadmin',
                role='SUPERADMIN',
                full_name='System Owner & Super Administrator',
                email='superadmin@sed.punjab.gov.pk',
                phone='042-99200000',
                is_active=True,
                is_first_login=False
            )
            superadmin.set_password('SuperAdmin@123')
            db.add(superadmin)

        # Department Admins
        admin_lhr = db.query(User).filter(User.username == 'admin_lahore').first()
        if not admin_lhr:
            admin_lhr = User(
                username='admin_lahore',
                role='ADMIN',
                full_name='District Education Officer (SE) Lahore',
                email='deo.se.lahore@sed.punjab.gov.pk',
                phone='042-99211111',
                district='Lahore',
                is_active=True,
                is_first_login=False
            )
            admin_lhr.set_password('Admin@123')
            db.add(admin_lhr)

        admin_rwp = db.query(User).filter(User.username == 'admin_rawalpindi').first()
        if not admin_rwp:
            admin_rwp = User(
                username='admin_rawalpindi',
                role='ADMIN',
                full_name='District Education Officer (SE) Rawalpindi',
                email='deo.se.rwp@sed.punjab.gov.pk',
                phone='051-99222222',
                district='Rawalpindi',
                is_active=True,
                is_first_login=False
            )
            admin_rwp.set_password('Admin@123')
            db.add(admin_rwp)

        db.flush()

        # 7. Seed 100 Realistic Teachers across Punjab with all scenarios
        seed_100_teachers(db)

        # 8. Predefined Teaching Posts (from punjab-school-education.pdf)
        seed_teaching_posts(db)

        db.commit()
        print("--- Database Seeding Complete Successfully! ---")

PREDEFINED_TEACHING_POSTS = [
    # Primary Cadre & Primary Educators
    {
        'post_code': 'PST_SCI_MATH',
        'post_title': 'Primary School Teacher - PST (Sci-Math)',
        'cadre': 'Primary Cadre',
        'basic_scale': 14,
        'category': 'Science-Math',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'B.Sc / BS (Science/Math) with B.Ed / ADE',
        'display_order': 10
    },
    {
        'post_code': 'PST_ARTS_GEN',
        'post_title': 'Primary School Teacher - PST (Arts / General)',
        'cadre': 'Primary Cadre',
        'basic_scale': 14,
        'category': 'Arts',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'BA / BS (Arts/Humanities) with B.Ed / ADE',
        'display_order': 20
    },
    {
        'post_code': 'ESE_SCI',
        'post_title': 'Elementary School Educator - ESE (Science)',
        'cadre': 'Educator Cadre',
        'basic_scale': 14,
        'category': 'Science',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'BS (16 Years) / Master in Physics, Chemistry, Biology, Mathematics',
        'display_order': 30
    },
    {
        'post_code': 'ESE_ARTS',
        'post_title': 'Elementary School Educator - ESE (Arts)',
        'cadre': 'Educator Cadre',
        'basic_scale': 14,
        'category': 'Arts',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'BS (16 Years) / Master in Urdu, English, Pak Studies, Islamiat, History, Geography',
        'display_order': 40
    },
    {
        'post_code': 'QARI_QARIA',
        'post_title': 'Qari / Qaria',
        'cadre': 'Primary Cadre',
        'basic_scale': 12,
        'category': 'Religious Education',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Shahadat-ul-Alia / Sanad Dars-e-Nizami with Qirat Certificate',
        'display_order': 50
    },

    # Elementary Cadre
    {
        'post_code': 'EST_SCIENCE',
        'post_title': 'Elementary School Teacher - EST (Science)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Science',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc / BS in Physics, Chemistry, Biology or Mathematics with B.Ed',
        'display_order': 100
    },
    {
        'post_code': 'EST_MATH',
        'post_title': 'Elementary School Teacher - EST (Mathematics)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Mathematics',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc / BS with Mathematics A & B with B.Ed',
        'display_order': 110
    },
    {
        'post_code': 'EST_ARTS',
        'post_title': 'Elementary School Teacher - EST (Arts / General)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Arts',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.A / BS in Arts/Humanities with B.Ed',
        'display_order': 120
    },
    {
        'post_code': 'EST_ENGLISH',
        'post_title': 'Elementary School Teacher - EST (English)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'English',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.A / BS with English Compulsory / Elective / Literature with B.Ed',
        'display_order': 130
    },
    {
        'post_code': 'EST_URDU',
        'post_title': 'Elementary School Teacher - EST (Urdu / Vernacular)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Urdu',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.A / BS with Urdu Elective / Literature with B.Ed',
        'display_order': 140
    },
    {
        'post_code': 'EST_CS_IT',
        'post_title': 'Elementary School Teacher - EST (Computer Science / IT)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Computer Science',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'BCS, BS CS, BS IT, MCS, MSc Computer Science with B.Ed',
        'display_order': 150
    },
    {
        'post_code': 'EST_ARABIC',
        'post_title': 'Elementary School Teacher - EST (Arabic)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Arabic',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 0,
        'prescribed_qualification': '(i) M.A Arabic (2nd Div) or B.A (2nd Div) with Shahadat-ul-Almia (16 Years equivalent recognized by HEC) / BS Arabic; and (ii) B.Ed, M.Ed or M.A (Education) (2nd Div)',
        'display_order': 160
    },
    {
        'post_code': 'EST_PET',
        'post_title': 'Elementary School Teacher - EST (Physical Education / PET)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Physical Education',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.A / B.Sc with Senior Diploma in Physical Education (SDPE)',
        'display_order': 170
    },
    {
        'post_code': 'EST_DM',
        'post_title': 'Elementary School Teacher - EST (Drawing Master / DM)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Drawing',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.A / B.FA with Diploma in Drawing / Fine Arts',
        'display_order': 180
    },
    {
        'post_code': 'EST_AGRI',
        'post_title': 'Elementary School Teacher - EST (Agriculture)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Agriculture',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc (Hons) Agriculture with B.Ed',
        'display_order': 190
    },
    {
        'post_code': 'EST_TECH',
        'post_title': 'Elementary School Teacher - EST (Technical / Tech)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Technical',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Tech / B.Sc Industrial Arts / DAE with B.Ed',
        'display_order': 200
    },
    {
        'post_code': 'EST_HOME_ECO',
        'post_title': 'Elementary School Teacher - EST (Home Economics)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Home Economics',
        'gender': 'Female',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc / BS Home Economics with B.Ed',
        'display_order': 210
    },
    {
        'post_code': 'EST_OT',
        'post_title': 'Elementary School Teacher - EST (Oriental / OT)',
        'cadre': 'Elementary Cadre',
        'basic_scale': 15,
        'category': 'Oriental Languages',
        'gender': 'Both',
        'feeder_post_title': 'Primary School Teacher (PST)',
        'min_service_years': 3,
        'prescribed_qualification': 'Fazil-e-Arabi / Fazil-e-Farsi / Fazil-e-Urdu with OT certificate',
        'display_order': 220
    },

    # Elementary Educators (SESE)
    {
        'post_code': 'SESE_SCI',
        'post_title': 'Senior Elementary School Educator - SESE (Science)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'Science',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'BS (16 Years) in Physics, Chemistry, Biology',
        'display_order': 230
    },
    {
        'post_code': 'SESE_MATH',
        'post_title': 'Senior Elementary School Educator - SESE (Mathematics)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'Mathematics',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'BS (16 Years) in Mathematics',
        'display_order': 240
    },
    {
        'post_code': 'SESE_ARTS',
        'post_title': 'Senior Elementary School Educator - SESE (Arts)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'Arts',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'BS (16 Years) in Arts / Humanities',
        'display_order': 250
    },
    {
        'post_code': 'SESE_ENG',
        'post_title': 'Senior Elementary School Educator - SESE (English)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'English',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'BS (16 Years) / MA in English',
        'display_order': 260
    },
    {
        'post_code': 'SESE_CS',
        'post_title': 'Senior Elementary School Educator - SESE (Computer Science)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'Computer Science',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'MCS, MIT, MSc IT, BS CS/IT (16 Years)',
        'display_order': 270
    },
    {
        'post_code': 'SESE_ARABIC',
        'post_title': 'Senior Elementary School Educator - SESE (Arabic)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'Arabic',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'MA / BS Arabic or Shahadat-ul-Alamia',
        'display_order': 280
    },
    {
        'post_code': 'SESE_PET',
        'post_title': 'Senior Elementary School Educator - SESE (PET)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'Physical Education',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master in Sports Sciences / BS Physical Education',
        'display_order': 290
    },
    {
        'post_code': 'SESE_DM',
        'post_title': 'Senior Elementary School Educator - SESE (DM)',
        'cadre': 'Educator Cadre',
        'basic_scale': 15,
        'category': 'Drawing',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master in Fine Arts / BFA (4 Years)',
        'display_order': 300
    },

    # Secondary Cadre (BS-16)
    {
        'post_code': 'SST_SCIENCE',
        'post_title': 'Secondary School Teacher - SST (Science)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Science',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc / BS (Science) with B.Ed / M.Ed',
        'display_order': 400
    },
    {
        'post_code': 'SST_MATH_PHY',
        'post_title': 'Secondary School Teacher - SST (Math & Physics)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Mathematics & Physics',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc / BS with Physics and Mathematics with B.Ed',
        'display_order': 410
    },
    {
        'post_code': 'SST_BIO_CHEM',
        'post_title': 'Secondary School Teacher - SST (Biology & Chemistry)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Biology & Chemistry',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc / BS with Chemistry and Biology (Botany/Zoology) with B.Ed',
        'display_order': 420
    },
    {
        'post_code': 'SST_ARTS_GEN',
        'post_title': 'Secondary School Teacher - SST (Arts / General)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Arts',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.A / BS (Arts/Humanities) with B.Ed',
        'display_order': 430
    },
    {
        'post_code': 'SST_ENGLISH',
        'post_title': 'Secondary School Teacher - SST (English)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'English',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.A / BS with English Literature or M.A English with B.Ed',
        'display_order': 440
    },
    {
        'post_code': 'SST_CS_IT',
        'post_title': 'Secondary School Teacher - SST (Computer Science / IT)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Computer Science',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'MCS, MIT, BS CS, BS IT, BS SE (16 Years) with B.Ed',
        'display_order': 450
    },
    {
        'post_code': 'SST_TECH',
        'post_title': 'Secondary School Teacher - SST (Technical)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Technical',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Tech (Hons) / B.Sc Engineering / B.Sc Industrial Arts with B.Ed',
        'display_order': 460
    },
    {
        'post_code': 'SST_COMMERCE',
        'post_title': 'Secondary School Teacher - SST (Commerce)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Commerce',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Com / M.Com / BS Commerce with B.Ed',
        'display_order': 470
    },
    {
        'post_code': 'SST_HOME_ECO',
        'post_title': 'Secondary School Teacher - SST (Home Economics)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Home Economics',
        'gender': 'Female',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'B.Sc / BS / M.Sc Home Economics with B.Ed',
        'display_order': 480
    },
    {
        'post_code': 'SST_PET',
        'post_title': 'Secondary School Teacher - SST (Physical Education)',
        'cadre': 'Secondary Cadre',
        'basic_scale': 16,
        'category': 'Physical Education',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'Master in Physical Education (MPE) / BS Sports Sciences with B.Ed',
        'display_order': 490
    },

    # Secondary Educators (SSE BS-16)
    {
        'post_code': 'SSE_SCIENCE',
        'post_title': 'Secondary School Educator - SSE (Science)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'Science',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in Physics/Chemistry/Botany/Zoology',
        'display_order': 500
    },
    {
        'post_code': 'SSE_MATH',
        'post_title': 'Secondary School Educator - SSE (Mathematics)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'Mathematics',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in Mathematics',
        'display_order': 510
    },
    {
        'post_code': 'SSE_CS',
        'post_title': 'Secondary School Educator - SSE (Computer Science)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'Computer Science',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in CS/IT/SE',
        'display_order': 520
    },
    {
        'post_code': 'SSE_ARTS',
        'post_title': 'Secondary School Educator - SSE (Arts)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'Arts',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in Urdu/English/Pak Studies/History',
        'display_order': 530
    },
    {
        'post_code': 'SSE_ENG',
        'post_title': 'Secondary School Educator - SSE (English)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'English',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in English',
        'display_order': 540
    },
    {
        'post_code': 'SSE_PHY',
        'post_title': 'Secondary School Educator - SSE (Physics)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'Physics',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in Physics',
        'display_order': 550
    },
    {
        'post_code': 'SSE_CHEM',
        'post_title': 'Secondary School Educator - SSE (Chemistry)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'Chemistry',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in Chemistry',
        'display_order': 560
    },
    {
        'post_code': 'SSE_BIO',
        'post_title': 'Secondary School Educator - SSE (Biology)',
        'cadre': 'Educator Cadre',
        'basic_scale': 16,
        'category': 'Biology',
        'gender': 'Both',
        'feeder_post_title': None,
        'min_service_years': 0,
        'prescribed_qualification': 'Master / BS (16 Years) in Botany / Zoology / Biology',
        'display_order': 570
    },

    # Higher Secondary & Administrative Cadres (BS-17 to BS-20)
    {
        'post_code': 'SS_PHYSICS',
        'post_title': 'Subject Specialist - SS Physics (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Physics',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Physics with B.Ed / M.Ed',
        'display_order': 600
    },
    {
        'post_code': 'SS_CHEMISTRY',
        'post_title': 'Subject Specialist - SS Chemistry (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Chemistry',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Chemistry with B.Ed / M.Ed',
        'display_order': 610
    },
    {
        'post_code': 'SS_BIOLOGY',
        'post_title': 'Subject Specialist - SS Biology (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Biology',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Botany / Zoology with B.Ed / M.Ed',
        'display_order': 620
    },
    {
        'post_code': 'SS_MATH',
        'post_title': 'Subject Specialist - SS Mathematics (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Mathematics',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Mathematics with B.Ed / M.Ed',
        'display_order': 630
    },
    {
        'post_code': 'SS_CS',
        'post_title': 'Subject Specialist - SS Computer Science (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Computer Science',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'MCS / MIT / BS CS / BS IT with B.Ed / M.Ed',
        'display_order': 640
    },
    {
        'post_code': 'SS_ENGLISH',
        'post_title': 'Subject Specialist - SS English (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'English',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in English with B.Ed / M.Ed',
        'display_order': 650
    },
    {
        'post_code': 'SS_URDU',
        'post_title': 'Subject Specialist - SS Urdu (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Urdu',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Urdu with B.Ed / M.Ed',
        'display_order': 660
    },
    {
        'post_code': 'SS_ISLAMIAT',
        'post_title': 'Subject Specialist - SS Islamiat (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Islamiat',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Islamiat / Islamic Studies with B.Ed',
        'display_order': 670
    },
    {
        'post_code': 'SS_PAK_STUDIES',
        'post_title': 'Subject Specialist - SS Pakistan Studies (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Pakistan Studies',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Pakistan Studies / History / Pol Sci with B.Ed',
        'display_order': 680
    },
    {
        'post_code': 'SS_ECONOMICS',
        'post_title': 'Subject Specialist - SS Economics (BS-17)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 17,
        'category': 'Economics',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Economics with B.Ed',
        'display_order': 690
    },
    {
        'post_code': 'HM_BS17',
        'post_title': 'Headmaster / Headmistress (BS-17)',
        'cadre': 'Administrative Cadre',
        'basic_scale': 17,
        'category': 'General / Administration',
        'gender': 'Both',
        'feeder_post_title': 'Secondary School Teacher (SST)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / BS (16 Years) in Arts or Science with B.Ed / M.Ed',
        'display_order': 700
    },
    {
        'post_code': 'AEO_BS16',
        'post_title': 'Assistant Education Officer - AEO (BS-16/17)',
        'cadre': 'Administrative Cadre',
        'basic_scale': 16,
        'category': 'Field Administration',
        'gender': 'Both',
        'feeder_post_title': 'Elementary School Teacher (EST)',
        'min_service_years': 3,
        'prescribed_qualification': 'Master / BS (16 Years) with B.Ed',
        'display_order': 710
    },
    {
        'post_code': 'SSS_ALL',
        'post_title': 'Senior Subject Specialist - SSS (BS-18)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 18,
        'category': 'Specialized Teaching',
        'gender': 'Both',
        'feeder_post_title': 'Subject Specialist (SS BS-17)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / M.Phil / PhD with 5 Years Service as Subject Specialist',
        'display_order': 720
    },
    {
        'post_code': 'SR_HM_BS18',
        'post_title': 'Senior Headmaster / Senior Headmistress (BS-18)',
        'cadre': 'Administrative Cadre',
        'basic_scale': 18,
        'category': 'Administration',
        'gender': 'Both',
        'feeder_post_title': 'Headmaster / Headmistress (BS-17)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / M.Ed with 5 Years Service as Headmaster / Headmistress',
        'display_order': 730
    },
    {
        'post_code': 'DY_DEO_BS18',
        'post_title': 'Deputy District Education Officer - Dy. DEO (BS-18)',
        'cadre': 'Administrative Cadre',
        'basic_scale': 18,
        'category': 'Educational Administration',
        'gender': 'Both',
        'feeder_post_title': 'Headmaster (BS-17) / AEO',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / M.Ed with Administrative Experience',
        'display_order': 740
    },
    {
        'post_code': 'DEO_BS19',
        'post_title': 'District Education Officer - DEO (BS-19)',
        'cadre': 'Administrative Cadre',
        'basic_scale': 19,
        'category': 'District Administration',
        'gender': 'Both',
        'feeder_post_title': 'Senior Headmaster / Dy. DEO / SSS (BS-18)',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / M.Phil with 12 Years gazetted service',
        'display_order': 750
    },
    {
        'post_code': 'PRINCIPAL_BS19',
        'post_title': 'Principal Higher Secondary / High School (BS-18/19)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 19,
        'category': 'Institutional Head',
        'gender': 'Both',
        'feeder_post_title': 'Senior Subject Specialist / Senior Headmaster',
        'min_service_years': 5,
        'prescribed_qualification': 'Master / M.Phil with Senior Administrative Experience',
        'display_order': 760
    },
    {
        'post_code': 'PRINCIPAL_BS20',
        'post_title': 'Principal Govt. Higher Secondary / Model School (BS-20)',
        'cadre': 'Higher Secondary Cadre',
        'basic_scale': 20,
        'category': 'Senior Leadership',
        'gender': 'Both',
        'feeder_post_title': 'Principal / DEO (BS-19)',
        'min_service_years': 4,
        'prescribed_qualification': '17 Years Gazetted Service in BS-17 and above, with 4 Years in BS-19',
        'display_order': 770
    },
    {
        'post_code': 'CEO_DEA_BS20',
        'post_title': 'Chief Executive Officer DEA / Director (BS-20)',
        'cadre': 'Administrative Cadre',
        'basic_scale': 20,
        'category': 'Executive Leadership',
        'gender': 'Both',
        'feeder_post_title': 'DEO / Principal (BS-19)',
        'min_service_years': 4,
        'prescribed_qualification': '17 Years Gazetted Service in BS-17 and above, with 4 Years in BS-19',
        'display_order': 780
    }
]

def seed_teaching_posts(db):
    """Seed or update official teaching posts according to Punjab School Education Department rules."""
    count = 0
    updated = 0
    for p_data in PREDEFINED_TEACHING_POSTS:
        existing = db.query(TeachingPost).filter(TeachingPost.post_code == p_data['post_code']).first()
        if not existing:
            p = TeachingPost(
                post_code=p_data['post_code'],
                post_title=p_data['post_title'],
                cadre=p_data['cadre'],
                basic_scale=p_data['basic_scale'],
                category=p_data['category'],
                gender=p_data.get('gender', 'Both'),
                feeder_post_title=p_data.get('feeder_post_title'),
                min_service_years=p_data.get('min_service_years', 0),
                prescribed_qualification=p_data.get('prescribed_qualification'),
                is_active=True,
                is_custom=False,
                display_order=p_data.get('display_order', 0)
            )
            db.add(p)
            count += 1
        else:
            existing.post_title = p_data['post_title']
            existing.cadre = p_data['cadre']
            existing.basic_scale = p_data['basic_scale']
            existing.category = p_data['category']
            existing.feeder_post_title = p_data.get('feeder_post_title')
            existing.min_service_years = p_data.get('min_service_years', 0)
            existing.prescribed_qualification = p_data.get('prescribed_qualification')
            existing.display_order = p_data.get('display_order', existing.display_order)
            updated += 1
    db.flush()
    if count > 0 or updated > 0:
        print(f"Seeded {count} and synchronized {updated} predefined teaching posts from SED Service Rules.")
    return count

if __name__ == '__main__':
    seed_database()

