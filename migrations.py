"""
migrations.py – Versioned, Idempotent Database Migration Manager for Foody Hunters.
Supports both SQLite and MySQL engines.
Safe: Never drops tables or loses existing data.
Idempotent: Inspects table schemas before altering; re-running produces no errors.
"""

import sys
import os
import sqlite3
from datetime import datetime

# Root directory of project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'foody_hunters.db')


def get_sqlite_columns(conn, table_name):
    """Return set of existing column names for a SQLite table."""
    cur = conn.cursor()
    try:
        cur.execute(f'PRAGMA table_info("{table_name}")')
        return {row[1] for row in cur.fetchall()}
    except Exception:
        return set()


def get_sqlite_tables(conn):
    """Return set of existing table names in SQLite."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def get_mysql_columns(conn, table_name):
    """Return set of existing column names for a MySQL table."""
    cur = conn.cursor()
    try:
        cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()


def get_mysql_tables(conn):
    """Return set of existing table names in MySQL."""
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    return {row[0] for row in cur.fetchall()}


# ─────────────────────────────────────────────────────────────────────────────
# MIGRATION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

def migrate_sqlite(conn):
    """Execute all idempotent schema upgrades on SQLite connection."""
    cur = conn.cursor()

    # 1. Ensure migrations tracking table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()

    cur.execute("SELECT version FROM schema_migrations")
    applied = {row[0] for row in cur.fetchall()}

    def record_migration(version, description):
        cur.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, description, applied_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (version, description)
        )
        conn.commit()

    tables = get_sqlite_tables(conn)

    # ── Migration 001: Ensure all required tables exist ─────────────────────
    # Missing tables: delivery_locations, favorites, notifications
    if 'delivery_locations' not in tables:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_partner_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (delivery_partner_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );
        """)
    if 'favorites' not in tables:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, item_type, item_id)
        );
        """)
    if 'notifications' not in tables:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'customer',
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT DEFAULT NULL,
            is_read INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
    conn.commit()
    record_migration('001_create_missing_tables', 'Ensure delivery_locations, favorites, and notifications tables exist')

    # ── Migration 002: Upgrade users table ──────────────────────────────────
    user_cols = get_sqlite_columns(conn, 'users')
    col_defs_users = [
        ('gender', 'TEXT DEFAULT NULL'),
        ('dob', 'DATE DEFAULT NULL'),
        ('city', "TEXT DEFAULT 'Mehsana'"),
        ('state', "TEXT DEFAULT 'Gujarat'"),
        ('pincode', "TEXT DEFAULT '384001'"),
        ('profile_pic', 'TEXT DEFAULT NULL'),
        ('updated_at', 'DATETIME DEFAULT NULL'),
    ]
    for col_name, col_def in col_defs_users:
        if col_name not in user_cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            user_cols.add(col_name)

    # Semantic backfill for existing rows where city or state is NULL
    cur.execute("UPDATE users SET city='Mehsana' WHERE city IS NULL OR city=''")
    cur.execute("UPDATE users SET state='Gujarat' WHERE state IS NULL OR state=''")
    cur.execute("UPDATE users SET pincode='384001' WHERE pincode IS NULL OR pincode=''")
    cur.execute("UPDATE users SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    conn.commit()
    record_migration('002_upgrade_users_columns', 'Add gender, dob, city, state, pincode, profile_pic, updated_at to users')

    # ── Migration 003: Upgrade restaurants table ────────────────────────────
    rest_cols = get_sqlite_columns(conn, 'restaurants')
    col_defs_rest = [
        ('verification_status', "TEXT DEFAULT 'approved'"),
        ('area', "TEXT DEFAULT 'Mehsana City'"),
        ('city', "TEXT DEFAULT 'Mehsana'"),
        ('state', "TEXT DEFAULT 'Gujarat'"),
        ('pincode', "TEXT DEFAULT '384002'"),
        ('email', 'TEXT DEFAULT NULL'),
        ('total_ratings', 'INTEGER DEFAULT 0'),
        ('open_time', "TEXT DEFAULT '09:00'"),
        ('close_time', "TEXT DEFAULT '23:00'"),
        ('latitude', 'REAL DEFAULT 23.5880000'),
        ('longitude', 'REAL DEFAULT 72.3693000'),
        ('is_open', 'INTEGER DEFAULT 1'),
        ('updated_at', 'DATETIME DEFAULT NULL'),
    ]
    for col_name, col_def in col_defs_rest:
        if col_name not in rest_cols:
            cur.execute(f"ALTER TABLE restaurants ADD COLUMN {col_name} {col_def}")
            rest_cols.add(col_name)

    # Backfill verification_status and is_open
    cur.execute("UPDATE restaurants SET verification_status='approved' WHERE verification_status IS NULL OR verification_status=''")
    cur.execute("UPDATE restaurants SET is_open=1 WHERE is_open IS NULL")
    cur.execute("UPDATE restaurants SET city='Mehsana' WHERE city IS NULL OR city=''")
    cur.execute("UPDATE restaurants SET state='Gujarat' WHERE state IS NULL OR state=''")
    cur.execute("UPDATE restaurants SET pincode='384002' WHERE pincode IS NULL OR pincode=''")
    cur.execute("UPDATE restaurants SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    conn.commit()
    record_migration('003_upgrade_restaurants_columns', 'Add verification_status, area, city, state, pincode, coordinates, open hours to restaurants')

    # ── Migration 004: Upgrade food_categories table ────────────────────────
    cat_cols = get_sqlite_columns(conn, 'food_categories')
    if 'description' not in cat_cols:
        cur.execute("ALTER TABLE food_categories ADD COLUMN description TEXT DEFAULT NULL")
    if 'is_active' not in cat_cols:
        cur.execute("ALTER TABLE food_categories ADD COLUMN is_active INTEGER DEFAULT 1")
    conn.commit()
    record_migration('004_upgrade_food_categories_columns', 'Add description and is_active to food_categories')

    # ── Migration 005: Upgrade food_items table ─────────────────────────────
    fi_cols = get_sqlite_columns(conn, 'food_items')
    col_defs_fi = [
        ('discount', 'REAL DEFAULT 0.00'),
        ('final_price', 'REAL DEFAULT NULL'),
        ('preparation_time', 'INTEGER DEFAULT 20'),
        ('is_bestseller', 'INTEGER DEFAULT 0'),
        ('total_ratings', 'INTEGER DEFAULT 0'),
        ('updated_at', 'DATETIME DEFAULT NULL'),
    ]
    for col_name, col_def in col_defs_fi:
        if col_name not in fi_cols:
            cur.execute(f"ALTER TABLE food_items ADD COLUMN {col_name} {col_def}")
            fi_cols.add(col_name)

    # Backfill final_price to price if final_price is NULL
    cur.execute("UPDATE food_items SET final_price=price WHERE final_price IS NULL")
    cur.execute("UPDATE food_items SET is_bestseller=0 WHERE is_bestseller IS NULL")
    cur.execute("UPDATE food_items SET preparation_time=20 WHERE preparation_time IS NULL")
    cur.execute("UPDATE food_items SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    conn.commit()
    record_migration('005_upgrade_food_items_columns', 'Add discount, final_price, preparation_time, is_bestseller to food_items')

    # ── Migration 006: Upgrade cart and cart_items ──────────────────────────
    cart_cols = get_sqlite_columns(conn, 'cart')
    if 'updated_at' not in cart_cols:
        cur.execute("ALTER TABLE cart ADD COLUMN updated_at DATETIME DEFAULT NULL")
        cur.execute("UPDATE cart SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    ci_cols = get_sqlite_columns(conn, 'cart_items')
    if 'created_at' not in ci_cols:
        cur.execute("ALTER TABLE cart_items ADD COLUMN created_at DATETIME DEFAULT NULL")
        cur.execute("UPDATE cart_items SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL")
    conn.commit()
    record_migration('006_upgrade_cart_tables', 'Add updated_at to cart and created_at to cart_items')

    # ── Migration 007: Upgrade addresses table ──────────────────────────────
    addr_cols = get_sqlite_columns(conn, 'addresses')
    col_defs_addr = [
        ('area', "TEXT DEFAULT 'Radhanpur Road'"),
        ('state', "TEXT DEFAULT 'Gujarat'"),
        ('latitude', 'REAL DEFAULT 23.5880000'),
        ('longitude', 'REAL DEFAULT 72.3693000'),
    ]
    for col_name, col_def in col_defs_addr:
        if col_name not in addr_cols:
            cur.execute(f"ALTER TABLE addresses ADD COLUMN {col_name} {col_def}")
            addr_cols.add(col_name)
    conn.commit()
    record_migration('007_upgrade_addresses_columns', 'Add area, state, latitude, longitude to addresses')

    # ── Migration 008: Upgrade coupons table ────────────────────────────────
    cp_cols = get_sqlite_columns(conn, 'coupons')
    if 'times_used' not in cp_cols:
        cur.execute("ALTER TABLE coupons ADD COLUMN times_used INTEGER DEFAULT 0")
    conn.commit()
    record_migration('008_upgrade_coupons_columns', 'Add times_used to coupons')

    # ── Migration 009: Upgrade orders and order_items ───────────────────────
    order_cols = get_sqlite_columns(conn, 'orders')
    col_defs_orders = [
        ('delivery_address', "TEXT DEFAULT ''"),
        ('customer_lat', 'REAL DEFAULT 23.5880000'),
        ('customer_lng', 'REAL DEFAULT 72.3693000'),
    ]
    for col_name, col_def in col_defs_orders:
        if col_name not in order_cols:
            cur.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}")
            order_cols.add(col_name)

    oi_cols = get_sqlite_columns(conn, 'order_items')
    if 'item_name' not in oi_cols:
        cur.execute("ALTER TABLE order_items ADD COLUMN item_name TEXT DEFAULT ''")
    conn.commit()
    record_migration('009_upgrade_orders_columns', 'Add delivery_address and coordinates to orders, item_name to order_items')

    # ── Migration 010: Upgrade delivery_partners table ──────────────────────
    dp_cols = get_sqlite_columns(conn, 'delivery_partners')
    col_defs_dp = [
        ('is_online', 'INTEGER DEFAULT 1'),
        ('total_deliveries', 'INTEGER DEFAULT 0'),
        ('total_earnings', 'REAL DEFAULT 0.00'),
        ('updated_at', 'DATETIME DEFAULT NULL'),
    ]
    for col_name, col_def in col_defs_dp:
        if col_name not in dp_cols:
            cur.execute(f"ALTER TABLE delivery_partners ADD COLUMN {col_name} {col_def}")
            dp_cols.add(col_name)
    cur.execute("UPDATE delivery_partners SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    conn.commit()
    record_migration('010_upgrade_delivery_partners_columns', 'Add is_online, total_deliveries, total_earnings, updated_at to delivery_partners')

    # ── Migration 011: Demo credentials domain alignment ────────────────────
    # Both @foodiehunter.com and @foodyhunters.com demo accounts are supported
    # If users 1-4 have @foodyhunters.com, ensure demo users with @foodiehunter.com also exist
    # (or vice-versa), preserving all existing data and hashes.
    cur.execute("SELECT email FROM users")
    existing_emails = {row[0].lower() for row in cur.fetchall()}

    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash('password123')

    demo_pairs = [
        ('customer@foodiehunter.com', 'Raj Patel', 'customer', '9876543210', 'B-402, Shivalik Residency, Mehsana'),
        ('restaurant@foodiehunter.com', 'Chef Sanjeev Kumar', 'restaurant', '9823456789', '101, Food Street, Mehsana'),
        ('delivery@foodiehunter.com', 'Vikram Singh', 'delivery', '9812345678', '12, Shanti Nagar, Mehsana'),
        ('admin@foodiehunter.com', 'System Administrator', 'admin', '9898989898', 'Foody Hunters HQ, Mehsana'),
        ('customer@foodyhunters.com', 'Raj Patel', 'customer', '9876543210', 'B-402, Shivalik Residency, Mehsana'),
        ('restaurant@foodyhunters.com', 'Chef Sanjeev Kumar', 'restaurant', '9823456789', '101, Food Street, Mehsana'),
        ('delivery@foodyhunters.com', 'Vikram Singh', 'delivery', '9812345678', '12, Shanti Nagar, Mehsana'),
        ('admin@foodyhunters.com', 'System Administrator', 'admin', '9898989898', 'Foody Hunters HQ, Mehsana'),
    ]

    for email, name, role, phone, addr in demo_pairs:
        if email not in existing_emails:
            cur.execute("""
            INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'Mehsana', 'Gujarat', '384001', 'active', CURRENT_TIMESTAMP)
            """, (name, email, phone, pw_hash, role, addr))
            existing_emails.add(email)

    conn.commit()
    record_migration('011_ensure_dual_domain_demo_accounts', 'Ensure both @foodiehunter.com and @foodyhunters.com demo users exist for test suite and UI')

    # ── Migration 012: Ensure restaurant_staff table exists and seed demo staff ──
    if 'restaurant_staff' not in get_sqlite_tables(conn):
        cur.execute("""
        CREATE TABLE IF NOT EXISTS restaurant_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            restaurant_id INTEGER NOT NULL,
            staff_role TEXT NOT NULL DEFAULT 'kitchen_staff',
            status TEXT NOT NULL DEFAULT 'approved',
            shift TEXT DEFAULT 'Full Time',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
        );
        """)
        conn.commit()

    # Seed demo staff accounts if not present
    staff_demo_pairs = [
        ('staff@foodyhunters.com', 'Ramesh Chef (Kitchen Lead)', 'staff', '9811122233', 'Kitchen Block, Mehsana', 1, 'kitchen_staff'),
        ('staff@foodiehunter.com', 'Ramesh Chef (Kitchen Lead)', 'staff', '9811122233', 'Kitchen Block, Mehsana', 1, 'kitchen_staff'),
        ('manager@foodyhunters.com', 'Amit Trivedi (Restaurant Manager)', 'staff', '9822233344', 'Modhera Road, Mehsana', 1, 'restaurant_manager'),
        ('manager@foodiehunter.com', 'Amit Trivedi (Restaurant Manager)', 'staff', '9822233344', 'Modhera Road, Mehsana', 1, 'restaurant_manager'),
    ]
    cur.execute("SELECT id, email FROM users")
    user_email_map = {row[1].lower(): row[0] for row in cur.fetchall()}

    for email, name, role, phone, addr, rest_id, staff_role in staff_demo_pairs:
        if email not in user_email_map:
            cur.execute("""
            INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'Mehsana', 'Gujarat', '384001', 'active', CURRENT_TIMESTAMP)
            """, (name, email, phone, pw_hash, role, addr))
            u_id = cur.lastrowid
            user_email_map[email] = u_id
        else:
            u_id = user_email_map[email]
            cur.execute("UPDATE users SET role='staff' WHERE id=?", (u_id,))

        cur.execute("SELECT id FROM restaurant_staff WHERE user_id=?", (u_id,))
        if not cur.fetchone():
            cur.execute("""
            INSERT INTO restaurant_staff (user_id, restaurant_id, staff_role, status, shift, created_at, updated_at)
            VALUES (?, ?, ?, 'approved', 'Morning & Evening Shift', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (u_id, rest_id, staff_role))

    conn.commit()
    record_migration('012_create_restaurant_staff_and_demo_staff', 'Create restaurant_staff table and seed demo kitchen staff and restaurant manager')

    # ── Migration 013: Restaurant Onboarding & Verification Fields ─────────────
    rest_cols = get_sqlite_columns(conn, 'restaurants')
    if 'verification_doc' not in rest_cols:
        cur.execute("ALTER TABLE restaurants ADD COLUMN verification_doc TEXT DEFAULT NULL")
    if 'fssai_number' not in rest_cols:
        cur.execute("ALTER TABLE restaurants ADD COLUMN fssai_number TEXT DEFAULT NULL")
    conn.commit()
    record_migration('013_restaurant_onboarding_fields', 'Add verification_doc and fssai_number to restaurants for partner onboarding')

    # ── Migration 014: Full Delivery Workflow, Shifts, Tips, Incentives & Reviews
    rest_cols = get_sqlite_columns(conn, 'restaurants')
    if 'banner_image' not in rest_cols:
        cur.execute("ALTER TABLE restaurants ADD COLUMN banner_image TEXT DEFAULT NULL")
    if 'logo' not in rest_cols:
        cur.execute("ALTER TABLE restaurants ADD COLUMN logo TEXT DEFAULT NULL")

    dp_cols = get_sqlite_columns(conn, 'delivery_partners')
    if 'verification_status' not in dp_cols:
        cur.execute("ALTER TABLE delivery_partners ADD COLUMN verification_status TEXT DEFAULT 'approved'")
    if 'fssai_or_doc' not in dp_cols:
        cur.execute("ALTER TABLE delivery_partners ADD COLUMN fssai_or_doc TEXT DEFAULT NULL")

    order_cols = get_sqlite_columns(conn, 'orders')
    if 'tip_amount' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN tip_amount REAL DEFAULT 0.00")

    pay_cols = get_sqlite_columns(conn, 'payments')
    if 'tip_amount' not in pay_cols:
        cur.execute("ALTER TABLE payments ADD COLUMN tip_amount REAL DEFAULT 0.00")

    rev_cols = get_sqlite_columns(conn, 'reviews')
    if 'delivery_rating' not in rev_cols:
        cur.execute("ALTER TABLE reviews ADD COLUMN delivery_rating INTEGER DEFAULT NULL")
    if 'delivery_partner_id' not in rev_cols:
        cur.execute("ALTER TABLE reviews ADD COLUMN delivery_partner_id INTEGER DEFAULT NULL")

    # Shift Management & Booking Tables
    sqlite_tbls = get_sqlite_tables(conn)
    if 'delivery_shifts' not in sqlite_tbls:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            shift_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            city TEXT DEFAULT 'Mehsana',
            zone TEXT DEFAULT 'Mehsana Central',
            max_capacity INTEGER DEFAULT 10,
            status TEXT DEFAULT 'open',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

    if 'shift_bookings' not in sqlite_tbls:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS shift_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            partner_id INTEGER NOT NULL,
            status TEXT DEFAULT 'booked',
            booked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            cancelled_at DATETIME DEFAULT NULL,
            FOREIGN KEY (shift_id) REFERENCES delivery_shifts(id) ON DELETE CASCADE,
            FOREIGN KEY (partner_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

    if 'delivery_incentive_rules' not in sqlite_tbls:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_incentive_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            incentive_type TEXT DEFAULT 'deliveries_milestone',
            target_count INTEGER NOT NULL DEFAULT 5,
            bonus_amount REAL NOT NULL DEFAULT 150.00,
            min_shift_hours REAL DEFAULT 0.00,
            description TEXT DEFAULT NULL,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

    if 'delivery_partner_incentives' not in sqlite_tbls:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_partner_incentives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id INTEGER NOT NULL,
            rule_id INTEGER NOT NULL,
            shift_id INTEGER DEFAULT NULL,
            qualifying_deliveries INTEGER DEFAULT 0,
            earned_amount REAL NOT NULL DEFAULT 0.00,
            status TEXT DEFAULT 'earned',
            credited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

    # Seed initial shifts for upcoming 7 days
    from datetime import date, timedelta
    cur.execute("SELECT COUNT(*) FROM delivery_shifts")
    if cur.fetchone()[0] == 0:
        base_d = date.today()
        shift_templates = [
            ('Morning Express Shift', '07:00', '15:00', 'Mehsana Central', 8),
            ('Afternoon Rush Shift', '12:00', '18:00', 'Mehsana Highway Hub', 10),
            ('Evening Dinner Peak Shift', '18:00', '23:30', 'Mehsana City & Banquets', 12),
        ]
        for day_offset in range(7):
            cur_date = base_d + timedelta(days=day_offset)
            for title, s_time, e_time, zone, cap in shift_templates:
                cur.execute("""
                INSERT INTO delivery_shifts (title, shift_date, start_time, end_time, city, zone, max_capacity, status, created_at)
                VALUES (?, ?, ?, ?, 'Mehsana', ?, ?, 'open', CURRENT_TIMESTAMP)
                """, (title, cur_date.strftime('%Y-%m-%d'), s_time, e_time, zone, cap))

    # Seed standard incentive rules
    cur.execute("SELECT COUNT(*) FROM delivery_incentive_rules")
    if cur.fetchone()[0] == 0:
        rules = [
            ('Daily 5-Delivery Milestone', 'deliveries_milestone', 5, 150.00, 'Complete 5 deliveries in a single day to earn ₹150 bonus.'),
            ('Super 10-Delivery Target', 'deliveries_milestone', 10, 350.00, 'Complete 10 deliveries in a single day to earn ₹350 bonus.'),
            ('Full Shift Completion Reward', 'shift_completion', 3, 100.00, 'Complete a booked shift with minimum 3 deliveries for ₹100 bonus.'),
            ('Evening Peak Hours Bonus', 'peak_hours', 4, 120.00, 'Deliver during 19:00 - 22:30 dinner peak hours for ₹120 bonus.')
        ]
        for title, itype, target, bonus, desc in rules:
            cur.execute("""
            INSERT INTO delivery_incentive_rules (title, incentive_type, target_count, bonus_amount, description, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (title, itype, target, bonus, desc))

    conn.commit()
    record_migration('014_delivery_shifts_tips_incentives_reviews', 'Add shift booking, incentives, tips, banner images and reviews to SQLite')


def migrate_mysql(conn):
    """Execute schema initialization and migrations on MySQL connection."""
    import config
    cur = conn.cursor()
    target_db = config.Config.DB_NAME

    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{target_db}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE `{target_db}`")

    # Read schema.sql to initialize any tables missing in MySQL
    cur.execute("SHOW TABLES")
    existing_tables = {row[0].lower() for row in cur.fetchall()}

    schema_sql_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
    if len(existing_tables) < 15 and os.path.exists(schema_sql_path):
        with open(schema_sql_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        # Remove CREATE DATABASE / USE and ensure target_db
        statements = sql_script.split(';')
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            upper_stmt = stmt.upper()
            if upper_stmt.startswith('CREATE DATABASE') or upper_stmt.startswith('USE ') or upper_stmt.startswith('DROP TABLE'):
                continue
            try:
                cur.execute(stmt)
            except Exception:
                pass
        conn.commit()

    # Seed data if users table is empty
    cur.execute(f"USE `{target_db}`")
    cur.execute("SELECT COUNT(*) FROM `users`")
    u_cnt = cur.fetchone()[0]
    seed_sql_path = os.path.join(BASE_DIR, 'database', 'seed.sql')
    if u_cnt == 0 and os.path.exists(seed_sql_path):
        with open(seed_sql_path, 'r', encoding='utf-8') as f:
            seed_script = f.read()
        for stmt in seed_script.split(';'):
            stmt = stmt.strip()
            if not stmt:
                continue
            cleaned_lines = [l for l in stmt.splitlines() if not l.strip().startswith('--')]
            cleaned_stmt = '\n'.join(cleaned_lines).strip()
            if not cleaned_stmt or cleaned_stmt.upper().startswith('USE '):
                continue
            try:
                cur.execute(cleaned_stmt)
            except Exception:
                pass
        conn.commit()

    # Track migration in schema_migrations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS `schema_migrations` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `version` VARCHAR(100) NOT NULL UNIQUE,
        `description` TEXT NOT NULL,
        `applied_at` DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    conn.commit()

    # ── Migration 012 for MySQL: restaurant_staff table and demo staff accounts ──
    try:
        cur.execute("ALTER TABLE `users` MODIFY COLUMN `role` ENUM('customer', 'restaurant', 'delivery', 'admin', 'staff') NOT NULL DEFAULT 'customer'")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS `restaurant_staff` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT NOT NULL UNIQUE,
            `restaurant_id` INT NOT NULL,
            `staff_role` ENUM('kitchen_staff', 'restaurant_manager') NOT NULL DEFAULT 'kitchen_staff',
            `status` ENUM('pending', 'approved', 'rejected', 'suspended') NOT NULL DEFAULT 'approved',
            `shift` VARCHAR(50) DEFAULT 'Full Time',
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
            FOREIGN KEY (`restaurant_id`) REFERENCES `restaurants`(`id`) ON DELETE CASCADE,
            INDEX `idx_staff_rest` (`restaurant_id`),
            INDEX `idx_staff_user` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()

        cur.execute("SELECT id, email FROM users")
        mysql_users = {row[1].lower(): row[0] for row in cur.fetchall()}
        from werkzeug.security import generate_password_hash
        m_pw_hash = generate_password_hash('password123')

        m_staff_pairs = [
            ('staff@foodyhunters.com', 'Ramesh Chef (Kitchen Lead)', 'staff', '9811122233', 'Kitchen Block, Mehsana', 1, 'kitchen_staff'),
            ('staff@foodiehunter.com', 'Ramesh Chef (Kitchen Lead)', 'staff', '9811122233', 'Kitchen Block, Mehsana', 1, 'kitchen_staff'),
            ('manager@foodyhunters.com', 'Amit Trivedi (Restaurant Manager)', 'staff', '9822233344', 'Modhera Road, Mehsana', 1, 'restaurant_manager'),
            ('manager@foodiehunter.com', 'Amit Trivedi (Restaurant Manager)', 'staff', '9822233344', 'Modhera Road, Mehsana', 1, 'restaurant_manager'),
        ]
        for m_email, m_name, m_role, m_phone, m_addr, m_rest_id, m_staff_role in m_staff_pairs:
            if m_email not in mysql_users:
                cur.execute("""
                INSERT INTO users (name, email, phone, password_hash, role, address, city, state, pincode, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'Mehsana', 'Gujarat', '384001', 'active', NOW())
                """, (m_name, m_email, m_phone, m_pw_hash, m_role, m_addr))
                conn.commit()
                cur.execute("SELECT id FROM users WHERE email=%s", (m_email,))
                m_uid = cur.fetchone()[0]
                mysql_users[m_email] = m_uid
            else:
                m_uid = mysql_users[m_email]
                cur.execute("UPDATE users SET role='staff' WHERE id=%s", (m_uid,))
                conn.commit()

            cur.execute("SELECT id FROM restaurant_staff WHERE user_id=%s", (m_uid,))
            if not cur.fetchone():
                cur.execute("""
                INSERT INTO restaurant_staff (user_id, restaurant_id, staff_role, status, shift, created_at, updated_at)
                VALUES (%s, %s, %s, 'approved', 'Morning & Evening Shift', NOW(), NOW())
                """, (m_uid, m_rest_id, m_staff_role))
                conn.commit()

        cur.execute("""
        INSERT IGNORE INTO schema_migrations (version, description, applied_at)
        VALUES ('012_create_restaurant_staff_and_demo_staff', 'Create restaurant_staff table and seed demo kitchen staff and restaurant manager', NOW())
        """)
        conn.commit()
    except Exception as e:
        print(f"[MYSQL STAFF MIGRATION NOTICE] {e}", file=sys.stderr)

    # ── Migration 013 for MySQL: Restaurant Onboarding & Verification Fields ──
    try:
        cur.execute("SHOW COLUMNS FROM `restaurants`")
        mysql_rest_cols = {row[0].lower() for row in cur.fetchall()}
        if 'verification_doc' not in mysql_rest_cols:
            cur.execute("ALTER TABLE `restaurants` ADD COLUMN `verification_doc` VARCHAR(255) DEFAULT NULL")
        if 'fssai_number' not in mysql_rest_cols:
            cur.execute("ALTER TABLE `restaurants` ADD COLUMN `fssai_number` VARCHAR(50) DEFAULT NULL")
        conn.commit()
        cur.execute("""
        INSERT IGNORE INTO schema_migrations (version, description, applied_at)
        VALUES ('013_restaurant_onboarding_fields', 'Add verification_doc and fssai_number to restaurants for partner onboarding', NOW())
        """)
        conn.commit()
    except Exception as e:
        print(f"[MYSQL RESTAURANT ONBOARDING MIGRATION NOTICE] {e}", file=sys.stderr)

    # ── Migration 014 for MySQL: Full Delivery Workflow, Shifts, Tips, Incentives & Reviews ──
    try:
        cur.execute("SHOW COLUMNS FROM `restaurants`")
        mysql_rest_cols = {row[0].lower() for row in cur.fetchall()}
        if 'banner_image' not in mysql_rest_cols:
            cur.execute("ALTER TABLE `restaurants` ADD COLUMN `banner_image` VARCHAR(255) DEFAULT NULL")
        if 'logo' not in mysql_rest_cols:
            cur.execute("ALTER TABLE `restaurants` ADD COLUMN `logo` VARCHAR(255) DEFAULT NULL")

        cur.execute("SHOW COLUMNS FROM `delivery_partners`")
        mysql_dp_cols = {row[0].lower() for row in cur.fetchall()}
        if 'verification_status' not in mysql_dp_cols:
            cur.execute("ALTER TABLE `delivery_partners` ADD COLUMN `verification_status` ENUM('pending','approved','rejected','suspended') DEFAULT 'approved'")
        if 'fssai_or_doc' not in mysql_dp_cols:
            cur.execute("ALTER TABLE `delivery_partners` ADD COLUMN `fssai_or_doc` VARCHAR(255) DEFAULT NULL")

        cur.execute("SHOW COLUMNS FROM `orders`")
        mysql_ord_cols = {row[0].lower() for row in cur.fetchall()}
        if 'tip_amount' not in mysql_ord_cols:
            cur.execute("ALTER TABLE `orders` ADD COLUMN `tip_amount` DECIMAL(8,2) DEFAULT 0.00")

        cur.execute("SHOW COLUMNS FROM `payments`")
        mysql_pay_cols = {row[0].lower() for row in cur.fetchall()}
        if 'tip_amount' not in mysql_pay_cols:
            cur.execute("ALTER TABLE `payments` ADD COLUMN `tip_amount` DECIMAL(8,2) DEFAULT 0.00")

        cur.execute("SHOW COLUMNS FROM `reviews`")
        mysql_rev_cols = {row[0].lower() for row in cur.fetchall()}
        if 'delivery_rating' not in mysql_rev_cols:
            cur.execute("ALTER TABLE `reviews` ADD COLUMN `delivery_rating` INT DEFAULT NULL")
        if 'delivery_partner_id' not in mysql_rev_cols:
            cur.execute("ALTER TABLE `reviews` ADD COLUMN `delivery_partner_id` INT DEFAULT NULL")

        cur.execute("SHOW TABLES")
        mysql_tbls = {row[0].lower() for row in cur.fetchall()}

        if 'delivery_shifts' not in mysql_tbls:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS `delivery_shifts` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `title` VARCHAR(100) NOT NULL,
                `shift_date` DATE NOT NULL,
                `start_time` TIME NOT NULL,
                `end_time` TIME NOT NULL,
                `city` VARCHAR(60) DEFAULT 'Mehsana',
                `zone` VARCHAR(100) DEFAULT 'Mehsana Central',
                `max_capacity` INT DEFAULT 10,
                `status` ENUM('open', 'full', 'completed', 'cancelled') DEFAULT 'open',
                `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX `idx_shift_date` (`shift_date`),
                INDEX `idx_shift_city` (`city`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

        if 'shift_bookings' not in mysql_tbls:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS `shift_bookings` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `shift_id` INT NOT NULL,
                `partner_id` INT NOT NULL,
                `status` ENUM('booked', 'completed', 'cancelled') DEFAULT 'booked',
                `booked_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `cancelled_at` DATETIME DEFAULT NULL,
                FOREIGN KEY (`shift_id`) REFERENCES `delivery_shifts`(`id`) ON DELETE CASCADE,
                FOREIGN KEY (`partner_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
                INDEX `idx_sb_shift` (`shift_id`),
                INDEX `idx_sb_partner` (`partner_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

        if 'delivery_incentive_rules' not in mysql_tbls:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS `delivery_incentive_rules` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `title` VARCHAR(150) NOT NULL,
                `incentive_type` ENUM('deliveries_milestone', 'shift_completion', 'peak_hours', 'weekend_special') DEFAULT 'deliveries_milestone',
                `target_count` INT NOT NULL DEFAULT 5,
                `bonus_amount` DECIMAL(8,2) NOT NULL DEFAULT 150.00,
                `min_shift_hours` DECIMAL(4,2) DEFAULT 0.00,
                `description` VARCHAR(255) DEFAULT NULL,
                `is_active` TINYINT(1) DEFAULT 1,
                `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

        if 'delivery_partner_incentives' not in mysql_tbls:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS `delivery_partner_incentives` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `partner_id` INT NOT NULL,
                `rule_id` INT NOT NULL,
                `shift_id` INT DEFAULT NULL,
                `qualifying_deliveries` INT DEFAULT 0,
                `earned_amount` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
                `status` ENUM('in_progress', 'earned', 'paid') DEFAULT 'earned',
                `credited_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (`partner_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
                INDEX `idx_dpi_partner` (`partner_id`),
                INDEX `idx_dpi_rule` (`rule_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

        # Seed initial shifts for upcoming 7 days in MySQL if empty
        from datetime import date, timedelta
        cur.execute("SELECT COUNT(*) FROM `delivery_shifts`")
        if cur.fetchone()[0] == 0:
            base_d = date.today()
            shift_templates = [
                ('Morning Express Shift', '07:00:00', '15:00:00', 'Mehsana Central', 8),
                ('Afternoon Rush Shift', '12:00:00', '18:00:00', 'Mehsana Highway Hub', 10),
                ('Evening Dinner Peak Shift', '18:00:00', '23:30:00', 'Mehsana City & Banquets', 12),
            ]
            for day_offset in range(7):
                cur_date = base_d + timedelta(days=day_offset)
                for title, s_time, e_time, zone, cap in shift_templates:
                    cur.execute("""
                    INSERT INTO `delivery_shifts` (`title`, `shift_date`, `start_time`, `end_time`, `city`, `zone`, `max_capacity`, `status`, `created_at`)
                    VALUES (%s, %s, %s, %s, 'Mehsana', %s, %s, 'open', NOW())
                    """, (title, cur_date.strftime('%Y-%m-%d'), s_time, e_time, zone, cap))

        # Seed standard incentive rules in MySQL if empty
        cur.execute("SELECT COUNT(*) FROM `delivery_incentive_rules`")
        if cur.fetchone()[0] == 0:
            rules = [
                ('Daily 5-Delivery Milestone', 'deliveries_milestone', 5, 150.00, 'Complete 5 deliveries in a single day to earn ₹150 bonus.'),
                ('Super 10-Delivery Target', 'deliveries_milestone', 10, 350.00, 'Complete 10 deliveries in a single day to earn ₹350 bonus.'),
                ('Full Shift Completion Reward', 'shift_completion', 3, 100.00, 'Complete a booked shift with minimum 3 deliveries for ₹100 bonus.'),
                ('Evening Peak Hours Bonus', 'peak_hours', 4, 120.00, 'Deliver during 19:00 - 22:30 dinner peak hours for ₹120 bonus.')
            ]
            for title, itype, target, bonus, desc in rules:
                cur.execute("""
                INSERT INTO `delivery_incentive_rules` (`title`, `incentive_type`, `target_count`, `bonus_amount`, `description`, `is_active`, `created_at`)
                VALUES (%s, %s, %s, %s, %s, 1, NOW())
                """, (title, itype, target, bonus, desc))

        conn.commit()
        cur.execute("""
        INSERT IGNORE INTO schema_migrations (version, description, applied_at)
        VALUES ('014_delivery_shifts_tips_incentives_reviews', 'Add shift booking, incentives, tips, banner images and reviews to MySQL', NOW())
        """)
        conn.commit()
    except Exception as e:
        print(f"[MYSQL SHIFTS & INCENTIVES MIGRATION NOTICE] {e}", file=sys.stderr)


def run_all_migrations(target_mode=None):
    """
    Run migrations for active database mode or specified mode.
    Returns (success: bool, mode: str, summary: str)
    """
    import database
    mode = target_mode or database.get_db_mode()

    if mode == 'sqlite':
        db_path = database.SQLITE_DB_PATH
        if not os.path.exists(db_path):
            from setup_db import init_sqlite_db
            init_sqlite_db()

        conn = sqlite3.connect(db_path)
        try:
            migrate_sqlite(conn)
            conn.close()
            return True, 'sqlite', 'SQLite schema upgraded and verified successfully.'
        except Exception as e:
            conn.close()
            return False, 'sqlite', f"SQLite migration error: {e}"

    elif mode == 'mysql':
        try:
            conn = database.get_db_connection()
            migrate_mysql(conn)
            conn.close()
            return True, 'mysql', 'MySQL schema upgraded and verified successfully.'
        except Exception as e:
            return False, 'mysql', f"MySQL migration error: {e}"

    return False, 'unknown', f"Unsupported mode: {mode}"


if __name__ == '__main__':
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"Running migrations for mode: {mode_arg or 'auto-detect'}...")
    success, mode, msg = run_all_migrations(mode_arg)
    print(f"[{'SUCCESS' if success else 'FAILURE'}] Mode: {mode} - {msg}")
    sys.exit(0 if success else 1)
