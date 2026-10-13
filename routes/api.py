"""
routes/api.py – JSON API endpoints for cart, coupon, payment (AJAX)
"""

try:
    import razorpay
except ImportError:
    razorpay = None
import json
import math
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, request, jsonify, session
from database import execute_query
from utils.helpers import (customer_required, calculate_order_totals,
                           generate_order_id, generate_transaction_id,
                           validate_and_calculate_coupon)
from config import Config

api_bp = Blueprint('api', __name__)


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two lat/lng coordinates."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c



# ─────────────────────────────────────────────
# CART APIS
# ─────────────────────────────────────────────

def _get_or_create_cart(user_id):
    """Get active cart or create one for this user."""
    cart = execute_query(
        "SELECT * FROM cart WHERE user_id=%s AND status='active'",
        (user_id,), fetchone=True
    )
    if not cart:
        cart_id = execute_query(
            "INSERT INTO cart (user_id, status) VALUES (%s, 'active')",
            (user_id,), commit=True
        )
        return cart_id
    return cart['id']


@api_bp.route('/cart/add', methods=['POST'])
@customer_required
def cart_add():
    """Add item to cart (or increment quantity)."""
    data = request.get_json()
    food_id  = data.get('food_id')
    quantity = int(data.get('quantity', 1))

    food = execute_query("SELECT * FROM food_items WHERE id=%s AND availability=1",
                         (food_id,), fetchone=True)
    if not food:
        return jsonify({'success': False, 'message': 'Item not available.'}), 404

    # Check if user already has items from a different restaurant
    cart_id = _get_or_create_cart(session['user_id'])
    existing_items = execute_query(
        """SELECT fi.restaurant_id FROM cart_items ci
           JOIN food_items fi ON ci.food_item_id=fi.id
           WHERE ci.cart_id=%s LIMIT 1""",
        (cart_id,), fetchone=True
    )
    if existing_items and existing_items['restaurant_id'] != food['restaurant_id']:
        return jsonify({
            'success': False,
            'message': 'Your cart has items from another restaurant. Clear cart first?',
            'conflict': True
        })

    # Upsert cart item
    existing = execute_query(
        "SELECT * FROM cart_items WHERE cart_id=%s AND food_item_id=%s",
        (cart_id, food_id), fetchone=True
    )
    if existing:
        execute_query(
            "UPDATE cart_items SET quantity=quantity+%s WHERE id=%s",
            (quantity, existing['id']), commit=True
        )
    else:
        execute_query(
            "INSERT INTO cart_items (cart_id, food_item_id, quantity, price) VALUES (%s,%s,%s,%s)",
            (cart_id, food_id, quantity, food['price']), commit=True
        )

    count = execute_query(
        "SELECT SUM(quantity) as total FROM cart_items WHERE cart_id=%s",
        (cart_id,), fetchone=True
    )
    total_count = int(count['total']) if count and count['total'] else 0
    return jsonify({'success': True, 'cart_count': total_count, 'message': f"{food['name']} added to cart!"})


@api_bp.route('/cart/update', methods=['POST'])
@customer_required
def cart_update():
    """Update item quantity in cart."""
    data     = request.get_json()
    item_id  = data.get('item_id')
    quantity = int(data.get('quantity', 1))

    cart_id = _get_or_create_cart(session['user_id'])
    if quantity <= 0:
        execute_query("DELETE FROM cart_items WHERE id=%s AND cart_id=%s",
                      (item_id, cart_id), commit=True)
    else:
        execute_query("UPDATE cart_items SET quantity=%s WHERE id=%s AND cart_id=%s",
                      (quantity, item_id, cart_id), commit=True)
    return jsonify({'success': True})


@api_bp.route('/cart/remove', methods=['POST'])
@customer_required
def cart_remove():
    """Remove specific item from cart."""
    data    = request.get_json()
    item_id = data.get('item_id')
    cart_id = _get_or_create_cart(session['user_id'])
    execute_query("DELETE FROM cart_items WHERE id=%s AND cart_id=%s",
                  (item_id, cart_id), commit=True)
    return jsonify({'success': True})


@api_bp.route('/cart/clear', methods=['POST'])
@customer_required
def cart_clear():
    """Clear entire cart."""
    cart_id = _get_or_create_cart(session['user_id'])
    execute_query("DELETE FROM cart_items WHERE cart_id=%s", (cart_id,), commit=True)
    return jsonify({'success': True})


@api_bp.route('/cart/data')
@customer_required
def cart_data():
    """Get cart items as JSON for dynamic updates."""
    cart_id = _get_or_create_cart(session['user_id'])
    items = execute_query(
        """SELECT ci.id, ci.quantity, ci.price,
                  fi.name, fi.image, fi.veg_type,
                  r.delivery_fee, r.name AS restaurant_name, r.id AS restaurant_id
           FROM cart_items ci
           JOIN food_items fi ON ci.food_item_id=fi.id
           JOIN restaurants r ON fi.restaurant_id=r.id
           WHERE ci.cart_id=%s""",
        (cart_id,), fetchall=True
    )
    subtotal = sum(float(i['price']) * i['quantity'] for i in items)
    delivery_fee = float(items[0]['delivery_fee']) if items else Config.DEFAULT_DELIVERY_FEE
    totals = calculate_order_totals(subtotal, delivery_fee)
    return jsonify({'success': True, 'items': items, 'totals': totals})


# ─────────────────────────────────────────────
# COUPON API
# ─────────────────────────────────────────────

@api_bp.route('/coupon/apply', methods=['POST'])
@customer_required
def apply_coupon():
    """Validate and apply a coupon code."""
    data     = request.get_json() or {}
    code     = data.get('code', '').strip().upper()
    subtotal = float(data.get('subtotal', 0))

    if not code:
        return jsonify({'success': False, 'message': 'Please enter a coupon code.'})

    is_valid, message, coupon, discount = validate_and_calculate_coupon(coupon_code=code, subtotal=subtotal)
    if not is_valid:
        return jsonify({'success': False, 'message': message})

    return jsonify({
        'success': True,
        'discount': discount,
        'message': message,
        'coupon_id': coupon['id'],
        'code': coupon['code']
    })


# ─────────────────────────────────────────────
# RAZORPAY PAYMENT API
# ─────────────────────────────────────────────

@api_bp.route('/payment/create-order', methods=['POST'])
@customer_required
def create_razorpay_order():
    """Create Razorpay order and return order_id to frontend."""
    if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
        return jsonify({
            'success': False,
            'is_configured': False,
            'error': 'Razorpay payment gateway credentials are not configured.',
            'message': 'Razorpay payment gateway credentials are not configured on this server. Please use Cash on Delivery or Demo Sandbox payment.'
        }), 400

    if razorpay is None:
        return jsonify({
            'success': False,
            'is_configured': False,
            'message': 'Razorpay SDK is not available in the environment.'
        }), 500

    data   = request.get_json() or {}
    amount = int(float(data.get('amount', 0)) * 100)  # in paise

    try:
        client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))
        rz_order = client.order.create({
            'amount': amount,
            'currency': 'INR',
            'payment_capture': 1
        })
        return jsonify({'success': True, 'order_id': rz_order['id'],
                        'key': Config.RAZORPAY_KEY_ID, 'amount': amount})
    except Exception as e:
        return jsonify({'success': False, 'message': f"Razorpay order creation failed: {str(e)}"}), 500


@api_bp.route('/payment/verify', methods=['POST'])
@customer_required
def verify_payment():
    """Verify Razorpay payment signature and create order in DB."""
    if not Config.RAZORPAY_KEY_SECRET:
        return jsonify({'success': False, 'message': 'Payment gateway credentials not configured.'}), 400

    import hmac, hashlib
    data = request.get_json() or {}
    rz_order_id  = data.get('razorpay_order_id', '')
    rz_payment_id= data.get('razorpay_payment_id', '')
    rz_signature = data.get('razorpay_signature', '')

    if not rz_order_id or not rz_payment_id or not rz_signature:
        return jsonify({'success': False, 'message': 'Incomplete payment response from gateway.'}), 400

    # Verify signature
    msg = f"{rz_order_id}|{rz_payment_id}"
    expected = hmac.new(
        Config.RAZORPAY_KEY_SECRET.encode(), msg.encode(), hashlib.sha256
    ).hexdigest()

    if expected != rz_signature:
        return jsonify({'success': False, 'message': 'Payment verification failed. Invalid gateway signature.'}), 400

    # Create order in database
    order_data = session.get('pending_order')
    if not order_data:
        return jsonify({'success': False, 'message': 'Session expired. Try again.'}), 400

    try:
        order_id = _create_order_in_db(order_data, 'online', 'paid',
                                       rz_payment_id, rz_order_id)
        session.pop('pending_order', None)
        return jsonify({'success': True, 'order_id': order_id,
                        'transaction_id': rz_payment_id})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to create order: {str(e)}'}), 500


@api_bp.route('/payment/demo', methods=['POST'])
@customer_required
def demo_payment():
    """Process demo/test payment (UPI, Card, Net Banking)."""
    data = request.get_json() or {}
    payment_method = data.get('payment_method', 'demo_upi')
    
    order_data = session.get('pending_order')
    if not order_data:
        return jsonify({'success': False, 'message': 'No pending order found. Please checkout again.'}), 400

    txn_id = generate_transaction_id()
    try:
        order_id = _create_order_in_db(order_data, payment_method, 'paid', txn_id)
        session.pop('pending_order', None)
        return jsonify({
            'success': True,
            'order_id': order_id,
            'transaction_id': txn_id,
            'message': 'Demo Payment Successful!'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Payment processing failed: {str(e)}'}), 500


def _create_order_in_db(order_data, payment_method, payment_status,
                        transaction_id=None, razorpay_order_id=None):
    """
    Persist order, order_items, payment, update coupon usage, and clear cart
    in a single atomic database transaction.
    """
    from database import db_transaction, execute_query
    from utils.helpers import (validate_and_calculate_coupon,
                               calculate_order_totals,
                               generate_order_id,
                               generate_transaction_id)

    user_id = session.get('user_id')
    if not user_id:
        raise ValueError("User session expired. Please log in again.")

    cart_id    = order_data.get('cart_id')
    address_id = order_data.get('address_id')
    raw_coupon = order_data.get('coupon_id')

    # Fetch and validate cart items from database to ensure fresh state and prevent duplicates
    items = execute_query(
        """SELECT ci.*, fi.name AS item_name, fi.price AS item_price, fi.restaurant_id
           FROM cart_items ci
           JOIN food_items fi ON ci.food_item_id = fi.id
           WHERE ci.cart_id = %s""",
        (cart_id,), fetchall=True
    )
    if not items:
        raise ValueError("Your cart is empty or this order has already been processed.")

    subtotal = sum(float(i['price']) * int(i['quantity']) for i in items)
    restaurant_id = items[0]['restaurant_id']

    # Fetch restaurant delivery fee
    rest = execute_query("SELECT delivery_fee FROM restaurants WHERE id=%s", (restaurant_id,), fetchone=True)
    delivery_fee = float(rest['delivery_fee']) if rest and rest.get('delivery_fee') is not None else Config.DEFAULT_DELIVERY_FEE

    # Sanitize and validate coupon_id
    coupon_id = None
    discount = 0.0
    if raw_coupon not in (None, '', 0, '0', 'null', 'None'):
        is_valid, msg, cp_rec, calc_discount = validate_and_calculate_coupon(
            coupon_id=raw_coupon,
            subtotal=subtotal
        )
        if is_valid and cp_rec:
            coupon_id = int(cp_rec['id'])
            discount = calc_discount
        else:
            coupon_id = None
            discount = 0.0

    # Recalculate verified totals on server side
    totals = calculate_order_totals(subtotal, delivery_fee, discount)

    order_code = generate_order_id()
    if not transaction_id:
        transaction_id = generate_transaction_id()

    # Fetch address details
    addr = None
    if address_id:
        addr = execute_query("SELECT * FROM addresses WHERE id=%s AND user_id=%s", (address_id, user_id), fetchone=True)
    delivery_address = addr['address'] if addr and addr.get('address') else "Mehsana City, Gujarat"
    customer_lat = float(addr['latitude']) if addr and addr.get('latitude') else 23.5880000
    customer_lng = float(addr['longitude']) if addr and addr.get('longitude') else 72.3693000

    # Atomic multi-statement transaction
    with db_transaction() as tx:
        # 1. Insert order
        db_order_id = tx.execute(
            """INSERT INTO orders
               (user_id, restaurant_id, address_id, delivery_address, customer_lat, customer_lng,
                order_code, total_amount, delivery_fee, discount, tax, payment_method, payment_status,
                order_status, coupon_id, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'placed',%s,NOW())""",
            (user_id, restaurant_id, address_id, delivery_address, customer_lat, customer_lng,
             order_code, totals['grand_total'], totals['delivery_fee'], totals['discount'],
             totals['tax'], payment_method, payment_status, coupon_id)
        )

        # 2. Insert order items
        for item in items:
            item_name = item.get('item_name') or 'Food Item'
            qty = int(item['quantity'])
            price = float(item['price'])
            item_subtotal = round(price * qty, 2)
            tx.execute(
                """INSERT INTO order_items (order_id, food_item_id, item_name, quantity, price, subtotal)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (db_order_id, item['food_item_id'], item_name, qty, price, item_subtotal)
            )

        # 3. Insert payment record
        tx.execute(
            """INSERT INTO payments (order_id, transaction_id, payment_method, amount, payment_status, payment_date)
               VALUES (%s,%s,%s,%s,%s,NOW())""",
            (db_order_id, transaction_id, payment_method, totals['grand_total'], payment_status)
        )

        # 4. Update coupon usage counter
        if coupon_id:
            tx.execute(
                "UPDATE coupons SET times_used = COALESCE(times_used, 0) + 1 WHERE id=%s",
                (coupon_id,)
            )

        # 5. Clear cart items and mark cart completed
        tx.execute("DELETE FROM cart_items WHERE cart_id=%s", (cart_id,))
        tx.execute("UPDATE cart SET status='completed' WHERE id=%s", (cart_id,))

        # 6. Notifications (best effort within transaction, does not abort order on failure)
        try:
            tx.execute(
                """INSERT INTO notifications (user_id, role, title, message)
                   VALUES (%s, 'customer', 'Order Placed! 🍔', CONCAT('Order #', %s, ' was successfully received.'))""",
                (user_id, order_code)
            )
            tx.execute(
                """INSERT INTO notifications (user_id, role, title, message)
                   SELECT owner_id, 'restaurant', 'New Order Alert! 🔔', CONCAT('New order #', %s, ' received.')
                   FROM restaurants WHERE id=%s AND owner_id IS NOT NULL""",
                (order_code, restaurant_id)
            )
        except Exception:
            pass

    return db_order_id


# ─────────────────────────────────────────────
# ORDER STATUS UPDATE (for delivery & restaurant)
# ─────────────────────────────────────────────

@api_bp.route('/order/update-status', methods=['POST'])
def update_order_status():
    """Update order status – used by restaurant and delivery panels."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    data     = request.get_json()
    order_id = data.get('order_id')
    status   = data.get('status')

    allowed_statuses = ['placed','confirmed','preparing','ready','out_for_delivery','delivered','cancelled']
    if status not in allowed_statuses:
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400

    execute_query(
        "UPDATE orders SET order_status=%s, updated_at=NOW() WHERE id=%s",
        (status, order_id), commit=True
    )
    # If delivered, create delivery assignment update
    if status == 'delivered':
        execute_query(
            """UPDATE delivery_assignments SET status='delivered', delivered_at=NOW()
               WHERE order_id=%s""",
            (order_id,), commit=True
        )
    return jsonify({'success': True})


# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# RESTAURANTS PUBLIC REST API
# ─────────────────────────────────────────────

def _clean_record(rec):
    """Serialize MySQL dictionary with Decimal and datetime to JSON-safe dict."""
    if not rec:
        return rec
    d = dict(rec)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
        elif isinstance(v, Decimal):
            d[k] = float(v)
    return d


@api_bp.route('/restaurants', methods=['GET'])
def get_restaurants():
    """
    Public REST API: List restaurants with search, cuisine, rating, sort, city, pagination.
    Returns all 50+ Mehsana restaurants in JSON format.
    """
    try:
        query_str   = request.args.get('q', '').strip()
        cuisine     = request.args.get('cuisine', '').strip()
        sort        = request.args.get('sort', 'recommended')
        city        = request.args.get('city', '').strip()
        min_rating  = request.args.get('rating', '')
        limit       = request.args.get('limit', type=int) or 100
        page        = request.args.get('page', type=int) or 1
        offset      = (page - 1) * limit

        sql = """SELECT r.*, 
                 (SELECT COUNT(*) FROM food_items fi WHERE fi.restaurant_id=r.id) AS menu_count
                 FROM restaurants r 
                 WHERE (r.verification_status='approved' OR r.verification_status IS NULL) 
                   AND (r.status='active' OR r.status='approved')"""
        params = []

        if query_str:
            sql += " AND (r.name LIKE %s OR r.cuisine LIKE %s OR r.description LIKE %s OR r.address LIKE %s)"
            like = f"%{query_str}%"
            params.extend([like, like, like, like])
        if cuisine:
            sql += " AND r.cuisine LIKE %s"
            params.append(f"%{cuisine}%")
        if min_rating:
            sql += " AND r.rating >= %s"
            params.append(float(min_rating))
        if city:
            sql += " AND LOWER(r.city) = LOWER(%s)"
            params.append(city)

        order_map = {
            'recommended': 'r.rating DESC, r.total_ratings DESC',
            'rating':      'r.rating DESC',
            'delivery':    'r.delivery_time ASC',
            'price_low':   'r.delivery_fee ASC',
            'price_high':  'r.delivery_fee DESC',
            'name':        'r.name ASC'
        }
        sql += f" ORDER BY {order_map.get(sort, 'r.rating DESC')}"
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

        raw_restaurants = execute_query(sql, tuple(params), fetchall=True) or []
        restaurants_list = [_clean_record(r) for r in raw_restaurants]

        # Total count query for accurate pagination
        count_sql = """SELECT COUNT(*) AS total FROM restaurants r
                       WHERE (r.verification_status='approved' OR r.verification_status IS NULL)
                         AND (r.status='active' OR r.status='approved')"""
        count_params = []
        if query_str:
            count_sql += " AND (r.name LIKE %s OR r.cuisine LIKE %s OR r.description LIKE %s OR r.address LIKE %s)"
            count_params.extend([like, like, like, like])
        if cuisine:
            count_sql += " AND r.cuisine LIKE %s"
            count_params.append(f"%{cuisine}%")
        if min_rating:
            count_sql += " AND r.rating >= %s"
            count_params.append(float(min_rating))
        if city:
            count_sql += " AND LOWER(r.city) = LOWER(%s)"
            count_params.append(city)

        total_row = execute_query(count_sql, tuple(count_params), fetchone=True)
        total_count = total_row['total'] if total_row else len(restaurants_list)

        return jsonify({
            'success': True,
            'count': len(restaurants_list),
            'total': total_count,
            'page': page,
            'limit': limit,
            'restaurants': restaurants_list,
            'data': restaurants_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0,
            'restaurants': [],
            'data': []
        }), 500


@api_bp.route('/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant_detail(restaurant_id):
    """Public REST API: Get single restaurant details by ID."""
    try:
        r = execute_query(
            """SELECT * FROM restaurants 
               WHERE id=%s 
                 AND (verification_status='approved' OR verification_status IS NULL) 
                 AND (status='active' OR status='approved')""",
            (restaurant_id,), fetchone=True
        )
        if not r:
            return jsonify({'success': False, 'message': 'Restaurant not found.'}), 404
        cleaned = _clean_record(r)
        return jsonify({'success': True, 'restaurant': cleaned, 'data': cleaned})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    """Public REST API: Get restaurant menu items grouped by categories."""
    try:
        categories = execute_query(
            """SELECT DISTINCT fc.id, fc.name, fc.icon
               FROM food_items fi
               JOIN food_categories fc ON fi.category_id = fc.id
               WHERE fi.restaurant_id=%s AND fi.availability=1
               ORDER BY fc.name""",
            (restaurant_id,), fetchall=True
        ) or []
        menu_items = execute_query(
            """SELECT * FROM food_items 
               WHERE restaurant_id=%s AND availability=1 
               ORDER BY name""",
            (restaurant_id,), fetchall=True
        ) or []
        cleaned_items = [_clean_record(item) for item in menu_items]
        return jsonify({
            'success': True,
            'restaurant_id': restaurant_id,
            'categories': categories,
            'items': cleaned_items,
            'total_items': len(cleaned_items)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────
# LIVE SEARCH AJAX
# ─────────────────────────────────────────────

@api_bp.route('/search/live')
def live_search():
    """Return quick search suggestions as JSON."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    like = f"%{q}%"
    restaurants_r = execute_query(
        """SELECT id, name, cuisine, 'restaurant' AS type FROM restaurants 
           WHERE (verification_status='approved' OR verification_status IS NULL) 
             AND (status='active' OR status='approved') 
             AND name LIKE %s LIMIT 5""",
        (like,), fetchall=True
    ) or []
    foods_r = execute_query(
        """SELECT fi.id, fi.name, r.id AS restaurant_id, 'food' AS type
           FROM food_items fi JOIN restaurants r ON fi.restaurant_id=r.id
           WHERE fi.availability=1 
             AND (r.verification_status='approved' OR r.verification_status IS NULL) 
             AND (r.status='active' OR r.status='approved') 
             AND fi.name LIKE %s LIMIT 5""",
        (like,), fetchall=True
    ) or []
    results = list(restaurants_r) + list(foods_r)
    return jsonify(results)


# ─────────────────────────────────────────────
# LIVE DELIVERY TRACKING & GPS APIS (GOOGLE MAPS PLATFORM)
# ─────────────────────────────────────────────

@api_bp.route('/orders/<int:order_id>/tracking', methods=['GET'])
def get_order_tracking(order_id):
    """
    Live tracking API for customers, riders, and restaurants.
    Returns real-time GPS coordinates, calculated Haversine distance, dynamic ETA, and assignment status.
    Protected with resource ownership validation.
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    user_id = session['user_id']
    role = session.get('role', 'customer')

    order = execute_query(
        """SELECT o.*, r.name AS restaurant_name, r.address AS restaurant_address,
                  r.phone AS restaurant_phone, r.latitude AS restaurant_lat,
                  r.longitude AS restaurant_lng,
                  da.partner_id, da.status AS delivery_stage,
                  u.name AS partner_name, u.phone AS partner_phone,
                  dp.vehicle_type, dp.vehicle_number, dp.current_lat AS partner_lat,
                  dp.current_lng AS partner_lng
           FROM orders o
           JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN delivery_assignments da ON da.order_id=o.id
           LEFT JOIN users u ON da.partner_id=u.id
           LEFT JOIN delivery_partners dp ON da.partner_id=dp.user_id
           WHERE o.id=%s""",
        (order_id,), fetchone=True
    )
    if not order:
        return jsonify({'success': False, 'message': 'Order not found.'}), 404

    # RBAC & Resource Ownership verification
    if role == 'customer' and order['user_id'] != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
    if role == 'delivery' and order['partner_id'] != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
    if role == 'restaurant':
        rest_owner = execute_query("SELECT owner_id FROM restaurants WHERE id=%s", (order['restaurant_id'],), fetchone=True)
        if not rest_owner or rest_owner['owner_id'] != user_id:
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403

    # Coordinates
    rest_lat = float(order['restaurant_lat'] or 23.5880)
    rest_lng = float(order['restaurant_lng'] or 72.3693)
    cust_lat = float(order['customer_lat'] or 23.5880)
    cust_lng = float(order['customer_lng'] or 72.3693)

    # Latest recorded location
    latest_loc = execute_query(
        "SELECT latitude, longitude, recorded_at FROM delivery_locations WHERE order_id=%s ORDER BY recorded_at DESC LIMIT 1",
        (order_id,), fetchone=True
    )

    if latest_loc:
        rider_lat = float(latest_loc['latitude'])
        rider_lng = float(latest_loc['longitude'])
        last_updated = str(latest_loc['recorded_at'])
    elif order['partner_lat'] and order['partner_lng']:
        rider_lat = float(order['partner_lat'])
        rider_lng = float(order['partner_lng'])
        last_updated = str(order['updated_at'])
    else:
        rider_lat = rest_lat
        rider_lng = rest_lng
        last_updated = str(order['updated_at'] or order['created_at'])

    # Compute actual distance and dynamic ETA
    dist_meters = calculate_haversine_distance(rider_lat, rider_lng, cust_lat, cust_lng)
    if dist_meters < 1000:
        dist_str = f"{int(dist_meters)} m away"
    else:
        dist_str = f"{dist_meters / 1000.0:.1f} km away"

    # Assume average city transit speed ~25 km/h + 3 min buffer
    eta_mins = max(2, int(round((dist_meters / 416.0) + 3)))
    eta_str = f"Estimated arrival in {eta_mins} minutes"

    return jsonify({
        'success': True,
        'order_id': order['id'],
        'order_code': order['order_code'],
        'order_status': order['order_status'],
        'delivery_stage': order['delivery_stage'] or 'pending',
        'delivery_partner': {
            'id': order['partner_id'],
            'name': order['partner_name'] or 'Assigned Delivery Partner',
            'phone': order['partner_phone'] or 'Contact Rider',
            'vehicle': f"{order['vehicle_type'] or 'Motorcycle'} ({order['vehicle_number'] or 'GJ-02'})"
        } if order['partner_id'] else None,
        'delivery_location': {
            'latitude': rider_lat,
            'longitude': rider_lng
        },
        'customer_location': {
            'latitude': cust_lat,
            'longitude': cust_lng,
            'address': order['delivery_address']
        },
        'restaurant_location': {
            'latitude': rest_lat,
            'longitude': rest_lng,
            'name': order['restaurant_name'],
            'address': order['restaurant_address']
        },
        'distance_remaining': dist_str,
        'distance_meters': round(dist_meters, 1),
        'eta': eta_str,
        'eta_minutes': eta_mins,
        'last_updated': last_updated
    })


@api_bp.route('/delivery/location', methods=['POST'])
def update_delivery_location():
    """
    Rider GPS Beacon Endpoint (Requirement #47).
    Receives device coordinates and persists breadcrumb to delivery_locations and rider profile.
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    user_id = session['user_id']
    role = session.get('role')
    data = request.get_json() or {}

    order_id = data.get('order_id')
    lat = data.get('latitude')
    lng = data.get('longitude')

    if lat is None or lng is None:
        return jsonify({'success': False, 'message': 'Latitude and longitude required.'}), 400

    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid coordinates.'}), 400

    # Authorization verification
    if role == 'delivery' and order_id:
        assignment = execute_query(
            "SELECT id FROM delivery_assignments WHERE order_id=%s AND partner_id=%s",
            (order_id, user_id), fetchone=True
        )
        if not assignment and role != 'admin':
            return jsonify({'success': False, 'message': 'You are not assigned to this order.'}), 403

    # Update delivery partner current lat/lng
    execute_query(
        "UPDATE delivery_partners SET current_lat=%s, current_lng=%s, updated_at=NOW() WHERE user_id=%s",
        (lat, lng, user_id), commit=True
    )

    if order_id:
        execute_query(
            """INSERT INTO delivery_locations (delivery_partner_id, order_id, latitude, longitude, recorded_at)
               VALUES (%s, %s, %s, %s, NOW())""",
            (user_id, order_id, lat, lng), commit=True
        )

    return jsonify({
        'success': True,
        'message': 'Location recorded successfully.',
        'data': {'latitude': lat, 'longitude': lng}
    })


@api_bp.route('/orders/<int:order_id>/simulate-step', methods=['POST'])
def simulate_order_step(order_id):
    """
    Demo Tracking Mode endpoint for viva examination (Requirement #59).
    Simulates rider progression along interpolated coordinates from Restaurant to Customer.
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    data = request.get_json() or {}
    progress = float(data.get('progress', 0.5))  # 0.0 to 1.0
    progress = max(0.0, min(1.0, progress))

    order = execute_query(
        """SELECT o.*, r.latitude AS rest_lat, r.longitude AS rest_lng,
                  da.partner_id
           FROM orders o
           JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN delivery_assignments da ON da.order_id=o.id
           WHERE o.id=%s""",
        (order_id,), fetchone=True
    )
    if not order:
        return jsonify({'success': False, 'message': 'Order not found.'}), 404

    r_lat = float(order['rest_lat'] or 23.5880)
    r_lng = float(order['rest_lng'] or 72.3693)
    c_lat = float(order['customer_lat'] or 23.5880)
    c_lng = float(order['customer_lng'] or 72.3693)

    # Linear interpolation between restaurant and customer
    sim_lat = r_lat + (c_lat - r_lat) * progress
    sim_lng = r_lng + (c_lng - r_lng) * progress

    partner_id = order['partner_id'] or session['user_id']
    execute_query(
        "UPDATE delivery_partners SET current_lat=%s, current_lng=%s, updated_at=NOW() WHERE user_id=%s",
        (sim_lat, sim_lng, partner_id), commit=True
    )
    execute_query(
        """INSERT INTO delivery_locations (delivery_partner_id, order_id, latitude, longitude, recorded_at)
           VALUES (%s, %s, %s, %s, NOW())""",
        (partner_id, order_id, sim_lat, sim_lng), commit=True
    )

    dist_meters = calculate_haversine_distance(sim_lat, sim_lng, c_lat, c_lng)
    dist_str = f"{int(dist_meters)} m away" if dist_meters < 1000 else f"{dist_meters / 1000.0:.1f} km away"
    eta_mins = max(1, int(round((dist_meters / 416.0) + 1)))

    return jsonify({
        'success': True,
        'mode': 'DEMO_TRACKING_MODE',
        'progress': progress,
        'simulated_location': {'latitude': sim_lat, 'longitude': sim_lng},
        'distance_remaining': dist_str,
        'eta': f"Estimated arrival in {eta_mins} minutes",
        'eta_minutes': eta_mins
    })

