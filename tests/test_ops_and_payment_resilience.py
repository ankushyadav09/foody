"""
tests/test_ops_and_payment_resilience.py – Regression tests for:
1. Razorpay checkout resilience (no AttributeError when unconfigured, friendly JSON from API)
2. Razorpay checkout with configured keys (mocked SDK client)
3. Operations Center role-based access control and isolation
4. Audit trail logging and display
"""

import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from config import Config
from database import execute_query


class TestOpsAndPaymentResilience(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_razorpay_checkout_without_credentials_no_crash(self):
        """Verify customer checkout page does not crash with AttributeError when Razorpay is not configured."""
        with patch.object(Config, 'RAZORPAY_KEY_ID', ''), patch.object(Config, 'RAZORPAY_KEY_SECRET', ''):
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['user_name'] = 'Test Customer'
                sess['role'] = 'customer'

            # Ensure user has an active cart with an item
            cart = execute_query("SELECT id FROM cart WHERE user_id=1 AND status='active'", fetchone=True)
            if not cart:
                execute_query("INSERT INTO cart (user_id, status) VALUES (1, 'active')", commit=True)
                cart = execute_query("SELECT id FROM cart WHERE user_id=1 AND status='active'", fetchone=True)
            execute_query("UPDATE cart SET status='active' WHERE id=%s", (cart['id'],), commit=True)
            
            cart_item = execute_query("SELECT id FROM cart_items WHERE cart_id=%s", (cart['id'],), fetchone=True)
            if not cart_item:
                food = execute_query("SELECT id, price FROM food_items LIMIT 1", fetchone=True)
                execute_query(
                    "INSERT INTO cart_items (cart_id, food_item_id, quantity, price) VALUES (%s, %s, 1, %s)",
                    (cart['id'], food['id'], food['price']), commit=True
                )

            res = self.client.get('/customer/checkout')
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Checkout', res.data)
            # Ensure no AttributeError trace occurred
            self.assertNotIn(b'AttributeError', res.data)

    def test_02_payment_create_order_without_credentials_returns_400(self):
        """Verify /api/payment/create-order returns clean JSON 400 when keys are missing."""
        with patch.object(Config, 'RAZORPAY_KEY_ID', ''), patch.object(Config, 'RAZORPAY_KEY_SECRET', ''):
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['role'] = 'customer'

            res = self.client.post('/api/payment/create-order', json={'amount': 250})
            self.assertEqual(res.status_code, 400)
            json_data = res.get_json()
            self.assertFalse(json_data['success'])
            self.assertIn('not configured', json_data['error'].lower())

    def test_03_payment_create_order_with_credentials_mock(self):
        """Verify /api/payment/create-order uses Razorpay client when keys are set."""
        with patch.object(Config, 'RAZORPAY_KEY_ID', 'rzp_test_MOCK123'), patch.object(Config, 'RAZORPAY_KEY_SECRET', 'mock_secret_key'):
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['role'] = 'customer'

            mock_rzp_instance = MagicMock()
            mock_rzp_instance.order.create.return_value = {
                'id': 'order_mock_777',
                'amount': 50000,
                'currency': 'INR'
            }

            with patch('razorpay.Client', return_value=mock_rzp_instance):
                res = self.client.post('/api/payment/create-order', json={'amount': 500})
                self.assertEqual(res.status_code, 200)
                json_data = res.get_json()
                self.assertTrue(json_data['success'])
                self.assertEqual(json_data['order_id'], 'order_mock_777')
                self.assertEqual(json_data['key'], 'rzp_test_MOCK123')

    def test_04_operations_center_access_control(self):
        """Verify /ops properly redirects operational roles and strictly blocks customers."""
        # 1. Anonymous user visiting /ops
        res = self.client.get('/ops')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/auth/login', res.headers['Location'])

        # 2. Customer user visiting /ops -> strictly denied
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'customer'
        res = self.client.get('/ops', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers['Location'], '/')

        # 3. Customer directly accessing privileged admin dashboard -> denied
        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers['Location'], '/')

        # 4. Customer directly accessing privileged restaurant dashboard -> denied
        res = self.client.get('/restaurant/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers['Location'], '/')

        # 5. Customer directly accessing privileged delivery dashboard -> denied
        res = self.client.get('/delivery/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers['Location'], '/')

        # 6. Admin visiting /ops -> routed to admin dashboard
        admin_user = execute_query("SELECT id FROM users WHERE role='admin' LIMIT 1", fetchone=True)
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
            sess['role'] = 'admin'
        res = self.client.get('/ops', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/dashboard', res.headers['Location'])

        # 7. Restaurant owner visiting /ops -> routed to restaurant dashboard
        rest_user = execute_query("SELECT id FROM users WHERE role='restaurant' LIMIT 1", fetchone=True)
        with self.client.session_transaction() as sess:
            sess['user_id'] = rest_user['id']
            sess['role'] = 'restaurant'
        res = self.client.get('/ops', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/restaurant/dashboard', res.headers['Location'])

        # 8. Delivery partner visiting /ops -> routed to delivery dashboard
        deliv_user = execute_query("SELECT id FROM users WHERE role='delivery' LIMIT 1", fetchone=True)
        with self.client.session_transaction() as sess:
            sess['user_id'] = deliv_user['id']
            sess['role'] = 'delivery'
        res = self.client.get('/ops', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/delivery/dashboard', res.headers['Location'])

    def test_05_admin_audit_trail_route(self):
        """Verify /admin/activity returns 200 for admin and renders audit stream."""
        admin_user = execute_query("SELECT id FROM users WHERE role='admin' LIMIT 1", fetchone=True)
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
            sess['role'] = 'admin'
            sess['user_name'] = 'Super Admin'

        # Record a test audit log
        from utils.helpers import log_activity
        log_activity(admin_user['id'], 'TEST_VERIFICATION_EVENT', 'Automated test recorded an audit event')

        res = self.client.get('/admin/activity')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Operations Audit Trail', res.data)
        self.assertIn(b'TEST_VERIFICATION_EVENT', res.data)


if __name__ == '__main__':
    unittest.main()
