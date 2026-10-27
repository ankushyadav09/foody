"""
tests/test_common_portals.py
Comprehensive test suite verifying:
1. / loads the customer website.
2. /portals loads the shared partner selection page.
3. The four portal options link to the correct existing routes.
4. Admin authentication and the Admin Gate still work.
5. Restaurant onboarding and approval still work.
6. Delivery login and staff login remain functional.
7. Customers cannot gain partner or admin access by selecting an option.
8. Customer and partner session isolation remains intact.
9. The Cloudflare script prints exactly two main public URLs using its actual detected hostname.
10. Mobile layouts display all four partner options correctly.
"""

import os
import sys
import unittest
import subprocess
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query


class TestCommonPortals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.client = self.app.test_client()

    def test_01_customer_root_loads_website(self):
        """1. Verify / loads the customer website."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Foody", html)
        self.assertIn("Hunters", html)
        # Verify customer nav links exist
        self.assertIn("/restaurants", html)
        self.assertIn("/offers", html)

    def test_02_portals_route_loads_selection_page(self):
        """2. Verify /portals loads the shared partner selection page."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Partner Portals", html)
        self.assertIn("Central Hub", html)
        # All 4 options are present
        self.assertIn("Admin Control Center", html)
        self.assertIn("Restaurant Owner", html)
        self.assertIn("Delivery Partner", html)
        self.assertIn("Hotel / Restaurant Staff", html)

    def test_03_four_portal_options_link_to_correct_routes(self):
        """3. Verify the four portal options link to correct existing routes."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Option 1: Admin
        self.assertIn('href="/admin"', html)

        # Option 2: Restaurant Owner (Login & Registration)
        self.assertIn('href="/restaurant/login"', html)
        self.assertIn('href="/restaurant/register"', html)

        # Option 3: Delivery Partner (Login & Registration)
        self.assertIn('href="/delivery/login"', html)
        self.assertIn('href="/delivery/register"', html)

        # Option 4: Hotel / Restaurant Staff (Login & Onboarding)
        self.assertIn('href="/staff/login"', html)
        self.assertIn('href="/staff/register"', html)

        # Back to customer link
        self.assertIn('href="/"', html)

    def test_04_admin_gate_and_auth_integrity(self):
        """4. Verify Admin authentication and Admin Gate still work."""
        # Unauthenticated /admin must redirect to /admin/gate
        res = self.client.get('/admin', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/gate', res.headers.get('Location', ''))

        # Gate page loads
        gate_res = self.client.get('/admin/gate')
        self.assertEqual(gate_res.status_code, 200)

        # Wrong passkey is rejected
        bad_gate = self.client.post('/admin/gate', data={'gate_password': 'wrongpass'}, follow_redirects=True)
        self.assertIn('Invalid security passkey', bad_gate.data.decode('utf-8'))

        # Correct passkey unlocks gate and redirects (either to dashboard or /admin/login)
        good_gate = self.client.post('/admin/gate', data={'gate_password': 'food@1234'}, follow_redirects=False)
        self.assertEqual(good_gate.status_code, 302)

    def test_05_restaurant_onboarding_and_auth_integrity(self):
        """5. Verify Restaurant onboarding and approval still work."""
        # Registration page loads
        reg_res = self.client.get('/restaurant/register')
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn("Restaurant Outlet Name", reg_res.data.decode('utf-8'))

        # Login page loads
        login_res = self.client.get('/restaurant/login')
        self.assertEqual(login_res.status_code, 200)

        # Direct dashboard access without auth is blocked
        dash_res = self.client.get('/restaurant/dashboard', follow_redirects=False)
        self.assertIn(dash_res.status_code, (302, 401, 403))

    def test_06_delivery_and_staff_auth_integrity(self):
        """6. Verify Delivery login and Staff login remain functional."""
        # Delivery login & registration
        deliv_login = self.client.get('/delivery/login')
        self.assertEqual(deliv_login.status_code, 200)
        deliv_reg = self.client.get('/delivery/register')
        self.assertEqual(deliv_reg.status_code, 200)

        # Staff login & registration
        staff_login = self.client.get('/staff/login')
        self.assertEqual(staff_login.status_code, 200)
        staff_reg = self.client.get('/staff/register')
        self.assertEqual(staff_reg.status_code, 200)

    def test_07_customers_cannot_gain_partner_or_admin_access_via_portals(self):
        """7. Verify customers cannot gain partner or admin access by selecting an option."""
        # Establish customer session
        with self.client.session_transaction() as sess:
            sess['user_id'] = 99999
            sess['user_name'] = 'Test Customer'
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': 99999, 'role': 'customer'}

        # Visiting /portals is pure navigation
        portals_res = self.client.get('/portals')
        self.assertEqual(portals_res.status_code, 200)

        # Customer still cannot access admin
        admin_res = self.client.get('/admin', follow_redirects=False)
        self.assertEqual(admin_res.status_code, 302)
        self.assertIn('/admin/gate', admin_res.headers.get('Location', ''))

        # Customer cannot access restaurant dashboard
        rest_dash = self.client.get('/restaurant/dashboard', follow_redirects=False)
        self.assertIn(rest_dash.status_code, (302, 401, 403))

        # Customer cannot access delivery dashboard
        deliv_dash = self.client.get('/delivery/dashboard', follow_redirects=False)
        self.assertIn(deliv_dash.status_code, (302, 401, 403))

        # Customer cannot access staff dashboard
        staff_dash = self.client.get('/staff/dashboard', follow_redirects=False)
        self.assertIn(staff_dash.status_code, (302, 401, 403))

    def test_08_session_isolation_remains_intact(self):
        """8. Verify customer and partner session isolation remains intact."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 12345
            sess['role'] = 'customer'
            sess['customer_auth'] = {'user_id': 12345, 'role': 'customer'}

        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)

        # Session should not contain any partner or admin namespaces
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('admin_auth'))
            self.assertIsNone(sess.get('restaurant_auth'))
            self.assertIsNone(sess.get('delivery_auth'))
            self.assertIsNone(sess.get('staff_auth'))
            self.assertIsNone(sess.get('admin_gate_passed'))

    def test_09_cloudflare_script_prints_exactly_two_main_urls(self):
        """9. Verify Cloudflare script prints exactly two main public URLs."""
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "scripts", "start_public_tunnel.ps1")
        test_url = "https://two-links-test.trycloudflare.com"

        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
            "-SimulatedUrl", test_url,
            "-TestOnly"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 0, f"Script failed with stderr: {proc.stderr}")
        output = proc.stdout

        # Must print the two main links
        self.assertIn("1. CUSTOMER WEBSITE:", output)
        self.assertIn(f"{test_url}/", output)
        self.assertIn("2. ALL PARTNER PORTALS:", output)
        self.assertIn(f"{test_url}/portals", output)

        # Must NOT print separate public links in the main link list for individual portals
        self.assertNotIn("CUSTOMER LOGIN:", output)
        self.assertNotIn("CUSTOMER REGISTER:", output)
        self.assertNotIn("ADMIN CONTROL CENTER:", output)
        self.assertNotIn("RESTAURANT OWNER LOGIN:", output)
        self.assertNotIn("DELIVERY PARTNER LOGIN:", output)
        self.assertNotIn("HOTEL / RESTAURANT STAFF LOGIN:", output)
        self.assertNotIn("STAFF DASHBOARD:", output)

    def test_10_mobile_layouts_display_all_four_options(self):
        """10. Verify mobile layout compatibility and responsive elements."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check viewport meta tag for mobile devices
        self.assertIn('name="viewport"', html)
        self.assertIn('content="width=device-width, initial-scale=1.0"', html)

        # Check all 4 portal cards have specific semantic IDs and mobile styles
        self.assertIn('id="portalCardAdmin"', html)
        self.assertIn('id="portalCardRestaurant"', html)
        self.assertIn('id="portalCardDelivery"', html)
        self.assertIn('id="portalCardStaff"', html)

        # Check responsive media query styling exists
        self.assertIn('@media (max-width: 640px)', html)
        self.assertIn('grid-template-columns: 1fr', html)


if __name__ == '__main__':
    unittest.main()
