import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

SECRET_KEY = "shopdesk-prod-2024-secret"
DATABASE = os.path.join(INSTANCE_DIR, "shopdesk.db")
UPLOAD_DIR = os.path.join(INSTANCE_DIR, "uploads")
PREFS_DIR = os.path.join(INSTANCE_DIR, "prefs")

ADMIN_EMAIL = "admin@shopdesk.local"
ADMIN_PASSWORD = "Admin@12345"

PAYMENT_API_URL = "https://payments.example.com/v1/charge"
PAYMENT_API_KEY = "sk_live_51Hq3JdKq9fXb7T2mPzVn4wLc"

SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = None
