from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.debug import sensitive_post_parameters


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

        if proxied_from := request.headers.get('X-Proxied-From'):
            response['X-Proxied-From'] = proxied_from
        else:
            response['X-Proxied-From'] = 'varda-backend'

        return response


class SensitiveMiddleware(MiddlewareMixin):
    """
    Makes sure certain sensitive post parameters are never included in error messages
    """
    @method_decorator(sensitive_post_parameters(*settings.SENSITIVE_POST_PARAMETERS))
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
