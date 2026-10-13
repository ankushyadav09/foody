"""
routes/admin.py – Admin panel routes for Foody Hunters
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from database import execute_query
from utils.helpers import admin_required, save_uploaded_image, log_activity
from werkzeug.security import generate_password_hash
import json

admin_bp = Blueprint('admin', __name__)


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@admin_bp.route('/')
@admin_required
def index():
    return redirect(url_for('admin.dashboard'))


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
        'open_complaints':       execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status='open'", fetchone=True)['c'],
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
    sql    = "SELECT r.*, u.name AS owner_name, u.email AS owner_email FROM restaurants r LEFT JOIN users u ON r.owner_id=u.id"
    params = []
    where  = []
    if status != 'all':
        where.append("r.verification_status=%s")
        params.append(status)
    if q:
        where.append("(r.name LIKE %s OR r.cuisine LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY r.created_at DESC"
    all_restaurants = execute_query(sql, tuple(params), fetchall=True)
    return render_template('admin/restaurants.html',
                           restaurants=all_restaurants, status=status, q=q)


@admin_bp.route('/restaurants/approve/<int:rid>', methods=['POST'])
@admin_required
def approve_restaurant(rid):
    execute_query(
        "UPDATE restaurants SET verification_status='approved', status='active' WHERE id=%s",
        (rid,), commit=True
    )
    log_activity(session.get('user_id'), 'RESTAURANT_APPROVED', f"Approved and activated restaurant #{rid}")
    flash('Restaurant approved and activated!', 'success')
    return redirect(url_for('admin.restaurants'))


@admin_bp.route('/restaurants/reject/<int:rid>', methods=['POST'])
@admin_required
def reject_restaurant(rid):
    execute_query(
        "UPDATE restaurants SET verification_status='rejected', status='inactive' WHERE id=%s",
        (rid,), commit=True
    )
    log_activity(session.get('user_id'), 'RESTAURANT_REJECTED', f"Rejected restaurant #{rid}")
    flash('Restaurant rejected.', 'warning')
    return redirect(url_for('admin.restaurants'))


@admin_bp.route('/restaurants/toggle/<int:rid>', methods=['POST'])
@admin_required
def toggle_restaurant(rid):
    r = execute_query("SELECT status, verification_status FROM restaurants WHERE id=%s", (rid,), fetchone=True)
    if r:
        new_status = 'inactive' if r['status'] == 'active' else 'active'
        execute_query("UPDATE restaurants SET status=%s WHERE id=%s", (new_status, rid), commit=True)
        log_activity(session.get('user_id'), 'RESTAURANT_TOGGLED', f"Toggled restaurant #{rid} status to {new_status}")
    return redirect(url_for('admin.restaurants'))


# ─────────────────────────────────────────────
# DELIVERY PARTNER MANAGEMENT
# ─────────────────────────────────────────────

@admin_bp.route('/delivery-partners')
@admin_required
def delivery_partners():
    partners = execute_query(
        "SELECT * FROM users WHERE role='delivery' ORDER BY created_at DESC",
        fetchall=True
    )
    return render_template('admin/delivery_partners.html', partners=partners)


@admin_bp.route('/delivery-partners/add', methods=['GET', 'POST'])
@admin_required
def add_delivery_partner():
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        pw    = request.form.get('password', 'foody123')

        existing = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetchone=True)
        if existing:
            flash('Email already registered.', 'danger')
        else:
            execute_query(
                """INSERT INTO users (name, email, phone, password_hash, role, status)
                   VALUES (%s,%s,%s,%s,'delivery','active')""",
                (name, email, phone, generate_password_hash(pw)), commit=True
            )
            flash(f"Delivery partner '{name}' added!", 'success')
            return redirect(url_for('admin.delivery_partners'))
    return render_template('admin/add_delivery_partner.html')


@admin_bp.route('/delivery-partners/assign', methods=['POST'])
@admin_required
def assign_delivery():
    order_id   = request.form.get('order_id')
    partner_id = request.form.get('partner_id')
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
    execute_query(
        "UPDATE orders SET order_status='confirmed' WHERE id=%s", (order_id,), commit=True
    )
    log_activity(session.get('user_id'), 'DELIVERY_ASSIGNED', f"Assigned order #{order_id} to rider #{partner_id}")
    flash('Delivery partner assigned!', 'success')
    return redirect(url_for('admin.orders'))


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
                       u2.name AS partner_name
                FROM orders o JOIN users u ON o.user_id=u.id
                JOIN restaurants r ON o.restaurant_id=r.id
                LEFT JOIN delivery_assignments da ON da.order_id=o.id
                LEFT JOIN users u2 ON da.partner_id=u2.id"""
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
    return render_template('admin/payments.html',
                           payments=all_payments, total_revenue=total_revenue)


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


