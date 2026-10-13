# System Testing Documentation & Test Cases – FOODY HUNTERS

This document contains black-box and integration test matrices conducted across the **Foody Hunters** platform for project verification.

---

## 1. Authentication & Security Testing

| Test Case ID | Test Scenario | Test Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| **TC-AUTH-01** | Valid Customer Registration | Name: "Rohan Patel", Email: "rohan@gmail.com", Phone: "9876543210", Pass: "pass123", Confirm: "pass123" | Account created, redirected to login with success flash | Redirected to login with success message | **PASSED** |
| **TC-AUTH-02** | Registration with Duplicate Email | Existing email `customer@foodyhunters.com` | Registration rejected; flash "Email already registered" | Flash message displayed; DB uncorrupted | **PASSED** |
| **TC-AUTH-03** | Mismatched Password Confirmation | Pass: "hello123", Confirm: "world123" | Form rejected with error message | Displayed "Passwords do not match" | **PASSED** |
| **TC-AUTH-04** | Valid Customer Login | `customer@foodyhunters.com` / `password123` | Session initialized, redirected to Home (`/`) | Logged in, customer navbar rendered | **PASSED** |
| **TC-AUTH-05** | Role-Based Redirection (Admin) | `admin@foodyhunters.com` / `password123` | Redirected to `/admin/dashboard` | Redirected to Admin Dashboard | **PASSED** |
| **TC-AUTH-06** | Role-Based Redirection (Restaurant) | `restaurant@foodyhunters.com` / `password123` | Redirected to `/restaurant/dashboard` | Redirected to Restaurant Dashboard | **PASSED** |
| **TC-AUTH-07** | Role-Based Redirection (Delivery) | `delivery@foodyhunters.com` / `password123` | Redirected to `/delivery/dashboard` | Redirected to Delivery Dashboard | **PASSED** |
| **TC-AUTH-08** | Unauthorized Admin Route Access | Unauthenticated GET `/admin/dashboard` | Redirected to `/auth/login` with warning | Redirected to login; protected | **PASSED** |

---

## 2. Food Browsing, Search & Filter Testing

| Test Case ID | Test Scenario | Test Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| **TC-SRCH-01** | Search by Food Name | Search keyword "Pizza" | Lists Pizza Palace and pizza menu dishes | Pizza Palace and pizzas displayed | **PASSED** |
| **TC-SRCH-02** | Search by Cuisine | Search keyword "Gujarati" | Lists Royal Gujarati restaurant & Thali | Royal Gujarati and dishes displayed | **PASSED** |
| **TC-FILT-01** | Pure Vegetarian Filter | Check `Veg Only` on `/restaurants` | Displays only vegetarian dining establishments | Only pure-veg restaurants displayed | **PASSED** |
| **TC-SORT-01** | Sort by Rating | Select "Rating: High to Low" | Highest rated restaurants appear first | Correct descending rating order | **PASSED** |

---

## 3. Shopping Cart & Discount Coupons Testing

| Test Case ID | Test Scenario | Test Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| **TC-CART-01** | Add Dish to Cart | Click "ADD" on Margherita Pizza (₹249) | Item added; cart badge count increments to 1 | Item added; toast notification shown | **PASSED** |
| **TC-CART-02** | Increment Quantity | Click `+` on Margherita Pizza in Cart | Quantity becomes 2; Subtotal becomes ₹498 | Subtotal recalculated to ₹498 | **PASSED** |
| **TC-CART-03** | Remove Item from Cart | Click Remove / Trash icon | Item deleted; grand total dynamically updated | Item removed; total recalculated | **PASSED** |
| **TC-CPN-01** | Valid Percentage Coupon | Code `WELCOME50` on order > ₹199 | Applies 50% discount up to ₹150 cap | Discount subtracted from grand total | **PASSED** |
| **TC-CPN-02** | Invalid Coupon Code | Code `FAKE999` | Displays error "Invalid or expired coupon" | Error displayed; no discount given | **PASSED** |
| **TC-CPN-03** | Minimum Spend Unmet | Code `HUNTER10` (Min ₹299) on ₹150 cart | Displays error indicating minimum order criteria | Flash message displayed correctly | **PASSED** |

---

## 4. Checkout, Payment & Order Lifecycle Testing

| Test Case ID | Test Scenario | Test Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| **TC-ORD-01** | Cash on Delivery (COD) | Delivery Address filled + Select COD | Order created, status `pending`, redirected to voucher | Order placed successfully | **PASSED** |
| **TC-PAY-01** | Demo UPI Payment | Select UPI + enter `rohan@okhdfcbank` | Realistic processing animation -> Success | Order created with `payment_status='completed'` | **PASSED** |
| **TC-PAY-02** | Demo Card Payment | 16-digit card, expiry, 3-digit CVV | Mock transaction ID generated; order placed | Order created with `TXN_...` ID | **PASSED** |
| **TC-TRK-01** | Live Order Tracking Page | Navigate to `/customer/order/track/<order_id>` | Progress timeline matches current order status | Visual timeline highlighted correctly | **PASSED** |

---

## 5. Restaurant, Delivery & Admin Role Operations

| Test Case ID | Test Scenario | Test Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| **TC-REST-01** | Add Food Item to Menu | Dish name, ₹220, category, veg | Dish saved and appears on restaurant menu | New item visible in restaurant catalog | **PASSED** |
| **TC-REST-02** | Update Order Status | Change order status to "Preparing" | Order updated; visible to customer tracking | Status updated in DB and UI | **PASSED** |
| **TC-DELV-01** | Mark Order Delivered | Delivery partner clicks "Mark Delivered" | Order status becomes `delivered`; customer notified | Status updated; delivery logged | **PASSED** |
| **TC-ADMN-01** | Restaurant Status Toggle | Admin toggles restaurant to "inactive" | Restaurant hidden from public browse | Restaurant unlisted from public page | **PASSED** |
| **TC-REVW-01** | Submit Customer Review | 5 Stars + "Amazing hot pizza!" | Review added to DB; restaurant rating updated | Review visible on restaurant page | **PASSED** |

---

## 6. Testing Summary & Conclusion
- **Total Test Cases Executed:** 22
- **Passed:** 22
- **Failed:** 0
- **Pass Rate:** 100%
- **Conclusion:** The Foody Hunters application functions reliably across all core user flows, database constraints, authentication barriers, and multi-role operations.
