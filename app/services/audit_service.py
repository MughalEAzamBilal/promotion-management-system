from app.models.audit import AuditLog

def log_audit(db_session, user, action, entity_type=None, entity_id=None, details=None, ip_address=None):
    """
    Records an immutable audit trail entry for administrative and user actions.
    """
    try:
        user_id = user.id if (user and hasattr(user, 'id')) else None
        username = user.username if (user and hasattr(user, 'username')) else (user if isinstance(user, str) else 'System')
        role = user.role if (user and hasattr(user, 'role')) else 'SYSTEM'
        
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            role=role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details,
            ip_address=ip_address
        )
        db_session.add(log_entry)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print(f"[Audit Log Error]: {e}")
