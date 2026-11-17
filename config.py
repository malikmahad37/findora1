import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def fix_db_url(url):
    """Force psycopg2 driver so SQLAlchemy doesn't try psycopg (v3)."""
    if url.startswith('postgresql://'):
        return url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+psycopg2://', 1)
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'campusfind-dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Upload settings
    # On Vercel (read-only fs), use /tmp which is writable
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads' if os.environ.get('VERCEL') else os.path.join(BASE_DIR, 'uploads'))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Matching
    MATCH_THRESHOLD = 40  # percent – show matches above this score

    # Pagination
    ITEMS_PER_PAGE = 12


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = fix_db_url(os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'campusfind.db')
    ))


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = fix_db_url(os.environ.get('DATABASE_URL', ''))


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
