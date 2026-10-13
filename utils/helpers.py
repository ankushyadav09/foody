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
from flask import session, redirect, url_for, flash


# ─────────────────────────────────────────────
# FILE UPLOAD HELPERS
# ─────────────────────────────────────────────

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS)


def save_uploaded_image(file, subfolder='uploads'):
    """
    Save an uploaded image to static/uploads (or subfolder).
    Returns the relative URL path for use in templates.
    """
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        save_dir = os.path.join(Config.UPLOAD_FOLDER)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, unique_name)
        file.save(filepath)
        return f"/static/uploads/{unique_name}"
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
# AUTH DECORATORS (Role-based access control)
# ─────────────────────────────────────────────

def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    """Allow only customers."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'customer':
            flash('Access denied. Customers only.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def restaurant_required(f):
    """Allow only restaurant owners."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'restaurant':
            flash('Access denied. Restaurant owners only.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def delivery_required(f):
    """Allow only delivery partners."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'delivery':
            flash('Access denied. Delivery partners only.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Allow only admins."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
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
