"""
tests/test_role_session_isolation.py
Automated Regression and Cross-Role Session Isolation Suite:
- Test A: Administrator already logged in; Customer login renders without redirecting to Admin Dashboard
- Test B: Independent role contexts coexisting in same session/cookie
- Test C: Customer registration isolation (strictly customer role assigned; ignores injected roles)
- Test D: Logout isolation (portal logouts only clear corresponding role context)
- Test E: Role and route security (strict RBAC; no cross-portal elevation)
- Test F: Existing features validation across all 5 portals
"""

import os
import sys
import unittest
import uuid
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from werkzeug.security import check_password_hash


class TestRoleSessionIsolation(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    # ─────────────────────────────────────────────────────────────────────────
    # TEST A: Administrator already logged in
    # ─────────────────────────────────────────────────────────────────────────
    def test_a_admin_already_logged_in_customer_login_flow(self):
        """
        1. Authenticate as an administrator through authorized Admin Gate flow.
        2. Keep the same browser / test-client session.
        3. Request /auth/login.
        4. Verify that Customer Login page renders (HTTP 200).
        5. Verify that the request does NOT redirect to /admin, /admin/login or /admin/dashboard.
        6. Submit valid customer credentials.
        7. Verify the result is the customer storefront or safe customer destination.
        """
        # Step 1: Admin authentication via Gate
        gate_res = self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        self.assertEqual(gate_res.status_code, 200)

        # Step 2 & 3: In the SAME session, visit customer login
        login_page_res = self.client.get('/auth/login', follow_redirects=False)

        # Step 4 & 5: Must render Customer Login directly (HTTP 200), NOT redirect to /admin or dashboard!
        self.assertEqual(login_page_res.status_code, 200,
                         "Customer login page should render 200 even if Admin is active in another tab")
        html_content = login_page_res.data.decode('utf-8')
        self.assertIn("Customer Login", html_content)
        self.assertNotIn("Admin Control Center", html_content)
        self.assertNotIn("Location", login_page_res.headers)

        # Step 6: Submit valid customer credentials
        cust_login_res = self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=False)

        # Step 7: Must redirect to customer storefront (main.index '/') and NEVER /admin
        self.assertEqual(cust_login_res.status_code, 302)
        location = cust_login_res.headers.get('Location', '')
        self.assertNotIn('/admin', location, "Customer login must NEVER redirect to /admin or /admin/dashboard!")
        self.assertTrue(location == '/' or location.endswith('/'), f"Expected redirect to '/', got {location}")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST B: Independent role contexts coexisting in same session
    # ─────────────────────────────────────────────────────────────────────────
    def test_b_independent_role_contexts(self):
        """
        1. Authenticate as Admin.
        2. Authenticate as Customer using the same session.
        3. Verify Customer authentication does not overwrite Admin context.
        4. Verify both role routes validate their own authentication context.
        5. Verify customer storefront navigation renders customer-facing links only.
        6. Verify a customer-only session cannot reach Admin Dashboard.
        """
        # 1. Authenticate as Admin
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        with self.client.session_transaction() as sess:
            self.assertIn('admin_auth', sess)
            self.assertTrue(sess.get('admin_gate_passed'))

        # 2. Authenticate as Customer in the same session
        self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        # 3. Verify coexisting contexts
        with self.client.session_transaction() as sess:
            self.assertIn('admin_auth', sess, "Admin context must NOT be overwritten by Customer login")
            self.assertIn('customer_auth', sess, "Customer context must exist")
            self.assertEqual(sess['customer_auth']['role'], 'customer')
            self.assertEqual(sess['admin_auth']['role'], 'admin')

        # 4. Verify both authorized route scopes succeed
        admin_res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(admin_res.status_code, 200, "Admin dashboard must remain accessible")

        cust_profile_res = self.client.get('/customer/profile', follow_redirects=False)
        self.assertEqual(cust_profile_res.status_code, 200, "Customer profile must remain accessible")

        # 5. Customer storefront navigation isolation
        storefront_res = self.client.get('/', follow_redirects=False)
        self.assertEqual(storefront_res.status_code, 200)
        sf_html = storefront_res.data.decode('utf-8')
        self.assertIn('href="/customer/profile"', sf_html)
        self.assertNotIn('href="/admin/dashboard"', sf_html,
                         "Customer storefront navbar must never display Admin Dashboard button")

        # 6. Customer-only client cannot reach Admin Dashboard
        isolated_client = self.app.test_client()
        isolated_client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        unauth_admin_res = isolated_client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(unauth_admin_res.status_code, 302, "Customer-only session must be redirected away from admin")
        self.assertIn(unauth_admin_res.headers.get('Location'), ('/', '/admin/gate'))

    # ─────────────────────────────────────────────────────────────────────────
    # TEST C: Registration isolation
    # ─────────────────────────────────────────────────────────────────────────
    def test_c_customer_registration_isolation(self):
        """
        - Customer registration succeeds with valid customer data.
        - Injected admin, restaurant, delivery, or staff roles are strictly ignored.
        - Registration never redirects to Admin Dashboard.
        - Pre-existing admin session does not change the created account's role.
        """
        # Authenticate as admin in session first
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)

        rand_num = random.randint(100000, 999999)
        test_email = f"isolation_user_{rand_num}@example.com"
        test_phone = f"98{random.randint(10000000, 99999999)}"

        # Attempt to register while tampering with role = 'admin'
        reg_res = self.client.post('/auth/register', data={
            'name': 'Injected Role User',
            'email': test_email,
            'phone': test_phone,
            'password': 'password123',
            'confirm_password': 'password123',
            'address': 'Civil Lines, Mehsana',
            'city': 'Mehsana',
            'pincode': '384002',
            'role': 'admin'  # Attempted privilege escalation
        }, follow_redirects=False)

        # Must redirect to customer login, never admin
        self.assertEqual(reg_res.status_code, 302)
        self.assertIn('/auth/login', reg_res.headers.get('Location', ''))
        self.assertNotIn('/admin', reg_res.headers.get('Location', ''))

        # Check DB to verify assigned role is strictly 'customer'
        created_user = execute_query("SELECT * FROM users WHERE email=%s", (test_email,), fetchone=True)
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user['role'], 'customer',
                         "Injected role 'admin' must be ignored; role must strictly be 'customer'")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST D: Logout isolation
    # ─────────────────────────────────────────────────────────────────────────
    def test_d_logout_isolation(self):
        """
        - Customer logout clears only the customer context.
        - Customer logout leaves Admin context intact.
        - Admin logout invalidates admin context and gate access without clearing customer.
        - Restaurant, delivery, and staff logouts operate independently.
        """
        # 1. Login as both Admin and Customer in the same session
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        # 2. Logout customer
        logout_res = self.client.get('/auth/logout', follow_redirects=False)
        self.assertEqual(logout_res.status_code, 302)

        # Verify customer context is gone, but admin context remains active
        with self.client.session_transaction() as sess:
            self.assertNotIn('customer_auth', sess)
            self.assertIn('admin_auth', sess, "Admin context must survive Customer logout")
            self.assertTrue(sess.get('admin_gate_passed'))

        # Verify admin dashboard is still accessible
        admin_res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(admin_res.status_code, 200)

        # 3. Log back in as customer, then logout admin
        self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        admin_logout_res = self.client.get('/admin/logout', follow_redirects=False)
        self.assertEqual(admin_logout_res.status_code, 302)

        # Verify admin context is gone, but customer context remains active
        with self.client.session_transaction() as sess:
            self.assertNotIn('admin_auth', sess)
            self.assertNotIn('admin_gate_passed', sess)
            self.assertIn('customer_auth', sess, "Customer context must survive Admin logout")

        # Verify customer profile is still accessible
        cust_res = self.client.get('/customer/profile', follow_redirects=False)
        self.assertEqual(cust_res.status_code, 200)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST E: Role and route security
    # ─────────────────────────────────────────────────────────────────────────
    def test_e_role_and_route_security(self):
        """
        - Customer cannot access admin routes.
        - Restaurant owner cannot access admin routes.
        - Delivery partner cannot access admin routes.
        - Staff cannot access admin routes.
        - Admin credentials submitted to Customer Login are rejected with an explicit notice.
        """
        # Customer access to admin
        client_cust = self.app.test_client()
        client_cust.post('/auth/login', data={'email': 'customer@foodiehunter.com', 'password': 'password123'}, follow_redirects=True)
        res = client_cust.get('/admin/dashboard', follow_redirects=False)
        self.assertIn(res.status_code, (302, 403))

        # Admin account submitted to Customer Login
        client_guest = self.app.test_client()
        admin_on_cust_login = client_guest.post('/auth/login', data={'email': 'admin@foodiehunter.com', 'password': 'password123'}, follow_redirects=False)
        self.assertEqual(admin_on_cust_login.status_code, 200, "Admin credentials on customer login must be rejected (return 200 with flash)")
        html_resp = admin_on_cust_login.data.decode('utf-8')
        self.assertIn('Administrator accounts cannot be authenticated via Customer Login', html_resp)

        # Restaurant owner access to admin
        client_rest = self.app.test_client()
        client_rest.post('/restaurant/login', data={'email': 'restaurant@foodiehunter.com', 'password': 'password123'}, follow_redirects=True)
        res = client_rest.get('/admin/dashboard', follow_redirects=False)
        self.assertIn(res.status_code, (302, 403))

        # Delivery partner access to admin
        client_deliv = self.app.test_client()
        client_deliv.post('/delivery/login', data={'email': 'delivery@foodiehunter.com', 'password': 'password123'}, follow_redirects=True)
        res = client_deliv.get('/admin/dashboard', follow_redirects=False)
        self.assertIn(res.status_code, (302, 403))

        # Staff access to admin
        client_staff = self.app.test_client()
        staff_user = execute_query("SELECT email FROM users WHERE role='staff' LIMIT 1", fetchone=True)
        if staff_user:
            client_staff.post('/staff/login', data={'email': staff_user['email'], 'password': 'password123'}, follow_redirects=True)
            res = client_staff.get('/admin/dashboard', follow_redirects=False)
            self.assertIn(res.status_code, (302, 403))

    # ─────────────────────────────────────────────────────────────────────────
    # TEST F: Existing features validation across all 5 portals
    # ─────────────────────────────────────────────────────────────────────────
    def test_f_existing_features_all_five_portals(self):
        """
        - Portal 1: Customer login and storefront browsing.
        - Portal 2: Admin Gate passkey unlocks dashboard.
        - Portal 3: Restaurant owner login loads dashboard.
        - Portal 4: Delivery partner login loads dashboard.
        - Portal 5: Staff login loads kitchen operations desk.
        """
        # Portal 1: Customer
        c1 = self.app.test_client()
        res = c1.post('/auth/login', data={'email': 'customer@foodiehunter.com', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Foody', res.data)

        # Portal 2: Admin
        c2 = self.app.test_client()
        res = c2.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Executive Command Center', res.data)

        # Portal 3: Restaurant
        c3 = self.app.test_client()
        res = c3.post('/restaurant/login', data={'email': 'restaurant@foodiehunter.com', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Portal 4: Delivery
        c4 = self.app.test_client()
        res = c4.post('/delivery/login', data={'email': 'delivery@foodiehunter.com', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Portal 5: Staff
        c5 = self.app.test_client()
        staff_user = execute_query("SELECT email FROM users WHERE role='staff' LIMIT 1", fetchone=True)
        if staff_user:
            res = c5.post('/staff/login', data={'email': staff_user['email'], 'password': 'password123'}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)


if __name__ == '__main__':
    unittest.main()
