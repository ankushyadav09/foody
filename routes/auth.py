"""
routes/auth.py – Authentication routes for Foody Hunters
Handles: Register, Login, Logout, Password reset
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import execute_query
from utils.helpers import (validate_email, validate_phone, validate_password,
                           get_customer_auth, set_customer_auth, clear_customer_auth,
                           set_restaurant_auth, set_delivery_auth, set_staff_auth,
                           clear_restaurant_auth, clear_delivery_auth, clear_staff_auth)

auth_bp = Blueprint('auth', __name__)


# ─────────────────────────────────────────────
# CUSTOMER REGISTER
# ─────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Customer registration only. Partner onboarding is separated."""
    # Only redirect if ALREADY authenticated as a customer
    if get_customer_auth():
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        phone    = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        address  = request.form.get('address', '').strip()
        city     = request.form.get('city', 'Mehsana').strip() or 'Mehsana'
        pincode  = request.form.get('pincode', '384002').strip() or '384002'

        # SECURITY: Strictly customer role only. Never trust any role passed from browser!
        # Reject/ignore any injected admin or partner role
        role = 'customer'

        # ── Validation ────────────────────────────────────────────────────────
        errors = []
        if not name:
            errors.append('Full name is required.')
        if not validate_email(email):
            errors.append('Enter a valid email address.')
        if not validate_phone(phone):
            errors.append('Enter a valid 10-digit Indian mobile number.')
        if not validate_password(password):
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html', form=request.form)

        # ── Check duplicate email or phone ──────────────────────────────────
        existing = execute_query(
            "SELECT id, email, phone FROM users WHERE email=%s OR phone=%s", (email, phone), fetchone=True
        )
        if existing:
            if existing['email'] == email:
                flash('This email is already registered. Please login.', 'warning')
            else:
                flash('This mobile number is already registered. Please login.', 'warning')
            return render_template('register.html', form=request.form)

        # ── Hash password and store customer ─────────────────────────────────
        pw_hash = generate_password_hash(password)
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Gujarat', %s, 'active')""",
            (name, email, phone, pw_hash, role, address, city, pincode),
            commit=True
        )

        if address:
            execute_query(
                """INSERT INTO addresses (user_id, label, address, area, city, state, pincode, is_default)
                   VALUES (%s, 'Home', %s, %s, %s, 'Gujarat', %s, 1)""",
                (user_id, address, 'Mehsana City', city, pincode),
                commit=True
            )

        flash('Customer registration successful! Please login to start ordering.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form={})


# ─────────────────────────────────────────────
# CUSTOMER LOGIN
# ─────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Customer login page."""
    # Only redirect if ALREADY authenticated as a customer
    if get_customer_auth():
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password   = request.form.get('password', '')
        remember   = request.form.get('remember_me')

        if not identifier or not password:
            flash('Email/Mobile and password are required.', 'danger')
            return render_template('login.html')

        # Check if login identifier is phone or email
        if identifier.isdigit() and len(identifier) == 10:
            user = execute_query("SELECT * FROM users WHERE phone=%s", (identifier,), fetchone=True)
        else:
            user = execute_query("SELECT * FROM users WHERE email=%s", (identifier,), fetchone=True)
            if not user and '@' in identifier:
                # Check domain alias (@foodiehunter.com <-> @foodyhunters.com)
                alt_domain = 'foodyhunters.com' if '@foodiehunter.com' in identifier else ('foodiehunter.com' if '@foodyhunters.com' in identifier else None)
                if alt_domain:
                    alt_email = identifier.split('@')[0] + '@' + alt_domain
                    user = execute_query("SELECT * FROM users WHERE email=%s", (alt_email,), fetchone=True)

        if not user:
            flash('Invalid email/mobile or password.', 'danger')
            return render_template('login.html')

        if user['status'] == 'inactive':
            flash('Your account has been deactivated. Contact support.', 'warning')
            return render_template('login.html')

        if not check_password_hash(user['password_hash'], password):
            flash('Invalid email/mobile or password.', 'danger')
            return render_template('login.html')

        # ── Strict Role Segregation on Customer Login ─────────────────────────
        if user['role'] == 'admin':
            # Strictly reject administrator login on customer portal
            flash('Administrator accounts cannot be authenticated via Customer Login. Please use the Admin Portal at /admin.', 'danger')
            return render_template('login.html')

        session.permanent = bool(remember)

        if user['role'] == 'customer':
            set_customer_auth(user)
            flash(f"Welcome back, {user['name']}!", 'success')
            next_url = request.args.get('next') or request.form.get('next')
            # Security: Prevent open redirects and NEVER redirect customer to /admin
            if next_url and next_url.startswith('/') and not next_url.startswith('//') and not next_url.startswith('/admin'):
                return redirect(next_url)
            return redirect(url_for('main.index'))

        elif user['role'] == 'restaurant':
            rest = execute_query("SELECT id FROM restaurants WHERE owner_id=%s", (user['id'],), fetchone=True)
            set_restaurant_auth(user, restaurant_id=rest['id'] if rest else None)
            flash(f"Welcome back, {user['name']}! Redirecting to Kitchen Operations.", 'success')
            return redirect(url_for('restaurant.dashboard'))

        elif user['role'] == 'delivery':
            set_delivery_auth(user)
            flash(f"Welcome back, {user['name']}! Redirecting to Delivery Portal.", 'success')
            return redirect(url_for('delivery.dashboard'))

        elif user['role'] == 'staff':
            staff_rec = execute_query("SELECT restaurant_id, staff_role FROM restaurant_staff WHERE user_id=%s", (user['id'],), fetchone=True)
            set_staff_auth(user, restaurant_id=staff_rec['restaurant_id'] if staff_rec else None,
                           staff_role=staff_rec['staff_role'] if staff_rec else None)
            flash(f"Welcome back, {user['name']}! Redirecting to Staff Operations.", 'success')
            return redirect(url_for('staff.dashboard'))

        else:
            set_customer_auth(user)
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(url_for('main.index'))

    return render_template('login.html')


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    """Clear customer session (and partner session if active) and redirect to home."""
    clear_customer_auth()
    if not session.get('admin_auth'):
        clear_delivery_auth()
        clear_restaurant_auth()
        clear_staff_auth()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


# ─────────────────────────────────────────────
# FORGOT PASSWORD (Demo – shows reset form only)
# ─────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page – demo implementation."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetchone=True)
        # Always show success to prevent email enumeration
        flash('If that email exists, a reset link has been sent (demo mode).', 'info')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────

def _redirect_by_role(role):
    """Redirect user to their respective dashboard."""
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'restaurant':
        return redirect(url_for('restaurant.dashboard'))
    elif role == 'delivery':
        return redirect(url_for('delivery.dashboard'))
    elif role == 'staff':
        return redirect(url_for('staff.dashboard'))
    else:
        return redirect(url_for('main.index'))
