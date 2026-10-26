"""
routes/restaurant.py – Restaurant owner dashboard routes
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from database import execute_query
from utils.helpers import (restaurant_required, save_uploaded_image,
                           save_uploaded_document, validate_email, validate_phone,
                           validate_password, get_restaurant_auth, set_restaurant_auth, clear_restaurant_auth)
from werkzeug.security import generate_password_hash, check_password_hash

restaurant_bp = Blueprint('restaurant', __name__)


def _get_restaurant(owner_id):
    """Get restaurant record for logged-in owner."""
    return execute_query(
        "SELECT * FROM restaurants WHERE owner_id=%s", (owner_id,), fetchone=True
    )


# ─────────────────────────────────────────────
# RESTAURANT PARTNER AUTHENTICATION
# ─────────────────────────────────────────────

@restaurant_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Separate dedicated login page for restaurant owners."""
    if get_restaurant_auth():
        rest = _get_restaurant(get_restaurant_auth()['user_id'])
        if rest and rest.get('verification_status') == 'approved':
            return redirect(url_for('restaurant.dashboard'))
        elif rest:
            return redirect(url_for('restaurant.application_status', id=rest['id']))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password   = request.form.get('password', '')
        remember   = request.form.get('remember_me')

        if not identifier or not password:
            flash('Email/Mobile and password are required.', 'danger')
            return render_template('restaurant/login.html')

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
            flash('Invalid partner credentials.', 'danger')
            return render_template('restaurant/login.html')

        if user['role'] not in ('restaurant', 'admin'):
            flash('This portal is reserved for restaurant partners. Please use Customer Login.', 'warning')
            return render_template('restaurant/login.html')

        if user['status'] == 'inactive':
            flash('Your partner account has been deactivated. Please contact support.', 'warning')
            return render_template('restaurant/login.html')

        # Check restaurant approval status
        rest = None
        if user['role'] == 'restaurant':
            rest = execute_query("SELECT * FROM restaurants WHERE owner_id=%s", (user['id'],), fetchone=True)
            if rest:
                v_status = rest.get('verification_status', 'pending')
                if v_status == 'pending':
                    flash('Your restaurant registration is currently pending admin approval. You can track your status below.', 'warning')
                    return redirect(url_for('restaurant.application_status', id=rest['id']))
                elif v_status in ('rejected', 'suspended'):
                    flash('Your restaurant partner account has been suspended or rejected. Please contact administrator support.', 'danger')
                    return redirect(url_for('restaurant.application_status', id=rest['id']))

        session.permanent = bool(remember)
        set_restaurant_auth(user, restaurant_id=rest['id'] if rest else None)

        flash(f"Welcome to Kitchen Operations, {user['name']}!", 'success')
        return redirect(url_for('restaurant.dashboard'))

    return render_template('restaurant/login.html')


@restaurant_bp.route('/logout')
def logout():
    """Securely log out restaurant partner."""
    clear_restaurant_auth()
    flash("Restaurant partner session ended.", "info")
    return redirect(url_for('restaurant.login'))


@restaurant_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Separate dedicated onboarding page for restaurant partners."""
    if 'user_id' in session and session.get('role') == 'restaurant':
        rest = _get_restaurant(session['user_id'])
        if rest and rest.get('verification_status') == 'approved':
            return redirect(url_for('restaurant.dashboard'))
        elif rest:
            return redirect(url_for('restaurant.application_status', id=rest['id']))

    if request.method == 'POST':
        name            = request.form.get('name', '').strip() or request.form.get('owner_name', '').strip()
        email           = request.form.get('email', '').strip().lower()
        phone           = request.form.get('phone', '').strip()
        restaurant_name = request.form.get('restaurant_name', '').strip()
        cuisine         = request.form.get('cuisine', '').strip()
        restaurant_area = request.form.get('restaurant_area', '').strip() or request.form.get('area', '').strip() or 'Mehsana City'
        address         = request.form.get('address', '').strip()
        
        # Extensible city handling (supports Mehsana, Ahmedabad, etc., or custom city)
        city_choice     = request.form.get('city_choice', 'Mehsana').strip()
        custom_city     = request.form.get('custom_city', '').strip()
        city = custom_city if (city_choice.lower() == 'other' and custom_city) else (city_choice or request.form.get('city', 'Mehsana').strip() or 'Mehsana')

        pincode         = request.form.get('pincode', '384002').strip() or '384002'
        open_time       = request.form.get('open_time', '09:00').strip() or '09:00'
        close_time      = request.form.get('close_time', '23:00').strip() or '23:00'
        description     = request.form.get('description', '').strip() or f"Authentic {cuisine} dining outlet in {city}"
        fssai_number    = request.form.get('fssai_number', '').strip()
        password        = request.form.get('password', '')
        confirm         = request.form.get('confirm_password', '')

        # SECURITY: Strictly restaurant role only!
        role = 'restaurant'

        errors = []
        if not name:
            errors.append('Owner full name is required.')
        if not validate_email(email):
            errors.append('Enter a valid business email address.')
        if not validate_phone(phone):
            errors.append('Enter a valid 10-digit Indian mobile number.')
        if not restaurant_name:
            errors.append('Restaurant outlet name is required.')
        if not cuisine:
            errors.append('Cuisine types are required.')
        if not address:
            errors.append('Shop/outlet address is required.')
        if not city:
            errors.append('Operating city is required.')
        if not validate_password(password):
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        # Securely handle verification document upload
        doc_url = None
        doc_file = request.files.get('document') or request.files.get('verification_doc')
        if doc_file and doc_file.filename:
            doc_url = save_uploaded_document(doc_file)
            if not doc_url and doc_file.filename:
                errors.append('Invalid verification document. Allowed formats: PDF, PNG, JPG, JPEG, WEBP.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('restaurant/register.html', form=request.form)

        existing = execute_query(
            "SELECT id, email, phone FROM users WHERE email=%s OR phone=%s", (email, phone), fetchone=True
        )
        if existing:
            if existing['email'] == email:
                flash('This email is already registered. Please login.', 'warning')
            else:
                flash('This contact number is already registered. Please login.', 'warning')
            return render_template('restaurant/register.html', form=request.form)

        pw_hash = generate_password_hash(password)
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Gujarat', %s, 'active')""",
            (name, email, phone, pw_hash, role, address, city, pincode),
            commit=True
        )

        rest_id = execute_query(
            """INSERT INTO restaurants (owner_id, name, description, cuisine, address, area, city, state, pincode, phone, email, open_time, close_time, fssai_number, verification_doc, rating, verification_status, status, is_open)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Gujarat', %s, %s, %s, %s, %s, %s, %s, 4.50, 'pending', 'inactive', 1)""",
            (user_id, restaurant_name, description, cuisine, address, restaurant_area, city, pincode, phone, email, open_time, close_time, fssai_number, doc_url),
            commit=True
        )

        flash(f"Restaurant registration for '{restaurant_name}' submitted successfully! Application is currently pending administrator verification.", 'success')
        return redirect(url_for('restaurant.application_status', id=rest_id))

    return render_template('restaurant/register.html', form={})


@restaurant_bp.route('/application-status')
def application_status():
    """Public/partner application tracking page."""
    rid = request.args.get('id')
    rest = None
    if rid and str(rid).isdigit():
        rest = execute_query(
            """SELECT r.*, u.name AS owner_name, u.email AS owner_email, u.phone AS owner_phone
               FROM restaurants r
               LEFT JOIN users u ON r.owner_id=u.id
               WHERE r.id=%s""",
            (int(rid),), fetchone=True
        )
    elif 'user_id' in session:
        rest = execute_query(
            """SELECT r.*, u.name AS owner_name, u.email AS owner_email, u.phone AS owner_phone
               FROM restaurants r
               LEFT JOIN users u ON r.owner_id=u.id
               WHERE r.owner_id=%s""",
            (session['user_id'],), fetchone=True
        )

    return render_template('restaurant/application_status.html', restaurant=rest)


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@restaurant_bp.route('/')
@restaurant_required
def index():
    return redirect(url_for('restaurant.dashboard'))


@restaurant_bp.route('/dashboard')
@restaurant_required
def dashboard():
    rest = _get_restaurant(session['user_id'])
    if not rest:
        flash('Your restaurant profile is not set up yet. Please complete it.', 'info')
        return redirect(url_for('restaurant.profile'))

    if rest.get('verification_status') != 'approved':
        flash('Your restaurant application is currently under review by administrators.', 'warning')
        return redirect(url_for('restaurant.application_status', id=rest['id']))

    stats = {
        'total_orders': execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s",
            (rest['id'],), fetchone=True)['c'],
        'today_orders': execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s AND DATE(created_at)=CURDATE()",
            (rest['id'],), fetchone=True)['c'],
        'today_sales': execute_query(
            "SELECT COALESCE(SUM(total_amount),0) AS s FROM orders "
            "WHERE restaurant_id=%s AND DATE(created_at)=CURDATE() AND order_status!='cancelled'",
            (rest['id'],), fetchone=True)['s'],
        'total_items': execute_query(
            "SELECT COUNT(*) AS c FROM food_items WHERE restaurant_id=%s",
            (rest['id'],), fetchone=True)['c'],
        'pending_orders': execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s AND order_status='placed'",
            (rest['id'],), fetchone=True)['c'],
    }
    recent_orders = execute_query(
        """SELECT o.*, u.name AS customer_name, u.phone AS customer_phone
           FROM orders o JOIN users u ON o.user_id=u.id
           WHERE o.restaurant_id=%s ORDER BY o.created_at DESC LIMIT 10""",
        (rest['id'],), fetchall=True
    )
    return render_template('restaurant/dashboard.html',
                           restaurant=rest, stats=stats, recent_orders=recent_orders)


# ─────────────────────────────────────────────
# RESTAURANT PROFILE
# ─────────────────────────────────────────────

@restaurant_bp.route('/profile', methods=['GET', 'POST'])
@restaurant_required
def profile():
    rest = _get_restaurant(session['user_id'])

    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        description  = request.form.get('description', '').strip()
        cuisine      = request.form.get('cuisine', '').strip()
        address      = request.form.get('address', '').strip()
        area         = request.form.get('area', 'Mehsana City').strip()
        city         = request.form.get('city', 'Mehsana').strip()
        state        = request.form.get('state', 'Gujarat').strip()
        pincode      = request.form.get('pincode', '384002').strip()
        phone        = request.form.get('phone', '').strip()
        email        = request.form.get('email', '').strip()
        delivery_time= request.form.get('delivery_time', '25-35 min').strip()
        delivery_fee = float(request.form.get('delivery_fee', 40.0) or 40.0)
        min_order    = float(request.form.get('min_order', 100.0) or 100.0)
        open_time    = request.form.get('open_time', '09:00').strip()
        close_time   = request.form.get('close_time', '23:00').strip()
        is_open      = 1 if request.form.get('is_open') == '1' or request.form.get('is_open') == 'on' else 0

        try:
            lat = float(request.form.get('latitude', rest['latitude'] if rest else 23.5880))
            lng = float(request.form.get('longitude', rest['longitude'] if rest else 72.3693))
        except (ValueError, TypeError):
            lat, lng = 23.5880, 72.3693

        image_url = request.form.get('image_url', '').strip() or None
        if 'image' in request.files and request.files['image'].filename:
            uploaded_pic = save_uploaded_image(request.files['image'])
            if uploaded_pic:
                image_url = uploaded_pic

        if rest:
            img_clause = ", image=%s" if image_url else ""
            params = [name, description, cuisine, address, area, city, state, pincode,
                      phone, email, delivery_time, delivery_fee, min_order, open_time, close_time,
                      is_open, lat, lng]
            if image_url:
                params.append(image_url)
            params.append(rest['id'])
            execute_query(
                f"""UPDATE restaurants SET name=%s, description=%s, cuisine=%s,
                    address=%s, area=%s, city=%s, state=%s, pincode=%s, phone=%s, email=%s,
                    delivery_time=%s, delivery_fee=%s, min_order=%s, open_time=%s, close_time=%s,
                    is_open=%s, latitude=%s, longitude=%s, updated_at=NOW(){img_clause}
                    WHERE id=%s""",
                tuple(params), commit=True
            )
            flash('Restaurant profile updated successfully in MySQL!', 'success')
        else:
            execute_query(
                """INSERT INTO restaurants
                   (owner_id, name, description, cuisine, address, area, city, state, pincode, phone, email,
                    delivery_time, delivery_fee, min_order, open_time, close_time,
                    image, is_open, latitude, longitude, verification_status, status, rating)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending','active',4.50)""",
                (session['user_id'], name, description, cuisine, address, area, city, state, pincode, phone, email,
                 delivery_time, delivery_fee, min_order, open_time, close_time,
                 image_url or 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80',
                 is_open, lat, lng),
                commit=True
            )
            flash('Restaurant profile registered successfully! Pending admin approval.', 'success')

        return redirect(url_for('restaurant.profile'))

    owner = execute_query("SELECT * FROM users WHERE id=%s", (session['user_id'],), fetchone=True)
    return render_template('restaurant/profile.html', restaurant=rest, owner=owner)


@restaurant_bp.route('/profile/toggle-open', methods=['POST'])
@restaurant_required
def toggle_open():
    """Toggle restaurant open/closed status."""
    rest = _get_restaurant(session['user_id'])
    if rest:
        new_val = 0 if rest.get('is_open', 1) else 1
        execute_query("UPDATE restaurants SET is_open=%s WHERE id=%s", (new_val, rest['id']), commit=True)
        status_label = "OPEN" if new_val else "CLOSED"
        flash(f'Restaurant is now marked as {status_label}.', 'info')
    return redirect(request.referrer or url_for('restaurant.dashboard'))


# ─────────────────────────────────────────────
# FOOD MENU MANAGEMENT
# ─────────────────────────────────────────────

@restaurant_bp.route('/menu')
@restaurant_required
def menu():
    rest = _get_restaurant(session['user_id'])
    if not rest:
        return redirect(url_for('restaurant.profile'))

    items = execute_query(
        """SELECT fi.*, fc.name AS category_name
           FROM food_items fi
           LEFT JOIN food_categories fc ON fi.category_id=fc.id
           WHERE fi.restaurant_id=%s ORDER BY fc.name, fi.name""",
        (rest['id'],), fetchall=True
    )
    categories = execute_query(
        "SELECT * FROM food_categories ORDER BY name", fetchall=True
    )
    return render_template('restaurant/menu.html',
                           restaurant=rest, items=items, categories=categories)


@restaurant_bp.route('/menu/add', methods=['GET', 'POST'])
@restaurant_bp.route('/food/add', methods=['GET', 'POST'])
@restaurant_required
def add_food():
    rest = _get_restaurant(session['user_id'])
    categories = execute_query("SELECT * FROM food_categories ORDER BY name", fetchall=True)

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category_id = request.form.get('category_id') or 1
        description = request.form.get('description', '').strip()
        price       = float(request.form.get('price', 0) or 0)
        discount    = float(request.form.get('discount', 0) or 0)
        final_price = price - (price * discount / 100.0) if discount > 0 else price
        veg_type    = request.form.get('veg_type', 'veg')
        prep_time   = int(request.form.get('preparation_time', 20) or 20)
        availability= 1 if request.form.get('availability') in ('1', 'on', True) else 0
        is_bestseller = 1 if request.form.get('is_bestseller') in ('1', 'on', True) else 0

        image_url = 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500&q=80'
        if 'image' in request.files and request.files['image'].filename:
            image_url = save_uploaded_image(request.files['image']) or image_url

        if not name or not price:
            flash('Name and price are required.', 'danger')
        else:
            execute_query(
                """INSERT INTO food_items
                   (restaurant_id, category_id, name, description, price, discount, final_price,
                    image, veg_type, preparation_time, availability, is_bestseller)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (rest['id'], category_id, name, description, price, discount, final_price,
                 image_url, veg_type, prep_time, availability, is_bestseller),
                commit=True
            )
            flash(f"'{name}' added to menu successfully!", 'success')
            return redirect(url_for('restaurant.menu'))

    return render_template('restaurant/add_food.html',
                           restaurant=rest, categories=categories)


@restaurant_bp.route('/menu/edit/<int:item_id>', methods=['GET', 'POST'])
@restaurant_bp.route('/food/edit/<int:item_id>', methods=['GET', 'POST'])
@restaurant_required
def edit_food(item_id):
    rest = _get_restaurant(session['user_id'])
    item = execute_query(
        "SELECT * FROM food_items WHERE id=%s AND restaurant_id=%s",
        (item_id, rest['id']), fetchone=True
    )
    if not item:
        flash('Food item not found or unauthorized access.', 'danger')
        return redirect(url_for('restaurant.menu'))

    categories = execute_query("SELECT * FROM food_categories ORDER BY name", fetchall=True)

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category_id = request.form.get('category_id') or item['category_id']
        description = request.form.get('description', '').strip()
        price       = float(request.form.get('price', 0) or 0)
        discount    = float(request.form.get('discount', 0) or 0)
        final_price = price - (price * discount / 100.0) if discount > 0 else price
        veg_type    = request.form.get('veg_type', 'veg')
        prep_time   = int(request.form.get('preparation_time', 20) or 20)
        availability= 1 if request.form.get('availability') in ('1', 'on', True) else 0
        is_bestseller = 1 if request.form.get('is_bestseller') in ('1', 'on', True) else 0

        image_url = item['image']
        if 'image' in request.files and request.files['image'].filename:
            image_url = save_uploaded_image(request.files['image']) or image_url

        execute_query(
            """UPDATE food_items SET name=%s, category_id=%s, description=%s,
               price=%s, discount=%s, final_price=%s, image=%s, veg_type=%s,
               preparation_time=%s, availability=%s, is_bestseller=%s, updated_at=NOW()
               WHERE id=%s AND restaurant_id=%s""",
            (name, category_id, description, price, discount, final_price, image_url,
             veg_type, prep_time, availability, is_bestseller, item_id, rest['id']),
            commit=True
        )
        flash('Food item updated successfully!', 'success')
        return redirect(url_for('restaurant.menu'))

    return render_template('restaurant/edit_food.html',
                           restaurant=rest, item=item, categories=categories)


@restaurant_bp.route('/menu/toggle/<int:item_id>', methods=['POST', 'GET'])
@restaurant_bp.route('/food/toggle/<int:item_id>', methods=['POST', 'GET'])
@restaurant_required
def toggle_food(item_id):
    rest = _get_restaurant(session['user_id'])
    item = execute_query(
        "SELECT id, availability FROM food_items WHERE id=%s AND restaurant_id=%s",
        (item_id, rest['id']), fetchone=True
    )
    if item:
        new_avail = 0 if item['availability'] else 1
        execute_query("UPDATE food_items SET availability=%s WHERE id=%s", (new_avail, item_id), commit=True)
        status_text = "available" if new_avail else "out of stock"
        flash(f'Food item marked as {status_text}.', 'info')
    return redirect(url_for('restaurant.menu'))


@restaurant_bp.route('/menu/delete/<int:item_id>', methods=['POST', 'GET'])
@restaurant_bp.route('/food/delete/<int:item_id>', methods=['POST', 'GET'])
@restaurant_required
def delete_food(item_id):
    rest = _get_restaurant(session['user_id'])
    execute_query(
        "DELETE FROM food_items WHERE id=%s AND restaurant_id=%s",
        (item_id, rest['id']), commit=True
    )
    flash('Food item deleted from menu.', 'success')
    return redirect(url_for('restaurant.menu'))





# ─────────────────────────────────────────────
# ORDER MANAGEMENT
# ─────────────────────────────────────────────

@restaurant_bp.route('/orders')
@restaurant_required
def orders():
    rest   = _get_restaurant(session['user_id'])
    status = request.args.get('status', 'placed')
    all_orders = execute_query(
        """SELECT o.*, u.name AS customer_name, u.phone AS customer_phone,
                  a.address AS delivery_address
           FROM orders o JOIN users u ON o.user_id=u.id
           LEFT JOIN addresses a ON o.address_id=a.id
           WHERE o.restaurant_id=%s AND o.order_status=%s
           ORDER BY o.created_at DESC""",
        (rest['id'], status), fetchall=True
    )
    # Get counts per status for tabs
    status_counts = {}
    for s in ['placed','confirmed','preparing','ready','delivered','cancelled']:
        r = execute_query(
            "SELECT COUNT(*) AS c FROM orders WHERE restaurant_id=%s AND order_status=%s",
            (rest['id'], s), fetchone=True
        )
        status_counts[s] = r['c']

    return render_template('restaurant/orders.html',
                           orders=all_orders, restaurant=rest,
                           current_status=status, status_counts=status_counts)


@restaurant_bp.route('/orders/<int:order_id>')
@restaurant_required
def order_detail(order_id):
    rest = _get_restaurant(session['user_id'])
    order = execute_query(
        """SELECT o.*, u.name AS customer_name, u.phone AS customer_phone,
                  a.address AS delivery_address
           FROM orders o JOIN users u ON o.user_id=u.id
           LEFT JOIN addresses a ON o.address_id=a.id
           WHERE o.id=%s AND o.restaurant_id=%s""",
        (order_id, rest['id']), fetchone=True
    )
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('restaurant.orders'))
    items = execute_query(
        """SELECT oi.*, fi.name, fi.image, fi.veg_type
           FROM order_items oi JOIN food_items fi ON oi.food_item_id=fi.id
           WHERE oi.order_id=%s""",
        (order_id,), fetchall=True
    )
    return render_template('restaurant/order_detail.html',
                           order=order, items=items, restaurant=rest)


# ─────────────────────────────────────────────
# SALES SUMMARY
# ─────────────────────────────────────────────

@restaurant_bp.route('/sales')
@restaurant_required
def sales():
    rest = _get_restaurant(session['user_id'])
    daily = execute_query(
        """SELECT DATE(created_at) AS day,
                  COUNT(*) AS order_count,
                  SUM(total_amount) AS revenue
           FROM orders WHERE restaurant_id=%s AND order_status='delivered'
           GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30""",
        (rest['id'],), fetchall=True
    )
    total_revenue = execute_query(
        "SELECT COALESCE(SUM(total_amount),0) AS t FROM orders "
        "WHERE restaurant_id=%s AND order_status='delivered'",
        (rest['id'],), fetchone=True
    )['t']
    top_items = execute_query(
        """SELECT fi.name, SUM(oi.quantity) AS total_qty, SUM(oi.subtotal) AS total_revenue
           FROM order_items oi
           JOIN food_items fi ON oi.food_item_id=fi.id
           JOIN orders o ON oi.order_id=o.id
           WHERE o.restaurant_id=%s AND o.order_status='delivered'
           GROUP BY fi.id, fi.name ORDER BY total_qty DESC LIMIT 10""",
        (rest['id'],), fetchall=True
    )
    return render_template('restaurant/sales.html',
                           restaurant=rest, daily=daily,
                           total_revenue=total_revenue, top_items=top_items)


# ─────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────

@restaurant_bp.route('/reviews')
@restaurant_required
def reviews():
    rest = _get_restaurant(session['user_id'])
    all_reviews = execute_query(
        """SELECT rv.*, u.name AS customer_name
           FROM reviews rv JOIN users u ON rv.user_id=u.id
           WHERE rv.restaurant_id=%s ORDER BY rv.created_at DESC""",
        (rest['id'],), fetchall=True
    )
    return render_template('restaurant/reviews.html',
                           restaurant=rest, reviews=all_reviews)


# ─────────────────────────────────────────────
# KITCHEN ORDER STATUS UPDATE & DISPATCH
# ─────────────────────────────────────────────

@restaurant_bp.route('/order/update-status', methods=['POST'])
@restaurant_required
def update_order_status():
    rest = _get_restaurant(session['user_id'])
    order_id = request.form.get('order_id')
    new_status = request.form.get('status')

    order = execute_query(
        "SELECT * FROM orders WHERE id=%s AND restaurant_id=%s",
        (order_id, rest['id']), fetchone=True
    )
    if not order:
        flash('Order not found or permission denied.', 'danger')
        return redirect(url_for('restaurant.orders'))

    allowed_statuses = ['confirmed', 'preparing', 'ready', 'ready_for_pickup', 'cancelled', 'rejected']
    if new_status not in allowed_statuses:
        flash('Invalid status update.', 'danger')
        return redirect(request.referrer or url_for('restaurant.orders'))

    db_status = 'ready_for_pickup' if new_status in ['ready', 'ready_for_pickup'] else new_status
    execute_query("UPDATE orders SET order_status=%s, updated_at=NOW() WHERE id=%s", (db_status, order_id), commit=True)

    status_messages = {
        'confirmed': 'Order Confirmed by restaurant kitchen.',
        'preparing': 'Chef is cooking your fresh dishes.',
        'ready_for_pickup': 'Food is packed and ready for delivery partner pickup.',
        'ready': 'Food is packed and ready for delivery partner pickup.',
        'rejected': 'Order could not be accepted by restaurant.',
        'cancelled': 'Order has been cancelled by restaurant.',
    }
    if new_status in status_messages:
        try:
            execute_query(
                "INSERT INTO notifications (user_id, role, title, message) VALUES (%s, 'customer', %s, %s)",
                (order['user_id'], f"Order #{order['order_code']} Update", status_messages[new_status]),
                commit=True
            )
        except Exception:
            pass

    # When order is ready for pickup, dispatch to an available delivery partner
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
                execute_query(
                    "INSERT INTO notifications (user_id, role, title, message) VALUES (%s, 'delivery', 'New Delivery Assigned! 🛵', CONCAT('Order #', %s, ' is ready for pickup.'))",
                    (partner['user_id'], order['order_code']), commit=True
                )

    flash(f"Order #{order['order_code']} updated to {new_status.replace('_', ' ').title()}.", 'success')
    return redirect(request.referrer or url_for('restaurant.orders'))


# ─────────────────────────────────────────────
# RESTAURANT STAFF MANAGEMENT
# ─────────────────────────────────────────────

@restaurant_bp.route('/staff')
@restaurant_required
def staff():
    """View restaurant staff accounts and permissions."""
    rest = _get_restaurant(session['user_id'])
    if not rest:
        flash('Restaurant record not found.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    staff_list = execute_query(
        """SELECT s.*, u.name, u.email, u.phone, u.status AS account_status
           FROM restaurant_staff s
           JOIN users u ON s.user_id = u.id
           WHERE s.restaurant_id = %s
           ORDER BY s.created_at DESC""",
        (rest['id'],), fetchall=True
    ) or []

    pending_count = sum(1 for s in staff_list if s['status'] == 'pending')

    return render_template('restaurant/staff.html',
                           restaurant=rest,
                           staff_list=staff_list,
                           pending_count=pending_count)


@restaurant_bp.route('/staff/add', methods=['GET', 'POST'])
@restaurant_required
def add_staff():
    """Restaurant owner directly onboards a kitchen staff or manager."""
    rest = _get_restaurant(session['user_id'])
    if not rest:
        flash('Restaurant record not found.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip().lower()
        phone      = request.form.get('phone', '').strip()
        staff_role = request.form.get('staff_role', 'kitchen_staff').strip()
        shift      = request.form.get('shift', 'Full Time').strip()
        password   = request.form.get('password', '')

        errors = []
        if not name:
            errors.append('Staff name is required.')
        if not validate_email(email):
            errors.append('Valid email address required.')
        if not validate_phone(phone):
            errors.append('Valid 10-digit mobile number required.')
        if not validate_password(password):
            errors.append('Password must be at least 6 characters.')
        if staff_role not in ('kitchen_staff', 'restaurant_manager'):
            staff_role = 'kitchen_staff'

        if errors:
            for e in errors:
                flash(e, 'danger')
            return redirect(url_for('restaurant.staff'))

        existing = execute_query("SELECT id FROM users WHERE email=%s OR phone=%s", (email, phone), fetchone=True)
        if existing:
            flash('This email or phone is already registered on Foody Hunters.', 'warning')
            return redirect(url_for('restaurant.staff'))

        pw_hash = generate_password_hash(password)
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status)
               VALUES (%s, %s, %s, %s, 'staff', %s, 'Mehsana', 'Gujarat', '384001', 'active')""",
            (name, email, phone, pw_hash, f"Staff at {rest['name']}"),
            commit=True
        )

        execute_query(
            """INSERT INTO restaurant_staff (user_id, restaurant_id, staff_role, status, shift)
               VALUES (%s, %s, %s, 'approved', %s)""",
            (user_id, rest['id'], staff_role, shift),
            commit=True
        )

        flash(f"Staff member '{name}' onboarded successfully as {staff_role.replace('_', ' ').title()}.", 'success')
        return redirect(url_for('restaurant.staff'))

    return redirect(url_for('restaurant.staff'))


@restaurant_bp.route('/staff/approve/<int:staff_id>', methods=['POST'])
@restaurant_required
def approve_staff(staff_id):
    """Approve a pending staff applicant."""
    rest = _get_restaurant(session['user_id'])
    execute_query(
        "UPDATE restaurant_staff SET status='approved', updated_at=NOW() WHERE id=%s AND restaurant_id=%s",
        (staff_id, rest['id']), commit=True
    )
    flash('Staff application approved. Staff member can now login to Kitchen Operations.', 'success')
    return redirect(url_for('restaurant.staff'))


@restaurant_bp.route('/staff/reject/<int:staff_id>', methods=['POST'])
@restaurant_required
def reject_staff(staff_id):
    """Reject a pending staff applicant."""
    rest = _get_restaurant(session['user_id'])
    execute_query(
        "UPDATE restaurant_staff SET status='rejected', updated_at=NOW() WHERE id=%s AND restaurant_id=%s",
        (staff_id, rest['id']), commit=True
    )
    flash('Staff application rejected.', 'info')
    return redirect(url_for('restaurant.staff'))


@restaurant_bp.route('/staff/toggle/<int:staff_id>', methods=['POST'])
@restaurant_required
def toggle_staff(staff_id):
    """Toggle staff account between active/approved and suspended."""
    rest = _get_restaurant(session['user_id'])
    rec = execute_query("SELECT status FROM restaurant_staff WHERE id=%s AND restaurant_id=%s", (staff_id, rest['id']), fetchone=True)
    if rec:
        new_status = 'suspended' if rec['status'] == 'approved' else 'approved'
        execute_query("UPDATE restaurant_staff SET status=%s, updated_at=NOW() WHERE id=%s AND restaurant_id=%s",
                      (new_status, staff_id, rest['id']), commit=True)
        flash(f"Staff member marked as {new_status.title()}.", 'success')
    return redirect(url_for('restaurant.staff'))


@restaurant_bp.route('/staff/delete/<int:staff_id>', methods=['POST'])
@restaurant_required
def delete_staff(staff_id):
    """Remove a staff member from the restaurant."""
    rest = _get_restaurant(session['user_id'])
    rec = execute_query("SELECT user_id FROM restaurant_staff WHERE id=%s AND restaurant_id=%s", (staff_id, rest['id']), fetchone=True)
    if rec:
        execute_query("DELETE FROM restaurant_staff WHERE id=%s AND restaurant_id=%s", (staff_id, rest['id']), commit=True)
        execute_query("DELETE FROM users WHERE id=%s AND role='staff'", (rec['user_id'],), commit=True)
        flash('Staff record deleted.', 'success')
    return redirect(url_for('restaurant.staff'))


