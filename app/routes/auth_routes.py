from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from app.config import Config
from app.models.user import User
from app.models.teacher import Teacher
from app.models.password_reset import PasswordResetRequest
from app.services.audit_service import log_audit

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'SUPERADMIN':
            return redirect(url_for('superadmin.dashboard'))
        elif role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '').strip()

        if not login_id or not password:
            flash("Please enter both login identifier and password.", "danger")
            return render_template('auth/login.html')

        db = g.db
        # Allow login by Username, direct User CNIC, or linked Teacher CNIC / Personnel No
        user = db.query(User).filter((User.username == login_id) | (User.cnic == login_id)).first()
        if not user:
            cnic_clean = login_id.replace('-', '').replace(' ', '')
            if len(cnic_clean) == 13:
                std_cnic = f"{cnic_clean[:5]}-{cnic_clean[5:12]}-{cnic_clean[12]}"
                user = db.query(User).filter(User.cnic == std_cnic).first()
        if not user:
            # Try searching by CNIC in teachers
            cnic_clean = login_id.replace('-', '').replace(' ', '')
            teacher = db.query(Teacher).filter(
                (Teacher.cnic == login_id) | 
                (Teacher.cnic == f"{cnic_clean[:5]}-{cnic_clean[5:12]}-{cnic_clean[12]}" if len(cnic_clean) == 13 else False) |
                (Teacher.personnel_no == login_id)
            ).first()
            if teacher:
                user = db.query(User).filter(User.teacher_id == teacher.id).first()

        if not user or not user.check_password(password):
            flash("Invalid credentials. Please verify your username / CNIC and password.", "danger")
            return render_template('auth/login.html')

        if not user.is_active:
            flash("Your account has been deactivated or suspended. Please contact your administrator.", "danger")
            return render_template('auth/login.html')

        # Authentication successful
        session.clear()
        session.permanent = True
        now_ts = datetime.utcnow().timestamp()
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['username'] = user.username
        session['full_name'] = user.full_name
        session['teacher_id'] = user.teacher_id
        session['last_activity'] = now_ts
        session['show_login_guide'] = True

        user.last_login = datetime.utcnow()
        user.failed_login_attempts = 0
        db.commit()

        log_audit(db, user, 'LOGIN_SUCCESS', entity_type='User', entity_id=user.id, details="User logged in successfully", ip_address=request.remote_addr)

        if user.is_first_login and user.role == 'TEACHER':
            flash("Welcome! As this is your initial login, please set a personal secure password.", "info")
            return redirect(url_for('auth.change_password'))

        flash(f"Welcome back, {user.full_name}!", "success")
        if user.role == 'SUPERADMIN':
            return redirect(url_for('superadmin.dashboard'))
        elif user.role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('teacher.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    db = g.db
    reason = request.args.get('reason', 'manual')
    if g.user:
        detail_msg = "User session expired due to inactivity" if reason == 'timeout' else "User logged out safely"
        log_audit(db, g.user, 'LOGOUT', entity_type='User', entity_id=g.user.id, details=detail_msg, ip_address=request.remote_addr)
    session.clear()
    if reason == 'timeout':
        flash("Your session has expired due to inactivity. Please sign in again to continue.", "warning")
    else:
        flash("You have been signed out safely.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/keep-alive', methods=['GET', 'POST'])
def keep_alive():
    """Lightweight endpoint for extending user session on activity or warning dialog confirmation."""
    if 'user_id' not in session or not g.user:
        return jsonify({
            'status': 'unauthorized',
            'authenticated': False,
            'message': 'No active session found',
            'redirect': url_for('auth.login')
        }), 401

    now_ts = datetime.utcnow().timestamp()
    session['last_activity'] = now_ts
    timeout_seconds = Config.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60
    return jsonify({
        'status': 'ok',
        'authenticated': True,
        'user': g.user.username,
        'role': g.user.role,
        'last_activity': now_ts,
        'timeout_seconds': timeout_seconds,
        'remaining_seconds': timeout_seconds
    })

@auth_bp.route('/session-status')
def session_status():
    """Returns current session status, remaining seconds, and authenticated state."""
    timeout_seconds = Config.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60
    if 'user_id' not in session or not g.user:
        return jsonify({
            'status': 'unauthenticated',
            'authenticated': False,
            'remaining_seconds': 0,
            'timeout_seconds': timeout_seconds
        })

    last_activity = session.get('last_activity', datetime.utcnow().timestamp())
    now_ts = datetime.utcnow().timestamp()
    elapsed = max(0, int(now_ts - last_activity))
    remaining = max(0, int(timeout_seconds - elapsed))
    return jsonify({
        'status': 'active',
        'authenticated': True,
        'user': g.user.username,
        'role': g.user.role,
        'elapsed_seconds': elapsed,
        'remaining_seconds': remaining,
        'timeout_seconds': timeout_seconds
    })

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = g.user
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not user.is_first_login and not user.check_password(current_password):
            flash("Current password entered is incorrect.", "danger")
            return render_template('auth/change_password.html')

        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "danger")
            return render_template('auth/change_password.html')

        if new_password != confirm_password:
            flash("New passwords do not match. Please re-enter.", "danger")
            return render_template('auth/change_password.html')

        user.set_password(new_password)
        user.is_first_login = False
        g.db.commit()

        log_audit(g.db, user, 'PASSWORD_CHANGE', entity_type='User', entity_id=user.id, details="User updated password", ip_address=request.remote_addr)
        flash("Password updated successfully!", "success")

        if user.role == 'SUPERADMIN':
            return redirect(url_for('superadmin.dashboard'))
        elif user.role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('teacher.dashboard'))

    return render_template('auth/change_password.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Public Registration Route: Enforces that signups are strictly as Department Administrator (ADMIN)."""
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'SUPERADMIN':
            return redirect(url_for('superadmin.dashboard'))
        elif role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        cnic = request.form.get('cnic', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        district = request.form.get('district', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validation
        if not full_name or not username or not cnic or not phone or not email or not password:
            flash("All required fields must be completed.", "danger")
            return render_template('auth/register.html', form_data=request.form)

        db = g.db
        # Format and validate CNIC
        cnic_clean = cnic.replace('-', '').replace(' ', '')
        if len(cnic_clean) != 13 or not cnic_clean.isdigit():
            flash("CNIC must be a valid 13-digit Pakistani National Identity Card number (e.g. 35201-1234567-1).", "danger")
            return render_template('auth/register.html', form_data=request.form)
        formatted_cnic = f"{cnic_clean[:5]}-{cnic_clean[5:12]}-{cnic_clean[12]}"

        # Check existing username or CNIC
        if db.query(User).filter(User.username == username).first():
            flash(f"The username '{username}' is already taken. Please choose another official username.", "danger")
            return render_template('auth/register.html', form_data=request.form)

        if db.query(User).filter((User.cnic == formatted_cnic) | (User.cnic == cnic)).first():
            flash(f"An administrator account is already registered with CNIC {formatted_cnic}.", "danger")
            return render_template('auth/register.html', form_data=request.form)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('auth/register.html', form_data=request.form)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter carefully.", "danger")
            return render_template('auth/register.html', form_data=request.form)

        # Create new Admin User (Always ADMIN as per requirement)
        new_admin = User(
            username=username,
            full_name=full_name,
            role='ADMIN',
            cnic=formatted_cnic,
            phone=phone,
            email=email,
            district=district if district else None,
            is_active=True,
            is_first_login=False
        )
        new_admin.set_password(password)
        db.add(new_admin)
        db.commit()

        log_audit(db, new_admin, 'ADMIN_SELF_REGISTRATION', entity_type='User', entity_id=new_admin.id,
                  details=f"New Department Admin registered: {username} ({full_name}) for District {district or 'General'}",
                  ip_address=request.remote_addr)

        flash(f"Administrator account for '{full_name}' registered successfully! You may now sign in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form_data={})

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot Password Route: Users submit CNIC, Phone, and Email; logged for SuperAdmin manual review and dispatch."""
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        cnic = request.form.get('cnic', '').strip()
        personnel_no = request.form.get('personnel_no', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        notes = request.form.get('notes', '').strip()

        if not cnic or not phone or not email:
            flash("CNIC, Phone Number, and Email Address are all mandatory for password reset verification.", "danger")
            return render_template('auth/forgot_password.html', form_data=request.form)

        db = g.db
        cnic_clean = cnic.replace('-', '').replace(' ', '')
        if len(cnic_clean) != 13 or not cnic_clean.isdigit():
            flash("Please enter a valid 13-digit CNIC (e.g. 35201-1234567-1).", "danger")
            return render_template('auth/forgot_password.html', form_data=request.form)
        formatted_cnic = f"{cnic_clean[:5]}-{cnic_clean[5:12]}-{cnic_clean[12]}"

        # Look up matching account in Teacher or User
        matched_user = None
        teacher = None

        # 1. Search in Teacher by CNIC or Personnel Number
        teacher_query = db.query(Teacher).filter(
            (Teacher.cnic == formatted_cnic) | (Teacher.cnic == cnic)
        )
        if personnel_no:
            teacher_query = db.query(Teacher).filter(
                ((Teacher.cnic == formatted_cnic) | (Teacher.cnic == cnic)) | (Teacher.personnel_no == personnel_no)
            )
        teacher = teacher_query.first()

        if teacher:
            matched_user = db.query(User).filter(User.teacher_id == teacher.id).first()
            if not matched_user:
                matched_user = db.query(User).filter(
                    (User.cnic == formatted_cnic) | (User.username == formatted_cnic) | (User.username == teacher.cnic)
                ).first()

        # 2. Search directly in User by CNIC or username
        if not matched_user:
            matched_user = db.query(User).filter(
                (User.cnic == formatted_cnic) | (User.cnic == cnic) | (User.username == formatted_cnic) | (User.username == cnic)
            ).first()
            if matched_user and matched_user.teacher_id:
                teacher = db.query(Teacher).get(matched_user.teacher_id)

        # 3. Fallback search by email
        if not matched_user and email:
            matched_user = db.query(User).filter(User.email == email).first()
            if matched_user and matched_user.teacher_id and not teacher:
                teacher = db.query(Teacher).get(matched_user.teacher_id)

        role_str = 'TEACHER' if teacher else (matched_user.role if matched_user else 'UNRESOLVED')
        name_str = teacher.full_name if teacher else (matched_user.full_name if matched_user else 'Candidate Pending Verification')
        p_no = personnel_no or (teacher.personnel_no if teacher else None)
        district_str = teacher.district if teacher else (matched_user.district if matched_user else None)

        # Create PasswordResetRequest ticket
        req = PasswordResetRequest(
            user_id=matched_user.id if matched_user else None,
            teacher_id=teacher.id if teacher else None,
            district=district_str,
            cnic=formatted_cnic,
            personnel_no=p_no,
            phone=phone,
            email=email,
            account_username=matched_user.username if matched_user else (formatted_cnic if teacher else 'Unknown / Not Found'),
            account_role=role_str,
            user_full_name=name_str,
            user_notes=notes,
            status='Pending'
        )
        db.add(req)
        db.commit()

        log_audit(db, matched_user, 'PASSWORD_RESET_REQUESTED', entity_type='PasswordResetRequest', entity_id=req.id,
                  details=f"Password reset ticket #{req.id} submitted for {role_str} {name_str} (CNIC: {formatted_cnic}, P#: {p_no}, Phone: {phone}, Email: {email})",
                  ip_address=request.remote_addr)

        return render_template('auth/forgot_password.html', ticket_submitted=True, ticket=req)

    return render_template('auth/forgot_password.html', form_data={})
