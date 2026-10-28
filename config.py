"""
Configuration file for FOODIE HUNTER
Online Food Delivery & Restaurant Management System
Supports MySQL (XAMPP default) with automatic environment loading.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env if present
basedir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    # Flask secret key for sessions
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or os.environ.get('SECRET_KEY') or 'foodie_hunter_super_secret_key_2026_academic_demo'

    # Database configuration for XAMPP MySQL
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'foodie_hunter')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))

    # Security Gate Passkey for Admin Portal Access (Default: food@1234)
    ADMIN_GATE_PASSWORD = os.environ.get('ADMIN_GATE_PASSWORD', 'food@1234').strip()

    # Direct Demo Admin Access Flow (Default: True for seamless college presentation)
    ADMIN_DIRECT_LOGIN_ENABLED = os.environ.get('ADMIN_DIRECT_LOGIN_ENABLED', '1').strip().lower() in ('1', 'true', 'yes')

    # Google Maps Platform API Key
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip()

    # Razorpay Payment Gateway
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '').strip()
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '').strip()

    # Base project directory
    BASE_DIR = basedir

    # Upload folder for food/restaurant images and verification documents
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    SECURE_DOCS_FOLDER = os.path.join(basedir, 'uploads_secure', 'documents')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size

    # Allowed image and document extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    ALLOWED_DOC_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'webp'}

    # App and Network settings
    HOST = os.environ.get('HOST', '127.0.0.1').strip()
    try:
        PORT = int(os.environ.get('PORT', 5000))
    except (ValueError, TypeError):
        PORT = 5000

    # Debug configuration: default FLASK_DEBUG is 0 (off)
    # Debug mode is forced OFF when binding to 0.0.0.0 unless FLASK_DEBUG=1
    _raw_debug = os.environ.get('FLASK_DEBUG', os.environ.get('DEBUG', '0')).strip().lower()
    DEBUG = _raw_debug in ('1', 'true', 'yes')
    if HOST == '0.0.0.0' and os.environ.get('FLASK_DEBUG', '').strip().lower() not in ('1', 'true', 'yes'):
        DEBUG = False
    TESTING = False

    # Session configuration
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # Business parameters
    TAX_RATE = 0.05
    DEFAULT_DELIVERY_FEE = 40.0
