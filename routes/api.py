"""
routes/api.py – JSON API endpoints for cart, coupon, payment (AJAX)
"""

try:
    import razorpay
except ImportError:
    razorpay = None
import json
import math
import logging
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, request, jsonify, session
from database import execute_query
from utils.helpers import (customer_required, calculate_order_totals,
                           generate_order_id, generate_transaction_id,
                           validate_and_calculate_coupon)
from config import Config

logger = logging.getLogger('foody.api')
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

    # Fetch restaurant delivery fee and preparation time
    rest = execute_query("SELECT name, delivery_fee, prep_time FROM restaurants WHERE id=%s", (restaurant_id,), fetchone=True)
    delivery_fee = float(rest['delivery_fee']) if rest and rest.get('delivery_fee') is not None else Config.DEFAULT_DELIVERY_FEE

    # Preparation time and estimated delivery time calculation
    prep_time_str = str(rest.get('prep_time') or '25') if rest else '25'
    import re
    from datetime import datetime, timedelta
    match = re.search(r'\d+', prep_time_str)
    prep_minutes = int(match.group()) if match else 25
    total_est_minutes = prep_minutes + 10  # 10 min transit
    est_delivery_time = datetime.now() + timedelta(minutes=total_est_minutes)

    tip_amount = float(order_data.get('tip_amount') or order_data.get('tip') or 0.0)

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
    grand_total_with_tip = round(totals['grand_total'] + tip_amount, 2)

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
                order_code, total_amount, delivery_fee, discount, tax, tip_amount, payment_method, payment_status,
                order_status, coupon_id, prep_time_minutes, estimated_delivery_time, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'placed',%s,%s,%s,NOW())""",
            (user_id, restaurant_id, address_id, delivery_address, customer_lat, customer_lng,
             order_code, grand_total_with_tip, totals['delivery_fee'], totals['discount'],
             totals['tax'], tip_amount, payment_method, payment_status, coupon_id,
             prep_minutes, est_delivery_time)
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
            (db_order_id, transaction_id, payment_method, grand_total_with_tip, payment_status)
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
            # If eligible for delivery (paid or COD), broadcast to online delivery partners
            if payment_status == 'paid' or payment_method == 'cod':
                rest_name = rest['name'] if rest and rest.get('name') else 'Kitchen'
                tx.execute(
                    """INSERT INTO notifications (user_id, role, title, message)
                       SELECT dp.user_id, 'delivery', 'New Delivery Available! 🛵',
                              CONCAT('New order #', %s, ' at ', %s, ' is available in your dispatch pool.')
                       FROM delivery_partners dp
                       WHERE dp.is_online = 1 AND dp.verification_status = 'approved'""",
                    (order_code, rest_name)
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
    user_id = session.get('user_id')
    role = session.get('role', 'customer')
    if not user_id:
        for auth_key in ('customer_auth', 'delivery_auth', 'restaurant_auth', 'admin_auth'):
            auth_val = session.get(auth_key)
            if auth_val and isinstance(auth_val, dict) and auth_val.get('user_id'):
                user_id = auth_val.get('user_id')
                role = auth_val.get('role', 'customer')
                break

    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    order = execute_query(
        """SELECT o.*,
                  COALESCE(r.name, 'Restaurant Kitchen') AS restaurant_name,
                  COALESCE(r.address, 'Restaurant Kitchen') AS restaurant_address,
                  COALESCE(r.phone, '+91 98250 12345') AS restaurant_phone,
                  COALESCE(r.latitude, 23.5880) AS restaurant_lat,
                  COALESCE(r.longitude, 72.3693) AS restaurant_lng,
                  COALESCE(a.address, o.delivery_address, 'Customer Delivery Address') AS delivery_address,
                  COALESCE(o.customer_lat, a.latitude, 23.5880) AS customer_lat,
                  COALESCE(o.customer_lng, a.longitude, 72.3693) AS customer_lng,
                  da.partner_id, da.status AS delivery_stage,
                  u.name AS partner_name, u.phone AS partner_phone,
                  dp.vehicle_type, dp.vehicle_number, dp.current_lat AS partner_lat,
                  dp.current_lng AS partner_lng
           FROM orders o
           LEFT JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN addresses a ON o.address_id=a.id
           LEFT JOIN delivery_assignments da ON da.order_id=o.id AND da.status != 'cancelled'
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

    # Time-based persistent countdown and progress graph metrics (Phase 4)
    from datetime import datetime
    created_dt = order.get('created_at')
    if isinstance(created_dt, str):
        try:
            created_dt = datetime.strptime(created_dt.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except Exception:
            created_dt = datetime.now()
    elif not created_dt:
        created_dt = datetime.now()

    prep_mins = int(order.get('prep_time_minutes') or 25)
    total_est_seconds = (prep_mins + 10) * 60
    now = datetime.now()
    elapsed_seconds = max(0, int((now - created_dt).total_seconds()))

    raw_status = (order['order_status'] or 'placed').lower()
    delivery_stage = (order['delivery_stage'] or 'pending').lower()
    has_partner = bool(order['partner_id'])

    is_delivered = (raw_status == 'delivered' or delivery_stage == 'delivered')
    if is_delivered:
        remaining_seconds = 0
        countdown_display = "Delivered 🎉"
        progress_percent = 100
        stage_index = 6
    else:
        remaining_seconds = max(0, total_est_seconds - elapsed_seconds)
        rem_mins = int(math.ceil(remaining_seconds / 60.0))
        if remaining_seconds == 0:
            countdown_display = "Arriving any moment"
            progress_percent = 95
        else:
            countdown_display = f"{rem_mins} mins remaining"
            time_ratio = elapsed_seconds / float(total_est_seconds)
            progress_percent = min(92, max(8, int(time_ratio * 100)))

        # Determine effective lifecycle progression index (0 to 6):
        if raw_status in ('out_for_delivery', 'picked_up') or delivery_stage in ('picked_up', 'out_for_delivery'):
            stage_index = 5
        elif raw_status == 'assigned' or has_partner or delivery_stage == 'assigned':
            stage_index = 4
        elif raw_status in ('ready_for_pickup', 'ready'):
            stage_index = 3
        elif raw_status == 'preparing':
            stage_index = 2
        elif raw_status == 'confirmed':
            stage_index = 1
        elif raw_status == 'placed':
            stage_index = 0
        else:
            stage_index = 0

    milestones = {
        'placed': True,
        'confirmed': stage_index >= 1 or raw_status in ('confirmed', 'preparing', 'ready', 'ready_for_pickup', 'out_for_delivery', 'delivered', 'assigned') or has_partner,
        'preparing': stage_index >= 2 or raw_status in ('preparing', 'ready', 'ready_for_pickup', 'out_for_delivery', 'delivered', 'assigned'),
        'ready_for_pickup': stage_index >= 3 or raw_status in ('ready', 'ready_for_pickup', 'out_for_delivery', 'delivered', 'assigned'),
        'assigned': stage_index >= 4 or has_partner or delivery_stage in ('assigned', 'picked_up', 'out_for_delivery', 'delivered') or raw_status == 'assigned',
        'out_for_delivery': stage_index >= 5 or raw_status in ('out_for_delivery', 'delivered') or delivery_stage in ('picked_up', 'out_for_delivery', 'delivered'),
        'delivered': is_delivered
    }

    # GPS Honesty check
    has_real_gps = (latest_loc is not None)

    return jsonify({
        'success': True,
        'order_id': order['id'],
        'order_code': order['order_code'],
        'order_status': order['order_status'],
        'delivery_stage': order['delivery_stage'] or 'pending',
        'has_partner': has_partner,
        'stage_index': stage_index,
        'is_delivered': is_delivered,
        'milestones': milestones,
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
        'time_tracking': {
            'elapsed_seconds': elapsed_seconds,
            'remaining_seconds': remaining_seconds,
            'countdown_display': countdown_display,
            'total_estimated_seconds': total_est_seconds,
            'progress_percent': progress_percent,
            'is_delivered': is_delivered,
            'prep_time_minutes': prep_mins,
            'estimated_delivery_time': str(order.get('estimated_delivery_time') or ''),
            'created_at': str(created_dt),
            'delivered_at': str(order.get('delivered_at') or '')
        },
        'gps_telemetry': {
            'has_real_gps': has_real_gps,
            'mode': 'real_satellite_gps' if has_real_gps else 'status_progression',
            'label': 'Live Device GPS Active' if has_real_gps else 'Status Progression (Awaiting Rider GPS)'
        },
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
    user_id = session.get('user_id')
    role = session.get('role', 'customer')
    if not user_id:
        for auth_key in ('customer_auth', 'delivery_auth', 'restaurant_auth', 'admin_auth'):
            auth_val = session.get(auth_key)
            if auth_val and isinstance(auth_val, dict) and auth_val.get('user_id'):
                user_id = auth_val.get('user_id')
                role = auth_val.get('role', 'customer')
                break

    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    data = request.get_json() or {}
    progress = float(data.get('progress', 0.5))  # 0.0 to 1.0
    progress = max(0.0, min(1.0, progress))

    order = execute_query(
        """SELECT o.*,
                  COALESCE(r.latitude, 23.5880) AS rest_lat,
                  COALESCE(r.longitude, 72.3693) AS rest_lng,
                  COALESCE(o.customer_lat, a.latitude, 23.5880) AS cust_lat,
                  COALESCE(o.customer_lng, a.longitude, 72.3693) AS cust_lng,
                  da.partner_id
           FROM orders o
           LEFT JOIN restaurants r ON o.restaurant_id=r.id
           LEFT JOIN addresses a ON o.address_id=a.id
           LEFT JOIN delivery_assignments da ON da.order_id=o.id
           WHERE o.id=%s""",
        (order_id,), fetchone=True
    )
    if not order:
        return jsonify({'success': False, 'message': 'Order not found.'}), 404

    # Resource ownership check
    if role == 'customer' and order['user_id'] != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403
    if role == 'delivery' and order['partner_id'] and order['partner_id'] != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403

    r_lat = float(order['rest_lat'] or 23.5880)
    r_lng = float(order['rest_lng'] or 72.3693)
    c_lat = float(order['customer_lat'] or 23.5880)
    c_lng = float(order['customer_lng'] or 72.3693)

    # Linear interpolation between restaurant and customer
    sim_lat = r_lat + (c_lat - r_lat) * progress
    sim_lng = r_lng + (c_lng - r_lng) * progress

    # Visual canvas simulation only (Requirement #59)
    # Does NOT alter persisted delivery_locations or database GPS telemetry
    dist_meters = calculate_haversine_distance(sim_lat, sim_lng, c_lat, c_lng)
    dist_str = f"{int(dist_meters)} m away" if dist_meters < 1000 else f"{dist_meters / 1000.0:.1f} km away"
    eta_mins = max(1, int(round((dist_meters / 416.0) + 1)))

    return jsonify({
        'success': True,
        'mode': 'DEMO_TRACKING_MODE',
        'is_simulation': True,
        'progress': progress,
        'simulated_location': {'latitude': sim_lat, 'longitude': sim_lng},
        'distance_remaining': dist_str,
        'eta': f"Estimated arrival in {eta_mins} minutes",
        'eta_minutes': eta_mins
    })


# ─────────────────────────────────────────────
# LIVE DELIVERY DISPATCH & FLEET APIS
# ─────────────────────────────────────────────

@api_bp.route('/delivery/dispatches', methods=['GET'])
def get_delivery_dispatches():
    """
    Authoritative live delivery dispatch feed for the Delivery Partner portal.
    Returns:
    - available_orders: Unassigned orders ready for rider self-acceptance.
    - active_deliveries: Orders currently assigned to this delivery partner.
    - stats: Daily & total delivery statistics and accumulated earnings.
    - is_online: Current duty status of the delivery partner.
    """
    from utils.helpers import get_delivery_auth
    auth = get_delivery_auth()
    partner_id = (auth.get('user_id') if auth else None) or (session.get('user_id') if session.get('role') == 'delivery' else None)
    if not partner_id:
        return jsonify({'success': False, 'message': 'Authentication required. Delivery partners only.'}), 401

    partner = execute_query("SELECT * FROM delivery_partners WHERE user_id=%s", (partner_id,), fetchone=True)
    if not partner:
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, is_online, is_available) VALUES (%s, 'Motorcycle', 'GJ-02-AB-1234', 1, 1)",
            (partner_id,), commit=True
        )
        partner = execute_query("SELECT * FROM delivery_partners WHERE user_id=%s", (partner_id,), fetchone=True)

    is_online = bool(partner.get('is_online', 1))

    # Available eligible unassigned orders
    # Filter out cancelled, delivered, rejected, or already-assigned orders
    available_orders = []
    if is_online:
        raw_available = execute_query(
            """SELECT o.*, r.name AS restaurant_name, r.address AS restaurant_address,
                      r.phone AS restaurant_phone, r.area AS restaurant_area,
                      u.name AS customer_name, u.phone AS customer_phone,
                      COALESCE(a.address, o.delivery_address) AS full_delivery_address,
                      (SELECT COUNT(*) FROM order_items WHERE order_id=o.id) AS item_count
               FROM orders o
               JOIN restaurants r ON o.restaurant_id=r.id
               JOIN users u ON o.user_id=u.id
               LEFT JOIN addresses a ON o.address_id=a.id
               LEFT JOIN delivery_assignments da ON da.order_id=o.id AND da.status != 'cancelled'
               WHERE o.order_status IN ('placed', 'confirmed', 'preparing', 'ready_for_pickup')
                 AND (o.payment_status = 'paid' OR o.payment_method = 'cod')
                 AND da.id IS NULL
               ORDER BY o.created_at ASC""",
            fetchall=True
        ) or []

        for o in raw_available:
            delivery_fee = float(o.get('delivery_fee') or 40.0)
            tip_amount = float(o.get('tip_amount') or 0.0)
            earnings = round(delivery_fee + tip_amount, 2)
            prep_minutes = int(o.get('prep_time_minutes') or 25)

            full_addr = str(o.get('full_delivery_address') or o.get('delivery_address') or 'Mehsana City, Gujarat')
            dest_display = full_addr if len(full_addr) <= 45 else full_addr[:45] + '...'

            available_orders.append({
                'id': o['id'],
                'order_code': o['order_code'],
                'restaurant_id': o['restaurant_id'],
                'restaurant_name': o['restaurant_name'],
                'restaurant_address': o['restaurant_address'],
                'restaurant_phone': o.get('restaurant_phone', ''),
                'restaurant_area': o.get('restaurant_area', 'Mehsana City'),
                'customer_name': o['customer_name'],
                'delivery_address': full_addr,
                'delivery_destination': dest_display,
                'item_count': int(o.get('item_count') or 1),
                'total_amount': float(o['total_amount']),
                'delivery_fee': delivery_fee,
                'tip_amount': tip_amount,
                'earnings': earnings,
                'order_status': o['order_status'],
                'order_status_display': (o.get('order_status') or 'placed').replace('_', ' ').title(),
                'prep_time_minutes': prep_minutes,
                'estimated_delivery_time': str(o.get('estimated_delivery_time') or ''),
                'created_at': str(o.get('created_at') or '')
            })

    # Active tasks assigned to this partner
    raw_assigned = execute_query(
        """SELECT da.id AS assignment_id, da.status AS assignment_status, da.assigned_at, da.picked_at,
                  o.id AS order_id, o.order_code, o.total_amount, o.order_status, o.delivery_fee, o.tip_amount,
                  u.name AS customer_name, u.phone AS customer_phone,
                  COALESCE(a.address, o.delivery_address) AS delivery_address,
                  r.name AS restaurant_name, r.address AS restaurant_address, r.phone AS restaurant_phone
           FROM delivery_assignments da
           JOIN orders o ON da.order_id=o.id
           JOIN users u ON o.user_id=u.id
           LEFT JOIN addresses a ON o.address_id=a.id
           JOIN restaurants r ON o.restaurant_id=r.id
           WHERE da.partner_id=%s AND da.status NOT IN ('delivered','cancelled')
           ORDER BY da.assigned_at DESC""",
        (partner_id,), fetchall=True
    ) or []

    active_deliveries = []
    for a in raw_assigned:
        earnings = round(float(a.get('delivery_fee') or 40.0) + float(a.get('tip_amount') or 0.0), 2)
        ord_st = (a.get('order_status') or '').lower()
        asg_st = (a.get('assignment_status') or '').lower()
        can_pickup = (asg_st == 'assigned' and ord_st in ('ready_for_pickup', 'ready'))
        can_deliver = (asg_st in ('picked_up', 'out_for_delivery'))

        active_deliveries.append({
            'id': a['assignment_id'],
            'assignment_id': a['assignment_id'],
            'order_id': a['order_id'],
            'order_code': a['order_code'],
            'status': a['assignment_status'],
            'order_status': a['order_status'],
            'order_status_display': ord_st.replace('_', ' ').title(),
            'assignment_status': a['assignment_status'],
            'restaurant_name': a['restaurant_name'],
            'restaurant_address': a['restaurant_address'],
            'restaurant_phone': a.get('restaurant_phone', ''),
            'customer_name': a['customer_name'],
            'customer_phone': a['customer_phone'],
            'delivery_address': a['delivery_address'],
            'total_amount': float(a['total_amount']),
            'earnings': earnings,
            'assigned_at': str(a.get('assigned_at') or ''),
            'picked_at': str(a.get('picked_at') or ''),
            'can_pickup': can_pickup,
            'can_deliver': can_deliver
        })

    today_res = execute_query(
        "SELECT COUNT(*) AS c FROM delivery_assignments WHERE partner_id=%s AND DATE(assigned_at)=CURDATE() AND status='delivered'",
        (partner_id,), fetchone=True
    )
    total_res = execute_query(
        "SELECT COUNT(*) AS c FROM delivery_assignments WHERE partner_id=%s AND status='delivered'",
        (partner_id,), fetchone=True
    )
    earn_res = execute_query(
        """SELECT COALESCE(SUM(COALESCE(os.partner_payout_amount, o.delivery_fee)),0) AS e
           FROM delivery_assignments da
           JOIN orders o ON da.order_id=o.id
           LEFT JOIN order_settlements os ON os.order_id=o.id
           WHERE da.partner_id=%s AND da.status='delivered'""",
        (partner_id,), fetchone=True
    )

    stats = {
        'today_deliveries': today_res['c'] if today_res else 0,
        'total_deliveries': total_res['c'] if total_res else 0,
        'pending': len(active_deliveries),
        'earnings': float(earn_res['e'] if earn_res else 0.0)
    }

    return jsonify({
        'success': True,
        'partner_id': partner_id,
        'is_online': is_online,
        'available_orders': available_orders,
        'available_count': len(available_orders),
        'active_deliveries': active_deliveries,
        'assigned': active_deliveries,
        'assigned_count': len(active_deliveries),
        'stats': stats,
        'timestamp': datetime.now().isoformat()
    })


@api_bp.route('/delivery/order/accept/<int:order_id>', methods=['POST'])
def api_delivery_accept(order_id):
    """API endpoint for accepting an order assignment."""
    from routes.delivery import accept_order
    return accept_order(order_id)


@api_bp.route('/delivery/order/pickup/<int:assignment_id>', methods=['POST'])
def api_delivery_pickup(assignment_id):
    """API endpoint for rider food pickup."""
    from routes.delivery import pickup_order
    return pickup_order(assignment_id)


@api_bp.route('/delivery/order/delivered/<int:assignment_id>', methods=['POST'])
def api_delivery_delivered(assignment_id):
    """API endpoint for rider delivery completion."""
    from routes.delivery import deliver_order
    return deliver_order(assignment_id)


@api_bp.route('/delivery/available-count', methods=['GET'])
def get_delivery_available_count():
    """
    Rider Dashboard polling endpoint.
    Allows Delivery Partner portal to detect newly placed eligible orders without full manual page reloads.
    """
    user_id = session.get('user_id') or (session.get('delivery_auth') or {}).get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    avail = execute_query(
        """SELECT COUNT(*) AS c FROM orders o
           LEFT JOIN delivery_assignments da ON da.order_id=o.id AND da.status != 'cancelled'
           WHERE o.order_status IN ('placed', 'confirmed', 'preparing', 'ready_for_pickup')
             AND (o.payment_status = 'paid' OR o.payment_method = 'cod')
             AND da.id IS NULL""",
        fetchone=True
    )
    assigned = execute_query(
        "SELECT COUNT(*) AS c FROM delivery_assignments WHERE partner_id=%s AND status NOT IN ('delivered','cancelled')",
        (user_id,), fetchone=True
    )
    return jsonify({
        'success': True,
        'available_count': avail['c'] if avail else 0,
        'assigned_count': assigned['c'] if assigned else 0
    })


@api_bp.route('/auth/status', methods=['GET'])
def auth_status():
    """
    Return current session authentication status and authoritative role information.
    Guarantees that client-side components can query and verify the authentic account identity.
    """
    user_id = session.get('user_id')
    raw_role = session.get('role')
    staff_role = session.get('staff_role')

    db_role = None
    if user_id:
        from utils.helpers import get_authoritative_account_role, get_role_display_name
        db_role = get_authoritative_account_role(user_id)
        role_label = get_role_display_name(db_role or raw_role, staff_role)
    else:
        from utils.helpers import get_role_display_name
        role_label = get_role_display_name(None)

    return jsonify({
        'authenticated': bool(user_id),
        'user_id': user_id,
        'user_name': session.get('user_name'),
        'role': db_role or raw_role or None,
        'role_display': role_label,
        'staff_role': staff_role,
        'restaurant_id': session.get('restaurant_id')
    })


