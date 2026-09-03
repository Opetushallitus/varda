from django.conf import LazySettings, settings as django_settings

_OPPIJA_CAS_SETTINGS = {
    "CAS_SERVER_URL": django_settings.OPPIJA_CAS_SERVER_URL,
    "CAS_APPLY_ATTRIBUTES_TO_USER": django_settings.OPPIJA_CAS_APPLY_ATTRIBUTES_TO_USER,
}

settings = LazySettings()
settings.configure(django_settings, **_OPPIJA_CAS_SETTINGS)
