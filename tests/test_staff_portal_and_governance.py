"""
tests/test_staff_portal_and_governance.py
Comprehensive test suite verifying the permanent retirement of Hotel / Restaurant Staff:
1. No active Staff portal links are displayed in public templates (navbar, footer, /portals).
2. Staff login (/staff/login) and registration (/staff/register) entry points are retired.
3. Obsolete Staff portal routes (/staff/dashboard, /staff/orders, /staff/menu, /staff/profile) redirect safely.
4. Staff POST action endpoints are retired.
5. Legacy staff credentials submitted on /auth/login redirect to /portals with retirement notice.
6. Admin operations remain active and protected through authorized admin routes.
7. Delivery partner operations remain active and protected through authorized delivery routes.
8. Existing restaurant records, dishes, and orders in the database remain intact.
"""

import os
import random
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from werkzeug.security import generate_password_hash


class TestStaffPortalRetirement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.client = self.app.test_client()

    def test_01_staff_public_links_absent(self):
        """1. Verify no active Staff portal links are displayed in customer or partner templates."""
        # Check Home page
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        home_html = res_home.get_data(as_text=True)
        self.assertNotIn('/staff/login', home_html)
        self.assertNotIn('/staff/register', home_html)
        self.assertNotIn('Kitchen Staff Login', home_html)

        # Check /portals page
        res_portals = self.client.get('/portals')
        self.assertEqual(res_portals.status_code, 200)
        portals_html = res_portals.get_data(as_text=True)
        self.assertNotIn('portalCardStaff', portals_html)
        self.assertNotIn('Hotel / Restaurant Staff', portals_html)
        self.assertNotIn('/staff/login', portals_html)
        self.assertNotIn('/staff/register', portals_html)

    def test_02_staff_login_and_registration_retired(self):
        """2. Verify /staff/login and /staff/register redirect safely with retirement notice."""
        # GET /staff/login
        res_login = self.client.get('/staff/login', follow_redirects=False)
        self.assertEqual(res_login.status_code, 302)
        self.assertIn('/portals', res_login.headers.get('Location', ''))

        # Following redirect to /portals shows retirement message
        res_login_followed = self.client.get('/staff/login', follow_redirects=True)
        self.assertEqual(res_login_followed.status_code, 200)
        self.assertIn('Staff feature has been retired', res_login_followed.get_data(as_text=True))

        # GET /staff/register
        res_reg = self.client.get('/staff/register', follow_redirects=False)
        self.assertEqual(res_reg.status_code, 302)
        self.assertIn('/portals', res_reg.headers.get('Location', ''))

    def test_03_staff_dashboard_and_operations_retired(self):
        """3. Verify all operational staff endpoints redirect to /portals."""
        retired_endpoints = [
            '/staff/',
            '/staff/dashboard',
            '/staff/orders',
            '/staff/menu',
            '/staff/profile'
        ]
        for ep in retired_endpoints:
            res = self.client.get(ep, follow_redirects=False)
            self.assertEqual(res.status_code, 302, f"{ep} must return 302 redirect")
            self.assertIn('/portals', res.headers.get('Location', ''))

    def test_04_staff_post_actions_retired(self):
        """4. Verify staff POST actions are safely retired."""
        # /staff/order/update-status
        res_order = self.client.post('/staff/order/update-status', follow_redirects=False)
        self.assertEqual(res_order.status_code, 302)

        # /staff/menu/toggle-availability
        res_menu = self.client.post('/staff/menu/toggle-availability', follow_redirects=False)
        self.assertEqual(res_menu.status_code, 302)

    def test_05_legacy_staff_login_via_auth_redirects(self):
        """5. Verify legacy user with role 'staff' logging in via /auth/login is redirected to /portals."""
        uid = uuid.uuid4().hex[:6]
        email = f"legacy_staff_{uid}@foodyhunters.com"
        pw = "password123"
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, password_hash, role, status)
               VALUES (%s, %s, %s, %s, 'staff', 'active')""",
            (f"Chef {uid}", email, f"91{random.randint(10000000, 99999999)}", generate_password_hash(pw)),
            commit=True
        )

        res = self.client.post('/auth/login', data={'email': email, 'password': pw}, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/portals', res.headers.get('Location', ''))

        res_followed = self.client.post('/auth/login', data={'email': email, 'password': pw}, follow_redirects=True)
        self.assertIn('Staff portal has been retired', res_followed.get_data(as_text=True))

    def test_06_admin_operations_intact(self):
        """6. Verify Admin operations remain available through authorized admin routes."""
        with self.client.session_transaction() as sess:
            sess['admin_gate_passed'] = True
            sess['role'] = 'admin'
            admin = execute_query("SELECT id, name, email FROM users WHERE role='admin' LIMIT 1", fetchone=True)
            if admin:
                sess['user_id'] = admin['id']
                sess['user_name'] = admin['name']
                sess['user_email'] = admin['email']
            else:
                sess['user_id'] = 1
                sess['user_name'] = 'Administrator'
                sess['user_email'] = 'admin@foodyhunters.com'

        # Admin dashboard loads
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # Admin restaurant management loads
        res_rest = self.client.get('/admin/restaurants')
        self.assertEqual(res_rest.status_code, 200)

    def test_07_delivery_partner_operations_intact(self):
        """7. Verify Delivery Partner operations remain available through authorized delivery routes."""
        # Delivery login page loads
        res_login = self.client.get('/delivery/login')
        self.assertEqual(res_login.status_code, 200)

        # Delivery register page loads
        res_reg = self.client.get('/delivery/register')
        self.assertEqual(res_reg.status_code, 200)

    def test_08_existing_restaurant_records_and_dishes_intact(self):
        """8. Verify existing restaurant and menu records remain non-destructively preserved."""
        rest_count = execute_query("SELECT COUNT(*) AS c FROM restaurants", fetchone=True)
        self.assertGreater(rest_count['c'], 0)

        dish_count = execute_query("SELECT COUNT(*) AS c FROM food_items", fetchone=True)
        self.assertGreater(dish_count['c'], 0)


if __name__ == '__main__':
    unittest.main()
