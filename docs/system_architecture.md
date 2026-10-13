# System Architecture – FOODY HUNTERS

## 1. Architectural Pattern: 3-Tier Architecture

Foody Hunters follows a traditional, industry-standard **3-Tier Web Application Architecture**:

```
+-------------------------------------------------------------+
|                     PRESENTATION TIER                       |
|   HTML5 + CSS3 + Vanilla JavaScript + Responsive Design     |
|   (Chrome / Edge / Firefox / Mobile Web Browsers)           |
+-------------------------------------------------------------+
                              |
                     HTTP / JSON / AJAX
                              |
+-------------------------------------------------------------+
|                      APPLICATION TIER                       |
|         Python 3.x + Flask Web Framework (WSGI)             |
|   - Blueprint Routing & Controllers                         |
|   - Role-Based Access Control (RBAC) Decorators             |
|   - Session & Cookie Security (PBKDF2 Password Hashing)     |
|   - Business Logic (Cart, Orders, Coupons, Demo Gateway)    |
+-------------------------------------------------------------+
                              |
                     MySQL Connector / SQL
                              |
+-------------------------------------------------------------+
|                        DATA TIER                            |
|             MySQL Server (Port 3306 via XAMPP)              |
|        (Dual-Mode SQLite Fallback Engine Supported)         |
|   - Relational Tables, Foreign Key Constraints, Cascades    |
|   - Indexed Lookup Columns (email, status, restaurant_id)   |
+-------------------------------------------------------------+
```

---

## 2. Component Breakdown

### A. Presentation Layer (Frontend)
- **HTML5 Semantic Templates:** Clean Jinja2 template inheritance starting from `base.html`.
- **Custom CSS3 Styling:** CSS variables for consistent theming, custom glassmorphism card styling, responsive CSS Grid and Flexbox layouts.
- **JavaScript Engine (`main.js`):**
  - Asynchronous AJAX for Cart operations (no full page reload required when adding/modifying items).
  - Client-side validation for phone numbers, email formats, and password confirmation.
  - Interactive toast notifications system.
  - Simulated real-time GPS delivery coordinates and status polling.

### B. Controller & Application Logic (Backend)
- **Modular Blueprints:**
  - `auth_bp`: User registration, role redirection, and session destruction.
  - `main_bp`: Public browsing, search engine query matching, informational pages.
  - `customer_bp`: Shopping cart calculation, coupon validation engine, checkout, order placement, order tracking, review submission.
  - `restaurant_bp`: Store catalog CRUD, incoming order dispatch, live kitchen status tracking, sales reports.
  - `delivery_bp`: Delivery partner dashboard, order dispatch acceptance, multi-stage delivery timeline transitions.
  - `admin_bp`: Platform administration, merchant approvals, user role toggle, category definitions, financial auditing.
  - `api_bp`: REST endpoints for asynchronous suggestions and demo payment processing.

### C. Data Persistence Layer (Database)
- Primary engine: **MySQL** (Community Edition shipped with XAMPP).
- Secondary fallback: **SQLite 3** transparent failover if MySQL service is halted.
- Parameterized SQL statements using `%s` placeholders to guarantee **100% SQL injection prevention**.

---

## 3. Data Flow Diagram (DFD - Level 1)

```
[Customer]
    │
    ├─► 1. Browse / Search Food & Restaurant ──► [System Query DB]
    │
    ├─► 2. Add Item to Cart ───────────────────► [Session / Cart DB]
    │
    ├─► 3. Apply Coupon & Checkout ────────────► [Validate Coupon Rules]
    │
    ├─► 4. Demo Payment / COD ─────────────────► [Create Order & Payment Record]
    │
    ▼
[Order Created: Status = 'pending']
    │
    ├─► 5. Restaurant Accepts & Prepares ─────► [Update Status = 'preparing']
    │
    ├─► 6. Order Dispatched to Delivery Rider ─► [Update Status = 'out_for_delivery']
    │
    ├─► 7. Delivery Partner Delivers Order ───► [Update Status = 'delivered']
    │
    ▼
[Customer Submits Rating & Review] ───────────► [Update Restaurant Average Rating]
```

---

## 4. Security Architecture
1. **Password Security:** Passwords are never stored in plaintext. They are encrypted using `werkzeug.security.generate_password_hash` utilizing salted PBKDF2 with SHA-256 iterations.
2. **Session Security:** Flask cryptographically signs session cookies using `SECRET_KEY` with `HttpOnly` and `SameSite=Lax` protection.
3. **Role Enforcement:** Custom Python decorators (`@login_required`, `@admin_required`, `@restaurant_required`, `@delivery_required`) verify credentials and role before granting access to protected views.
4. **Parameterized Queries:** All database interactions pass variables as separate parameter tuples, disallowing arbitrary SQL injection attacks.
