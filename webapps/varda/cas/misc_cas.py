from functools import wraps
from urllib import parse

from django.contrib.auth import REDIRECT_FIELD_NAME


def is_local_url_decorator(original_function):
    """
    Decorator that is used to override django_cas_ng.views.is_local_url. next-parameter can be used to redirect user to
    a third party website when three or more forward slashes are used (e.g. ?next=///google.com), so we need to check
    that it is not the case.
    :param original_function: django_cas_ng.views.is_local_url
    :return: decorator function
    """
    @wraps(original_function)
    def is_local_url_wrapper(*args, **kwargs):
        url = args[1]
        if url.startswith('///'):
            return False
        return original_function(*args, **kwargs)
    return is_local_url_wrapper


def get_service_url_decorator(original_function, get_redirect_url, cas_settings):
    """
    Decorator that is used to override django_cas_ng.views.is_local_url. service_url is fetched from header in
    Opintopolku environments.
    :param original_function: django_cas_ng.utils.get_service_url
    :param get_redirect_url: django_cas_ng.utils.get_redirect_url
    :param cas_settings: django.conf.settings
    :return: decorator function
    """
    @wraps(original_function)
    def get_service_url_wrapper(*args, **kwargs):
        request = args[0]
        redirect_to = kwargs.get('redirect_to', None)
        if (cas_settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER and
                (service := request.META.get(f'HTTP_{cas_settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER}', False))):
            if not cas_settings.CAS_STORE_NEXT:
                if '?' in service:
                    service += '&'
                else:
                    service += '?'
                service += parse.urlencode({
                    REDIRECT_FIELD_NAME: redirect_to or get_redirect_url(request)
                })
            return service
        return original_function(*args, **kwargs)
    return get_service_url_wrapper
