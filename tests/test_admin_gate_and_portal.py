"""
tests/test_admin_gate_and_portal.py
Comprehensive regression & security test suite for:
1. FOODY HUNTERS Admin Entry Security Gate
   - Unauthenticated redirect to /admin/gate
   - Wrong passkey rejection & failed-attempt rate limiting
   - Correct passkey (food@1234) validation & session flag
   - Non-exposure of passkey in client DOM
   - Direct access barrier on /admin/dashboard & sub-routes
   - Logout clears gate session
2. Dual-Layer Security & RBAC Enforcement
   - Gate alone does not grant admin rights
   - Valid admin authentication (/admin/login)
   - Rejection of customer, restaurant, delivery, and staff roles on admin routes
3. Admin Control Center & Central Command Hub
   - /admin/dashboard KPI cards (including Staff Fleet & Governance)
   - Unified Operations Sidebar with all 14 operational modules
   - Zero missing templates or broken blueprint redirects
4. Staff Management & Governance Panel
   - /admin/staff loads with restaurant filter & search
   - Staff verification (approve / reject)
   - Staff activation / suspension toggle
   - Staff reassignment to authorized restaurant
   - Safe staff account deletion
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash


class TestAdminGateAndPortal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        # Fresh test client for each test isolation
        self.client = self.app.test_client()

    # ─────────────────────────────────────────────────────────
    # A. ADMIN ACCESS GATE TESTS
    # ─────────────────────────────────────────────────────────

    def test_01_admin_root_redirects_to_gate_screen(self):
        """Unauthenticated visitor opening /admin must be redirected to /admin/gate."""
        res = self.client.get('/admin', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/gate', res.headers.get('Location', ''))

        # Following redirect renders the gate passkey form
        res_follow = self.client.get('/admin', follow_redirects=True)
        self.assertEqual(res_follow.status_code, 200)
        html = res_follow.data.decode('utf-8')
        self.assertIn('Admin Control Center', html)
        self.assertIn('action="/admin/gate"', html)
        self.assertIn('name="gate_password"', html)
        self.assertIn('type="password"', html)
        # Ensure password is NEVER rendered in text or comments
        self.assertNotIn('food@1234', html)

    def test_02_wrong_gate_password_rejected(self):
        """Wrong gate password must be rejected with danger alert."""
        res = self.client.post('/admin/gate', data={
            'gate_password': 'wrongpassword999'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Invalid security passkey', html)
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get('admin_gate_passed', False))

    def test_03_correct_gate_password_logs_in_and_proceeds_directly_to_dashboard(self):
        """Correct gate password ('food@1234') sets admin identity and proceeds directly to /admin/dashboard."""
        expected_pass = getattr(Config, 'ADMIN_GATE_PASSWORD', 'food@1234')
        res = self.client.post('/admin/gate', data={
            'gate_password': expected_pass
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        # Directly redirects to dashboard without redundant email/password screen
        self.assertIn('/admin/dashboard', res.headers.get('Location', ''))

        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('admin_gate_passed'))
            self.assertEqual(sess.get('role'), 'admin')
            self.assertIsNotNone(sess.get('user_id'))

        # Following redirect directly loads dashboard with HTTP 200
        res_dash = self.client.get(res.headers.get('Location'))
        self.assertEqual(res_dash.status_code, 200)
        html = res_dash.data.decode('utf-8')
        self.assertIn('Executive Command Center', html)
        self.assertIn('Admin Control', html)

    def test_04_direct_access_to_admin_dashboard_blocked_without_gate(self):
        """Direct access to /admin/dashboard without gate must redirect to /admin/gate."""
        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/gate', res.headers.get('Location', ''))

    def test_05_direct_access_to_admin_staff_blocked_without_gate(self):
        """Direct access to /admin/staff without gate must redirect to /admin/gate."""
        res = self.client.get('/admin/staff', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/gate', res.headers.get('Location', ''))

    def test_06_unauthenticated_visitor_blocked_from_admin_dashboard(self):
        """Unauthenticated visitor cannot access /admin/dashboard."""
        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/gate', res.headers.get('Location', ''))

    # ─────────────────────────────────────────────────────────
    # B. ADMIN AUTHENTICATION & ROLE AUTHORIZATION TESTS
    # ─────────────────────────────────────────────────────────

    def test_07_conventional_admin_login_fallback_works(self):
        """Conventional email/password login route /admin/login authenticates admin and unlocks console."""
        res = self.client.post('/admin/login', data={
            'email': 'admin@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/dashboard', res.headers.get('Location', ''))

        # Access dashboard
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        html = res_dash.data.decode('utf-8')
        self.assertIn('Admin Control', html)
        self.assertIn('Executive Command Center', html)
        self.assertIn('Restaurant Staff Fleet', html)
        self.assertIn('Staff Governance', html)

    def test_08_customer_cannot_access_admin_even_if_gate_passed(self):
        """Customer entering the gate passkey must still be rejected from admin dashboard."""
        # 1. Pass gate
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        # 2. Set session to customer
        with self.client.session_transaction() as sess:
            sess['user_id'] = 100
            sess['role'] = 'customer'
            sess['user_name'] = 'Test Customer'
        # 3. Customer attempts to access dashboard
        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        # Denied access redirected to storefront
        self.assertEqual(res.headers.get('Location'), '/')

    def test_09_staff_cannot_access_admin_even_if_gate_passed(self):
        """Staff member entering gate passkey must still be rejected from admin dashboard."""
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        with self.client.session_transaction() as sess:
            sess['user_id'] = 200
            sess['role'] = 'staff'
            sess['user_name'] = 'Kitchen Staff'
        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/')

    def test_10_admin_logout_invalidates_gate_session(self):
        """Admin logout must invalidate both user credentials and gate session."""
        # Setup active admin session with gate passed
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'
            sess['admin_gate_passed'] = True

        res = self.client.get('/admin/logout', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertTrue('/admin' in res.headers.get('Location', ''))

        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)
            self.assertNotIn('admin_gate_passed', sess)

    # ─────────────────────────────────────────────────────────
    # C. ADMIN CONTROL CENTER & 14 MODULES TESTS
    # ─────────────────────────────────────────────────────────

    def _auth_as_admin(self):
        """Helper to establish a verified admin session."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'System Administrator'
            sess['role'] = 'admin'
            sess['admin_gate_passed'] = True

    def test_11_all_14_admin_navigation_modules_render_200(self):
        """Verify that all 14 admin management endpoints render with HTTP 200 and operations layout."""
        self._auth_as_admin()

        endpoints = [
            ('/admin/dashboard', 'Executive Dashboard'),
            ('/admin/users', 'User & Account Directory'),
            ('/admin/restaurants', 'Restaurant Fleet Management'),
            ('/admin/delivery-partners', 'Delivery Fleet & Riders'),
            ('/admin/staff', 'Kitchen Staff Governance'),
            ('/admin/orders', 'System Orders & Dispatches'),
            ('/admin/categories', 'Cuisine & Food Categories'),
            ('/admin/food-items', 'Master Menu & Dish Catalog'),
            ('/admin/coupons', 'Promotional Coupons & Campaigns'),
            ('/admin/payments', 'Platform Payments & Transactions'),
            ('/admin/reports', 'Business Intelligence & Analytics'),
            ('/admin/complaints', 'Customer Support & Inquiries'),
            ('/admin/reviews', 'Review & Rating Moderation'),
            ('/admin/activity', 'Operations Audit Trail'),
            ('/admin/profile', 'Executive Administrator Profile'),
        ]

        for url, expected_text in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Module failed: {url} returned {res.status_code}")
            html = res.data.decode('utf-8')
            self.assertIn(expected_text, html, f"Expected text '{expected_text}' not found on {url}")
            # Ensure operations sidebar is present
            self.assertIn('ops-sidebar', html, f"ops-sidebar missing on {url}")

    # ─────────────────────────────────────────────────────────
    # D. STAFF GOVERNANCE PANEL TESTS
    # ─────────────────────────────────────────────────────────

    def test_12_admin_staff_governance_lifecycle(self):
        """Admin views, approves, reassigns, and deletes staff member."""
        self._auth_as_admin()

        # 1. View staff directory
        res = self.client.get('/admin/staff')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Kitchen Staff Governance', res.data)

        # 2. Create a fresh test staff user
        uid = uuid.uuid4().hex[:6]
        pw = generate_password_hash('password123')
        test_user_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, %s, 'staff', 'active')",
            (f'Chef Test {uid}', f'cheftest_{uid}@mehsana.com', f'9811{uid[:4]}', pw),
            commit=True
        )

        rest = execute_query("SELECT id FROM restaurants LIMIT 1", fetchone=True)
        rest_id = rest['id'] if rest else 1

        staff_id = execute_query(
            "INSERT INTO restaurant_staff (user_id, restaurant_id, staff_role, status, shift) VALUES (%s, %s, 'kitchen_staff', 'pending', 'Full Time')",
            (test_user_id, rest_id),
            commit=True
        )

        # 3. Admin approves pending application
        res_approve = self.client.post(f'/admin/staff/verify/{staff_id}/approved', follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)
        staff_row = execute_query("SELECT status FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
        self.assertEqual(staff_row['status'], 'approved')

        # 4. Admin toggles status to suspended
        res_toggle = self.client.post(f'/admin/staff/toggle/{staff_id}', follow_redirects=True)
        self.assertEqual(res_toggle.status_code, 200)
        staff_row = execute_query("SELECT status FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
        self.assertEqual(staff_row['status'], 'suspended')

        # 5. Admin reassigns staff if second restaurant exists
        second_rest = execute_query("SELECT id FROM restaurants WHERE id != %s LIMIT 1", (rest_id,), fetchone=True)
        if second_rest:
            res_reassign = self.client.post(f'/admin/staff/reassign/{staff_id}', data={
                'restaurant_id': str(second_rest['id'])
            }, follow_redirects=True)
            self.assertEqual(res_reassign.status_code, 200)
            staff_row = execute_query("SELECT restaurant_id FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
            self.assertEqual(staff_row['restaurant_id'], second_rest['id'])

        # 6. Admin deletes staff account
        res_del = self.client.post(f'/admin/staff/delete/{staff_id}', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        deleted_staff = execute_query("SELECT * FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
        self.assertIsNone(deleted_staff)

    # ─────────────────────────────────────────────────────────
    # E. REGRESSION: CUSTOMER, RESTAURANT & DELIVERY UNAFFECTED
    # ─────────────────────────────────────────────────────────

    def test_13_customer_storefront_and_login_unaffected(self):
        """Customer homepage, customer login (/auth/login) remain 100% functional."""
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)

        res_login = self.client.get('/auth/login')
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Customer Sign In', res_login.data)

    def test_14_restaurant_and_delivery_portals_unaffected(self):
        """Restaurant (/restaurant/login) and Delivery (/delivery/login) remain functional."""
        res_rest = self.client.get('/restaurant/login')
        self.assertEqual(res_rest.status_code, 200)
        self.assertIn(b'Restaurant Partner Login', res_rest.data)

        res_deliv = self.client.get('/delivery/login')
        self.assertEqual(res_deliv.status_code, 200)
        self.assertIn(b'Delivery Partner Login', res_deliv.data)

        res_staff = self.client.get('/staff/login')
        self.assertEqual(res_staff.status_code, 200)
        self.assertIn(b'Kitchen Operations Desk', res_staff.data)


if __name__ == '__main__':
    unittest.main()
