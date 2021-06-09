from django.utils.deprecation import MiddlewareMixin


class AdditionalHeadersMiddleware(MiddlewareMixin):
    """
    Adds additional headers to response
    """
    def __call__(self, *args, **kwargs):
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

        return response
