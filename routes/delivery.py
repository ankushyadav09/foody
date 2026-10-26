"""
routes/delivery.py – Delivery partner dashboard, profile, and order management
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from database import execute_query
from utils.helpers import (delivery_required, save_uploaded_image,
                           validate_email, validate_phone, validate_password,
                           get_delivery_auth, set_delivery_auth, clear_delivery_auth)
from werkzeug.security import generate_password_hash, check_password_hash

delivery_bp = Blueprint('delivery', __name__)


# ─────────────────────────────────────────────
# DELIVERY PARTNER AUTHENTICATION
# ─────────────────────────────────────────────

@delivery_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Separate dedicated login page for delivery partners."""
    if get_delivery_auth():
        return redirect(url_for('delivery.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password   = request.form.get('password', '')
        remember   = request.form.get('remember_me')

        if not identifier or not password:
            flash('Email/Mobile and password are required.', 'danger')
            return render_template('delivery/login.html')

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
            flash('Invalid rider credentials.', 'danger')
            return render_template('delivery/login.html')

        if user['role'] not in ('delivery', 'admin'):
            flash('This portal is reserved for delivery partners. Please use Customer Login.', 'warning')
            return render_template('delivery/login.html')

        if user['status'] == 'inactive':
            flash('Your rider account has been deactivated. Please contact support.', 'warning')
            return render_template('delivery/login.html')

        session.permanent = bool(remember)
        set_delivery_auth(user)

        flash(f"Welcome back to Rider Portal, {user['name']}!", 'success')
        return redirect(url_for('delivery.dashboard'))

    return render_template('delivery/login.html')


@delivery_bp.route('/logout')
def logout():
    """Securely log out delivery partner."""
    clear_delivery_auth()
    flash("Delivery partner session ended.", "info")
    return redirect(url_for('delivery.login'))


@delivery_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Separate dedicated onboarding page for delivery partners."""
    if 'user_id' in session and session.get('role') == 'delivery':
        return redirect(url_for('delivery.dashboard'))

    if request.method == 'POST':
        name           = request.form.get('name', '').strip()
        email          = request.form.get('email', '').strip().lower()
        phone          = request.form.get('phone', '').strip()
        vehicle_type   = request.form.get('vehicle_type', 'Motorcycle').strip()
        vehicle_number = request.form.get('vehicle_number', '').strip()
        license_number = request.form.get('license_number', '').strip()
        address        = request.form.get('address', '').strip()
        city           = request.form.get('city', 'Mehsana').strip() or 'Mehsana'
        pincode        = request.form.get('pincode', '384002').strip() or '384002'
        password       = request.form.get('password', '')
        confirm        = request.form.get('confirm_password', '')

        # SECURITY: Strictly delivery role only!
        role = 'delivery'

        errors = []
        if not name:
            errors.append('Full name is required.')
        if not validate_email(email):
            errors.append('Enter a valid email address.')
        if not validate_phone(phone):
            errors.append('Enter a valid 10-digit Indian mobile number.')
        if not vehicle_number:
            errors.append('Vehicle registration number is required.')
        if not license_number:
            errors.append('Driving license number is required.')
        if not address:
            errors.append('Residential address is required.')
        if not validate_password(password):
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('delivery/register.html', form=request.form)

        existing = execute_query(
            "SELECT id, email, phone FROM users WHERE email=%s OR phone=%s", (email, phone), fetchone=True
        )
        if existing:
            if existing['email'] == email:
                flash('This email is already registered. Please login.', 'warning')
            else:
                flash('This contact number is already registered. Please login.', 'warning')
            return render_template('delivery/register.html', form=request.form)

        pw_hash = generate_password_hash(password)
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Gujarat', %s, 'active')""",
            (name, email, phone, pw_hash, role, address, city, pincode),
            commit=True
        )

        execute_query(
            """INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings)
               VALUES (%s, %s, %s, %s, 1, 1, 0, 0.00)""",
            (user_id, vehicle_type, vehicle_number, license_number),
            commit=True
        )

        flash('Delivery partner registration successful! You can now log in.', 'success')
        return redirect(url_for('delivery.login'))

    return render_template('delivery/register.html', form={})


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@delivery_bp.route('/')
@delivery_required
def index():
    return redirect(url_for('delivery.dashboard'))


@delivery_bp.route('/dashboard')
@delivery_required
def dashboard():
    partner_id = session['user_id']
    
    # Ensure partner record exists in delivery_partners
    partner = execute_query(
        "SELECT * FROM delivery_partners WHERE user_id=%s",
        (partner_id,), fetchone=True
    )
    if not partner:
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, is_online, is_available) VALUES (%s, 'Motorcycle', 'GJ-02-AB-1234', 1, 1)",
            (partner_id,), commit=True
        )
        partner = execute_query(
            "SELECT * FROM delivery_partners WHERE user_id=%s",
            (partner_id,), fetchone=True
        )

    assigned = execute_query(
        """SELECT da.*, o.order_code, o.total_amount, o.order_status,
                  u.name AS customer_name, u.phone AS customer_phone,
                  a.address AS delivery_address, r.name AS restaurant_name,
                  r.address AS restaurant_address
           FROM delivery_assignments da
           JOIN orders o ON da.order_id=o.id
           JOIN users u ON o.user_id=u.id
           LEFT JOIN addresses a ON o.address_id=a.id
           JOIN restaurants r ON o.restaurant_id=r.id
           WHERE da.partner_id=%s AND da.status NOT IN ('delivered','cancelled')
           ORDER BY da.assigned_at DESC""",
        (partner_id,), fetchall=True
    )
    stats = {
        'today_deliveries': execute_query(
            "SELECT COUNT(*) AS c FROM delivery_assignments "
            "WHERE partner_id=%s AND DATE(assigned_at)=CURDATE() AND status='delivered'",
            (partner_id,), fetchone=True)['c'],
        'total_deliveries': execute_query(
            "SELECT COUNT(*) AS c FROM delivery_assignments "
            "WHERE partner_id=%s AND status='delivered'",
            (partner_id,), fetchone=True)['c'],
        'pending': execute_query(
            "SELECT COUNT(*) AS c FROM delivery_assignments "
            "WHERE partner_id=%s AND status='assigned'",
            (partner_id,), fetchone=True)['c'],
        'earnings': execute_query(
            """SELECT COALESCE(SUM(o.delivery_fee),0) AS e
               FROM delivery_assignments da JOIN orders o ON da.order_id=o.id
               WHERE da.partner_id=%s AND da.status='delivered'""",
            (partner_id,), fetchone=True)['e'],
    }
    return render_template('delivery/dashboard.html',
                           assigned=assigned, stats=stats, partner=partner)


# ─────────────────────────────────────────────
# PROFILE (VIEW & EDIT PERSISTENCE)
# ─────────────────────────────────────────────

@delivery_bp.route('/profile')
@delivery_required
def profile():
    user_id = session['user_id']
    user = execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetchone=True)
    partner = execute_query("SELECT * FROM delivery_partners WHERE user_id=%s", (user_id,), fetchone=True)
    if not partner:
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, is_online, is_available) VALUES (%s, 'Motorcycle', 'GJ-02-AB-1234', 1, 1)",
            (user_id,), commit=True
        )
        partner = execute_query("SELECT * FROM delivery_partners WHERE user_id=%s", (user_id,), fetchone=True)

    return render_template('delivery/profile.html', user=user, partner=partner)


@delivery_bp.route('/profile/update', methods=['POST'])
@delivery_required
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

    vehicle_type = request.form.get('vehicle_type', '').strip() or 'Motorcycle'
    vehicle_number = request.form.get('vehicle_number', '').strip()
    license_number = request.form.get('license_number', '').strip()

    if not name or not phone:
        flash('Name and phone number are required.', 'danger')
        return redirect(url_for('delivery.profile'))

    # Update users table
    execute_query(
        """UPDATE users 
           SET name=%s, phone=%s, gender=%s, dob=%s, address=%s,
               city=%s, state=%s, pincode=%s, updated_at=NOW()
           WHERE id=%s""",
        (name, phone, gender, dob, address, city, state, pincode, user_id),
        commit=True
    )

    # Handle image upload if provided
    pic_file = request.files.get('profile_pic')
    if pic_file and pic_file.filename:
        pic_url = save_uploaded_image(pic_file, 'users')
        if pic_url:
            execute_query("UPDATE users SET profile_pic=%s WHERE id=%s", (pic_url, user_id), commit=True)

    # Update or insert delivery_partners
    existing_partner = execute_query("SELECT id FROM delivery_partners WHERE user_id=%s", (user_id,), fetchone=True)
    if existing_partner:
        execute_query(
            """UPDATE delivery_partners
               SET vehicle_type=%s, vehicle_number=%s, license_number=%s, updated_at=NOW()
               WHERE user_id=%s""",
            (vehicle_type, vehicle_number, license_number, user_id),
            commit=True
        )
    else:
        execute_query(
            """INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number)
               VALUES (%s, %s, %s, %s)""",
            (user_id, vehicle_type, vehicle_number, license_number),
            commit=True
        )

    session['user_name'] = name
    flash('Delivery partner profile updated successfully!', 'success')
    return redirect(url_for('delivery.profile'))


@delivery_bp.route('/toggle-online', methods=['POST'])
@delivery_required
def toggle_online():
    user_id = session['user_id']
    partner = execute_query("SELECT is_online FROM delivery_partners WHERE user_id=%s", (user_id,), fetchone=True)
    if not partner:
        execute_query("INSERT INTO delivery_partners (user_id, is_online) VALUES (%s, 1)", (user_id,), commit=True)
        new_status = 1
    else:
        new_status = 0 if partner['is_online'] else 1
        execute_query("UPDATE delivery_partners SET is_online=%s, updated_at=NOW() WHERE user_id=%s",
                      (new_status, user_id), commit=True)

    msg = "You are now ONLINE and ready to receive deliveries!" if new_status else "You are now OFFLINE. No new orders will be assigned."
    flash(msg, 'success' if new_status else 'info')
    return redirect(request.referrer or url_for('delivery.dashboard'))


# ─────────────────────────────────────────────
# ORDER DETAIL
# ─────────────────────────────────────────────

@delivery_bp.route('/order/<int:order_id>')
@delivery_required
def order_detail(order_id):
    assignment = execute_query(
        "SELECT * FROM delivery_assignments WHERE (order_id=%s OR id=%s) AND partner_id=%s",
        (order_id, order_id, session['user_id']), fetchone=True
    )
    if not assignment:
        flash('Order not found or not assigned to you.', 'danger')
        return redirect(url_for('delivery.dashboard'))

    real_order_id = assignment['order_id']

    order = execute_query(
        """SELECT o.*, u.name AS customer_name, u.phone AS customer_phone,
                  a.address AS delivery_address, r.name AS restaurant_name,
                  r.address AS restaurant_address, r.phone AS restaurant_phone
           FROM orders o JOIN users u ON o.user_id=u.id
           LEFT JOIN addresses a ON o.address_id=a.id
           JOIN restaurants r ON o.restaurant_id=r.id
           WHERE o.id=%s""",
        (real_order_id,), fetchone=True
    )
    items = execute_query(
        """SELECT oi.*, fi.name, fi.veg_type
           FROM order_items oi JOIN food_items fi ON oi.food_item_id=fi.id
           WHERE oi.order_id=%s""",
        (real_order_id,), fetchall=True
    )
    return render_template('delivery/order_detail.html',
                           order=order, items=items, assignment=assignment)


# ─────────────────────────────────────────────
# UPDATE DELIVERY STATUS & LIFECYCLE
# ─────────────────────────────────────────────

@delivery_bp.route('/order/pickup/<int:assignment_id>', methods=['POST'])
@delivery_required
def pickup_order(assignment_id):
    assignment = execute_query(
        "SELECT * FROM delivery_assignments WHERE id=%s AND partner_id=%s",
        (assignment_id, session['user_id']), fetchone=True
    )
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('delivery.dashboard'))

    order_id = assignment['order_id']
    execute_query("UPDATE delivery_assignments SET status='picked_up', picked_at=NOW() WHERE id=%s", (assignment_id,), commit=True)
    execute_query("UPDATE orders SET order_status='out_for_delivery', updated_at=NOW() WHERE id=%s", (order_id,), commit=True)
    
    # Notify customer
    try:
        execute_query(
            """INSERT INTO notifications (user_id, role, title, message)
               SELECT user_id, 'customer', 'Food Picked Up! 🛵', CONCAT('Your order #', order_code, ' is picked up and headed your way.')
               FROM orders WHERE id=%s""",
            (order_id,), commit=True
        )
    except Exception:
        pass

    flash('Order picked up from kitchen! Delivery in progress.', 'success')
    return redirect(url_for('delivery.dashboard'))


@delivery_bp.route('/order/out-for-delivery/<int:assignment_id>', methods=['POST'])
@delivery_required
def out_for_delivery_order(assignment_id):
    assignment = execute_query(
        "SELECT * FROM delivery_assignments WHERE id=%s AND partner_id=%s",
        (assignment_id, session['user_id']), fetchone=True
    )
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('delivery.dashboard'))

    order_id = assignment['order_id']
    execute_query("UPDATE delivery_assignments SET status='out_for_delivery' WHERE id=%s", (assignment_id,), commit=True)
    execute_query("UPDATE orders SET order_status='out_for_delivery', updated_at=NOW() WHERE id=%s", (order_id,), commit=True)

    flash('Order status updated to Out for Delivery!', 'success')
    return redirect(url_for('delivery.dashboard'))


@delivery_bp.route('/order/delivered/<int:assignment_id>', methods=['POST'])
@delivery_required
def deliver_order(assignment_id):
    assignment = execute_query(
        "SELECT * FROM delivery_assignments WHERE id=%s AND partner_id=%s",
        (assignment_id, session['user_id']), fetchone=True
    )
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('delivery.dashboard'))

    order_id = assignment['order_id']
    partner_id = session['user_id']
    
    execute_query("UPDATE delivery_assignments SET status='delivered', delivered_at=NOW() WHERE id=%s", (assignment_id,), commit=True)
    execute_query("UPDATE orders SET order_status='delivered', updated_at=NOW() WHERE id=%s", (order_id,), commit=True)

    # Update delivery partner lifetime deliveries and earnings
    execute_query(
        """UPDATE delivery_partners
           SET total_deliveries = total_deliveries + 1,
               total_earnings = total_earnings + (SELECT COALESCE(delivery_fee, 40.00) FROM orders WHERE id=%s),
               updated_at = NOW()
           WHERE user_id=%s""",
        (order_id, partner_id), commit=True
    )

    # Notify customer
    try:
        execute_query(
            """INSERT INTO notifications (user_id, role, title, message)
               SELECT user_id, 'customer', 'Order Delivered! 🎉', CONCAT('Your order #', order_code, ' has arrived. Enjoy your meal!')
               FROM orders WHERE id=%s""",
            (order_id,), commit=True
        )
    except Exception:
        pass

    flash('Order marked as Delivered! Earnings have been credited.', 'success')
    return redirect(url_for('delivery.dashboard'))


@delivery_bp.route('/order/<int:order_id>/status', methods=['POST'])
@delivery_required
def update_status(order_id):
    new_status = request.form.get('status')
    allowed = ['accepted', 'picked_up', 'out_for_delivery', 'delivered']
    if new_status not in allowed:
        flash('Invalid status.', 'danger')
        return redirect(url_for('delivery.order_detail', order_id=order_id))

    order_status_map = {
        'accepted':          'confirmed',
        'picked_up':         'out_for_delivery',
        'out_for_delivery':  'out_for_delivery',
        'delivered':         'delivered',
    }

    execute_query(
        "UPDATE delivery_assignments SET status=%s WHERE order_id=%s AND partner_id=%s",
        (new_status, order_id, session['user_id']), commit=True
    )
    execute_query(
        "UPDATE orders SET order_status=%s, updated_at=NOW() WHERE id=%s",
        (order_status_map[new_status], order_id), commit=True
    )
    if new_status == 'delivered':
        execute_query(
            "UPDATE delivery_assignments SET delivered_at=NOW() WHERE order_id=%s",
            (order_id,), commit=True
        )
        execute_query(
            """UPDATE delivery_partners
               SET total_deliveries = total_deliveries + 1,
                   total_earnings = total_earnings + (SELECT COALESCE(delivery_fee, 40.00) FROM orders WHERE id=%s),
                   updated_at = NOW()
               WHERE user_id=%s""",
            (order_id, session['user_id']), commit=True
        )
    flash(f"Status updated to '{new_status}'!", 'success')
    return redirect(url_for('delivery.dashboard'))


# ─────────────────────────────────────────────
# HISTORY & EARNINGS
# ─────────────────────────────────────────────

@delivery_bp.route('/history')
@delivery_required
def history():
    completed = execute_query(
        """SELECT da.*, o.order_code, o.total_amount, o.delivery_fee,
                  u.name AS customer_name, r.name AS restaurant_name,
                  a.address AS delivery_address
           FROM delivery_assignments da
           JOIN orders o ON da.order_id=o.id
           JOIN users u ON o.user_id=u.id
           JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN addresses a ON o.address_id=a.id
           WHERE da.partner_id=%s AND da.status='delivered'
           ORDER BY da.delivered_at DESC""",
        (session['user_id'],), fetchall=True
    )
    total_earnings = sum(float(d['delivery_fee'] or 0) for d in completed)
    return render_template('delivery/history.html',
                           completed=completed, total_earnings=total_earnings)

