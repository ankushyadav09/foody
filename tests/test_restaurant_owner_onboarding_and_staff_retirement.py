"""
tests/test_restaurant_owner_onboarding_and_staff_retirement.py
Comprehensive end-to-end test suite verifying:
1. Public Partner With Us experience (Restaurant Owner only)
2. Complete Restaurant Owner onboarding workflow (Owner details, Outlet details, Multi-dish onboarding, Secure KYC docs)
3. Document protection (Private verification document access control)
4. Admin approval/rejection lifecycle with rejection reasons
5. Permanent retirement of Hotel / Restaurant Staff feature
6. Preservation of Admin operations and Delivery Partner operations
"""

import io
import os
import random
import sys
import unittest
import uuid
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from werkzeug.security import generate_password_hash


def create_dummy_png():
    """Create a minimal genuine 100x100 PNG in memory for image upload testing."""
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color=(255, 69, 0))
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


class TestRestaurantOwnerOnboardingAndStaffRetirement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.client = self.app.test_client()

    def _login_as_admin(self):
        with self.client.session_transaction() as sess:
            sess['admin_gate_passed'] = True
            sess['role'] = 'admin'
            admin = execute_query("SELECT id, name, email FROM users WHERE role='admin' LIMIT 1", fetchone=True)
            u_id = admin['id'] if admin else 1
            u_name = admin['name'] if admin else 'Administrator'
            u_email = admin['email'] if admin else 'admin@foodyhunters.com'
            sess['user_id'] = u_id
            sess['user_name'] = u_name
            sess['user_email'] = u_email
            sess['admin_auth'] = {
                'user_id': u_id,
                'user_name': u_name,
                'user_email': u_email,
                'role': 'admin'
            }

    # ─────────────────────────────────────────────────────────────────────────
    # 1. PUBLIC NAVIGATION & PARTNER WITH US EXPERIENCE
    # ─────────────────────────────────────────────────────────────────────────

    def test_01_partner_with_us_loads_restaurant_owner_only_portal(self):
        """Navbar 'Partner With Us' opens /portals showing exactly ONE option: Restaurant Owner."""
        res = self.client.get('/portals')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Branding & Heading
        self.assertIn("Partner With", html)
        self.assertIn("FOODY HUNTERS", html)

        # Exactly ONE partner card is present: Restaurant Owner
        self.assertIn('id="portalCardRestaurant"', html)
        self.assertIn('Restaurant Owner', html)
        self.assertIn('id="btnRestaurantRegister"', html)
        self.assertIn('id="btnRestaurantLogin"', html)
        self.assertIn('id="backToCustomerLink"', html)

        # Admin, Delivery Partner, and Staff cards are strictly ABSENT
        self.assertNotIn('id="portalCardAdmin"', html)
        self.assertNotIn('Admin Control Center', html)
        self.assertNotIn('id="portalCardDelivery"', html)
        self.assertNotIn('Delivery Partner', html)
        self.assertNotIn('id="portalCardStaff"', html)
        self.assertNotIn('Hotel / Restaurant Staff', html)

    def test_02_customer_facing_templates_have_no_admin_delivery_or_staff_portals(self):
        """Customer homepage, footer, and login pages do not expose Admin, Delivery Partner or Staff portals."""
        # 1. Customer Home & Footer
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        home_html = res_home.get_data(as_text=True)
        self.assertNotIn('href="/admin"', home_html)
        self.assertNotIn('href="/delivery/login"', home_html)
        self.assertNotIn('href="/staff/login"', home_html)
        self.assertIn('href="/portals"', home_html)
        self.assertIn('href="/restaurant/register"', home_html)

        # 2. Customer Login
        res_login = self.client.get('/auth/login')
        self.assertEqual(res_login.status_code, 200)
        login_html = res_login.get_data(as_text=True)
        self.assertNotIn('Delivery Rider Login', login_html)
        self.assertNotIn('/delivery/login', login_html)
        self.assertNotIn('/staff/login', login_html)

        # 3. Customer Register
        res_reg = self.client.get('/auth/register')
        self.assertEqual(res_reg.status_code, 200)
        reg_html = res_reg.get_data(as_text=True)
        self.assertNotIn('Join Delivery Fleet', reg_html)
        self.assertNotIn('/delivery/register', reg_html)
        self.assertNotIn('/staff/register', reg_html)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. RESTAURANT OWNER ONBOARDING WORKFLOW & VALIDATION
    # ─────────────────────────────────────────────────────────────────────────

    def test_03_registration_missing_required_fields_rejected(self):
        """Missing required fields (owner name, email, phone, restaurant_name, password) are rejected."""
        res = self.client.post('/restaurant/register', data={}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Owner full name is required.', html)

    def test_04_registration_invalid_email_and_phone_rejected(self):
        """Invalid email formats and non-10-digit phone numbers are rejected with clear errors."""
        res = self.client.post('/restaurant/register', data={
            'name': 'Test Owner',
            'email': 'not-an-email',
            'phone': '12345',
            'restaurant_name': 'Test Cafe',
            'cuisine': 'Fast Food',
            'address': 'Main Road',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Enter a valid business email address.', html)
        self.assertIn('Enter a valid 10-digit Indian mobile number.', html)

    def test_05_registration_duplicate_owner_rejected(self):
        """Duplicate owner email and mobile are rejected gracefully without losing input."""
        uid = uuid.uuid4().hex[:6]
        dup_email = f"dup_{uid}@test.com"
        dup_phone = f"98{random.randint(10000000, 99999999)}"

        execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'customer', 'active')",
            (f"Existing User {uid}", dup_email, dup_phone), commit=True
        )

        res = self.client.post('/restaurant/register', data={
            'name': 'Duplicate Owner',
            'email': dup_email,
            'phone': dup_phone,
            'restaurant_name': 'Dup Cafe',
            'cuisine': 'Beverages',
            'address': 'Highway Circle',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('already registered', html)

    def test_06_complete_registration_with_owner_outlet_and_dishes(self):
        """Full registration with owner details, contact person, outlet specs, private KYC doc, and multiple dishes."""
        uid = uuid.uuid4().hex[:6]
        email = f"owner_complete_{uid}@testkitchen.com"
        phone = f"98{random.randint(10000000, 99999999)}"
        rest_name = f"Heritage Rasoi {uid}"

        mock_kyc_pdf = (io.BytesIO(b"%PDF-1.4 Mock Private FSSAI Certificate"), "fssai_cert.pdf")
        mock_dish_img1 = (create_dummy_png(), "paneer_tikka.png")
        mock_dish_img2 = (create_dummy_png(), "dal_makhani.png")

        data = {
            'name': f"Chef {uid}",
            'email': email,
            'phone': phone,
            'contact_person': f"Manager {uid}",
            'restaurant_name': rest_name,
            'cuisine': 'North Indian, Mughlai',
            'address': 'Shop 12, Heritage Square, Modhera Road',
            'restaurant_area': 'Modhera Road',
            'city_choice': 'Mehsana',
            'pincode': '384002',
            'restaurant_phone': phone,
            'restaurant_email': email,
            'open_time': '10:00',
            'close_time': '23:30',
            'operating_days': 'Monday - Sunday',
            'prep_time': '25-35 mins',
            'description': 'Royal traditional recipes with freshly ground spices.',
            'fssai_number': '11521000000000',
            'gstin': '24AAACH7409R1ZZ',
            'password': 'SecretPassword@123',
            'confirm_password': 'SecretPassword@123',
            'document': mock_kyc_pdf,
            # Multi-dish inputs:
            'dish_name[]': ['Paneer Tikka Angara', 'Dal Makhani Special'],
            'dish_category[]': ['2', '2'],
            'dish_price[]': ['260.00', '190.00'],
            'dish_veg_type[]': ['veg', 'veg'],
            'dish_prep_time[]': ['20', '15'],
            'dish_description[]': ['Smoky char-grilled cottage cheese with bell peppers', 'Slow-cooked black lentils in rich cream butter'],
            'dish_image[]': [mock_dish_img1, mock_dish_img2]
        }

        res = self.client.post('/restaurant/register', data=data, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/restaurant/application-status', res.headers.get('Location', ''))

        # Check DB User
        user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'restaurant')

        # Check DB Restaurant
        rest = execute_query("SELECT * FROM restaurants WHERE owner_id=%s", (user['id'],), fetchone=True)
        self.assertIsNotNone(rest)
        self.assertEqual(rest['name'], rest_name)
        self.assertEqual(rest['verification_status'], 'pending')
        self.assertEqual(rest['status'], 'inactive')
        self.assertEqual(rest['contact_person'], f"Manager {uid}")
        self.assertEqual(rest['gstin'], '24AAACH7409R1ZZ')
        self.assertEqual(rest['operating_days'], 'Monday - Sunday')
        self.assertEqual(rest['prep_time'], '25-35 mins')

        # Check KYC Document was saved to secure route (NOT static)
        self.assertTrue(rest['verification_doc'].startswith('/documents/secure-view/'))

        # Check Dishes were created in food_items
        dishes = execute_query("SELECT * FROM food_items WHERE restaurant_id=%s ORDER BY id ASC", (rest['id'],), fetchall=True)
        self.assertEqual(len(dishes), 2)
        self.assertEqual(dishes[0]['name'], 'Paneer Tikka Angara')
        self.assertEqual(float(dishes[0]['price']), 260.00)
        self.assertEqual(dishes[1]['name'], 'Dal Makhani Special')
        self.assertEqual(float(dishes[1]['price']), 190.00)

        # Check Application Status displays restaurant and submitted dishes
        res_status = self.client.get(f"/restaurant/application-status?id={rest['id']}")
        self.assertEqual(res_status.status_code, 200)
        status_html = res_status.get_data(as_text=True)
        self.assertIn('Pending Administrator Verification', status_html)
        self.assertIn(rest_name, status_html)
        self.assertIn('Paneer Tikka Angara', status_html)
        self.assertIn('Dal Makhani Special', status_html)

    def test_07_dish_validation_rejects_negative_or_zero_price(self):
        """Dish validation catches invalid prices (zero or negative) and displays error."""
        uid = uuid.uuid4().hex[:6]
        res = self.client.post('/restaurant/register', data={
            'name': f"Owner {uid}",
            'email': f"owner_badprice_{uid}@test.com",
            'phone': f"98{random.randint(10000000, 99999999)}",
            'restaurant_name': f"Invalid Price Cafe {uid}",
            'cuisine': 'Snacks',
            'address': 'Main Market',
            'password': 'password123',
            'confirm_password': 'password123',
            'dish_name[]': ['Invalid Zero Dish'],
            'dish_price[]': ['0.00']
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Price must be greater than zero.', html)

    def test_08_dish_validation_rejects_corrupted_image(self):
        """Dish validation catches corrupted non-image files uploaded as dish images."""
        uid = uuid.uuid4().hex[:6]
        corrupted_file = (io.BytesIO(b"This is completely invalid corrupted binary payload"), "bad_food.png")
        res = self.client.post('/restaurant/register', data={
            'name': f"Owner {uid}",
            'email': f"owner_badimg_{uid}@test.com",
            'phone': f"98{random.randint(10000000, 99999999)}",
            'restaurant_name': f"Bad Image Cafe {uid}",
            'cuisine': 'Snacks',
            'address': 'Main Market',
            'password': 'password123',
            'confirm_password': 'password123',
            'dish_name[]': ['Corrupted Image Dish'],
            'dish_price[]': ['120.00'],
            'dish_image[]': [corrupted_file]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Invalid food image file.', html)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. SECURE VERIFICATION DOCUMENT ACCESS CONTROL
    # ─────────────────────────────────────────────────────────────────────────

    def test_09_private_verification_document_protection(self):
        """Confidential verification documents are protected: unauthenticated users cannot access them."""
        # 1. Unauthenticated request to /documents/secure-view/<filename> is redirected or rejected
        res = self.client.get('/documents/secure-view/doc_nonexistent_test.pdf')
        self.assertIn(res.status_code, (302, 401, 403, 404))

        # 2. Authenticated Admin can access secure document viewer
        self._login_as_admin()
        res_admin = self.client.get('/documents/secure-view/doc_nonexistent_test.pdf')
        # Admin is authorized; since file doesn't exist, returns 404 rather than 403 Forbidden
        self.assertEqual(res_admin.status_code, 404)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. ADMIN APPROVAL & REJECTION LIFECYCLE
    # ─────────────────────────────────────────────────────────────────────────

    def test_10_admin_rejects_restaurant_with_logged_reason(self):
        """Admin rejection records rejection reason and owner sees it on application status desk."""
        uid = uuid.uuid4().hex[:6]
        user_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'restaurant', 'active')",
            (f"Owner {uid}", f"owner_reject_{uid}@test.com", f"99{random.randint(10000000, 99999999)}"),
            commit=True
        )
        rest_id = execute_query(
            """INSERT INTO restaurants (owner_id, name, cuisine, address, city, phone, rating, verification_status, status)
               VALUES (%s, %s, 'Gujarati', 'Highway', 'Mehsana', '9898989898', 4.5, 'pending', 'inactive')""",
            (user_id, f"To Be Rejected Outlet {uid}"),
            commit=True
        )

        self._login_as_admin()
        reason = "Missing FSSAI license certificate and health compliance certificate."
        res_reject = self.client.post(f'/admin/restaurants/reject/{rest_id}', data={'rejection_reason': reason}, follow_redirects=True)
        self.assertEqual(res_reject.status_code, 200)

        # Check DB state
        rest = execute_query("SELECT verification_status, status, rejection_reason FROM restaurants WHERE id=%s", (rest_id,), fetchone=True)
        self.assertEqual(rest['verification_status'], 'rejected')
        self.assertEqual(rest['status'], 'inactive')
        self.assertEqual(rest['rejection_reason'], reason)

        # Owner status page displays reason
        res_status = self.client.get(f'/restaurant/application-status?id={rest_id}')
        self.assertEqual(res_status.status_code, 200)
        status_html = res_status.get_data(as_text=True)
        self.assertIn('Application Not Approved', status_html)
        self.assertIn(reason, status_html)

    def test_11_admin_approves_restaurant_and_becomes_visible_to_customers(self):
        """Admin approves application; restaurant and its dishes become visible on customer storefront."""
        uid = uuid.uuid4().hex[:6]
        user_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'restaurant', 'active')",
            (f"Owner {uid}", f"owner_approve_{uid}@test.com", f"99{random.randint(10000000, 99999999)}"),
            commit=True
        )
        rest_name = f"Approved Grand Palace {uid}"
        rest_id = execute_query(
            """INSERT INTO restaurants (owner_id, name, cuisine, address, city, phone, rating, verification_status, status)
               VALUES (%s, %s, 'North Indian', 'Highway', 'Mehsana', '9898989898', 4.8, 'pending', 'inactive')""",
            (user_id, rest_name),
            commit=True
        )

        # Before approval: Restaurant card is NOT listed on customer storefront
        res_before = self.client.get(f'/restaurants?q={rest_name}')
        self.assertNotIn(f'/restaurant/{rest_id}', res_before.get_data(as_text=True))
        self.assertIn('Showing <span class="text-primary">0</span> Restaurants', res_before.get_data(as_text=True))

        # Admin approves
        self._login_as_admin()
        res_appr = self.client.post(f'/admin/restaurants/approve/{rest_id}', follow_redirects=True)
        self.assertEqual(res_appr.status_code, 200)

        # After approval: Restaurant is listed on customer storefront
        res_after = self.client.get(f'/restaurants?q={rest_name}')
        self.assertIn(f'/restaurant/{rest_id}', res_after.get_data(as_text=True))
        self.assertIn(rest_name, res_after.get_data(as_text=True))

    # ─────────────────────────────────────────────────────────────────────────
    # 5. STAFF RETIREMENT & OPERATIONAL PRESERVATION
    # ─────────────────────────────────────────────────────────────────────────

    def test_12_staff_portal_retired_and_cannot_expose_working_portal(self):
        """All staff routes are retired and redirect to /portals without exposing working portal."""
        for endpoint in ['/staff/login', '/staff/register', '/staff/dashboard', '/staff/orders', '/staff/menu']:
            res = self.client.get(endpoint, follow_redirects=False)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/portals', res.headers.get('Location', ''))

    def test_13_admin_and_delivery_operations_preserved(self):
        """Admin and Delivery operational routes remain intact and accessible."""
        # 1. Admin login route exists
        res_admin_login = self.client.get('/admin/login')
        self.assertEqual(res_admin_login.status_code, 200)

        # 2. Delivery partner login and registration exist
        res_deliv_login = self.client.get('/delivery/login')
        self.assertEqual(res_deliv_login.status_code, 200)
        res_deliv_reg = self.client.get('/delivery/register')
        self.assertEqual(res_deliv_reg.status_code, 200)


if __name__ == '__main__':
    unittest.main()
