"""
tests/test_live_dispatch_and_tracking_repair.py

Comprehensive End-to-End Automated Test Suite covering:
1. Dispatch feed: real-time unassigned orders, status exclusions, offline riders, and payload integrity.
2. Assignment concurrency & RBAC: single atomic claim, 409 conflict on duplicate acceptance, unapproved rider rejection.
3. Authoritative customer tracking: 7 lifecycle stages synchronization, stage 4 on rider acceptance, pickup locking until ready.
4. Pickup & completion: authorized rider validation, in-transit transition, idempotent settlement (exactly once).
"""

import unittest
import uuid
from decimal import Decimal
from werkzeug.security import generate_password_hash
from app import create_app
from database import execute_query
from utils.settlement import create_order_settlement, get_order_settlement


class TestLiveDispatchAndTrackingRepair(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        self._setup_fixtures()

    def _setup_fixtures(self):
        # 1. Test Customer
        c = execute_query("SELECT id FROM users WHERE email='cust_live_repair@foody.com'", fetchone=True)
        if not c:
            self.customer_id = execute_query(
                "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'customer','active')",
                ('Aarav Customer', 'cust_live_repair@foody.com', generate_password_hash('password123')), commit=True
            )
        else:
            self.customer_id = c['id']

        # 2. Test Restaurant
        ro = execute_query("SELECT id FROM users WHERE email='rest_live_repair@foody.com'", fetchone=True)
        if not ro:
            self.owner_id = execute_query(
                "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'restaurant','active')",
                ('Vikram Chef', 'rest_live_repair@foody.com', generate_password_hash('password123')), commit=True
            )
        else:
            self.owner_id = ro['id']

        rest = execute_query("SELECT id FROM restaurants WHERE owner_id=%s", (self.owner_id,), fetchone=True)
        if not rest:
            self.restaurant_id = execute_query(
                """INSERT INTO restaurants (owner_id, name, cuisine, address, area, city, delivery_fee, commission_rate, prep_time, verification_status, status, is_open)
                   VALUES (%s, 'Vikram Kitchen Hub', 'North Indian', 'Highway Cross Rd', 'Mehsana City', 'Mehsana', 40.00, 15.00, '25 mins', 'approved', 'active', 1)""",
                (self.owner_id,), commit=True
            )
        else:
            self.restaurant_id = rest['id']

        # 3. Rider Alpha (Approved & Online)
        r_a = execute_query("SELECT id FROM users WHERE email='rider_alpha_repair@foody.com'", fetchone=True)
        if not r_a:
            self.rider_alpha_id = execute_query(
                "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s,%s,'9898220001',%s,'delivery','active')",
                ('Rider Alpha', 'rider_alpha_repair@foody.com', generate_password_hash('password123')), commit=True
            )
            execute_query(
                "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-AL-1001', 'DL-GJ02-AL01', 1, 1, 0, 0.00, 'approved')",
                (self.rider_alpha_id,), commit=True
            )
        else:
            self.rider_alpha_id = r_a['id']
            execute_query("UPDATE delivery_partners SET is_online=1, is_available=1, verification_status='approved' WHERE user_id=%s", (self.rider_alpha_id,), commit=True)
            execute_query("UPDATE users SET status='active' WHERE id=%s", (self.rider_alpha_id,), commit=True)

        # 4. Rider Beta (Approved & Online, Concurrency rival)
        r_b = execute_query("SELECT id FROM users WHERE email='rider_beta_repair@foody.com'", fetchone=True)
        if not r_b:
            self.rider_beta_id = execute_query(
                "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s,%s,'9898220002',%s,'delivery','active')",
                ('Rider Beta', 'rider_beta_repair@foody.com', generate_password_hash('password123')), commit=True
            )
            execute_query(
                "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-BE-2002', 'DL-GJ02-BE02', 1, 1, 0, 0.00, 'approved')",
                (self.rider_beta_id,), commit=True
            )
        else:
            self.rider_beta_id = r_b['id']
            execute_query("UPDATE delivery_partners SET is_online=1, is_available=1, verification_status='approved' WHERE user_id=%s", (self.rider_beta_id,), commit=True)
            execute_query("UPDATE users SET status='active' WHERE id=%s", (self.rider_beta_id,), commit=True)

        # 5. Rider Inactive / Unapproved
        r_pend = execute_query("SELECT id FROM users WHERE email='rider_pending_repair@foody.com'", fetchone=True)
        if not r_pend:
            self.rider_pending_id = execute_query(
                "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s,%s,'9898220003',%s,'delivery','pending')",
                ('Rider Pending', 'rider_pending_repair@foody.com', generate_password_hash('password123')), commit=True
            )
            execute_query(
                "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-PE-3003', 'DL-GJ02-PE03', 1, 1, 0, 0.00, 'pending')",
                (self.rider_pending_id,), commit=True
            )
        else:
            self.rider_pending_id = r_pend['id']

    def _login_as(self, user_id, role, name='User'):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = role
            sess['user_name'] = name
            if role == 'customer':
                sess['customer_auth'] = {'user_id': user_id, 'role': 'customer', 'name': name}
            elif role == 'delivery':
                sess['delivery_auth'] = {'user_id': user_id, 'role': 'delivery', 'name': name}
            elif role == 'restaurant':
                sess['restaurant_auth'] = {'user_id': user_id, 'role': 'restaurant', 'name': name, 'restaurant_id': self.restaurant_id}

    def _create_test_order(self, status='placed', payment_status='paid'):
        code = f"FH-REP-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee,
                                   discount, tax, tip_amount, payment_method, payment_status, order_status,
                                   prep_time_minutes, estimated_delivery_time, created_at)
               VALUES (%s, %s, 'Sector 7, Gandhinagar Rd, Mehsana', %s, 450.00, 40.00, 0.00, 20.00, 10.00, 'online', %s, %s,
                       25, DATETIME(CURRENT_TIMESTAMP, '+35 minutes'), CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code, payment_status, status), commit=True
        )
        return oid, code

    # ── 1. DISPATCH FEED TESTS ──────────────────────────────────────────

    def test_01_new_eligible_order_appears_in_live_dispatch_feed(self):
        """Newly placed eligible order appears in the delivery dispatch API for online riders."""
        oid, code = self._create_test_order(status='placed', payment_status='paid')

        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        res = self.client.get('/api/delivery/dispatches')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        avail_ids = [o['id'] for o in data['available_orders']]
        self.assertIn(oid, avail_ids)

        # Confirm order details in dispatch offer
        order_offer = next(o for o in data['available_orders'] if o['id'] == oid)
        self.assertEqual(order_offer['order_code'], code)
        self.assertEqual(order_offer['restaurant_name'], 'Vikram Kitchen Hub')
        self.assertIn('Highway Cross Rd', order_offer['restaurant_address'])
        self.assertEqual(float(order_offer['delivery_fee']), 40.0)
        self.assertEqual(float(order_offer['total_amount']), 450.0)

    def test_02_ineligible_and_cancelled_orders_excluded_from_dispatch(self):
        """Cancelled, delivered, or unconfirmed unpaid orders do not appear in dispatch pool."""
        oid_cancel, _ = self._create_test_order(status='cancelled', payment_status='paid')
        oid_delivered, _ = self._create_test_order(status='delivered', payment_status='paid')
        oid_unpaid, _ = self._create_test_order(status='placed', payment_status='pending')

        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        res = self.client.get('/api/delivery/dispatches')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        avail_ids = [o['id'] for o in data['available_orders']]

        self.assertNotIn(oid_cancel, avail_ids)
        self.assertNotIn(oid_delivered, avail_ids)
        self.assertNotIn(oid_unpaid, avail_ids)

    def test_03_offline_rider_does_not_receive_available_orders(self):
        """Offline delivery partner receives empty dispatch pool to prevent dispatching paused riders."""
        oid, _ = self._create_test_order(status='placed', payment_status='paid')

        execute_query("UPDATE delivery_partners SET is_online=0 WHERE user_id=%s", (self.rider_alpha_id,), commit=True)
        try:
            self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
            res = self.client.get('/api/delivery/dispatches')
            data = res.get_json()
            self.assertEqual(res.status_code, 200)
            self.assertFalse(data['is_online'])
            self.assertEqual(len(data['available_orders']), 0)
        finally:
            execute_query("UPDATE delivery_partners SET is_online=1 WHERE user_id=%s", (self.rider_alpha_id,), commit=True)

    # ── 2. ASSIGNMENT & CONCURRENCY TESTS ────────────────────────────────

    def test_04_rider_can_accept_order_and_moves_to_active_deliveries(self):
        """Rider accepts unassigned order: claims assignment, moves to active drops, order is confirmed."""
        oid, code = self._create_test_order(status='placed', payment_status='paid')

        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        res_accept = self.client.post(f'/api/delivery/order/accept/{oid}')
        self.assertEqual(res_accept.status_code, 200)
        acc_data = res_accept.get_json()
        self.assertTrue(acc_data['success'])

        # Verify DB assignment
        asg = execute_query("SELECT * FROM delivery_assignments WHERE order_id=%s", (oid,), fetchone=True)
        self.assertIsNotNone(asg)
        self.assertEqual(asg['partner_id'], self.rider_alpha_id)
        self.assertEqual(asg['status'], 'assigned')

        # Verify order status updated to confirmed
        order = execute_query("SELECT order_status FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(order['order_status'], 'confirmed')

        # Verify order now in Rider Alpha's active tasks
        res_disp = self.client.get('/api/delivery/dispatches')
        disp_data = res_disp.get_json()
        active_order_ids = [a['order_id'] for a in disp_data['active_deliveries']]
        self.assertIn(oid, active_order_ids)

        # Verify order removed from available pool
        avail_ids = [o['id'] for o in disp_data['available_orders']]
        self.assertNotIn(oid, avail_ids)

    def test_05_duplicate_acceptance_returns_409_conflict(self):
        """Second rider attempting to claim the same order receives HTTP 409 conflict."""
        oid, code = self._create_test_order(status='placed', payment_status='paid')

        # Rider Alpha claims first
        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        res_a = self.client.post(f'/api/delivery/order/accept/{oid}')
        self.assertEqual(res_a.status_code, 200)

        # Rider Beta attempts duplicate claim
        self._login_as(self.rider_beta_id, 'delivery', 'Rider Beta')
        res_b = self.client.post(f'/api/delivery/order/accept/{oid}')
        self.assertEqual(res_b.status_code, 409)
        data_b = res_b.get_json()
        self.assertFalse(data_b['success'])
        self.assertTrue(data_b.get('conflict'))

        # DB confirms single assignment strictly to Rider Alpha
        assignments = execute_query("SELECT * FROM delivery_assignments WHERE order_id=%s", (oid,), fetchall=True)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]['partner_id'], self.rider_alpha_id)

    def test_06_unapproved_or_pending_rider_cannot_accept_orders(self):
        """Riders pending approval cannot claim deliveries."""
        oid, _ = self._create_test_order(status='placed', payment_status='paid')

        self._login_as(self.rider_pending_id, 'delivery', 'Rider Pending')
        res = self.client.post(f'/api/delivery/order/accept/{oid}')
        self.assertIn(res.status_code, (400, 403))
        data = res.get_json()
        self.assertFalse(data['success'])

    # ── 3. CUSTOMER TRACKING TESTS ──────────────────────────────────────

    def test_07_customer_tracking_advances_to_assigned_on_rider_acceptance(self):
        """Authoritative tracking synchronizes: stage_index advances to 4 ('Delivery Partner Assigned')."""
        oid, _ = self._create_test_order(status='placed', payment_status='paid')

        # Before acceptance: stage 0 (placed)
        self._login_as(self.customer_id, 'customer', 'Aarav Customer')
        res_before = self.client.get(f'/api/orders/{oid}/tracking')
        self.assertEqual(res_before.status_code, 200)
        data_before = res_before.get_json()
        self.assertEqual(data_before['stage_index'], 0)
        self.assertFalse(data_before['has_partner'])

        # Rider Alpha accepts
        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        self.client.post(f'/api/delivery/order/accept/{oid}')

        # After acceptance: stage 4 (Delivery Partner Assigned)
        self._login_as(self.customer_id, 'customer', 'Aarav Customer')
        res_after = self.client.get(f'/api/orders/{oid}/tracking')
        self.assertEqual(res_after.status_code, 200)
        data_after = res_after.get_json()
        self.assertEqual(data_after['stage_index'], 4)
        self.assertTrue(data_after['has_partner'])
        self.assertEqual(data_after['delivery_partner']['id'], self.rider_alpha_id)
        self.assertEqual(data_after['delivery_partner']['name'], 'Rider Alpha')
        self.assertTrue(data_after['milestones']['assigned'])

    def test_08_pickup_locked_until_kitchen_marks_ready(self):
        """Rider cannot pick up order while kitchen is still cooking; unlocks upon 'ready_for_pickup'."""
        oid, _ = self._create_test_order(status='placed', payment_status='paid')

        # Rider Alpha accepts
        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        self.client.post(f'/api/delivery/order/accept/{oid}')
        asg = execute_query("SELECT id FROM delivery_assignments WHERE order_id=%s", (oid,), fetchone=True)
        asg_id = asg['id']

        # Restaurant marks order 'preparing'
        execute_query("UPDATE orders SET order_status='preparing' WHERE id=%s", (oid,), commit=True)

        # Rider attempts pickup while preparing -> 400 Bad Request (Locked)
        res_early = self.client.post(f'/api/delivery/order/pickup/{asg_id}')
        self.assertEqual(res_early.status_code, 400)
        data_early = res_early.get_json()
        self.assertFalse(data_early['success'])
        self.assertIn("still preparing", data_early['message'])

        # Restaurant marks order 'ready_for_pickup'
        execute_query("UPDATE orders SET order_status='ready_for_pickup' WHERE id=%s", (oid,), commit=True)

        # Rider executes pickup -> 200 OK
        res_pickup = self.client.post(f'/api/delivery/order/pickup/{asg_id}')
        self.assertEqual(res_pickup.status_code, 200)
        data_pickup = res_pickup.get_json()
        self.assertTrue(data_pickup['success'])
        self.assertEqual(data_pickup['order_status'], 'out_for_delivery')

        # Customer tracking advances to stage 5 (Picked Up / Out for Delivery)
        self._login_as(self.customer_id, 'customer', 'Aarav Customer')
        res_track = self.client.get(f'/api/orders/{oid}/tracking')
        data_track = res_track.get_json()
        self.assertEqual(data_track['stage_index'], 5)
        self.assertEqual(data_track['order_status'], 'out_for_delivery')
        self.assertTrue(data_track['milestones']['out_for_delivery'])

    # ── 4. COMPLETION & SETTLEMENT IDEMPOTENCY TESTS ─────────────────────

    def test_09_authorized_delivery_completion_persists_and_settles(self):
        """Assigned rider completes delivery: marks delivered, timestamps recorded, settlement created."""
        oid, _ = self._create_test_order(status='ready_for_pickup', payment_status='paid')

        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        self.client.post(f'/api/delivery/order/accept/{oid}')
        asg = execute_query("SELECT id FROM delivery_assignments WHERE order_id=%s", (oid,), fetchone=True)
        asg_id = asg['id']

        # Pick up order
        self.client.post(f'/api/delivery/order/pickup/{asg_id}')

        # Unassigned rider cannot complete delivery
        self._login_as(self.rider_beta_id, 'delivery', 'Rider Beta')
        res_unauth = self.client.post(f'/api/delivery/order/delivered/{asg_id}')
        self.assertIn(res_unauth.status_code, (403, 404))

        # Authorized Rider Alpha completes delivery
        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        res_deliv = self.client.post(f'/api/delivery/order/delivered/{asg_id}')
        self.assertEqual(res_deliv.status_code, 200)
        data_deliv = res_deliv.get_json()
        self.assertTrue(data_deliv['success'])
        self.assertEqual(data_deliv['order_status'], 'delivered')

        # Verify DB state
        order = execute_query("SELECT * FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(order['order_status'], 'delivered')
        self.assertIsNotNone(order['delivered_at'])

        asg_rec = execute_query("SELECT * FROM delivery_assignments WHERE id=%s", (asg_id,), fetchone=True)
        self.assertEqual(asg_rec['status'], 'delivered')
        self.assertIsNotNone(asg_rec['delivered_at'])

        # Verify settlement created
        settlement = get_order_settlement(oid)
        self.assertIsNotNone(settlement)
        self.assertEqual(settlement['partner_id'], self.rider_alpha_id)
        self.assertIn(settlement['partner_settlement_status'], ('settlement_pending', 'payout_initiated', 'settled'))
        self.assertGreater(float(settlement['partner_payout_amount']), 0)

        # Customer tracking confirms stage 6 (Delivered)
        self._login_as(self.customer_id, 'customer', 'Aarav Customer')
        res_track = self.client.get(f'/api/orders/{oid}/tracking')
        data_track = res_track.get_json()
        self.assertEqual(data_track['stage_index'], 6)
        self.assertTrue(data_track['is_delivered'])

    def test_10_repeated_completion_is_idempotent_no_duplicate_earnings(self):
        """Repeated completion requests return idempotent responses without duplicate settlement rows."""
        oid, _ = self._create_test_order(status='ready_for_pickup', payment_status='paid')

        self._login_as(self.rider_alpha_id, 'delivery', 'Rider Alpha')
        self.client.post(f'/api/delivery/order/accept/{oid}')
        asg = execute_query("SELECT id FROM delivery_assignments WHERE order_id=%s", (oid,), fetchone=True)
        asg_id = asg['id']
        self.client.post(f'/api/delivery/order/pickup/{asg_id}')

        # 1st completion
        res1 = self.client.post(f'/api/delivery/order/delivered/{asg_id}')
        self.assertEqual(res1.status_code, 200)

        # 2nd completion (replay)
        res2 = self.client.post(f'/api/delivery/order/delivered/{asg_id}')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2['success'])
        self.assertTrue(data2.get('idempotent', False))

        # Check order_settlements row count for this order
        settlements = execute_query("SELECT * FROM order_settlements WHERE order_id=%s", (oid,), fetchall=True)
        self.assertEqual(len(settlements), 1, "Exactly one settlement record must exist for the order")


if __name__ == '__main__':
    unittest.main()
