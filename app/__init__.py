import os
from datetime import datetime
from functools import wraps
from flask import Flask, session, g, redirect, url_for, flash, request, abort, render_template, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.config import Config
from app.models.user import Base, User
from app.models.adsense import AdSenseSetting, AdSlot
from app.models.audit import SystemSetting
from app.models.post import TeachingPost

db_session = None

def get_db():
    global db_session
    return db_session

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this portal.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please sign in to access this portal.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            
            user_role = session.get('user_role')
            # SuperAdmin has universal master access to everything
            if user_role == 'SUPERADMIN':
                return f(*args, **kwargs)
            
            # Admin can access ADMIN and TEACHER sections
            if user_role == 'ADMIN' and ('ADMIN' in allowed_roles or 'TEACHER' in allowed_roles):
                return f(*args, **kwargs)

            # Check direct role match
            if user_role not in allowed_roles:
                flash("Access denied. You do not have permission for this section.", "danger")
                if user_role == 'TEACHER':
                    return redirect(url_for('teacher.dashboard'))
                elif user_role == 'ADMIN':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

PUNJAB_DISTRICTS = [
    "Attock", "Bahawalnagar", "Bahawalpur", "Bhakkar", "Chakwal", "Chiniot",
    "Dera Ghazi Khan", "Faisalabad", "Gujranwala", "Gujrat", "Hafizabad", "Jhang",
    "Jhelum", "Kasur", "Khanewal", "Khushab", "Kot Addu", "Lahore", "Layyah",
    "Lodhran", "Mandi Bahauddin", "Mianwali", "Multan", "Murree", "Muzaffargarh",
    "Nankana Sahib", "Narowal", "Okara", "Pakpattan", "Rahim Yar Khan", "Rajanpur",
    "Rawalpindi", "Sahiwal", "Sargodha", "Sheikhupura", "Sialkot", "Talagang",
    "Taunsa", "Toba Tek Singh", "Vehari", "Wazirabad"
]

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure uploads and backups directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['BACKUP_FOLDER'], exist_ok=True)

    # Initialize SQLAlchemy Engine & Session
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        connect_args={'check_same_thread': False} if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI'] else {}
    )
    Base.metadata.create_all(bind=engine)

    # Safe Schema Evolution / Column Verification
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN cnic VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE teachers ADD COLUMN previous_designation VARCHAR(80)"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE teachers ADD COLUMN previous_bs INTEGER"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE teachers ADD COLUMN previous_seniority_no INTEGER"))
            conn.commit()
        except Exception:
            pass
        for col_sql in [
            "ALTER TABLE teachers ADD COLUMN is_data_verified_by_teacher BOOLEAN DEFAULT 0",
            "ALTER TABLE teachers ADD COLUMN teacher_verified_at DATETIME",
            "ALTER TABLE teachers ADD COLUMN has_edited_records BOOLEAN DEFAULT 0",
            "ALTER TABLE teachers ADD COLUMN has_new_records BOOLEAN DEFAULT 0",
            "ALTER TABLE qualifications ADD COLUMN change_type VARCHAR(20)",
            "ALTER TABLE qualifications ADD COLUMN is_edited BOOLEAN DEFAULT 0",
            "ALTER TABLE qualifications ADD COLUMN is_new BOOLEAN DEFAULT 0",
            "ALTER TABLE service_history ADD COLUMN change_type VARCHAR(20)",
            "ALTER TABLE service_history ADD COLUMN is_edited BOOLEAN DEFAULT 0",
            "ALTER TABLE service_history ADD COLUMN is_new BOOLEAN DEFAULT 0",
            "ALTER TABLE correction_requests ADD COLUMN record_type VARCHAR(50) DEFAULT 'PERSONAL'",
            "ALTER TABLE correction_requests ADD COLUMN record_id INTEGER",
            "ALTER TABLE correction_requests ADD COLUMN target_attribute VARCHAR(100)",
            "ALTER TABLE correction_requests ADD COLUMN batch_id VARCHAR(50)",
            "ALTER TABLE teachers ADD COLUMN is_promotion_disabled BOOLEAN DEFAULT 0",
            "ALTER TABLE teachers ADD COLUMN promotion_disable_reason VARCHAR(100)",
            "ALTER TABLE teachers ADD COLUMN promotion_disable_remarks TEXT",
            "ALTER TABLE teachers ADD COLUMN promotion_disabled_at DATETIME",
            "ALTER TABLE teachers ADD COLUMN promotion_disabled_by VARCHAR(80)",
            "ALTER TABLE teachers ADD COLUMN retirement_order_no VARCHAR(100)",
            "ALTER TABLE teachers ADD COLUMN retirement_order_date DATE",
            "ALTER TABLE dpc_meetings ADD COLUMN end_date DATE",
            "ALTER TABLE pdf_settings ADD COLUMN is_stamp_enabled BOOLEAN DEFAULT 1",
            "ALTER TABLE pdf_settings ADD COLUMN signatories_json TEXT",
            "ALTER TABLE rule_sources ADD COLUMN version VARCHAR(20) DEFAULT '1.0'",
            "ALTER TABLE rule_sources ADD COLUMN effective_from DATE",
            "ALTER TABLE rule_sources ADD COLUMN effective_to DATE",
            "ALTER TABLE rule_sources ADD COLUMN amendment_notes TEXT",
            "ALTER TABLE promotion_rules ADD COLUMN version VARCHAR(20) DEFAULT '1.0'",
            "ALTER TABLE promotion_rules ADD COLUMN effective_from DATE",
            "ALTER TABLE promotion_rules ADD COLUMN effective_to DATE",
            "ALTER TABLE promotion_rules ADD COLUMN amendment_notes TEXT",
            "ALTER TABLE promotion_rules ADD COLUMN predecessor_rule_id INTEGER",
            "ALTER TABLE password_reset_requests ADD COLUMN personnel_no VARCHAR(50)",
            "ALTER TABLE password_reset_requests ADD COLUMN dispatch_channel VARCHAR(50)",
            "ALTER TABLE password_reset_requests ADD COLUMN teacher_id INTEGER",
            "ALTER TABLE password_reset_requests ADD COLUMN district VARCHAR(100)",
        ]:
            try:
                conn.execute(text(col_sql))
                conn.commit()
            except Exception:
                pass
    
    global db_session
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    # Load current user before each request and enforce session inactivity timeout
    @app.before_request
    def load_logged_in_user():
        g.db = db_session
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
        else:
            g.user = db_session.query(User).get(user_id)
            if not g.user or not g.user.is_active:
                session.clear()
                g.user = None
                return

            # Skip inactivity timeout check on the logout route itself so it can terminate gracefully
            if request.path.startswith('/auth/logout'):
                return

            # Check session inactivity timeout (10 minutes default)
            timeout_seconds = app.config.get('SESSION_INACTIVITY_TIMEOUT_MINUTES', 10) * 60
            last_activity = session.get('last_activity')
            now_ts = datetime.utcnow().timestamp()

            if last_activity is not None and (now_ts - last_activity > timeout_seconds):
                # Session has expired due to idle inactivity
                session.clear()
                g.user = None
                if request.is_json or request.path.startswith('/api/') or request.path in ['/auth/keep-alive', '/auth/session-status']:
                    return jsonify({'authenticated': False, 'message': 'Session expired due to inactivity', 'redirect': url_for('auth.login')}), 401
                flash("Your session has expired due to inactivity. Please sign in again.", "warning")
                return redirect(url_for('auth.login', timeout=1))

            # Refresh last activity timestamp for non-static asset requests
            if not request.path.startswith('/static'):
                session['last_activity'] = now_ts

    # Global Context Processors for Templates
    @app.context_processor
    def inject_global_data():
        user = getattr(g, 'user', None)
        adsense = None
        ad_slots_by_placement = {}
        teaching_posts = []
        pending_resets_count = 0
        pending_corrections_count = 0
        pending_retirements_count = 0
        try:
            from datetime import date
            from app.models.password_reset import PasswordResetRequest
            from app.models.correction import CorrectionRequest
            from app.models.teacher import Teacher
            adsense = db_session.query(AdSenseSetting).first()
            slots = db_session.query(AdSlot).filter(AdSlot.is_active == True).all()
            for s in slots:
                if user and s.target_roles != 'ALL' and user.role not in s.target_roles:
                    continue
                ad_slots_by_placement.setdefault(s.placement, []).append(s)

            teaching_posts = db_session.query(TeachingPost).filter(TeachingPost.is_active == True).order_by(TeachingPost.basic_scale.asc(), TeachingPost.display_order.asc(), TeachingPost.post_title.asc()).all()
            
            if user and user.role == 'SUPERADMIN':
                pending_resets_count = db_session.query(PasswordResetRequest).filter(PasswordResetRequest.status == 'Pending').count()
            elif user and user.role == 'ADMIN':
                admin_district = getattr(user, 'district', None)
                if admin_district:
                    pending_resets_count = db_session.query(PasswordResetRequest).filter(
                        PasswordResetRequest.status == 'Pending',
                        PasswordResetRequest.account_role == 'TEACHER',
                        (PasswordResetRequest.district == admin_district) | (PasswordResetRequest.district.is_(None))
                    ).count()
                else:
                    pending_resets_count = db_session.query(PasswordResetRequest).filter(
                        PasswordResetRequest.status == 'Pending',
                        PasswordResetRequest.account_role == 'TEACHER'
                    ).count()
            if user and user.role in ('ADMIN', 'SUPERADMIN'):
                pending_corrections_count = db_session.query(CorrectionRequest).filter(CorrectionRequest.status == 'Pending').count()
                # Count teachers aged 60+ who are not marked as Retired
                cutoff_dob = date.today().replace(year=date.today().year - 60)
                pending_retirements_count = db_session.query(Teacher).filter(
                    Teacher.is_deleted == False,
                    Teacher.account_status != 'Retired',
                    Teacher.date_of_birth <= cutoff_dob
                ).count()
        except Exception:
            pass

        return {
            'current_user': user,
            'app_name': Config.APP_NAME,
            'app_subtitle': Config.APP_SUBTITLE,
            'department': Config.DEPARTMENT,
            'app_version': Config.VERSION,
            'session_timeout_minutes': Config.SESSION_INACTIVITY_TIMEOUT_MINUTES,
            'session_timeout_seconds': Config.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60,
            'adsense': adsense,
            'ad_slots': ad_slots_by_placement,
            'active_teaching_posts': teaching_posts,
            'punjab_districts': PUNJAB_DISTRICTS,
            'pending_password_resets_count': pending_resets_count,
            'pending_corrections_count': pending_corrections_count,
            'pending_retirements_count': pending_retirements_count
        }

    @app.template_filter('display_role')
    def display_role_filter(role):
        if not role:
            return ''
        mapping = {
            'SUPERADMIN': 'Provincial Administrator',
            'ADMIN': 'District Administrator',
            'TEACHER': 'Teacher'
        }
        return mapping.get(str(role).upper(), str(role))

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.superadmin_routes import superadmin_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.teacher_routes import teacher_bp
    from app.routes.api_routes import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(superadmin_bp, url_prefix='/superadmin')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        from app.models.teacher import Teacher
        from app.models.rule import PromotionRule
        from app.models.vacancy import Vacancy
        
        # If logged in and no explicit ?view=home requested, redirect to respective role dashboard
        if 'user_id' in session and request.args.get('view') != 'home':
            role = session.get('user_role')
            if role == 'SUPERADMIN':
                return redirect(url_for('superadmin.dashboard'))
            elif role == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('teacher.dashboard'))

        # Fetch public statistics for high-impact landing page
        try:
            stats = {
                'total_teachers': db_session.query(Teacher).filter(Teacher.is_deleted == False).count(),
                'total_rules': db_session.query(PromotionRule).filter(PromotionRule.is_active == True).count(),
                'total_vacancies': db_session.query(Vacancy).count(),
                'total_districts': len(PUNJAB_DISTRICTS)
            }
        except Exception:
            stats = {'total_teachers': 100, 'total_rules': 12, 'total_vacancies': 9, 'total_districts': 41}

        return render_template('home.html', stats=stats)

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('base.html', error_code=403, error_message="Access Forbidden. Insufficient permissions."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html', error_code=404, error_message="Requested resource not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('base.html', error_code=500, error_message="An internal server error occurred."), 500

    return app
