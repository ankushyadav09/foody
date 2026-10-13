# System Modules Breakdown – FOODY HUNTERS

This document outlines each functional module within the **Foody Hunters** platform, suitable for presentation slides and college viva examination.

---

## Module 1: Authentication & Authorization Module (`routes/auth.py`)
- **User Registration:** Validates customer inputs (10-digit Indian phone number, valid email, password length >= 6, password confirmation matching).
- **Password Encryption:** Implements PBKDF2 with SHA-256 password hashing.
- **Role-Based Redirection:** Authenticates credentials and routes users according to their assigned role:
  - `customer` -> Public Marketplace (`/`)
  - `restaurant` -> Restaurant Owner Dashboard (`/restaurant/dashboard`)
  - `delivery` -> Delivery Rider Portal (`/delivery/dashboard`)
  - `admin` -> Super Administrator Panel (`/admin/dashboard`)
- **Session Management:** Secure cryptographic cookie storage with Flask `session`.
- **Demo Quick-Login:** 1-click credential auto-fill for frictionless college viva demonstrations.

---

## Module 2: Customer Browsing & Search Engine Module (`routes/main.py`)
- **Homepage Showcase:** Hero banner, interactive category carousels, top-rated restaurants, and promotional discount banners.
- **Multi-Parameter Search:** Real-time search across restaurant names, food titles, and cuisine keywords using SQL `LIKE %query%`.
- **Faceted Filters & Sorting:**
  - Filtering by Cuisine (Italian, Gujarati, Biryani, Chinese, Fast Food).
  - Vegetarian filter toggle (`veg_only`).
  - Sorting options: Rating (high to low), Delivery Time (fastest), Price (low-to-high, high-to-low).
- **Restaurant Details & Menu Catalog:** Displays restaurant header with rating badge, delivery fee, average timing, and categorized food items.

---

## Module 3: Dynamic Cart & Coupon Discount Engine (`routes/customer.py`)
- **Cart Session Management:** Add, increase, decrease, and delete items from cart with real-time feedback.
- **Dynamic Breakdown Calculations:**
  - Subtotal = Sum of all item subtotals.
  - Delivery Fee = Restaurant standard fee (or ₹0 if cart is empty).
  - GST / Taxes = Dynamic 5% calculation on subtotal.
  - Discount = Calculated based on applied coupon rules.
  - Grand Total = Subtotal + Delivery Fee + Tax - Discount.
- **Coupon Validation Engine:** Checks coupon code existence, minimum cart value criteria, calculates flat or percentage discounts with maximum cap limits.

---

## Module 4: Checkout & Payment Gateway Module (`routes/customer.py` & `routes/api.py`)
- **Delivery Address Handling:** Customer can select an existing address or enter a new delivery destination.
- **Multiple Payment Modes:**
  - **Cash on Delivery (COD):** Direct order confirmation without payment preprocessing.
  - **Demo UPI:** Interactive UPI VPA / QR simulation with instant mock processing.
  - **Demo Debit / Credit Card:** Cardholder, 16-digit card number, expiry, and CVV validation with realistic payment gateway animations.
- **Transaction Generation:** Automatically produces unique transaction tracking numbers (`TXN_XXXXXXXX`).

---

## Module 5: Order Lifecycle & Tracking Module (`routes/customer.py`)
- **Order Placement:** Atomic database insertion into `orders` and `order_items` tables, clearing active cart.
- **Order Confirmation Voucher:** Summarizes itemized receipt, delivery address, and payment status.
- **Visual Status Progression Timeline:**
  - `pending` (Order Placed)
  - `confirmed` (Restaurant Confirmed)
  - `preparing` (Kitchen Preparing)
  - `ready` (Ready for Pickup)
  - `out_for_delivery` (Rider On The Way)
  - `delivered` (Delivered)
- **Live GPS Simulation:** Visual canvas simulation showing delivery rider transit towards customer coordinates.

---

## Module 6: Ratings & Review System (`routes/customer.py`)
- **Verified Order Reviews:** Only customers who have received a `delivered` order can submit a rating.
- **5-Star Scoring:** Interactive star selection and written review feedback.
- **Average Rating Recalculation:** Submitting a review recalculates the restaurant's average rating in the `restaurants` table.

---

## Module 7: Restaurant Owner Management Module (`routes/restaurant.py`)
- **Owner Dashboard:** Overview cards for Total Orders, Today's Orders, Today's Revenue, and Active Dishes.
- **Store Profile Management:** Update restaurant name, description, cuisine, contact phone, delivery charges, and cover photo.
- **Food Catalog CRUD:**
  - Add new dish with price, veg/non-veg flag, and image upload.
  - Edit existing menu dish details.
  - Toggle instant availability (In-Stock / Out-of-Stock).
  - Delete items.
- **Kitchen Order Management:** Live order stream where the kitchen can accept orders, update preparation stages, or cancel orders.
- **Sales Analytics:** Daily revenue tables and top-selling food items breakdown.

---

## Module 8: Delivery Partner Portal (`routes/delivery.py`)
- **Rider Dashboard:** Displays active assigned orders, pickup addresses, customer contact numbers, and delivery locations.
- **Status Progression Controls:** Simple buttons to transition order status from `picked_up` to `out_for_delivery` to `delivered`.
- **Rider Earnings Log:** Calculation of completed deliveries and historical earnings.

---

## Module 9: Super-Administrator Control Center (`routes/admin.py`)
- **Executive Metric Counters:** Total Users, Active Restaurants, Delivery Riders, Total Platform Orders, Gross Revenue.
- **Merchant Approval Workflow:** Approve new restaurant applications or deactivate non-compliant restaurants.
- **User Role Management:** Toggle active/inactive status across all customer and partner accounts.
- **Category & Menu Catalog Oversight:** Add or edit global food categories.
- **Financial Audit & Transactions:** Review all payments and transaction IDs.
- **Marketing & Coupons Manager:** Create and retire promotional coupon codes.
- **Customer Support & Ticketing:** View customer grievance complaints and mark them resolved.
- **Visual Platform Reports:** Visual sales performance bars, order status distributions, and top revenue drivers.
