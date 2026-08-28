import os
from pathlib import Path

import dj_database_url
import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"
#DEBUG = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS","gesac.up.railway.app,adminsoftheron.onrender.com,www.gesac.com.mx").split(",")
#ALLOWED_HOSTS = ["192.168.0.159","*",]  # For development purposes, change this in production

CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://gesac.up.railway.app,https://adminsoftheron.onrender.com,https://gesac.com.mx,https://www.gesac.com.mx",
).split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "empresas.apps.EmpresasConfig",
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
    "widget_tweaks",
    "rest_framework",
    "adminpanel",
    "publicidad",
    "conciliaciones",
    "estacionamiento",
    "cobros_estado_cuenta",
    "acceso_empresas",
    "asistente_premium",
    "traspasos",
    "amenidades",
    "catalogos",
    "sanitarios",
    "nomina",
    "gestion_cobranza",
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
                "empresas.context_processors.empresa_actual",  # nuevo context processor para exponer la empresa actual en todos los templates
                "acceso_empresas.context_processors.alertas_portal_context",  # nuevo context processor para exponer las alertas del portal en todos los templates
                "principal.context_processors.stripe_context",  # nuevo context processor para exponer la clave pública de Stripe en todos los templates
            ],
        },
    },
]


TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
STATICFILES_DIRS = [BASE_DIR / "static"]

WSGI_APPLICATION = "core.wsgi.application"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


####################BASE DE DATOS########################

# desarrollo sqlite
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# desarrollo postgres
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.getenv("DB_NAME"),  # nombre de tu base clonada
#         "USER": os.getenv("DB_USER"),  # tu usuario de postgres
#         "PASSWORD": os.getenv("DB_PASSWORD"),  # tu contraseña
#         "HOST": os.getenv("DB_HOST", "localhost"),
#         "PORT": os.getenv("DB_PORT", "5432"),
#     }
# }

# produccion
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///" + os.path.join(BASE_DIR, "db.sqlite3")
    )
}


#######################EMAIL CONFIGURATION########################

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",  # default: SMTP (Render/local)
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True") == "True"
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
SENDGRID_SANDBOX_MODE_IN_DEBUG = False


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


LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_L10N = True
USE_TZ = True


STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/login/"


if os.getenv("DEBUG", "True") == "False":
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY_TEST")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY_TEST")
    STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET_TEST")
    ## STRIPE_PORTAL_PRICES ADMINISTRADORES Y/O COMITE
    STRIPE_PORTAL_WEBHOOK_SECRET = os.getenv("STRIPE_PORTAL_WEBHOOK_SECRET_TEST")
    STRIPE_PORTAL_PRICES = {
        'basico': os.getenv("STRIPE_PORTAL_PRICE_BASICO_TEST"),
        'profesional': os.getenv("STRIPE_PORTAL_PRICE_PROFESIONAL_TEST"),
        'enterprise': os.getenv("STRIPE_PORTAL_PRICE_ENTERPRISE_TEST"),
    }
else:
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")
    ## STRIPE_PORTAL_PRICES ADMINISTRADORES Y/O COMITE
    STRIPE_PORTAL_WEBHOOK_SECRET = os.getenv("STRIPE_PORTAL_WEBHOOK_SECRET")
    STRIPE_PORTAL_PRICES = {
        'basico': os.getenv("STRIPE_PORTAL_PRICE_BASICO"),
        'profesional': os.getenv("STRIPE_PORTAL_PRICE_PROFESIONAL"),
        'enterprise': os.getenv("STRIPE_PORTAL_PRICE_ENTERPRISE"),
    }


AWS_ACCESS_KEY_ID = os.getenv("DO_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("DO_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("DO_SPACE_NAME")
AWS_S3_REGION_NAME = os.getenv("DO_REGION")
AWS_S3_ENDPOINT_URL = os.getenv("DO_ENDPOINT_URL")
AWS_S3_ADDRESSING_STYLE = "virtual"
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = "public-read"
AWS_QUERYSTRING_AUTH = False
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.nyc3.digitaloceanspaces.com"


SENTRY_DSN = os.getenv("SENTRY_DSN_KEY")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,  # Puedes bajarlo a 0.1 si no quieres rastreo de performance
    send_default_pii=True,  # Para capturar datos de usuario autenticado
)

FACTURAMA_USER = os.getenv("FACTURAMA_USER")
FACTURAMA_PASSWORD = os.getenv("FACTURAMA_PASSWORD")


PORTAL_PAGOS_URL = os.getenv(
    "PORTAL_PAGOS_URL", "https://www.gesac.com.mx/visitante/login/"
)

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
