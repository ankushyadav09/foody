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

    # Google Maps Platform API Key
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip()

    # Razorpay Payment Gateway
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '').strip()
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '').strip()

    # Upload folder for food/restaurant images
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size

    # Allowed image extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # App settings
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
    TESTING = False

    # Session configuration
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # Business parameters
    TAX_RATE = 0.05
    DEFAULT_DELIVERY_FEE = 40.0
