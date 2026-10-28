"""
tests/test_order_delivery_and_settlement_workflow.py
Production-Grade Workflow & Integration Test Suite:
1. Customer checkout and order creation with persisted timestamps & prep estimate
2. Eligible orders visibility in Delivery Partner Available Dispatches
3. Atomic Delivery Partner self-acceptance and duplicate-acceptance race prevention
4. Time-based live delivery tracking with persistent countdown & honest GPS telemetry
5. Delivery completion verification with delivered_at timestamp
6. Decimal-safe platform commission (15%), restaurant net payable, and rider payouts
7. Settlement idempotency preventing duplicate ledger entries or earnings inflation
8. Account isolation and RBAC security across Restaurant, Delivery Partner, and Customer
"""

import unittest
import uuid
from decimal import Decimal
from werkzeug.security import generate_password_hash
from app import create_app
from database import execute_query
from utils.settlement import calculate_order_financials, create_order_settlement, get_order_settlement


class TestOrderDeliveryAndSettlementWorkflow(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        self._setup_fixtures()

    def _setup_fixtures(self):
        # 1. Customer
        c = execute_query("SELECT id FROM users WHERE email='cust_settle_test@foody.com'", fetchone=True)
        if not c:
            self.customer_id = execute_query(
                "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'customer','active')",
                ('Pooja Customer', 'cust_settle_test@foody.com', generate_password_hash('password123')), commit=True
            )
        else:
            self.customer_id = c['id']

        # 2. Restaurant Owner & Restaurant
        ro = execute_query("SELECT id FROM users WHERE email='rest_settle_test@foody.com'", fetchone=True)
        if not ro:
            self.owner_id = execute_query(
                "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'restaurant','active')",
                ('Sanjay Owner', 'rest_settle_test@foody.com', generate_password_hash('password123')), commit=True
            )
        else:
            self.owner_id = ro['id']

        rest = execute_query("SELECT id FROM restaurants WHERE owner_id=%s", (self.owner_id,), fetchone=True)
        if not rest:
            self.restaurant_id = execute_query(
                """INSERT INTO restaurants (owner_id, name, cuisine, address, area, city, delivery_fee, commission_rate, prep_time, verification_status, status, is_open)
                   VALUES (%s, 'Sanjay Kitchen Hub', 'Gujarati Thali', 'Radhanpur Road', 'Mehsana City', 'Mehsana', 40.00, 15.00, '25 mins', 'approved', 'active', 1)""",
                (self.owner_id,), commit=True
            )
        else:
            self.restaurant_id = rest['id']

        # 3. Delivery Partner 1 (Primary)
        dp1 = execute_query("SELECT id FROM users WHERE email='rider1_settle_test@foody.com'", fetchone=True)
        if not dp1:
            self.rider1_id = execute_query(
                "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s,%s,'9898111001',%s,'delivery','active')",
                ('Rider One', 'rider1_settle_test@foody.com', generate_password_hash('password123')), commit=True
            )
            execute_query(
                "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-ZZ-1001', 'DL-GJ02-1001', 1, 1, 0, 0.00, 'approved')",
                (self.rider1_id,), commit=True
            )
        else:
            self.rider1_id = dp1['id']
            execute_query("UPDATE delivery_partners SET is_online=1, is_available=1 WHERE user_id=%s", (self.rider1_id,), commit=True)

        # 4. Delivery Partner 2 (Compromise / Second Rider)
        dp2 = execute_query("SELECT id FROM users WHERE email='rider2_settle_test@foody.com'", fetchone=True)
        if not dp2:
            self.rider2_id = execute_query(
                "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s,%s,'9898111002',%s,'delivery','active')",
                ('Rider Two', 'rider2_settle_test@foody.com', generate_password_hash('password123')), commit=True
            )
            execute_query(
                "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, total_deliveries, total_earnings, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-ZZ-1002', 'DL-GJ02-1002', 1, 1, 0, 0.00, 'approved')",
                (self.rider2_id,), commit=True
            )
        else:
            self.rider2_id = dp2['id']
            execute_query("UPDATE delivery_partners SET is_online=1, is_available=1 WHERE user_id=%s", (self.rider2_id,), commit=True)

    def test_01_order_creation_persists_prep_and_delivery_estimates(self):
        """Order creation calculates preparation time and persists estimated delivery time."""
        code = f"FH-EST-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee,
                                   discount, tax, tip_amount, payment_method, payment_status, order_status,
                                   prep_time_minutes, estimated_delivery_time, created_at)
               VALUES (%s, %s, 'Modhera Cross Road, Mehsana', %s, 540.00, 40.00, 0.00, 25.00, 15.00, 'cod', 'pending', 'confirmed',
                       25, DATETIME(CURRENT_TIMESTAMP, '+35 minutes'), CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )

        order = execute_query("SELECT * FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertIsNotNone(order)
        self.assertEqual(order['prep_time_minutes'], 25)
        self.assertIsNotNone(order['estimated_delivery_time'])
        self.assertEqual(float(order['delivery_fee']), 40.00)
        self.assertEqual(float(order['tip_amount']), 15.00)

    def test_02_unassigned_eligible_order_visible_on_rider_dashboard(self):
        """An eligible confirmed order appears in available orders for online delivery partners."""
        code = f"FH-AVAIL-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee, order_status, created_at)
               VALUES (%s, %s, 'Dairy Road, Mehsana', %s, 380.00, 40.00, 'confirmed', CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.rider1_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': self.rider1_id, 'role': 'delivery'}

        res = self.client.get('/delivery/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Available Delivery Requests', html)
        self.assertIn(code, html)
        self.assertIn('Accept Delivery Assignment', html)

    def test_03_atomic_order_acceptance_and_race_condition_prevention(self):
        """Rider 1 can accept order; Rider 2 attempting to accept the same order is safely rejected."""
        code = f"FH-RACE-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee, order_status, created_at)
               VALUES (%s, %s, 'Mal Godown Road, Mehsana', %s, 420.00, 40.00, 'confirmed', CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )

        # Rider 1 accepts
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.rider1_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': self.rider1_id, 'role': 'delivery'}

        res1 = self.client.post(f'/delivery/order/accept/{oid}', follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # Verify assignment in DB
        da = execute_query("SELECT * FROM delivery_assignments WHERE order_id=%s", (oid,), fetchone=True)
        self.assertIsNotNone(da)
        self.assertEqual(da['partner_id'], self.rider1_id)
        self.assertEqual(da['status'], 'assigned')

        # Rider 2 attempts to accept the exact same order
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.rider2_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': self.rider2_id, 'role': 'delivery'}

        res2 = self.client.post(f'/delivery/order/accept/{oid}', follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        html2 = res2.data.decode('utf-8')
        self.assertIn('already been accepted', html2)

        # Verify assignment was NOT stolen or overwritten
        da_after = execute_query("SELECT * FROM delivery_assignments WHERE order_id=%s", (oid,), fetchone=True)
        self.assertEqual(da_after['partner_id'], self.rider1_id)

    def test_04_time_based_tracking_and_honest_gps_telemetry(self):
        """Tracking endpoint returns accurate elapsed and remaining metrics, and honest GPS mode."""
        code = f"FH-TIME-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee, order_status,
                                   prep_time_minutes, estimated_delivery_time, created_at)
               VALUES (%s, %s, 'Pilaji Ganj, Mehsana', %s, 350.00, 40.00, 'out_for_delivery',
                       20, DATETIME(CURRENT_TIMESTAMP, '+30 minutes'), CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.customer_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.customer_id, 'role': 'customer'}

        res = self.client.get(f'/api/orders/{oid}/tracking')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('time_tracking', data)

        tt = data['time_tracking']
        self.assertEqual(tt['is_delivered'], False)
        self.assertGreaterEqual(tt['remaining_seconds'], 0)
        self.assertLessEqual(tt['progress_percent'], 95)  # Never 100% until delivered

        # GPS honesty verification (no pings yet)
        gps = data['gps_telemetry']
        self.assertFalse(gps['has_real_gps'])
        self.assertEqual(gps['mode'], 'status_progression')

        # Add genuine GPS ping
        execute_query(
            """INSERT INTO delivery_locations (delivery_partner_id, order_id, latitude, longitude, recorded_at)
               VALUES (%s, %s, 23.5901, 72.3712, CURRENT_TIMESTAMP)""",
            (self.rider1_id, oid), commit=True
        )

        res2 = self.client.get(f'/api/orders/{oid}/tracking')
        data2 = res2.get_json()
        self.assertTrue(data2['gps_telemetry']['has_real_gps'])
        self.assertEqual(data2['gps_telemetry']['mode'], 'real_satellite_gps')

    def test_05_timer_expiry_alone_never_marks_order_delivered(self):
        """Even if an order was placed 60 minutes ago, tracking remains unfulfilled without completion confirmation."""
        code = f"FH-OLD-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee, order_status,
                                   prep_time_minutes, estimated_delivery_time, created_at)
               VALUES (%s, %s, 'Nagori Dairy, Mehsana', %s, 400.00, 40.00, 'out_for_delivery',
                       25, DATETIME(CURRENT_TIMESTAMP, '-35 minutes'), DATETIME(CURRENT_TIMESTAMP, '-60 minutes'))""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.customer_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.customer_id, 'role': 'customer'}

        res = self.client.get(f'/api/orders/{oid}/tracking')
        data = res.get_json()
        tt = data['time_tracking']

        # Countdown shows arriving any moment, progress capped at 95%, order NOT delivered
        self.assertEqual(tt['is_delivered'], False)
        self.assertEqual(tt['countdown_display'], 'Arriving any moment')
        self.assertEqual(tt['progress_percent'], 95)

        # Verify DB order status is still out_for_delivery
        order = execute_query("SELECT order_status FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(order['order_status'], 'out_for_delivery')

    def test_06_decimal_safe_financial_calculation(self):
        """Financial calculation precisely deducts 15% platform commission and calculates rider earnings."""
        order_dict = {
            'id': 999,
            'subtotal': 600.00,
            'discount': 100.00,
            'delivery_fee': 40.00,
            'tax': 25.00,
            'tip_amount': 20.00,
            'total_amount': 585.00,
            'commission_rate': 15.00
        }
        fin = calculate_order_financials(order_dict)

        # Net food subtotal = 600 - 100 = 500
        # Platform commission = 500 * 15% = 75.00
        # Restaurant net payable = 500 - 75 = 425.00
        # Rider earnings = 40.00 + 20.00 = 60.00
        self.assertEqual(fin['platform_commission_amount'], 75.00)
        self.assertEqual(fin['restaurant_net_payable'], 425.00)
        self.assertEqual(fin['partner_payout_amount'], 60.00)
        self.assertEqual(fin['platform_commission_rate'], 15.00)

    def test_07_delivery_completion_triggers_automatic_settlement_idempotently(self):
        """Marking an order delivered creates an order_settlements record and prevents duplicate earnings on retry."""
        code = f"FH-COMP-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee,
                                   discount, tax, tip_amount, payment_method, payment_status, order_status, created_at)
               VALUES (%s, %s, 'Visnagar Road, Mehsana', %s, 560.00, 40.00, 50.00, 20.00, 10.00, 'cod', 'paid', 'out_for_delivery', CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )
        aid = execute_query(
            "INSERT INTO delivery_assignments (order_id, partner_id, status, assigned_at) VALUES (%s, %s, 'out_for_delivery', CURRENT_TIMESTAMP)",
            (oid, self.rider1_id), commit=True
        )

        # Initial lifetime earnings
        dp_before = execute_query("SELECT total_deliveries, total_earnings FROM delivery_partners WHERE user_id=%s", (self.rider1_id,), fetchone=True)
        initial_deliveries = dp_before['total_deliveries']
        initial_earnings = float(dp_before['total_earnings'])

        # Rider marks delivered
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.rider1_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': self.rider1_id, 'role': 'delivery'}

        res1 = self.client.post(f'/delivery/order/delivered/{aid}', follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # Verify order and assignment completed
        ord_db = execute_query("SELECT order_status, delivered_at FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(ord_db['order_status'], 'delivered')
        self.assertIsNotNone(ord_db['delivered_at'])

        # Verify settlement created
        settle1 = get_order_settlement(oid)
        self.assertIsNotNone(settle1)
        self.assertEqual(settle1['restaurant_id'], self.restaurant_id)
        self.assertEqual(settle1['partner_id'], self.rider1_id)
        self.assertEqual(settle1['partner_payout_amount'], 50.00)  # 40 fee + 10 tip
        self.assertEqual(settle1['restaurant_settlement_status'], 'settlement_pending')

        # Verify partner stats incremented once
        dp_after1 = execute_query("SELECT total_deliveries, total_earnings FROM delivery_partners WHERE user_id=%s", (self.rider1_id,), fetchone=True)
        self.assertEqual(dp_after1['total_deliveries'], initial_deliveries + 1)
        self.assertEqual(float(dp_after1['total_earnings']), initial_earnings + 50.00)

        # RETRY DUPLICATE COMPLETION: Call deliver_order again
        res2 = self.client.post(f'/delivery/order/delivered/{aid}', follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        # Assert no duplicate settlement created
        count = execute_query("SELECT COUNT(*) AS c FROM order_settlements WHERE order_id=%s", (oid,), fetchone=True)['c']
        self.assertEqual(count, 1)

        # Assert lifetime statistics did NOT double credit
        dp_after2 = execute_query("SELECT total_deliveries, total_earnings FROM delivery_partners WHERE user_id=%s", (self.rider1_id,), fetchone=True)
        self.assertEqual(dp_after2['total_deliveries'], initial_deliveries + 1)
        self.assertEqual(float(dp_after2['total_earnings']), initial_earnings + 50.00)

    def test_08_restaurant_account_isolation_on_sales_and_settlement(self):
        """Restaurant owner can only view their own sales and settlement ledger, not another kitchen's."""
        # Create second restaurant with different owner
        o2_id = execute_query(
            "INSERT INTO users (name, email, password_hash, role, status) VALUES (%s,%s,%s,'restaurant','active')",
            ('Chef Patel', f'patel_{uuid.uuid4().hex[:6]}@foody.com', generate_password_hash('password123')), commit=True
        )
        r2_id = execute_query(
            """INSERT INTO restaurants (owner_id, name, cuisine, address, area, city, delivery_fee, commission_rate, verification_status, status)
               VALUES (%s, 'Patel Sweets', 'Desserts', 'Bhavnagar Chowk', 'Mehsana City', 'Mehsana', 40.00, 15.00, 'approved', 'active')""",
            (o2_id,), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.owner_id
            sess['role'] = 'restaurant'
            sess['restaurant_auth'] = {'user_id': self.owner_id, 'restaurant_id': self.restaurant_id, 'role': 'restaurant'}

        res = self.client.get('/restaurant/sales')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Kitchen Sales & Settlement Ledger', html)
        self.assertNotIn('Patel Sweets', html)


    def test_09_newly_placed_order_immediately_visible_in_rider_available_pool(self):
        """Newly placed order (status='placed') is immediately visible to online delivery partners."""
        code = f"FH-NEW-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee,
                                   payment_method, payment_status, order_status, created_at)
               VALUES (%s, %s, 'Highway Circle, Mehsana', %s, 310.00, 40.00, 'cod', 'pending', 'placed', CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.rider1_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': self.rider1_id, 'role': 'delivery'}

        res = self.client.get('/delivery/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn(code, html)
        self.assertIn('Accept Delivery Assignment', html)

        # Also check /api/delivery/available-count
        res_cnt = self.client.get('/api/delivery/available-count')
        self.assertEqual(res_cnt.status_code, 200)
        self.assertGreaterEqual(res_cnt.get_json()['available_count'], 1)

    def test_10_premature_pickup_locked_until_kitchen_packs_food(self):
        """Rider cannot pick up order while restaurant is cooking ('preparing'); unlocks once 'ready_for_pickup'."""
        code = f"FH-LOCK-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee,
                                   payment_method, payment_status, order_status, created_at)
               VALUES (%s, %s, 'GIDC Gate 2, Mehsana', %s, 450.00, 40.00, 'cod', 'pending', 'preparing', CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )
        aid = execute_query(
            "INSERT INTO delivery_assignments (order_id, partner_id, status, assigned_at) VALUES (%s, %s, 'assigned', CURRENT_TIMESTAMP)",
            (oid, self.rider1_id), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.rider1_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': self.rider1_id, 'role': 'delivery'}

        # Rider attempts pickup while preparing
        res = self.client.post(f'/delivery/order/pickup/{aid}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('still preparing dishes', html)

        # Order must still be preparing
        curr_order = execute_query("SELECT order_status FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(curr_order['order_status'], 'preparing')

        # Now kitchen marks ready_for_pickup
        execute_query("UPDATE orders SET order_status='ready_for_pickup' WHERE id=%s", (oid,), commit=True)

        # Now pickup succeeds
        res_ok = self.client.post(f'/delivery/order/pickup/{aid}', follow_redirects=True)
        self.assertEqual(res_ok.status_code, 200)
        curr_order2 = execute_query("SELECT order_status FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(curr_order2['order_status'], 'out_for_delivery')

    def test_11_customer_tracking_timeline_all_7_stages_and_milestones(self):
        """Customer tracking template and API reflect all 7 stages and persisted milestones."""
        code = f"FH-7STG-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee,
                                   payment_method, payment_status, order_status, prep_time_minutes,
                                   estimated_delivery_time, created_at)
               VALUES (%s, %s, 'Jail Road, Mehsana', %s, 400.00, 40.00, 'cod', 'pending', 'ready_for_pickup',
                       20, DATETIME(CURRENT_TIMESTAMP, '+25 minutes'), CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )
        aid = execute_query(
            "INSERT INTO delivery_assignments (order_id, partner_id, status, assigned_at) VALUES (%s, %s, 'assigned', CURRENT_TIMESTAMP)",
            (oid, self.rider1_id), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.customer_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.customer_id, 'role': 'customer'}

        # 1. API endpoint verification
        res_api = self.client.get(f'/api/orders/{oid}/tracking')
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        self.assertEqual(data['stage_index'], 4)  # 0:placed, 1:confirmed, 2:prep, 3:ready, 4:assigned
        self.assertTrue(data['milestones']['placed'])
        self.assertTrue(data['milestones']['confirmed'])
        self.assertTrue(data['milestones']['preparing'])
        self.assertTrue(data['milestones']['ready_for_pickup'])
        self.assertTrue(data['milestones']['assigned'])
        self.assertFalse(data['milestones']['out_for_delivery'])
        self.assertFalse(data['milestones']['delivered'])
        self.assertEqual(data['has_partner'], True)
        self.assertEqual(data['delivery_partner']['name'], 'Rider One')

        # 2. Template render verification
        res_page = self.client.get(f'/customer/order/track/{oid}')
        self.assertEqual(res_page.status_code, 200)
        html = res_page.data.decode('utf-8')
        self.assertIn('step_placed', html)
        self.assertIn('step_confirmed', html)
        self.assertIn('step_preparing', html)
        self.assertIn('step_ready_for_pickup', html)
        self.assertIn('step_assigned', html)
        self.assertIn('step_out_for_delivery', html)
        self.assertIn('step_delivered', html)
        self.assertIn('DEMO TRACKING SIMULATOR', html)

    def test_12_demo_simulation_does_not_corrupt_database_or_falsify_delivery(self):
        """Simulation slider tests visual motion without inserting fake GPS pings or completing orders."""
        code = f"FH-SIM-{uuid.uuid4().hex[:6].upper()}"
        oid = execute_query(
            """INSERT INTO orders (user_id, restaurant_id, delivery_address, order_code, total_amount, delivery_fee,
                                   payment_method, payment_status, order_status, created_at)
               VALUES (%s, %s, 'Station Road, Mehsana', %s, 290.00, 40.00, 'cod', 'pending', 'placed', CURRENT_TIMESTAMP)""",
            (self.customer_id, self.restaurant_id, code), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.customer_id
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': self.customer_id, 'role': 'customer'}

        # Step simulation to 100%
        res = self.client.post(f'/api/orders/{oid}/simulate-step', json={'progress': 1.0})
        self.assertEqual(res.status_code, 200)
        sim_data = res.get_json()
        self.assertTrue(sim_data['success'])
        self.assertEqual(sim_data['mode'], 'DEMO_TRACKING_MODE')

        # Verify NO rows in delivery_locations
        loc_count = execute_query("SELECT COUNT(*) AS c FROM delivery_locations WHERE order_id=%s", (oid,), fetchone=True)['c']
        self.assertEqual(loc_count, 0)

        # Verify order status is STILL 'placed', NOT 'delivered'
        ord_db = execute_query("SELECT order_status, delivered_at FROM orders WHERE id=%s", (oid,), fetchone=True)
        self.assertEqual(ord_db['order_status'], 'placed')
        self.assertIsNone(ord_db['delivered_at'])

        # Verify tracking telemetry still honestly reports no real GPS
        res_track = self.client.get(f'/api/orders/{oid}/tracking')
        track_json = res_track.get_json()
        self.assertFalse(track_json['gps_telemetry']['has_real_gps'])
        self.assertEqual(track_json['is_delivered'], False)


if __name__ == '__main__':
    unittest.main()
