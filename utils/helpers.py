"""
utils/helpers.py – Utility/helper functions for Foody Hunters
"""

import os
import uuid
import re
from datetime import datetime, date
from werkzeug.utils import secure_filename
from config import Config
from functools import wraps
from flask import session, redirect, url_for, flash, request


# ─────────────────────────────────────────────
# FILE UPLOAD HELPERS
# ─────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    """Check if uploaded file has an allowed image extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(file, subfolder='uploads'):
    """
    Save an uploaded image to static/uploads (or subfolder).
    Validates file extension, sanitizes filename, verifies genuine image content with Pillow,
    and returns the relative URL path for use in templates and DB.
    Returns None if validation or saving fails.
    """
    if not file or not file.filename:
        return None

    # 1. Sanitize filename and verify allowed image extension
    clean_name = secure_filename(file.filename)
    if not allowed_file(clean_name):
        return None

    ext = clean_name.rsplit('.', 1)[1].lower()

    # 2. Validate file size and content integrity using Pillow
    try:
        from PIL import Image
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(0)

        # Reject empty files or files exceeding maximum content length (16MB)
        max_size = getattr(Config, 'MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        if size == 0 or size > max_size:
            return None

        # Verify image content and format
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
    except Exception:
        return None

    # 3. Generate unique random filename to prevent collision & traversal
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    # 4. Resolve destination directory safely
    if subfolder and subfolder != 'uploads':
        safe_subfolder = secure_filename(subfolder)
        save_dir = os.path.join(Config.UPLOAD_FOLDER, safe_subfolder)
        url_path = f"/static/uploads/{safe_subfolder}/{unique_name}"
    else:
        save_dir = Config.UPLOAD_FOLDER
        url_path = f"/static/uploads/{unique_name}"

    try:
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, unique_name)
        file.save(filepath)
        return url_path
    except Exception as e:
        print(f"[IMAGE SAVE ERROR] {e}", file=sys.stderr)
        return None

def allowed_doc_file(filename):
    """Check if uploaded document has an allowed extension."""
    doc_exts = getattr(Config, 'ALLOWED_DOC_EXTENSIONS', {'png', 'jpg', 'jpeg', 'pdf', 'webp'})
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in doc_exts)


def save_uploaded_document(file, subfolder='documents'):
    """
    Save an uploaded verification document (PDF, PNG, JPG) to static/uploads/documents.
    Returns the relative URL path for use in templates and DB.
    """
    if file and file.filename and allowed_doc_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"doc_{uuid.uuid4().hex}.{ext}"
        save_dir = os.path.join(Config.UPLOAD_FOLDER, subfolder)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, unique_name)
        file.save(filepath)
        return f"/static/uploads/{subfolder}/{unique_name}"
    return None


# ─────────────────────────────────────────────
# VALIDATION HELPERS
# ─────────────────────────────────────────────

def validate_email(email):
    """Simple email format validation."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate Indian mobile number (10 digits, starts with 6-9)."""
    pattern = r'^[6-9]\d{9}$'
    return re.match(pattern, str(phone)) is not None


def validate_password(password):
    """Password must be at least 6 characters."""
    return len(password) >= 6


# ─────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────

def format_currency(amount):
    """Format amount as Indian rupee string."""
    return f"₹{float(amount):,.2f}"


def format_datetime(dt):
    """Format datetime for display."""
    if isinstance(dt, datetime):
        return dt.strftime('%d %b %Y, %I:%M %p')
    return str(dt)


def generate_order_id():
    """Generate a unique readable order ID like FH-2026-ABC123."""
    year_str = datetime.now().strftime('%Y')
    random_part = uuid.uuid4().hex[:6].upper()
    return f"FH-{year_str}-{random_part}"



def generate_transaction_id():
    """Generate a unique transaction ID."""
    return f"TXN{uuid.uuid4().hex[:12].upper()}"


# ─────────────────────────────────────────────
# AUTHORITATIVE ROLE IDENTITIES & DISPLAY LABELS
# ─────────────────────────────────────────────

ROLE_DISPLAY_NAMES = {
    'customer': 'Customer',
    'admin': 'Administrator',
    'restaurant': 'Restaurant Owner',
    'delivery': 'Delivery Partner',
    'staff': 'Restaurant / Hotel Staff',
}

STAFF_ROLE_DISPLAY_NAMES = {
    'kitchen_staff': 'Kitchen Staff',
    'restaurant_manager': 'Restaurant Manager',
    'head_chef': 'Head Chef',
    'sous_chef': 'Sous Chef',
    'waiter': 'Waitstaff',
    'cashier': 'Cashier',
}

def get_role_display_name(role, staff_role=None):
    """
    Centralized, server-side role normalization and authoritative display mapping.
    Ensures consistent, unambiguous identity labels across all portals:
    - customer -> 'Customer'
    - admin -> 'Administrator'
    - restaurant -> 'Restaurant Owner'
    - delivery -> 'Delivery Partner'
    - staff -> 'Restaurant / Hotel Staff — <Position>' (e.g., 'Restaurant / Hotel Staff — Kitchen Staff')
    Returns 'Guest' for missing or unknown roles without privilege escalation.
    """
    if not role:
        return 'Guest'
    role_key = str(role).strip().lower()
    base_label = ROLE_DISPLAY_NAMES.get(role_key)
    if not base_label:
        return 'Guest'
    if role_key == 'staff' and staff_role:
        clean_pos = str(staff_role).strip().lower()
        pos_title = STAFF_ROLE_DISPLAY_NAMES.get(clean_pos, clean_pos.replace('_', ' ').title())
        return f"{base_label} — {pos_title}"
    return base_label


def get_authoritative_account_role(user_id):
    """
    Query the authoritative role from the database for a given user_id.
    Guarantees server-side verification and prevents session or URL role spoofing.
    """
    if not user_id:
        return None
    try:
        from database import execute_query
        user = execute_query("SELECT role FROM users WHERE id=%s", (user_id,), fetchone=True)
        if user and user.get('role'):
            return str(user['role']).strip().lower()
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
# ROLE-SCOPED SESSION CONTEXT HELPERS
# ─────────────────────────────────────────────

def get_customer_auth():
    """Retrieve validated customer authentication context."""
    auth = session.get('customer_auth')
    if auth and isinstance(auth, dict) and auth.get('user_id') and auth.get('role') == 'customer':
        return auth
    # Backward compatibility with legacy direct session assignment
    if session.get('role') == 'customer' and session.get('user_id'):
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name', 'Customer'),
            'user_email': session.get('user_email', ''),
            'role': 'customer'
        }
    return None


def set_customer_auth(user):
    """Establish customer-specific authentication context."""
    session['customer_auth'] = {
        'user_id': user['id'],
        'user_name': user['name'],
        'user_email': user['email'],
        'role': 'customer'
    }
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = 'customer'


def clear_customer_auth():
    """Clear only the customer-specific authentication context."""
    session.pop('customer_auth', None)
    if session.get('role') == 'customer':
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session.pop('role', None)


def get_admin_auth():
    """Retrieve validated admin authentication context."""
    auth = session.get('admin_auth')
    if auth and isinstance(auth, dict) and auth.get('user_id') and auth.get('role') == 'admin':
        return auth
    # Backward compatibility
    if session.get('role') == 'admin' and session.get('user_id'):
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name', 'Administrator'),
            'user_email': session.get('user_email', ''),
            'role': 'admin'
        }
    return None


def set_admin_auth(user):
    """Establish administrator-specific authentication context."""
    session['admin_auth'] = {
        'user_id': user['id'],
        'user_name': user['name'],
        'user_email': user['email'],
        'role': 'admin'
    }
    session['admin_gate_passed'] = True
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = 'admin'


def clear_admin_auth():
    """Clear only administrator-specific authentication context and gate access."""
    session.pop('admin_auth', None)
    session.pop('admin_gate_passed', None)
    if session.get('role') == 'admin':
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session.pop('role', None)


def get_restaurant_auth():
    """Retrieve validated restaurant owner authentication context."""
    auth = session.get('restaurant_auth')
    if auth and isinstance(auth, dict) and auth.get('user_id') and auth.get('role') == 'restaurant':
        return auth
    if session.get('role') == 'restaurant' and session.get('user_id'):
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name', ''),
            'user_email': session.get('user_email', ''),
            'role': 'restaurant',
            'restaurant_id': session.get('restaurant_id')
        }
    return None


def set_restaurant_auth(user, restaurant_id=None):
    """Establish restaurant-specific authentication context."""
    session['restaurant_auth'] = {
        'user_id': user['id'],
        'user_name': user['name'],
        'user_email': user['email'],
        'role': 'restaurant',
        'restaurant_id': restaurant_id
    }
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = 'restaurant'
    if restaurant_id:
        session['restaurant_id'] = restaurant_id


def clear_restaurant_auth():
    """Clear only restaurant-specific authentication context."""
    session.pop('restaurant_auth', None)
    if session.get('role') == 'restaurant':
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session.pop('role', None)
        session.pop('restaurant_id', None)


def get_delivery_auth():
    """Retrieve validated delivery partner authentication context."""
    auth = session.get('delivery_auth')
    if auth and isinstance(auth, dict) and auth.get('user_id') and auth.get('role') == 'delivery':
        return auth
    if session.get('role') == 'delivery' and session.get('user_id'):
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name', ''),
            'user_email': session.get('user_email', ''),
            'role': 'delivery'
        }
    return None


def set_delivery_auth(user):
    """Establish delivery-specific authentication context."""
    session['delivery_auth'] = {
        'user_id': user['id'],
        'user_name': user['name'],
        'user_email': user['email'],
        'role': 'delivery'
    }
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = 'delivery'


def clear_delivery_auth():
    """Clear only delivery-specific authentication context."""
    session.pop('delivery_auth', None)
    if session.get('role') == 'delivery':
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session.pop('role', None)


def get_staff_auth():
    """Retrieve validated kitchen staff authentication context."""
    auth = session.get('staff_auth')
    if auth and isinstance(auth, dict) and auth.get('user_id') and auth.get('role') == 'staff':
        return auth
    if session.get('role') == 'staff' and session.get('user_id'):
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name', ''),
            'user_email': session.get('user_email', ''),
            'role': 'staff',
            'restaurant_id': session.get('restaurant_id'),
            'staff_role': session.get('staff_role'),
            'restaurant_name': session.get('restaurant_name'),
            'shift': session.get('shift')
        }
    return None


def set_staff_auth(user, restaurant_id=None, staff_role=None, restaurant_name=None, shift=None):
    """Establish staff-specific authentication context."""
    session['staff_auth'] = {
        'user_id': user['id'],
        'user_name': user['name'],
        'user_email': user['email'],
        'role': 'staff',
        'restaurant_id': restaurant_id,
        'staff_role': staff_role,
        'restaurant_name': restaurant_name,
        'shift': shift
    }
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = 'staff'
    if restaurant_id:
        session['restaurant_id'] = restaurant_id
    if staff_role:
        session['staff_role'] = staff_role
    if restaurant_name:
        session['restaurant_name'] = restaurant_name
    if shift:
        session['shift'] = shift


def clear_staff_auth():
    """Clear only staff-specific authentication context."""
    session.pop('staff_auth', None)
    if session.get('role') == 'staff':
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session.pop('role', None)
        session.pop('restaurant_id', None)
        session.pop('staff_role', None)
        session.pop('restaurant_name', None)
        session.pop('shift', None)


# ─────────────────────────────────────────────
# AUTH DECORATORS (Role-based access control)
# ─────────────────────────────────────────────

def login_required(f):
    """Redirect to customer login if visitor has no customer session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = get_customer_auth()
        if not auth:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        session['user_id'] = auth['user_id']
        session['role'] = auth.get('role', 'customer')
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    """Allow only authenticated customers."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = get_customer_auth()
        if not auth:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        if auth.get('role') != 'customer':
            flash('Access denied. Customers only.', 'danger')
            return redirect(url_for('main.index'))
        session['user_id'] = auth['user_id']
        session['user_name'] = auth.get('user_name', '')
        session['user_email'] = auth.get('user_email', '')
        session['role'] = 'customer'
        return f(*args, **kwargs)
    return decorated


def restaurant_required(f):
    """Allow only approved restaurant owners."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Reject active non-restaurant role sessions immediately
        if session.get('role') and session.get('role') != 'restaurant':
            flash('Access denied. Restaurant owners only.', 'danger')
            return redirect(url_for('main.index'))

        auth = get_restaurant_auth()
        if not auth:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('restaurant.login'))
        if auth.get('role') != 'restaurant':
            flash('Access denied. Restaurant owners only.', 'danger')
            return redirect(url_for('main.index'))

        session['user_id'] = auth['user_id']
        session['role'] = 'restaurant'
        session['user_name'] = auth.get('user_name', '')
        session['user_email'] = auth.get('user_email', '')

        from database import execute_query
        rest = execute_query(
            "SELECT id, verification_status, status FROM restaurants WHERE owner_id=%s",
            (auth['user_id'],), fetchone=True
        )
        if rest:
            session['restaurant_id'] = rest['id']
            auth['restaurant_id'] = rest['id']
            v_status = rest.get('verification_status')
            if v_status == 'pending':
                flash('Your restaurant application is currently pending admin approval.', 'warning')
                return redirect(url_for('restaurant.application_status'))
            elif v_status in ('rejected', 'suspended'):
                flash('Your restaurant partner account has been suspended or rejected.', 'danger')
                return redirect(url_for('restaurant.application_status'))
        return f(*args, **kwargs)
    return decorated


def delivery_required(f):
    """Allow only delivery partners."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Reject active non-delivery role sessions immediately
        if session.get('role') and session.get('role') != 'delivery':
            flash('Access denied. Delivery partners only.', 'danger')
            return redirect(url_for('main.index'))

        auth = get_delivery_auth()
        if not auth:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('delivery.login'))
        if auth.get('role') != 'delivery':
            flash('Access denied. Delivery partners only.', 'danger')
            return redirect(url_for('main.index'))

        session['user_id'] = auth['user_id']
        session['role'] = 'delivery'
        session['user_name'] = auth.get('user_name', '')
        session['user_email'] = auth.get('user_email', '')
        return f(*args, **kwargs)
    return decorated


def admin_gate_required(f):
    """Enforce that visitor has successfully passed the Admin Security Gate passkey."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_gate_passed'):
            flash('Admin security passkey required to access administrator portal.', 'warning')
            return redirect(url_for('admin.gate', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Allow only authenticated admins who have cleared entry security."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. Reject active non-admin role sessions immediately
        if session.get('role') and session.get('role') != 'admin':
            flash('Access denied: System administrator privileges required.', 'danger')
            return redirect(url_for('main.index'))

        auth = get_admin_auth()

        # 2. Gate & Authentication Check
        if not session.get('admin_gate_passed') or not auth:
            if getattr(Config, 'ADMIN_DIRECT_LOGIN_ENABLED', True):
                flash('Admin security passkey required to access administrator portal.', 'warning')
                return redirect(url_for('admin.gate', next=request.path))
            if not session.get('admin_gate_passed'):
                flash('Admin security gate passkey required to access administrator portal.', 'warning')
                return redirect(url_for('admin.gate', next=request.path))
            flash('Please sign in with administrator credentials.', 'warning')
            return redirect(url_for('admin.login', next=request.path))

        # 3. Role Authorization Check
        if auth.get('role') != 'admin':
            flash('Access denied: System administrator privileges required.', 'danger')
            return redirect(url_for('main.index'))

        session['user_id'] = auth['user_id']
        session['user_name'] = auth.get('user_name', 'Administrator')
        session['user_email'] = auth.get('user_email', '')
        session['role'] = 'admin'
        return f(*args, **kwargs)
    return decorated


def staff_required(f):
    """Allow only approved restaurant staff members."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Reject active non-staff role sessions immediately
        if session.get('role') and session.get('role') != 'staff':
            flash('Access denied. Restaurant staff only.', 'danger')
            return redirect(url_for('main.index'))

        auth = get_staff_auth()
        if not auth:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('staff.login'))
        if auth.get('role') != 'staff':
            flash('Access denied. Restaurant staff only.', 'danger')
            return redirect(url_for('main.index'))
        
        session['user_id'] = auth['user_id']
        session['role'] = 'staff'
        session['user_name'] = auth.get('user_name', '')
        session['user_email'] = auth.get('user_email', '')

        # Verify approval status and assigned restaurant
        from database import execute_query
        staff_rec = execute_query(
            "SELECT s.*, r.name as restaurant_name, r.is_open FROM restaurant_staff s "
            "JOIN restaurants r ON s.restaurant_id=r.id WHERE s.user_id=%s",
            (auth['user_id'],), fetchone=True
        )
        if not staff_rec:
            flash('No restaurant assignment found for this staff account.', 'danger')
            return redirect(url_for('staff.login'))
        if staff_rec['status'] != 'approved':
            flash(f"Staff account status: {staff_rec['status'].title()}. Approval required to access kitchen desk.", 'warning')
            return redirect(url_for('staff.login'))
            
        session['restaurant_id'] = staff_rec['restaurant_id']
        session['restaurant_name'] = staff_rec['restaurant_name']
        session['staff_role'] = staff_rec['staff_role']
        return f(*args, **kwargs)
    return decorated


def staff_or_restaurant_required(f):
    """Allow either restaurant owner, approved restaurant staff, or admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        rest_auth = get_restaurant_auth()
        staff_auth = get_staff_auth()
        admin_auth = get_admin_auth()

        if rest_auth:
            session['user_id'] = rest_auth['user_id']
            session['role'] = 'restaurant'
            return f(*args, **kwargs)
        elif staff_auth:
            session['user_id'] = staff_auth['user_id']
            session['role'] = 'staff'
            return f(*args, **kwargs)
        elif admin_auth and session.get('admin_gate_passed'):
            session['user_id'] = admin_auth['user_id']
            session['role'] = 'admin'
            return f(*args, **kwargs)

        flash('Please login to continue.', 'warning')
        return redirect(url_for('restaurant.login'))
    return decorated



# ─────────────────────────────────────────────
# ORDER / CART HELPERS
# ─────────────────────────────────────────────

def calculate_order_totals(subtotal, delivery_fee=None, discount=0):
    """
    Calculate order totals with tax.
    Ensures discount <= subtotal and grand_total >= 0.
    Returns dict with subtotal, delivery_fee, discount, tax, grand_total.
    """
    if delivery_fee is None:
        delivery_fee = Config.DEFAULT_DELIVERY_FEE
    subtotal = max(0.0, float(subtotal or 0))
    delivery_fee = max(0.0, float(delivery_fee or 0))
    discount = max(0.0, min(float(discount or 0), subtotal))
    taxable = max(0.0, subtotal - discount)
    tax = round(taxable * Config.TAX_RATE, 2)
    grand_total = round(max(0.0, taxable + delivery_fee + tax), 2)
    return {
        'subtotal': round(subtotal, 2),
        'delivery_fee': round(delivery_fee, 2),
        'discount': round(discount, 2),
        'tax': tax,
        'grand_total': grand_total
    }


def validate_and_calculate_coupon(coupon_id=None, coupon_code=None, subtotal=0.0):
    """
    Validate a coupon by ID or code against current business rules:
    - Exists in `coupons` table
    - `is_active == 1`
    - `expiry_date` is None or >= current date
    - `usage_limit` is None or 0 or `times_used < usage_limit`
    - `subtotal >= min_order_amount`
    Recalculates exact discount and verifies total cannot become negative.

    Returns:
        tuple: (is_valid: bool, message: str, coupon_dict: dict|None, discount: float)
    """
    from database import execute_query

    coupon = None
    subtotal = max(0.0, float(subtotal or 0))

    # Clean inputs
    if coupon_id not in (None, '', 0, '0', 'null', 'None'):
        try:
            cid = int(coupon_id)
            coupon = execute_query("SELECT * FROM coupons WHERE id=%s", (cid,), fetchone=True)
        except (ValueError, TypeError):
            coupon = None

    if not coupon and coupon_code:
        code_str = str(coupon_code).strip().upper()
        if code_str:
            coupon = execute_query("SELECT * FROM coupons WHERE code=%s", (code_str,), fetchone=True)

    if not coupon:
        return False, "Invalid or non-existent coupon code.", None, 0.0

    if not coupon.get('is_active'):
        return False, f"Coupon '{coupon['code']}' is currently inactive.", None, 0.0

    # Expiration check
    expiry = coupon.get('expiry_date')
    if expiry:
        exp_date = None
        if isinstance(expiry, (datetime, date)):
            exp_date = expiry.date() if isinstance(expiry, datetime) else expiry
        else:
            try:
                exp_date = datetime.strptime(str(expiry)[:10], '%Y-%m-%d').date()
            except Exception:
                exp_date = None
        if exp_date and exp_date < date.today():
            return False, f"Coupon '{coupon['code']}' has expired.", None, 0.0

    # Usage limit check
    usage_limit = coupon.get('usage_limit')
    times_used = coupon.get('times_used') or 0
    if usage_limit is not None and int(usage_limit) > 0:
        if int(times_used) >= int(usage_limit):
            return False, f"Coupon '{coupon['code']}' has reached its maximum redemption limit.", None, 0.0

    # Minimum order check
    min_order = float(coupon.get('min_order_amount') or 0.0)
    if subtotal < min_order:
        return False, f"Minimum order ₹{min_order:.2f} required for this coupon.", None, 0.0

    # Discount calculation
    discount_type = coupon.get('discount_type', 'percentage')
    discount_val = float(coupon.get('discount_value') or 0.0)
    max_discount = coupon.get('max_discount')
    max_disc_float = float(max_discount) if max_discount is not None else None

    if discount_type == 'percentage':
        discount = round(subtotal * (discount_val / 100.0), 2)
        if max_disc_float is not None and discount > max_disc_float:
            discount = round(max_disc_float, 2)
    else:  # fixed
        discount = round(discount_val, 2)

    # Ensure discount never exceeds subtotal and is not negative
    discount = max(0.0, min(discount, subtotal))

    return True, f"Coupon applied! You save ₹{discount:.2f}", coupon, discount



def log_activity(admin_id=None, action="", details=""):
    """
    Log an operational audit event into admin_logs.
    Safe against failures; never logs credentials or secrets.
    """
    try:
        from database import execute_query
        execute_query(
            "INSERT INTO admin_logs (admin_id, action, details) VALUES (%s, %s, %s)",
            (admin_id, str(action)[:100], str(details)[:500]),
            commit=True
        )
    except Exception:
        pass
