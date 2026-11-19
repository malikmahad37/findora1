import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Supabase storage bucket name
SUPABASE_BUCKET = 'item-images'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_supabase_client():
    """Return a Supabase client if credentials are available."""
    try:
        from supabase import create_client
        url = os.environ.get('SUPABASE_URL', '')
        key = os.environ.get('SUPABASE_KEY', '')
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


def save_uploaded_file(file, subfolder='items'):
    """
    Save uploaded file to Supabase Storage (preferred) or local /tmp fallback.
    Returns a full public URL (Supabase) or relative path (local).
    """
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None

    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    storage_path = f"{subfolder}/{unique_name}"

    # Try Supabase Storage first
    supabase = _get_supabase_client()
    if supabase:
        try:
            file_bytes = file.read()
            content_type = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            # Return public URL
            public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
            return public_url
        except Exception as e:
            # Reset file pointer if Supabase upload failed
            try:
                file.seek(0)
            except Exception:
                pass

    # Fallback: save to local/tmp filesystem
    try:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, unique_name))
        return storage_path  # relative path for local serving
    except Exception:
        return None


def log_activity(action, details=None, user_id=None):
    """Log an activity to the ActivityLog table."""
    from flask import request
    from app import db
    from app.models import ActivityLog
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=request.remote_addr if request else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def create_notification(user_id, notif_type, message, link=None):
    """Create a notification for a user."""
    from app import db
    from app.models import Notification
    try:
        notif = Notification(
            user_id=user_id,
            notif_type=notif_type,
            message=message,
            link=link
        )
        db.session.add(notif)
        db.session.commit()
    except Exception:
        db.session.rollback()


def format_date(dt):
    if dt is None:
        return ''
    return dt.strftime('%d %b %Y')


def time_ago(dt):
    """Return human-readable relative time string."""
    from datetime import datetime
    if dt is None:
        return ''
    now = datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        m = seconds // 60
        return f'{m} minute{"s" if m > 1 else ""} ago'
    elif seconds < 86400:
        h = seconds // 3600
        return f'{h} hour{"s" if h > 1 else ""} ago'
    elif seconds < 604800:
        d = seconds // 86400
        return f'{d} day{"s" if d > 1 else ""} ago'
    else:
        return format_date(dt)
