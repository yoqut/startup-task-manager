"""
AIManager — Development Settings
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Show emails in console during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar (optional, install separately)
INTERNAL_IPS = ["127.0.0.1"]

# Looser CORS in dev
CORS_ALLOW_ALL_ORIGINS = True

# SQLite fallback for quick local dev without Postgres
import os
if os.environ.get("USE_SQLITE") == "true":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
