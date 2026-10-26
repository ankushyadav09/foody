"""
routes/staff.py – Portal 5: Restaurant / Hotel Staff Portal
Kitchen Operations, Order Queue Management, Menu Availability & Prep Telemetry
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from database import execute_query
from utils.helpers import (staff_required, validate_email, validate_phone,
                           validate_password, format_datetime,
                           get_staff_auth, set_staff_auth, clear_staff_auth)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

staff_bp = Blueprint('staff', __name__)


# ─────────────────────────────────────────────
# STAFF AUTHENTICATION & ONBOARDING
# ─────────────────────────────────────────────

@staff_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Dedicated login page for Restaurant / Hotel Kitchen Staff."""
    if get_staff_auth():
        return redirect(url_for('staff.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password   = request.form.get('password', '')
        remember   = request.form.get('remember_me')

        if not identifier or not password:
            flash('Staff email/mobile and password are required.', 'danger')
            return render_template('staff/login.html')

        if identifier.isdigit() and len(identifier) == 10:
            user = execute_query("SELECT * FROM users WHERE phone=%s", (identifier,), fetchone=True)
        else:
            user = execute_query("SELECT * FROM users WHERE email=%s", (identifier,), fetchone=True)
            if not user and '@' in identifier:
                alt_domain = 'foodyhunters.com' if '@foodiehunter.com' in identifier else ('foodiehunter.com' if '@foodyhunters.com' in identifier else None)
                if alt_domain:
                    alt_email = identifier.split('@')[0] + '@' + alt_domain
                    user = execute_query("SELECT * FROM users WHERE email=%s", (alt_email,), fetchone=True)

        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid staff credentials.', 'danger')
            return render_template('staff/login.html')

        if user['role'] != 'staff':
            flash('This portal is reserved for restaurant and kitchen staff. Please use the appropriate portal for your role.', 'warning')
            return render_template('staff/login.html')

        if user['status'] == 'inactive':
            flash('Your staff account is currently deactivated. Please contact your restaurant manager or administrator.', 'warning')
            return render_template('staff/login.html')

        # Check restaurant staff assignment and approval
        staff_rec = execute_query(
            """SELECT s.*, r.name as restaurant_name, r.is_open, r.verification_status as rest_verification
               FROM restaurant_staff s
               JOIN restaurants r ON s.restaurant_id=r.id
               WHERE s.user_id=%s""",
            (user['id'],), fetchone=True
        )

        if not staff_rec:
            flash('No restaurant assignment found for this staff account. Please contact your restaurant owner.', 'danger')
            return render_template('staff/login.html')

        if staff_rec['status'] == 'pending':
            flash('Your staff registration is currently pending approval by your restaurant owner or administrator.', 'info')
            return render_template('staff/login.html')

        if staff_rec['status'] in ('rejected', 'suspended'):
            flash(f"Your staff access has been {staff_rec['status']}. Please contact your restaurant manager.", 'danger')
            return render_template('staff/login.html')

        session.permanent = bool(remember)
        set_staff_auth(
            user,
            restaurant_id=staff_rec['restaurant_id'],
            staff_role=staff_rec['staff_role'],
            restaurant_name=staff_rec.get('restaurant_name'),
            shift=staff_rec.get('shift', 'Full Time')
        )

        flash(f"Kitchen Desk Active. Welcome, {user['name']} ({staff_rec['restaurant_name']})!", 'success')
        return redirect(url_for('staff.dashboard'))

    return render_template('staff/login.html')


@staff_bp.route('/logout')
def logout():
    """Securely log out staff member."""
    clear_staff_auth()
    flash("Staff session ended.", "info")
    return redirect(url_for('staff.login'))


@staff_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Onboarding application page for restaurant kitchen staff."""
    if 'user_id' in session and session.get('role') == 'staff':
        return redirect(url_for('staff.dashboard'))

    # Load approved restaurants for dropdown selection
    approved_restaurants = execute_query(
        "SELECT id, name, area, cuisine FROM restaurants WHERE verification_status='approved' ORDER BY name ASC",
        fetchall=True
    )

    if request.method == 'POST':
        name            = request.form.get('name', '').strip()
        email           = request.form.get('email', '').strip().lower()
        phone           = request.form.get('phone', '').strip()
        restaurant_id   = request.form.get('restaurant_id', '').strip()
        staff_role      = request.form.get('staff_role', 'kitchen_staff').strip()
        shift           = request.form.get('shift', 'Full Time').strip()
        password        = request.form.get('password', '')
        confirm         = request.form.get('confirm_password', '')

        errors = []
        if not name:
            errors.append('Full name is required.')
        if not validate_email(email):
            errors.append('Enter a valid email address.')
        if not validate_phone(phone):
            errors.append('Enter a valid 10-digit Indian mobile number.')
        if not restaurant_id:
            errors.append('Please select your assigned restaurant.')
        if staff_role not in ('kitchen_staff', 'restaurant_manager'):
            staff_role = 'kitchen_staff'
        if not validate_password(password):
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        target_rest = None
        if restaurant_id:
            try:
                target_rest = execute_query("SELECT id, name, owner_id FROM restaurants WHERE id=%s", (int(restaurant_id),), fetchone=True)
                if not target_rest:
                    errors.append('Selected restaurant does not exist.')
            except Exception:
                errors.append('Invalid restaurant selection.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('staff/register.html', restaurants=approved_restaurants, form=request.form)

        # Check duplicate email or phone
        existing = execute_query("SELECT id, email, phone FROM users WHERE email=%s OR phone=%s", (email, phone), fetchone=True)
        if existing:
            if existing['email'] == email:
                flash('This email is already registered. Please login.', 'warning')
            else:
                flash('This contact number is already registered. Please login.', 'warning')
            return render_template('staff/register.html', restaurants=approved_restaurants, form=request.form)

        # SECURITY: Strictly staff role
        pw_hash = generate_password_hash(password)
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status)
               VALUES (%s, %s, %s, %s, 'staff', %s, 'Mehsana', 'Gujarat', '384001', 'active')""",
            (name, email, phone, pw_hash, f"Staff at {target_rest['name']}"),
            commit=True
        )

        execute_query(
            """INSERT INTO restaurant_staff (user_id, restaurant_id, staff_role, status, shift)
               VALUES (%s, %s, %s, 'pending', %s)""",
            (user_id, int(restaurant_id), staff_role, shift),
            commit=True
        )

        # Notify restaurant owner of new staff registration
        if target_rest and target_rest.get('owner_id'):
            try:
                execute_query(
                    """INSERT INTO notifications (user_id, role, title, message)
                       VALUES (%s, 'restaurant', 'New Staff Application', %s)""",
                    (target_rest['owner_id'], f"{name} applied for {staff_role.replace('_', ' ').title()} position. Review in Staff Management."),
                    commit=True
                )
            except Exception:
                pass

        flash(f'Staff registration submitted for {target_rest["name"]}! Pending restaurant owner or admin approval.', 'info')
        return redirect(url_for('staff.login'))

    return render_template('staff/register.html', restaurants=approved_restaurants, form={})


# ─────────────────────────────────────────────
# KITCHEN DASHBOARD & OPERATIONS
# ─────────────────────────────────────────────

@staff_bp.route('/')
@staff_bp.route('/dashboard')
@staff_required
def dashboard():
    """Main kitchen operations workspace for assigned restaurant staff."""
    rest_id = session.get('restaurant_id')

    rest = execute_query("SELECT * FROM restaurants WHERE id=%s", (rest_id,), fetchone=True)
    if not rest:
        flash('Restaurant record not found.', 'danger')
        return redirect(url_for('auth.logout'))

    # Kitchen status counts for this restaurant ONLY
    stats = {
        'new_orders': execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s AND order_status IN ('placed','confirmed')",
            (rest_id,), fetchone=True)['c'],
        'preparing_orders': execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s AND order_status='preparing'",
            (rest_id,), fetchone=True)['c'],
        'ready_orders': execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s AND order_status='ready_for_pickup'",
            (rest_id,), fetchone=True)['c'],
        'today_delivered': execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s AND order_status='delivered' AND DATE(created_at)=CURDATE()",
            (rest_id,), fetchone=True)['c'],
        'out_of_stock_items': execute_query(
            "SELECT COUNT(*) AS c FROM food_items WHERE restaurant_id=%s AND availability=0",
            (rest_id,), fetchone=True)['c']
    }

    # Fetch active orders requiring kitchen action
    active_orders = execute_query(
        """SELECT o.*, u.name AS customer_name, u.phone AS customer_phone
           FROM orders o
           JOIN users u ON o.user_id = u.id
           WHERE o.restaurant_id = %s
             AND o.order_status IN ('placed', 'confirmed', 'preparing', 'ready_for_pickup')
           ORDER BY o.created_at ASC""",
        (rest_id,), fetchall=True
    ) or []

    # Attach itemized dishes to each order
    now = datetime.now()
    for o in active_orders:
        dish_items = execute_query(
            """SELECT oi.*, fi.veg_type, fi.preparation_time
               FROM order_items oi
               LEFT JOIN food_items fi ON oi.food_item_id = fi.id
               WHERE oi.order_id = %s""",
            (o['id'],), fetchall=True
        ) or []
        o['items'] = dish_items
        o['order_items'] = dish_items

        # Calculate preparation elapsed time in minutes
        created_time = o['created_at']
        if isinstance(created_time, str):
            try:
                created_time = datetime.strptime(created_time[:19], '%Y-%m-%d %H:%M:%S')
            except Exception:
                created_time = now
        elapsed_min = int((now - created_time).total_seconds() / 60) if created_time else 0
        o['elapsed_min'] = max(0, elapsed_min)

    return render_template('staff/dashboard.html',
                           restaurant=rest,
                           stats=stats,
                           active_orders=active_orders)


# ─────────────────────────────────────────────
# KITCHEN ORDER QUEUE
# ─────────────────────────────────────────────

@staff_bp.route('/orders')
@staff_required
def orders():
    """Filterable kitchen order queue for the assigned restaurant."""
    rest_id = session.get('restaurant_id')
    status_filter = request.args.get('status', 'active')

    rest = execute_query("SELECT * FROM restaurants WHERE id=%s", (rest_id,), fetchone=True)

    base_sql = """
        SELECT o.*, u.name AS customer_name, u.phone AS customer_phone
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.restaurant_id = %s
    """
    params = [rest_id]

    if status_filter == 'active':
        base_sql += " AND o.order_status IN ('placed', 'confirmed', 'preparing', 'ready_for_pickup')"
    elif status_filter in ('placed', 'confirmed', 'preparing', 'ready_for_pickup', 'delivered', 'cancelled'):
        base_sql += " AND o.order_status = %s"
        params.append(status_filter)

    base_sql += " ORDER BY o.created_at DESC LIMIT 50"

    all_orders = execute_query(base_sql, tuple(params), fetchall=True) or []
    for o in all_orders:
        order_dish_items = execute_query(
            "SELECT * FROM order_items WHERE order_id = %s",
            (o['id'],), fetchall=True
        ) or []
        o['items'] = order_dish_items
        o['order_items'] = order_dish_items

    return render_template('staff/orders.html',
                           restaurant=rest,
                           orders=all_orders,
                           status_filter=status_filter)


# ─────────────────────────────────────────────
# KITCHEN ORDER STATUS TRANSITION
# ─────────────────────────────────────────────

@staff_bp.route('/order/update-status', methods=['POST'])
@staff_required
def update_order_status():
    """
    Staff kitchen order status advancement:
    placed -> confirmed -> preparing -> ready_for_pickup
    Enforces strict restaurant-level data isolation.
    """
    rest_id = session.get('restaurant_id')
    order_id = request.form.get('order_id')
    new_status = request.form.get('status')

    # DATA ISOLATION: Confirm order belongs strictly to this staff member's restaurant
    order = execute_query(
        "SELECT * FROM orders WHERE id=%s AND restaurant_id=%s",
        (order_id, rest_id), fetchone=True
    )
    if not order:
        flash('Order not found or permission denied: You can only update orders for your assigned restaurant.', 'danger')
        return redirect(url_for('staff.dashboard'))

    # Permitted kitchen state transitions
    allowed_transitions = {
        'placed': ['confirmed', 'preparing', 'rejected'],
        'confirmed': ['preparing', 'ready_for_pickup', 'cancelled'],
        'preparing': ['ready_for_pickup', 'cancelled'],
        'ready_for_pickup': ['ready_for_pickup']
    }

    current_status = order['order_status']
    valid_targets = allowed_transitions.get(current_status, [])
    if new_status not in valid_targets and new_status != current_status:
        flash(f"Invalid transition from '{current_status.title()}' to '{new_status.title()}'.", 'danger')
        return redirect(request.referrer or url_for('staff.dashboard'))

    db_status = 'ready_for_pickup' if new_status in ['ready', 'ready_for_pickup'] else new_status
    execute_query("UPDATE orders SET order_status=%s, updated_at=NOW() WHERE id=%s", (db_status, order_id), commit=True)

    status_messages = {
        'confirmed': 'Order Confirmed by kitchen staff. Preparing fresh ingredients.',
        'preparing': 'Chef is cooking your order dishes now.',
        'ready_for_pickup': 'Food is packed hot and ready for delivery partner pickup.',
        'rejected': 'Kitchen is unable to prepare this order.',
    }
    if new_status in status_messages:
        try:
            execute_query(
                "INSERT INTO notifications (user_id, role, title, message) VALUES (%s, 'customer', %s, %s)",
                (order['user_id'], f"Order #{order['order_code']} Kitchen Update", status_messages[new_status]),
                commit=True
            )
        except Exception:
            pass

    # When food is ready for pickup, ensure delivery partner dispatch is initialized
    if db_status == 'ready_for_pickup':
        existing_assignment = execute_query("SELECT id FROM delivery_assignments WHERE order_id=%s", (order_id,), fetchone=True)
        if not existing_assignment:
            partner = execute_query(
                "SELECT user_id FROM delivery_partners WHERE is_online=1 ORDER BY total_deliveries ASC LIMIT 1",
                fetchone=True
            )
            if not partner:
                partner = execute_query("SELECT user_id FROM delivery_partners LIMIT 1", fetchone=True)
            if partner:
                execute_query(
                    "INSERT INTO delivery_assignments (order_id, partner_id, status, assigned_at) VALUES (%s, %s, 'assigned', NOW())",
                    (order_id, partner['user_id']), commit=True
                )
                try:
                    execute_query(
                        "INSERT INTO notifications (user_id, role, title, message) VALUES (%s, 'delivery', 'New Pickup Ready! 🛵', CONCAT('Order #', %s, ' is ready for pickup.'))",
                        (partner['user_id'], order['order_code']), commit=True
                    )
                except Exception:
                    pass

    flash(f"Order #{order['order_code']} updated to '{db_status.replace('_', ' ').title()}'.", 'success')
    return redirect(request.referrer or url_for('staff.dashboard'))


# ─────────────────────────────────────────────
# MENU INVENTORY & STOCK MANAGEMENT
# ─────────────────────────────────────────────

@staff_bp.route('/menu')
@staff_required
def menu():
    """Kitchen dish stock & availability management for the assigned restaurant."""
    rest_id = session.get('restaurant_id')
    rest = execute_query("SELECT * FROM restaurants WHERE id=%s", (rest_id,), fetchone=True)

    food_items = execute_query(
        """SELECT fi.*, fc.name AS category_name
           FROM food_items fi
           LEFT JOIN food_categories fc ON fi.category_id = fc.id
           WHERE fi.restaurant_id = %s
           ORDER BY fc.name ASC, fi.name ASC""",
        (rest_id,), fetchall=True
    ) or []

    return render_template('staff/menu.html',
                           restaurant=rest,
                           food_items=food_items)


@staff_bp.route('/menu/toggle-availability', methods=['POST'])
@staff_required
def toggle_availability():
    """Toggle dish availability (In Stock / Out of Stock)."""
    rest_id = session.get('restaurant_id')
    item_id = request.form.get('food_item_id')

    # DATA ISOLATION: Ensure item belongs strictly to staff's assigned restaurant
    item = execute_query(
        "SELECT id, name, availability, restaurant_id FROM food_items WHERE id=%s AND restaurant_id=%s",
        (item_id, rest_id), fetchone=True
    )
    if not item:
        flash('Item not found or permission denied.', 'danger')
        return redirect(url_for('staff.menu'))

    new_avail = 0 if item['availability'] == 1 else 1
    execute_query("UPDATE food_items SET availability=%s, updated_at=NOW() WHERE id=%s", (new_avail, item_id), commit=True)

    status_str = "Available" if new_avail == 1 else "Out of Stock"
    flash(f"'{item['name']}' has been marked as {status_str}.", 'success')
    return redirect(url_for('staff.menu'))


# ─────────────────────────────────────────────
# STAFF PROFILE & SHIFT INFORMATION
# ─────────────────────────────────────────────

@staff_bp.route('/profile')
@staff_required
def profile():
    """Staff member profile and shift details."""
    user = execute_query("SELECT * FROM users WHERE id=%s", (session['user_id'],), fetchone=True)
    staff_rec = execute_query(
        """SELECT s.*, r.name as restaurant_name, r.address as restaurant_address, r.phone as restaurant_phone
           FROM restaurant_staff s
           JOIN restaurants r ON s.restaurant_id = r.id
           WHERE s.user_id=%s""",
        (session['user_id'],), fetchone=True
    )
    return render_template('staff/profile.html', user=user, staff=staff_rec)
