"""
tests/test_staff_portal_and_governance.py
Comprehensive test suite for Portal 5 (Restaurant Staff Portal) and Central Governance:
1. Staff authentication & onboarding isolation
2. Role enforcement and access restrictions
3. Restaurant data boundary enforcement (orders and dishes)
4. Kitchen order state transitions (placed -> preparing -> ready_for_pickup)
5. Stock/Availability management (86-list)
6. Restaurant owner staff roster and approval workflow
7. Administrator central staff governance and reassignment
8. Cross-role boundary security checks
"""

import os
import random
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from werkzeug.security import generate_password_hash


class TestStaffPortalAndGovernance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def test_01_staff_login_and_registration_pages(self):
        """Verify dedicated /staff/login and /staff/register interfaces."""
        res = self.client.get('/staff/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Kitchen Operations Desk', html)
        self.assertIn('action="/staff/login"', html)
        self.assertIn('name="viewport"', html)

        res_reg = self.client.get('/staff/register')
        self.assertEqual(res_reg.status_code, 200)
        html_reg = res_reg.data.decode('utf-8')
        self.assertIn('Staff Onboarding Application', html_reg)
        self.assertIn('name="restaurant_id"', html_reg)
        self.assertIn('name="staff_role"', html_reg)
        self.assertIn('kitchen_staff', html_reg)
        self.assertIn('restaurant_manager', html_reg)

    def test_02_staff_registration_creates_pending_record(self):
        """Staff self-registration creates pending record strictly linked to selected restaurant."""
        uid = uuid.uuid4().hex[:6]
        email = f"chef_{uid}@testkitchen.com"
        phone = f"98{random.randint(10000000, 99999999)}"

        # Pick a valid restaurant
        rest = execute_query("SELECT id FROM restaurants WHERE verification_status='approved' LIMIT 1", fetchone=True)
        self.assertIsNotNone(rest)
        rest_id = rest['id']

        res = self.client.post('/staff/register', data={
            'name': f'Chef Test {uid}',
            'email': email,
            'phone': phone,
            'restaurant_id': str(rest_id),
            'staff_role': 'kitchen_staff',
            'shift': 'Morning Shift (7 AM - 3 PM)',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'staff')

        staff_rec = execute_query("SELECT * FROM restaurant_staff WHERE user_id=%s", (user['id'],), fetchone=True)
        self.assertIsNotNone(staff_rec)
        self.assertEqual(staff_rec['status'], 'pending')
        self.assertEqual(staff_rec['restaurant_id'], rest_id)
        self.assertEqual(staff_rec['staff_role'], 'kitchen_staff')

        # Attempt to login while pending -> must be blocked
        res_login = self.client.post('/staff/login', data={
            'email': email,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'pending approval', res_login.data)

    def test_03_demo_staff_login_and_dashboard_telemetry(self):
        """Login with demo kitchen staff account and view kitchen workspace."""
        res = self.client.post('/staff/login', data={
            'email': 'staff@foodyhunters.com',
            'password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Kitchen Operations', html)
        self.assertIn('Active Kitchen Preparation Queue', html)

        # Profile route
        res_prof = self.client.get('/staff/profile')
        self.assertEqual(res_prof.status_code, 200)
        self.assertIn(b'Staff Credentials', res_prof.data)

    def test_04_kitchen_order_transition_and_data_isolation(self):
        """Staff advances order status with strict restaurant-level data isolation."""
        # Find approved demo staff user
        demo_staff = execute_query(
            """SELECT u.id, u.name, u.email, s.restaurant_id, s.staff_role 
               FROM users u 
               JOIN restaurant_staff s ON u.id=s.user_id 
               WHERE u.role='staff' AND s.status='approved' LIMIT 1""",
            fetchone=True
        )
        self.assertIsNotNone(demo_staff)

        with self.client.session_transaction() as sess:
            sess['user_id'] = demo_staff['id']
            sess['user_name'] = demo_staff['name']
            sess['user_email'] = demo_staff['email']
            sess['role'] = 'staff'
            sess['restaurant_id'] = demo_staff['restaurant_id']
            sess['staff_role'] = demo_staff['staff_role']

        rest_id = demo_staff['restaurant_id']

        # Find or create a test order for this restaurant
        test_order = execute_query(
            "SELECT id, order_code, order_status FROM orders WHERE restaurant_id=%s LIMIT 1",
            (rest_id,), fetchone=True
        )
        if not test_order:
            order_id = execute_query(
                """INSERT INTO orders (user_id, restaurant_id, order_code, total_amount, payment_method, payment_status, order_status)
                   VALUES (1, %s, 'TEST-STF-01', 350.00, 'cod', 'pending', 'placed')""",
                (rest_id,), commit=True
            )
        else:
            order_id = test_order['id']
            execute_query("UPDATE orders SET order_status='placed' WHERE id=%s", (order_id,), commit=True)

        # Transition placed -> preparing
        res = self.client.post('/staff/order/update-status', data={
            'order_id': str(order_id),
            'status': 'preparing'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        updated_order = execute_query("SELECT order_status FROM orders WHERE id=%s", (order_id,), fetchone=True)
        self.assertEqual(updated_order['order_status'], 'preparing')

        # Transition preparing -> ready_for_pickup
        res2 = self.client.post('/staff/order/update-status', data={
            'order_id': str(order_id),
            'status': 'ready_for_pickup'
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        updated_order2 = execute_query("SELECT order_status FROM orders WHERE id=%s", (order_id,), fetchone=True)
        self.assertEqual(updated_order2['order_status'], 'ready_for_pickup')

        # DATA ISOLATION TEST: Attempt to mutate an order belonging to another restaurant
        other_order = execute_query("SELECT id FROM orders WHERE restaurant_id != %s LIMIT 1", (rest_id,), fetchone=True)
        if other_order:
            res_cross = self.client.post('/staff/order/update-status', data={
                'order_id': str(other_order['id']),
                'status': 'preparing'
            }, follow_redirects=True)
            self.assertIn(b'permission denied', res_cross.data.lower())

    def test_05_staff_menu_dish_availability_toggle(self):
        """Staff toggles dish availability (86-list) with restaurant boundary enforcement."""
        demo_staff = execute_query(
            """SELECT u.id, u.name, u.email, s.restaurant_id, s.staff_role 
               FROM users u 
               JOIN restaurant_staff s ON u.id=s.user_id 
               WHERE u.role='staff' AND s.status='approved' LIMIT 1""",
            fetchone=True
        )
        self.assertIsNotNone(demo_staff)
        rest_id = demo_staff['restaurant_id']

        with self.client.session_transaction() as sess:
            sess['user_id'] = demo_staff['id']
            sess['role'] = 'staff'
            sess['restaurant_id'] = rest_id
            sess['staff_role'] = demo_staff['staff_role']

        dish = execute_query("SELECT id, availability FROM food_items WHERE restaurant_id=%s LIMIT 1", (rest_id,), fetchone=True)
        self.assertIsNotNone(dish)
        orig_avail = dish['availability']

        # Toggle availability
        res = self.client.post('/staff/menu/toggle-availability', data={
            'food_item_id': str(dish['id'])
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        dish_after = execute_query("SELECT availability FROM food_items WHERE id=%s", (dish['id'],), fetchone=True)
        self.assertNotEqual(dish_after['availability'], orig_avail)

        # Restore original availability
        self.client.post('/staff/menu/toggle-availability', data={'food_item_id': str(dish['id'])}, follow_redirects=True)

        # DATA ISOLATION: Attempt to toggle dish belonging to another restaurant
        other_dish = execute_query("SELECT id FROM food_items WHERE restaurant_id != %s LIMIT 1", (rest_id,), fetchone=True)
        if other_dish:
            res_cross = self.client.post('/staff/menu/toggle-availability', data={
                'food_item_id': str(other_dish['id'])
            }, follow_redirects=True)
            self.assertIn(b'permission denied', res_cross.data.lower())

    def test_06_restaurant_owner_staff_roster_and_actions(self):
        """Restaurant owner onboards staff, approves applicants, and manages roster."""
        rest = execute_query("SELECT r.id, r.owner_id, u.email FROM restaurants r JOIN users u ON r.owner_id=u.id LIMIT 1", fetchone=True)
        self.assertIsNotNone(rest)

        with self.client.session_transaction() as sess:
            sess['user_id'] = rest['owner_id']
            sess['role'] = 'restaurant'
            sess['user_email'] = rest['email']
            sess['restaurant_id'] = rest['id']

        # View staff roster
        res = self.client.get('/restaurant/staff')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Staff Roster', res.data)

        # Onboard new staff directly
        uid = uuid.uuid4().hex[:6]
        phone = f"98{random.randint(10000000, 99999999)}"
        res_add = self.client.post('/restaurant/staff/add', data={
            'name': f'Direct Staff {uid}',
            'email': f'direct_{uid}@kitchen.com',
            'phone': phone,
            'staff_role': 'kitchen_staff',
            'shift': 'Full Time',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)

        new_user = execute_query("SELECT * FROM users WHERE email=%s", (f'direct_{uid}@kitchen.com',), fetchone=True)
        self.assertIsNotNone(new_user)
        staff_rec = execute_query("SELECT * FROM restaurant_staff WHERE user_id=%s", (new_user['id'],), fetchone=True)
        self.assertIsNotNone(staff_rec)
        self.assertEqual(staff_rec['status'], 'approved')
        self.assertEqual(staff_rec['restaurant_id'], rest['id'])

        # Toggle staff account status
        self.client.post(f'/restaurant/staff/toggle/{staff_rec["id"]}', follow_redirects=True)
        toggled = execute_query("SELECT status FROM restaurant_staff WHERE id=%s", (staff_rec['id'],), fetchone=True)
        self.assertEqual(toggled['status'], 'suspended')

        # Clean up
        self.client.post(f'/restaurant/staff/delete/{staff_rec["id"]}', follow_redirects=True)

    def test_07_admin_central_staff_governance(self):
        """Admin views staff across all restaurants, approves, reassigns, and toggles."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'
            sess['user_email'] = 'admin@foodiehunter.com'
            sess['admin_gate_passed'] = True

        # View admin staff directory
        res = self.client.get('/admin/staff')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Kitchen Staff Governance', res.data)

        # Create a pending staff member for verification testing
        uid = uuid.uuid4().hex[:6]
        phone = f"98{random.randint(10000000, 99999999)}"
        pw_hash = generate_password_hash('password123')
        test_user_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, %s, 'staff', 'active')",
            (f'Pending Staff {uid}', f'pending_{uid}@gov.com', phone, pw_hash),
            commit=True
        )
        staff_id = execute_query(
            "INSERT INTO restaurant_staff (user_id, restaurant_id, staff_role, status) VALUES (%s, 1, 'kitchen_staff', 'pending')",
            (test_user_id,), commit=True
        )

        # Admin approves staff
        res_appr = self.client.post(f'/admin/staff/verify/{staff_id}/approved', follow_redirects=True)
        self.assertEqual(res_appr.status_code, 200)
        staff_rec = execute_query("SELECT status, restaurant_id FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
        self.assertEqual(staff_rec['status'], 'approved')

        # Admin reassigns staff to another restaurant if available
        other_rest = execute_query("SELECT id FROM restaurants WHERE id != 1 LIMIT 1", fetchone=True)
        if other_rest:
            res_reassign = self.client.post(f'/admin/staff/reassign/{staff_id}', data={
                'restaurant_id': str(other_rest['id'])
            }, follow_redirects=True)
            self.assertEqual(res_reassign.status_code, 200)
            reassigned = execute_query("SELECT restaurant_id FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
            self.assertEqual(reassigned['restaurant_id'], other_rest['id'])

        # Admin deletes staff
        res_del = self.client.post(f'/admin/staff/delete/{staff_id}', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        deleted = execute_query("SELECT * FROM restaurant_staff WHERE id=%s", (staff_id,), fetchone=True)
        self.assertIsNone(deleted)

    def test_08_cross_role_access_boundary_security(self):
        """Strict server-side validation that roles cannot cross portal boundaries."""
        # Staff user cannot access admin or restaurant owner portals
        demo_staff = execute_query(
            """SELECT u.id, s.restaurant_id FROM users u 
               JOIN restaurant_staff s ON u.id=s.user_id 
               WHERE u.role='staff' AND s.status='approved' LIMIT 1""",
            fetchone=True
        )
        self.assertIsNotNone(demo_staff)

        with self.client.session_transaction() as sess:
            sess['user_id'] = demo_staff['id']
            sess['role'] = 'staff'
            sess['restaurant_id'] = demo_staff['restaurant_id']

        res_adm = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertIn(res_adm.status_code, [302, 403])

        res_rest = self.client.get('/restaurant/dashboard', follow_redirects=False)
        self.assertIn(res_rest.status_code, [302, 403])

        res_deliv = self.client.get('/delivery/dashboard', follow_redirects=False)
        self.assertIn(res_deliv.status_code, [302, 403])

        # Customer user cannot access staff portal
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1001
            sess['role'] = 'customer'

        res_stf = self.client.get('/staff/dashboard', follow_redirects=False)
        self.assertIn(res_stf.status_code, [302, 403])


if __name__ == '__main__':
    unittest.main()
