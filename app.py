


"""
app.py – Main Flask application entry point for Foody Hunters
Online Food Delivery System

Run:
    python app.py

Requirements:
    pip install -r requirements.txt
    XAMPP MySQL must be running with foody_hunters database imported.
"""

from flask import Flask, render_template, session, request
from config import Config
from werkzeug.middleware.proxy_fix import ProxyFix
import os

# ── Blueprint imports ─────────────────────────────────────────────────────────
from routes.auth import auth_bp
from routes.main import main_bp
from routes.customer import customer_bp
from routes.restaurant import restaurant_bp
from routes.delivery import delivery_bp
from routes.admin import admin_bp
from routes.staff import staff_bp
from routes.api import api_bp
from utils.helpers import get_role_display_name


def create_app():
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Respect reverse proxy & tunnel headers (Cloudflare Quick Tunnel, etc.)
    # Ensures request.scheme is https and request.host reflects the public tunnel domain
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Register Blueprints ───────────────────────────────────────────────────
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(restaurant_bp, url_prefix='/restaurant')
    app.register_blueprint(delivery_bp, url_prefix='/delivery')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(api_bp, url_prefix='/api')

    # ── Role-Scoped Session Resolution Hook ──────────────────────────────────
    @app.before_request
    def resolve_portal_session_context():
        """
        Enforce strict isolation between the five portal authentication contexts:
        Customer, Admin, Restaurant Owner, Delivery Partner, Kitchen Staff.
        Ensures that authenticating or operating within one portal never leaks
        into, overwrites, or alters navigation/redirects of another portal.
        """
        path = request.path

        # If visiting admin login desk without an active admin user identity, clear admin_auth
        if path == '/admin/login':
            if 'user_id' not in session or session.get('role') != 'admin':
                session.pop('admin_auth', None)

        if 'role' in session and 'user_id' in session:
            legacy_role = session.get('role')
            auth_key = f"{legacy_role}_auth"
            # If the session has a legacy non-admin role directly set without its auth namespace,
            # or with a different user_id, this represents a direct session mock (e.g. test setting sess['role'] = 'staff')
            # Clear any conflicting admin_auth from earlier in the same client session!
            is_mock_session = auth_key not in session or session[auth_key].get('user_id') != session.get('user_id')
            if legacy_role != 'admin' and is_mock_session:
                session.pop('admin_auth', None)
                session.pop('admin_gate_passed', None)
            if is_mock_session:
                session[auth_key] = {
                    'user_id': session.get('user_id'),
                    'user_name': session.get('user_name', ''),
                    'user_email': session.get('user_email', ''),
                    'role': legacy_role,
                    'restaurant_id': session.get('restaurant_id'),
                    'staff_role': session.get('staff_role')
                }

        path = request.path

        if path.startswith('/admin'):
            admin_auth = session.get('admin_auth')
            if admin_auth and isinstance(admin_auth, dict) and admin_auth.get('role') == 'admin':
                if session.get('role') in ('staff', 'restaurant', 'delivery'):
                    pass
                else:
                    session['user_id'] = admin_auth['user_id']
                    session['user_name'] = admin_auth.get('user_name', 'Administrator')
                    session['user_email'] = admin_auth.get('user_email', '')
                    session['role'] = 'admin'

        elif path.startswith('/restaurant') and not path.startswith(('/restaurant/view', '/restaurant/review')):
            rest_auth = session.get('restaurant_auth')
            if rest_auth and isinstance(rest_auth, dict) and rest_auth.get('role') == 'restaurant':
                if session.get('role') in ('staff', 'delivery', 'customer'):
                    pass
                else:
                    session['user_id'] = rest_auth['user_id']
                    session['user_name'] = rest_auth.get('user_name', '')
                    session['user_email'] = rest_auth.get('user_email', '')
                    session['role'] = 'restaurant'
                    if rest_auth.get('restaurant_id'):
                        session['restaurant_id'] = rest_auth.get('restaurant_id')

        elif path.startswith('/delivery'):
            deliv_auth = session.get('delivery_auth')
            if deliv_auth and isinstance(deliv_auth, dict) and deliv_auth.get('role') == 'delivery':
                if session.get('role') in ('staff', 'restaurant', 'customer'):
                    pass
                else:
                    session['user_id'] = deliv_auth['user_id']
                    session['user_name'] = deliv_auth.get('user_name', '')
                    session['user_email'] = deliv_auth.get('user_email', '')
                    session['role'] = 'delivery'

        elif path.startswith('/staff'):
            staff_auth = session.get('staff_auth')
            if staff_auth and isinstance(staff_auth, dict) and staff_auth.get('role') == 'staff':
                if session.get('role') in ('restaurant', 'delivery', 'customer'):
                    pass
                else:
                    session['user_id'] = staff_auth['user_id']
                    session['user_name'] = staff_auth.get('user_name', '')
                    session['user_email'] = staff_auth.get('user_email', '')
                    session['role'] = 'staff'
                    if staff_auth.get('restaurant_id'):
                        session['restaurant_id'] = staff_auth.get('restaurant_id')
                    if staff_role := staff_auth.get('staff_role'):
                        session['staff_role'] = staff_role

        elif path.startswith('/customer') or path.startswith('/auth') or path in ('/', '/portals', '/restaurants', '/offers', '/about', '/contact', '/search') or path.startswith(('/restaurant/view', '/restaurant/review')):
            cust_auth = session.get('customer_auth')
            if cust_auth and isinstance(cust_auth, dict) and cust_auth.get('role') == 'customer':
                session['user_id'] = cust_auth['user_id']
                session['user_name'] = cust_auth.get('user_name', '')
                session['user_email'] = cust_auth.get('user_email', '')
                session['role'] = 'customer'
            elif session.get('role') in ('admin', 'restaurant', 'delivery', 'staff'):
                # Customer views must never reflect an active admin or partner session
                session.pop('user_id', None)
                session.pop('role', None)
                session.pop('user_name', None)
                session.pop('user_email', None)

        elif path.startswith('/api'):
            # Determine preferred auth namespace based on sub-path to preserve portal isolation
            if path.startswith('/api/delivery'):
                preferred_keys = ('delivery_auth', 'admin_auth', 'restaurant_auth', 'customer_auth')
            elif path.startswith('/api/restaurant'):
                preferred_keys = ('restaurant_auth', 'staff_auth', 'admin_auth', 'customer_auth')
            elif path.startswith('/api/staff'):
                preferred_keys = ('staff_auth', 'restaurant_auth', 'admin_auth')
            elif path.startswith('/api/admin'):
                preferred_keys = ('admin_auth',)
            else:
                preferred_keys = ('customer_auth', 'delivery_auth', 'restaurant_auth', 'admin_auth')

            matched_auth = None
            for auth_key in preferred_keys:
                auth_val = session.get(auth_key)
                if auth_val and isinstance(auth_val, dict) and auth_val.get('user_id'):
                    matched_auth = auth_val
                    break

            if matched_auth:
                session['user_id'] = matched_auth.get('user_id')
                session['role'] = matched_auth.get('role', 'customer')
                session['user_name'] = matched_auth.get('user_name', '')
                session['user_email'] = matched_auth.get('user_email', '')
                if matched_auth.get('restaurant_id'):
                    session['restaurant_id'] = matched_auth.get('restaurant_id')
                if matched_auth.get('staff_role'):
                    session['staff_role'] = matched_auth.get('staff_role')

    # ── Context Processors ────────────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        """Inject commonly needed variables into all templates."""
        path = request.path if request else ''

        # 1. Customer Context for storefront navigation
        customer_auth = session.get('customer_auth')
        if not customer_auth and session.get('role') == 'customer' and session.get('user_id'):
            customer_auth = {
                'user_id': session.get('user_id'),
                'user_name': session.get('user_name', 'Customer'),
                'user_email': session.get('user_email', ''),
                'role': 'customer'
            }

        cart_count = 0
        if customer_auth:
            try:
                from database import execute_query
                result = execute_query(
                    "SELECT SUM(quantity) as total FROM cart_items "
                    "WHERE cart_id IN (SELECT id FROM cart WHERE user_id=%s AND status='active')",
                    (customer_auth['user_id'],),
                    fetchone=True
                )
                cart_count = int(result['total']) if result and result['total'] else 0
            except Exception:
                cart_count = 0

        # 2. Ops Context (Admin, Restaurant, Delivery, Staff)
        ops_role = None
        ops_user_name = None
        ops_logout_url = '/auth/logout'

        if path.startswith('/admin'):
            admin_auth = session.get('admin_auth') or ({'role': 'admin', 'user_name': session.get('user_name')} if session.get('role') == 'admin' else None)
            if admin_auth:
                ops_role = 'admin'
                ops_user_name = admin_auth.get('user_name') or 'Administrator'
                ops_logout_url = '/admin/logout'
        elif path.startswith('/restaurant') and not path.startswith(('/restaurant/view', '/restaurant/review')):
            rest_auth = session.get('restaurant_auth') or ({'role': 'restaurant', 'user_name': session.get('user_name')} if session.get('role') == 'restaurant' else None)
            if rest_auth:
                ops_role = 'restaurant'
                ops_user_name = rest_auth.get('user_name') or 'Restaurant Partner'
                ops_logout_url = '/restaurant/logout'
        elif path.startswith('/delivery'):
            deliv_auth = session.get('delivery_auth') or ({'role': 'delivery', 'user_name': session.get('user_name')} if session.get('role') == 'delivery' else None)
            if deliv_auth:
                ops_role = 'delivery'
                ops_user_name = deliv_auth.get('user_name') or 'Delivery Partner'
                ops_logout_url = '/delivery/logout'
        elif path.startswith('/staff'):
            st_auth = session.get('staff_auth') or ({'role': 'staff', 'user_name': session.get('user_name')} if session.get('role') == 'staff' else None)
            if st_auth:
                ops_role = 'staff'
                ops_user_name = st_auth.get('user_name') or 'Kitchen Staff'
                ops_logout_url = '/staff/logout'
        elif session.get('role') in ('admin', 'restaurant', 'delivery', 'staff'):
            ops_role = session.get('role')
            ops_user_name = session.get('user_name')
            if ops_role == 'admin':
                ops_logout_url = '/admin/logout'
            elif ops_role == 'restaurant':
                ops_logout_url = '/restaurant/logout'
            elif ops_role == 'delivery':
                ops_logout_url = '/delivery/logout'
            elif ops_role == 'staff':
                ops_logout_url = '/staff/logout'

        is_ops_route = path.startswith(('/admin', '/restaurant', '/delivery', '/staff', '/ops', '/operations')) and not path.startswith(('/restaurant/view', '/restaurant/review'))
        if is_ops_route and ops_role:
            cur_role = ops_role
            cur_user = ops_user_name or session.get('user_name', '')
            cur_uid = session.get('user_id')
        elif customer_auth:
            cur_role = 'customer'
            cur_user = customer_auth.get('user_name', '')
            cur_uid = customer_auth.get('user_id')
        else:
            cur_role = ''
            cur_user = ''
            cur_uid = None

        cur_role_display = get_role_display_name(cur_role, session.get('staff_role'))
        ops_role_display = get_role_display_name(ops_role or session.get('role'), session.get('staff_role'))

        return {
            'cart_count': cart_count,
            'customer_auth': customer_auth,
            'current_user': cur_user,
            'current_role': cur_role,
            'current_role_display': cur_role_display,
            'current_user_id': cur_uid,
            'current_restaurant_id': session.get('restaurant_id', None),
            'current_staff_role': session.get('staff_role', None),
            'ops_role': ops_role or session.get('role'),
            'ops_role_display': ops_role_display,
            'ops_user_name': ops_user_name or session.get('user_name'),
            'ops_logout_url': ops_logout_url,
            'get_role_display_name': get_role_display_name,
        }

    # ── Error Handlers ────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    return app


def _get_lan_ip():
    """Retrieve active local IPv4 address for Wi-Fi / LAN connection."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = '127.0.0.1'
    finally:
        s.close()
    return ip


app = create_app()

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Configurable HOST (default: 127.0.0.1) and PORT (default: 5000)
    host = os.environ.get('HOST', '127.0.0.1').strip()
    try:
        port = int(os.environ.get('PORT', 5000))
    except (ValueError, TypeError):
        port = 5000

    # Configurable FLASK_DEBUG (default: 0)
    flask_debug_env = os.environ.get('FLASK_DEBUG', '0').strip().lower()
    debug = flask_debug_env in ('1', 'true', 'yes')

    # Security: Set debug mode off by default when using network access (0.0.0.0)
    if host == '0.0.0.0' and flask_debug_env not in ('1', 'true', 'yes'):
        debug = False

    lan_ip = _get_lan_ip()

    print("=" * 66)
    print("  FOODY HUNTERS - Online Food Delivery System")
    print("=" * 66)
    if host == '0.0.0.0':
        print(f"  1. USER / CUSTOMER WEBSITE:  http://127.0.0.1:{port}/")
        print(f"  2. ADMIN CONTROL CENTER:     http://127.0.0.1:{port}/admin")
        print(f"  3. DELIVERY PARTNER PORTAL:  http://127.0.0.1:{port}/delivery/portal")
        print(f"  Mobile Phone (Wi-Fi):        http://{lan_ip}:{port}/")
        print(f"  Network Mode:                OPEN TO LOCAL WI-FI (0.0.0.0:{port})")
        print(f"  Debug Mode:                  {'ON' if debug else 'OFF (Safe for Local Network)'}")
        if debug:
            print("  [SECURITY NOTICE] Flask debugger is ON. Turn off on public Wi-Fi.")
    else:
        print(f"  1. USER / CUSTOMER WEBSITE:  http://{host}:{port}/")
        print(f"  2. ADMIN CONTROL CENTER:     http://{host}:{port}/admin")
        print(f"  3. DELIVERY PARTNER PORTAL:  http://{host}:{port}/delivery/portal")
        print(f"  Network Mode:                LOCAL / TUNNEL READY ({host}:{port})")
        print(f"  Debug Mode:                  {'ON' if debug else 'OFF (Safe for Demo/Tunnel)'}")
        print(f"  Public Tunnel:               Run .\\scripts\\start_public_tunnel.ps1 in Terminal 2")
    print("=" * 66)

    app.run(host=host, port=port, debug=debug)

