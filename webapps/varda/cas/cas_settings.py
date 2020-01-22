from django.conf import settings as django_settings, LazySettings

_OPPIJA_CAS_SETTINGS = {
    "CAS_SERVER_URL": django_settings.OPPIJA_CAS_SERVER_URL,
    "CAS_CREATE_USER": django_settings.OPPIJA_CAS_CREATE_USER,
    "CAS_LOGIN_MSG": django_settings.OPPIJA_CAS_LOGGED_MSG,
    "CAS_LOGGED_MSG": django_settings.OPPIJA_CAS_LOGGED_MSG,
    "CAS_VERSION": django_settings.OPPIJA_CAS_VERSION,
    "CAS_RETRY_LOGIN": django_settings.OPPIJA_CAS_RETRY_LOGIN,
    "CAS_APPLY_ATTRIBUTES_TO_USER": django_settings.OPPIJA_CAS_APPLY_ATTRIBUTES_TO_USER
}

settings = LazySettings()
settings.configure(django_settings, **_OPPIJA_CAS_SETTINGS)
