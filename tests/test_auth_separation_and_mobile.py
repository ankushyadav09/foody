"""
test_auth_separation_and_mobile.py
Automated test suite verifying:
1. Strict separation of customer auth from restaurant, delivery, and admin portals
2. Server-side role enforcement (customer registration cannot be hijacked with role=admin)
3. Dedicated login and registration endpoints for all 3 partner roles
4. Viewport meta tags, mobile nav drawer markup, and tunnel compatibility (no hardcoded localhost)
"""

import sys
import os
import unittest
import random
from werkzeug.security import check_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query

class TestAuthSeparationAndMobile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_01_customer_login_page_has_no_role_tabs_and_has_viewport(self):
        """Verify /auth/login is strictly customer-facing with no role tabs."""
        res = self.client.get('/auth/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Must have viewport meta tag for mobile
        self.assertIn('name="viewport"', html)

        # Must NOT have role selection tabs
        self.assertNotIn('role-tabs-wrap', html)
        self.assertNotIn('data-role="restaurant"', html)
        self.assertNotIn('data-role="delivery"', html)

        # Must have customer login form fields
        self.assertIn('action="/auth/login"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="password"', html)
        self.assertIn("togglePassword('password'", html)

    def test_02_customer_register_page_has_no_role_tabs_and_pure_customer_fields(self):
        """Verify /auth/register is strictly customer-facing."""
        res = self.client.get('/auth/register')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Must have viewport meta tag
        self.assertIn('name="viewport"', html)

        # Must NOT have role selection tabs
        self.assertNotIn('role-tabs-wrap', html)
        self.assertNotIn('role-tab-btn', html)
        self.assertNotIn('data-role="restaurant"', html)

        # Must NOT have partner onboarding fields on customer registration
        self.assertNotIn('name="restaurant_name"', html)
        self.assertNotIn('name="vehicle_type"', html)
        self.assertNotIn('name="license_number"', html)

        # Must have customer registration form
        self.assertIn('action="/auth/register"', html)
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="phone"', html)
        self.assertIn('name="address"', html)
        self.assertIn('name="password"', html)
        self.assertIn('name="confirm_password"', html)

    def test_03_customer_registration_enforces_customer_role_even_if_tampered(self):
        """Security: Browser-submitted role tampering must NEVER assign admin or partner roles."""
        rand_id = random.randint(10000, 99999)
        tamper_email = f"tamper_{rand_id}@securitytest.com"

        # Attempt to register while sending role='admin'
        res = self.client.post('/auth/register', data={
            'name': 'Malicious User',
            'email': tamper_email,
            'phone': f'91{rand_id:08d}'[:10],
            'password': 'password123',
            'confirm_password': 'password123',
            'address': 'Test Lane, Mehsana',
            'city': 'Mehsana',
            'pincode': '384002',
            'role': 'admin'  # Attacker attempts privilege escalation!
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        # Query database to confirm user was created with role='customer', NOT 'admin'
        created_user = execute_query("SELECT id, role, email FROM users WHERE email=%s", (tamper_email,), fetchone=True)
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user['role'], 'customer', "Privilege escalation vulnerability: tampered role was accepted!")

        # Clean up test record
        execute_query("DELETE FROM users WHERE email=%s", (tamper_email,), commit=True)

    def test_04_customer_login_with_phone_number(self):
        """Verify customer can authenticate using their 10-digit registered mobile number."""
        cust = execute_query("SELECT id, email, phone FROM users WHERE role='customer' AND phone IS NOT NULL AND phone != '' LIMIT 1", fetchone=True)
        if cust:
            res = self.client.post('/auth/login', data={
                'email': cust['phone'],
                'password': 'password123'
            }, follow_redirects=False)
            self.assertEqual(res.status_code, 302)
            self.client.get('/auth/logout')

    def test_05_restaurant_partner_separate_auth(self):
        """Verify dedicated /restaurant/login and /restaurant/register."""
        # 1. GET /restaurant/login
        res = self.client.get('/restaurant/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('name="viewport"', html)
        self.assertIn('Kitchen Desk', html)
        self.assertIn('action="/restaurant/login"', html)

        # 2. Reject non-restaurant user on /restaurant/login
        res_fail = self.client.post('/restaurant/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        fail_html = res_fail.data.decode('utf-8')
        self.assertTrue('This portal is reserved for restaurant partners' in fail_html or 'Invalid partner credentials' in fail_html)

        # 3. Allow valid restaurant user on /restaurant/login
        res_ok = self.client.post('/restaurant/login', data={
            'email': 'restaurant@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=False)
        self.assertEqual(res_ok.status_code, 302)
        self.assertIn('/restaurant/dashboard', res_ok.headers.get('Location', ''))
        self.client.get('/auth/logout')

        # 4. GET /restaurant/register
        res_reg = self.client.get('/restaurant/register')
        self.assertEqual(res_reg.status_code, 200)
        reg_html = res_reg.data.decode('utf-8')
        self.assertIn('name="viewport"', reg_html)
        self.assertIn('action="/restaurant/register"', reg_html)
        self.assertIn('name="restaurant_name"', reg_html)
        self.assertIn('name="cuisine"', reg_html)

    def test_06_delivery_partner_separate_auth(self):
        """Verify dedicated /delivery/login and /delivery/register."""
        # 1. GET /delivery/login
        res = self.client.get('/delivery/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('name="viewport"', html)
        self.assertIn('Rider Desk', html)
        self.assertIn('action="/delivery/login"', html)

        # 2. Reject non-delivery user on /delivery/login
        res_fail = self.client.post('/delivery/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        fail_html = res_fail.data.decode('utf-8')
        self.assertTrue('This portal is reserved for delivery partners' in fail_html or 'Invalid rider credentials' in fail_html)

        # 3. Allow valid delivery user on /delivery/login
        res_ok = self.client.post('/delivery/login', data={
            'email': 'delivery@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=False)
        self.assertEqual(res_ok.status_code, 302)
        self.assertIn('/delivery/dashboard', res_ok.headers.get('Location', ''))
        self.client.get('/auth/logout')

        # 4. GET /delivery/register
        res_reg = self.client.get('/delivery/register')
        self.assertEqual(res_reg.status_code, 200)
        reg_html = res_reg.data.decode('utf-8')
        self.assertIn('name="viewport"', reg_html)
        self.assertIn('action="/delivery/register"', reg_html)
        self.assertIn('name="vehicle_type"', reg_html)
        self.assertIn('name="vehicle_number"', reg_html)
        self.assertIn('name="license_number"', reg_html)

    def test_07_admin_separate_auth(self):
        """Verify dedicated /admin/login and absence of public registration."""
        # Clear gate pass to allow access to admin login desk
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        # In direct demo mode, gate logs in admin; clear user identity to test conventional login desk
        with self.client.session_transaction() as sess:
            sess.pop('user_id', None)
            sess.pop('role', None)

        # 1. GET /admin/login
        res = self.client.get('/admin/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('name="viewport"', html)
        self.assertIn('Executive Desk', html)
        self.assertIn('action="/admin/login"', html)
        # Public registration must not be shown
        self.assertNotIn('/admin/register', html)

        # 2. Reject non-admin user on /admin/login
        res_fail = self.client.post('/admin/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        fail_html = res_fail.data.decode('utf-8')
        self.assertTrue('Access denied' in fail_html or 'Admin privilege required' in fail_html)

        # 3. Allow admin user on /admin/login
        res_ok = self.client.post('/admin/login', data={
            'email': 'admin@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=False)
        self.assertEqual(res_ok.status_code, 302)
        self.assertIn('/admin/dashboard', res_ok.headers.get('Location', ''))
        self.client.get('/auth/logout')

    def test_08_mobile_drawer_and_responsive_elements(self):
        """Verify mobile navigation drawer markup exists in shared base layouts."""
        res = self.client.get('/')
        html = res.data.decode('utf-8')
        self.assertIn('id="hamburgerBtn"', html)
        self.assertIn('id="mainNav"', html)
        self.assertIn('id="navBackdrop"', html)
        self.assertIn('class="mobile-nav-search"', html)
        self.assertIn('id="navBackdrop"', html)
        self.assertIn('class="mobile-nav-search"', html)

        # Ops layout mobile drawer verification
        with self.client.session_transaction() as sess:
            sess['user_id'] = 4
            sess['role'] = 'admin'
            sess['user_name'] = 'System Administrator'
            sess['user_email'] = 'admin@foodiehunter.com'
            sess['admin_gate_passed'] = True
        
        ops_res = self.client.get('/admin/dashboard')
        ops_html = ops_res.data.decode('utf-8')
        self.assertIn('id="opsHamburger"', ops_html)
        self.assertIn('id="opsSidebar"', ops_html)
        self.assertIn('id="opsSidebarBackdrop"', ops_html)

    def test_09_no_hardcoded_localhost_in_templates(self):
        """Verify tunnel compatibility: no http://localhost: or http://127.0.0.1 in rendered HTML."""
        routes_to_scan = [
            '/',
            '/restaurants',
            '/auth/login',
            '/auth/register',
            '/restaurant/login',
            '/delivery/login',
            '/admin/login'
        ]
        for route in routes_to_scan:
            res = self.client.get(route)
            html = res.data.decode('utf-8')
            self.assertNotIn('http://localhost:', html, f"Hardcoded localhost found in {route}")
            self.assertNotIn('http://127.0.0.1:', html, f"Hardcoded 127.0.0.1 found in {route}")

if __name__ == '__main__':
    unittest.main()
