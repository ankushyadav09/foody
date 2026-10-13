# FOODIE HUNTER: Complete Relational Data Dictionary

**System Name:** FOODIE HUNTER – Online Food Delivery & Restaurant Management System  
**Engine:** MySQL InnoDB / XAMPP Compatible  
**Database Name:** `foody_hunters`  
**Character Set:** `utf8mb4`  
**Collation:** `utf8mb4_unicode_ci`  
**Standard:** Final Semester Major Project Academic Specification

---

## 1. Table: `users`
Primary identity and authorization catalog storing credentials and full profile information across all four system roles.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Unique user identifier |
| `name` | VARCHAR(100) | | NO | NULL | User's full legal name |
| `email` | VARCHAR(120) | UNIQUE | NO | NULL | Unique login email address |
| `phone` | VARCHAR(20) | | NO | NULL | Primary contact mobile number |
| `password_hash` | VARCHAR(255) | | NO | NULL | Salted PBKDF2/SHA256 password hash |
| `role` | ENUM('customer','restaurant','delivery','admin') | INDEX | NO | 'customer' | System authorization role |
| `gender` | ENUM('male','female','other') | | YES | NULL | Gender identity |
| `dob` | DATE | | YES | NULL | Date of birth for customer |
| `address` | TEXT | | YES | NULL | Primary/default postal address |
| `city` | VARCHAR(60) | | YES | 'Mehsana' | Registered residence city |
| `state` | VARCHAR(60) | | YES | 'Gujarat' | Registered residence state |
| `pincode` | VARCHAR(10) | | YES | '384001' | Postal area code |
| `profile_pic` | VARCHAR(255) | | YES | NULL | Relative path/URL to uploaded avatar |
| `status` | ENUM('active','inactive','suspended') | | YES | 'active' | User account state |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Registration timestamp |
| `updated_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Last record modification timestamp |

---

## 2. Table: `addresses`
Saved delivery locations for customers, complete with GPS coordinates for accurate route mapping and delivery estimation.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Unique address identifier |
| `user_id` | INT | FK -> users(id) | NO | NULL | Owning customer ID |
| `label` | VARCHAR(50) | | YES | 'Home' | Address tag (Home, Work, Other) |
| `address` | TEXT | | NO | NULL | Full street address and flat/house number |
| `area` | VARCHAR(100) | | YES | 'Radhanpur Road' | Locality / Sector name in Mehsana |
| `city` | VARCHAR(60) | | YES | 'Mehsana' | City name |
| `state` | VARCHAR(60) | | YES | 'Gujarat' | State name |
| `pincode` | VARCHAR(10) | | YES | '384002' | Postal code |
| `latitude` | DECIMAL(10,7) | | YES | 23.5880000 | Destination latitude coordinate |
| `longitude` | DECIMAL(10,7) | | YES | 72.3693000 | Destination longitude coordinate |
| `is_default` | TINYINT(1) | | YES | 0 | Default delivery address flag |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Record creation timestamp |

---

## 3. Table: `restaurants`
Food outlets located in Mehsana with operating hours, cuisines, operational status, and geographical coordinates.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Unique restaurant identifier |
| `owner_id` | INT | FK -> users(id) | YES | NULL | Associated restaurant owner user account |
| `name` | VARCHAR(150) | | NO | NULL | Trade name of the restaurant |
| `description` | TEXT | | YES | NULL | Marketing overview and specialities |
| `cuisine` | VARCHAR(150) | | NO | NULL | Comma-separated cuisines offered |
| `address` | TEXT | | NO | NULL | Physical address in Mehsana |
| `area` | VARCHAR(100) | INDEX | YES | 'Mehsana City' | Neighborhood / landmark area |
| `city` | VARCHAR(60) | | YES | 'Mehsana' | City |
| `state` | VARCHAR(60) | | YES | 'Gujarat' | State |
| `pincode` | VARCHAR(10) | | YES | '384002' | Postal code |
| `phone` | VARCHAR(20) | | YES | NULL | Business telephone number |
| `email` | VARCHAR(120) | | YES | NULL | Business contact email |
| `rating` | DECIMAL(3,2) | INDEX | YES | 4.50 | Aggregate customer rating (1.00 - 5.00) |
| `total_ratings` | INT | | YES | 0 | Total reviews contributing to rating |
| `delivery_time` | VARCHAR(30) | | YES | '25-35 min' | Typical delivery duration label |
| `delivery_fee` | DECIMAL(8,2) | | YES | 40.00 | Base delivery charge (₹) |
| `min_order` | DECIMAL(8,2) | | YES | 100.00 | Minimum order threshold (₹) |
| `open_time` | VARCHAR(10) | | YES | '09:00' | Daily opening time (HH:MM) |
| `close_time` | VARCHAR(10) | | YES | '23:00' | Daily closing time (HH:MM) |
| `image` | VARCHAR(255) | | YES | NULL | Showcase banner/storefront image |
| `latitude` | DECIMAL(10,7) | | YES | 23.5880000 | Restaurant physical latitude |
| `longitude` | DECIMAL(10,7) | | YES | 72.3693000 | Restaurant physical longitude |
| `verification_status` | ENUM('pending','approved','rejected','suspended') | | YES | 'approved' | Admin verification state |
| `status` | ENUM('active','inactive') | | YES | 'active' | Operational listing status |
| `is_open` | TINYINT(1) | | YES | 1 | Real-time open/closed switch |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Onboarding timestamp |
| `updated_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Last profile edit timestamp |

---

## 4. Table: `food_categories`
Classification taxonomy for food items.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Unique category identifier |
| `name` | VARCHAR(60) | UNIQUE | NO | NULL | Category name (e.g., Gujarati, Pizza, Kathiyawadi) |
| `icon` | VARCHAR(50) | | YES | '🍽️' | Display emoji or icon code |
| `image` | VARCHAR(255) | | YES | NULL | Category representative image |
| `description` | TEXT | | YES | NULL | Category description |
| `is_active` | TINYINT(1) | | YES | 1 | Category availability flag |
| `sort_order` | INT | | YES | 0 | Display sequence priority |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Creation timestamp |

---

## 5. Table: `restaurant_categories`
Associative junction linking restaurants with their culinary categories.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Junction entry ID |
| `restaurant_id` | INT | FK -> restaurants(id) | NO | NULL | Associated restaurant ID |
| `category_id` | INT | FK -> food_categories(id) | NO | NULL | Associated category ID |

---

## 6. Table: `food_items`
Dishes catalog sold by restaurants with pricing, diet categorization, and availability.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Unique food item identifier |
| `restaurant_id` | INT | FK -> restaurants(id) | NO | NULL | Outlets offering this dish |
| `category_id` | INT | FK -> food_categories(id) | NO | NULL | Item categorization |
| `name` | VARCHAR(150) | | NO | NULL | Dish name |
| `description` | TEXT | | YES | NULL | Ingredient details and culinary summary |
| `price` | DECIMAL(8,2) | | NO | NULL | Base retail price (₹) |
| `discount` | DECIMAL(8,2) | | YES | 0.00 | Promotional discount percentage/amount |
| `final_price` | DECIMAL(8,2) | | NO | NULL | Final calculated price (₹) |
| `image` | VARCHAR(255) | | YES | NULL | Dish photograph path |
| `veg_type` | ENUM('veg','non_veg') | | YES | 'veg' | Vegetarian certification flag |
| `preparation_time` | INT | | YES | 20 | Typical prep time in minutes |
| `availability` | TINYINT(1) | | YES | 1 | In-stock (1) or sold-out (0) |
| `is_bestseller` | TINYINT(1) | | YES | 0 | Bestseller highlighted badge |
| `rating` | DECIMAL(3,2) | | YES | 4.50 | Item rating score |
| `total_ratings` | INT | | YES | 0 | Count of customer reviews |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Catalog entry timestamp |
| `updated_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Last modification timestamp |

---

## 7. Table: `cart` & `cart_items`
Active shopping cart sessions and associated line items for customers.

### `cart`
| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Cart session ID |
| `user_id` | INT | FK -> users(id) | NO | NULL | Owning customer ID |
| `status` | ENUM('active','completed','abandoned') | | YES | 'active' | Current cart state |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Cart initialization timestamp |
| `updated_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Cart activity timestamp |

### `cart_items`
| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Cart item entry ID |
| `cart_id` | INT | FK -> cart(id) | NO | NULL | Parent cart session ID |
| `food_item_id` | INT | FK -> food_items(id) | NO | NULL | Chosen food dish ID |
| `quantity` | INT | | NO | 1 | Quantity ordered |
| `price` | DECIMAL(8,2) | | NO | NULL | Unit price at time of cart addition (₹) |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Addition timestamp |

---

## 8. Table: `coupons`
Discount promo vouchers.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Unique coupon ID |
| `code` | VARCHAR(50) | UNIQUE | NO | NULL | Promo coupon code (e.g., WELCOME50) |
| `description` | VARCHAR(255) | | YES | NULL | Offer description |
| `discount_type` | ENUM('percentage','fixed') | | YES | 'percentage' | Calculation formula |
| `discount_value` | DECIMAL(8,2) | | NO | NULL | Value (percentage or ₹) |
| `max_discount` | DECIMAL(8,2) | | YES | NULL | Maximum cap for percentage discounts |
| `min_order_amount` | DECIMAL(8,2) | | YES | 0.00 | Minimum cart qualification total (₹) |
| `expiry_date` | DATE | | YES | NULL | Expiration validity date |
| `usage_limit` | INT | | YES | 1000 | Global usage threshold |
| `times_used` | INT | | YES | 0 | Redemptions count |
| `is_active` | TINYINT(1) | | YES | 1 | Enable/disable flag |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Creation timestamp |

---

## 9. Table: `orders`
Master orders placed with complete status lifecycle and financial totals.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Internal primary key |
| `order_code` | VARCHAR(50) | UNIQUE | NO | NULL | Friendly unique order reference (e.g., FH-2026-000001) |
| `user_id` | INT | FK -> users(id) | NO | NULL | Placing customer ID |
| `restaurant_id` | INT | FK -> restaurants(id) | NO | NULL | Outlet preparing order |
| `address_id` | INT | FK -> addresses(id) | YES | NULL | Selected delivery address ID |
| `delivery_address` | TEXT | | NO | NULL | Full frozen snapshot of delivery address |
| `customer_lat` | DECIMAL(10,7) | | YES | 23.5880000 | Destination latitude coordinate |
| `customer_lng` | DECIMAL(10,7) | | YES | 72.3693000 | Destination longitude coordinate |
| `total_amount` | DECIMAL(10,2) | | NO | NULL | Final total payable (₹) |
| `delivery_fee` | DECIMAL(8,2) | | YES | 40.00 | Delivery charge (₹) |
| `discount` | DECIMAL(8,2) | | YES | 0.00 | Applied coupon discount (₹) |
| `tax` | DECIMAL(8,2) | | YES | 0.00 | GST/government levy (₹) |
| `payment_method` | VARCHAR(50) | | YES | 'cod' | Payment channel ('cod', 'upi_demo', 'card_demo') |
| `payment_status` | ENUM('pending','paid','failed','refunded') | | YES | 'pending' | Financial settlement status |
| `order_status` | ENUM('placed','confirmed','preparing','ready_for_pickup','assigned','picked_up','out_for_delivery','delivered','cancelled','rejected') | INDEX | YES | 'placed' | Current lifecycle progression |
| `coupon_id` | INT | FK -> coupons(id) | YES | NULL | Applied coupon ID |
| `notes` | TEXT | | YES | NULL | Special kitchen or delivery instructions |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Placement timestamp |
| `updated_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Status update timestamp |

---

## 10. Table: `order_items`
Itemized line-item snapshot of dishes inside each order.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Line item ID |
| `order_id` | INT | FK -> orders(id) | NO | NULL | Parent order reference |
| `food_item_id` | INT | FK -> food_items(id) | NO | NULL | Ordered food item reference |
| `item_name` | VARCHAR(150) | | NO | NULL | Frozen food name snapshot |
| `quantity` | INT | | NO | 1 | Ordered count |
| `price` | DECIMAL(8,2) | | NO | NULL | Unit price at time of order (₹) |
| `subtotal` | DECIMAL(10,2) | | NO | NULL | `quantity * price` (₹) |

---

## 11. Table: `payments`
Academic demo payment transaction logs.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Internal transaction record ID |
| `order_id` | INT | FK -> orders(id) | NO | NULL | Associated order |
| `transaction_id` | VARCHAR(100) | UNIQUE | NO | NULL | Unique transaction ID (e.g. TXN-2026-XXXX) |
| `payment_method` | VARCHAR(50) | | NO | NULL | Payment gateway simulator name |
| `amount` | DECIMAL(10,2) | | NO | NULL | Transacted monetary sum (₹) |
| `payment_status` | ENUM('pending','paid','failed','refunded') | | YES | 'paid' | Final payment state |
| `payment_date` | DATETIME | | YES | CURRENT_TIMESTAMP | Execution timestamp |

---

## 12. Table: `delivery_partners`
Rider profiles, vehicle documentation, online/offline availability, and live coordinates.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Courier partner profile ID |
| `user_id` | INT | FK -> users(id) | NO | NULL | Linked courier user account |
| `vehicle_type` | VARCHAR(50) | | YES | 'Motorcycle' | Mode of transport (Bike, Scooter, EV) |
| `vehicle_number` | VARCHAR(50) | | YES | 'GJ-02-AB-1234' | Vehicle registration number |
| `license_number` | VARCHAR(50) | | YES | 'DL-GJ02-2022-00123' | Driver license number |
| `is_available` | TINYINT(1) | | YES | 1 | Assignment eligibility |
| `is_online` | TINYINT(1) | | YES | 1 | Active shift toggle (Online/Offline) |
| `current_lat` | DECIMAL(10,7) | | YES | 23.5880000 | Current cached latitude |
| `current_lng` | DECIMAL(10,7) | | YES | 72.3693000 | Current cached longitude |
| `total_deliveries` | INT | | YES | 0 | Lifetime delivered orders |
| `total_earnings` | DECIMAL(10,2) | | YES | 0.00 | Total earnings in Rupees (₹) |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Registration date |
| `updated_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Last location sync timestamp |

---

## 13. Table: `delivery_assignments`
Dispatches pairing ready orders with delivery partners.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Assignment dispatch ID |
| `order_id` | INT | FK -> orders(id) | NO | NULL | Associated order |
| `partner_id` | INT | FK -> users(id) | NO | NULL | Assigned rider user ID |
| `status` | ENUM('assigned','picked_up','out_for_delivery','delivered','cancelled') | | YES | 'assigned' | Dispatch lifecycle status |
| `assigned_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Assignment timestamp |
| `picked_at` | DATETIME | | YES | NULL | Restaurant pickup timestamp |
| `delivered_at` | DATETIME | | YES | NULL | Final customer handover timestamp |

---

## 14. Table: `delivery_locations`
Breadcrumb telemetry logging live GPS coordinates during transit.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Breadcrumb tracking entry ID |
| `delivery_partner_id` | INT | FK -> users(id) | NO | NULL | Reporting delivery partner |
| `order_id` | INT | FK -> orders(id) | NO | NULL | Active delivery order |
| `latitude` | DECIMAL(10,7) | | NO | NULL | Reported latitude |
| `longitude` | DECIMAL(10,7) | | NO | NULL | Reported longitude |
| `recorded_at` | DATETIME | INDEX | YES | CURRENT_TIMESTAMP | Telemetry capture timestamp |

---

## 15. Table: `reviews`
Customer reviews and star ratings for delivered orders.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Review entry ID |
| `user_id` | INT | FK -> users(id) | NO | NULL | Reviewing customer |
| `restaurant_id` | INT | FK -> restaurants(id) | NO | NULL | Evaluated restaurant |
| `order_id` | INT | FK -> orders(id) | YES | NULL | Verified completed order |
| `rating` | INT | | NO | NULL | Star rating (1 to 5) |
| `comment` | TEXT | | YES | NULL | Review remarks and feedback |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Review submission timestamp |

---

## 16. Table: `favorites`
Customer saved bookmarks for restaurants and favorite foods.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Favorite record ID |
| `user_id` | INT | FK -> users(id) | NO | NULL | Owning customer ID |
| `item_type` | ENUM('restaurant','food') | | NO | NULL | Entity type bookmarked |
| `item_id` | INT | | NO | NULL | Foreign ID of restaurant or food item |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Bookmark creation timestamp |

---

## 17. Table: `notifications`
System alerts and order status push notices.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Notification ID |
| `user_id` | INT | FK -> users(id) | NO | NULL | Target recipient user ID |
| `role` | ENUM('customer','restaurant','delivery','admin') | | YES | 'customer' | Role recipient context |
| `title` | VARCHAR(150) | | NO | NULL | Notification heading |
| `message` | TEXT | | NO | NULL | Notification detailed message |
| `link` | VARCHAR(255) | | YES | NULL | Destination action URL |
| `is_read` | TINYINT(1) | INDEX | YES | 0 | Read receipt status (0 = Unread, 1 = Read) |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Dispatch timestamp |

---

## 18. Table: `complaints`
Customer grievance ticketing and contact messages.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Complaint record ID |
| `user_id` | INT | FK -> users(id) | YES | NULL | Submitting user ID (optional) |
| `name` | VARCHAR(100) | | YES | NULL | Submitter name |
| `email` | VARCHAR(100) | | YES | NULL | Submitter email |
| `order_id` | INT | FK -> orders(id) | YES | NULL | Associated order reference |
| `subject` | VARCHAR(150) | | YES | NULL | Subject topic |
| `message` | TEXT | | YES | NULL | Description of problem |
| `status` | ENUM('open','in_progress','resolved') | | YES | 'open' | Resolution progress state |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Ticket opened timestamp |

---

## 19. Table: `admin_logs`
Security audit trail recording administrative actions.

| Field | Data Type | Key | Null | Default | Description |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | PK | NO | NULL | Audit log ID |
| `admin_id` | INT | FK -> users(id) | YES | NULL | Operating admin user ID |
| `action` | VARCHAR(100) | | NO | NULL | Action code/descriptor |
| `details` | TEXT | | YES | NULL | Payload / parameter change details |
| `created_at` | DATETIME | | YES | CURRENT_TIMESTAMP | Audit timestamp |
