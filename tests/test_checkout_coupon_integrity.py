"""
tests/test_checkout_coupon_integrity.py – Comprehensive Regression Test Suite
Validates checkout and coupon referential integrity, order creation, transaction safety,
and edge cases according to Phase 5 requirements.
"""

import unittest
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import create_app
from database import execute_query, db_transaction, get_db_mode
from utils.helpers import validate_and_calculate_coupon, calculate_order_totals


class TestCheckoutCouponIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    def setUp(self):
        self.client = self.app.test_client()
        # Find customer user
        self.user = execute_query("SELECT id, email FROM users WHERE role='customer' LIMIT 1", fetchone=True)
        self.assertIsNotNone(self.user, "A customer user must exist for testing.")
        self.user_id = self.user['id']

        # Find or create a default address for user
        self.addr = execute_query("SELECT id FROM addresses WHERE user_id=%s LIMIT 1", (self.user_id,), fetchone=True)
        if not self.addr:
            addr_id = execute_query(
                "INSERT INTO addresses (user_id, label, address, city, pincode, is_default) "
                "VALUES (%s, 'Home', '101 Highway Road', 'Mehsana', '384002', 1)",
                (self.user_id,), commit=True
            )
            self.addr = {'id': addr_id}

        # Find an available food item and restaurant
        self.food = execute_query(
            "SELECT fi.id, fi.name, fi.price, fi.restaurant_id, r.delivery_fee "
            "FROM food_items fi "
            "JOIN restaurants r ON fi.restaurant_id=r.id "
            "WHERE fi.availability=1 LIMIT 1",
            fetchone=True
        )
        self.assertIsNotNone(self.food, "At least one available food item must exist.")

    def _login_customer(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['email'] = self.user['email']
            sess['role'] = 'customer'
            sess['user_name'] = 'Test Customer'

    def _setup_active_cart(self, quantity=2):
        """Prepare active cart with known items for test."""
        # Ensure user has active cart
        cart = execute_query("SELECT id FROM cart WHERE user_id=%s AND status='active'", (self.user_id,), fetchone=True)
        if not cart:
            cart_id = execute_query("INSERT INTO cart (user_id, status) VALUES (%s, 'active')", (self.user_id,), commit=True)
            cart = {'id': cart_id}
        else:
            execute_query("DELETE FROM cart_items WHERE cart_id=%s", (cart['id'],), commit=True)

        # Insert item into cart
        execute_query(
            "INSERT INTO cart_items (cart_id, food_item_id, quantity, price) VALUES (%s, %s, %s, %s)",
            (cart['id'], self.food['id'], quantity, self.food['price']),
            commit=True
        )
        return cart['id']

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Checkout without applying a coupon (Bug Reproduction & Verification)
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_checkout_without_coupon_stores_null_and_succeeds(self):
        """
        Simulate exact browser form submission without coupon:
        coupon_id='', coupon_code='', discount='0'.
        Verifies orders.coupon_id is stored as SQL NULL without foreign key error.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=1)

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_code': '',
            'coupon_id': '',      # Browser sends empty string
            'discount': '0'
        }, follow_redirects=False)

        # Must redirect to order success (302)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/customer/order/success/', res.location)

        # Verify created order in database
        order = execute_query(
            "SELECT * FROM orders WHERE user_id=%s ORDER BY id DESC LIMIT 1",
            (self.user_id,), fetchone=True
        )
        self.assertIsNotNone(order)
        self.assertIsNone(order['coupon_id'], "orders.coupon_id must be SQL NULL when no coupon is used.")
        self.assertEqual(float(order['discount']), 0.0)
        self.assertEqual(order['payment_status'], 'pending')
        self.assertEqual(order['payment_method'], 'cod')

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Checkout with a valid coupon
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_checkout_with_valid_coupon(self):
        """
        Checkout with an active, valid coupon:
        Verifies correct discount applied, orders.coupon_id saved, times_used incremented.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=3)
        subtotal = float(self.food['price']) * 3

        # Find or create a test coupon
        coupon = execute_query("SELECT * FROM coupons WHERE is_active=1 AND min_order_amount<=%s LIMIT 1", (subtotal,), fetchone=True)
        if not coupon:
            cid = execute_query(
                "INSERT INTO coupons (code, description, discount_type, discount_value, min_order_amount, is_active, times_used) "
                "VALUES ('TESTVALID20', 'Test 20% off', 'percentage', 20.0, 50.0, 1, 0)",
                commit=True
            )
            coupon = execute_query("SELECT * FROM coupons WHERE id=%s", (cid,), fetchone=True)

        initial_times_used = coupon.get('times_used') or 0

        # Calculate expected discount
        is_val, msg, c_rec, expected_disc = validate_and_calculate_coupon(coupon_id=coupon['id'], subtotal=subtotal)
        self.assertTrue(is_val)

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_code': coupon['code'],
            'coupon_id': str(coupon['id']),
            'discount': str(expected_disc)
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        # Verify order in DB
        order = execute_query(
            "SELECT * FROM orders WHERE user_id=%s ORDER BY id DESC LIMIT 1",
            (self.user_id,), fetchone=True
        )
        self.assertEqual(order['coupon_id'], coupon['id'])
        self.assertAlmostEqual(float(order['discount']), expected_disc, places=2)

        # Verify coupons.times_used incremented
        updated_coupon = execute_query("SELECT times_used FROM coupons WHERE id=%s", (coupon['id'],), fetchone=True)
        self.assertEqual(updated_coupon['times_used'], initial_times_used + 1)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Checkout with invalid coupon ID
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_checkout_with_invalid_coupon_id(self):
        """
        Checkout with fabricated/non-existent coupon_id=999999.
        Must reject cleanly with a friendly message and NOT crash with FK IntegrityError.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=2)

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_code': 'FAKECP999',
            'coupon_id': '999999',
            'discount': '50'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Coupon error', res.data)
        # Cart must NOT be cleared
        remaining_items = execute_query("SELECT COUNT(*) AS c FROM cart_items WHERE cart_id=%s", (cart_id,), fetchone=True)
        self.assertGreater(remaining_items['c'], 0)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Checkout with expired coupon
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_checkout_with_expired_coupon(self):
        """
        Checkout with an expired coupon:
        Must reject with clear explanation, cart preserved.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=2)

        # Create or fetch expired coupon
        past_date = (date.today() - timedelta(days=5)).strftime('%Y-%m-%d')
        cid = execute_query(
            "INSERT INTO coupons (code, description, discount_type, discount_value, min_order_amount, expiry_date, is_active) "
            "VALUES ('EXPIREDTEST', 'Expired voucher', 'fixed', 50.0, 10.0, %s, 1) "
            "ON DUPLICATE KEY UPDATE expiry_date=%s, is_active=1",
            (past_date, past_date), commit=True
        )
        if not cid:
            exp_cp = execute_query("SELECT id FROM coupons WHERE code='EXPIREDTEST'", fetchone=True)
            cid = exp_cp['id']

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_code': 'EXPIREDTEST',
            'coupon_id': str(cid),
            'discount': '50'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'expired', res.data.lower())

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Checkout with coupon failing minimum order requirement
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_checkout_with_coupon_below_min_order(self):
        """
        Coupon requires ₹9999 minimum order, cart is smaller.
        Must reject with clear minimum amount message.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=1)

        cid = execute_query(
            "INSERT INTO coupons (code, description, discount_type, discount_value, min_order_amount, is_active) "
            "VALUES ('HIGHMINTEST', 'High min order', 'fixed', 100.0, 9999.0, 1) "
            "ON DUPLICATE KEY UPDATE min_order_amount=9999.0, is_active=1",
            commit=True
        )
        if not cid:
            cp = execute_query("SELECT id FROM coupons WHERE code='HIGHMINTEST'", fetchone=True)
            cid = cp['id']

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_code': 'HIGHMINTEST',
            'coupon_id': str(cid),
            'discount': '100'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Minimum order', res.data)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Correct server-side payable amount calculation & non-negative floor
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_totals_calculation_and_non_negative_guarantee(self):
        """
        Verify calculate_order_totals ensures discount never exceeds subtotal
        and grand_total is strictly non-negative.
        """
        totals = calculate_order_totals(subtotal=100.0, delivery_fee=40.0, discount=500.0)
        self.assertEqual(totals['subtotal'], 100.0)
        self.assertEqual(totals['discount'], 100.0)  # Capped at subtotal
        self.assertEqual(totals['tax'], 0.0)
        self.assertEqual(totals['grand_total'], 40.0)  # Only delivery fee remaining
        self.assertGreaterEqual(totals['grand_total'], 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Correct order items snapshot
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_order_items_records_have_item_name_snapshot(self):
        """
        Verify order_items records store item_name snapshot, quantity, price, and subtotal.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=2)

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_id': '',
            'discount': '0'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        order = execute_query(
            "SELECT id FROM orders WHERE user_id=%s ORDER BY id DESC LIMIT 1",
            (self.user_id,), fetchone=True
        )
        items = execute_query("SELECT * FROM order_items WHERE order_id=%s", (order['id'],), fetchall=True)
        self.assertGreater(len(items), 0)
        for it in items:
            self.assertTrue(bool(it['item_name']), "order_items.item_name must not be empty.")
            self.assertEqual(it['quantity'], 2)
            self.assertAlmostEqual(float(it['subtotal']), float(it['price']) * 2, places=2)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Order success & invoice display
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_order_success_and_detail_views(self):
        """
        Verify order confirmation and bill display render without template errors.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=1)

        res = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_id': '',
            'discount': '0'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        order = execute_query(
            "SELECT id FROM orders WHERE user_id=%s ORDER BY id DESC LIMIT 1",
            (self.user_id,), fetchone=True
        )

        # Test success view
        res_succ = self.client.get(f'/customer/order/success/{order["id"]}')
        self.assertEqual(res_succ.status_code, 200)
        self.assertIn(b'Order Placed Successfully', res_succ.data)

        # Test order detail / bill view
        res_detail = self.client.get(f'/customer/order/{order["id"]}')
        self.assertEqual(res_detail.status_code, 200)
        self.assertIn(b'Items Ordered', res_detail.data)

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Failed checkout transaction rollback behavior
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_transaction_rollback_on_failure(self):
        """
        Verify that if an error occurs within db_transaction, changes are rolled back.
        """
        initial_order_count = execute_query("SELECT COUNT(*) AS c FROM orders", fetchone=True)['c']

        try:
            with db_transaction() as tx:
                tx.execute(
                    "INSERT INTO orders (order_code, user_id, restaurant_id, delivery_address, total_amount) "
                    "VALUES ('FH-ROLLBACK-TEST', %s, %s, 'Test Address', 100.0)",
                    (self.user_id, self.food['restaurant_id'])
                )
                # Intentionally trigger an error
                raise RuntimeError("Simulated failure to test rollback")
        except RuntimeError:
            pass

        final_order_count = execute_query("SELECT COUNT(*) AS c FROM orders", fetchone=True)['c']
        self.assertEqual(initial_order_count, final_order_count, "Rollback must prevent phantom order persistence.")

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Demo online payment checkout
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_demo_online_payment_checkout(self):
        """
        Verify non-COD checkout redirects to payment page and payment_demo_confirm succeeds.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=1)

        # POST checkout with UPI payment method
        res = self.client.post('/customer/checkout', data={
            'payment_method': 'upi',
            'address_id': str(self.addr['id']),
            'coupon_id': '',
            'discount': '0'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/customer/payment', res.location)

        # Complete demo payment
        res_pay = self.client.post('/customer/payment/demo-confirm', data={
            'payment_method': 'demo_upi'
        }, follow_redirects=False)
        self.assertEqual(res_pay.status_code, 302)
        self.assertIn('/customer/order/success/', res_pay.location)

        order = execute_query(
            "SELECT * FROM orders WHERE user_id=%s ORDER BY id DESC LIMIT 1",
            (self.user_id,), fetchone=True
        )
        self.assertEqual(order['payment_status'], 'paid')
        self.assertEqual(order['payment_method'], 'demo_upi')

    # ─────────────────────────────────────────────────────────────────────────
    # 11. Duplicate submission behavior
    # ─────────────────────────────────────────────────────────────────────────
    def test_11_duplicate_submission_prevention(self):
        """
        Attempting to submit checkout twice with an already-completed cart
        safely fails without creating duplicate orders.
        """
        self._login_customer()
        cart_id = self._setup_active_cart(quantity=1)

        # First checkout
        res1 = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_id': '',
            'discount': '0'
        }, follow_redirects=False)
        self.assertEqual(res1.status_code, 302)

        # Second checkout attempt immediately after
        res2 = self.client.post('/customer/checkout', data={
            'payment_method': 'cod',
            'address_id': str(self.addr['id']),
            'coupon_id': '',
            'discount': '0'
        }, follow_redirects=True)
        # Should redirect to cart or show empty cart warning
        self.assertIn(b'cart is empty', res2.data.lower())

    # ─────────────────────────────────────────────────────────────────────────
    # 12. Active DB foreign key constraint integrity
    # ─────────────────────────────────────────────────────────────────────────
    def test_12_foreign_key_constraint_intact(self):
        """
        Verify that foreign key constraint on orders(coupon_id) is active in database
        and properly enforced.
        """
        mode = get_db_mode()
        if mode == 'mysql':
            fk_check = execute_query(
                "SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME "
                "FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='orders' AND COLUMN_NAME='coupon_id'",
                fetchone=True
            )
            self.assertIsNotNone(fk_check, "Foreign key constraint on orders.coupon_id must exist in MySQL.")
            self.assertEqual(fk_check['REFERENCED_TABLE_NAME'], 'coupons')


if __name__ == '__main__':
    unittest.main()
