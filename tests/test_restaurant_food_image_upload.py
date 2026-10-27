"""
tests/test_restaurant_food_image_upload.py
Comprehensive regression tests for Restaurant Food Item Add and Image Upload:

Test A: Route and Add Food page access, methods, and auth protection (no 404s).
Test B: Food item creation without uploaded file (or with image_url).
Test C: Food item creation with genuine image upload (multipart/form-data, Pillow validation, disk persistence, URL accessibility, and menu/storefront visibility).
Test D: Edit food item (preserving existing image vs replacing with new image).
Test E: Invalid, malicious, corrupted, and path-traversal upload rejection (no invalid DB records).
Test F: Restaurant data isolation and approval gating (anti-tamper restaurant_id, cross-restaurant edit prevention, pending restaurant gating).
"""

import os
import sys
import io
import unittest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from config import Config
from database import execute_query


def generate_test_image(format='PNG', size=(120, 120), color=(34, 197, 94)):
    """Generate in-memory valid image bytes using Pillow."""
    buf = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(buf, format=format)
    buf.seek(0)
    return buf


class TestRestaurantFoodImageUpload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        # Ensure upload folder exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

        # Retrieve or setup test restaurants
        # Restaurant 1: The Grand Thakar (owner_id = 2)
        cls.rest1 = execute_query("SELECT * FROM restaurants WHERE id=1", fetchone=True)
        # Restaurant 2: Royal Gujarati Thali (owner_id = 5)
        cls.rest2 = execute_query("SELECT * FROM restaurants WHERE id=2", fetchone=True)

        # Get a valid food category id
        cat = execute_query("SELECT id FROM food_categories LIMIT 1", fetchone=True)
        cls.cat_id = cat['id'] if cat else 1

        cls.created_item_ids = []
        cls.created_files = []

    @classmethod
    def tearDownClass(cls):
        # Clean up database records created during test
        if cls.created_item_ids:
            for item_id in cls.created_item_ids:
                execute_query("DELETE FROM food_items WHERE id=%s", (item_id,), commit=True)
        # Clean up files created on disk
        for fpath in cls.created_files:
            if os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass

    def _login_owner_1(self, client):
        """Helper to establish session for Restaurant 1 Owner (owner_id=2)."""
        with client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_name'] = 'Chef Sanjeev Kumar'
            sess['role'] = 'restaurant'
            sess['user_email'] = 'restaurant@foodiehunter.com'
            sess['restaurant_auth'] = {
                'user_id': 2,
                'user_name': 'Chef Sanjeev Kumar',
                'user_email': 'restaurant@foodiehunter.com',
                'role': 'restaurant',
                'restaurant_id': 1
            }

    def _login_owner_2(self, client):
        """Helper to establish session for Restaurant 2 Owner (owner_id=5)."""
        with client.session_transaction() as sess:
            sess['user_id'] = 5
            sess['user_name'] = 'Owner 2'
            sess['role'] = 'restaurant'
            sess['user_email'] = 'owner2@foodiehunter.com'
            sess['restaurant_auth'] = {
                'user_id': 5,
                'user_name': 'Owner 2',
                'user_email': 'owner2@foodiehunter.com',
                'role': 'restaurant',
                'restaurant_id': 2
            }

    def _login_customer(self, client):
        """Helper to establish session for a regular customer."""
        with client.session_transaction() as sess:
            sess['user_id'] = 999
            sess['user_name'] = 'Customer Test'
            sess['role'] = 'customer'
            sess['user_email'] = 'customer@test.com'

    # ─────────────────────────────────────────────────────────────────────────
    # TEST A: Route and Add Food Page Access & Methods
    # ─────────────────────────────────────────────────────────────────────────

    def test_01_add_food_routes_accessible_for_approved_owner(self):
        """Test A1: Approved owner can open /restaurant/add-food, /restaurant/menu/add, /restaurant/food/add without 404."""
        client = self.app.test_client()
        self._login_owner_1(client)

        for route in ['/restaurant/add-food', '/restaurant/menu/add', '/restaurant/food/add']:
            res = client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with status {res.status_code}")
            html = res.data.decode('utf-8')
            self.assertIn("Add New Food Item", html, f"Page title missing on {route}")
            self.assertIn('name="name"', html)
            self.assertIn('name="price"', html)
            self.assertIn('name="image"', html)
            self.assertIn('enctype="multipart/form-data"', html, f"Missing multipart enctype on {route}")
            self.assertIn('action="/restaurant/add-food"', html, f"Form action should target /restaurant/add-food")

    def test_02_add_food_requires_restaurant_authentication(self):
        """Test A2: Unauthenticated visitors cannot access or post to /restaurant/add-food (redirected, not 404)."""
        client = self.app.test_client()
        # GET without auth
        res_get = client.get('/restaurant/add-food')
        self.assertEqual(res_get.status_code, 302)
        self.assertIn('/restaurant/login', res_get.headers.get('Location', ''))

        # POST without auth
        res_post = client.post('/restaurant/add-food', data={'name': 'Hacker Dish', 'price': '100'})
        self.assertEqual(res_post.status_code, 302)
        self.assertIn('/restaurant/login', res_post.headers.get('Location', ''))

    def test_03_customer_cannot_access_restaurant_add_food(self):
        """Test A3: Customer accounts are blocked from accessing or posting to /restaurant/add-food."""
        client = self.app.test_client()
        self._login_customer(client)

        res_get = client.get('/restaurant/add-food', follow_redirects=True)
        self.assertEqual(res_get.status_code, 200)
        self.assertIn("Access denied", res_get.data.decode('utf-8'))

        res_post = client.post('/restaurant/add-food', data={'name': 'Customer Dish', 'price': '99'}, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn("Access denied", res_post.data.decode('utf-8'))

    # ─────────────────────────────────────────────────────────────────────────
    # TEST B: Food Item Without Image Creation
    # ─────────────────────────────────────────────────────────────────────────

    def test_04_create_food_item_without_file_upload(self):
        """Test B: Submit valid food item with no file (or manual image_url) saves correctly."""
        client = self.app.test_client()
        self._login_owner_1(client)

        dish_name = f"Test Dish No-Image {os.urandom(3).hex()}"
        res = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'description': 'Delicious traditional dish cooked with aromatic spices.',
            'price': '180.00',
            'discount': '0',
            'veg_type': 'veg',
            'preparation_time': '15',
            'availability': '1',
            'is_bestseller': '0'
        }, follow_redirects=False)

        # Expect redirect to menu
        self.assertEqual(res.status_code, 302)
        self.assertIn('/restaurant/menu', res.headers.get('Location', ''))

        # Verify database record
        item = execute_query(
            "SELECT * FROM food_items WHERE name=%s AND restaurant_id=1",
            (dish_name,), fetchone=True
        )
        self.assertIsNotNone(item, "Food item was not saved to database!")
        self.created_item_ids.append(item['id'])
        self.assertEqual(item['restaurant_id'], 1)
        self.assertEqual(float(item['price']), 180.0)
        self.assertEqual(item['veg_type'], 'veg')
        self.assertEqual(item['availability'], 1)
        self.assertTrue(item['image'].startswith('http') or item['image'].startswith('/static/'))

    # ─────────────────────────────────────────────────────────────────────────
    # TEST C: Food Item with Genuine Image Upload
    # ─────────────────────────────────────────────────────────────────────────

    def test_05_create_food_item_with_real_image_upload(self):
        """Test C: Upload valid PNG image via multipart/form-data, verify disk file, DB path, URL serve, and storefront."""
        client = self.app.test_client()
        self._login_owner_1(client)

        dish_name = f"Special Paneer Butter Masala {os.urandom(3).hex()}"
        img_stream = generate_test_image(format='PNG', size=(200, 200), color=(234, 88, 12))

        data = {
            'name': dish_name,
            'category_id': str(self.cat_id),
            'description': 'Cottage cheese cubes tossed in rich creamy tomato butter gravy.',
            'price': '275.50',
            'discount': '10',
            'veg_type': 'veg',
            'preparation_time': '25',
            'availability': '1',
            'is_bestseller': '1',
            'image': (img_stream, 'paneer_special.png', 'image/png')
        }

        res = client.post('/restaurant/add-food', data=data, content_type='multipart/form-data', follow_redirects=False)
        self.assertEqual(res.status_code, 302, f"Failed with status {res.status_code}")
        self.assertIn('/restaurant/menu', res.headers.get('Location', ''))

        # Verify DB entry
        item = execute_query(
            "SELECT * FROM food_items WHERE name=%s AND restaurant_id=1",
            (dish_name,), fetchone=True
        )
        self.assertIsNotNone(item, "Uploaded food item record not found in database!")
        self.created_item_ids.append(item['id'])
        self.assertEqual(item['restaurant_id'], 1)
        self.assertEqual(float(item['price']), 275.50)
        self.assertEqual(float(item['final_price']), 247.95)

        # Image path must be /static/uploads/...
        saved_img_path = item['image']
        self.assertTrue(saved_img_path.startswith('/static/uploads/'), f"Invalid image path saved: {saved_img_path}")

        # Verify the physical file exists on disk
        relative_path = saved_img_path.lstrip('/')
        full_disk_path = os.path.join(self.app.root_path, relative_path)
        self.assertTrue(os.path.isfile(full_disk_path), f"Image file does not exist on disk at: {full_disk_path}")
        self.created_files.append(full_disk_path)

        # Verify the image is accessible via HTTP GET request to Flask
        img_res = client.get(saved_img_path)
        self.assertEqual(img_res.status_code, 200, f"Saved image URL {saved_img_path} returned {img_res.status_code}")
        self.assertTrue(len(img_res.data) > 0, "Saved image returned empty byte stream")
        img_res.close()

        # Verify item appears on the restaurant menu management page
        menu_res = client.get('/restaurant/menu')
        self.assertEqual(menu_res.status_code, 200)
        self.assertIn(dish_name.encode('utf-8'), menu_res.data)
        self.assertIn(saved_img_path.encode('utf-8'), menu_res.data)

        # Verify item appears on the customer restaurant detail storefront page (/restaurant/1)
        cust_client = self.app.test_client()
        store_res = cust_client.get('/restaurant/1')
        self.assertEqual(store_res.status_code, 200)
        self.assertIn(dish_name.encode('utf-8'), store_res.data)
        self.assertIn(saved_img_path.encode('utf-8'), store_res.data)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST D: Edit Food Item (Preserve Image vs Update Image)
    # ─────────────────────────────────────────────────────────────────────────

    def test_06_edit_food_item_preserves_image_when_not_replaced(self):
        """Test D1: Editing dish without choosing a file preserves the original image."""
        client = self.app.test_client()
        self._login_owner_1(client)

        # Create item with initial image
        orig_img_stream = generate_test_image(format='JPEG', size=(150, 150), color=(59, 130, 246))
        dish_name = f"Dal Tadka {os.urandom(3).hex()}"
        res_add = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'description': 'Yellow lentils tempered with cumin, garlic and ghee.',
            'price': '160.00',
            'veg_type': 'veg',
            'availability': '1',
            'image': (orig_img_stream, 'dal.jpg', 'image/jpeg')
        }, content_type='multipart/form-data', follow_redirects=False)
        self.assertEqual(res_add.status_code, 302)

        item = execute_query("SELECT * FROM food_items WHERE name=%s AND restaurant_id=1", (dish_name,), fetchone=True)
        self.created_item_ids.append(item['id'])
        original_image_url = item['image']
        orig_disk_path = os.path.join(self.app.root_path, original_image_url.lstrip('/'))
        self.created_files.append(orig_disk_path)

        # Edit the item: change price and name, do NOT upload a file
        updated_dish_name = f"{dish_name} Deluxe"
        res_edit = client.post(f'/restaurant/food/edit/{item["id"]}', data={
            'name': updated_dish_name,
            'category_id': str(self.cat_id),
            'description': 'Yellow lentils tempered with extra double ghee and Kashmiri chillies.',
            'price': '195.00',
            'veg_type': 'veg',
            'availability': '1'
        }, content_type='multipart/form-data', follow_redirects=False)
        self.assertEqual(res_edit.status_code, 302)

        # Verify DB: Name and price changed, but original image remains identical!
        updated_item = execute_query("SELECT * FROM food_items WHERE id=%s", (item['id'],), fetchone=True)
        self.assertEqual(updated_item['name'], updated_dish_name)
        self.assertEqual(float(updated_item['price']), 195.00)
        self.assertEqual(updated_item['image'], original_image_url, "Original image was unexpectedly modified or cleared!")

    def test_07_edit_food_item_replaces_image_with_new_upload(self):
        """Test D2: Uploading replacement image updates the DB and saves new file."""
        client = self.app.test_client()
        self._login_owner_1(client)

        # Create item
        dish_name = f"Jeera Rice {os.urandom(3).hex()}"
        res_add = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '120.00',
            'veg_type': 'veg',
            'availability': '1'
        }, follow_redirects=False)
        self.assertEqual(res_add.status_code, 302)

        item = execute_query("SELECT * FROM food_items WHERE name=%s AND restaurant_id=1", (dish_name,), fetchone=True)
        self.created_item_ids.append(item['id'])

        # Now upload replacement photo
        new_img_stream = generate_test_image(format='PNG', size=(180, 180), color=(168, 85, 247))
        res_edit = client.post(f'/restaurant/food/edit/{item["id"]}', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '135.00',
            'veg_type': 'veg',
            'availability': '1',
            'image': (new_img_stream, 'jeera_rice_new.png', 'image/png')
        }, content_type='multipart/form-data', follow_redirects=False)
        self.assertEqual(res_edit.status_code, 302)

        updated_item = execute_query("SELECT * FROM food_items WHERE id=%s", (item['id'],), fetchone=True)
        self.assertTrue(updated_item['image'].startswith('/static/uploads/'))
        new_disk_path = os.path.join(self.app.root_path, updated_item['image'].lstrip('/'))
        self.assertTrue(os.path.isfile(new_disk_path), "Replacement image file missing on disk!")
        self.created_files.append(new_disk_path)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST E: Invalid, Malicious, Corrupted, and Oversized Uploads
    # ─────────────────────────────────────────────────────────────────────────

    def test_08_reject_non_image_extension(self):
        """Test E1: Reject disallowed extensions (e.g., .pdf, .exe, .sh, .txt) without creating a DB record."""
        client = self.app.test_client()
        self._login_owner_1(client)

        fake_file = io.BytesIO(b"%PDF-1.4 Fake PDF Content")
        dish_name = f"Malicious Dish {os.urandom(3).hex()}"

        res = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '150.00',
            'image': (fake_file, 'exploit.pdf', 'application/pdf')
        }, content_type='multipart/form-data')

        # Should NOT redirect, should render form (200) with error
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Invalid image file", html)

        # Verify NO record was inserted
        item = execute_query("SELECT * FROM food_items WHERE name=%s", (dish_name,), fetchone=True)
        self.assertIsNone(item, "Disallowed file extension upload created an invalid database record!")

    def test_09_reject_corrupted_or_fake_image_content(self):
        """Test E2: File with .png extension but plain text content is rejected by Pillow verification."""
        client = self.app.test_client()
        self._login_owner_1(client)

        fake_png = io.BytesIO(b"NOT A REAL PNG FILE -- PLAIN TEXT PAYLOAD")
        dish_name = f"Corrupt Dish {os.urandom(3).hex()}"

        res = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '199.00',
            'image': (fake_png, 'fake_photo.png', 'image/png')
        }, content_type='multipart/form-data')

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Invalid image file", html)

        item = execute_query("SELECT * FROM food_items WHERE name=%s", (dish_name,), fetchone=True)
        self.assertIsNone(item, "Corrupted image file created an invalid database record!")

    def test_10_reject_empty_zero_byte_file(self):
        """Test E3: 0-byte file is rejected and does not insert record."""
        client = self.app.test_client()
        self._login_owner_1(client)

        empty_file = io.BytesIO(b"")
        dish_name = f"Empty File Dish {os.urandom(3).hex()}"

        res = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '90.00',
            'image': (empty_file, 'empty.jpg', 'image/jpeg')
        }, content_type='multipart/form-data')

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Invalid image file", html)

        item = execute_query("SELECT * FROM food_items WHERE name=%s", (dish_name,), fetchone=True)
        self.assertIsNone(item, "Empty file created an invalid database record!")

    def test_11_path_traversal_filename_sanitization(self):
        """Test E4: Path traversal attempts in filename are sanitized and cannot escape upload directory."""
        client = self.app.test_client()
        self._login_owner_1(client)

        img_stream = generate_test_image(format='PNG', size=(100, 100))
        dish_name = f"Traversal Test {os.urandom(3).hex()}"

        # Attempt traversal in filename
        res = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '110.00',
            'image': (img_stream, '../../../../etc/malicious.png', 'image/png')
        }, content_type='multipart/form-data', follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        item = execute_query("SELECT * FROM food_items WHERE name=%s", (dish_name,), fetchone=True)
        self.assertIsNotNone(item)
        self.created_item_ids.append(item['id'])

        # Must be stored under static/uploads without directory traversal characters
        self.assertTrue(item['image'].startswith('/static/uploads/'))
        actual_path = os.path.normpath(os.path.join(self.app.root_path, item['image'].lstrip('/')))
        upload_folder_norm = os.path.normpath(Config.UPLOAD_FOLDER)
        self.assertTrue(os.path.isfile(actual_path))
        self.assertTrue(actual_path.lower().startswith(upload_folder_norm.lower()))
        self.created_files.append(actual_path)

    def test_12_form_validation_retains_submitted_data_on_error(self):
        """Test E5: When validation fails, form re-renders and preserves user-entered fields."""
        client = self.app.test_client()
        self._login_owner_1(client)

        # Enter invalid negative price
        res = client.post('/restaurant/add-food', data={
            'name': 'Retained Dish Name',
            'category_id': str(self.cat_id),
            'description': 'Description to preserve',
            'price': '-50.00'
        })
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Please enter a valid price greater than zero", html)
        self.assertIn("Retained Dish Name", html)
        self.assertIn("Description to preserve", html)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST F: Restaurant Data Isolation and Approval Gating
    # ─────────────────────────────────────────────────────────────────────────

    def test_13_restaurant_id_derived_from_session_prevents_tampering(self):
        """Test F1: An owner cannot assign a dish to another restaurant by tampering with form data."""
        client = self.app.test_client()
        self._login_owner_1(client)  # Owner of Restaurant 1

        dish_name = f"Anti-Tamper Dish {os.urandom(3).hex()}"
        # Submit with forged restaurant_id=2 (Restaurant 2)
        res = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '250.00',
            'restaurant_id': '2'  # Attacker attempts to inject into Restaurant 2
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        # Verify dish belongs strictly to Restaurant 1, NOT Restaurant 2
        item = execute_query("SELECT * FROM food_items WHERE name=%s", (dish_name,), fetchone=True)
        self.assertIsNotNone(item)
        self.created_item_ids.append(item['id'])
        self.assertEqual(item['restaurant_id'], 1, "Server allowed client to tamper with restaurant_id!")

    def test_14_cross_restaurant_edit_blocked(self):
        """Test F2: Restaurant 2 owner cannot edit or modify Restaurant 1's dishes."""
        client = self.app.test_client()

        # Step 1: Owner 1 creates a dish
        self._login_owner_1(client)
        dish_name = f"Rest 1 Dish {os.urandom(3).hex()}"
        res_add = client.post('/restaurant/add-food', data={
            'name': dish_name,
            'category_id': str(self.cat_id),
            'price': '300.00'
        }, follow_redirects=False)
        self.assertEqual(res_add.status_code, 302)

        item = execute_query("SELECT * FROM food_items WHERE name=%s AND restaurant_id=1", (dish_name,), fetchone=True)
        self.created_item_ids.append(item['id'])

        # Step 2: Owner 2 attempts to edit Owner 1's dish
        client2 = self.app.test_client()
        self._login_owner_2(client2)

        res_edit = client2.post(f'/restaurant/food/edit/{item["id"]}', data={
            'name': 'Hacked Name By Owner 2',
            'price': '1.00'
        }, follow_redirects=False)

        # Must be rejected (redirected with error flash)
        self.assertEqual(res_edit.status_code, 302)

        # Verify DB is unaltered
        unmodified_item = execute_query("SELECT * FROM food_items WHERE id=%s", (item['id'],), fetchone=True)
        self.assertEqual(unmodified_item['name'], dish_name)
        self.assertEqual(float(unmodified_item['price']), 300.00)

    def test_15_pending_restaurant_cannot_add_food_items(self):
        """Test F3: A restaurant owner whose verification_status is pending cannot add food items."""
        # Create a temporary pending restaurant
        execute_query(
            """INSERT INTO restaurants (owner_id, name, cuisine, address, verification_status, status)
               VALUES (998, 'Pending Cafe', 'Cafe', '123 Pending St', 'pending', 'pending')""",
            commit=True
        )
        pending_rest = execute_query("SELECT * FROM restaurants WHERE owner_id=998", fetchone=True)

        try:
            client = self.app.test_client()
            with client.session_transaction() as sess:
                sess['user_id'] = 998
                sess['role'] = 'restaurant'
                sess['user_email'] = 'pending@cafe.com'
                sess['restaurant_auth'] = {
                    'user_id': 998,
                    'role': 'restaurant',
                    'restaurant_id': pending_rest['id']
                }

            # GET should redirect to application_status
            res_get = client.get('/restaurant/add-food')
            self.assertEqual(res_get.status_code, 302)
            self.assertIn('/restaurant/application-status', res_get.headers.get('Location', ''))

            # POST should also redirect to application_status
            res_post = client.post('/restaurant/add-food', data={'name': 'Illegal Dish', 'price': '100'})
            self.assertEqual(res_post.status_code, 302)
            self.assertIn('/restaurant/application-status', res_post.headers.get('Location', ''))

            # Verify no food item created
            item = execute_query("SELECT * FROM food_items WHERE name='Illegal Dish'", fetchone=True)
            self.assertIsNone(item)
        finally:
            if pending_rest:
                execute_query("DELETE FROM restaurants WHERE id=%s", (pending_rest['id'],), commit=True)


if __name__ == '__main__':
    unittest.main()
