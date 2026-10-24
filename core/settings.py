import os
from pathlib import Path

import dj_database_url  # noqa: F401, RUF100
import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG se controla desde .env (local: DEBUG=True para pruebas). En Render no existe => False.
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "gesac.up.railway.app,adminsoftheron.onrender.com,www.gesac.com.mx",
).split(",")
if DEBUG:
    # Solo en desarrollo
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "192.168.0.159", ".ngrok-free.dev"]

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
    "notificaciones_sistema",
    "usuarios_extra",
    "arrendamientos",
    "escuelas",
    "leasing",
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
    "core.middleware.MembresiaBloqueoMiddleware", # Middleware para bloquear el acceso a usuarios con membresía vencida
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
                "notificaciones_sistema.context_processors.notificaciones_sistema_context",  # nuevo context processor para exponer las notificaciones del sistema en todos los templates
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

# Render define RENDER=true automaticamente: ahi se usa DATABASE_URL (produccion).
# En local se usa la base clonada configurada con DB_* en el .env.
if os.getenv("RENDER"):
    DATABASES = {
        "default": dj_database_url.config(
            default="sqlite:///" + os.path.join(BASE_DIR, "db.sqlite3")
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),  # nombre de tu base clonada
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }


#######################EMAIL CONFIGURATION########################

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",  # default: SMTP (Render/local)
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))  # noqa: PLW1508
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True") == "True"
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
DEFAULT_FROM_EMAIL_MEMBRESIAS = os.getenv("DEFAULT_FROM_EMAIL_MEMBRESIAS")
SENDGRID_SANDBOX_MODE_IN_DEBUG = False
BANXICO_TOKEN = os.environ.get('BANXICO_TOKEN', '')
HUBSPOT_WEBHOOK_TOKEN = os.environ.get('HUBSPOT_WEBHOOK_TOKEN', '')


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


# STRIPE_MODE=live|test fija el modo de forma explicita (recomendado en Render).
# Si no esta definida se conserva la logica anterior (DEBUG=False explicito => test).
_stripe_mode = os.getenv("STRIPE_MODE", "").strip().lower()
if _stripe_mode in ("live", "test"):
    _usar_stripe_test = _stripe_mode == "test"
else:
    _usar_stripe_test = os.getenv("DEBUG", "True") == "False"

if _usar_stripe_test:
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
# Archivos privados: se sirven con URL firmada que caduca (comprobantes, estados de cuenta, CFDI)
AWS_DEFAULT_ACL = "private"
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600

# Archivos subidos (MEDIA): a Spaces cuando hay credenciales; si no, disco local (desarrollo).
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    _default_storage = {"BACKEND": "storages.backends.s3.S3Storage"}
else:
    _default_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": _default_storage,
    # Igual que hoy en la practica (STATICFILES_STORAGE se ignora en Django 5.x)
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


SENTRY_DSN = os.getenv("SENTRY_DSN_KEY")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,  # Para capturar datos de usuario autenticado
)

FACTURAMA_USER = os.getenv("FACTURAMA_USER")
FACTURAMA_PASSWORD = os.getenv("FACTURAMA_PASSWORD")
# FACTURAMA_ENV=production usa api.facturama.mx; cualquier otro valor (o vacio) = sandbox.
FACTURAMA_ENV = os.getenv("FACTURAMA_ENV", "sandbox").strip().lower()
FACTURAMA_HOST = (
    "https://api.facturama.mx"
    if FACTURAMA_ENV == "production"
    else "https://apisandbox.facturama.mx"
)
FACTURAMA_TIMEOUT = 30  # segundos


PORTAL_PAGOS_URL = os.getenv(
    "PORTAL_PAGOS_URL", "https://www.gesac.com.mx/visitante/login/"
)

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True

# Endurecimiento HTTPS: solo en Render (Render define RENDER=true automaticamente),
# para no romper el login en local aunque ahi DEBUG=False.
if os.getenv("RENDER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}