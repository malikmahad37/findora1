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
    """Return a Supabase client using service key (preferred) or anon key."""
    try:
        from supabase import create_client
        url = os.environ.get('SUPABASE_URL', '')
        # Prefer service role key (bypasses RLS), fallback to anon key
        key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY', '')
        if url and key:
            return create_client(url, key)
    except Exception as e:
        import sys
        print(f"[SUPABASE] Client init failed: {e}", file=sys.stderr)
    return None


def _upload_to_supabase(file_bytes, storage_path, content_type):
    """Upload directly to Supabase Storage via REST API, fallback to client library."""
    url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY', '')
    if not url or not key:
        return None

    # Method 1: Standard library REST request (fast, no package version quirks)
    try:
        import urllib.request
        upload_url = f"{url}/storage/v1/object/{SUPABASE_BUCKET}/{storage_path}"
        req = urllib.request.Request(
            upload_url,
            data=file_bytes,
            headers={
                'Authorization': f'Bearer {key}',
                'apikey': key,
                'Content-Type': content_type,
                'x-upsert': 'true'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                public_url = f"{url}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_path}"
                return public_url
    except Exception as e:
        import sys
        print(f"[IMG_UPLOAD] REST upload error: {e}", file=sys.stderr)

    # Method 2: Supabase Python SDK client fallback
    try:
        supabase = _get_supabase_client()
        if supabase:
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
    except Exception as e:
        import sys
        print(f"[IMG_UPLOAD] Supabase SDK error: {e}", file=sys.stderr)

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

    try:
        file_bytes = file.read()
        content_type = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'
        public_url = _upload_to_supabase(file_bytes, storage_path, content_type)
        if public_url:
            return public_url
    except Exception as e:
        import sys
        print(f"[IMG_UPLOAD] Upload failed: {e}", file=sys.stderr)

    # Fallback: save to local/tmp filesystem
    try:
        file.seek(0)
    except Exception:
        pass

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
