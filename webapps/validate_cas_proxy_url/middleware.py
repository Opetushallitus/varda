import hashlib
from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings as django_settings


class ValidateCASProxyURL:
    def __init__(self, get_response):
        # If there is no header set to accept
        if not django_settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER:
            raise MiddlewareNotUsed('No CAS Proxy URL header configured')

        self.get_response = get_response

    def __call__(self, request):
        # Validate the proxy url header if provided
        proxyurl = request.META.get('HTTP_' + django_settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER, None)
        hashvalue = request.META.get('HTTP_' + django_settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER + '_HASH', '')
        if (proxyurl is not None and (not hashvalue or
            hashvalue != hashlib.sha1(django_settings.CAS_SALT.encode('utf-8') +
                                      proxyurl.encode('utf-8')).hexdigest())):
            # Header(s) doesn't exist or invalid - remove the header
            del request.META['HTTP_' + django_settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER]

        response = self.get_response(request)
        return response
