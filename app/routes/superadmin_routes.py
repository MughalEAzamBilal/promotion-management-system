import os
import shutil
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, send_file, current_app
from app import role_required
from app.models.user import User
from app.models.teacher import Teacher
from app.models.rule import RuleSource, PromotionRule
from app.models.vacancy import Vacancy
from app.models.adsense import AdSenseSetting, AdSlot
from app.models.audit import AuditLog, SystemSetting
from app.models.password_reset import PasswordResetRequest
from app.services.audit_service import log_audit

superadmin_bp = Blueprint('superadmin', __name__)

@superadmin_bp.route('/')
@superadmin_bp.route('/dashboard')
@role_required(['SUPERADMIN'])
def dashboard():
    db = g.db
    # Gather System Health & Counts
    total_users = db.query(User).count()
    total_admins = db.query(User).filter(User.role == 'ADMIN').count()
    total_teachers = db.query(Teacher).filter(Teacher.is_deleted == False).count()
    pending_verifications = db.query(Teacher).filter(Teacher.verification_status == 'Pending', Teacher.is_deleted == False).count()
    pending_password_resets = db.query(PasswordResetRequest).filter(PasswordResetRequest.status == 'Pending').count()
    total_rules = db.query(PromotionRule).filter(PromotionRule.is_active == True).count()
    total_rule_sources = db.query(RuleSource).count()
    total_vacancies = db.query(Vacancy).count()
    recent_logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()

    # Database file health
    db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2) if os.path.exists(db_path) else 0.0

    system_health = {
        'database_status': 'Healthy (Operational)',
        'database_size_mb': db_size_mb,
        'storage_status': 'Healthy',
        'background_jobs': 'Active',
        'environment': 'Production-Ready (Windows/Linux WSGI)'
    }

    return render_template(
        'superadmin/dashboard.html',
        total_users=total_users,
        total_admins=total_admins,
        total_teachers=total_teachers,
        pending_verifications=pending_verifications,
        pending_password_resets=pending_password_resets,
        total_rules=total_rules,
        total_rule_sources=total_rule_sources,
        total_vacancies=total_vacancies,
        recent_logs=recent_logs,
        system_health=system_health
    )

@superadmin_bp.route('/admins', methods=['GET', 'POST'])
@role_required(['SUPERADMIN'])
def manage_admins():
    db = g.db
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            username = request.form.get('username', '').strip()
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            district = request.form.get('district', '').strip()
            password = request.form.get('password', '').strip()

            if not username or not password or not full_name:
                flash("Username, Full Name, and Password are required.", "danger")
            elif db.query(User).filter(User.username == username).first():
                flash("An administrator with this username already exists.", "danger")
            else:
                new_admin = User(
                    username=username,
                    role='ADMIN',
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    district=district,
                    is_active=True,
                    is_first_login=False
                )
                new_admin.set_password(password)
                db.add(new_admin)
                db.commit()
                log_audit(db, g.user, 'CREATE_ADMIN', entity_type='User', entity_id=new_admin.id, details=f"Created Admin user: {username} ({district})", ip_address=request.remote_addr)
                flash(f"Administrator '{full_name}' created successfully.", "success")
                return redirect(url_for('superadmin.manage_admins'))

        elif action == 'toggle_status':
            admin_id = request.form.get('admin_id')
            admin = db.query(User).get(admin_id)
            if admin and admin.role == 'ADMIN':
                admin.is_active = not admin.is_active
                db.commit()
                status_str = "Activated" if admin.is_active else "Deactivated"
                log_audit(db, g.user, 'TOGGLE_ADMIN_STATUS', entity_type='User', entity_id=admin.id, details=f"{status_str} admin: {admin.username}", ip_address=request.remote_addr)
                flash(f"Administrator '{admin.username}' {status_str}.", "info")
                return redirect(url_for('superadmin.manage_admins'))

        elif action == 'reset_password':
            admin_id = request.form.get('admin_id')
            new_pass = request.form.get('new_password', '').strip()
            admin = db.query(User).get(admin_id)
            if admin and admin.role == 'ADMIN' and new_pass:
                admin.set_password(new_pass)
                db.commit()
                log_audit(db, g.user, 'RESET_ADMIN_PASSWORD', entity_type='User', entity_id=admin.id, details=f"Reset password for admin: {admin.username}", ip_address=request.remote_addr)
                flash(f"Password for administrator '{admin.username}' reset successfully.", "success")
                return redirect(url_for('superadmin.manage_admins'))

    admins = db.query(User).filter(User.role == 'ADMIN').order_by(User.created_at.desc()).all()
    return render_template('superadmin/admins.html', admins=admins)

@superadmin_bp.route('/adsense', methods=['GET', 'POST'])
@role_required(['SUPERADMIN'])
def manage_adsense():
    db = g.db
    adsense = db.query(AdSenseSetting).first()
    if not adsense:
        adsense = AdSenseSetting()
        db.add(adsense)
        db.commit()

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'settings':
            adsense.publisher_id = request.form.get('publisher_id', '').strip()
            adsense.ads_enabled = bool(request.form.get('ads_enabled'))
            adsense.auto_ads_enabled = bool(request.form.get('auto_ads_enabled'))
            adsense.test_mode = bool(request.form.get('test_mode'))
            adsense.header_code = request.form.get('header_code', '').strip()
            db.commit()
            log_audit(db, g.user, 'UPDATE_ADSENSE_CONFIG', entity_type='AdSenseSetting', entity_id=adsense.id, details="Updated Google AdSense global configuration", ip_address=request.remote_addr)
            flash("Google AdSense settings updated successfully.", "success")
            return redirect(url_for('superadmin.manage_adsense'))

        elif form_type == 'add_slot':
            name = request.form.get('slot_name', '').strip()
            slot_id = request.form.get('slot_id', '').strip()
            placement = request.form.get('placement', 'header')
            slot_format = request.form.get('slot_format', 'responsive')
            target_roles = request.form.get('target_roles', 'ALL')

            if name and slot_id:
                new_slot = AdSlot(
                    slot_name=name,
                    slot_id=slot_id,
                    placement=placement,
                    slot_format=slot_format,
                    target_roles=target_roles,
                    is_active=True
                )
                db.add(new_slot)
                db.commit()
                log_audit(db, g.user, 'CREATE_AD_SLOT', entity_type='AdSlot', entity_id=new_slot.id, details=f"Added AdSlot '{name}' ({placement})", ip_address=request.remote_addr)
                flash(f"Ad slot '{name}' created successfully.", "success")
                return redirect(url_for('superadmin.manage_adsense'))

        elif form_type == 'toggle_slot':
            slot_id = request.form.get('slot_id')
            slot = db.query(AdSlot).get(slot_id)
            if slot:
                slot.is_active = not slot.is_active
                db.commit()
                flash(f"Ad slot '{slot.slot_name}' {'enabled' if slot.is_active else 'disabled'}.", "info")
                return redirect(url_for('superadmin.manage_adsense'))

        elif form_type == 'delete_slot':
            slot_id = request.form.get('slot_id')
            slot = db.query(AdSlot).get(slot_id)
            if slot:
                db.delete(slot)
                db.commit()
                flash("Ad slot deleted.", "info")
                return redirect(url_for('superadmin.manage_adsense'))

    slots_list = db.query(AdSlot).order_by(AdSlot.placement).all()
    return render_template('superadmin/adsense.html', adsense=adsense, slots_list=slots_list)

@superadmin_bp.route('/rules', methods=['GET', 'POST'])
@role_required(['SUPERADMIN'])
def manage_rules():
    db = g.db
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_source':
            title = request.form.get('title', '').strip()
            notif_no = request.form.get('notification_no', '').strip()
            notif_date_str = request.form.get('notification_date')
            summary = request.form.get('document_summary', '').strip()
            authority = request.form.get('issuing_authority', 'S&GAD / SED').strip()

            notif_date = datetime.strptime(notif_date_str, '%Y-%m-%d').date() if notif_date_str else datetime.utcnow().date()
            src = RuleSource(
                title=title,
                notification_no=notif_no,
                notification_date=notif_date,
                effective_date=notif_date,
                issuing_authority=authority,
                document_summary=summary,
                is_active=True
            )
            db.add(src)
            db.commit()
            log_audit(db, g.user, 'CREATE_RULE_SOURCE', entity_type='RuleSource', entity_id=src.id, details=f"Added Rule Source: {notif_no}", ip_address=request.remote_addr)
            flash(f"Rule Source '{notif_no}' registered successfully.", "success")
            return redirect(url_for('superadmin.manage_rules'))

        elif action == 'create_rule':
            source_id = int(request.form.get('source_id'))
            code = request.form.get('rule_code', '').strip().upper()
            name = request.form.get('rule_name', '').strip()
            src_desig = request.form.get('source_designation', '').strip()
            src_bs = int(request.form.get('source_bs', 14))
            tgt_desig = request.form.get('target_designation', '').strip()
            tgt_bs = int(request.form.get('target_bs', 15))
            cat = request.form.get('promotion_category', 'General').strip()
            min_service = float(request.form.get('min_regular_service_years', 3.0))
            req_level = request.form.get('required_degree_level', 'Bachelor').strip()
            req_degrees = request.form.get('required_degree_names', '').strip()
            req_subjects = request.form.get('required_subjects', '').strip()
            req_prof = request.form.get('required_professional_degree', 'B.Ed').strip()
            quota = float(request.form.get('quota_percentage', 50.0))

            new_rule = PromotionRule(
                source_id=source_id,
                rule_code=code,
                rule_name=name,
                source_designation=src_desig,
                source_bs=src_bs,
                target_designation=tgt_desig,
                target_bs=tgt_bs,
                promotion_category=cat,
                min_regular_service_years=min_service,
                min_total_service_years=min_service,
                required_degree_level=req_level,
                required_degree_names=req_degrees,
                required_subjects=req_subjects,
                required_professional_degree=req_prof,
                quota_percentage=quota,
                is_active=True
            )
            db.add(new_rule)
            db.commit()
            log_audit(db, g.user, 'CREATE_PROMOTION_RULE', entity_type='PromotionRule', entity_id=new_rule.id, details=f"Configured Rule: {code} ({src_desig} -> {tgt_desig})", ip_address=request.remote_addr)
            flash(f"Promotion Rule '{name}' configured successfully.", "success")
            return redirect(url_for('superadmin.manage_rules'))

        elif action == 'edit_rule':
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
                return redirect(url_for('superadmin.manage_rules'))

    sources = db.query(RuleSource).order_by(RuleSource.created_at.desc()).all()
    rules = db.query(PromotionRule).order_by(PromotionRule.source_bs, PromotionRule.target_bs).all()
    return render_template('superadmin/rules_manager.html', sources=sources, rules=rules)

@superadmin_bp.route('/system-settings', methods=['GET', 'POST'])
@role_required(['SUPERADMIN'])
def system_settings():
    db = g.db
    if request.method == 'POST':
        app_title = request.form.get('app_title', '').strip()
        dept_name = request.form.get('dept_name', '').strip()
        announcement = request.form.get('announcement', '').strip()
        maintenance_mode = request.form.get('maintenance_mode', 'false')

        settings_dict = {
            'app_title': app_title,
            'department_name': dept_name,
            'announcement_banner': announcement,
            'maintenance_mode': maintenance_mode
        }

        for k, v in settings_dict.items():
            setting = db.query(SystemSetting).filter(SystemSetting.setting_key == k).first()
            if not setting:
                setting = SystemSetting(setting_key=k, setting_value=v)
                db.add(setting)
            else:
                setting.setting_value = v
        db.commit()
        log_audit(db, g.user, 'UPDATE_SYSTEM_SETTINGS', entity_type='SystemSetting', details="Updated global application settings", ip_address=request.remote_addr)
        flash("System settings saved successfully.", "success")
        return redirect(url_for('superadmin.system_settings'))

    settings_rows = db.query(SystemSetting).all()
    settings_map = {s.setting_key: s.setting_value for s in settings_rows}
    return render_template('superadmin/system_settings.html', settings_map=settings_map)

@superadmin_bp.route('/audit-logs')
@role_required(['SUPERADMIN'])
def audit_logs():
    db = g.db
    action_filter = request.args.get('action')
    query = db.query(AuditLog)
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    logs = query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template('superadmin/audit_logs.html', logs=logs, selected_action=action_filter)

@superadmin_bp.route('/backups', methods=['GET', 'POST'])
@role_required(['SUPERADMIN'])
def backups():
    backup_dir = current_app.config['BACKUP_FOLDER']
    db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_backup':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"teacher_promotion_backup_{timestamp}.db"
            dest_path = os.path.join(backup_dir, backup_filename)
            shutil.copy2(db_path, dest_path)
            log_audit(g.db, g.user, 'CREATE_DATABASE_BACKUP', entity_type='Backup', details=f"Generated database snapshot: {backup_filename}", ip_address=request.remote_addr)
            flash(f"Database backup '{backup_filename}' created successfully.", "success")
            return redirect(url_for('superadmin.backups'))

    # List available backup files
    backup_files = []
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            if f.endswith('.db'):
                fp = os.path.join(backup_dir, f)
                backup_files.append({
                    'filename': f,
                    'size_mb': round(os.path.getsize(fp) / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(os.path.getctime(fp)).strftime('%Y-%m-%d %H:%M:%S')
                })
    backup_files.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('superadmin/backups.html', backup_files=backup_files)

@superadmin_bp.route('/backups/download/<filename>')
@role_required(['SUPERADMIN'])
def download_backup(filename):
    backup_dir = current_app.config['BACKUP_FOLDER']
    filepath = os.path.join(backup_dir, filename)
    if os.path.exists(filepath):
        log_audit(g.db, g.user, 'DOWNLOAD_DATABASE_BACKUP', entity_type='Backup', details=f"Downloaded backup file: {filename}", ip_address=request.remote_addr)
        return send_file(filepath, as_attachment=True, download_name=filename)
    flash("Backup file not found.", "danger")
    return redirect(url_for('superadmin.backups'))

@superadmin_bp.route('/password-resets', methods=['GET', 'POST'])
@role_required(['SUPERADMIN'])
def password_resets():
    """SuperAdmin Management Console for reviewing and manually dispatching passwords for forgot-password claims."""
    db = g.db
    if request.method == 'POST':
        action = request.form.get('action')
        ticket_id = request.form.get('ticket_id')
        ticket = db.query(PasswordResetRequest).get(ticket_id)

        if not ticket:
            flash("Password reset ticket not found.", "danger")
            return redirect(url_for('superadmin.password_resets'))

        if action == 'process':
            new_password = request.form.get('new_password', '').strip()
            dispatch_channel = request.form.get('dispatch_channel', 'Official SMS').strip()
            admin_notes = request.form.get('admin_notes', '').strip()

            if not new_password:
                flash("Please provide the new password to set and communicate to the user.", "danger")
                return redirect(url_for('superadmin.password_resets'))

            # Locate user to update password
            target_user = None
            if ticket.user_id:
                target_user = db.query(User).get(ticket.user_id)
            if not target_user and ticket.cnic:
                target_user = db.query(User).filter(
                    (User.cnic == ticket.cnic) | (User.username == ticket.cnic)
                ).first()
                if not target_user:
                    teacher = db.query(Teacher).filter(Teacher.cnic == ticket.cnic).first()
                    if teacher:
                        target_user = db.query(User).filter(User.teacher_id == teacher.id).first()

            if target_user:
                target_user.set_password(new_password)
                target_user.failed_login_attempts = 0
                target_user.locked_until = None
                target_user.is_active = True
                user_updated_info = f"Password updated on account {target_user.username} ({target_user.role})"
            else:
                user_updated_info = "No direct database account matched; issued manual verification token"

            ticket.status = 'Processed'
            ticket.temporary_password_set = new_password
            full_notes = f"[{dispatch_channel}] {admin_notes}".strip()
            ticket.admin_response_notes = full_notes
            ticket.processed_by = g.user.username
            ticket.processed_at = datetime.utcnow()
            db.commit()

            log_audit(db, g.user, 'PASSWORD_RESET_DISPATCHED', entity_type='PasswordResetRequest', entity_id=ticket.id,
                      details=f"Processed password reset ticket #{ticket.id} for CNIC {ticket.cnic}. Channel: {dispatch_channel}. {user_updated_info}",
                      ip_address=request.remote_addr)

            flash(f"Ticket #{ticket.id} processed successfully! Password set to '{new_password}' and logged as dispatched via {dispatch_channel}.", "success")
            return redirect(url_for('superadmin.password_resets'))

        elif action == 'reject':
            rejection_reason = request.form.get('rejection_reason', 'Discrepancy in CNIC/contact details').strip()
            ticket.status = 'Rejected'
            ticket.admin_response_notes = rejection_reason
            ticket.processed_by = g.user.username
            ticket.processed_at = datetime.utcnow()
            db.commit()

            log_audit(db, g.user, 'PASSWORD_RESET_REJECTED', entity_type='PasswordResetRequest', entity_id=ticket.id,
                      details=f"Rejected password reset ticket #{ticket.id} for CNIC {ticket.cnic}: {rejection_reason}",
                      ip_address=request.remote_addr)

            flash(f"Ticket #{ticket.id} has been marked as Rejected.", "warning")
            return redirect(url_for('superadmin.password_resets'))

    # GET Request: Filter & Search
    status_filter = request.args.get('status', 'all')
    search_q = request.args.get('q', '').strip()

    query = db.query(PasswordResetRequest)
    if status_filter and status_filter != 'all':
        query = query.filter(PasswordResetRequest.status == status_filter)

    if search_q:
        query = query.filter(
            (PasswordResetRequest.cnic.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.phone.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.email.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.account_username.ilike(f"%{search_q}%")) |
            (PasswordResetRequest.user_full_name.ilike(f"%{search_q}%"))
        )

    tickets = query.order_by(PasswordResetRequest.created_at.desc()).all()
    pending_count = db.query(PasswordResetRequest).filter(PasswordResetRequest.status == 'Pending').count()
    processed_count = db.query(PasswordResetRequest).filter(PasswordResetRequest.status == 'Processed').count()
    rejected_count = db.query(PasswordResetRequest).filter(PasswordResetRequest.status == 'Rejected').count()

    return render_template(
        'superadmin/password_resets.html',
        tickets=tickets,
        status_filter=status_filter,
        search_q=search_q,
        pending_count=pending_count,
        processed_count=processed_count,
        rejected_count=rejected_count
    )
