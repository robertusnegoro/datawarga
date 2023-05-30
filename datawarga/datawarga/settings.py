"""
Django settings for datawarga project.

Generated by 'django-admin startproject' using Django 4.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
from google.oauth2 import service_account
from distutils.util import strtobool
import sys
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DATA_WARGA_SECRET", "")

# SECURITY WARNING: don't run with debug turned on in production!
WG_ENV = os.getenv("WG_ENV", "dev")
WG_TRUSTED = os.getenv("WG_TRUSTED", "")
if WG_ENV == "dev":
    DEBUG = True
    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/4.1/howto/static-files/

    STATIC_URL = "static/"
    STATIC_ROOT = BASE_DIR / "static"
else:
    DEBUG = False
    STATIC_URL = os.getenv("STATIC_URL")
    STATIC_ROOT = os.getenv("STATIC_ROOT")
    CSRF_TRUSTED_ORIGINS = [WG_TRUSTED]

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "kependudukan",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "django_cleanup.apps.CleanupConfig",
    "django.contrib.humanize",
]

CRISPY_TEMPLATE_PACK = "bootstrap4"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "datawarga.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "datawarga.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "ngantridb")
DB_PASS = os.getenv("DB_PASS", "")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "robi")
DB_SSL = strtobool(os.getenv("DB_SSL", "False"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "USER": DB_USER,
        "PASSWORD": DB_PASS,
    }
}

if DB_SSL:
    DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Media settings
MEDIA_URL = "/media/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Apps related settings

KECAMATAN = os.getenv("WG_KECAMATAN", "SETU")
KELURAHAN = os.getenv("WG_KELURAHAN", "BABAKAN")
KOTA = os.getenv("WG_KOTA", "TANGERANG SELATAN")
PROVINSI = os.getenv("WG_PROVINSI", "BANTEN")
RUKUNTANGGA = os.getenv("WG_RT", "006")
RUKUNWARGA = os.getenv("WG_RW", "012")
ALAMAT = os.getenv("WG_ALAMAT", "Jalan Nirwana")
FINANCE_PERIOD_START = int(os.getenv("WG_FINANCE_PERIOD_START", 2018))
IURAN_BULANAN = int(os.getenv("WG_IURAN_BULANAN", 150000))

GENERATE_KOMPLEKS_LIMIT = 200

TIME_ZONE = "Asia/Jakarta"

GOOGLE_SHEETS_CREDS = os.getenv("GOOGLE_CRED_PATH", None)
GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
GOOGLE_SHEETS_SERVICE_ACCOUNT = None
if os.path.isfile(GOOGLE_SHEETS_CREDS):
    GOOGLE_SHEETS_SERVICE_ACCOUNT = (
        service_account.Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDS, scopes=GOOGLE_SHEETS_SCOPES
        )
    )
GOOGLE_DRIVE_USER = os.getenv("GOOGLE_DRIVE_USER", None)
