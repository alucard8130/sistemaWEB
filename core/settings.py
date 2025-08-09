from dotenv import load_dotenv

load_dotenv()
from pathlib import Path
import os
import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"
#DEBUG = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "adminsoftheron.onrender.com").split(",")
#ALLOWED_HOSTS = ['*']  # For development purposes, change this in production

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "empresas",
    "principal",
    "locales",
    "areas",
    "clientes",
    "facturacion",
    "proveedores",
    "empleados",
    "gastos",
    "presupuestos",
    "informes_financieros",
    "storages", 
    "caja_chica",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
STATICFILES_DIRS = [BASE_DIR / "static"]

WSGI_APPLICATION = "core.wsgi.application"

#MEDIA_URL = "/media/"
#MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {"default": dj_database_url.config(default=os.getenv("DATABASE_URL"))}


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True") == "True"
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"

STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
#STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/login/"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True


if os.getenv("DEBUG", "False") == "True":
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY_TEST")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY_TEST")
    STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET_TEST")
else:
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")




AWS_ACCESS_KEY_ID = os.getenv('DO_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('DO_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('DO_SPACE_NAME')
AWS_S3_REGION_NAME = os.getenv('DO_REGION') 
AWS_S3_ENDPOINT_URL = f'https://{AWS_S3_REGION_NAME}.digitaloceanspaces.com'
#AWS_S3_ADDRESSING_STYLE = "virtual"
#AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
#AWS_QUERYSTRING_AUTH = False

#STATIC_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/static/'
#STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_REGION_NAME}.digitaloceanspaces.com/'
#MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/'
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

SENTRY_DSN = os.getenv("SENTRY_DSN_KEY")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,  # Puedes bajarlo a 0.1 si no quieres rastreo de performance
    send_default_pii=True,   # Para capturar datos de usuario autenticado
)
