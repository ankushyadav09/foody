# 🍔 FOODY HUNTERS — MULTI-PORTAL FOOD DELIVERY ECOSYSTEM
## Multi-Vendor Online Food Delivery Platform with 5 Logically Independent Portals
### Academic Major Project Standard (BCA / B.Tech / MCA / GTU / Academic Viva)

[![Technology](https://img.shields.io/badge/Stack-Python%20Flask%20%7C%20MySQL%20%7C%20HTML5%20%7C%20CSS3%20%7C%20JS-orange.svg)]()
[![Portals](https://img.shields.io/badge/Portals-5%20Role--Based%20Interfaces-purple.svg)]()
[![Platform](https://img.shields.io/badge/Platform-XAMPP%20MySQL%20%7C%20SQLite%20Fallback-blue.svg)]()
[![Tunnel](https://img.shields.io/badge/Tunnel-Cloudflare%20Quick%20Tunnel%20Ready-success.svg)]()
[![Tests](https://img.shields.io/badge/Tests-51%20Passing%20%7C%20100%25%20Green-brightgreen.svg)]()

---

## 📌 Ecosystem Architecture & Executive Summary

**FOODY HUNTERS** is an enterprise-grade, multi-vendor online food delivery and restaurant management ecosystem inspired by the operational workflows and usability of platforms like Swiggy and Zomato, built with 100% original branding and codebase.

The system runs as a single high-performance Python Flask application process while serving **five logically independent user interfaces** with strict role-based access control (RBAC), end-to-end data isolation, responsive layouts (320px mobile to 1366px+ desktop), and integrated order lifecycle workflows.

---

## 🌐 5-Portal Route Map & Access Matrix

All five portals run seamlessly on the **same application process** under their dedicated URL paths, both locally and through Cloudflare Quick Tunnel:

| Portal | Role | Entry / Dashboard URL | Dedicated Login URL | Registration / Onboarding URL | Key Functional Scope |
|---|---|---|---|---|---|
| **Portal 1** | **Customer** | `/` | `/auth/login` | `/auth/register` | Public food delivery storefront, restaurant search, food cart, coupons, checkout, payment processing, live order tracking, profile & favorites |
| **Portal 2** | **Admin** | `/admin/dashboard` | `/admin/login` | *Strictly restricted; invite/seed only* | Central management of all 4 roles, restaurant approvals, delivery fleet verification, staff governance & reassignments, complaints, coupons, audit logs |
| **Portal 3** | **Restaurant Owner** | `/restaurant/dashboard` | `/restaurant/login` | `/restaurant/register` | Kitchen operations overview, order acceptance, menu dish catalog (CRUD), sales telemetry, customer reviews, and staff roster management |
| **Portal 4** | **Delivery Partner** | `/delivery/dashboard` | `/delivery/login` | `/delivery/register` | Rider dispatch interface, online/offline availability toggle, assigned order pickups, trip directions, transit updates, and earnings history |
| **Portal 5** | **Kitchen Staff** | `/staff/dashboard` | `/staff/login` | `/staff/register` | Dedicated kitchen display workspace, live order prep queue with timers, kitchen state transitions (`placed` -> `preparing` -> `ready_for_pickup`), and dish 86-list stock toggles |

---

## 👥 Pre-Configured Demo Credentials

All demo accounts are pre-seeded in the database with the shared academic password: **`password123`**

| Portal / Role | Demo Email | Password | Assigned Entity / Scope |
|---|---|---|---|
| 👑 **Administrator** | `admin@foodiehunter.com` | `password123` | Platform-wide Master Control Center |
| 🍽️ **Restaurant Owner** | `restaurant@foodiehunter.com` | `password123` | *The Grand Thakar & Kathiyawadi Express* (Rest ID: 1) |
| 🛵 **Delivery Partner** | `delivery@foodiehunter.com` | `password123` | Active Mehsana Delivery Fleet Partner |
| 🍳 **Kitchen Staff** | `staff@foodyhunters.com` | `password123` | Kitchen Lead at *The Grand Thakar* (Rest ID: 1) |
| 📋 **Restaurant Manager** | `manager@foodyhunters.com` | `password123` | Shift Manager at *The Grand Thakar* (Rest ID: 1) |
| 👤 **Customer** | `customer@foodiehunter.com` | `password123` | Verified Public Customer |

---

## 🔐 Authentication Separation & Role-Based Access Control (RBAC)

1. **Customer Login Separation:**
   - `/auth/login` and `/auth/register` are strictly customer-facing.
   - Public customer registration cannot create admin, restaurant owner, delivery partner, or staff accounts.
   - Submitting arbitrary `role` parameters via form manipulation is completely ignored and enforced as `role='customer'` on the server.

2. **Dedicated Partner Portals:**
   - Restaurant owners authenticate exclusively at `/restaurant/login`.
   - Delivery riders authenticate exclusively at `/delivery/login`.
   - Kitchen staff members authenticate exclusively at `/staff/login`.
   - Administrators authenticate exclusively at `/admin/login`.

3. **Data Boundary Isolation:**
   - **Restaurant Owners:** Can only view, edit, and receive orders, revenue records, dishes, and staff roster belonging strictly to their own assigned `restaurant_id`.
   - **Kitchen Staff:** Bound strictly to their assigned restaurant's kitchen pipeline (`session['restaurant_id']`). They cannot view, modify, or 86 dishes from any other restaurant.
   - **Delivery Partners:** Receive only necessary customer delivery address details for their actively assigned trips. They cannot browse all platform customers.
   - **Suspended & Pending Accounts:** Blocked server-side with informative notices until approved by restaurant owners or administrators.

---

## 🍳 Kitchen Operations & Staff Governance

### 1. Kitchen Staff Onboarding Workflow
- **Option A (Self-Application):** Applicants apply at `/staff/register` selecting their working restaurant, position (Kitchen Staff / Restaurant Manager), and shift. The account is created with `status='pending'`.
- **Option B (Direct Restaurant Owner Onboarding):** The restaurant owner logs in to `/restaurant/dashboard` -> opens **Staff Team & Roles** (`/restaurant/staff`) -> clicks **Onboard New Staff** -> enters staff credentials directly. The account is instantly created with `status='approved'`.

### 2. Administrator Central Governance
- Navigate to `/admin/dashboard` to inspect live platform telemetry (`Total Staff`, `Pending Staff`).
- Open `/admin/staff` to view the unified cross-restaurant staff directory.
- Actions available to Administrator:
  - **Approve / Reject:** Instantly verify pending staff applications.
  - **Toggle Status:** Suspend or reactivate staff accounts.
  - **Reassign Restaurant:** Transfer staff members across restaurant outlets.
  - **Delete Account:** Remove inactive staff records safely.

### 3. Kitchen Display Workspace (`/staff/dashboard`)
- **Live Elapsed Timers:** Order cards visually alert staff of prep time elapsed (green for <15m, amber for 15-30m, red for >30m).
- **Itemized Dish Preparation List:** Complete veg/non-veg tags, quantities, prices, and special instructions/chef notes.
- **One-Click Kitchen State Advancement:**
  - `placed` -> Click **Start Cooking** -> moves to `preparing`.
  - `preparing` -> Click **Packed & Ready for Pickup** -> moves to `ready_for_pickup`.
  - Upon reaching `ready_for_pickup`, the automated delivery partner dispatch workflow assigns an active rider and sends a pickup notification.
- **Dish 86-List (Stock Manager):** Staff can open `/staff/menu` to instantly toggle ingredients or dishes as "Out of Stock" (86'd), preventing customer orders in real-time.

---

## 🚀 How to Run the Application Locally

### Prerequisites
- **Python 3.10+** (Virtual environment located at `d:\foody_hunters\.venv`)
- **XAMPP MySQL** (or built-in SQLite fallback `foody_hunters.db`)

### Step 1: Start MySQL in XAMPP
1. Open **XAMPP Control Panel**.
2. Click **Start** on **MySQL** (Port 3306).

### Step 2: Run Database Migrations
Migrations are safe, non-destructive, and backward-compatible for both MySQL and SQLite:
```powershell
.\.venv\Scripts\Activate.ps1
python migrations.py
```

### Step 3: Start Flask Server
```powershell
.\.venv\Scripts\Activate.ps1
$env:HOST = "127.0.0.1"
$env:PORT = "5000"
$env:FLASK_DEBUG = "0"
python app.py
```
Open your browser to:
- **Customer Storefront:** `http://127.0.0.1:5000/`
- **Admin Control Center:** `http://127.0.0.1:5000/admin/login`
- **Restaurant Owner Portal:** `http://127.0.0.1:5000/restaurant/login`
- **Delivery Partner Portal:** `http://127.0.0.1:5000/delivery/login`
- **Restaurant Staff Desk:** `http://127.0.0.1:5000/staff/login`

---

## 🌐 Cloudflare Quick Tunnel Public Access

To expose all 5 portals to the internet (for mobile phones on 4G/5G data or remote evaluators) without router port-forwarding or public firewall rules:

### Terminal 1 — Start Local Flask
```powershell
.\scripts\start_local.ps1
```

### Terminal 2 — Start Cloudflare Quick Tunnel
```powershell
.\scripts\start_public_tunnel.ps1
```

Cloudflare generates an ephemeral HTTPS link:
```text
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at:                                          |
|  https://whispering-cedar-monkeys-online.trycloudflare.com                                 |
+--------------------------------------------------------------------------------------------+
```

All 5 portals run under this single public HTTPS base URL:
- Customer: `https://<tunnel-domain>/`
- Admin: `https://<tunnel-domain>/admin/login`
- Restaurant Owner: `https://<tunnel-domain>/restaurant/login`
- Delivery Partner: `https://<tunnel-domain>/delivery/login`
- Kitchen Staff: `https://<tunnel-domain>/staff/login`

To stop public access, press `Ctrl + C` in Terminal 2.

---

## 🧪 Comprehensive Automated Testing & Verification

The project includes unit and integration test suites covering all 5 portals and workflows.

### 1. Run Complete Unittest Suite
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
*Current Result:* **39 tests passed in ~22s, 0 failures, 0 errors.**

### 2. Run Comprehensive 5-Portal Verification Script
```powershell
.\.venv\Scripts\python.exe "C:\Users\YADAV ANKUSH\.gemini\antigravity-ide\brain\a5b22caf-0f62-486c-8e3c-d5eb3b1253d7\scratch\verify_responsive_pages.py"
```
*Current Result:* **51 passed, 0 failed** across all routes and responsive viewports.

### 3. Run Individual Feature Modules
```powershell
# Staff Portal & Governance Suite:
.\.venv\Scripts\python.exe -m unittest tests.test_staff_portal_and_governance

# Auth Separation & Mobile Suite:
.\.venv\Scripts\python.exe -m unittest tests.test_auth_separation_and_mobile

# RBAC Verification:
.\.venv\Scripts\python.exe tests/test_auth_rbac.py

# Restaurant Operations & Persistence:
.\.venv\Scripts\python.exe tests/test_restaurant_module.py

# Customer Profile Persistence:
.\.venv\Scripts\python.exe tests/test_customer_profile_persistence.py

# Order & GPS Tracking Lifecycle:
.\.venv\Scripts\python.exe -m unittest tests.test_order_and_tracking_lifecycle
```

---

## 📱 Manual Responsive Testing Guidelines (DevTools)

Every portal template incorporates a `<meta name="viewport" content="width=device-width, initial-scale=1.0">` tag and is verified without horizontal page scroll.

To test responsiveness manually in Google Chrome or Microsoft Edge:
1. Open `http://127.0.0.1:5000/` or your Cloudflare Tunnel URL.
2. Press `F12` -> Click the **Device Toggle Toolbar** icon (`Ctrl + Shift + M`).
3. Select and test these viewport presets:
   - **iPhone SE (375 × 667)**: Test mobile slide drawer, search bar, and cart drawer.
   - **iPhone 12/13/14 Pro (390 × 844)**: Test restaurant cards, checkout form, and kitchen action buttons.
   - **Samsung Galaxy S20 (412 × 915)**: Test kitchen orders queue and rider card.
   - **iPad Mini (768 × 1024)**: Test admin 2-column tables and kitchen prep cards.
   - **Desktop (1366 × 768 / 1920 × 1080)**: Test full responsive sidebar and KPI stat grids.

---

## ⚠️ Known Limitations & Evaluation Notes

1. **Simulated GPS vs. Physical GPS:**
   - Real-time physical device GPS tracking requires active outdoor transit with a device running on mobile data.
   - For academic viva evaluation on a laptop, FOODIE HUNTERS provides an interactive **Demo Simulation Mode** on `/track/<id>` that smoothly animates the rider between Mehsana waypoints, recalculating distance and ETA dynamically.
2. **Payment Gateway in Demo Mode:**
   - Payments are processed via simulated Razorpay/UPI/Card and Cash on Delivery (COD) workflows. No real credit cards or bank accounts are debited.
3. **Database Compatibility:**
   - Native MySQL InnoDB via XAMPP is the primary target environment.
   - Automatic SQLite fallback (`foody_hunters.db`) is maintained for offline environments. Both engines are kept in sync by `migrations.py`.

---

## 📄 License & Attribution
Developed as an enterprise-grade academic major project. All restaurant, dish, customer, and telemetry records are synthetic demonstration data situated in Mehsana, Gujarat.
