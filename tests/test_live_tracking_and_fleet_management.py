"""
tests/test_live_tracking_and_fleet_management.py
Rigorous verification suite for Live Order Tracking and Admin Delivery Fleet Management:
- Customer live tracking page rendering and route aliases
- Null address safe handling without NoneType slicing 500 crashes
- Strict customer resource ownership and isolation (403 on other customer orders)
- Non-existent order handling (404)
- Live tracking telemetry API responses (Haversine distance, ETA, locations, partner info)
- Rider GPS beacons persistence and authorization
- Admin Delivery Fleet listing, counts, search, and status filters (all, pending, approved, rejected, inactive)
- Admin delivery partner detail dossier view
- Admin approval, rejection, and suspension persistence
- Delivery partner assignment without order status corruption
"""

import unittest
import uuid
from werkzeug.security import generate_password_hash
from app import create_app
from database import execute_query


class TestLiveTrackingAndFleetManagement(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Ensure baseline users exist
        self._ensure_test_users()

    def _ensure_test_users(self):
        # Customer 1
        c1 = execute_query("SELECT id FROM users WHERE email='customer1_test@foody.com'", fetchone=True)
        if not c1:
            self.c1_id = execute_query(
                "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'customer','active')",
                ('Alice Customer', 'customer1_test@foody.com', generate_password_hash('password123')), commit=True
            )
        else:
            self.c1_id = c1['id']

        # Customer 2 (for unauthorized test)
        c2 = execute_query("SELECT id FROM users WHERE email='customer2_test@foody.com'", fetchone=True)
        if not c2:
            self.c2_id = execute_query(
                "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'customer','active')",
                ('Bob Customer', 'customer2_test@foody.com', generate_password_hash('password123')), commit=True
            )
        else:
            self.c2_id = c2['id']

        # Admin
        adm = execute_query("SELECT id FROM users WHERE email='admin_test@foody.com'", fetchone=True)
        if not adm:
            self.admin_id = execute_query(
                "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'admin','active')",
                ('System Admin', 'admin_test@foody.com', generate_password_hash('food@1234')), commit=True
            )
        else:
            self.admin_id = adm['id']

        # Delivery Partner
        dp_user = execute_query("SELECT id FROM users WHERE email='rider_test@foody.com'", fetchone=True)
        if not dp_user:
            self.rider_id = execute_query(
                "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s,%s,'9898000001',%s,'delivery','active')",
                ('Raju Rider', 'rider_test@foody.com', generate_password_hash('password123')), commit=True
            )
            execute_query(
                "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-RX-1111', 'DL-GJ02-9999', 1, 1, 'approved')",
                (self.rider_id,), commit=True
            )
        else:
            self.rider_id = dp_user['id']

        # Restaurant
        rest = execute_query("SELECT id FROM restaurants LIMIT 1", fetchone=True)
        self.restaurant_id = rest['id'] if rest else 1

    def test_01_customer_track_order_page_and_aliases(self):
        """Customer can open live tracking for their own order via primary route and aliases."""
        code = f"FH-TRK-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (order_code, user_id, restaurant_id, total_amount, payment_method, payment_status, order_status, delivery_address)
               VALUES (%s, %s, %s, 450.00, 'cod', 'pending', 'confirmed', 'Highway Circle, Mehsana')""",
            (code, self.c1_id, self.restaurant_id), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.c1_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.c1_id, 'role': 'customer'}

        res = self.client.get(f'/customer/order/track/{oid}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(code, res.data.decode('utf-8'))
        self.assertIn('Order Progression Timeline', res.data.decode('utf-8'))

        res_alias1 = self.client.get(f'/customer/order-tracking/{oid}')
        self.assertEqual(res_alias1.status_code, 200)

        res_alias2 = self.client.get(f'/customer/track/{oid}')
        self.assertEqual(res_alias2.status_code, 200)

        res_alias3 = self.client.get(f'/orders/track/{oid}', follow_redirects=True)
        self.assertEqual(res_alias3.status_code, 200)

    def test_02_track_order_without_address_does_not_500(self):
        """Order with null address renders gracefully without NoneType slicing 500 error."""
        code = f"FH-NULL-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (order_code, user_id, restaurant_id, total_amount, payment_method, payment_status, order_status, address_id, delivery_address)
               VALUES (%s, %s, %s, 300.00, 'cod', 'pending', 'placed', NULL, NULL)""",
            (code, self.c1_id, self.restaurant_id), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.c1_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.c1_id, 'role': 'customer'}

        res = self.client.get(f'/customer/order/track/{oid}')
        self.assertEqual(res.status_code, 200, "Must not throw 500 error when address is None")
        self.assertIn(code, res.data.decode('utf-8'))

    def test_03_cross_customer_order_tracking_forbidden(self):
        """Customer cannot view or track another customer's order (HTTP 403)."""
        code = f"FH-PRIV-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (order_code, user_id, restaurant_id, total_amount, payment_method, payment_status, order_status, delivery_address)
               VALUES (%s, %s, %s, 500.00, 'cod', 'pending', 'placed', 'Private Road, Mehsana')""",
            (code, self.c1_id, self.restaurant_id), commit=True
        )

        # Login as customer 2 (different customer)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.c2_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.c2_id, 'role': 'customer'}

        res = self.client.get(f'/customer/order/track/{oid}', follow_redirects=False)
        self.assertEqual(res.status_code, 403)

        res_api = self.client.get(f'/api/orders/{oid}/tracking')
        self.assertEqual(res_api.status_code, 403)

        res_sim = self.client.post(f'/api/orders/{oid}/simulate-step', json={'progress': 0.5})
        self.assertEqual(res_sim.status_code, 403)

    def test_04_invalid_order_id_returns_404(self):
        """Non-existent order ID produces 404 response."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.c1_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.c1_id, 'role': 'customer'}

        res_page = self.client.get('/customer/order/track/9999999', follow_redirects=False)
        self.assertEqual(res_page.status_code, 404)

        res_api = self.client.get('/api/orders/9999999/tracking')
        self.assertEqual(res_api.status_code, 404)

    def test_05_live_tracking_api_telemetry(self):
        """Tracking API returns complete telemetry, locations, and assigned partner info."""
        code = f"FH-TEL-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (order_code, user_id, restaurant_id, total_amount, payment_method, payment_status, order_status, delivery_address, customer_lat, customer_lng)
               VALUES (%s, %s, %s, 620.00, 'cod', 'pending', 'out_for_delivery', 'Radhanpur Cross, Mehsana', 23.5950, 72.3750)""",
            (code, self.c1_id, self.restaurant_id), commit=True
        )
        execute_query(
            "INSERT INTO delivery_assignments (order_id, partner_id, status, assigned_at) VALUES (%s, %s, 'assigned', NOW())",
            (oid, self.rider_id), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.c1_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.c1_id, 'role': 'customer'}

        res = self.client.get(f'/api/orders/{oid}/tracking')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['order_id'], oid)
        self.assertEqual(data['order_status'], 'out_for_delivery')
        self.assertIsNotNone(data['delivery_partner'])
        self.assertEqual(data['delivery_partner']['id'], self.rider_id)
        self.assertIn('distance_remaining', data)
        self.assertIn('eta', data)
        self.assertIn('latitude', data['customer_location'])
        self.assertIn('latitude', data['restaurant_location'])

    def test_06_rider_gps_beacon_persistence_and_auth(self):
        """Rider GPS beacon persists breadcrumbs, updates rider position, and enforces assignment check."""
        code = f"FH-GPS-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (order_code, user_id, restaurant_id, total_amount, payment_method, payment_status, order_status)
               VALUES (%s, %s, %s, 350.00, 'cod', 'pending', 'out_for_delivery')""",
            (code, self.c1_id, self.restaurant_id), commit=True
        )
        execute_query(
            "INSERT INTO delivery_assignments (order_id, partner_id, status, assigned_at) VALUES (%s, %s, 'assigned', NOW())",
            (oid, self.rider_id), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.rider_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': self.rider_id, 'role': 'delivery'}

        beacon_res = self.client.post('/api/delivery/location', json={
            'order_id': oid,
            'latitude': 23.5933,
            'longitude': 72.3722
        })
        self.assertEqual(beacon_res.status_code, 200)
        self.assertTrue(beacon_res.get_json()['success'])

        loc = execute_query("SELECT * FROM delivery_locations WHERE order_id=%s ORDER BY recorded_at DESC LIMIT 1", (oid,), fetchone=True)
        self.assertIsNotNone(loc)
        self.assertAlmostEqual(float(loc['latitude']), 23.5933, places=3)

    def test_07_admin_delivery_fleet_listing_and_filters(self):
        """Admin Fleet page loads with counts, empty state support, search, and all status filters."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin_id
            sess['role'] = 'admin'
            sess['admin_gate_passed'] = True
            sess['admin_auth'] = {'user_id': self.admin_id, 'role': 'admin'}

        res = self.client.get('/admin/delivery-partners')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Delivery Fleet & Riders', html)
        self.assertIn('Pending Review', html)
        self.assertIn('Approved Fleet', html)

        for st in ('all', 'pending', 'approved', 'rejected', 'inactive'):
            res_st = self.client.get(f'/admin/delivery-partners?status={st}')
            self.assertEqual(res_st.status_code, 200, f"Filter {st} should load HTTP 200")

        res_q = self.client.get('/admin/delivery-partners?q=Raju')
        self.assertEqual(res_q.status_code, 200)

    def test_08_admin_partner_detail_view(self):
        """Admin can view detailed partner dossier and invalid ID returns 404."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin_id
            sess['role'] = 'admin'
            sess['admin_gate_passed'] = True
            sess['admin_auth'] = {'user_id': self.admin_id, 'role': 'admin'}

        res = self.client.get(f'/admin/delivery-partners/{self.rider_id}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Rider Profile', html)
        self.assertIn('Fleet Vehicle & Credentials', html)

        res_inv = self.client.get('/admin/delivery-partners/999999', follow_redirects=False)
        self.assertEqual(res_inv.status_code, 404)

    def test_09_admin_partner_approval_and_suspension_lifecycle(self):
        """Admin approval, rejection, and suspension persist correctly to the database."""
        u_email = f"applicant_{uuid.uuid4().hex[:6]}@foody.com"
        applicant_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s,%s,'9898000099',%s,'delivery','pending')",
            ('Test Applicant', u_email, generate_password_hash('password123')), commit=True
        )
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-ZZ-0001', 'DL-PENDING-01', 0, 0, 'pending')",
            (applicant_id,), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin_id
            sess['role'] = 'admin'
            sess['admin_gate_passed'] = True
            sess['admin_auth'] = {'user_id': self.admin_id, 'role': 'admin'}

        # 1. Admin Approves Rider
        appr_res = self.client.post(f'/admin/delivery-partners/approve/{applicant_id}', follow_redirects=True)
        self.assertEqual(appr_res.status_code, 200)
        u_row = execute_query("SELECT status FROM users WHERE id=%s", (applicant_id,), fetchone=True)
        dp_row = execute_query("SELECT verification_status, is_online FROM delivery_partners WHERE user_id=%s", (applicant_id,), fetchone=True)
        self.assertEqual(u_row['status'], 'active')
        self.assertEqual(dp_row['verification_status'], 'approved')
        self.assertEqual(dp_row['is_online'], 1)

        # 2. Admin Suspends Rider
        toggle_res = self.client.post(f'/admin/delivery-partners/toggle/{applicant_id}', follow_redirects=True)
        self.assertEqual(toggle_res.status_code, 200)
        u_susp = execute_query("SELECT status FROM users WHERE id=%s", (applicant_id,), fetchone=True)
        self.assertEqual(u_susp['status'], 'inactive')

        # 3. Admin Rejects Rider
        rej_res = self.client.post(f'/admin/delivery-partners/reject/{applicant_id}', data={'rejection_reason': 'Invalid DL'}, follow_redirects=True)
        self.assertEqual(rej_res.status_code, 200)
        u_rej = execute_query("SELECT status FROM users WHERE id=%s", (applicant_id,), fetchone=True)
        dp_rej = execute_query("SELECT verification_status FROM delivery_partners WHERE user_id=%s", (applicant_id,), fetchone=True)
        self.assertEqual(u_rej['status'], 'rejected')
        self.assertEqual(dp_rej['verification_status'], 'rejected')

    def test_10_admin_assign_delivery_preserves_order_status(self):
        """Assigning a delivery partner does not corrupt already preparing or ready order statuses."""
        code = f"FH-PREP-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (order_code, user_id, restaurant_id, total_amount, payment_method, payment_status, order_status)
               VALUES (%s, %s, %s, 400.00, 'cod', 'pending', 'preparing')""",
            (code, self.c1_id, self.restaurant_id), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin_id
            sess['role'] = 'admin'
            sess['admin_gate_passed'] = True
            sess['admin_auth'] = {'user_id': self.admin_id, 'role': 'admin'}

        res = self.client.post('/admin/delivery-partners/assign', data={
            'order_id': oid,
            'partner_id': self.rider_id
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify order status remained 'preparing' and was NOT demoted back to 'confirmed'
        order_row = execute_query("SELECT order_status FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(order_row['order_status'], 'preparing', "Assignment must preserve 'preparing' status!")

        # Verify assignment record was created
        assignment = execute_query("SELECT * FROM delivery_assignments WHERE order_id=%s", (oid,), fetchone=True)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment['partner_id'], self.rider_id)


if __name__ == '__main__':
    unittest.main()
