import os
from datetime import timedelta

# Try loading environment variables from .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

class Config:
    # Production secret key from environment or fallback
    SECRET_KEY = os.environ.get('SECRET_KEY', 'punjab-sed-promotion-mgmt-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(INSTANCE_DIR, "teacher_promotion.db")}'
    )

    # Database configuration with automated PostgreSQL prefix migration
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url and _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url or f'sqlite:///{os.path.join(INSTANCE_DIR, "teacher_promotion.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Directories for uploads and backups
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    BACKUP_FOLDER = os.path.join(BASE_DIR, 'backups')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB max upload
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(BACKUP_FOLDER, exist_ok=True)

    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 32 * 1024 * 1024))  # 32 MB default max upload
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg'}

    # Session & Security Settings (10 minutes inactivity timeout)
    SESSION_INACTIVITY_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 10))
    from datetime import timedelta
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=SESSION_INACTIVITY_TIMEOUT_MINUTES)

    # Application Branding
    APP_NAME = "Teacher Promotion Portal"
    APP_SUBTITLE = "School Education Department"
    DEPARTMENT = "School Education Department"
    VERSION = "2.5.0"

