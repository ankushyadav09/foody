"""
tests/test_global_layout_and_clipping.py – Comprehensive Layout Offset, Navbar Clearance, and Clipping Verification
Tests across all five portals, customer pages, restaurant detail hero banner, and sticky navigation anchors.
"""

import os
import re
import unittest
from app import create_app
from database import execute_query

class TestGlobalLayoutAndClipping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.css_path = os.path.join(cls.app.root_path, 'static', 'css', 'style.css')
        with open(cls.css_path, 'r', encoding='utf-8') as f:
            cls.css_content = f.read()

    def setUp(self):
        self.client = self.app.test_client()

    # ── 1. CSS Architecture & Global Content Offset Rules ──────────────
    def test_01_css_navbar_tokens_and_scroll_padding(self):
        """Verify CSS tokens and global offset architecture in style.css."""
        # 1. Desktop and responsive navbar tokens
        self.assertIn('--navbar-height: 70px', self.css_content, "Desktop --navbar-height token must be defined in :root")
        self.assertIn('--navbar-height: 64px', self.css_content, "Tablet/mobile --navbar-height token must be defined in media query")

        # 2. Global html scroll-padding-top
        self.assertTrue(
            re.search(r'html\s*\{[^}]*scroll-padding-top:\s*var\(--navbar-height\)', self.css_content),
            "html element must define scroll-padding-top: var(--navbar-height) to prevent anchor clipping behind navbar"
        )

        # 3. Global body content offset
        self.assertTrue(
            re.search(r'body:not\(\.ops-body\)\s*\{[^}]*padding-top:\s*var\(--navbar-height\)', self.css_content),
            "body:not(.ops-body) must enforce padding-top: var(--navbar-height) so all public/customer pages start below navbar"
        )

        # 4. Navbar fixed positioning and height
        self.assertTrue(
            re.search(r'\.navbar\s*\{[^}]*position:\s*fixed', self.css_content),
            ".navbar must use position: fixed"
        )
        self.assertTrue(
            re.search(r'\.navbar\s*\{[^}]*height:\s*var\(--navbar-height\)', self.css_content),
            ".navbar must bind its height to var(--navbar-height)"
        )

        # 5. Hero margin-top reset
        self.assertTrue(
            re.search(r'\.hero\s*\{[^}]*margin-top:\s*0', self.css_content),
            ".hero margin-top must be 0 to prevent double-gap with body padding-top"
        )

    def test_02_css_restaurant_hero_and_menu_nav_bar(self):
        """Verify .restaurant-hero and .menu-nav-bar styles in style.css."""
        # .restaurant-hero
        self.assertTrue(
            re.search(r'\.restaurant-hero\s*\{[^}]*position:\s*relative', self.css_content),
            ".restaurant-hero must be styled with relative positioning"
        )

        # .menu-nav-bar
        self.assertTrue(
            re.search(r'\.menu-nav-bar\s*\{[^}]*position:\s*sticky', self.css_content),
            ".menu-nav-bar must use position: sticky"
        )
        self.assertTrue(
            re.search(r'\.menu-nav-bar\s*\{[^}]*top:\s*var\(--navbar-height', self.css_content),
            ".menu-nav-bar must stick to top: var(--navbar-height)"
        )

    # ── 2. Public Pages & Header Rendering ─────────────────────────────
    def test_03_customer_home_page_layout(self):
        """Customer home page renders navbar and hero banner cleanly."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('class="navbar"', html)
        self.assertIn('class="hero"', html)
        self.assertNotIn('margin-top: 70px', html, "Inline margin-top: 70px must not exist on hero")

    def test_04_restaurants_listing_page_layout(self):
        """Browse restaurants page renders page-header cleanly."""
        res = self.client.get('/restaurants')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('class="navbar"', html)
        self.assertIn('class="page-header"', html)
        self.assertIn('Restaurants in Your City', html)
        self.assertIn('All Restaurants', html)

    def test_05_restaurant_detail_page_hero_and_anchor_clearance(self):
        """Restaurant detail page displays full hero banner and scroll margins."""
        rest = execute_query("SELECT id, name FROM restaurants LIMIT 1", fetchone=True)
        self.assertIsNotNone(rest, "At least one restaurant must exist for detail page test")

        res = self.client.get(f'/restaurant/{rest["id"]}')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Navbar and restaurant-hero exist
        self.assertIn('class="navbar"', html)
        self.assertIn('class="restaurant-hero"', html)
        import html as py_html
        self.assertIn(py_html.escape(rest['name']), html)

        # Verify rating badge, delivery time, delivery fee, and view on map button exist
        self.assertIn('Rating', html)
        self.assertIn('VIEW ON MAP', html)

        # Category sticky bar and scroll-margin-top
        self.assertIn('class="menu-nav-bar"', html)
        self.assertIn('scroll-margin-top:calc(var(--navbar-height, 70px) + 65px)', html)
        self.assertIn('id="reviews-section"', html)

    def test_06_offers_about_contact_search_pages(self):
        """Offers, About, Contact, and Search pages render page-headers cleanly."""
        pages = [
            ('/offers', 'Offers & Promo Codes'),
            ('/about', 'About Foody Hunters'),
            ('/contact', "We'd Love to Hear From You"),
            ('/search?q=pizza', 'Search Results for')
        ]
        for url, expected_heading in pages:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Page {url} must return 200")
            html = res.get_data(as_text=True)
            self.assertIn('class="navbar"', html)
            self.assertIn('class="page-header"', html)
            self.assertIn(expected_heading, html)

    def test_07_portals_page_layout(self):
        """Restaurant Partner Portal at /portals renders single Restaurant Owner card cleanly."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('class="navbar"', html)
        self.assertIn('class="portals-page"', html)
        self.assertIn('Restaurant Owner', html)
        self.assertIn('portalCardRestaurant', html)
        # Verify other portals are not present
        self.assertNotIn('portalCardAdmin', html)
        self.assertNotIn('portalCardDelivery', html)
        self.assertNotIn('portalCardStaff', html)

    def test_08_auth_pages_wrapper_styling(self):
        """Auth pages (login, register, forgot-password, partner logins) render auth-card."""
        auth_urls = [
            '/auth/login',
            '/auth/register',
            '/auth/forgot-password',
            '/restaurant/login',
            '/delivery/login',
            '/delivery/register'
        ]
        for url in auth_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"{url} must return 200")
            html = res.get_data(as_text=True)
            self.assertIn('class="navbar"', html)
            self.assertIn('class="auth-card"', html)

        # Admin login uses dedicated scoped admin layout without customer navbar
        res_admin = self.client.get('/admin/login')
        self.assertEqual(res_admin.status_code, 200)
        admin_html = res_admin.get_data(as_text=True)
        self.assertNotIn('class="navbar"', admin_html)
        self.assertIn('class="auth-card"', admin_html)

        # Restaurant registration renders with card and navbar
        res_reg = self.client.get('/restaurant/register')
        self.assertEqual(res_reg.status_code, 200)
        reg_html = res_reg.get_data(as_text=True)
        self.assertIn('class="navbar"', reg_html)
        self.assertIn('class="card"', reg_html)

        # Staff login is retired
        res_staff = self.client.get('/staff/login', follow_redirects=False)
        self.assertEqual(res_staff.status_code, 302)

    # ── 3. Authenticated Customer & Partner Pages ──────────────────────
    def test_09_authenticated_customer_profile_and_cart(self):
        """Customer profile and cart render page-header without clipping."""
        self.client.post('/auth/login', data={
            'email': 'customer@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Cart
        res_cart = self.client.get('/customer/cart')
        self.assertEqual(res_cart.status_code, 200)
        cart_html = res_cart.get_data(as_text=True)
        self.assertIn('class="page-header"', cart_html)
        self.assertIn('Your Shopping Cart', cart_html)

        # Profile
        res_prof = self.client.get('/customer/profile')
        self.assertEqual(res_prof.status_code, 200)
        prof_html = res_prof.get_data(as_text=True)
        self.assertIn('class="page-header"', prof_html)
        self.assertIn('id="userRoleBadge"', prof_html)

    def test_10_ops_base_uses_sticky_header_without_body_padding(self):
        """Ops Center pages use .ops-body and .ops-header with sticky positioning."""
        # Login admin
        admin_user = execute_query("SELECT email FROM users WHERE role='admin' LIMIT 1", fetchone=True)
        self.client.post('/admin/gate', data={'passkey': 'FH-ADMIN-2026-X99'}, follow_redirects=True)
        self.client.post('/admin/login', data={
            'email': admin_user['email'],
            'password': 'password123'
        }, follow_redirects=True)

        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('class="ops-body"', html)
        self.assertIn('class="ops-header"', html)
        self.assertIn('OPS CENTER', html)

if __name__ == '__main__':
    unittest.main()
