"""
routes/customer.py – Customer-facing routes (cart, checkout, orders, profile)
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from database import execute_query
from utils.helpers import (customer_required, calculate_order_totals,
                           generate_order_id, generate_transaction_id,
                           validate_phone, save_uploaded_image,
                           validate_and_calculate_coupon)
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

customer_bp = Blueprint('customer', __name__)


# ─────────────────────────────────────────────
# CART PAGE
# ─────────────────────────────────────────────

@customer_bp.route('/cart')
@customer_required
def cart():
    """Display shopping cart."""
    cart_record = execute_query(
        "SELECT * FROM cart WHERE user_id=%s AND status='active'",
        (session['user_id'],), fetchone=True
    )
    items = []
    subtotal = 0
    restaurant = None
    if cart_record:
        items = execute_query(
            """SELECT ci.id, ci.quantity, ci.price, fi.name, fi.image,
                      fi.veg_type, fi.description, fi.id AS food_id,
                      r.name AS restaurant_name, r.id AS restaurant_id,
                      r.delivery_fee, r.min_order
               FROM cart_items ci
               JOIN food_items fi ON ci.food_item_id=fi.id
               JOIN restaurants r ON fi.restaurant_id=r.id
               WHERE ci.cart_id=%s""",
            (cart_record['id'],), fetchall=True
        )
        subtotal = sum(float(i['price']) * i['quantity'] for i in items)
        if items:
            restaurant = {'name': items[0]['restaurant_name'],
                          'id':   items[0]['restaurant_id'],
                          'delivery_fee': items[0]['delivery_fee']}
    delivery_fee = float(restaurant['delivery_fee']) if restaurant else Config.DEFAULT_DELIVERY_FEE
    totals = calculate_order_totals(subtotal, delivery_fee)
    return render_template('cart.html', items=items, totals=totals,
                           restaurant=restaurant, cart=cart_record)


# ─────────────────────────────────────────────
# CHECKOUT
# ─────────────────────────────────────────────

@customer_bp.route('/checkout', methods=['GET', 'POST'])
@customer_required
def checkout():
    """Checkout: address, coupon, payment selection."""
    cart_record = execute_query(
        "SELECT * FROM cart WHERE user_id=%s AND status='active'",
        (session['user_id'],), fetchone=True
    )
    if not cart_record:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('customer.cart'))

    items = execute_query(
        """SELECT ci.*, fi.name, fi.image, fi.veg_type,
                  r.name AS restaurant_name, r.id AS restaurant_id,
                  r.delivery_fee, r.min_order
           FROM cart_items ci
           JOIN food_items fi ON ci.food_item_id=fi.id
           JOIN restaurants r ON fi.restaurant_id=r.id
           WHERE ci.cart_id=%s""",
        (cart_record['id'],), fetchall=True
    )
    if not items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('customer.cart'))

    subtotal     = sum(float(i['price']) * i['quantity'] for i in items)
    delivery_fee = float(items[0]['delivery_fee'])
    restaurant_id= items[0]['restaurant_id']
    totals       = calculate_order_totals(subtotal, delivery_fee)

    # Saved addresses
    addresses = execute_query(
        "SELECT * FROM addresses WHERE user_id=%s ORDER BY is_default DESC",
        (session['user_id'],), fetchall=True
    )
    user = execute_query(
        "SELECT * FROM users WHERE id=%s", (session['user_id'],), fetchone=True
    )

    if request.method == 'POST':
        payment_method  = request.form.get('payment_method', 'cod')
        raw_coupon_code = (request.form.get('coupon_code') or request.form.get('coupon_code_input') or '').strip().upper()
        raw_coupon_id   = request.form.get('coupon_id', '').strip()
        client_discount = float(request.form.get('discount', 0) or 0)
        address_id      = request.form.get('address_id')
        new_address     = request.form.get('new_address', '').strip()

        # Handle new address
        if not address_id and new_address:
            address_id = execute_query(
                "INSERT INTO addresses (user_id, address, is_default) VALUES (%s,%s,0)",
                (session['user_id'], new_address), commit=True
            )

        if not address_id:
            flash('Please select or enter a delivery address.', 'danger')
            return render_template('checkout.html', items=items, totals=totals,
                                   addresses=addresses, user=user)

        # Robust server-side coupon validation
        validated_coupon_id = None
        validated_discount  = 0.0

        has_coupon = bool((raw_coupon_id not in ('', '0', 'null', 'None')) or raw_coupon_code)
        if has_coupon:
            is_valid, msg, coupon_rec, calc_discount = validate_and_calculate_coupon(
                coupon_id=raw_coupon_id,
                coupon_code=raw_coupon_code,
                subtotal=subtotal
            )
            if not is_valid:
                flash(f"Coupon error: {msg}", 'danger')
                return render_template('checkout.html', items=items, totals=totals,
                                       addresses=addresses, user=user)

            # Prevent silently charging or recording a different total than customer was shown
            if client_discount > 0 and abs(calc_discount - client_discount) > 0.05:
                flash(f"Order total updated: recalculated coupon discount is ₹{calc_discount:.2f} (was ₹{client_discount:.2f}). Please review and place order.", 'warning')
                totals = calculate_order_totals(subtotal, delivery_fee, calc_discount)
                return render_template('checkout.html', items=items, totals=totals,
                                       addresses=addresses, user=user)

            validated_coupon_id = int(coupon_rec['id'])
            validated_discount  = calc_discount

        totals = calculate_order_totals(subtotal, delivery_fee, validated_discount)
        order_data = {
            'cart_id':       cart_record['id'],
            'restaurant_id': restaurant_id,
            'address_id':    address_id,
            'totals':        totals,
            'coupon_id':     validated_coupon_id,
        }
        session['pending_order'] = order_data

        if payment_method == 'cod':
            # Create order immediately
            from routes.api import _create_order_in_db
            try:
                db_order_id = _create_order_in_db(order_data, 'cod', 'pending')
                session.pop('pending_order', None)
                flash('Order placed successfully!', 'success')
                return redirect(url_for('customer.order_success', order_id=db_order_id))
            except Exception as e:
                flash(f"Order placement failed: {str(e)}", 'danger')
                return redirect(url_for('customer.checkout'))
        else:
            # Redirect to payment page
            session['pending_order']['payment_method'] = payment_method
            return redirect(url_for('customer.payment'))

    razorpay_key = getattr(Config, 'RAZORPAY_KEY_ID', '') or ''
    razorpay_enabled = bool(razorpay_key and getattr(Config, 'RAZORPAY_KEY_SECRET', ''))
    return render_template('checkout.html', items=items, totals=totals,
                           addresses=addresses, user=user,
                           razorpay_key=razorpay_key,
                           razorpay_enabled=razorpay_enabled)


# ─────────────────────────────────────────────
# PAYMENT PAGE
# ─────────────────────────────────────────────

@customer_bp.route('/payment', methods=['GET', 'POST'])
@customer_required
def payment():
    """Payment page for non-COD methods."""
    order_data = session.get('pending_order')
    if not order_data:
        flash('No pending order found. Please checkout again.', 'warning')
        return redirect(url_for('customer.cart'))

    razorpay_key = getattr(Config, 'RAZORPAY_KEY_ID', '') or ''
    razorpay_enabled = bool(razorpay_key and getattr(Config, 'RAZORPAY_KEY_SECRET', ''))
    return render_template('payment.html',
                           order_data=order_data,
                           razorpay_key=razorpay_key,
                           razorpay_enabled=razorpay_enabled)


@customer_bp.route('/payment/cod-confirm', methods=['POST'])
@customer_required
def payment_cod():
    """Process COD payment."""
    order_data = session.get('pending_order')
    if not order_data:
        flash('No pending order found. Please checkout again.', 'warning')
        return redirect(url_for('customer.cart'))
    from routes.api import _create_order_in_db
    try:
        db_order_id = _create_order_in_db(order_data, 'cod', 'pending')
        session.pop('pending_order', None)
        flash('Order placed successfully!', 'success')
        return redirect(url_for('customer.order_success', order_id=db_order_id))
    except Exception as e:
        flash(f"Order placement failed: {str(e)}", 'danger')
        return redirect(url_for('customer.checkout'))


@customer_bp.route('/payment/demo-confirm', methods=['POST'])
@customer_required
def payment_demo_confirm():
    """Process demo online payment (card/UPI/netbanking)."""
    order_data = session.get('pending_order')
    if not order_data:
        flash('No pending order found.', 'warning')
        return redirect(url_for('customer.cart'))
    payment_method = request.form.get('payment_method', 'demo_upi')
    from routes.api import _create_order_in_db
    from utils.helpers import generate_transaction_id
    txn_id = generate_transaction_id()
    try:
        db_order_id = _create_order_in_db(order_data, payment_method, 'paid', txn_id)
        session.pop('pending_order', None)
        flash('Payment successful! Your order has been placed.', 'success')
        return redirect(url_for('customer.order_success', order_id=db_order_id))
    except Exception as e:
        flash(f"Payment processing failed: {str(e)}", 'danger')
        return redirect(url_for('customer.checkout'))


# ─────────────────────────────────────────────
# ORDER SUCCESS
# ─────────────────────────────────────────────

@customer_bp.route('/order/success/<int:order_id>')
@customer_required
def order_success(order_id):
    """Order confirmation page."""
    order = execute_query(
        """SELECT o.*, r.name AS restaurant_name, a.address AS delivery_address,
                  p.transaction_id
           FROM orders o
           JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN addresses a ON o.address_id=a.id
           LEFT JOIN payments p ON p.order_id=o.id
           WHERE o.id=%s AND o.user_id=%s""",
        (order_id, session['user_id']), fetchone=True
    )
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('main.index'))

    items = execute_query(
        """SELECT oi.*, fi.name, fi.image, fi.veg_type
           FROM order_items oi JOIN food_items fi ON oi.food_item_id=fi.id
           WHERE oi.order_id=%s""",
        (order_id,), fetchall=True
    )
    return render_template('order_success.html', order=order, items=items)


# ─────────────────────────────────────────────
# ORDER TRACKING
# ─────────────────────────────────────────────

@customer_bp.route('/order/track/<int:order_id>')
@customer_bp.route('/order-tracking/<int:order_id>')
@customer_bp.route('/track/<int:order_id>')
@customer_required
def track_order(order_id):
    """Order tracking page with live Google Maps and status timeline."""
    order = execute_query(
        """SELECT o.*,
                  COALESCE(r.name, 'Restaurant Kitchen') AS restaurant_name,
                  COALESCE(r.phone, '+91 98250 12345') AS restaurant_phone,
                  COALESCE(r.address, 'Restaurant Kitchen') AS restaurant_address,
                  COALESCE(r.latitude, 23.5880) AS restaurant_lat,
                  COALESCE(r.longitude, 72.3693) AS restaurant_lng,
                  COALESCE(a.address, o.delivery_address, 'Customer Delivery Address') AS delivery_address,
                  COALESCE(o.customer_lat, a.latitude, 23.5880) AS customer_lat,
                  COALESCE(o.customer_lng, a.longitude, 72.3693) AS customer_lng,
                  da.partner_id, da.status AS assignment_status,
                  dp.name AS partner_name, dp.phone AS partner_phone,
                  dpart.vehicle_type, dpart.vehicle_number,
                  dpart.current_lat AS partner_lat, dpart.current_lng AS partner_lng
           FROM orders o
           LEFT JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN addresses a ON o.address_id=a.id
           LEFT JOIN delivery_assignments da ON da.order_id=o.id AND da.status != 'cancelled'
           LEFT JOIN users dp ON da.partner_id=dp.id
           LEFT JOIN delivery_partners dpart ON da.partner_id=dpart.user_id
           WHERE o.id=%s""",
        (order_id,), fetchone=True
    )
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('customer.orders')), 404

    current_uid = session.get('user_id') or (session.get('customer_auth') or {}).get('user_id')
    current_role = session.get('role') or (session.get('customer_auth') or {}).get('role')
    if order['user_id'] != current_uid and current_role not in ('admin',):
        flash("Unauthorized: You cannot access another customer's order tracking.", 'danger')
        return redirect(url_for('customer.orders')), 403

    statuses = ['placed', 'confirmed', 'preparing', 'ready_for_pickup', 'assigned', 'out_for_delivery', 'delivered']
    raw_status = (order.get('order_status') or 'placed').lower()
    normalized_status = 'ready_for_pickup' if raw_status == 'ready' else raw_status
    delivery_stage = (order.get('assignment_status') or '').lower()
    has_rider = bool(order.get('partner_name') or order.get('partner_id'))

    if normalized_status == 'delivered' or delivery_stage == 'delivered':
        current_index = 6
    elif normalized_status in ('out_for_delivery', 'picked_up') or delivery_stage in ('picked_up', 'out_for_delivery'):
        current_index = 5
    elif normalized_status == 'assigned' or has_rider or delivery_stage == 'assigned':
        current_index = 4
    elif normalized_status in ('ready_for_pickup', 'ready'):
        current_index = 3
    elif normalized_status == 'preparing':
        current_index = 2
    elif normalized_status == 'confirmed':
        current_index = 1
    elif normalized_status == 'placed':
        current_index = 0
    else:
        current_index = 0

    milestones = {
        'placed': True,
        'confirmed': current_index >= 1 or normalized_status in ('confirmed', 'preparing', 'ready_for_pickup', 'ready', 'assigned', 'out_for_delivery', 'delivered') or has_rider,
        'preparing': current_index >= 2 or normalized_status in ('preparing', 'ready_for_pickup', 'ready', 'assigned', 'out_for_delivery', 'delivered'),
        'ready_for_pickup': current_index >= 3 or normalized_status in ('ready_for_pickup', 'ready', 'assigned', 'out_for_delivery', 'delivered'),
        'assigned': current_index >= 4 or has_rider or delivery_stage in ('assigned', 'picked_up', 'out_for_delivery', 'delivered') or normalized_status in ('assigned', 'out_for_delivery', 'delivered'),
        'out_for_delivery': current_index >= 5 or normalized_status in ('out_for_delivery', 'delivered') or delivery_stage in ('picked_up', 'out_for_delivery', 'delivered'),
        'delivered': current_index == 6 or normalized_status == 'delivered' or delivery_stage == 'delivered'
    }

    return render_template('track_order.html', order=order,
                           statuses=statuses, current_index=current_index,
                           milestones=milestones,
                           google_maps_api_key=Config.GOOGLE_MAPS_API_KEY)


# ─────────────────────────────────────────────
# ORDER HISTORY
# ─────────────────────────────────────────────

@customer_bp.route('/orders')
@customer_required
def orders():
    """Order history page."""
    all_orders = execute_query(
        """SELECT o.*, r.name AS restaurant_name
           FROM orders o JOIN restaurants r ON o.restaurant_id=r.id
           WHERE o.user_id=%s ORDER BY o.created_at DESC""",
        (session['user_id'],), fetchall=True
    )
    return render_template('orders.html', orders=all_orders)


@customer_bp.route('/order/<int:order_id>')
@customer_required
def order_detail(order_id):
    """Order detail page."""
    order = execute_query(
        """SELECT o.*, r.name AS restaurant_name, a.address AS delivery_address,
                  p.transaction_id, p.payment_status AS pay_status
           FROM orders o
           JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN addresses a ON o.address_id=a.id
           LEFT JOIN payments p ON p.order_id=o.id
           WHERE o.id=%s AND o.user_id=%s""",
        (order_id, session['user_id']), fetchone=True
    )
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('customer.orders'))
    items = execute_query(
        """SELECT oi.*, fi.name, fi.image, fi.veg_type
           FROM order_items oi JOIN food_items fi ON oi.food_item_id=fi.id
           WHERE oi.order_id=%s""",
        (order_id,), fetchall=True
    )
    return render_template('order_detail.html', order=order, items=items)


# ─────────────────────────────────────────────
# PROFILE (View, Edit, Save, Cancel - Fully Persisted in MySQL)
# ─────────────────────────────────────────────

@customer_bp.route('/profile', methods=['GET', 'POST'])
@customer_required
def profile():
    """Customer profile page."""
    user_id = session['user_id']
    if request.method == 'POST':
        return _handle_profile_update(user_id)

    user = execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetchone=True)
    addresses = execute_query(
        "SELECT * FROM addresses WHERE user_id=%s ORDER BY is_default DESC, id DESC",
        (user_id,), fetchall=True
    )
    return render_template('profile.html', user=user, addresses=addresses)


@customer_bp.route('/profile/update', methods=['POST'])
@customer_required
def profile_update():
    """Explicit endpoint for profile update matching template action."""
    return _handle_profile_update(session['user_id'])


def _handle_profile_update(user_id):
    """Processes profile update and persists to MySQL."""
    name    = request.form.get('name', '').strip()
    phone   = request.form.get('phone', '').strip()
    gender  = request.form.get('gender', '').strip().lower()
    dob     = request.form.get('dob', '').strip() or None
    address = request.form.get('address', '').strip()
    city    = request.form.get('city', 'Mehsana').strip()
    state   = request.form.get('state', 'Gujarat').strip()
    pincode = request.form.get('pincode', '384002').strip()

    if not name:
        flash('Full name cannot be empty.', 'danger')
        return redirect(url_for('customer.profile'))
    if not validate_phone(phone):
        flash('Please enter a valid 10-digit mobile number.', 'danger')
        return redirect(url_for('customer.profile'))
    if gender not in ('male', 'female', 'other'):
        gender = None

    # Handle profile image upload if present
    profile_pic = None
    if 'profile_pic' in request.files:
        uploaded = request.files['profile_pic']
        if uploaded and uploaded.filename:
            profile_pic = save_uploaded_image(uploaded)

    if profile_pic:
        execute_query(
            """UPDATE users SET name=%s, phone=%s, gender=%s, dob=%s, address=%s,
                                city=%s, state=%s, pincode=%s, profile_pic=%s, updated_at=NOW()
               WHERE id=%s""",
            (name, phone, gender, dob, address, city, state, pincode, profile_pic, user_id),
            commit=True
        )
    else:
        execute_query(
            """UPDATE users SET name=%s, phone=%s, gender=%s, dob=%s, address=%s,
                                city=%s, state=%s, pincode=%s, updated_at=NOW()
               WHERE id=%s""",
            (name, phone, gender, dob, address, city, state, pincode, user_id),
            commit=True
        )

    session['user_name'] = name
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('customer.profile'))


@customer_bp.route('/profile/change-password', methods=['POST'])
@customer_required
def change_password():
    """Change password form handler."""
    current = request.form.get('current_password', '')
    new_pw  = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    user = execute_query("SELECT * FROM users WHERE id=%s",
                         (session['user_id'],), fetchone=True)
    if not check_password_hash(user['password_hash'], current):
        flash('Current password is incorrect.', 'danger')
    elif len(new_pw) < 6:
        flash('New password must be at least 6 characters.', 'danger')
    elif new_pw != confirm:
        flash('Passwords do not match.', 'danger')
    else:
        execute_query(
            "UPDATE users SET password_hash=%s, updated_at=NOW() WHERE id=%s",
            (generate_password_hash(new_pw), session['user_id']), commit=True
        )
        flash('Password changed successfully!', 'success')
    return redirect(url_for('customer.profile'))


# ─────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────

@customer_bp.route('/review/<int:order_id>', methods=['GET', 'POST'])
@customer_required
def review(order_id):
    """Submit review for a delivered order."""
    order = execute_query(
        "SELECT * FROM orders WHERE id=%s AND user_id=%s AND order_status='delivered'",
        (order_id, session['user_id']), fetchone=True
    )
    if not order:
        flash('You can only review delivered orders.', 'warning')
        return redirect(url_for('customer.orders'))

    existing = execute_query(
        "SELECT id FROM reviews WHERE order_id=%s AND user_id=%s",
        (order_id, session['user_id']), fetchone=True
    )
    if existing:
        flash('You have already reviewed this order.', 'info')
        return redirect(url_for('customer.orders'))

    if request.method == 'POST':
        try:
            rating = int(request.form.get('rating', 5))
            if rating < 1 or rating > 5:
                rating = 5
        except (ValueError, TypeError):
            rating = 5
        comment = request.form.get('comment', '').strip()
        execute_query(
            """INSERT INTO reviews (user_id, restaurant_id, order_id, rating, comment)
               VALUES (%s,%s,%s,%s,%s)""",
            (session['user_id'], order['restaurant_id'], order_id, rating, comment),
            commit=True
        )
        # Recalculate restaurant average rating
        execute_query(
            """UPDATE restaurants SET rating = (
               SELECT ROUND(AVG(rating), 2) FROM reviews WHERE restaurant_id=%s
            ), total_ratings = (
               SELECT COUNT(*) FROM reviews WHERE restaurant_id=%s
            ) WHERE id=%s""",
            (order['restaurant_id'], order['restaurant_id'], order['restaurant_id']), commit=True
        )
        flash('Thank you for your rating and review!', 'success')
        return redirect(url_for('customer.orders'))

    restaurant = execute_query(
        "SELECT * FROM restaurants WHERE id=%s", (order['restaurant_id'],), fetchone=True
    )
    return render_template('review.html', order=order, restaurant=restaurant)


# ─────────────────────────────────────────────
# ADDRESS MANAGEMENT
# ─────────────────────────────────────────────

@customer_bp.route('/address/add', methods=['POST'])
@customer_required
def add_address():
    """Add a new saved address with coordinates."""
    label     = request.form.get('label', 'Home').strip()
    address   = request.form.get('address', '').strip()
    area      = request.form.get('area', 'Mehsana City').strip()
    city      = request.form.get('city', 'Mehsana').strip()
    state     = request.form.get('state', 'Gujarat').strip()
    pincode   = request.form.get('pincode', '384002').strip()
    try:
        lat = float(request.form.get('latitude', 23.5880))
        lng = float(request.form.get('longitude', 72.3693))
    except (ValueError, TypeError):
        lat, lng = 23.5880, 72.3693
    is_default = 1 if request.form.get('is_default') else 0

    if not address:
        flash('Address field cannot be empty.', 'danger')
        return redirect(url_for('customer.profile'))

    if is_default:
        execute_query("UPDATE addresses SET is_default=0 WHERE user_id=%s", (session['user_id'],), commit=True)

    execute_query(
        """INSERT INTO addresses (user_id, label, address, area, city, state, pincode, latitude, longitude, is_default)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (session['user_id'], label, address, area, city, state, pincode, lat, lng, is_default),
        commit=True
    )
    flash(f'{label} address saved successfully!', 'success')
    return redirect(url_for('customer.profile'))


@customer_bp.route('/address/delete/<int:addr_id>', methods=['POST', 'GET'])
@customer_required
def delete_address(addr_id):
    """Delete a customer address."""
    execute_query("DELETE FROM addresses WHERE id=%s AND user_id=%s", (addr_id, session['user_id']), commit=True)
    flash('Address removed.', 'info')
    return redirect(url_for('customer.profile'))


@customer_bp.route('/address/set-default/<int:addr_id>', methods=['POST', 'GET'])
@customer_required
def set_default_address(addr_id):
    """Mark an address as default."""
    execute_query("UPDATE addresses SET is_default=0 WHERE user_id=%s", (session['user_id'],), commit=True)
    execute_query("UPDATE addresses SET is_default=1 WHERE id=%s AND user_id=%s", (addr_id, session['user_id']), commit=True)
    flash('Default address updated!', 'success')
    return redirect(url_for('customer.profile'))


# ─────────────────────────────────────────────
# FAVORITES / WISHLIST
# ─────────────────────────────────────────────

@customer_bp.route('/favorites')
@customer_required
def favorites():
    """Customer favorites page for saved restaurants and foods."""
    user_id = session['user_id']
    fav_restaurants = execute_query(
        """SELECT r.* FROM restaurants r
           JOIN favorites f ON f.item_id=r.id AND f.item_type='restaurant'
           WHERE f.user_id=%s""",
        (user_id,), fetchall=True
    )
    fav_foods = execute_query(
        """SELECT fi.*, r.name AS restaurant_name FROM food_items fi
           JOIN restaurants r ON fi.restaurant_id=r.id
           JOIN favorites f ON f.item_id=fi.id AND f.item_type='food'
           WHERE f.user_id=%s""",
        (user_id,), fetchall=True
    )
    return render_template('customer/favorites.html',
                           restaurants=fav_restaurants, foods=fav_foods)


@customer_bp.route('/favorite/toggle', methods=['POST'])
@customer_required
def toggle_favorite():
    """Toggle favorite status via AJAX or form POST."""
    data = request.get_json() or request.form
    item_type = data.get('item_type')
    item_id   = data.get('item_id')

    if item_type not in ('restaurant', 'food') or not item_id:
        return jsonify({'success': False, 'message': 'Invalid parameters'}), 400

    existing = execute_query(
        "SELECT id FROM favorites WHERE user_id=%s AND item_type=%s AND item_id=%s",
        (session['user_id'], item_type, item_id), fetchone=True
    )
    if existing:
        execute_query("DELETE FROM favorites WHERE id=%s", (existing['id'],), commit=True)
        return jsonify({'success': True, 'favorited': False, 'message': 'Removed from favorites'})
    else:
        execute_query(
            "INSERT INTO favorites (user_id, item_type, item_id) VALUES (%s, %s, %s)",
            (session['user_id'], item_type, item_id), commit=True
        )
        return jsonify({'success': True, 'favorited': True, 'message': 'Added to favorites!'})


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

@customer_bp.route('/notifications')
@customer_required
def notifications():
    """Customer in-app notification center."""
    notifs = execute_query(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
        (session['user_id'],), fetchall=True
    )
    # Mark as read
    execute_query("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session['user_id'],), commit=True)
    return render_template('customer/notifications.html', notifications=notifs)


# ─────────────────────────────────────────────
# REVIEW & RATING
# ─────────────────────────────────────────────

@customer_bp.route('/order/review/<int:order_id>', methods=['GET', 'POST'])
@customer_required
def order_review(order_id):
    """Customer rating and review for completed order."""
    user_id = session['user_id']
    order = execute_query(
        """SELECT o.*, r.name AS restaurant_name
           FROM orders o JOIN restaurants r ON o.restaurant_id=r.id
           WHERE o.id=%s AND o.user_id=%s""",
        (order_id, user_id), fetchone=True
    )
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('customer.orders'))

    restaurant = execute_query("SELECT * FROM restaurants WHERE id=%s", (order['restaurant_id'],), fetchone=True)

    if request.method == 'POST':
        try:
            rating = int(request.form.get('rating', 5))
            rating = max(1, min(5, rating))
        except (ValueError, TypeError):
            rating = 5
        comment = request.form.get('comment', '').strip()

        # Check existing review
        existing = execute_query(
            "SELECT id FROM reviews WHERE order_id=%s AND user_id=%s",
            (order_id, user_id), fetchone=True
        )
        if existing:
            execute_query(
                "UPDATE reviews SET rating=%s, comment=%s, created_at=NOW() WHERE id=%s",
                (rating, comment, existing['id']), commit=True
            )
        else:
            execute_query(
                """INSERT INTO reviews (user_id, restaurant_id, order_id, rating, comment, created_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())""",
                (user_id, order['restaurant_id'], order_id, rating, comment), commit=True
            )

        # Recalculate restaurant rating
        execute_query(
            """UPDATE restaurants
               SET rating = (SELECT ROUND(AVG(rating), 2) FROM reviews WHERE restaurant_id=%s)
               WHERE id=%s""",
            (order['restaurant_id'], order['restaurant_id']), commit=True
        )

        # Notify restaurant
        try:
            execute_query(
                """INSERT INTO notifications (user_id, role, title, message)
                   SELECT owner_id, 'restaurant', 'New Customer Review ⭐', CONCAT('New ', %s, '-star review on Order #', %s)
                   FROM restaurants WHERE id=%s AND owner_id IS NOT NULL""",
                (rating, order['order_code'], order['restaurant_id']), commit=True
            )
        except Exception:
            pass

        flash('Thank you! Your review and star rating have been submitted.', 'success')
        return redirect(url_for('customer.orders'))

    return render_template('review.html', order=order, restaurant=restaurant)


