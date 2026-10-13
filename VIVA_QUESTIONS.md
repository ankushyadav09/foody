# 🎓 FOODY HUNTERS – Final-Year Viva Questions & Answers

This document contains **45 common viva questions and student-friendly answers** prepared for BCA, iMCA, and B.Tech external examiners.

---

### Q1: What is the title and objective of your project?
**Answer:** The project is **Foody Hunters**, a full-stack web-based online food delivery system. Its objective is to connect four primary stakeholders—Customers, Restaurant Owners, Delivery Partners, and Administrators—enabling online food ordering, menu management, order dispatch, and delivery tracking.

---

### Q2: Why did you choose Python for the backend?
**Answer:** Python is an expressive, highly readable, and maintainable language with rich standard libraries, clean syntax, rapid development capabilities, and strong community support.

---

### Q3: Why did you choose Flask instead of Django?
**Answer:** Flask is a lightweight micro-framework that provides flexibility without enforced boilerplate. It allows us to structure blueprints, routes, database queries, and templates cleanly, making it ideal for learning, modularity, and explaining during academic viva examinations.

---

### Q4: Why did you choose MySQL for the database?
**Answer:** MySQL is an open-source, robust, ACID-compliant Relational Database Management System (RDBMS) that supports foreign key constraints, indexing, transactions, and high concurrent read performance.

---

### Q5: What is XAMPP and why was it used?
**Answer:** XAMPP is a free, cross-platform software package providing Apache, MySQL, PHP, and Perl in a single unified control panel. It allows local hosting of the MySQL database engine without complex server installations.

---

### Q6: What architecture does this application follow?
**Answer:** It follows the **3-Tier Architecture**:
1. **Presentation Tier:** HTML5, CSS3, JavaScript.
2. **Application / Logic Tier:** Python Flask with Blueprint controllers and helpers.
3. **Data Tier:** MySQL database running on port 3306.

---

### Q7: What are the primary user roles in Foody Hunters?
**Answer:** There are four roles:
1. **Customer:** Searches food, adds items to cart, places orders, and tracks delivery.
2. **Restaurant Owner:** Manages menu items, sets prices, and updates food preparation status.
3. **Delivery Partner:** Views assigned deliveries and updates transit statuses.
4. **Administrator:** Oversees users, approves restaurants, manages categories, and views financial reports.

---

### Q8: What is CRUD? Where is CRUD implemented in your project?
**Answer:** CRUD stands for **Create, Read, Update, Delete**. In Foody Hunters:
- **Create:** Adding a food dish, placing an order, registering an account.
- **Read:** Browsing restaurants, viewing menus, viewing order receipts.
- **Update:** Changing food prices, updating order status, editing user profile.
- **Delete:** Removing items from cart, deleting a menu item.

---

### Q9: What is the difference between Authentication and Authorization?
**Answer:**
- **Authentication:** Verifying *who you are* (e.g., logging in with email and password).
- **Authorization:** Verifying *what you are allowed to do* (e.g., a customer cannot access the Admin panel).

---

### Q10: How do you protect passwords in your database?
**Answer:** Passwords are never stored in plain text. We use `werkzeug.security.generate_password_hash` with **PBKDF2 and SHA-256** with random salt. During login, `check_password_hash` verifies the hash.

---

### Q11: What is a Session in web development? How is it handled in Flask?
**Answer:** A session stores user state across multiple HTTP requests. Flask uses cryptographically signed client-side cookies using a secret key (`SECRET_KEY`), storing data like `user_id`, `user_name`, and `role`.

---

### Q12: What is a Primary Key? Give an example from your database.
**Answer:** A Primary Key is a column or set of columns that uniquely identifies every record in a table and cannot contain NULL values. Example: `id` in the `users` and `orders` tables.

---

### Q13: What is a Foreign Key? Give an example from your database.
**Answer:** A Foreign Key is a field in one table that links to the Primary Key of another table, ensuring referential integrity. Example: `user_id` and `restaurant_id` in the `orders` table.

---

### Q14: What is Database Normalization? Did you apply it?
**Answer:** Normalization is the process of organizing data in a database to reduce data redundancy and improve data integrity. We normalized the schema up to **3rd Normal Form (3NF)** by separating users, restaurants, food categories, food items, orders, order items, and payments into distinct relational tables.

---

### Q15: Why is there a separate `order_items` table instead of storing items inside the `orders` table?
**Answer:** Because an order can have multiple food items (a 1-to-many relationship). Placing items directly in `orders` would violate First Normal Form (1NF) or require repeating rows. `order_items` stores each dish, snapshot price, and quantity separately.

---

### Q16: Why do you store price again in `order_items` if it is already in `food_items`?
**Answer:** To preserve historical accuracy. If a restaurant changes the price of a burger from ₹150 to ₹200 next week, past completed orders must still reflect the price at the time of purchase (₹150).

---

### Q17: How does the complete Order Processing workflow work?
**Answer:**
1. Customer adds items to the cart and proceeds to checkout.
2. Order record is created in `orders` with status `pending`.
3. Items are recorded in `order_items`, and active cart is cleared.
4. Restaurant owner accepts and updates status to `preparing` then `ready`.
5. Delivery rider picks up the order (`picked_up` -> `out_for_delivery`).
6. Delivery rider marks `delivered`, and customer can post a review.

---

### Q18: How does your shopping cart calculate totals?
**Answer:**
- **Subtotal:** Sum of (`quantity * price`) for all items.
- **Delivery Fee:** Standard fee charged by the restaurant.
- **Tax (GST):** 5% calculated on subtotal.
- **Discount:** Deducted if a valid coupon is applied.
- **Grand Total:** `Subtotal + Delivery Fee + Tax - Discount`.

---

### Q19: How do promo coupons work in Foody Hunters?
**Answer:** The coupon code is queried in the `coupons` table. The backend checks if it is active and if the cart subtotal meets `min_order`. It then applies either a flat deduction or a percentage deduction up to `max_discount`.

---

### Q20: How is payment handled? Does it use real money?
**Answer:** For academic presentation, the project implements **Cash on Delivery (COD)** and a **Realistic Demo/Sandbox Payment Gateway**. Customers can simulate UPI and Debit/Credit cards. It validates fields, shows a realistic processing animation, and generates mock transaction IDs (`TXN_XXXXXXXX`) without charging real money.

---

### Q21: What are Flask Blueprints and why did you use them?
**Answer:** Blueprints are Flask's way of organizing an application into modular components. Instead of putting all routes in a single huge file, we split them logically into `auth`, `main`, `customer`, `restaurant`, `delivery`, `admin`, and `api`.

---

### Q22: What is SQL Injection and how did you prevent it?
**Answer:** SQL Injection is an attack where malicious SQL statements are inserted into entry fields. We prevented it by using **parameterized queries** with `%s` placeholders in `mysql.connector`, ensuring user inputs are treated strictly as data and never executed as code.

---

### Q23: What is Cross-Site Scripting (XSS) and how is it prevented?
**Answer:** XSS is an attack where malicious scripts are injected into web pages viewed by other users. Jinja2 template engine automatically escapes all HTML variables (e.g. converting `<` to `&lt;`) unless explicitly marked safe.

---

### Q24: What are HTTP methods used in the project?
**Answer:**
- **GET:** Retrieve data from the server (e.g., viewing restaurant list, viewing cart).
- **POST:** Submit data to the server (e.g., login, registering, placing an order, adding a dish).

---

### Q25: What is the dual-mode database feature in `database.py`?
**Answer:** While MySQL via XAMPP is our primary database, `database.py` includes an automatic SQLite fallback (`foody_hunters.db`). If XAMPP is closed or MySQL service is stopped during testing, the app transparently shifts to SQLite so the site never crashes.

---

### Q26: What role decorators did you create and why?
**Answer:** We created Python decorators (`@login_required`, `@admin_required`, `@restaurant_required`, `@delivery_required`) in `utils/helpers.py`. They wrap route functions to ensure unauthenticated or unauthorized users are intercepted and redirected before the view runs.

---

### Q27: How does search work in Foody Hunters?
**Answer:** When a user types a query, Flask executes SQL `LIKE` queries against `food_items.name`, `food_items.description`, `restaurants.name`, and `restaurants.cuisine`. Matching results are returned and displayed on the search results page.

---

### Q28: How does live order tracking work?
**Answer:** The customer views `/customer/order/track/<id>`, which reads `order_status` from the database. A visual step timeline highlights stages (`pending` → `confirmed` → `preparing` → `ready` → `out_for_delivery` → `delivered`). When out for delivery, an interactive animated canvas simulates rider transit.

---

### Q29: Can a customer rate a restaurant without ordering?
**Answer:** No. The system strictly checks the `orders` table to ensure the customer has an order from that restaurant with status `delivered` before accepting a rating and review.

---

### Q30: How does the Admin panel maintain data integrity?
**Answer:** Admins have tools to approve or reject restaurant applications, view all transaction logs, manage categories, moderate reviews, and resolve customer complaints, maintaining platform quality.

---

### Q31: What happens if an image fails to load?
**Answer:** We implemented client-side image fallback handlers (`onerror="this.src='/static/images/foods/default.jpg'"`) so missing or broken images gracefully fall back to a high-quality default image without distorting UI layouts.

---

### Q32: What frontend technologies and libraries were used?
**Answer:** HTML5 for semantic structure, custom CSS3 for responsive layout and animations, vanilla JavaScript (ES6) for DOM manipulation and AJAX, and Font Awesome for icons. No third-party UI framework was copied, giving the site an original brand identity.

---

### Q33: How does the restaurant owner toggle item availability?
**Answer:** In the restaurant menu table, there is an instant toggle action (`/restaurant/food/toggle/<id>`) that flips the `availability` column between 1 (in-stock) and 0 (sold out) in the database.

---

### Q34: What status values can an order have?
**Answer:**
1. `pending` – Placed by customer.
2. `confirmed` – Accepted by restaurant.
3. `preparing` – Food in kitchen.
4. `ready` – Packed and waiting for rider.
5. `out_for_delivery` – Rider transit.
6. `delivered` – Handed to customer.
7. `cancelled` – Cancelled by customer or rejected by restaurant.

---

### Q35: What is the function of `requirements.txt`?
**Answer:** It lists all Python external dependencies (e.g. `Flask`, `mysql-connector-python`, `Werkzeug`) with version specifications so any developer can install the environment using `pip install -r requirements.txt`.

---

### Q36: What is an Application Factory pattern in Flask?
**Answer:** In `app.py`, instead of defining a single global `app` directly, we wrap configuration and blueprint registration inside `create_app()`. This makes testing, blueprint separation, and configuration switching clean and maintainable.

---

### Q37: What is the difference between synchronous and asynchronous requests in your project?
**Answer:**
- **Synchronous:** Form submissions (like login and checkout) where the browser waits and reloads a new page.
- **Asynchronous (AJAX):** Adding an item to cart or changing quantity where JavaScript sends a `fetch` request in the background and updates the UI badge without reloading the page.

---

### Q38: How does the database handle unique emails?
**Answer:** The `email` column in the `users` table has a `UNIQUE` constraint. If a user tries to register with an existing email, MySQL prevents duplicate insertion, and Flask catches this to display a friendly error message.

---

### Q39: What are the current limitations of this project?
**Answer:**
1. SMS gateway for real OTP verification is not integrated.
2. Map tracking uses simulated canvas movement rather than a paid Google Maps API key.
3. Payment runs in sandbox/demo mode rather than charging real bank accounts.

---

### Q40: What is the future scope of this project?
**Answer:**
1. Native Android and iOS apps using Flutter or React Native.
2. Real-time push notifications using WebSockets (Socket.IO).
3. Live Google Maps routing API integration for automated driver dispatch.
4. AI-based food recommendation engine based on past customer orders.

---

### Q41: What error pages are handled in your application?
**Answer:** Custom templates are created for HTTP **404** (Page Not Found), **403** (Forbidden / Unauthorized Access), and **500** (Internal Server Error) with friendly messages and navigation buttons back to the home page.

---

### Q42: What is the purpose of `config.py`?
**Answer:** It centralizes application configuration variables such as `SECRET_KEY`, database credentials (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`), and file upload paths (`UPLOAD_FOLDER`) in one location rather than hardcoding them across different files.

---

### Q43: How does the restaurant owner receive order earnings?
**Answer:** The restaurant sales page computes `SUM(total_amount)` of all non-cancelled orders belonging to that restaurant, showing daily breakdowns, total revenue, and top-performing dishes.

---

### Q44: How are file uploads (food images) handled securely?
**Answer:** `utils/helpers.py` uses `secure_filename()` from Werkzeug to sanitize uploaded image filenames and stores them in `static/uploads/`, preventing directory traversal attacks.

---

### Q45: Why is this project suitable for a final-year submission?
**Answer:** It demonstrates the complete software development lifecycle (SDLC): comprehensive database normalization, full CRUD operations, multi-role access control, secure authentication, real-time dynamic pricing calculations, error handling, responsive UI design, and end-to-end transaction processing.
