


"""
app.py – Main Flask application entry point for Foody Hunters
Online Food Delivery System

Run:
    python app.py

Requirements:
    pip install -r requirements.txt
    XAMPP MySQL must be running with foody_hunters database imported.
"""

from flask import Flask, render_template, session
from config import Config
import os

# ── Blueprint imports ─────────────────────────────────────────────────────────
from routes.auth import auth_bp
from routes.main import main_bp
from routes.customer import customer_bp
from routes.restaurant import restaurant_bp
from routes.delivery import delivery_bp
from routes.admin import admin_bp
from routes.api import api_bp


def create_app():
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Register Blueprints ───────────────────────────────────────────────────
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(restaurant_bp, url_prefix='/restaurant')
    app.register_blueprint(delivery_bp, url_prefix='/delivery')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # ── Context Processors ────────────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        """Inject commonly needed variables into all templates."""
        cart_count = 0
        if 'user_id' in session and session.get('role') == 'customer':
            try:
                from database import execute_query
                result = execute_query(
                    "SELECT SUM(quantity) as total FROM cart_items "
                    "WHERE cart_id IN (SELECT id FROM cart WHERE user_id=%s AND status='active')",
                    (session['user_id'],),
                    fetchone=True
                )
                cart_count = int(result['total']) if result and result['total'] else 0
            except Exception:
                cart_count = 0
        return {
            'cart_count': cart_count,
            'current_user': session.get('user_name', ''),
            'current_role': session.get('role', ''),
            'current_user_id': session.get('user_id', None),
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


app = create_app()

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("  FOODY HUNTERS - Online Food Delivery System")
    print("=" * 60)
    print("  Server running at: http://127.0.0.1:5000")
    print("  Admin Panel:       http://127.0.0.1:5000/admin")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
