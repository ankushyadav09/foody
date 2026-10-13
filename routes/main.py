"""
routes/main.py – Public-facing routes for Foody Hunters
Home, Restaurants, Search, Restaurant Details, etc.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from database import execute_query

main_bp = Blueprint('main', __name__)


# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────

@main_bp.route('/')
def index():
    """Home page – shows hero, categories, top restaurants, popular foods."""
    categories = execute_query(
        "SELECT * FROM food_categories ORDER BY sort_order ASC LIMIT 12",
        fetchall=True
    )
    top_restaurants = execute_query(
        """SELECT * FROM restaurants 
           WHERE (verification_status='approved' OR verification_status IS NULL) 
             AND (status='active' OR status='approved')
           ORDER BY rating DESC LIMIT 8""",
        fetchall=True
    )
    popular_foods = execute_query(
        """SELECT fi.*, r.name AS restaurant_name, r.delivery_time
           FROM food_items fi
           JOIN restaurants r ON fi.restaurant_id = r.id
           WHERE fi.availability=1 
             AND (r.verification_status='approved' OR r.verification_status IS NULL) 
             AND (r.status='active' OR r.status='approved')
           ORDER BY fi.rating DESC LIMIT 8""",
        fetchall=True
    )
    reviews = execute_query(
        """SELECT rv.*, u.name AS user_name
           FROM reviews rv
           JOIN users u ON rv.user_id = u.id
           ORDER BY rv.created_at DESC LIMIT 6""",
        fetchall=True
    )
    return render_template('index.html',
                           categories=categories,
                           top_restaurants=top_restaurants,
                           popular_foods=popular_foods,
                           reviews=reviews)


# ─────────────────────────────────────────────
# RESTAURANT LISTING
# ─────────────────────────────────────────────

@main_bp.route('/restaurants')
def restaurants():
    """Restaurant listing page with search, filter, sort."""
    query_str   = request.args.get('q', '').strip()
    cuisine     = request.args.get('cuisine', '').strip()
    sort        = request.args.get('sort', 'recommended')
    veg_filter  = request.args.get('veg', '')
    min_rating  = request.args.get('rating', '')
    offers_only = request.args.get('offers', '')

    sql = """SELECT r.*, 
             (SELECT COUNT(*) FROM food_items fi WHERE fi.restaurant_id=r.id) AS menu_count
             FROM restaurants r 
             WHERE (r.verification_status='approved' OR r.verification_status IS NULL) 
               AND (r.status='active' OR r.status='approved')"""
    params = []

    if query_str:
        sql += " AND (r.name LIKE %s OR r.cuisine LIKE %s OR r.description LIKE %s)"
        like = f"%{query_str}%"
        params.extend([like, like, like])
    if cuisine:
        sql += " AND r.cuisine LIKE %s"
        params.append(f"%{cuisine}%")
    if min_rating:
        sql += " AND r.rating >= %s"
        params.append(float(min_rating))

    order_map = {
        'recommended': 'r.rating DESC',
        'rating':      'r.rating DESC',
        'delivery':    'r.delivery_time ASC',
        'price_low':   'r.delivery_fee ASC',
        'price_high':  'r.delivery_fee DESC',
    }
    sql += f" ORDER BY {order_map.get(sort, 'r.rating DESC')}"

    restaurants_list = execute_query(sql, tuple(params), fetchall=True)

    # Get all distinct cuisines for filter dropdown
    cuisines = execute_query(
        """SELECT DISTINCT cuisine FROM restaurants 
           WHERE (verification_status='approved' OR verification_status IS NULL) 
             AND (status='active' OR status='approved') 
           ORDER BY cuisine""",
        fetchall=True
    )
    return render_template('restaurants.html',
                           restaurants=restaurants_list,
                           cuisines=cuisines,
                           query_str=query_str,
                           selected_cuisine=cuisine,
                           sort=sort)


# ─────────────────────────────────────────────
# RESTAURANT DETAIL + MENU
# ─────────────────────────────────────────────

@main_bp.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    """Show restaurant details and categorized menu."""
    restaurant = execute_query(
        """SELECT * FROM restaurants 
           WHERE id=%s 
             AND (verification_status='approved' OR verification_status IS NULL) 
             AND (status='active' OR status='approved')""",
        (restaurant_id,), fetchone=True
    )
    if not restaurant:
        return render_template('errors/404.html'), 404

    # Get menu grouped by category
    categories = execute_query(
        """SELECT DISTINCT fc.id, fc.name, fc.icon
           FROM food_items fi
           JOIN food_categories fc ON fi.category_id = fc.id
           WHERE fi.restaurant_id=%s AND fi.availability=1
           ORDER BY fc.name""",
        (restaurant_id,), fetchall=True
    )
    menu = {}
    for cat in categories:
        items = execute_query(
            """SELECT * FROM food_items
               WHERE restaurant_id=%s AND category_id=%s AND availability=1
               ORDER BY name""",
            (restaurant_id, cat['id']), fetchall=True
        )
        menu[cat['name']] = {'icon': cat['icon'], 'items': items}

    reviews = execute_query(
        """SELECT rv.*, u.name AS user_name
           FROM reviews rv JOIN users u ON rv.user_id=u.id
           WHERE rv.restaurant_id=%s ORDER BY rv.created_at DESC LIMIT 10""",
        (restaurant_id,), fetchall=True
    )
    return render_template('restaurant_detail.html',
                           restaurant=restaurant,
                           menu=menu,
                           reviews=reviews)


# ─────────────────────────────────────────────
# SEARCH (AJAX endpoint)
# ─────────────────────────────────────────────

@main_bp.route('/search')
def search():
    """Search restaurants and food items."""
    q = request.args.get('q', '').strip()
    if not q:
        return render_template('search_results.html', results=[], query='')

    like = f"%{q}%"
    restaurants_r = execute_query(
        """SELECT *, 'restaurant' AS result_type FROM restaurants 
           WHERE (verification_status='approved' OR verification_status IS NULL) 
             AND (status='active' OR status='approved')
             AND (name LIKE %s OR cuisine LIKE %s OR description LIKE %s) LIMIT 10""",
        (like, like, like), fetchall=True
    )
    foods_r = execute_query(
        """SELECT fi.*, r.name AS restaurant_name, r.id AS restaurant_id,
                  'food' AS result_type
           FROM food_items fi JOIN restaurants r ON fi.restaurant_id=r.id
           WHERE fi.availability=1 
             AND (r.verification_status='approved' OR r.verification_status IS NULL) 
             AND (r.status='active' OR r.status='approved')
             AND (fi.name LIKE %s OR fi.description LIKE %s) LIMIT 10""",
        (like, like), fetchall=True
    )
    return render_template('search_results.html',
                           restaurants=restaurants_r,
                           foods=foods_r,
                           query=q)


# ─────────────────────────────────────────────
# STATIC PAGES
# ─────────────────────────────────────────────

@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Store complaint/contact
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        if name and email and message:
            execute_query(
                "INSERT INTO complaints (name, email, message, status) VALUES (%s,%s,%s,'open')",
                (name, email, message), commit=True
            )
            from flask import flash
            flash('Your message has been sent! We will get back to you soon.', 'success')
    return render_template('contact.html')


@main_bp.route('/offers')
def offers():
    coupons = execute_query(
        "SELECT * FROM coupons WHERE is_active=1 ORDER BY discount_value DESC",
        fetchall=True
    )
    return render_template('offers.html', coupons=coupons)


# ─────────────────────────────────────────────
# UNIFIED OPERATIONS CENTER ENTRY
# ─────────────────────────────────────────────

@main_bp.route('/ops')
def operations_center():
    """
    Unified entry point for Foody Hunters Operations Center.
    Directs authorized operational staff (admin, restaurant, delivery)
    to their designated control deck, while strictly denying customers.
    """
    if 'user_id' not in session:
        flash('Please login with your staff or partner credentials to access the Operations Center.', 'info')
        return redirect(url_for('auth.login', next=url_for('main.operations_center')))

    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'restaurant':
        return redirect(url_for('restaurant.dashboard'))
    elif role == 'delivery':
        return redirect(url_for('delivery.dashboard'))
    else:
        # Customer or unrecognized role attempting internal operations access
        flash('Access Denied: The Operations Center is strictly reserved for authorized operating personnel.', 'danger')
        return redirect(url_for('main.index'))

