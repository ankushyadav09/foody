# 🍔 FOODIE HUNTER
## Online Food Delivery & Restaurant Management System
### Final Semester Major Project — Academic Standard (BCA / B.Tech / MCA / GTU)

[![Technology](https://img.shields.io/badge/Stack-Python%20Flask%20%7C%20MySQL%20%7C%20HTML5%20%7C%20CSS3%20%7C%20JS-orange.svg)]()
[![Platform](https://img.shields.io/badge/Platform-XAMPP%20MySQL%20%7C%20Windows%2010%2F11-blue.svg)]()
[![Maps](https://img.shields.io/badge/Maps-Google%20Maps%20API%20%2B%20Demo%20Simulation-green.svg)]()
[![Status](https://img.shields.io/badge/Status-Complete%20%26%20Verified-brightgreen.svg)]()

---

## 📌 Project Executive Summary

**FOODIE HUNTER** is a full-stack, enterprise-grade Online Food Delivery and Restaurant Management platform architected specifically for academic final-semester project demonstrations, technical vivas, and practical software engineering evaluations.

Built with an original brand identity, the system features a complete multi-role ecosystem supporting:
1. **Customer Marketplace** (Browse, Search, Filter, Saved Addresses, Cart, Coupons, Demo Payments, Live GPS Order Tracking, Reviews)
2. **Restaurant Owner Portal** (Kitchen Ticket Workflow, Menu CRUD, Pricing & Discounts, Real-Time Order Stream, Sales Analytics)
3. **Delivery Partner Hub** (Online/Offline Dispatch Toggle, Order Acceptance, Live GPS Breadcrumb Beacon, Transit Updates, Earnings)
4. **Administrator Command Center** (Platform KPIs, Restaurant Approvals, User RBAC Controls, Fleet Management, Categories, Coupons, Visual Chart.js Analytics)

The database contains **52 authentic synthetic restaurants** located throughout **Mehsana, Gujarat** (Radhanpur Road, Modhera Road, Highway, Malgodown, Nagalpur, Widya Nagar), cataloging over **156 dishes** across 19 distinct cuisines (Kathiyawadi, Gujarati Thali, Punjabi, South Indian, Pizza, Desserts, etc.).

---

## 🛠️ Technology Stack (Strict College Guidelines)

| Layer | Technologies Used | Description |
|---|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla ES6+) | Modern responsive cards, glassmorphic accents, CSS Grid/Flexbox |
| **Icons & Typography** | Font Awesome 6.4, Google Fonts (Plus Jakarta Sans) | Premium visual appeal, no placeholder images |
| **Backend Framework** | Python 3.12, Flask 2.3+ | Application factory, modular route blueprints, strict RBAC |
| **Database** | MySQL 8.x / MariaDB (XAMPP) | 20 relational InnoDB tables with foreign key cascading and indexes |
| **Maps & Routing** | Google Maps Platform (JS API + Routes) | Interactive maps, Haversine distance, dynamic ETA, and Viva Demo Mode |
| **Charts & Analytics** | Chart.js 4.x | Real-time administrative revenue and sales distribution charts |
| **Security** | Werkzeug Security (PBKDF2:SHA256) | Parameterized SQL queries, session authentication, password hashing |
| **Environment** | Windows 10/11, PowerShell, VS Code, Google Chrome | Native local development and evaluation environment |

---

## 👥 Pre-Configured Demo Credentials

All demo accounts are pre-seeded in the MySQL database with the shared academic password: **`password123`**

| Role | Demo Email | Password | Access URL | Key Functionalities |
|---|---|---|---|---|
| 👑 **Administrator** | `admin@foodiehunter.com` | `password123` | `/admin/dashboard` | Platform KPI metrics, restaurant approval, users, categories, coupons, analytics |
| 🍽️ **Restaurant Owner** | `restaurant@foodiehunter.com` | `password123` | `/restaurant/dashboard` | Kitchen orders, accept/cook/pack, menu management, sales summary |
| 🛵 **Delivery Partner** | `delivery@foodiehunter.com` | `password123` | `/delivery/dashboard` | Active orders, live GPS broadcasting, transit dispatch, earnings |
| 👤 **Customer** | `customer@foodiehunter.com` | `password123` | `/` | Food search, cart, demo payment, live GPS tracking, editable profile |

> 💡 **Quick Login Buttons:** On the Login page (`/auth/login`), one-click demo buttons are provided to instantly populate credentials for any role during viva demonstrations.

---

## 🗺️ Google Maps Platform Integration & Demo Simulation Mode

Live delivery tracking is a core architectural feature of FOODIE HUNTER.

### Features
1. **Interactive Map View:** Displays Restaurant Origin (🏪), Delivery Partner Live Location (🛵), and Customer Destination (🏠).
2. **Calculated Distance & Dynamic ETA:** Real-time Haversine distance computation (e.g. `1.8 km away` or `650 m away`) and dynamic transit arrival estimation (`Arriving in approximately 8 minutes`).
3. **Background Telemetry Polling:** Updates coordinates and marker positions every 4–5 seconds without page reload.
4. **Rider Device Geolocation:** Supports `navigator.geolocation.watchPosition()` broadcasting GPS coordinates to `POST /api/delivery/location`.
5. **DEMO TRACKING MODE (Essential for Viva Evaluation):**
   - Enables single-laptop demonstrations where walking outdoors with GPS is impractical.
   - Interactive waypoint progression simulator: allows evaluator/student to step or auto-play rider movement between Restaurant and Customer.
   - Dynamically recalculates distance, ETA, and progress bar in real-time.
6. **Graceful Keyless Fallback:**
   - If `GOOGLE_MAPS_API_KEY` is not configured, the system displays an interactive high-resolution telemetry canvas plotting Mehsana coordinates with moving markers and calculated ETA without crashing!

### Google Maps API Key Setup
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable:
   - **Maps JavaScript API**
   - **Directions API**
   - **Geocoding API**
3. Generate an API Key under **Credentials**.
4. Open `.env` in the project root and insert:
   ```ini
   GOOGLE_MAPS_API_KEY=AIzaSyYourActualGoogleMapsKeyHere
   ```
5. Restart Flask to load the new key.

---

## ⚙️ Quick Installation & Setup (PowerShell on Windows)

### Prerequisites
- **Python 3.10+** installed on Windows.
- **XAMPP** installed and running on Windows.

### Step 1: Start XAMPP MySQL
1. Launch **XAMPP Control Panel**.
2. Click **Start** next to **MySQL** (Port 3306).
3. *(Optional)* Click **Start** next to **Apache** to access phpMyAdmin.

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure your database parameters in `.env` match your XAMPP installation:
```ini
FLASK_SECRET_KEY=foodie_hunter_super_secret_jwt_key_2026
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=foody_hunters
GOOGLE_MAPS_API_KEY=
```

### Step 3: Set Up Python Virtual Environment
Open PowerShell inside the project directory:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Import Database Schema & Seed Data
You can initialize the database using either method:

#### Option A: Direct MySQL Command Line (Fastest)
```powershell
mysql -u root -e "CREATE DATABASE IF NOT EXISTS foody_hunters;"
mysql -u root foody_hunters < database/schema.sql
mysql -u root foody_hunters < database/seed.sql
```

#### Option B: phpMyAdmin Import
1. Navigate to `http://localhost/phpmyadmin` in Google Chrome.
2. Click **New** and create database `foody_hunters` with `utf8mb4_unicode_ci`.
3. Click database `foody_hunters` -> **Import** tab.
4. Import `database/schema.sql`, then import `database/seed.sql`.

### Step 5: Start Flask Application
```powershell
python app.py
```
Open Google Chrome and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Automated Testing & Verification

The project includes automated regression test suites covering all modules:

```powershell
# Run all automated test suites
python -m unittest discover tests

# Or run individual feature tests:
python -m unittest tests/test_auth_rbac.py
python -m unittest tests/test_customer_profile_persistence.py
python -m unittest tests/test_restaurant_module.py
python -m unittest tests/test_delivery_and_admin_modules.py
python -m unittest tests/test_order_and_tracking_lifecycle.py
```

### Mandatory Profile Persistence Verification
Each of the 4 roles strictly adheres to the college evaluation pattern:
1. Login -> Profile -> View Profile
2. Edit Profile fields (Name, Phone, Address, Vehicle, Operational Details)
3. Save -> Flask validates and executes parameterized MySQL update
4. Browser Refresh -> Updated values remain permanently visible in HTML from MySQL.

---

## 📂 Project Architecture

```
foody_hunters/
├── app.py                      # Application factory & Blueprint registration
├── config.py                   # Centralized configuration & environment loader
├── database.py                 # Thread-safe MySQL connection pool & query executor
├── requirements.txt            # Pinned Python package dependencies
├── .env                        # Local environment variables (not committed)
├── .env.example                # Example configuration template
├── .gitignore                  # Git exclusion rules
├── database/
│   ├── schema.sql              # 20 relational InnoDB tables schema
│   ├── seed.sql                # Complete seed data (52 restaurants, 156 dishes)
│   ├── sample_data.sql         # Backup baseline records
│   └── data_dictionary.md      # Comprehensive academic data dictionary
├── routes/
│   ├── auth.py                 # Multi-role authentication & registration
│   ├── main.py                 # Public marketplace, search, food browsing
│   ├── customer.py             # Cart, checkout, profile, addresses, favorites
│   ├── restaurant.py           # Kitchen orders, menu CRUD, restaurant profile
│   ├── delivery.py             # Rider dispatch, online toggle, rider profile
│   ├── admin.py                # Admin management, approvals, categories, reports
│   └── api.py                  # Live tracking API, GPS beacon, demo simulation
├── templates/
│   ├── base.html               # Master layout with responsive navbar & footer
│   ├── index.html              # Customer home page (50+ Mehsana restaurants)
│   ├── login.html              # Multi-role login with 1-click viva demo buttons
│   ├── register.html           # Multi-role registration (Customer, Owner, Rider)
│   ├── restaurant_detail.html  # Menu categories, dishes, and "VIEW ON MAP"
│   ├── cart.html               # Dynamic shopping cart with quantity controls
│   ├── checkout.html           # Address selection, coupons, and demo payment
│   ├── track_order.html        # Live Google Maps tracking & Demo Simulation
│   ├── customer/               # Customer favorites and notification center
│   ├── restaurant/             # Kitchen orders, menu management, sales summary
│   ├── delivery/               # Rider portal, order details, earnings history
│   └── admin/                  # Admin KPIs, users, categories, coupons, charts
├── static/
│   ├── css/                    # Custom CSS styling (style.css, index.css)
│   ├── js/                     # Client-side JavaScript helpers
│   └── uploads/                # User avatars and food images
└── tests/                      # Automated unit and integration test suites
```

---

## 🎟️ Active Demo Coupons
- **`WELCOME50`** — 50% discount up to ₹150 (Min order: ₹199)
- **`MEHSANA50`** — Flat 50% off for Mehsana residents (Min order: ₹100)
- **`HUNTER10`** — Flat ₹100 discount (Min order: ₹299)
- **`FOOD20`** — 20% discount on cart items (Min order: ₹149)

---

## 🎓 Academic Viva Demonstration Workflow

For presenting to the university project examiner:
1. **Introduction:** Show the landing page with 52 Mehsana restaurants, search bar, categories, and statistics.
2. **Profile Persistence Demonstration:** Log into Customer, Restaurant Owner, Delivery Partner, and Admin profiles -> Edit contact information -> Click Save -> Refresh browser -> Verify persistent MySQL update.
3. **End-to-End Order Flow:**
   - Customer adds dishes from *The Grand Thakar* or *Honest Restaurant* to cart.
   - Applies coupon `WELCOME50` and selects Delivery Address on Radhanpur Road.
   - Places order via Demo UPI / COD -> Unique order ID generated (`FH-2026-XXXXXX`).
4. **Kitchen Order Processing:**
   - Switch to Restaurant Owner panel -> Accept order -> Cook -> Pack dish (`ready_for_pickup`).
   - Show automated delivery assignment dispatched in MySQL.
5. **Rider Pickup & Live Tracking:**
   - Switch to Delivery Partner panel -> Confirm Food Pickup -> Order enters `out_for_delivery`.
   - Customer opens Live Tracking page -> Google Map / GPS telemetry visualizer displays Restaurant, Rider, Customer Home, Distance (`1.8 km`), and dynamic ETA.
   - Activate **Demo Simulation Mode** -> Evaluator watches rider marker move in real-time between Mehsana waypoints while Distance and ETA continuously update.
6. **Completion & Review:**
   - Rider marks order delivered -> Payout updates in delivery earnings.
   - Customer submits 5-star review -> Restaurant rating is dynamically recalculated.
7. **Admin Oversight:**
   - Open Admin Dashboard -> Review Chart.js daily revenue trends, order status breakdown, and customer logs.

---

## 📄 License & Attribution
Developed for academic final-semester project examination. All restaurant and dish data is synthetic demonstration data modeled on the geography of Mehsana, Gujarat.
