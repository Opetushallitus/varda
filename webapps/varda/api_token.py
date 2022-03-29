import os
from urllib.parse import urlparse

from django.conf import settings
from rest_framework import status

from varda.monkey_patch import knox_views


class KnoxLoginView(knox_views.LoginView):
    def post(self, request, format=None):
        response = super().post(request, format=format)
        if response.status_code == status.HTTP_403_FORBIDDEN:
            # Maximum amount of tokens exceeded, delete the oldest one
            request.user.auth_token_set.order_by('created').first().delete()
            response = super().post(request, format=format)
        return response


def set_api_token_cookie(request, response, next_page):
    """
    Send cookie (i.e. modify the response) only for allowed redirects/domains.
    """
    allowed_client_domain = None
    if settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER:
        proxyurl = request.META.get('HTTP_' + settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER, None)
        if proxyurl is not None:
            parsed_uri = urlparse(proxyurl)
            allowed_client_domain = '{uri.netloc}'.format(uri=parsed_uri)

    if allowed_client_domain is None:
        allowed_client_domain = get_allowed_client_domain(next_page)

    if allowed_client_domain:
        secure = True
        if allowed_client_domain == 'localhost':
            allowed_client_domain = None
            # local Angular-testing environment 'http://localhost:4200' doesn't support TLS
            secure = False
        token = KnoxLoginView().post(request).data['token']
        response.set_cookie(key='token', value=token, max_age=30, expires=None,
                            path='/', domain=allowed_client_domain, secure=secure, httponly=False, samesite='Lax')


def get_allowed_client_domain(next_page):
    """
    Cookie-settings require domain where the cookie is readable.
    VARDA_CLIENT_DOMAIN env-variable tells which client-domain can make requests to the backend-app.
    The only exception to this is the localhost testing environments, where we support 'localhost' domain as well.
    """
    next_page_allowed = False  # First check if the requested 'next_page' is allowed.
    if any(sub_url in next_page for sub_url in get_allowed_redirects()):
        next_page_allowed = True

    allowed_client_domain = os.getenv('VARDA_CLIENT_DOMAIN', '')
    env_type = os.getenv('VARDA_ENVIRONMENT_TYPE', '')

    if next_page_allowed and (env_type == 'env-varda-prod' or env_type == 'env-varda-testing'):
        return allowed_client_domain
    elif next_page_allowed:
        return 'localhost'
    return ''


def get_allowed_redirects():
    """
    Do not allow redirects from Django-auth to unknown external sites.
    """
    env_type = os.getenv('VARDA_ENVIRONMENT_TYPE', '')
    if env_type == 'env-varda-prod' or env_type == 'env-varda-testing':
        return ['varda']
    return ['http://localhost']
