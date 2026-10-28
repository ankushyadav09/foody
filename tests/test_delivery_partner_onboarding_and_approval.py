"""
tests/test_delivery_partner_onboarding_and_approval.py
Comprehensive automated test suite for Delivery Partner onboarding, pending approval workflow,
admin fleet management, and operational authorization.
"""

import unittest
import uuid
import random
from app import create_app
from database import execute_query
from config import Config
from werkzeug.security import generate_password_hash


class TestDeliveryPartnerOnboardingAndApproval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.client = self.app.test_client()

    def _auth_as_admin(self):
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
    # 1. REGISTRATION & VALIDATION
    # ─────────────────────────────────────────────────────────────────────────

    def test_01_delivery_registration_form_renders(self):
        """GET /delivery/register renders dedicated onboarding form with required vehicle and license inputs."""
        res = self.client.get('/delivery/register')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('action="/delivery/register"', html)
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="phone"', html)
        self.assertIn('name="vehicle_type"', html)
        self.assertIn('name="vehicle_number"', html)
        self.assertIn('name="license_number"', html)
        self.assertIn('name="password"', html)

    def test_02_valid_registration_creates_pending_applicant(self):
        """Valid registration creates account with status='pending' and verification_status='pending'."""
        uid = uuid.uuid4().hex[:6]
        email = f"rider_valid_{uid}@test.com"
        phone = f"97{random.randint(10000000, 99999999)}"

        res = self.client.post('/delivery/register', data={
            'name': f"Rider Applicant {uid}",
            'email': email,
            'phone': phone,
            'vehicle_type': 'Motorcycle',
            'vehicle_number': f"GJ-02-AB-{random.randint(1000, 9999)}",
            'license_number': f"DL-GJ02-2024-{random.randint(10000, 99999)}",
            'address': 'Radhanpur Road, Mehsana',
            'city': 'Mehsana',
            'pincode': '384002',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('pending administrator verification', html)

        # Confirm DB records
        user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'delivery')
        self.assertEqual(user['status'], 'pending')

        partner = execute_query("SELECT * FROM delivery_partners WHERE user_id=%s", (user['id'],), fetchone=True)
        self.assertIsNotNone(partner)
        self.assertEqual(partner['verification_status'], 'pending')
        self.assertEqual(partner['is_available'], 0)
        self.assertEqual(partner['is_online'], 0)

    def test_03_invalid_registration_data_rejected(self):
        """Missing required fields or invalid phone numbers are rejected with validation alerts."""
        res_missing = self.client.post('/delivery/register', data={
            'name': '',
            'email': 'bad_email',
            'phone': '123',
            'password': 'short',
            'confirm_password': 'mismatch'
        }, follow_redirects=True)

        self.assertEqual(res_missing.status_code, 200)
        html = res_missing.get_data(as_text=True)
        self.assertIn('Full name is required.', html)
        self.assertIn('Enter a valid email address.', html)
        self.assertIn('Enter a valid 10-digit Indian mobile number.', html)

    def test_04_duplicate_email_or_phone_rejected(self):
        """Duplicate email or phone is gracefully rejected."""
        uid = uuid.uuid4().hex[:6]
        email = f"rider_dup_{uid}@test.com"
        phone = f"96{random.randint(10000000, 99999999)}"

        # First registration
        self.client.post('/delivery/register', data={
            'name': 'Original Rider',
            'email': email,
            'phone': phone,
            'vehicle_type': 'Scooter',
            'vehicle_number': 'GJ-02-XY-1234',
            'license_number': 'DL-GJ02-2024-11111',
            'address': 'Highway, Mehsana',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        # Duplicate attempt
        res_dup = self.client.post('/delivery/register', data={
            'name': 'Duplicate Rider',
            'email': email,
            'phone': f"95{random.randint(10000000, 99999999)}",
            'vehicle_type': 'Scooter',
            'vehicle_number': 'GJ-02-XY-9999',
            'license_number': 'DL-GJ02-2024-22222',
            'address': 'Highway, Mehsana',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(res_dup.status_code, 200)
        self.assertIn('already registered', res_dup.get_data(as_text=True))

    # ─────────────────────────────────────────────────────────────────────────
    # 2. PENDING ACCESS RESTRICTION
    # ─────────────────────────────────────────────────────────────────────────

    def test_05_pending_applicant_cannot_login_at_delivery_login(self):
        """Pending delivery partner cannot sign in to the rider portal."""
        uid = uuid.uuid4().hex[:6]
        email = f"rider_pending_login_{uid}@test.com"
        phone = f"94{random.randint(10000000, 99999999)}"

        execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, %s, 'delivery', 'pending')",
            (f"Pending Rider {uid}", email, phone, generate_password_hash('password123')),
            commit=True
        )

        res_login = self.client.post('/delivery/login', data={
            'email': email,
            'password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(res_login.status_code, 200)
        html = res_login.get_data(as_text=True)
        self.assertIn('pending administrator verification', html)

        # Confirm session was NOT established
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('delivery_auth'))

    def test_06_pending_applicant_cannot_access_dashboard_directly(self):
        """Pending delivery partner cannot access /delivery/dashboard directly."""
        uid = uuid.uuid4().hex[:6]
        u_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'hash', 'delivery', 'pending')",
            (f"Pending Bypass Rider {uid}", f"rider_bypass_{uid}@test.com", f"93{random.randint(10000000, 99999999)}"),
            commit=True
        )
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-BP-1111', 'DL-BP-1111', 0, 0, 'pending')",
            (u_id,),
            commit=True
        )

        # Mock an auth session with pending user_id
        with self.client.session_transaction() as sess:
            sess['user_id'] = u_id
            sess['role'] = 'delivery'
            sess['delivery_auth'] = {'user_id': u_id, 'role': 'delivery'}

        res_dash = self.client.get('/delivery/dashboard', follow_redirects=False)
        self.assertEqual(res_dash.status_code, 302)
        self.assertIn('/delivery/login', res_dash.headers.get('Location', ''))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. ADMIN REVIEW, APPROVAL & REJECTION LIFECYCLE
    # ─────────────────────────────────────────────────────────────────────────

    def test_07_admin_reviews_and_approves_delivery_partner(self):
        """Admin views pending delivery partner and approves application."""
        uid = uuid.uuid4().hex[:6]
        email = f"rider_to_approve_{uid}@test.com"
        u_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, %s, 'delivery', 'pending')",
            (f"Approve Rider {uid}", email, f"92{random.randint(10000000, 99999999)}", generate_password_hash('password123')),
            commit=True
        )
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, verification_status) VALUES (%s, 'Electric Bike', 'GJ-02-EV-9999', 'DL-EV-9999', 0, 0, 'pending')",
            (u_id,),
            commit=True
        )

        self._auth_as_admin()

        # Admin checks pending fleet list
        res_list = self.client.get('/admin/delivery-partners?status=pending')
        self.assertEqual(res_list.status_code, 200)
        self.assertIn(f"Approve Rider {uid}", res_list.get_data(as_text=True))

        # Admin approves
        res_appr = self.client.post(f'/admin/delivery-partners/approve/{u_id}', follow_redirects=True)
        self.assertEqual(res_appr.status_code, 200)
        self.assertIn('approved and activated', res_appr.get_data(as_text=True))

        # Check DB status
        user = execute_query("SELECT status FROM users WHERE id=%s", (u_id,), fetchone=True)
        self.assertEqual(user['status'], 'active')
        dp = execute_query("SELECT verification_status, is_available, is_online FROM delivery_partners WHERE user_id=%s", (u_id,), fetchone=True)
        self.assertEqual(dp['verification_status'], 'approved')
        self.assertEqual(dp['is_available'], 1)

        # Clear admin session and verify approved rider can now log in
        self.client.get('/admin/logout')
        res_rider_login = self.client.post('/delivery/login', data={
            'email': email,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res_rider_login.status_code, 200)
        self.assertIn('Welcome back to Rider Portal', res_rider_login.get_data(as_text=True))

    def test_08_admin_rejects_delivery_partner(self):
        """Admin rejects delivery partner application and applicant cannot log in."""
        uid = uuid.uuid4().hex[:6]
        email = f"rider_to_reject_{uid}@test.com"
        u_id = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, %s, 'delivery', 'pending')",
            (f"Reject Rider {uid}", email, f"91{random.randint(10000000, 99999999)}", generate_password_hash('password123')),
            commit=True
        )
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-RJ-0000', 'DL-RJ-0000', 0, 0, 'pending')",
            (u_id,),
            commit=True
        )

        self._auth_as_admin()

        # Admin rejects applicant
        res_rej = self.client.post(f'/admin/delivery-partners/reject/{u_id}', data={
            'rejection_reason': 'Invalid vehicle registration documents.'
        }, follow_redirects=True)
        self.assertEqual(res_rej.status_code, 200)

        # Verify DB status
        user = execute_query("SELECT status FROM users WHERE id=%s", (u_id,), fetchone=True)
        self.assertEqual(user['status'], 'rejected')
        dp = execute_query("SELECT verification_status FROM delivery_partners WHERE user_id=%s", (u_id,), fetchone=True)
        self.assertEqual(dp['verification_status'], 'rejected')

        # Clear admin session and verify rejected applicant login attempt is blocked
        self.client.get('/admin/logout')
        res_rej_login = self.client.post('/delivery/login', data={
            'email': email,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res_rej_login.status_code, 200)
        self.assertIn('application has been rejected', res_rej_login.get_data(as_text=True))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. OPERATIONAL MODULES & ROLE ISOLATION
    # ─────────────────────────────────────────────────────────────────────────

    def test_09_approved_rider_operational_dashboard_and_history(self):
        """Approved rider can access operational dashboard, trips history, and profile."""
        # Use existing active test delivery partner
        res_login = self.client.post('/delivery/login', data={
            'email': 'delivery@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)

        res_dash = self.client.get('/delivery/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        res_hist = self.client.get('/delivery/history')
        self.assertEqual(res_hist.status_code, 200)

        res_prof = self.client.get('/delivery/profile')
        self.assertEqual(res_prof.status_code, 200)

        # Delivery partner cannot access admin dashboard
        res_admin = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res_admin.status_code, 302)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. OPERATIONAL ACCESS PAGE & FULL LIFECYCLE
    # ─────────────────────────────────────────────────────────────────────────

    def test_10_operational_access_page_renders_two_distinct_options(self):
        """Dedicated operational access page (/operations) renders Option A (Admin) and Option B (Delivery Partner Rider)."""
        for url in ('/operations', '/ops-access', '/ops/access'):
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Failed at {url}")
            html = res.get_data(as_text=True)

            # Option A: Admin Control Center
            self.assertIn('Admin Control Center', html)
            self.assertIn('/admin/gate', html)
            self.assertIn('btnOpenAdminControlCenter', html)

            # Option B: Delivery Partner (Rider)
            self.assertIn('Delivery Partner (Rider)', html)
            self.assertIn('/delivery/register', html)
            self.assertIn('btnRegisterDeliveryPartner', html)
            self.assertIn('/delivery/login', html)
            self.assertIn('btnLoginDeliveryPartner', html)
            self.assertIn('Admin Approval Required', html)

    def test_11_full_delivery_partner_approval_lifecycle_end_to_end(self):
        """
        Complete isolated lifecycle:
        Register Rider -> Confirm Pending -> Deny Login -> Deny Dashboard ->
        Admin Passkey Login -> Approve Rider -> Rider Login Success -> Dashboard Access 200.
        """
        uid = uuid.uuid4().hex[:6]
        email = f"lifecycle_rider_{uid}@test.com"
        phone = f"90{random.randint(10000000, 99999999)}"
        password = "RiderPass@123"

        # 1. Prospective Rider registers
        reg_res = self.client.post('/delivery/register', data={
            'name': f"Lifecycle Rider {uid}",
            'email': email,
            'phone': phone,
            'vehicle_type': 'Motorcycle',
            'vehicle_number': f"GJ-02-LC-{random.randint(1000, 9999)}",
            'license_number': f"DL-GJ02-LC-{random.randint(10000, 99999)}",
            'address': 'Mehsana Highway Circle',
            'city': 'Mehsana',
            'pincode': '384002',
            'password': password,
            'confirm_password': password
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn('pending administrator verification', reg_res.get_data(as_text=True))

        # Check DB pending
        rider_user = execute_query("SELECT id, role, status FROM users WHERE email=%s", (email,), fetchone=True)
        self.assertIsNotNone(rider_user)
        self.assertEqual(rider_user['role'], 'delivery')
        self.assertEqual(rider_user['status'], 'pending')
        rider_uid = rider_user['id']

        # 2. Login denial while pending
        login_res1 = self.client.post('/delivery/login', data={'email': email, 'password': password}, follow_redirects=True)
        self.assertEqual(login_res1.status_code, 200)
        self.assertIn('pending administrator verification', login_res1.get_data(as_text=True))

        # 3. Direct dashboard access blocked
        with self.client.session_transaction() as sess:
            sess['delivery_auth'] = {'user_id': rider_uid, 'role': 'delivery'}
        dash_res = self.client.get('/delivery/dashboard', follow_redirects=False)
        self.assertEqual(dash_res.status_code, 302)
        self.assertIn('/delivery/login', dash_res.headers.get('Location', ''))

        # 4. Admin authenticates via direct passkey at /admin/gate
        self.client.get('/delivery/logout')
        gate_res = self.client.post('/admin/gate', data={'gate_password': Config.ADMIN_GATE_PASSWORD}, follow_redirects=False)
        self.assertEqual(gate_res.status_code, 302)
        self.assertIn('/admin/dashboard', gate_res.headers.get('Location', ''))

        # 5. Admin approves rider
        appr_res = self.client.post(f'/admin/delivery-partners/approve/{rider_uid}', follow_redirects=True)
        self.assertEqual(appr_res.status_code, 200)
        self.assertIn('approved and activated', appr_res.get_data(as_text=True))

        # 6. Admin logs out
        self.client.get('/admin/logout')

        # 7. Approved rider signs in successfully
        login_res2 = self.client.post('/delivery/login', data={'email': email, 'password': password}, follow_redirects=True)
        self.assertEqual(login_res2.status_code, 200)
        self.assertIn('Welcome back to Rider Portal', login_res2.get_data(as_text=True))

        # 8. Operational Delivery Dashboard renders HTTP 200 with rider info
        dash_res2 = self.client.get('/delivery/dashboard')
        self.assertEqual(dash_res2.status_code, 200)
        self.assertIn(f"Lifecycle Rider {uid}", dash_res2.get_data(as_text=True))

    def test_12_unified_rider_and_delivery_role_architecture(self):
        """Confirms that Rider and Delivery Partner use exactly one unified role ('delivery') and schema."""
        # Ensure no orphan 'rider' role exists in database schema
        invalid_roles = execute_query("SELECT COUNT(*) as count FROM users WHERE role='rider'", fetchone=True)
        self.assertEqual(invalid_roles['count'], 0)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. SINGLE MAIN DELIVERY PARTNER PORTAL (/delivery/portal)
    # ─────────────────────────────────────────────────────────────────────────

    def test_13_delivery_portal_renders_unauthenticated_with_register_and_login_links(self):
        """GET /delivery/portal renders dedicated unified rider portal with active register and login buttons."""
        res = self.client.get('/delivery/portal')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('DELIVERY PARTNER (RIDER)', html)
        self.assertIn('/delivery/register', html)
        self.assertIn('btnRegisterDeliveryPartner', html)
        self.assertIn('/delivery/login', html)
        self.assertIn('btnLoginDeliveryPartner', html)
        self.assertIn('Mandatory Admin Approval Notice', html)

        # Verify buttons link to valid existing endpoints
        reg_res = self.client.get('/delivery/register')
        self.assertEqual(reg_res.status_code, 200)
        login_res = self.client.get('/delivery/login')
        self.assertEqual(login_res.status_code, 200)

    def test_14_delivery_portal_approved_rider_reaches_dashboard(self):
        """Approved authenticated rider visiting /delivery/portal reaches the authorized operational dashboard."""
        # Authenticate as approved rider
        self.client.post('/delivery/login', data={
            'email': 'delivery@foodiehunter.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Visiting portal redirects or provides dashboard entry
        res_portal = self.client.get('/delivery/portal', follow_redirects=False)
        self.assertEqual(res_portal.status_code, 302)
        self.assertIn('/delivery/dashboard', res_portal.headers.get('Location', ''))

        # Direct follow to dashboard
        res_dash = self.client.get('/delivery/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # Portal with ?stay=1 renders dashboard button
        res_stay = self.client.get('/delivery/portal?stay=1')
        self.assertEqual(res_stay.status_code, 200)
        self.assertIn('Open Delivery Dashboard', res_stay.get_data(as_text=True))
        self.assertIn('btnDeliveryDashboard', res_stay.get_data(as_text=True))

    def test_15_delivery_portal_pending_and_rejected_status_protection(self):
        """Pending and rejected applicants see clear status guidance and cannot reach protected operations."""
        uid = uuid.uuid4().hex[:6]
        # Pending applicant
        u_pending = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'h', 'delivery', 'pending')",
            (f"Pending Test {uid}", f"portal_pending_{uid}@test.com", f"99{random.randint(10000000, 99999999)}"),
            commit=True
        )
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-P-1', 'DL-P-1', 0, 0, 'pending')",
            (u_pending,), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['delivery_auth'] = {'user_id': u_pending, 'role': 'delivery'}

        res_p = self.client.get('/delivery/portal')
        self.assertEqual(res_p.status_code, 200)
        self.assertIn('Application Pending Admin Verification', res_p.get_data(as_text=True))

        # Direct dashboard remains blocked
        res_dash_p = self.client.get('/delivery/dashboard', follow_redirects=False)
        self.assertEqual(res_dash_p.status_code, 302)
        self.assertIn('/delivery/login', res_dash_p.headers.get('Location', ''))

        # Clear session and test rejected applicant
        self.client.get('/delivery/logout')
        u_rej = execute_query(
            "INSERT INTO users (name, email, phone, password_hash, role, status) VALUES (%s, %s, %s, 'h', 'delivery', 'rejected')",
            (f"Rejected Test {uid}", f"portal_rej_{uid}@test.com", f"98{random.randint(10000000, 99999999)}"),
            commit=True
        )
        execute_query(
            "INSERT INTO delivery_partners (user_id, vehicle_type, vehicle_number, license_number, is_available, is_online, verification_status) VALUES (%s, 'Motorcycle', 'GJ-02-R-1', 'DL-R-1', 0, 0, 'rejected')",
            (u_rej,), commit=True
        )

        with self.client.session_transaction() as sess:
            sess['delivery_auth'] = {'user_id': u_rej, 'role': 'delivery'}
            sess['user_id'] = u_rej
            sess['role'] = 'delivery'

        res_r = self.client.get('/delivery/portal')
        self.assertEqual(res_r.status_code, 200)
        self.assertIn('Application Not Approved', res_r.get_data(as_text=True))

        # Direct dashboard remains blocked
        res_dash_r = self.client.get('/delivery/dashboard', follow_redirects=False)
        self.assertEqual(res_dash_r.status_code, 302)
        self.assertIn('/delivery/login', res_dash_r.headers.get('Location', ''))


if __name__ == '__main__':
    unittest.main()


