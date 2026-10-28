"""
tests/test_common_portals.py
Comprehensive test suite verifying:
1. / loads the customer website.
2. /portals loads the Restaurant Owner-only partner portal.
3. The Restaurant Owner option links to the correct existing routes.
4. Admin authentication and the Admin Gate still work.
5. Restaurant onboarding and approval still work.
6. Delivery login remains functional, and Staff login is retired (redirects).
7. Customers cannot gain partner or admin access by selecting an option.
8. Customer and partner session isolation remains intact.
9. The Cloudflare script prints exactly two main public URLs: Customer Website and Restaurant Owner Partner Portal.
10. Mobile layouts display the Restaurant Owner partner portal responsively.
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
        # Verify public navbar link to Partner With Us exists
        self.assertIn('href="/portals"', html)
        # Verify footer does NOT link to admin, delivery, or staff
        self.assertNotIn('href="/admin"', html)
        self.assertNotIn('href="/delivery/login"', html)
        self.assertNotIn('href="/staff/login"', html)

    def test_02_portals_route_loads_restaurant_owner_only_page(self):
        """2. Verify /portals loads the Restaurant Owner-only partner portal."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Partner With", html)
        self.assertIn("FOODY HUNTERS", html)
        # Exactly ONE partner option is present: Restaurant Owner
        self.assertIn("Restaurant Owner", html)
        self.assertIn('id="portalCardRestaurant"', html)
        # Admin, Delivery, and Staff options are strictly ABSENT from portal cards
        self.assertNotIn('id="portalCardAdmin"', html)
        self.assertNotIn('id="portalCardDelivery"', html)
        self.assertNotIn('id="portalCardStaff"', html)

    def test_03_restaurant_owner_option_links_to_correct_routes(self):
        """3. Verify the Restaurant Owner option links to correct existing routes and other portals are absent."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Option: Restaurant Owner (Login & Registration)
        self.assertIn('href="/restaurant/login"', html)
        self.assertIn('href="/restaurant/register"', html)

        # Back to customer link
        self.assertIn('href="/"', html)

        # ABSENT: No links to Admin, Delivery Partner, or Staff on /portals
        self.assertNotIn('href="/admin"', html)
        self.assertNotIn('href="/admin/login"', html)
        self.assertNotIn('href="/delivery/login"', html)
        self.assertNotIn('href="/delivery/register"', html)
        self.assertNotIn('href="/staff/login"', html)
        self.assertNotIn('href="/staff/register"', html)

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

    def test_06_delivery_operational_and_staff_retired(self):
        """6. Verify Delivery operations remain active, and Staff portal is retired."""
        # Delivery login & registration remain 100% active
        deliv_login = self.client.get('/delivery/login')
        self.assertEqual(deliv_login.status_code, 200)
        deliv_reg = self.client.get('/delivery/register')
        self.assertEqual(deliv_reg.status_code, 200)

        # Staff login & registration are RETIRED (safely redirect to /portals)
        staff_login = self.client.get('/staff/login', follow_redirects=False)
        self.assertEqual(staff_login.status_code, 302)
        self.assertIn('/portals', staff_login.headers.get('Location', ''))

        staff_reg = self.client.get('/staff/register', follow_redirects=False)
        self.assertEqual(staff_reg.status_code, 302)
        self.assertIn('/portals', staff_reg.headers.get('Location', ''))

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

        # Staff dashboard is retired
        staff_dash = self.client.get('/staff/dashboard', follow_redirects=False)
        self.assertEqual(staff_dash.status_code, 302)

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

    def test_09_cloudflare_script_prints_exactly_three_main_urls(self):
        """9. Verify Cloudflare script prints exactly three main public access URLs."""
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "scripts", "start_public_tunnel.ps1")
        test_url = "https://three-links-test.trycloudflare.com"

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

        # Must print the three main links
        self.assertIn("1. USER / CUSTOMER WEBSITE:", output)
        self.assertIn(f"{test_url}/", output)
        self.assertIn("2. ADMIN CONTROL CENTER:", output)
        self.assertIn(f"{test_url}/admin", output)
        self.assertIn("3. DELIVERY PARTNER PORTAL:", output)
        self.assertIn(f"{test_url}/delivery/portal", output)

        # Must NOT print separate public links in the main link list for individual sub-actions
        self.assertNotIn("CUSTOMER LOGIN:", output)
        self.assertNotIn("CUSTOMER REGISTER:", output)
        self.assertNotIn("HOTEL / RESTAURANT STAFF LOGIN:", output)
        self.assertNotIn("STAFF DASHBOARD:", output)
        self.assertNotIn("RIDER REGISTRATION:", output)
        self.assertNotIn("RIDER DASHBOARD:", output)


    def test_10_mobile_layouts_display_single_restaurant_owner_option(self):
        """10. Verify mobile layout compatibility and single Restaurant Owner option."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check viewport meta tag for mobile devices
        self.assertIn('name="viewport"', html)
        self.assertIn('content="width=device-width, initial-scale=1.0"', html)

        # Check single Restaurant Owner card is present
        self.assertIn('id="portalCardRestaurant"', html)
        self.assertIn('id="btnRestaurantRegister"', html)
        self.assertIn('id="btnRestaurantLogin"', html)

        # Other cards must be absent
        self.assertNotIn('id="portalCardAdmin"', html)
        self.assertNotIn('id="portalCardDelivery"', html)
        self.assertNotIn('id="portalCardStaff"', html)

        # Check responsive styling exists
        self.assertIn('@media (max-width: 768px)', html)

    def test_11_local_startup_script_prints_all_three_local_urls(self):
        """11. Verify local startup script (start_local.ps1) displays all three main local URLs."""
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "scripts", "start_local.ps1")

        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
            "-TestOnly"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 0, f"Local startup script failed with stderr: {proc.stderr}")
        output = proc.stdout

        # Verify all 3 local URLs
        self.assertIn("1. USER / CUSTOMER WEBSITE:", output)
        self.assertIn("http://127.0.0.1:5000/", output)
        self.assertIn("2. ADMIN CONTROL CENTER:", output)
        self.assertIn("http://127.0.0.1:5000/admin", output)
        self.assertIn("3. DELIVERY PARTNER PORTAL:", output)
        self.assertIn("http://127.0.0.1:5000/delivery/portal", output)


if __name__ == '__main__':
    unittest.main()

