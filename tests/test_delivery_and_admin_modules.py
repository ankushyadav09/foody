"""
tests/test_delivery_and_admin_modules.py – Automated tests for Phase 5 (Delivery) and Phase 6 (Admin)
"""

import unittest
from app import create_app
from database import execute_query

class TestDeliveryAndAdminModules(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_delivery_partner_login_and_profile_persistence(self):
        # 1. Login as delivery partner
        res = self.client.post('/auth/login', data={
            'email': 'delivery@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 2. View profile
        res = self.client.get('/delivery/profile')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Delivery Partner Profile Details', res.data)

        # 3. Update profile
        new_name = "Vikram S. Parmar"
        new_phone = "9825099999"
        new_vehicle_no = "GJ-02-ZZ-9999"
        res = self.client.post('/delivery/profile/update', data={
            'name': new_name,
            'phone': new_phone,
            'gender': 'male',
            'dob': '1996-08-15',
            'address': 'Near Modhera Circle, Mehsana',
            'city': 'Mehsana',
            'state': 'Gujarat',
            'pincode': '384002',
            'vehicle_type': 'Motorcycle',
            'vehicle_number': new_vehicle_no,
            'license_number': 'DL-GJ02-2022-99999'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Delivery partner profile updated successfully!', res.data)

        # 4. Verify in MySQL
        user = execute_query("SELECT * FROM users WHERE email='delivery@foodiehunter.com'", fetchone=True)
        self.assertEqual(user['name'], new_name)
        self.assertEqual(user['phone'], new_phone)
        partner = execute_query("SELECT * FROM delivery_partners WHERE user_id=%s", (user['id'],), fetchone=True)
        self.assertEqual(partner['vehicle_number'], new_vehicle_no)

        # 5. Refresh profile page to confirm persistence in HTML
        res_refresh = self.client.get('/delivery/profile')
        self.assertEqual(res_refresh.status_code, 200)
        self.assertIn(new_name.encode('utf-8'), res_refresh.data)
        self.assertIn(new_vehicle_no.encode('utf-8'), res_refresh.data)

    def test_02_delivery_toggle_online(self):
        self.client.post('/auth/login', data={
            'email': 'delivery@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        user = execute_query("SELECT id FROM users WHERE email='delivery@foodiehunter.com'", fetchone=True)
        orig = execute_query("SELECT is_online FROM delivery_partners WHERE user_id=%s", (user['id'],), fetchone=True)
        orig_val = orig['is_online'] if orig else 1

        # Toggle online
        res = self.client.post('/delivery/toggle-online', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        new_row = execute_query("SELECT is_online FROM delivery_partners WHERE user_id=%s", (user['id'],), fetchone=True)
        self.assertNotEqual(new_row['is_online'], orig_val)

        # Toggle back
        self.client.post('/delivery/toggle-online', follow_redirects=True)
        final_row = execute_query("SELECT is_online FROM delivery_partners WHERE user_id=%s", (user['id'],), fetchone=True)
        self.assertEqual(final_row['is_online'], orig_val)

    def test_03_admin_login_and_profile_persistence(self):
        # 1. Clear gate and login as admin via dedicated admin desk
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        res = self.client.post('/admin/login', data={
            'email': 'admin@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 2. View profile
        res = self.client.get('/admin/profile')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Administrator Profile', res.data)

        # 3. Update admin profile
        new_admin_name = "Super Admin Mehsana"
        new_admin_phone = "9825000001"
        res = self.client.post('/admin/profile/update', data={
            'name': new_admin_name,
            'phone': new_admin_phone,
            'gender': 'other',
            'dob': '1990-01-01',
            'address': 'HQ Central Hub, Highway Road',
            'city': 'Mehsana',
            'state': 'Gujarat',
            'pincode': '384002'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Administrator profile updated successfully!', res.data)

        # 4. Verify in MySQL
        admin_user = execute_query("SELECT * FROM users WHERE email='admin@foodiehunter.com'", fetchone=True)
        self.assertEqual(admin_user['name'], new_admin_name)
        self.assertEqual(admin_user['phone'], new_admin_phone)

        # 5. Refresh profile page to confirm persistence in HTML
        res_refresh = self.client.get('/admin/profile')
        self.assertEqual(res_refresh.status_code, 200)
        self.assertIn(new_admin_name.encode('utf-8'), res_refresh.data)

    def test_04_admin_management_features(self):
        self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=True)
        self.client.post('/admin/login', data={
            'email': 'admin@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Admin dashboard
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)

        # Admin restaurants list
        res = self.client.get('/admin/restaurants')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'restaurants', res.data.lower())

        # Admin coupons list
        res = self.client.get('/admin/coupons')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'WELCOME50', res.data)

if __name__ == '__main__':
    unittest.main()
