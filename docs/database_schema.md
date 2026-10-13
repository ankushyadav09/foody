# Database Schema & Entity-Relationship Details – FOODY HUNTERS

## 1. Database Identification
- **Database Name:** `foody_hunters`
- **Engine:** InnoDB
- **Default Charset:** `utf8mb4`
- **Collation:** `utf8mb4_general_ci`

---

## 2. Entity-Relationship (ER) Overview

```
                      +------------------+
                      |      USERS       |
                      +------------------+
                        |1            |1
                        |             |
           +------------+             +------------+
           |                                       |
           |1 (owner)                              |1 (rider)
           v                                       v
    +-------------+                       +-------------------+
    | RESTAURANTS |                       | DELIVERY_PARTNERS |
    +-------------+                       +-------------------+
       |1        |1                                 |1
       |         |                                  |
       |         +------------+                     |
       v                      v                     v
+------------+          +------------+    +----------------------+
| FOOD_ITEMS |          |   ORDERS   |<---| DELIVERY_ASSIGNMENTS |
+------------+          +------------+    +----------------------+
       ^                      |1
       |                      |
       |               +------+------+
       |               |             |
       |               v             v
       |        +-------------+ +----------+
       +--------| ORDER_ITEMS | | PAYMENTS |
                +-------------+ +----------+
```

---

## 3. Relational Table Specifications

### 1. `users` Table
Stores authentication details and profiles for all user roles.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique User Identifier |
| `name` | VARCHAR(100) | NOT NULL | User's full name |
| `email` | VARCHAR(120) | UNIQUE, NOT NULL | Unique email address used for login |
| `phone` | VARCHAR(20) | NOT NULL | 10-digit mobile phone number |
| `password_hash`| VARCHAR(255) | NOT NULL | Salted PBKDF2:SHA256 password hash |
| `role` | ENUM | 'customer', 'restaurant', 'delivery', 'admin' | User authorization role |
| `address` | TEXT | NULL | Default delivery address |
| `profile_pic` | VARCHAR(255) | NULL | Filepath/URL to user avatar |
| `status` | ENUM | 'active', 'inactive', 'suspended' | Account status flag |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration timestamp |

---

### 2. `restaurants` Table
Stores details and operational parameters for registered food outlets.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | Restaurant ID |
| `owner_id` | INT | FOREIGN KEY -> `users(id)` | User ID of the restaurant owner |
| `name` | VARCHAR(150) | NOT NULL | Restaurant outlet name |
| `description` | TEXT | NULL | Summary of restaurant & specialties |
| `cuisine` | VARCHAR(150) | NOT NULL | Cuisines served (e.g. Italian, North Indian) |
| `address` | TEXT | NOT NULL | Physical outlet address |
| `phone` | VARCHAR(20) | NOT NULL | Outlet contact number |
| `rating` | DECIMAL(3,2) | DEFAULT 4.00 | Average rating calculated from customer reviews |
| `delivery_time`| INT | DEFAULT 30 | Average delivery time in minutes |
| `delivery_fee` | DECIMAL(8,2) | DEFAULT 40.00 | Standard delivery charge (₹) |
| `min_order` | DECIMAL(8,2) | DEFAULT 0.00 | Minimum order threshold (₹) |
| `open_time` | VARCHAR(10) | DEFAULT '09:00' | Opening time |
| `close_time` | VARCHAR(10) | DEFAULT '23:00' | Closing time |
| `image` | VARCHAR(255) | NULL | Outlet storefront cover image |
| `status` | ENUM | 'active', 'pending', 'inactive' | Approval state from Admin |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

---

### 3. `food_categories` Table
Categorical classification of food items across the platform.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | Category ID |
| `name` | VARCHAR(100) | UNIQUE, NOT NULL | Category name (e.g. Pizza, Gujarati) |
| `description` | TEXT | NULL | Brief description |
| `image` | VARCHAR(255) | NULL | Visual icon/thumbnail |
| `status` | ENUM | 'active', 'inactive' | Active category flag |

---

### 4. `food_items` Table
Complete food dish catalog with menu details and availability.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | Food item ID |
| `restaurant_id`| INT | FOREIGN KEY -> `restaurants(id)` | Belonging restaurant outlet |
| `category_id` | INT | FOREIGN KEY -> `food_categories(id)`| Classification category |
| `name` | VARCHAR(150) | NOT NULL | Dish name |
| `description` | TEXT | NULL | Ingredients and taste description |
| `price` | DECIMAL(8,2) | NOT NULL | Selling price in Indian Rupees (₹) |
| `image` | VARCHAR(255) | NULL | Food photograph image path |
| `veg_type` | ENUM | 'veg', 'non-veg' | Pure vegetarian or non-vegetarian flag |
| `availability`| TINYINT(1) | DEFAULT 1 | In-stock (1) or Out-of-stock (0) |
| `rating` | DECIMAL(3,2) | DEFAULT 4.20 | Item rating score |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Item creation timestamp |

---

### 5. `cart` & `cart_items` Tables
Stores the active shopping cart state for customers.
- `cart`: Links `user_id` to their active cart session.
- `cart_items`: Foreign key links to `cart(id)` and `food_items(id)`, storing quantity and line subtotal.

---

### 6. `orders` & `order_items` Tables
Master historical transactions and itemized line records.
- `orders`:
  - `id`: Unique Order ID.
  - `user_id`: Customer Foreign Key.
  - `restaurant_id`: Restaurant Foreign Key.
  - `total_amount`: Final payable total after discounts and taxes.
  - `delivery_fee`, `discount`, `tax`: Pricing breakdown fields.
  - `payment_method`: 'cod', 'upi', 'card', 'netbanking'.
  - `payment_status`: 'pending', 'completed', 'failed'.
  - `order_status`: 'pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'cancelled'.
- `order_items`:
  - `order_id`: Foreign Key referencing `orders(id)`.
  - `food_item_id`: Snapshot Foreign Key.
  - `quantity`: Quantity ordered.
  - `price`: Unit price snapshot at time of checkout.
  - `subtotal`: `quantity * price`.

---

### 7. `payments` Table
Records all financial transactions and payment gateway logs.
- `transaction_id`: System-generated unique transaction tracking number (e.g. `TXN_20261006_XXXX`).
- `payment_method`, `amount`, `payment_status`, `payment_date`.

---

### 8. `coupons` Table
Promotional discounting rules and constraints.
- `code`: Promo string (e.g. `WELCOME50`, `HUNTER10`).
- `discount_type`: 'percentage' or 'flat'.
- `discount_value`: Amount or percentage value.
- `min_order`: Minimum cart subtotal required to qualify.
- `max_discount`: Cap for percentage discounts.
- `status`: Active or disabled flag.

---

### 9. `reviews`, `delivery_partners`, `delivery_assignments`, `complaints`
- `reviews`: Stores `rating` (1–5) and `comment` for delivered orders.
- `delivery_partners`: Stores vehicle registration, active status, and total earnings.
- `delivery_assignments`: Dispatches an order to a delivery partner with status progression.
- `complaints`: Customer grievance ticketing system manageable by Admin.
