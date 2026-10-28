"""
routes/staff.py – Hotel / Restaurant Staff Feature (Permanently Retired)
In accordance with system requirements, the separate Hotel / Restaurant Staff portal has
been retired from active service. Kitchen and menu operations are managed directly by
authorized Restaurant Owners through the Restaurant Owner Portal.
All endpoints safely redirect to the Restaurant Owner Partner Portal (/portals).
"""

from flask import Blueprint, request, redirect, url_for, flash, jsonify
from utils.helpers import clear_staff_auth

staff_bp = Blueprint('staff', __name__)

RETIRED_MSG = "The Hotel / Restaurant Staff feature has been retired from the active platform. Kitchen and restaurant operations are managed directly by Restaurant Owners."


def _retire_redirect():
    clear_staff_auth()
    flash(RETIRED_MSG, "info")
    return redirect(url_for('main.portals'))


@staff_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Retired Staff login endpoint."""
    return _retire_redirect()


@staff_bp.route('/logout')
def logout():
    """Clear staff session and redirect to partner portal."""
    clear_staff_auth()
    return redirect(url_for('main.portals'))


@staff_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Retired Staff registration endpoint."""
    return _retire_redirect()


@staff_bp.route('/')
@staff_bp.route('/dashboard')
def dashboard():
    """Retired Staff dashboard endpoint."""
    return _retire_redirect()


@staff_bp.route('/orders')
def orders():
    """Retired Staff orders queue endpoint."""
    return _retire_redirect()


@staff_bp.route('/order/update-status', methods=['POST'])
def update_order_status():
    """Retired Staff order status update endpoint."""
    if request.is_json:
        return jsonify({'success': False, 'message': RETIRED_MSG, 'retired': True}), 410
    return _retire_redirect()


@staff_bp.route('/menu')
def menu():
    """Retired Staff menu endpoint."""
    return _retire_redirect()


@staff_bp.route('/menu/toggle-availability', methods=['POST'])
def toggle_availability():
    """Retired Staff toggle availability endpoint."""
    if request.is_json:
        return jsonify({'success': False, 'message': RETIRED_MSG, 'retired': True}), 410
    return _retire_redirect()


@staff_bp.route('/profile')
def profile():
    """Retired Staff profile endpoint."""
    return _retire_redirect()
