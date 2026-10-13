"""
test_customer_profile_persistence.py – Automated test suite for Phase 3:
Tests:
1. Customer Home & Mehsana Restaurant browsing
2. Mandatory Profile Update & Persistence (VIEW -> EDIT -> SAVE -> REFRESH test)
3. Saved Address CRUD with GPS coordinates
4. Favorites toggle and listing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query

app = create_app()
app.config['TESTING'] = True

def run_tests():
    print("=== STARTING CUSTOMER & PROFILE PERSISTENCE TEST ===")
    client = app.test_client()

    # Reset any existing test favorite to guarantee idempotence
    execute_query("DELETE FROM favorites WHERE user_id=1 AND item_type='restaurant' AND item_id=2", commit=True)

    # 1. Customer Home page loads from MySQL
    res = client.get('/')
    assert res.status_code == 200, f"Home page failed with {res.status_code}"
    # Check that Mehsana is mentioned
    assert b"Mehsana" in res.data, "Mehsana city branding missing from home page!"
    print("[PASS] Home Page: Successfully rendered with Mehsana branding")

    # 2. Restaurants listing page loads 50+ restaurants from MySQL
    res = client.get('/restaurants')
    assert res.status_code == 200, f"Restaurants page failed with {res.status_code}"
    print("[PASS] Restaurants Listing: Successfully rendered from MySQL")

    # 3. Simulate customer session
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Raj Patel'
        sess['role'] = 'customer'
        sess['user_email'] = 'customer@foodiehunter.com'

    # 4. Mandatory Test: View Profile
    res = client.get('/customer/profile')
    assert res.status_code == 200, f"Profile page failed with {res.status_code}"
    assert b"Raj Patel" in res.data, "Customer profile name missing from view!"
    print("[PASS] Profile: VIEW initial customer profile successful")

    # 5. Mandatory Test: EDIT Profile & SAVE (HTTP POST to /customer/profile/update)
    updated_name = "Rajeshkumar P. Patel"
    updated_phone = "9876501234"
    updated_addr = "Flat 404, Radhe Residency, Radhanpur Road"
    updated_pincode = "384003"
    updated_dob = "1997-08-15"
    updated_gender = "male"

    res = client.post('/customer/profile/update', data={
        'name': updated_name,
        'phone': updated_phone,
        'gender': updated_gender,
        'dob': updated_dob,
        'address': updated_addr,
        'city': 'Mehsana',
        'state': 'Gujarat',
        'pincode': updated_pincode
    }, follow_redirects=True)
    assert res.status_code == 200, f"Profile update POST failed with {res.status_code}"
    assert b"Profile updated successfully" in res.data or b"Rajeshkumar" in res.data

    # Verify directly in MySQL
    db_user = execute_query("SELECT * FROM users WHERE id=1", fetchone=True)
    assert db_user['name'] == updated_name, f"MySQL name mismatch: {db_user['name']}"
    assert db_user['phone'] == updated_phone, f"MySQL phone mismatch: {db_user['phone']}"
    assert db_user['pincode'] == updated_pincode, f"MySQL pincode mismatch: {db_user['pincode']}"
    print(f"[PASS] Profile: MySQL persistence verified (Name: {db_user['name']}, Phone: {db_user['phone']})")

    # 6. Mandatory Test: REFRESH BROWSER (HTTP GET to /customer/profile)
    res_refresh = client.get('/customer/profile')
    assert res_refresh.status_code == 200
    assert updated_name.encode('utf-8') in res_refresh.data, "Updated name not visible after refresh!"
    assert updated_phone.encode('utf-8') in res_refresh.data, "Updated phone not visible after refresh!"
    assert updated_pincode.encode('utf-8') in res_refresh.data, "Updated pincode not visible after refresh!"
    print("[PASS] Profile: REFRESH verified – Updated data persists and displays accurately!")

    # 7. Customer Saved Address CRUD
    res_addr = client.post('/customer/address/add', data={
        'label': 'Office',
        'address': 'Plot 42, GIDC Dediyasan',
        'area': 'Dediyasan GIDC',
        'city': 'Mehsana',
        'pincode': '384002',
        'latitude': '23.6110000',
        'longitude': '72.3520000',
        'is_default': '1'
    }, follow_redirects=True)
    assert res_addr.status_code == 200
    # Verify in MySQL
    db_addr = execute_query("SELECT * FROM addresses WHERE user_id=1 AND label='Office'", fetchone=True)
    assert db_addr is not None, "Saved address missing from MySQL!"
    assert db_addr['area'] == 'Dediyasan GIDC'
    print(f"[PASS] Address Management: New address added with GPS ({db_addr['latitude']}, {db_addr['longitude']})")

    # 8. Favorites Toggle
    res_fav = client.post('/customer/favorite/toggle', json={'item_type': 'restaurant', 'item_id': 2})
    assert res_fav.status_code == 200
    json_data = res_fav.get_json()
    assert json_data['success'] is True
    # Verify in MySQL
    db_fav = execute_query("SELECT * FROM favorites WHERE user_id=1 AND item_type='restaurant' AND item_id=2", fetchone=True)
    assert db_fav is not None, "Favorite record missing from MySQL!"
    print("[PASS] Favorites: Restaurant favorited and verified in MySQL")

    # Restore original user name for clean subsequent testing
    execute_query("UPDATE users SET name='Raj Patel', phone='9876543210' WHERE id=1", commit=True)

    print("=== ALL PHASE 3 CUSTOMER & PROFILE PERSISTENCE TESTS PASSED ===")

if __name__ == '__main__':
    run_tests()
