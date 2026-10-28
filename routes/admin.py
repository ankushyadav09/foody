"""
routes/admin.py – Admin panel routes for Foody Hunters
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from database import execute_query
from config import Config
from utils.helpers import (admin_required, admin_gate_required,
                           save_uploaded_image, log_activity,
                           get_admin_auth, set_admin_auth, clear_admin_auth)
from werkzeug.security import generate_password_hash, check_password_hash
import json
import time

admin_bp = Blueprint('admin', __name__)


# ─────────────────────────────────────────────
# ADMIN ENTRY GATE (SECURITY PASSKEY SCREEN)
# ─────────────────────────────────────────────

@admin_bp.route('', strict_slashes=False)
@admin_bp.route('/', strict_slashes=False)
def index():
    """
    Entry point for /admin.
    If authenticated as admin, directs straight to dashboard.
    Otherwise renders/redirects to the Admin Control Center passkey screen.
    """
    if session.get('admin_gate_passed') and get_admin_auth():
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.gate'))


@admin_bp.route('/gate', methods=['GET', 'POST'])
def gate():
    """
    Admin Entry Gate: Dedicated security passkey verification screen.
    Directly authenticates authorized administrators with the configured password.
    """
    next_url = request.args.get('next') or request.form.get('next') or url_for('admin.dashboard')

    # If already authenticated as admin with gate passed, jump straight to dashboard
    if session.get('admin_gate_passed') and get_admin_auth():
        return redirect(next_url)

    # Detect Cloudflare Tunnel or public reverse proxy
    host_hdr = request.headers.get('X-Forwarded-Host', request.host).lower()
    is_tunnel = ('trycloudflare.com' in host_hdr or
                 'cloudflare' in host_hdr or
                 bool(request.headers.get('Cf-Ray')))

    failed_attempts = session.get('gate_failed_attempts', 0)
    last_failed_time = session.get('gate_last_failed_time', 0)
    now = time.time()

    # Rate limiting: 5 failed attempts locks for 5 minutes (300 seconds)
    if failed_attempts >= 5 and (now - last_failed_time) < 300:
        remaining = int(300 - (now - last_failed_time))
        flash(f"Security Gate Lockout: Too many failed passkey attempts. Please wait {remaining} seconds.", "danger")
        return render_template('admin/gate.html', locked=True, remaining=remaining, next_url=next_url, is_tunnel=is_tunnel)

    if request.method == 'POST':
        gate_pass = (request.form.get('gate_password') or request.form.get('password') or '').strip()
        expected_pass = getattr(Config, 'ADMIN_GATE_PASSWORD', 'food@1234')

        # Fail securely if not configured
        if not expected_pass:
            flash("Admin security gate is not configured on the server.", "danger")
            return render_template('admin/gate.html', locked=False, next_url=next_url, is_tunnel=is_tunnel)

        if gate_pass == expected_pass:
            session['admin_gate_passed'] = True
            session['gate_failed_attempts'] = 0
            session.pop('gate_last_failed_time', None)

            # Direct Demo Admin Mode: associate session with existing admin account from database
            if getattr(Config, 'ADMIN_DIRECT_LOGIN_ENABLED', True):
                admin_user = execute_query(
                    "SELECT * FROM users WHERE role='admin' AND status='active' ORDER BY id ASC LIMIT 1",
                    fetchone=True
                )
                if not admin_user:
                    admin_user = execute_query(
                        "SELECT * FROM users WHERE role='admin' ORDER BY id ASC LIMIT 1",
                        fetchone=True
                    )

                if admin_user:
                    set_admin_auth(admin_user)
                    log_activity(admin_user['id'], 'ADMIN_LOGIN',
                                 f"Administrator {admin_user['name']} authenticated via Master Control passkey.")
                    flash(f"Admin Control Center Unlocked. Welcome, {admin_user['name']}.", "success")
                    return redirect(next_url)
                else:
                    flash("No active system administrator account found in database.", "danger")
                    return render_template('admin/gate.html', locked=False, next_url=next_url, is_tunnel=is_tunnel)
            else:
                # Conventional 2-step mode (if configured)
                if get_admin_auth():
                    flash("Admin Security Gate verified. Welcome back.", "success")
                    return redirect(next_url)
                else:
                    flash("Admin Security Gate verified. Please sign in with administrator credentials.", "success")
                    return redirect(url_for('admin.login', next=next_url))
        else:
            session['gate_failed_attempts'] = failed_attempts + 1
            session['gate_last_failed_time'] = now
            flash("Invalid security passkey. Entry denied.", "danger")
            return render_template('admin/gate.html', locked=False, next_url=next_url, is_tunnel=is_tunnel)

    return render_template('admin/gate.html', locked=False, next_url=next_url, is_tunnel=is_tunnel)


# ─────────────────────────────────────────────
# ADMIN AUTHENTICATION
# ─────────────────────────────────────────────

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Conventional secure login page for system administrators."""
    if 'user_id' in session and session.get('role') == 'admin' and get_admin_auth():
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember_me')
        next_url = request.args.get('next') or request.form.get('next') or url_for('admin.dashboard')

        if not email or not password:
            flash('Administrator email and passkey are required.', 'danger')
            return render_template('admin/login.html')

        user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        if not user and '@' in email:
            alt_domain = 'foodyhunters.com' if '@foodiehunter.com' in email else ('foodiehunter.com' if '@foodyhunters.com' in email else None)
            if alt_domain:
                alt_email = email.split('@')[0] + '@' + alt_domain
                user = execute_query("SELECT * FROM users WHERE email=%s", (alt_email,), fetchone=True)

        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid administrator credentials.', 'danger')
            return render_template('admin/login.html')

        if user['role'] != 'admin':
            flash('Access denied: System administrator privileges required.', 'danger')
            return render_template('admin/login.html')

        if user['status'] == 'inactive':
            flash('Administrator account is deactivated.', 'danger')
            return render_template('admin/login.html')

        session.permanent = bool(remember)
        set_admin_auth(user)

        log_activity(user['id'], 'ADMIN_LOGIN', f"Administrator {user['name']} authenticated via Master Control desk.")
        flash(f"Executive Console Unlocked. Welcome, {user['name']}.", 'success')
        return redirect(next_url)

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Securely log out administrator and lock the security gate."""
    admin_auth = get_admin_auth() or {}
    admin_name = admin_auth.get('user_name', 'Administrator')
    try:
        log_activity(admin_auth.get('user_id'), 'ADMIN_LOGOUT', f"{admin_name} locked the console and logged out.")
    except Exception:
        pass
    clear_admin_auth()
    flash("Administrator session terminated and Security Gate locked.", "info")
    return redirect(url_for('admin.index'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    period = request.args.get('period', 'week')  # 'today', 'week', 'month', 'all'
    if period == 'today':
        rev_filter_sql = "DATE(created_at) = CURDATE()"
        interval_days = 1
    elif period == 'month':
        rev_filter_sql = "created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
        interval_days = 30
    elif period == 'all':
        rev_filter_sql = "1=1"
        interval_days = 365
    else:
        period = 'week'
        rev_filter_sql = "created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        interval_days = 7

    stats = {
        'total_users':           execute_query("SELECT COUNT(*) AS c FROM users WHERE role='customer'", fetchone=True)['c'],
        'active_customers':      execute_query("SELECT COUNT(*) AS c FROM users WHERE role='customer' AND status='active'", fetchone=True)['c'],
        'total_restaurants':     execute_query("SELECT COUNT(*) AS c FROM restaurants", fetchone=True)['c'],
        'pending_restaurants':   execute_query("SELECT COUNT(*) AS c FROM restaurants WHERE verification_status='pending'", fetchone=True)['c'],
        'approved_restaurants':  execute_query("SELECT COUNT(*) AS c FROM restaurants WHERE verification_status='approved'", fetchone=True)['c'],
        'total_partners':        execute_query("SELECT COUNT(*) AS c FROM users WHERE role='delivery'", fetchone=True)['c'],
        'active_partners':       execute_query("SELECT COUNT(*) AS c FROM delivery_partners WHERE is_online=1", fetchone=True)['c'],
        'total_orders':          execute_query("SELECT COUNT(*) AS c FROM orders", fetchone=True)['c'],
        'pending_orders':        execute_query("SELECT COUNT(*) AS c FROM orders WHERE order_status IN ('placed','confirmed')", fetchone=True)['c'],
        'preparing_orders':      execute_query("SELECT COUNT(*) AS c FROM orders WHERE order_status='preparing'", fetchone=True)['c'],
        'out_for_delivery':      execute_query("SELECT COUNT(*) AS c FROM orders WHERE order_status='out_for_delivery'", fetchone=True)['c'],
        'delivered_orders':      execute_query("SELECT COUNT(*) AS c FROM orders WHERE order_status='delivered'", fetchone=True)['c'],
        'cancelled_orders':      execute_query("SELECT COUNT(*) AS c FROM orders WHERE order_status='cancelled'", fetchone=True)['c'],
        'today_revenue':         execute_query(
            "SELECT COALESCE(SUM(total_amount),0) AS r FROM orders WHERE DATE(created_at)=CURDATE() AND order_status!='cancelled'",
            fetchone=True)['r'],
        'period_revenue':        execute_query(
            f"SELECT COALESCE(SUM(total_amount),0) AS r FROM orders WHERE {rev_filter_sql} AND order_status!='cancelled'",
            fetchone=True)['r'],
        'total_staff':           execute_query("SELECT COUNT(*) AS c FROM restaurant_staff", fetchone=True)['c'],
        'pending_staff':         execute_query("SELECT COUNT(*) AS c FROM restaurant_staff WHERE status='pending'", fetchone=True)['c'],
        'approved_staff':        execute_query("SELECT COUNT(*) AS c FROM restaurant_staff WHERE status='approved'", fetchone=True)['c'],
        'total_categories':      execute_query("SELECT COUNT(*) AS c FROM food_categories", fetchone=True)['c'],
        'total_food_items':      execute_query("SELECT COUNT(*) AS c FROM food_items", fetchone=True)['c'],
        'total_coupons':         execute_query("SELECT COUNT(*) AS c FROM coupons", fetchone=True)['c'],
        'open_complaints':       execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status='open' OR status='pending'", fetchone=True)['c'],
    }

    recent_orders = execute_query(
        """SELECT o.*, u.name AS customer_name, r.name AS restaurant_name
           FROM orders o JOIN users u ON o.user_id=u.id
           JOIN restaurants r ON o.restaurant_id=r.id
           ORDER BY o.created_at DESC LIMIT 8""",
        fetchall=True
    )

    # Chart data: revenue grouped by day for the requested interval
    daily_revenue = execute_query(
        f"""SELECT DATE(created_at) AS day, SUM(total_amount) AS revenue
           FROM orders WHERE order_status!='cancelled'
           AND created_at >= DATE_SUB(NOW(), INTERVAL {interval_days} DAY)
           GROUP BY DATE(created_at) ORDER BY day ASC""",
        fetchall=True
    )
    chart_labels = [str(d['day']) for d in daily_revenue]
    chart_data   = [float(d['revenue']) for d in daily_revenue]

    recent_logs = execute_query(
        """SELECT l.*, u.name AS admin_name
           FROM admin_logs l LEFT JOIN users u ON l.admin_id=u.id
           ORDER BY l.created_at DESC LIMIT 6""",
        fetchall=True
    )

    return render_template('admin/dashboard.html',
                           stats=stats, recent_orders=recent_orders,
                           chart_labels=json.dumps(chart_labels),
                           chart_data=json.dumps(chart_data),
                           recent_logs=recent_logs,
                           period=period)


# ─────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    role = request.args.get('role', 'customer')
    q    = request.args.get('q', '').strip()
    sql  = "SELECT * FROM users WHERE role=%s"
    params = [role]
    if q:
        sql += " AND (name LIKE %s OR email LIKE %s OR phone LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY created_at DESC"
    all_users = execute_query(sql, tuple(params), fetchall=True)
    return render_template('admin/users.html', users=all_users, role=role, q=q)


@admin_bp.route('/users/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user(user_id):
    user = execute_query("SELECT status FROM users WHERE id=%s", (user_id,), fetchone=True)
    if user:
        new_status = 'inactive' if user['status'] == 'active' else 'active'
        execute_query("UPDATE users SET status=%s WHERE id=%s",
                      (new_status, user_id), commit=True)
        log_activity(session.get('user_id'), 'USER_STATUS_CHANGE', f"Changed status of user #{user_id} to {new_status}")
        flash(f"User {'activated' if new_status=='active' else 'deactivated'}.", 'success')
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    execute_query("DELETE FROM users WHERE id=%s AND role!='admin'", (user_id,), commit=True)
    log_activity(session.get('user_id'), 'USER_DELETED', f"Deleted non-admin user account #{user_id}")
    flash('User deleted.', 'success')
    return redirect(url_for('admin.users'))


# ─────────────────────────────────────────────
# RESTAURANT MANAGEMENT
# ─────────────────────────────────────────────

@admin_bp.route('/restaurants')
@admin_required
def restaurants():
    status = request.args.get('status', 'all')
    q      = request.args.get('q', '').strip()
    sql    = """SELECT r.*, u.name AS owner_name, u.email AS owner_email, u.phone AS owner_phone
                FROM restaurants r
                LEFT JOIN users u ON r.owner_id=u.id"""
    params = []
    where  = []
    if status != 'all':
        where.append("r.verification_status=%s")
        params.append(status)
    if q:
        where.append("(r.name LIKE %s OR r.cuisine LIKE %s OR r.city LIKE %s OR r.area LIKE %s OR u.name LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like, like, like])
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY r.created_at DESC"
    all_restaurants = execute_query(sql, tuple(params), fetchall=True)

    counts = {
        'all': execute_query("SELECT COUNT(*) AS c FROM restaurants", fetchone=True)['c'],
        'pending': execute_query("SELECT COUNT(*) AS c FROM restaurants WHERE verification_status='pending'", fetchone=True)['c'],
        'approved': execute_query("SELECT COUNT(*) AS c FROM restaurants WHERE verification_status='approved'", fetchone=True)['c'],
        'rejected': execute_query("SELECT COUNT(*) AS c FROM restaurants WHERE verification_status='rejected'", fetchone=True)['c'],
    }

    return render_template('admin/restaurants.html',
                           restaurants=all_restaurants, status=status, q=q, counts=counts)


@admin_bp.route('/restaurants/approve/<int:rid>', methods=['POST'])
@admin_bp.route('/restaurant/approve/<int:rid>', methods=['POST'])
@admin_required
def approve_restaurant(rid):
    r = execute_query("SELECT name, owner_id FROM restaurants WHERE id=%s", (rid,), fetchone=True)
    execute_query(
        "UPDATE restaurants SET verification_status='approved', status='active' WHERE id=%s",
        (rid,), commit=True
    )
    if r and r.get('owner_id'):
        execute_query("UPDATE users SET status='active' WHERE id=%s", (r['owner_id'],), commit=True)
    r_name = r['name'] if r else f"#{rid}"
    log_activity(session.get('user_id'), 'RESTAURANT_APPROVED', f"Approved and activated restaurant application for '{r_name}' (ID #{rid})")
    flash(f"Restaurant '{r_name}' approved and listed on Foody Hunters!", 'success')
    return redirect(url_for('admin.restaurants'))


@admin_bp.route('/restaurants/reject/<int:rid>', methods=['POST'])
@admin_bp.route('/restaurant/reject/<int:rid>', methods=['POST'])
@admin_required
def reject_restaurant(rid):
    r = execute_query("SELECT name, owner_id FROM restaurants WHERE id=%s", (rid,), fetchone=True)
    reason = request.form.get('rejection_reason', '').strip() or 'Application did not meet onboarding documentation or hygiene standards.'
    execute_query(
        "UPDATE restaurants SET verification_status='rejected', status='inactive', rejection_reason=%s WHERE id=%s",
        (reason, rid), commit=True
    )
    r_name = r['name'] if r else f"#{rid}"
    log_activity(session.get('user_id'), 'RESTAURANT_REJECTED', f"Rejected restaurant application for '{r_name}' (ID #{rid}): {reason}")
    flash(f"Restaurant '{r_name}' application has been rejected.", 'warning')
    return redirect(url_for('admin.restaurants'))



@admin_bp.route('/restaurants/toggle/<int:rid>', methods=['POST'])
@admin_bp.route('/restaurant/toggle/<int:rid>', methods=['POST'])
@admin_required
def toggle_restaurant(rid):
    r = execute_query("SELECT name, status, verification_status FROM restaurants WHERE id=%s", (rid,), fetchone=True)
    if r:
        new_status = 'inactive' if r['status'] == 'active' else 'active'
        execute_query("UPDATE restaurants SET status=%s WHERE id=%s", (new_status, rid), commit=True)
        r_name = r.get('name', f'#{rid}')
        log_activity(session.get('user_id'), 'RESTAURANT_TOGGLED', f"Toggled restaurant '{r_name}' status to {new_status}")
        flash(f"Restaurant '{r_name}' status updated to {new_status}.", 'info')
    return redirect(url_for('admin.restaurants'))


# ─────────────────────────────────────────────
# DELIVERY PARTNER MANAGEMENT
# ─────────────────────────────────────────────

@admin_bp.route('/delivery-partners')
@admin_required
def delivery_partners():
    status = request.args.get('status', 'all')
    q      = request.args.get('q', '').strip()

    sql = """
        SELECT u.id AS user_id, u.name, u.email, u.phone, u.status AS user_status,
               u.address, u.city, u.pincode, u.created_at,
               dp.id AS partner_id, dp.vehicle_type, dp.vehicle_number,
               dp.license_number, dp.is_available, dp.is_online,
               dp.total_deliveries, dp.total_earnings,
               COALESCE(dp.verification_status, CASE WHEN u.status='active' THEN 'approved' ELSE u.status END) AS verification_status
        FROM users u
        LEFT JOIN delivery_partners dp ON dp.user_id = u.id
        WHERE u.role = 'delivery'
    """
    params = []
    if status == 'pending':
        sql += " AND (dp.verification_status='pending' OR u.status='pending')"
    elif status in ('approved', 'active'):
        sql += " AND (dp.verification_status='approved' OR (dp.verification_status IS NULL AND u.status='active'))"
    elif status == 'rejected':
        sql += " AND (dp.verification_status='rejected' OR u.status='rejected')"
    elif status == 'inactive':
        sql += " AND u.status='inactive'"

    if q:
        sql += " AND (u.name LIKE %s OR u.email LIKE %s OR u.phone LIKE %s OR dp.vehicle_number LIKE %s OR dp.license_number LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like, like, like])

    sql += " ORDER BY u.created_at DESC"
    all_partners = execute_query(sql, tuple(params), fetchall=True) or []

    counts = {
        'all': (execute_query("SELECT COUNT(*) AS c FROM users WHERE role='delivery'", fetchone=True) or {}).get('c', 0),
        'pending': (execute_query(
            """SELECT COUNT(*) AS c FROM users u
               LEFT JOIN delivery_partners dp ON dp.user_id = u.id
               WHERE u.role='delivery' AND (dp.verification_status='pending' OR u.status='pending')""",
            fetchone=True
        ) or {}).get('c', 0),
        'approved': (execute_query(
            """SELECT COUNT(*) AS c FROM users u
               LEFT JOIN delivery_partners dp ON dp.user_id = u.id
               WHERE u.role='delivery' AND (dp.verification_status='approved' OR (dp.verification_status IS NULL AND u.status='active'))""",
            fetchone=True
        ) or {}).get('c', 0),
        'rejected': (execute_query(
            """SELECT COUNT(*) AS c FROM users u
               LEFT JOIN delivery_partners dp ON dp.user_id = u.id
               WHERE u.role='delivery' AND (dp.verification_status='rejected' OR u.status='rejected')""",
            fetchone=True
        ) or {}).get('c', 0),
        'inactive': (execute_query(
            """SELECT COUNT(*) AS c FROM users WHERE role='delivery' AND status='inactive'""",
            fetchone=True
        ) or {}).get('c', 0)
    }

    return render_template('admin/delivery_partners.html',
                           partners=all_partners, status=status, q=q, counts=counts)


@admin_bp.route('/delivery-partners/approve/<int:partner_id>', methods=['POST'])
@admin_bp.route('/delivery-partner/approve/<int:partner_id>', methods=['POST'])
@admin_required
def approve_delivery_partner(partner_id):
    user = execute_query("SELECT * FROM users WHERE id=%s AND role='delivery'", (partner_id,), fetchone=True)
    if not user:
        dp = execute_query("SELECT * FROM delivery_partners WHERE id=%s", (partner_id,), fetchone=True)
        if dp:
            user = execute_query("SELECT * FROM users WHERE id=%s", (dp['user_id'],), fetchone=True)

    if user:
        execute_query("UPDATE users SET status='active' WHERE id=%s", (user['id'],), commit=True)
        dp = execute_query("SELECT id FROM delivery_partners WHERE user_id=%s", (user['id'],), fetchone=True)
        if dp:
            execute_query(
                "UPDATE delivery_partners SET verification_status='approved', is_available=1, is_online=1 WHERE id=%s",
                (dp['id'],), commit=True
            )
        else:
            execute_query(
                "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, is_available, is_online, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-AB-1234', 1, 1, 'approved')",
                (user['id'],), commit=True
            )
        log_activity(session.get('user_id'), 'DELIVERY_PARTNER_APPROVED', f"Approved delivery partner application for '{user['name']}' (ID #{user['id']})")
        flash(f"Delivery partner '{user['name']}' approved and activated for delivery operations!", 'success')
    else:
        flash("Delivery partner account not found.", "danger")
    return redirect(url_for('admin.delivery_partners'))


@admin_bp.route('/delivery-partners/reject/<int:partner_id>', methods=['POST'])
@admin_bp.route('/delivery-partner/reject/<int:partner_id>', methods=['POST'])
@admin_required
def reject_delivery_partner(partner_id):
    user = execute_query("SELECT * FROM users WHERE id=%s AND role='delivery'", (partner_id,), fetchone=True)
    if not user:
        dp = execute_query("SELECT * FROM delivery_partners WHERE id=%s", (partner_id,), fetchone=True)
        if dp:
            user = execute_query("SELECT * FROM users WHERE id=%s", (dp['user_id'],), fetchone=True)

    if user:
        reason = request.form.get('rejection_reason', '').strip() or 'Application details or driving documents could not be verified.'
        execute_query("UPDATE users SET status='rejected' WHERE id=%s", (user['id'],), commit=True)
        execute_query(
            "UPDATE delivery_partners SET verification_status='rejected', is_available=0, is_online=0 WHERE user_id=%s",
            (user['id'],), commit=True
        )
        log_activity(session.get('user_id'), 'DELIVERY_PARTNER_REJECTED', f"Rejected delivery partner application for '{user['name']}' (ID #{user['id']}): {reason}")
        flash(f"Delivery partner '{user['name']}' application has been rejected.", 'warning')
    else:
        flash("Delivery partner account not found.", "danger")
    return redirect(url_for('admin.delivery_partners'))


@admin_bp.route('/delivery-partners/toggle/<int:partner_id>', methods=['POST'])
@admin_bp.route('/delivery-partner/toggle/<int:partner_id>', methods=['POST'])
@admin_required
def toggle_delivery_partner(partner_id):
    user = execute_query("SELECT * FROM users WHERE id=%s AND role='delivery'", (partner_id,), fetchone=True)
    if not user:
        dp = execute_query("SELECT * FROM delivery_partners WHERE id=%s", (partner_id,), fetchone=True)
        if dp:
            user = execute_query("SELECT * FROM users WHERE id=%s", (dp['user_id'],), fetchone=True)

    if user:
        new_status = 'inactive' if user['status'] == 'active' else 'active'
        execute_query("UPDATE users SET status=%s WHERE id=%s", (new_status, user['id']), commit=True)
        new_avail = 1 if new_status == 'active' else 0
        execute_query(
            "UPDATE delivery_partners SET is_available=%s, is_online=%s WHERE user_id=%s",
            (new_avail, new_avail, user['id']),
            commit=True
        )
        log_activity(session.get('user_id'), 'DELIVERY_PARTNER_TOGGLED', f"Toggled delivery partner '{user['name']}' status to {new_status}")
        flash(f"Delivery partner '{user['name']}' status set to {new_status}.", 'info')
    else:
        flash("Delivery partner account not found.", "danger")
    return redirect(url_for('admin.delivery_partners'))


@admin_bp.route('/delivery-partners/add', methods=['GET', 'POST'])
@admin_required
def add_delivery_partner():
    if request.method == 'POST':
        name           = request.form.get('name', '').strip()
        email          = request.form.get('email', '').strip().lower()
        phone          = request.form.get('phone', '').strip()
        vehicle_type   = request.form.get('vehicle_type', 'Motorcycle').strip() or 'Motorcycle'
        vehicle_number = request.form.get('vehicle_number', 'GJ-02-AB-1234').strip() or 'GJ-02-AB-1234'
        license_number = request.form.get('license_number', 'DL-GJ02-2024-00000').strip() or 'DL-GJ02-2024-00000'
        pw             = request.form.get('password', 'foody123')

        existing = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetchone=True)
        if existing:
            flash('Email already registered.', 'danger')
        else:
            new_uid = execute_query(
                """INSERT INTO users (name, email, phone, password_hash, role, status)
                   VALUES (%s,%s,%s,%s,'delivery','active')""",
                (name, email, phone, generate_password_hash(pw)), commit=True
            )
            execute_query(
                """INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings, verification_status)
                   VALUES (%s, %s, %s, %s, 1, 1, 0, 0.00, 'approved')""",
                (new_uid, vehicle_type, vehicle_number, license_number), commit=True
            )
            flash(f"Delivery partner '{name}' added and activated!", 'success')
            return redirect(url_for('admin.delivery_partners'))
    return render_template('admin/add_delivery_partner.html')


@admin_bp.route('/delivery-partners/<int:partner_id>')
@admin_bp.route('/delivery-partner/<int:partner_id>')
@admin_required
def delivery_partner_detail(partner_id):
    """Admin view for detailed delivery partner dossier and delivery history."""
    partner = execute_query(
        """SELECT u.id AS user_id, u.name, u.email, u.phone, u.city, u.address,
                  u.status AS user_status, u.created_at,
                  dp.id AS partner_id, dp.vehicle_type, dp.vehicle_number,
                  dp.license_number, dp.is_available, dp.is_online,
                  dp.total_deliveries, dp.total_earnings, dp.current_lat, dp.current_lng,
                  COALESCE(dp.verification_status, CASE WHEN u.status='active' THEN 'approved' ELSE u.status END) AS verification_status
           FROM users u
           LEFT JOIN delivery_partners dp ON dp.user_id = u.id
           WHERE (u.id=%s OR dp.id=%s) AND u.role='delivery'""",
        (partner_id, partner_id), fetchone=True
    )
    if not partner:
        flash('Delivery partner not found.', 'danger')
        return redirect(url_for('admin.delivery_partners')), 404

    recent_assignments = execute_query(
        """SELECT da.*, o.order_code, o.order_status, o.total_amount,
                  r.name AS restaurant_name
           FROM delivery_assignments da
           JOIN orders o ON da.order_id = o.id
           LEFT JOIN restaurants r ON o.restaurant_id = r.id
           WHERE da.partner_id = %s
           ORDER BY da.assigned_at DESC LIMIT 15""",
        (partner['user_id'],), fetchall=True
    ) or []

    if request.headers.get('Accept') == 'application/json' or request.is_json:
        return jsonify({
            'success': True,
            'partner': partner,
            'recent_assignments': recent_assignments
        })

    return render_template('admin/delivery_partner_detail.html',
                           partner=partner,
                           recent_assignments=recent_assignments)


@admin_bp.route('/delivery-partners/assign', methods=['POST'])
@admin_required
def assign_delivery():
    order_id   = request.form.get('order_id')
    partner_id = request.form.get('partner_id')
    if not order_id or not partner_id:
        flash('Order ID and Delivery Partner ID are required.', 'danger')
        return redirect(url_for('admin.orders'))

    # Check if already assigned
    existing = execute_query(
        "SELECT id FROM delivery_assignments WHERE order_id=%s", (order_id,), fetchone=True
    )
    if existing:
        execute_query(
            "UPDATE delivery_assignments SET partner_id=%s, status='assigned', assigned_at=NOW() WHERE order_id=%s",
            (partner_id, order_id), commit=True
        )
    else:
        execute_query(
            "INSERT INTO delivery_assignments (order_id, partner_id, status, assigned_at) VALUES (%s,%s,'assigned',NOW())",
            (order_id, partner_id), commit=True
        )

    # Only set order_status='confirmed' if currently placed or not set, preserving preparing/ready status
    cur_order = execute_query("SELECT order_status FROM orders WHERE id=%s", (order_id,), fetchone=True)
    if cur_order and cur_order.get('order_status') in ('placed', None):
        execute_query(
            "UPDATE orders SET order_status='confirmed' WHERE id=%s", (order_id,), commit=True
        )

    log_activity(session.get('user_id'), 'DELIVERY_ASSIGNED', f"Assigned order #{order_id} to rider #{partner_id}")
    flash('Delivery partner assigned successfully!', 'success')
    return redirect(url_for('admin.orders'))


# ─────────────────────────────────────────────
# RESTAURANT STAFF MANAGEMENT
# ─────────────────────────────────────────────

@admin_bp.route('/staff')
@admin_required
def staff():
    """Admin staff management: view and govern staff across all restaurants."""
    status = request.args.get('status', 'all')
    rest_id = request.args.get('restaurant_id', 'all')
    q = request.args.get('q', '').strip()

    sql = """
        SELECT s.*, u.name, u.email, u.phone, u.status AS user_status, r.name AS restaurant_name
        FROM restaurant_staff s
        JOIN users u ON s.user_id = u.id
        JOIN restaurants r ON s.restaurant_id = r.id
        WHERE 1=1
    """
    params = []

    if status != 'all':
        sql += " AND s.status = %s"
        params.append(status)

    if rest_id != 'all' and rest_id.isdigit():
        sql += " AND s.restaurant_id = %s"
        params.append(int(rest_id))

    if q:
        sql += " AND (u.name LIKE %s OR u.email LIKE %s OR u.phone LIKE %s OR r.name LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like, like])

    sql += " ORDER BY s.created_at DESC"
    staff_members = execute_query(sql, tuple(params), fetchall=True) or []

    restaurants = execute_query("SELECT id, name FROM restaurants ORDER BY name ASC", fetchall=True) or []

    pending_count = execute_query("SELECT COUNT(*) AS c FROM restaurant_staff WHERE status='pending'", fetchone=True)['c']

    return render_template('admin/staff.html',
                           staff_members=staff_members,
                           restaurants=restaurants,
                           status=status,
                           rest_id=rest_id,
                           q=q,
                           pending_count=pending_count)


@admin_bp.route('/staff/verify/<int:staff_id>/<action>', methods=['POST'])
@admin_required
def verify_staff(staff_id, action):
    """Admin approve or reject pending staff application."""
    if action in ('approved', 'rejected'):
        execute_query("UPDATE restaurant_staff SET status=%s, updated_at=NOW() WHERE id=%s", (action, staff_id), commit=True)
        log_activity(session.get('user_id'), 'STAFF_VERIFIED', f"Set staff #{staff_id} status to {action}")
        flash(f"Staff member {action}.", 'success')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/staff/toggle/<int:staff_id>', methods=['POST'])
@admin_required
def toggle_staff(staff_id):
    """Toggle staff account between approved and suspended."""
    rec = execute_query("SELECT status FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
    if rec:
        new_status = 'suspended' if rec['status'] == 'approved' else 'approved'
        execute_query("UPDATE restaurant_staff SET status=%s, updated_at=NOW() WHERE id=%s", (new_status, staff_id), commit=True)
        log_activity(session.get('user_id'), 'STAFF_STATUS_TOGGLE', f"Changed staff #{staff_id} status to {new_status}")
        flash(f"Staff status updated to {new_status.title()}.", 'success')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/staff/reassign/<int:staff_id>', methods=['POST'])
@admin_required
def reassign_staff(staff_id):
    """Reassign staff member to another restaurant."""
    new_rest_id = request.form.get('restaurant_id')
    rest = execute_query("SELECT name FROM restaurants WHERE id=%s", (new_rest_id,), fetchone=True)
    if rest:
        execute_query("UPDATE restaurant_staff SET restaurant_id=%s, updated_at=NOW() WHERE id=%s", (new_rest_id, staff_id), commit=True)
        log_activity(session.get('user_id'), 'STAFF_REASSIGNED', f"Reassigned staff #{staff_id} to restaurant '{rest['name']}'")
        flash(f"Staff member reassigned to {rest['name']}.", 'success')
    else:
        flash('Invalid restaurant selected.', 'danger')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/staff/delete/<int:staff_id>', methods=['POST'])
@admin_required
def delete_staff(staff_id):
    """Delete staff member account."""
    rec = execute_query("SELECT user_id FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
    if rec:
        execute_query("DELETE FROM restaurant_staff WHERE id=%s", (staff_id,), commit=True)
        execute_query("DELETE FROM users WHERE id=%s AND role='staff'", (rec['user_id'],), commit=True)
        log_activity(session.get('user_id'), 'STAFF_DELETED', f"Deleted staff member #{staff_id}")
        flash('Staff member deleted.', 'success')
    return redirect(url_for('admin.staff'))


# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

@admin_bp.route('/categories')
@admin_required
def categories():
    cats = execute_query(
        "SELECT fc.*, COUNT(fi.id) AS food_count FROM food_categories fc "
        "LEFT JOIN food_items fi ON fc.id=fi.category_id "
        "GROUP BY fc.id ORDER BY fc.sort_order ASC",
        fetchall=True
    )
    return render_template('admin/categories.html', categories=cats)


@admin_bp.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    name   = request.form.get('name', '').strip()
    icon   = request.form.get('icon', '🍽️').strip()
    sort_o = request.form.get('sort_order', 99)
    if name:
        execute_query(
            "INSERT INTO food_categories (name, icon, sort_order) VALUES (%s,%s,%s)",
            (name, icon, sort_o), commit=True
        )
        flash(f"Category '{name}' added!", 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/delete/<int:cid>', methods=['POST'])
@admin_required
def delete_category(cid):
    execute_query("DELETE FROM food_categories WHERE id=%s", (cid,), commit=True)
    flash('Category deleted.', 'success')
    return redirect(url_for('admin.categories'))


# ─────────────────────────────────────────────
# FOOD ITEMS
# ─────────────────────────────────────────────

@admin_bp.route('/food-items')
@admin_required
def food_items():
    q = request.args.get('q', '').strip()
    if q:
        like = f"%{q}%"
        items = execute_query(
            """SELECT fi.*, r.name AS restaurant_name, fc.name AS category_name
               FROM food_items fi JOIN restaurants r ON fi.restaurant_id=r.id
               LEFT JOIN food_categories fc ON fi.category_id=fc.id
               WHERE fi.name LIKE %s OR r.name LIKE %s ORDER BY fi.name""",
            (like, like), fetchall=True
        )
    else:
        items = execute_query(
            """SELECT fi.*, r.name AS restaurant_name, fc.name AS category_name
               FROM food_items fi JOIN restaurants r ON fi.restaurant_id=r.id
               LEFT JOIN food_categories fc ON fi.category_id=fc.id
               ORDER BY r.name, fi.name""",
            fetchall=True
        )
    return render_template('admin/food_items.html', items=items, q=q)


# ─────────────────────────────────────────────
# ORDER MANAGEMENT
# ─────────────────────────────────────────────

@admin_bp.route('/orders')
@admin_required
def orders():
    status = request.args.get('status', 'all')
    q      = request.args.get('q', '').strip()
    sql    = """SELECT o.*, u.name AS customer_name, r.name AS restaurant_name,
                       u2.name AS partner_name,
                       os.restaurant_net_payable, os.platform_commission_amount,
                       os.partner_payout_amount, os.restaurant_settlement_status,
                       os.partner_settlement_status
                FROM orders o JOIN users u ON o.user_id=u.id
                JOIN restaurants r ON o.restaurant_id=r.id
                LEFT JOIN delivery_assignments da ON da.order_id=o.id
                LEFT JOIN users u2 ON da.partner_id=u2.id
                LEFT JOIN order_settlements os ON os.order_id=o.id"""
    params = []
    where  = []
    if status != 'all':
        where.append("o.order_status=%s")
        params.append(status)
    if q:
        where.append("(o.order_code LIKE %s OR u.name LIKE %s OR r.name LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY o.created_at DESC LIMIT 100"
    all_orders = execute_query(sql, tuple(params), fetchall=True)
    partners   = execute_query("SELECT * FROM users WHERE role='delivery' AND status='active'", fetchall=True)
    return render_template('admin/orders.html',
                           orders=all_orders, status=status, q=q, partners=partners)


# ─────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────

@admin_bp.route('/payments')
@admin_required
def payments():
    all_payments = execute_query(
        """SELECT p.*, o.order_code, u.name AS customer_name, r.name AS restaurant_name
           FROM payments p
           JOIN orders o ON p.order_id=o.id
           JOIN users u ON o.user_id=u.id
           JOIN restaurants r ON o.restaurant_id=r.id
           ORDER BY p.payment_date DESC LIMIT 100""",
        fetchall=True
    )
    total_revenue = execute_query(
        "SELECT COALESCE(SUM(amount),0) AS t FROM payments WHERE payment_status='paid'",
        fetchone=True
    )['t']

    settlements = execute_query(
        """SELECT os.*, o.order_code, r.name AS restaurant_name,
                  u.name AS partner_name
           FROM order_settlements os
           JOIN orders o ON os.order_id = o.id
           JOIN restaurants r ON os.restaurant_id = r.id
           LEFT JOIN users u ON os.partner_id = u.id
           ORDER BY os.created_at DESC LIMIT 100""",
        fetchall=True
    ) or []

    settlement_summary = execute_query(
        """SELECT 
               COALESCE(SUM(platform_commission_amount), 0) AS total_commission,
               COALESCE(SUM(restaurant_net_payable), 0) AS total_restaurant_payable,
               COALESCE(SUM(partner_payout_amount), 0) AS total_partner_payout,
               COALESCE(SUM(CASE WHEN restaurant_settlement_status IN ('paid_settled','settled') THEN restaurant_net_payable ELSE 0 END), 0) AS settled_payouts,
               COALESCE(SUM(CASE WHEN restaurant_settlement_status = 'settlement_pending' THEN restaurant_net_payable ELSE 0 END), 0) AS pending_payouts
           FROM order_settlements""",
        fetchone=True
    ) or {}

    return render_template('admin/payments.html',
                           payments=all_payments, total_revenue=total_revenue,
                           settlements=settlements, settlement_summary=settlement_summary)


# ─────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────

@admin_bp.route('/reviews')
@admin_required
def reviews():
    all_reviews = execute_query(
        """SELECT rv.*, u.name AS user_name, r.name AS restaurant_name
           FROM reviews rv JOIN users u ON rv.user_id=u.id
           JOIN restaurants r ON rv.restaurant_id=r.id
           ORDER BY rv.created_at DESC""",
        fetchall=True
    )
    return render_template('admin/reviews.html', reviews=all_reviews)


@admin_bp.route('/reviews/delete/<int:rid>', methods=['POST'])
@admin_required
def delete_review(rid):
    execute_query("DELETE FROM reviews WHERE id=%s", (rid,), commit=True)
    flash('Review deleted.', 'success')
    return redirect(url_for('admin.reviews'))


# ─────────────────────────────────────────────
# COMPLAINTS
# ─────────────────────────────────────────────

@admin_bp.route('/complaints')
@admin_required
def complaints():
    all_complaints = execute_query(
        "SELECT * FROM complaints ORDER BY created_at DESC",
        fetchall=True
    )
    return render_template('admin/complaints.html', complaints=all_complaints)


@admin_bp.route('/complaints/resolve/<int:cid>', methods=['POST'])
@admin_required
def resolve_complaint(cid):
    execute_query("UPDATE complaints SET status='resolved' WHERE id=%s", (cid,), commit=True)
    log_activity(session.get('user_id'), 'COMPLAINT_RESOLVED', f"Marked complaint ticket #{cid} as resolved")
    flash('Complaint marked as resolved.', 'success')
    return redirect(url_for('admin.complaints'))


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────

@admin_bp.route('/reports')
@admin_required
def reports():
    import json
    # Revenue by month
    monthly = execute_query(
        """SELECT DATE_FORMAT(created_at,'%Y-%m') AS month, SUM(total_amount) AS revenue
           FROM orders WHERE order_status!='cancelled'
           GROUP BY month ORDER BY month DESC LIMIT 12""",
        fetchall=True
    )
    # Orders by status
    by_status = execute_query(
        "SELECT order_status, COUNT(*) AS cnt FROM orders GROUP BY order_status",
        fetchall=True
    )
    # Top restaurants by revenue
    top_restaurants = execute_query(
        """SELECT r.name, SUM(o.total_amount) AS revenue, COUNT(o.id) AS orders
           FROM orders o JOIN restaurants r ON o.restaurant_id=r.id
           WHERE o.order_status='delivered'
           GROUP BY r.id, r.name ORDER BY revenue DESC LIMIT 10""",
        fetchall=True
    )
    # Most popular food
    popular_foods = execute_query(
        """SELECT fi.name, SUM(oi.quantity) AS total_qty
           FROM order_items oi JOIN food_items fi ON oi.food_item_id=fi.id
           GROUP BY fi.id, fi.name ORDER BY total_qty DESC LIMIT 10""",
        fetchall=True
    )
    return render_template('admin/reports.html',
                           monthly=monthly, by_status=by_status,
                           top_restaurants=top_restaurants,
                           popular_foods=popular_foods,
                           monthly_json=json.dumps([{'month': m['month'], 'revenue': float(m['revenue'])} for m in monthly]),
                           status_json=json.dumps([{'status': s['order_status'], 'count': s['cnt']} for s in by_status]))


# ─────────────────────────────────────────────
# COUPONS
# ─────────────────────────────────────────────

@admin_bp.route('/coupons')
@admin_required
def coupons():
    all_coupons = execute_query("SELECT * FROM coupons ORDER BY created_at DESC", fetchall=True)
    return render_template('admin/coupons.html', coupons=all_coupons)


@admin_bp.route('/coupons/add', methods=['POST'])
@admin_required
def add_coupon():
    code           = request.form.get('code', '').strip().upper()
    discount_type  = request.form.get('discount_type', 'percentage')
    discount_value = request.form.get('discount_value', 0)
    max_discount   = request.form.get('max_discount') or None
    min_order      = request.form.get('min_order_amount', 0)
    is_active      = 1 if request.form.get('is_active') else 0

    if code:
        execute_query(
            """INSERT INTO coupons (code, discount_type, discount_value, max_discount,
               min_order_amount, is_active) VALUES (%s,%s,%s,%s,%s,%s)""",
            (code, discount_type, discount_value, max_discount, min_order, is_active),
            commit=True
        )
        flash(f"Coupon '{code}' created!", 'success')
    return redirect(url_for('admin.coupons'))


@admin_bp.route('/coupons/toggle/<int:cid>', methods=['POST'])
@admin_required
def toggle_coupon(cid):
    c = execute_query("SELECT is_active FROM coupons WHERE id=%s", (cid,), fetchone=True)
    if c:
        execute_query("UPDATE coupons SET is_active=%s WHERE id=%s",
                      (0 if c['is_active'] else 1, cid), commit=True)
    return redirect(url_for('admin.coupons'))


@admin_bp.route('/coupons/delete/<int:cid>', methods=['POST'])
@admin_required
def delete_coupon(cid):
    execute_query("DELETE FROM coupons WHERE id=%s", (cid,), commit=True)
    flash('Coupon deleted.', 'success')
    return redirect(url_for('admin.coupons'))


# ─────────────────────────────────────────────
# ADMIN PROFILE (VIEW & EDIT PERSISTENCE)
# ─────────────────────────────────────────────

@admin_bp.route('/profile')
@admin_required
def profile():
    user_id = session['user_id']
    user = execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetchone=True)
    stats = {
        'total_orders': execute_query("SELECT COUNT(*) AS c FROM orders", fetchone=True)['c'],
        'total_users': execute_query("SELECT COUNT(*) AS c FROM users", fetchone=True)['c'],
        'total_restaurants': execute_query("SELECT COUNT(*) AS c FROM restaurants", fetchone=True)['c'],
    }
    return render_template('admin/profile.html', user=user, stats=stats)


@admin_bp.route('/profile/update', methods=['POST'])
@admin_required
def profile_update():
    user_id = session['user_id']
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    gender = request.form.get('gender') or None
    dob = request.form.get('dob') or None
    address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip() or 'Mehsana'
    state = request.form.get('state', '').strip() or 'Gujarat'
    pincode = request.form.get('pincode', '').strip() or '384001'

    if not name or not phone:
        flash('Name and phone number are required.', 'danger')
        return redirect(url_for('admin.profile'))

    execute_query(
        """UPDATE users 
           SET name=%s, phone=%s, gender=%s, dob=%s, address=%s,
               city=%s, state=%s, pincode=%s, updated_at=NOW()
           WHERE id=%s""",
        (name, phone, gender, dob, address, city, state, pincode, user_id),
        commit=True
    )

    pic_file = request.files.get('profile_pic')
    if pic_file and pic_file.filename:
        pic_url = save_uploaded_image(pic_file, 'users')
        if pic_url:
            execute_query("UPDATE users SET profile_pic=%s WHERE id=%s", (pic_url, user_id), commit=True)

    session['user_name'] = name
    log_activity(session.get('user_id'), 'ADMIN_PROFILE_UPDATE', f"Admin '{name}' updated system profile")
    flash('Administrator profile updated successfully!', 'success')
    return redirect(url_for('admin.profile'))


# ─────────────────────────────────────────────
# ACTIVITY & AUDIT LOGS
# ─────────────────────────────────────────────

@admin_bp.route('/activity')
@admin_required
def activity():
    page = request.args.get('page', 1, type=int)
    limit = 50
    offset = max(0, (page - 1) * limit)
    logs = execute_query(
        """SELECT l.*, u.name AS admin_name, u.email AS admin_email
           FROM admin_logs l
           LEFT JOIN users u ON l.admin_id = u.id
           ORDER BY l.created_at DESC
           LIMIT %s OFFSET %s""",
        (limit, offset), fetchall=True
    )
    total_logs = execute_query("SELECT COUNT(*) AS c FROM admin_logs", fetchone=True)['c']
    return render_template('admin/activity.html', logs=logs, total_logs=total_logs, page=page, limit=limit)


