import os
import dj_database_url
from .base import *

# In production, DEBUG must always be False
DEBUG = False

# Read allowed hosts from environment or Render's external hostname
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Additional allowed hosts passed via env comma-separated
CUSTOM_HOSTS = os.environ.get('ALLOWED_HOSTS')
if CUSTOM_HOSTS:
    ALLOWED_HOSTS.extend([h.strip() for h in CUSTOM_HOSTS.split(',') if h.strip()])

# CSRF trusted origins for HTTPS submissions on Render
CSRF_TRUSTED_ORIGINS = []
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
CUSTOM_CSRF = os.environ.get('CSRF_TRUSTED_ORIGINS')
if CUSTOM_CSRF:
    CSRF_TRUSTED_ORIGINS.extend([c.strip() for c in CUSTOM_CSRF.split(',') if c.strip()])

# ── DATABASE CONFIGURATION (Neon / PostgreSQL) ──────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True
        )
    }

# ── WHITENOISE STATIC FILE STORAGE ──────────────────────────────────────────
# Insert WhiteNoiseMiddleware directly after SecurityMiddleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
