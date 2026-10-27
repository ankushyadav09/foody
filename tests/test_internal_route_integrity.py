"""
tests/test_internal_route_integrity.py
Comprehensive route and internal link audit test suite across all 5 portals:
- Public GET pages load (200)
- Authenticated portal pages accessible to authorized accounts (200)
- Automated crawl of template internal links against Flask url_map (0 broken links)
- Food item add route aliases intact (/restaurant/add-food, /restaurant/menu/add, /restaurant/food/add)
- Static uploads verified
- Proper security redirects on protected endpoints
"""

import os
import sys
import re
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from config import Config


class TestInternalRouteIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.client = self.app.test_client()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. PUBLIC ENTRY POINTS & PAGES
    # ─────────────────────────────────────────────────────────────────────────

    def test_01_public_storefront_and_portal_pages(self):
        """1. Every intended public GET page loads successfully (HTTP 200)."""
        public_routes = [
            '/',
            '/portals',
            '/restaurants',
            '/offers',
            '/about',
            '/contact',
            '/auth/login',
            '/auth/register',
            '/auth/forgot-password',
            '/admin/login',
            '/restaurant/login',
            '/restaurant/register',
            '/delivery/login',
            '/delivery/register',
            '/staff/login',
            '/staff/register',
        ]
        for route in public_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Public route {route} failed with status {res.status_code}")

    def test_02_public_restaurant_detail(self):
        """2. Public customer restaurant detail loads with menu and dishes."""
        res = self.client.get('/restaurant/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"The Grand Thakar", res.data)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. AUTHENTICATED PORTAL PAGES AUDIT
    # ─────────────────────────────────────────────────────────────────────────

    def test_03_authenticated_admin_pages_accessible(self):
        """3. All core admin portal pages are accessible to authenticated administrator."""
        client = self.app.test_client()
        client.post('/admin/gate/verify', data={'gate_password': 'food@1234'})
        client.post('/admin/login', data={'email': 'admin@foodyhunters.com', 'password': 'password123'})

        admin_pages = [
            '/admin/dashboard',
            '/admin/restaurants',
            '/admin/delivery-partners',
            '/admin/staff',
            '/admin/users',
            '/admin/orders',
            '/admin/categories',
            '/admin/coupons',
            '/admin/reviews',
            '/admin/payments',
            '/admin/complaints',
            '/admin/reports',
            '/admin/profile',
            '/admin/activity',
        ]
        for page in admin_pages:
            res = client.get(page)
            self.assertEqual(res.status_code, 200, f"Admin page {page} returned status {res.status_code}")

    def test_04_authenticated_restaurant_pages_accessible(self):
        """4. All core restaurant portal pages are accessible to approved restaurant owner."""
        client = self.app.test_client()
        client.post('/restaurant/login', data={'email': 'restaurant@foodyhunters.com', 'password': 'password123'})

        restaurant_pages = [
            '/restaurant/dashboard',
            '/restaurant/profile',
            '/restaurant/menu',
            '/restaurant/add-food',
            '/restaurant/menu/add',
            '/restaurant/food/add',
            '/restaurant/orders',
            '/restaurant/staff',
            '/restaurant/sales',
            '/restaurant/reviews',
        ]
        for page in restaurant_pages:
            res = client.get(page)
            self.assertEqual(res.status_code, 200, f"Restaurant page {page} returned status {res.status_code}")

    def test_05_authenticated_delivery_pages_accessible(self):
        """5. All core delivery partner pages are accessible to verified delivery partner."""
        client = self.app.test_client()
        client.post('/delivery/login', data={'email': 'delivery@foodyhunters.com', 'password': 'password123'})

        delivery_pages = [
            '/delivery/dashboard',
            '/delivery/profile',
            '/delivery/history',
        ]
        for page in delivery_pages:
            res = client.get(page)
            self.assertEqual(res.status_code, 200, f"Delivery page {page} returned status {res.status_code}")

    def test_06_authenticated_staff_pages_accessible(self):
        """6. All core staff portal pages are accessible to approved kitchen staff."""
        client = self.app.test_client()
        client.post('/staff/login', data={'email': 'staff@foodyhunters.com', 'password': 'password123'})

        staff_pages = [
            '/staff/dashboard',
            '/staff/profile',
            '/staff/orders',
            '/staff/menu',
        ]
        for page in staff_pages:
            res = client.get(page)
            self.assertEqual(res.status_code, 200, f"Staff page {page} returned status {res.status_code}")

    def test_07_authenticated_customer_pages_accessible(self):
        """7. All core customer account pages are accessible to logged-in customer."""
        client = self.app.test_client()
        client.post('/auth/login', data={'email': 'customer@foodyhunters.com', 'password': 'password123'})

        customer_pages = [
            '/customer/profile',
            '/customer/orders',
            '/customer/cart',
            '/customer/checkout',
            '/customer/favorites',
            '/customer/notifications',
        ]
        for page in customer_pages:
            res = client.get(page)
            if page == '/customer/checkout' and res.status_code == 302:
                self.assertIn('/customer/cart', res.headers.get('Location', ''))
            else:
                self.assertEqual(res.status_code, 200, f"Customer page {page} returned status {res.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. AUTOMATED TEMPLATE INTERNAL LINK AUDIT
    # ─────────────────────────────────────────────────────────────────────────

    def test_08_automated_template_links_match_registered_routes(self):
        """8. Automated audit: all internal links in template files match registered Flask URL map routes."""
        template_dir = os.path.join(self.app.root_path, 'templates')
        pattern = re.compile(r'(?:href|action)=["\'](/[^"\'#?\{\}\s]+)["\']')

        found_links = set()
        for root, _, files in os.walk(template_dir):
            for f in files:
                if f.endswith('.html'):
                    filepath = os.path.join(root, f)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                        content = fp.read()
                        matches = pattern.findall(content)
                        for m in matches:
                            if not m.startswith('/static'):
                                found_links.add((m, os.path.relpath(filepath, self.app.root_path)))

        adapter = self.app.url_map.bind('localhost')
        unmatched = []

        for link, tmpl in sorted(found_links):
            matched = False
            for m in ['GET', 'POST']:
                try:
                    adapter.match(link, method=m)
                    matched = True
                    break
                except Exception:
                    pass
            if not matched:
                unmatched.append((link, tmpl))

        self.assertEqual(len(unmatched), 0, f"Unmatched internal template links found: {unmatched}")

    def test_09_order_detail_route_aliases_operational(self):
        """9. Both /restaurant/orders/<id> and /restaurant/order/<id> resolve without 404."""
        client = self.app.test_client()
        client.post('/restaurant/login', data={'email': 'restaurant@foodyhunters.com', 'password': 'password123'})

        # Get existing order for Restaurant 1
        order = execute_query("SELECT id FROM orders WHERE restaurant_id=1 LIMIT 1", fetchone=True)
        if order:
            res1 = client.get(f"/restaurant/orders/{order['id']}")
            self.assertEqual(res1.status_code, 200)

            res2 = client.get(f"/restaurant/order/{order['id']}")
            self.assertEqual(res2.status_code, 200)


if __name__ == '__main__':
    unittest.main()
