"""
database.py – Dual-mode Database connection manager for Foody Hunters.
Primary : MySQL via XAMPP (localhost:3306, user: root, password: '', db: foody_hunters)
Fallback: SQLite (foody_hunters.db) if MySQL is not running.
Ensures zero-crash execution on any Windows PC or college presentation setup.
"""

import sys
import os
import re
import sqlite3
from datetime import datetime, timedelta
from config import Config

# Track active database mode
DB_MODE = None  # 'mysql' or 'sqlite'
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'foody_hunters.db')


def _test_mysql():
    """Check if MySQL server is reachable."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT,
            connection_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False


_MIGRATIONS_RUN = set()


def _ensure_db_ready(mode):
    """Ensure active database schema is migrated and up-to-date."""
    if mode in _MIGRATIONS_RUN:
        return
    try:
        import migrations
        migrations.run_all_migrations(mode)
        _MIGRATIONS_RUN.add(mode)
    except Exception as e:
        print(f"[{mode.upper()} MIGRATION WARNING] {e}", file=sys.stderr)


def get_db_mode():
    """Detect whether MySQL or SQLite should be used."""
    global DB_MODE
    if DB_MODE is not None:
        return DB_MODE

    # Check for explicit override in environment or .env
    env_mode = os.environ.get('DB_MODE') or os.environ.get('DB_ENGINE')
    if env_mode and env_mode.strip().lower() in ('sqlite', 'mysql'):
        DB_MODE = env_mode.strip().lower()
    elif _test_mysql():
        DB_MODE = 'mysql'
    else:
        DB_MODE = 'sqlite'

    _ensure_db_ready(DB_MODE)
    return DB_MODE


def _ensure_mysql_db_ready():
    """Ensure database exists in MySQL and is migrated."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[MYSQL NOTICE] {e}", file=sys.stderr)


def get_db_connection():
    """Returns database connection based on active engine."""
    mode = get_db_mode()
    if mode == 'mysql':
        import mysql.connector
        return mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT,
            autocommit=False
        )
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        _register_sqlite_functions(conn)
        return conn


def _register_sqlite_functions(conn):
    """Register custom SQLite functions to emulate MySQL functions."""
    conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    conn.create_function("CURDATE", 0, lambda: datetime.now().strftime("%Y-%m-%d"))
    conn.create_function("DATE", 1, lambda val: str(val)[:10] if val else None)
    conn.create_function("CONCAT", -1, lambda *args: ''.join(str(a) if a is not None else '' for a in args))
    
    def _date_format(val, fmt):
        if not val:
            return None
        val_str = str(val)[:19]
        for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(val_str, f)
                py_fmt = fmt.replace('%Y', '{Y}').replace('%m', '{m}').replace('%d', '{d}')
                return dt.strftime('%Y-%m') if '%Y-%m' in fmt else dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        return str(val_str)[:7]

    conn.create_function("DATE_FORMAT", 2, _date_format)


def _convert_query_for_sqlite(query):
    """Convert MySQL query syntax to SQLite syntax."""
    # Convert %s placeholders to ?
    q = query.replace('%s', '?')
    # Replace DATE_SUB(NOW(), INTERVAL 7 DAY) with datetime('now', '-7 days')
    q = re.sub(r"DATE_SUB\s*\(\s*NOW\s*\(\s*\)\s*,\s*INTERVAL\s+(\d+)\s+DAY\s*\)", r"datetime('now', '-\1 days')", q, flags=re.IGNORECASE)
    # Convert ON DUPLICATE KEY UPDATE for coupons to SQLite ON CONFLICT
    if re.search(r"INSERT\s+INTO\s+coupons", q, re.IGNORECASE) and re.search(r"ON\s+DUPLICATE\s+KEY\s+UPDATE", q, re.IGNORECASE):
        q = re.sub(r"ON\s+DUPLICATE\s+KEY\s+UPDATE", "ON CONFLICT(code) DO UPDATE SET", q, flags=re.IGNORECASE)
    return q


def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    """
    Generic helper to run parameterized queries safely.
    Compatible with both MySQL and SQLite.
    """
    mode = get_db_mode()
    conn = get_db_connection()

    if mode == 'mysql':
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            cursor.execute(query, params or ())
            if commit:
                conn.commit()
                return cursor.lastrowid
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            return True
        except Exception as e:
            conn.rollback()
            print(f"[MYSQL ERROR] {e}\nQuery: {query}\nParams: {params}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()
    else:
        # SQLite execution
        sqlite_q = _convert_query_for_sqlite(query)
        cursor = conn.cursor()
        try:
            cursor.execute(sqlite_q, params or ())
            if commit:
                conn.commit()
                return cursor.lastrowid
            if fetchone:
                row = cursor.fetchone()
                return dict(row) if row else None
            if fetchall:
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            return True
        except Exception as e:
            conn.rollback()
            print(f"[SQLITE ERROR] {e}\nQuery: {sqlite_q}\nParams: {params}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()


def execute_many(query, params_list):
    """Batch execute parameterized query."""
    mode = get_db_mode()
    conn = get_db_connection()
    if mode == 'mysql':
        cursor = conn.cursor()
        try:
            cursor.executemany(query, params_list)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"[BATCH MYSQL ERROR] {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()
    else:
        sqlite_q = _convert_query_for_sqlite(query)
        cursor = conn.cursor()
        try:
            cursor.executemany(sqlite_q, params_list)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"[BATCH SQLITE ERROR] {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()


class db_transaction:
    """
    Context manager for atomic multi-statement database transactions.
    Supports both MySQL and SQLite engines.
    Commits on successful completion; rolls back completely on any error.
    """
    def __init__(self):
        self.mode = get_db_mode()
        self.conn = get_db_connection()
        self.cursor = None

    def __enter__(self):
        if self.mode == 'mysql':
            self.cursor = self.conn.cursor(dictionary=True, buffered=True)
        else:
            self.cursor = self.conn.cursor()
        return self

    def execute(self, query, params=None):
        params = params or ()
        if self.mode == 'mysql':
            self.cursor.execute(query, params)
            return self.cursor.lastrowid
        else:
            sqlite_q = _convert_query_for_sqlite(query)
            self.cursor.execute(sqlite_q, params)
            return self.cursor.lastrowid

    def fetchone(self, query, params=None):
        params = params or ()
        if self.mode == 'mysql':
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        else:
            sqlite_q = _convert_query_for_sqlite(query)
            self.cursor.execute(sqlite_q, params)
            row = self.cursor.fetchone()
            return dict(row) if row else None

    def fetchall(self, query, params=None):
        params = params or ()
        if self.mode == 'mysql':
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        else:
            sqlite_q = _convert_query_for_sqlite(query)
            self.cursor.execute(sqlite_q, params)
            rows = self.cursor.fetchall()
            return [dict(r) for r in rows]

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            if self.cursor:
                try:
                    self.cursor.close()
                except Exception:
                    pass
            try:
                self.conn.close()
            except Exception:
                pass

