from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-r_w=juq-m-add*fydoj37q(7!jpk_2fouwbiklzl$)nzf7d$gd"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "garantie",
    "commission",
    "recouvrement",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

import platform as _platform
_driver = "ODBC Driver 17 for SQL Server" if _platform.system() == "Linux" else "ODBC Driver 13 for SQL Server"

DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": "solidis",
        "HOST": "172.20.24.37",
        "USER": "Minonja",
        "PASSWORD": "Minonja",
        "OPTIONS": {
            "driver": _driver,
        },
    }
}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Indian/Antananarivo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
