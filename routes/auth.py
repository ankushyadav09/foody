"""
routes/auth.py – Authentication routes for Foody Hunters
Handles: Register, Login, Logout, Password reset
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import execute_query
from utils.helpers import validate_email, validate_phone, validate_password

auth_bp = Blueprint('auth', __name__)


# ─────────────────────────────────────────────
# REGISTER (Multi-Role: Customer, Restaurant Owner, Delivery Partner)
# ─────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Multi-role registration page."""
    if 'user_id' in session:
        return _redirect_by_role(session.get('role'))

    role_param = request.args.get('role', 'customer')

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        phone    = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        role     = request.form.get('role', 'customer').strip().lower()
        address  = request.form.get('address', '').strip()
        city     = request.form.get('city', 'Mehsana').strip()
        pincode  = request.form.get('pincode', '384002').strip()

        # Extra fields for restaurant
        restaurant_name = request.form.get('restaurant_name', '').strip()
        cuisine         = request.form.get('cuisine', '').strip()
        restaurant_area = request.form.get('restaurant_area', 'Mehsana City').strip()

        # Extra fields for delivery partner
        vehicle_type   = request.form.get('vehicle_type', 'Motorcycle').strip()
        vehicle_number = request.form.get('vehicle_number', '').strip()
        license_number = request.form.get('license_number', '').strip()

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
        if role not in ('customer', 'restaurant', 'delivery'):
            role = 'customer'

        if role == 'restaurant':
            if not restaurant_name:
                errors.append('Restaurant name is required.')
            if not cuisine:
                errors.append('Cuisine types are required.')
        elif role == 'delivery':
            if not vehicle_number:
                errors.append('Vehicle registration number is required.')
            if not license_number:
                errors.append('Driving license number is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html', form=request.form, selected_role=role)

        # ── Check duplicate email or phone ──────────────────────────────────
        existing = execute_query(
            "SELECT id, email, phone FROM users WHERE email=%s OR phone=%s", (email, phone), fetchone=True
        )
        if existing:
            if existing['email'] == email:
                flash('This email is already registered. Please login.', 'warning')
            else:
                flash('This mobile number is already registered. Please login.', 'warning')
            return render_template('register.html', form=request.form, selected_role=role)

        # ── Hash password and store user ─────────────────────────────────────
        pw_hash = generate_password_hash(password)
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Gujarat', %s, 'active')""",
            (name, email, phone, pw_hash, role, address, city, pincode),
            commit=True
        )

        # ── Role-specific secondary record creation ──────────────────────────
        if role == 'restaurant':
            execute_query(
                """INSERT INTO restaurants (owner_id, name, description, cuisine, address, area, city, state, pincode, phone, email, rating, verification_status, status, is_open)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'Gujarat', %s, %s, %s, 4.50, 'pending', 'active', 1)""",
                (user_id, restaurant_name, f"Authentic {cuisine} in Mehsana", cuisine, address or f"Shop on {restaurant_area}, Mehsana", restaurant_area, city, pincode, phone, email),
                commit=True
            )
            flash('Restaurant registration submitted! Pending administrator approval.', 'info')
        elif role == 'delivery':
            execute_query(
                """INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings)
                   VALUES (%s, %s, %s, %s, 1, 1, 0, 0.00)""",
                (user_id, vehicle_type, vehicle_number, license_number),
                commit=True
            )
            flash('Delivery partner registration successful! You can now log in.', 'success')
        else:
            if address:
                execute_query(
                    """INSERT INTO addresses (user_id, label, address, area, city, state, pincode, is_default)
                       VALUES (%s, 'Home', %s, %s, %s, 'Gujarat', %s, 1)""",
                    (user_id, address, 'Mehsana City', city, pincode),
                    commit=True
                )
            flash('Registration successful! Please login to start ordering.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('register.html', form={}, selected_role=role_param)


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login page for all user roles."""
    if 'user_id' in session:
        return _redirect_by_role(session.get('role'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember_me')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')

        # ── Fetch user ────────────────────────────────────────────────────────
        user = execute_query(
            "SELECT * FROM users WHERE email=%s", (email,), fetchone=True
        )
        if not user and '@' in email:
            # Check domain alias (@foodiehunter.com <-> @foodyhunters.com)
            alt_domain = 'foodyhunters.com' if '@foodiehunter.com' in email else ('foodiehunter.com' if '@foodyhunters.com' in email else None)
            if alt_domain:
                alt_email = email.split('@')[0] + '@' + alt_domain
                user = execute_query("SELECT * FROM users WHERE email=%s", (alt_email,), fetchone=True)

        if not user:
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        if user['status'] == 'inactive':
            flash('Your account has been deactivated. Contact support.', 'warning')
            return render_template('login.html')

        if not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        # ── Set session ───────────────────────────────────────────────────────
        session.permanent = bool(remember)
        session['user_id']   = user['id']
        session['user_name'] = user['name']
        session['user_email']= user['email']
        session['role']      = user['role']

        flash(f"Welcome back, {user['name']}!", 'success')
        return _redirect_by_role(user['role'])

    return render_template('login.html')


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to home."""
    session.clear()
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
    else:
        return redirect(url_for('main.index'))
