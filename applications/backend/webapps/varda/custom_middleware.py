import hashlib
import threading

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.utils.decorators import method_decorator
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.debug import sensitive_post_parameters


local_thread = threading.local()


class AdditionalHeadersMiddleware(MiddlewareMixin):
    """
    Adds additional headers to response
    """
    def __call__(self, *args, **kwargs):
        request = args[0]
        response = super().__call__(*args, **kwargs)

        # Add cache related headers to response so that response data is not cached in the client (browser)
        response['Cache-Control'] = 'no-store, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        # Add Strict-Transport-Security header
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubdomains'

        content_type = response.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            # If response is rendered, add X-XSS-Protection header
            response['X-XSS-Protection'] = '1; mode=block'

        proxied_from_header = request.headers.get('X-Proxied-From', None)
        match proxied_from_header:
            case settings.VARDA_FRONTEND_SECRET:
                proxied_from = 'varda-frontend'
            case _:
                proxied_from = 'varda-backend'
        response['X-Proxied-From'] = proxied_from

        return response


class SensitiveMiddleware(MiddlewareMixin):
    """
    Makes sure certain sensitive post parameters are never included in error messages
    """
    @method_decorator(sensitive_post_parameters(*settings.SENSITIVE_POST_PARAMETERS))
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


class ValidateCASProxyURL(MiddlewareMixin):
    def __init__(self, get_response):
        # If there is no header set to accept
        if not settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER:
            raise MiddlewareNotUsed('No CAS Proxy URL header configured')
        super().__init__(get_response)

    def __call__(self, request):
        # Validate the proxy url header if provided
        proxyurl = request.META.get('HTTP_' + settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER, None)
        hashvalue = request.META.get('HTTP_' + settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER + '_HASH', '')
        if (proxyurl is not None and (not hashvalue or
                                      hashvalue != hashlib.sha1(settings.CAS_API_SALT.encode('utf-8') +
                                                                proxyurl.encode('utf-8')).hexdigest())):
            # Header(s) doesn't exist or invalid - remove the header
            del request.META['HTTP_' + settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER]

        return super().__call__(request)


class LoggingExtraMiddleware(MiddlewareMixin):

    def __call__(self, request):
        # Store request data in local thread, they are later used in logging
        local_thread.request_id = request.META.get('HTTP_X_REQUEST_ID', '')
        local_thread.request_host = request.META.get('HTTP_HOST', '')
        return super().__call__(request)
