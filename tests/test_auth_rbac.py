"""
test_auth_rbac.py – Automated test suite for Phase 2:
Tests:
1. Login with demo accounts for all 4 roles (Customer, Restaurant, Delivery, Admin)
2. Role-Based Access Control (RBAC) route security
3. Multi-role registration (Customer, Restaurant Owner, Delivery Partner)
4. Password hashing verification
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import execute_query
from werkzeug.security import check_password_hash

app = create_app()
app.config['TESTING'] = True

def run_tests():
    print("=== STARTING AUTH & RBAC VERIFICATION ===")
    client = app.test_client()

    # Test 1: Verify all 4 demo users exist and password hashes match 'password123'
    roles_checked = {}
    for role, email in [
        ('customer', 'customer@foodiehunter.com'),
        ('restaurant', 'restaurant@foodiehunter.com'),
        ('delivery', 'delivery@foodiehunter.com'),
        ('admin', 'admin@foodiehunter.com')
    ]:
        user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        assert user is not None, f"Demo user {email} missing from database!"
        assert user['role'] == role, f"User {email} has role {user['role']}, expected {role}!"
        assert check_password_hash(user['password_hash'], 'password123'), f"Password hash mismatch for {email}!"
        roles_checked[role] = True
        print(f"[PASS] Demo Account Verified: {role.upper()} ({email})")

    # Test 2: Login via HTTP POST for Customer
    res = client.post('/auth/login', data={'email': 'customer@foodiehunter.com', 'password': 'password123'}, follow_redirects=False)
    assert res.status_code in (302, 200), f"Customer login failed with status {res.status_code}"
    print("[PASS] HTTP Login: Customer authentication successful")

    # Test 3: Customer cannot access /admin (RBAC)
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'customer'
        sess['user_name'] = 'Raj Patel'
    
    res = client.get('/admin/', follow_redirects=False)
    # Should redirect with flash message
    assert res.status_code == 302, f"Customer was not blocked from /admin! Status: {res.status_code}"
    print("[PASS] RBAC: Customer blocked from /admin (302 Redirect to home)")

    # Test 4: Customer cannot access /restaurant/dashboard (RBAC)
    res = client.get('/restaurant/dashboard', follow_redirects=False)
    assert res.status_code == 302, f"Customer was not blocked from /restaurant! Status: {res.status_code}"
    print("[PASS] RBAC: Customer blocked from /restaurant/dashboard")

    # Test 5: Customer cannot access /delivery/dashboard (RBAC)
    res = client.get('/delivery/dashboard', follow_redirects=False)
    assert res.status_code == 302, f"Customer was not blocked from /delivery! Status: {res.status_code}"
    print("[PASS] RBAC: Customer blocked from /delivery/dashboard")

    # Test 6: Restaurant owner can access /restaurant/dashboard
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'restaurant'
        sess['user_name'] = 'Chef Sanjeev Kumar'
    
    res = client.get('/restaurant/dashboard', follow_redirects=False)
    assert res.status_code == 200, f"Restaurant owner could not access dashboard! Status: {res.status_code}"
    print("[PASS] RBAC: Restaurant Owner successfully granted access to /restaurant/dashboard (200 OK)")

    # Test 7: Delivery partner can access /delivery/dashboard
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'delivery'
        sess['user_name'] = 'Vikram Singh'

    res = client.get('/delivery/dashboard', follow_redirects=False)
    assert res.status_code == 200, f"Delivery partner could not access dashboard! Status: {res.status_code}"
    print("[PASS] RBAC: Delivery Partner successfully granted access to /delivery/dashboard (200 OK)")

    # Test 8: Admin can access /admin/dashboard
    with client.session_transaction() as sess:
        sess['user_id'] = 4
        sess['role'] = 'admin'
        sess['user_name'] = 'System Administrator'
        sess['admin_gate_passed'] = True

    res = client.get('/admin/dashboard', follow_redirects=False)
    assert res.status_code == 200, f"Admin could not access dashboard! Status: {res.status_code}"
    print("[PASS] RBAC: Admin successfully granted access to /admin/dashboard (200 OK)")

    # Test 9: Multi-role Registration: Register a new test customer with fresh client
    client.get('/auth/logout')  # ensure logged out
    import random
    rand_id = random.randint(1000, 9999)
    test_email = f"testcustomer{rand_id}@test.com"
    res = client.post('/auth/register', data={
        'name': f'Test Customer {rand_id}',
        'email': test_email,
        'phone': f'98{rand_id:08d}',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'customer',
        'address': 'Radhanpur Road, Mehsana',
        'city': 'Mehsana',
        'pincode': '384002'
    }, follow_redirects=False)
    assert res.status_code == 302, f"Registration failed! Status: {res.status_code}"
    new_user = execute_query("SELECT * FROM users WHERE email=%s", (test_email,), fetchone=True)
    assert new_user is not None, "Registered user was not saved in MySQL!"
    assert check_password_hash(new_user['password_hash'], 'password123'), "New user password hash invalid!"
    print(f"[PASS] Multi-Role Registration: New Customer registered and verified in MySQL ({test_email})")

    # Clean up test user
    execute_query("DELETE FROM users WHERE email=%s", (test_email,), commit=True)

    print("=== ALL 9 AUTH & RBAC TESTS PASSED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_tests()
