"""
tests/test_order_and_tracking_lifecycle.py – Comprehensive End-to-End Order & Live Tracking Test
"""

import unittest
from werkzeug.security import generate_password_hash
from app import create_app
from database import execute_query

class TestOrderAndTrackingLifecycle(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_complete_order_and_tracking_lifecycle(self):
        # ── STEP 1: Customer Login & Cart Add ─────────────────────────────
        res = self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Get an available food item
        food = execute_query("SELECT id, restaurant_id, price FROM food_items WHERE availability=1 LIMIT 1", fetchone=True)
        self.assertIsNotNone(food)

        # Add to cart via API
        res = self.client.post('/api/cart/add', json={
            'food_id': food['id'],
            'quantity': 2
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        # ── STEP 2: Checkout & Place Order (Demo Payment) ─────────────────
        cust_user = execute_query("SELECT id FROM users WHERE email='customer@foodiehunter.com'", fetchone=True)
        addr = execute_query("SELECT id FROM addresses WHERE user_id=%s LIMIT 1", (cust_user['id'],), fetchone=True)
        addr_id = addr['id'] if addr else None

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': addr_id or '',
            'new_address': 'Radhanpur Road, Mehsana, Gujarat' if not addr_id else '',
            'discount': 0
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        # Extract created order
        order = execute_query(
            "SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC LIMIT 1",
            (cust_user['id'],), fetchone=True
        )
        self.assertIsNotNone(order)
        order_id = order['id']
        self.assertEqual(order['order_status'], 'placed')
        self.assertTrue(order['order_code'].startswith('FH-2026-'))

        # ── STEP 3: Restaurant Owner Acknowledges & Cooks Order ───────────
        # Logout customer & Login restaurant
        self.client.get('/auth/logout')
        rest_owner = execute_query("SELECT email FROM users WHERE role='restaurant' LIMIT 1", fetchone=True)
        self.client.post('/auth/login', data={
            'email': rest_owner['email'],
            'password': 'password123'
        }, follow_redirects=True)

        # Update restaurant order status to confirmed
        res = self.client.post('/restaurant/order/update-status', data={
            'order_id': order_id,
            'status': 'confirmed'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        curr = execute_query("SELECT order_status FROM orders WHERE id=%s", (order_id,), fetchone=True)
        self.assertEqual(curr['order_status'], 'confirmed')

        # Update to preparing
        res = self.client.post('/restaurant/order/update-status', data={
            'order_id': order_id,
            'status': 'preparing'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Update to ready (triggers automated courier dispatch)
        res = self.client.post('/restaurant/order/update-status', data={
            'order_id': order_id,
            'status': 'ready'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        assignment = execute_query("SELECT * FROM delivery_assignments WHERE order_id=%s", (order_id,), fetchone=True)
        self.assertIsNotNone(assignment, "Delivery assignment should be automatically generated when order is ready.")

        # ── STEP 4: Customer Live Tracking Verification ───────────────────
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        res_track = self.client.get(f'/api/orders/{order_id}/tracking')
        self.assertEqual(res_track.status_code, 200)
        track_data = res_track.get_json()
        self.assertTrue(track_data['success'])
        self.assertIn('distance_remaining', track_data)
        self.assertIn('eta', track_data)
        self.assertIsNotNone(track_data['restaurant_location'])
        self.assertIsNotNone(track_data['customer_location'])

        # ── STEP 5: Delivery Partner GPS Updates & Transit ────────────────
        self.client.get('/auth/logout')
        execute_query("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash('password123'), assignment['partner_id']), commit=True)
        partner_user = execute_query("SELECT email FROM users WHERE id=%s", (assignment['partner_id'],), fetchone=True)
        self.client.post('/delivery/login', data={
            'email': partner_user['email'],
            'password': 'password123'
        }, follow_redirects=True)

        # Rider starts delivery
        res = self.client.post(f'/delivery/order/pickup/{assignment["id"]}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        curr_order = execute_query("SELECT order_status FROM orders WHERE id=%s", (order_id,), fetchone=True)
        self.assertEqual(curr_order['order_status'], 'out_for_delivery')

        # Send live GPS beacon
        res_loc = self.client.post('/api/delivery/location', json={
            'order_id': order_id,
            'latitude': 23.5910,
            'longitude': 72.3710
        })
        self.assertEqual(res_loc.status_code, 200)
        self.assertTrue(res_loc.get_json()['success'])

        # Verify breadcrumb saved in MySQL
        loc_row = execute_query(
            "SELECT * FROM delivery_locations WHERE order_id=%s ORDER BY recorded_at DESC LIMIT 1",
            (order_id,), fetchone=True
        )
        self.assertIsNotNone(loc_row)
        self.assertAlmostEqual(float(loc_row['latitude']), 23.5910, places=3)

        # ── STEP 6: Demo Simulation Mode (Requirement #59) ────────────────
        res_sim = self.client.post(f'/api/orders/{order_id}/simulate-step', json={'progress': 0.85})
        self.assertEqual(res_sim.status_code, 200)
        sim_data = res_sim.get_json()
        self.assertEqual(sim_data['mode'], 'DEMO_TRACKING_MODE')
        self.assertIn('simulated_location', sim_data)

        # ── STEP 7: Complete Delivery & Verify Payout ─────────────────────
        rider_before = execute_query("SELECT total_deliveries, total_earnings FROM delivery_partners WHERE user_id=%s",
                                     (assignment['partner_id'],), fetchone=True)
        prev_drops = rider_before['total_deliveries'] if rider_before else 0

        res_deliv = self.client.post(f'/delivery/order/delivered/{assignment["id"]}', follow_redirects=True)
        self.assertEqual(res_deliv.status_code, 200)

        final_order = execute_query("SELECT order_status FROM orders WHERE id=%s", (order_id,), fetchone=True)
        self.assertEqual(final_order['order_status'], 'delivered')

        rider_after = execute_query("SELECT total_deliveries, total_earnings FROM delivery_partners WHERE user_id=%s",
                                    (assignment['partner_id'],), fetchone=True)
        self.assertEqual(rider_after['total_deliveries'], prev_drops + 1)

        # ── STEP 8: Customer Reviews Completed Order ──────────────────────
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        res_review = self.client.post(f'/customer/order/review/{order_id}', data={
            'rating': 5,
            'comment': 'Delicious hot Gujarati food, super fast delivery in Mehsana!'
        }, follow_redirects=True)
        self.assertEqual(res_review.status_code, 200)

        # Verify review in MySQL
        rev = execute_query("SELECT * FROM reviews WHERE order_id=%s", (order_id,), fetchone=True)
        self.assertIsNotNone(rev)
        self.assertEqual(rev['rating'], 5)
        self.assertIn('Delicious', rev['comment'])

if __name__ == '__main__':
    unittest.main()

