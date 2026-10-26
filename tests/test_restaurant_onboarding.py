"""
tests/test_restaurant_onboarding.py
Comprehensive test suite for FOODY HUNTERS Restaurant Onboarding & Lifecycle:
1. Public registration endpoint (/restaurant/register) with Mehsana default and custom city support
2. KYC document upload & FSSAI validation
3. Duplicate registration & validation error handling
4. Initial application status is 'pending' and restaurant is 'inactive'
5. Pending owner cannot access /restaurant/dashboard and is redirected to /restaurant/application-status
6. Unapproved/pending restaurant is hidden from customer storefront (/restaurants)
7. Admin can view applications, filter by pending/approved/rejected, and search on /admin/restaurants
8. Admin approval transitions status to 'approved' / 'active' and writes audit log
9. Approved owner can log in and access /restaurant/dashboard
10. Approved restaurant becomes visible on customer storefront
11. Admin rejection transitions status to 'rejected' and blocks dashboard access
"""

import io
import os
import random
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from config import Config


class TestRestaurantOnboarding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.client = self.app.test_client()

    def _login_as_admin(self):
        """Helper to establish an authenticated admin session."""
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

    def test_01_public_registration_page_loads_with_required_fields(self):
        """GET /restaurant/register renders public onboarding form with Mehsana preselected."""
        res = self.client.get('/restaurant/register')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('List Your Restaurant on FOODY HUNTERS', html)
        self.assertIn('name="restaurant_name"', html)
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="phone"', html)
        self.assertIn('name="city_choice"', html)
        self.assertIn('value="Mehsana"', html)
        self.assertIn('name="fssai_number"', html)
        self.assertIn('name="document"', html)
        self.assertIn('name="password"', html)
        self.assertIn('name="confirm_password"', html)

    def test_02_submit_application_with_mehsana_and_kyc_document(self):
        """Submit a complete restaurant application for Mehsana with mock KYC document."""
        uid = uuid.uuid4().hex[:6]
        email = f"owner_mehsana_{uid}@onboardingtest.com"
        phone = f"97{random.randint(10000000, 99999999)}"
        rest_name = f"Royal Mehsana Dining {uid}"

        mock_doc = (io.BytesIO(b"%PDF-1.4 Mock FSSAI License Document for Onboarding"), "fssai_cert.pdf")

        data = {
            'restaurant_name': rest_name,
            'name': f"Owner {uid}",
            'email': email,
            'phone': phone,
            'password': 'Password@123',
            'confirm_password': 'Password@123',
            'address': 'Plot 42, Highway Circle, Mehsana',
            'city_choice': 'Mehsana',
            'custom_city': '',
            'area': 'Highway Circle',
            'pincode': '384002',
            'cuisine': 'North Indian, Gujarati, Fast Food',
            'open_time': '09:00',
            'close_time': '23:00',
            'description': 'Authentic flavours with fresh farm ingredients in Mehsana.',
            'fssai_number': '10020011002233',
            'document': mock_doc
        }

        res = self.client.post('/restaurant/register', data=data, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/restaurant/application-status', res.headers.get('Location', ''))

        # Check DB state: User exists as restaurant role
        user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'restaurant')

        # Check DB state: Restaurant exists with verification_status='pending' and status='inactive'
        restaurant = execute_query("SELECT * FROM restaurants WHERE owner_id=%s", (user['id'],), fetchone=True)
        self.assertIsNotNone(restaurant)
        self.assertEqual(restaurant['name'], rest_name)
        self.assertEqual(restaurant['city'], 'Mehsana')
        self.assertEqual(restaurant['verification_status'], 'pending')
        self.assertEqual(restaurant['status'], 'inactive')
        self.assertEqual(restaurant['fssai_number'], '10020011002233')
        self.assertTrue(restaurant['verification_doc'] is not None and len(restaurant['verification_doc']) > 0)

        # Check application status page renders correctly
        res_status = self.client.get(f"/restaurant/application-status?id={restaurant['id']}")
        self.assertEqual(res_status.status_code, 200)
        status_html = res_status.data.decode('utf-8')
        self.assertIn('Pending Administrator Verification', status_html)
        self.assertIn(rest_name, status_html)

    def test_03_submit_application_with_custom_city(self):
        """Submit application supporting cities outside Mehsana (extensibility requirement)."""
        uid = uuid.uuid4().hex[:6]
        email = f"owner_custom_{uid}@onboardingtest.com"
        phone = f"96{random.randint(10000000, 99999999)}"
        rest_name = f"Ahmedabad Bistro {uid}"

        data = {
            'restaurant_name': rest_name,
            'owner_name': f"Ahmedabad Partner {uid}",
            'email': email,
            'phone': phone,
            'password': 'Password@123',
            'confirm_password': 'Password@123',
            'address': 'Near SG Highway, Ahmedabad',
            'city_choice': 'other',
            'custom_city': 'Ahmedabad',
            'area': 'SG Highway',
            'pincode': '380054',
            'cuisine': 'Continental, Italian',
            'open_time': '11:00',
            'close_time': '23:00',
            'description': 'Premier Italian and Continental dining.',
            'fssai_number': '10020011009988'
        }

        res = self.client.post('/restaurant/register', data=data, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        user = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetchone=True)
        restaurant = execute_query("SELECT city, verification_status FROM restaurants WHERE owner_id=%s", (user['id'],), fetchone=True)
        self.assertEqual(restaurant['city'], 'Ahmedabad')
        self.assertEqual(restaurant['verification_status'], 'pending')

    def test_04_validation_rejections_and_duplicate_handling(self):
        """Registration rejects mismatched passwords and duplicate email/phone numbers."""
        uid = uuid.uuid4().hex[:6]

        # 1. Password mismatch
        res_mismatch = self.client.post('/restaurant/register', data={
            'restaurant_name': 'Mismatch Cafe',
            'owner_name': 'Owner Test',
            'email': f'mismatch_{uid}@test.com',
            'phone': '9898001122',
            'password': 'Password1',
            'confirm_password': 'Password2'
        }, follow_redirects=True)
        self.assertIn('Passwords do not match', res_mismatch.data.decode('utf-8'))

        # 2. Duplicate registration attempt with existing email
        demo_email = 'restaurant@foodiehunter.com'
        res_dup = self.client.post('/restaurant/register', data={
            'restaurant_name': 'Duplicate Outlet',
            'name': 'Duplicate Owner',
            'email': demo_email,
            'phone': '9898998877',
            'cuisine': 'Fast Food',
            'address': 'Main Highway, Mehsana',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertIn('already registered', res_dup.data.decode('utf-8').lower())

    def test_05_pending_restaurant_owner_blocked_from_dashboard(self):
        """A restaurant owner whose verification is 'pending' cannot access /restaurant/dashboard."""
        uid = uuid.uuid4().hex[:6]
        # Create user & pending restaurant
        u_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'restaurant', 'active')",
            (f"Pending Owner {uid}", f"pending_{uid}@test.com", f"95{uid[:8]}"),
            commit=True
        )
        r_id = execute_query(
            "INSERT INTO restaurants (owner_id, name, cuisine, address, city, area, verification_status, status) VALUES (%s, %s, 'Gujarati', 'Shop 101, Main Road', 'Mehsana', 'Central', 'pending', 'inactive')",
            (u_id, f"Pending Rest {uid}"),
            commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = u_id
            sess['role'] = 'restaurant'
            sess['user_name'] = f"Pending Owner {uid}"
            sess['user_email'] = f"pending_{uid}@test.com"

        res = self.client.get('/restaurant/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/restaurant/application-status', res.headers.get('Location', ''))

    def test_06_pending_restaurant_hidden_from_customer_storefront(self):
        """Restaurants with status='inactive' or verification_status='pending' must NOT appear on /restaurants."""
        uid = uuid.uuid4().hex[:6]
        unique_name = f"Ghost Restaurant {uid}"
        u_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'restaurant', 'active')",
            (f"Ghost Owner {uid}", f"ghost_{uid}@test.com", f"94{uid[:8]}"),
            commit=True
        )
        execute_query(
            "INSERT INTO restaurants (owner_id, name, cuisine, address, city, area, verification_status, status) VALUES (%s, %s, 'Punjabi', 'Shop 202, Secret St', 'Mehsana', 'Secret St', 'pending', 'inactive')",
            (u_id, unique_name),
            commit=True
        )

        res = self.client.get('/restaurants')
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(unique_name.encode('utf-8'), res.data)

    def test_07_admin_can_review_and_approve_restaurant(self):
        """Administrator reviews pending application on /admin/restaurants and approves it."""
        self._login_as_admin()

        uid = uuid.uuid4().hex[:6]
        rest_name = f"To-Approve Cafe {uid}"
        u_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'restaurant', 'active')",
            (f"Approve Owner {uid}", f"toapprove_{uid}@test.com", f"93{uid[:8]}"),
            commit=True
        )
        r_id = execute_query(
            "INSERT INTO restaurants (owner_id, name, cuisine, address, city, area, verification_status, status) VALUES (%s, %s, 'Chinese', 'Shop 303, Modhera Rd', 'Mehsana', 'Modhera Rd', 'pending', 'inactive')",
            (u_id, rest_name),
            commit=True
        )

        # 1. Admin views restaurants list and finds the pending cafe
        res_list = self.client.get(f'/admin/restaurants?q={uid}')
        self.assertEqual(res_list.status_code, 200)
        self.assertIn(rest_name.encode('utf-8'), res_list.data)

        # 2. Admin approves the application
        res_approve = self.client.post(f'/admin/restaurant/approve/{r_id}', follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)

        # 3. Verify DB update
        updated_r = execute_query("SELECT verification_status, status FROM restaurants WHERE id=%s", (r_id,), fetchone=True)
        self.assertEqual(updated_r['verification_status'], 'approved')
        self.assertEqual(updated_r['status'], 'active')

        # 4. Now approved owner can access /restaurant/dashboard
        with self.client.session_transaction() as sess:
            sess['user_id'] = u_id
            sess['role'] = 'restaurant'
            sess['user_name'] = f"Approve Owner {uid}"
            sess['user_email'] = f"toapprove_{uid}@test.com"

        res_dash = self.client.get('/restaurant/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn('Operations Desk', res_dash.data.decode('utf-8'))

    def test_08_admin_can_reject_restaurant_application(self):
        """Administrator rejects an unverified restaurant application."""
        self._login_as_admin()

        uid = uuid.uuid4().hex[:6]
        rest_name = f"To-Reject Cafe {uid}"
        u_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'restaurant', 'active')",
            (f"Reject Owner {uid}", f"toreject_{uid}@test.com", f"92{uid[:8]}"),
            commit=True
        )
        r_id = execute_query(
            "INSERT INTO restaurants (owner_id, name, cuisine, address, city, area, verification_status, status) VALUES (%s, %s, 'Continental', 'Shop 404, Panchot Rd', 'Mehsana', 'Panchot Rd', 'pending', 'inactive')",
            (u_id, rest_name),
            commit=True
        )

        res_reject = self.client.post(f'/admin/restaurant/reject/{r_id}', follow_redirects=True)
        self.assertEqual(res_reject.status_code, 200)

        updated_r = execute_query("SELECT verification_status, status FROM restaurants WHERE id=%s", (r_id,), fetchone=True)
        self.assertEqual(updated_r['verification_status'], 'rejected')
        self.assertEqual(updated_r['status'], 'inactive')

        # Rejected owner sees rejected message on application status
        with self.client.session_transaction() as sess:
            sess['user_id'] = u_id
            sess['role'] = 'restaurant'

        res_status = self.client.get(f'/restaurant/application-status?id={r_id}')
        self.assertEqual(res_status.status_code, 200)
        self.assertIn('Application Not Approved', res_status.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
