"""
tests/test_role_identity_consistency.py
Comprehensive regression tests for authoritative role identity display,
session isolation, and mixed-session coexistence across all 5 portals:
1. Customer
2. Administrator
3. Restaurant Owner
4. Delivery Partner
5. Restaurant / Hotel Staff
"""

import os
import sys
import unittest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from utils.helpers import get_role_display_name


class TestRoleIdentityConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.client = self.app.test_client()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. INDIVIDUAL ROLE IDENTITY & DISPLAY TESTS
    # ─────────────────────────────────────────────────────────────────────────

    def test_01_customer_identity_consistency(self):
        """1. Customer role: authoritative database match, profile label 'Customer', and API status."""
        client = self.app.test_client()
        # Log in as Customer (user 1: Raj Patel)
        res = client.post('/auth/login', data={
            'email': 'customer@foodyhunters.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB role
        db_user = execute_query("SELECT role FROM users WHERE email='customer@foodyhunters.com'", fetchone=True)
        self.assertEqual(db_user['role'], 'customer')

        # Check API status
        api_res = client.get('/api/auth/status')
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()
        self.assertEqual(data['role'], 'customer')
        self.assertEqual(data['role_display'], 'Customer')

        # Check Customer Profile page
        prof_res = client.get('/customer/profile')
        self.assertEqual(prof_res.status_code, 200)
        html = prof_res.data.decode('utf-8')
        self.assertIn("Customer", html)
        self.assertIn('id="userRoleBadge"', html)
        badge_idx = html.find('id="userRoleBadge"')
        badge_snippet = html[badge_idx:badge_idx + 200]
        self.assertIn("Customer", badge_snippet)
        self.assertNotIn("Administrator", badge_snippet)

    def test_02_admin_identity_consistency(self):
        """2. Administrator role: authoritative database match, dashboard header 'Administrator', and API status."""
        client = self.app.test_client()
        # Pass Admin Gate and login
        client.post('/admin/gate/verify', data={'gate_password': 'food@1234'})
        res = client.post('/admin/login', data={
            'email': 'admin@foodyhunters.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB role
        db_user = execute_query("SELECT role FROM users WHERE email='admin@foodyhunters.com'", fetchone=True)
        self.assertEqual(db_user['role'], 'admin')

        # Check API status
        api_res = client.get('/api/auth/status')
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()
        self.assertEqual(data['role'], 'admin')
        self.assertEqual(data['role_display'], 'Administrator')

        # Check Admin Profile page
        prof_res = client.get('/admin/profile')
        self.assertEqual(prof_res.status_code, 200)
        html = prof_res.data.decode('utf-8')
        self.assertIn("Administrator", html)

    def test_03_restaurant_owner_identity_consistency(self):
        """3. Restaurant Owner role: authoritative database match, profile label 'Restaurant Owner', and API status."""
        client = self.app.test_client()
        res = client.post('/restaurant/login', data={
            'email': 'restaurant@foodyhunters.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB role
        db_user = execute_query("SELECT role FROM users WHERE email='restaurant@foodyhunters.com'", fetchone=True)
        self.assertEqual(db_user['role'], 'restaurant')

        # Check API status
        api_res = client.get('/api/auth/status')
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()
        self.assertEqual(data['role'], 'restaurant')
        self.assertEqual(data['role_display'], 'Restaurant Owner')

        # Check Restaurant Profile page
        prof_res = client.get('/restaurant/profile')
        self.assertEqual(prof_res.status_code, 200)
        html = prof_res.data.decode('utf-8')
        self.assertIn("Restaurant Owner", html)

    def test_04_delivery_partner_identity_consistency(self):
        """4. Delivery Partner role: authoritative database match, profile label 'Delivery Partner', and API status."""
        client = self.app.test_client()
        res = client.post('/delivery/login', data={
            'email': 'delivery@foodyhunters.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB role
        db_user = execute_query("SELECT role FROM users WHERE email='delivery@foodyhunters.com'", fetchone=True)
        self.assertEqual(db_user['role'], 'delivery')

        # Check API status
        api_res = client.get('/api/auth/status')
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()
        self.assertEqual(data['role'], 'delivery')
        self.assertEqual(data['role_display'], 'Delivery Partner')

        # Check Delivery Profile page
        prof_res = client.get('/delivery/profile')
        self.assertEqual(prof_res.status_code, 200)
        html = prof_res.data.decode('utf-8')
        self.assertIn("Delivery Partner", html)

    def test_05_staff_identity_consistency(self):
        """5. Staff role: authoritative database match, label 'Restaurant / Hotel Staff — Kitchen Staff', and API status."""
        client = self.app.test_client()
        res = client.post('/staff/login', data={
            'email': 'staff@foodyhunters.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB role
        db_user = execute_query("SELECT role FROM users WHERE email='staff@foodyhunters.com'", fetchone=True)
        self.assertEqual(db_user['role'], 'staff')

        # Check API status
        api_res = client.get('/api/auth/status')
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()
        self.assertEqual(data['role'], 'staff')
        self.assertIn("Restaurant / Hotel Staff", data['role_display'])
        self.assertIn("Kitchen Staff", data['role_display'])

        # Check Staff Profile page
        prof_res = client.get('/staff/profile')
        self.assertEqual(prof_res.status_code, 200)
        html = prof_res.data.decode('utf-8')
        self.assertIn("Restaurant / Hotel Staff", html)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. TAMPER RESISTANCE & UNKNOWN ROLE SAFETY
    # ─────────────────────────────────────────────────────────────────────────

    def test_06_unknown_role_neutral_display(self):
        """6. Unknown, empty, or malicious role string is rendered safely as 'Guest' without privilege escalation."""
        self.assertEqual(get_role_display_name(''), 'Guest')
        self.assertEqual(get_role_display_name(None), 'Guest')
        self.assertEqual(get_role_display_name('hacker_admin'), 'Guest')
        self.assertEqual(get_role_display_name('superuser'), 'Guest')
        self.assertEqual(get_role_display_name('root'), 'Guest')

    def test_07_form_tampering_cannot_elevate_role(self):
        """7. A customer cannot elevate role to admin by tampering with form fields or POST data."""
        client = self.app.test_client()
        # Attempt to register with role='admin'
        res = client.post('/auth/register', data={
            'name': 'Attacker',
            'email': 'attacker@hack.com',
            'phone': '9876543210',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'admin'  # Form tamper attempt
        }, follow_redirects=True)

        user = execute_query("SELECT role FROM users WHERE email='attacker@hack.com'", fetchone=True)
        if user:
            # Must remain customer!
            self.assertEqual(user['role'], 'customer', "Form tampering allowed client to set role to admin!")
            execute_query("DELETE FROM users WHERE email='attacker@hack.com'", commit=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. MIXED-SESSION COEXISTENCE SCENARIOS
    # ─────────────────────────────────────────────────────────────────────────

    def test_08_admin_session_then_customer_navigation(self):
        """8. Admin logs in, then navigates to Customer login page without leaking Admin identity into Customer context."""
        client = self.app.test_client()
        # Log in as Admin
        client.post('/admin/gate/verify', data={'gate_password': 'food@1234'})
        client.post('/admin/login', data={'email': 'admin@foodyhunters.com', 'password': 'password123'})

        # Visit customer login page
        cust_res = client.get('/auth/login')
        self.assertEqual(cust_res.status_code, 200)
        html = cust_res.data.decode('utf-8')
        # Admin is not treated as logged in Customer on customer login page
        self.assertIn("Sign In", html)

    def test_09_customer_authenticates_after_admin_session_exists(self):
        """9. Authenticating as Customer while Admin session exists maintains isolated contexts for both."""
        client = self.app.test_client()
        # 1. Admin login
        client.post('/admin/gate/verify', data={'gate_password': 'food@1234'})
        client.post('/admin/login', data={'email': 'admin@foodyhunters.com', 'password': 'password123'})

        # 2. Customer login in same client
        cust_login = client.post('/auth/login', data={'email': 'customer@foodyhunters.com', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(cust_login.status_code, 200)

        # Visiting customer profile shows Customer identity
        cust_prof = client.get('/customer/profile')
        self.assertEqual(cust_prof.status_code, 200)
        self.assertIn("Customer", cust_prof.data.decode('utf-8'))

        # Visiting admin dashboard still accesses Admin identity
        admin_dash = client.get('/admin/dashboard')
        self.assertEqual(admin_dash.status_code, 200)
        self.assertIn("Administrator", admin_dash.data.decode('utf-8'))

    def test_10_logout_from_customer_does_not_revoke_admin(self):
        """10. Logging out from Customer portal does not revoke independent Admin session."""
        client = self.app.test_client()
        # Log in Admin
        client.post('/admin/gate/verify', data={'gate_password': 'food@1234'})
        client.post('/admin/login', data={'email': 'admin@foodyhunters.com', 'password': 'password123'})

        # Log in Customer
        client.post('/auth/login', data={'email': 'customer@foodyhunters.com', 'password': 'password123'})

        # Logout Customer
        logout_res = client.get('/auth/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)

        # Admin dashboard remains accessible
        admin_dash = client.get('/admin/dashboard')
        self.assertEqual(admin_dash.status_code, 200)

    def test_11_logout_from_admin_revokes_admin_access(self):
        """11. Logging out from Admin portal revokes Admin access completely."""
        client = self.app.test_client()
        # Log in Admin
        client.post('/admin/gate/verify', data={'gate_password': 'food@1234'})
        client.post('/admin/login', data={'email': 'admin@foodyhunters.com', 'password': 'password123'})

        # Log out Admin
        admin_logout = client.get('/admin/logout', follow_redirects=False)
        self.assertEqual(admin_logout.status_code, 302)

        # Admin dashboard is now blocked
        admin_dash = client.get('/admin/dashboard')
        self.assertIn(admin_dash.status_code, (302, 403))

    def test_12_delivery_partner_cannot_access_restaurant_or_admin_dashboard(self):
        """12. Delivery Partner account cannot access Restaurant or Admin dashboards."""
        client = self.app.test_client()
        client.post('/delivery/login', data={'email': 'delivery@foodyhunters.com', 'password': 'password123'})

        res_rest = client.get('/restaurant/dashboard')
        self.assertEqual(res_rest.status_code, 302)

        res_admin = client.get('/admin/dashboard')
        self.assertIn(res_admin.status_code, (302, 403))


if __name__ == '__main__':
    unittest.main()
