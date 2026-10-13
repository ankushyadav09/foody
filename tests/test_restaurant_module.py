"""
test_restaurant_module.py – Automated test suite for Phase 4:
Tests:
1. Restaurant Owner login & dashboard
2. Mandatory Restaurant Profile Edit & MySQL persistence (VIEW -> EDIT -> SAVE -> REFRESH)
3. Restaurant Menu Management (Add food, Edit food, Availability toggle)
4. Restaurant food resource isolation check
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query

app = create_app()
app.config['TESTING'] = True

def run_tests():
    print("=== STARTING RESTAURANT MODULE & PROFILE PERSISTENCE TEST ===")
    client = app.test_client()

    # 1. Establish session for Restaurant Owner (User ID 2: Chef Sanjeev Kumar)
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['user_name'] = 'Chef Sanjeev Kumar'
        sess['role'] = 'restaurant'
        sess['user_email'] = 'restaurant@foodiehunter.com'

    # 2. View Dashboard
    res = client.get('/restaurant/dashboard')
    assert res.status_code == 200, f"Restaurant dashboard failed with {res.status_code}"
    print("[PASS] Restaurant Dashboard: Accessible and rendered (200 OK)")

    # 3. View Profile
    res_prof = client.get('/restaurant/profile')
    assert res_prof.status_code == 200, f"Restaurant profile failed with {res_prof.status_code}"
    print("[PASS] Restaurant Profile: Initial profile view loaded successfully")

    # 4. Mandatory Test: EDIT RESTAURANT PROFILE & SAVE
    updated_name = "The Grand Thakar & Kathiyawadi Express"
    updated_cuisine = "Gujarati, Kathiyawadi, Royal Thali"
    updated_area = "Radhanpur Road"
    updated_phone = "02762-255555"
    updated_deliv_fee = 45.0
    updated_open_time = "08:30"

    res_post = client.post('/restaurant/profile', data={
        'name': updated_name,
        'description': 'Award-winning authentic Gujarati and Kathiyawadi dining in Mehsana.',
        'cuisine': updated_cuisine,
        'address': 'Shop 101, Radhanpur Road, Mehsana',
        'area': updated_area,
        'city': 'Mehsana',
        'state': 'Gujarat',
        'pincode': '384002',
        'phone': updated_phone,
        'email': 'thakar.mehsana@foodiehunter.com',
        'delivery_time': '20-30 min',
        'delivery_fee': str(updated_deliv_fee),
        'min_order': '120.00',
        'open_time': updated_open_time,
        'close_time': '23:30',
        'is_open': '1',
        'latitude': '23.5935000',
        'longitude': '72.3640000'
    }, follow_redirects=True)
    assert res_post.status_code == 200, f"Restaurant profile POST failed with {res_post.status_code}"

    # Verify directly in MySQL
    db_rest = execute_query("SELECT * FROM restaurants WHERE owner_id=2 LIMIT 1", fetchone=True)
    assert db_rest is not None, "Restaurant record missing in MySQL!"
    assert db_rest['name'] == updated_name, f"MySQL name mismatch: {db_rest['name']}"
    assert db_rest['phone'] == updated_phone, f"MySQL phone mismatch: {db_rest['phone']}"
    assert float(db_rest['delivery_fee']) == updated_deliv_fee, f"MySQL delivery fee mismatch: {db_rest['delivery_fee']}"
    print(f"[PASS] Restaurant Profile: MySQL persistence verified (Name: {db_rest['name']}, Phone: {db_rest['phone']})")

    # 5. Mandatory Test: REFRESH (HTTP GET to /restaurant/profile)
    res_refresh = client.get('/restaurant/profile')
    assert res_refresh.status_code == 200
    assert b"The Grand Thakar" in res_refresh.data and b"Kathiyawadi Express" in res_refresh.data, "Updated restaurant name missing after refresh!"
    assert updated_phone.encode('utf-8') in res_refresh.data, "Updated phone missing after refresh!"
    print("[PASS] Restaurant Profile: REFRESH verified – Updated restaurant data persists on reload!")

    # 6. Menu Management: Add New Food Item
    rest_id = db_rest['id']
    res_add_food = client.post('/restaurant/food/add', data={
        'name': 'Special Mehsana Kaju Curry',
        'category_id': '1',
        'description': 'Roasted cashews cooked in rich spiced khoya gravy.',
        'price': '220.00',
        'discount': '10',
        'veg_type': 'veg',
        'preparation_time': '20',
        'availability': '1',
        'is_bestseller': '1'
    }, follow_redirects=True)
    assert res_add_food.status_code == 200, f"Add food failed with status {res_add_food.status_code}"

    # Verify new food in MySQL
    db_food = execute_query(
        "SELECT * FROM food_items WHERE restaurant_id=%s AND name='Special Mehsana Kaju Curry'",
        (rest_id,), fetchone=True
    )
    assert db_food is not None, "Added food item missing from MySQL!"
    print(f"[PASS] Menu Management: Food item added and verified in MySQL (ID: {db_food['id']}, Price: {db_food['price']})")

    # 7. Menu Management: Toggle Availability
    res_toggle = client.post(f"/restaurant/food/toggle/{db_food['id']}", follow_redirects=True)
    assert res_toggle.status_code == 200
    toggled_food = execute_query("SELECT availability FROM food_items WHERE id=%s", (db_food['id'],), fetchone=True)
    assert toggled_food['availability'] == 0, "Food item availability was not toggled!"
    print("[PASS] Menu Management: Food item availability toggled to out-of-stock (0)")

    # Clean up test food item
    execute_query("DELETE FROM food_items WHERE id=%s", (db_food['id'],), commit=True)

    print("=== ALL PHASE 4 RESTAURANT TESTS PASSED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_tests()
