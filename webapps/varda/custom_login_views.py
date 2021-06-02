import logging
import os

from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth import views
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from ratelimit.decorators import ratelimit
from rest_framework import status
from urllib.parse import urlparse


# Get an instance of a logger
logger = logging.getLogger(__name__)


class CustomLogoutView(views.LogoutView):
    """
    We want to log out from application and CAS.
    """
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        auth_logout(request)
        next_page = self.get_next_page()
        if next_page:
            # Redirect to this page until the session has been cleared.
            # return HttpResponseRedirect(next_page)  \\// Original line
            return HttpResponseRedirect('/accounts/logout?next=' + next_page)
        return super(views.LogoutView, self).dispatch(request, *args, **kwargs)


class RatelimitedLoginView(views.LoginView):
    """
    Current limit is 50 login requests/hour per IP.
    This might need more evaluation in case many active users behind NAT for example.
    """
    @method_decorator(ratelimit(key='header:x-real-ip',
                                rate=settings.CUSTOM_LOGIN_RATELIMIT['header_x_real_ip'],
                                block=False))
    @method_decorator(ratelimit(key='post:username', rate=settings.CUSTOM_LOGIN_RATELIMIT['post_form'],
                                method=['POST'], block=False))
    @method_decorator(ratelimit(key='post:password', rate=settings.CUSTOM_LOGIN_RATELIMIT['post_form'],
                                method=['POST'], block=False))
    @method_decorator(sensitive_post_parameters())  # Original decorator
    @method_decorator(csrf_protect)                 # Original decorator
    @method_decorator(never_cache)                  # Original decorator
    def dispatch(self, request, *args, **kwargs):
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            if 'HTTP_X_REAL_IP' in request.META:
                logger.error("Ratelimit was reached! HTTP_X_REAL_IP=" + request.META['HTTP_X_REAL_IP'] + ".")
            return render(request, '429.html', status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self):
        """
        Use a custom redirect for varda-frontend
        """
        request = self.request
        if request is not None:
            allowed_redirects_list = get_allowed_redirects()
            if request.method == 'POST' and 'HTTP_REFERER' in request.META:  # HTTP_REFERER e.g. http://localhost:8000/api-auth/login/?next=/api/v1/:
                splitted_referer = request.META['HTTP_REFERER'].split("?next=")
                if len(splitted_referer) == 2 and any(sub_url in splitted_referer[1] for sub_url in allowed_redirects_list):
                    redirect_url = splitted_referer[1]
                    return redirect_url
            elif request.method == 'GET':
                splitted_redirect_url = request.get_full_path().split("?next=")  # full_path() e.g. /api-auth/login/?next=/api/v1/
                if len(splitted_redirect_url) == 2 and any(sub_url in splitted_redirect_url[1] for sub_url in allowed_redirects_list):
                    redirect_url = splitted_redirect_url[1]
                    return redirect_url
        return super().get_redirect_url()

    def form_valid(self, form):
        """Disallow admin-access from non-allowed IP-addresses."""
        request = self.request
        user = form.get_user()
        if user.is_staff and 'HTTP_X_REAL_IP' in request.META and check_if_ip_not_allowed_for_admin_access(request):
            logger.error("Security warning! " + user.username + " tried to log in from disallowed IP: HTTP_X_REAL_IP=" + request.META['HTTP_X_REAL_IP'] + ".")
            return render(request, '403.html', status=status.HTTP_403_FORBIDDEN)
        """Security check complete. Log the user in."""
        auth_login(request, user)
        """Use a custom redirect for varda-frontend."""
        redirect_url = self.get_success_url()
        response = HttpResponseRedirect(redirect_url)
        set_cookie(request, response, redirect_url)
        return response


def get_allowed_redirects():
    """
    Do not allow redirects from Django-auth to unknown external sites.
    """
    env_type = os.getenv('VARDA_ENVIRONMENT_TYPE', '')
    if env_type == "env-varda-prod" or env_type == "env-varda-testing":
        return ['varda']  # TODO: allow redirects only to frontend-proxy
    return ['http://localhost']


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

    if next_page_allowed and (env_type == "env-varda-prod" or env_type == "env-varda-testing"):
        return allowed_client_domain
    elif next_page_allowed:
        return "localhost"
    return ""


def set_cookie(request, response, next_page):
    """
    Send cookie (i.e. modify the response) only for allowed redirects/domains.
    """
    allowed_client_domain = None
    if settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER:
        proxyurl = request.META.get('HTTP_' + settings.CAS_ACCEPT_PROXY_URL_FROM_HEADER, None)
        if (proxyurl is not None):
            parsed_uri = urlparse(proxyurl)
            allowed_client_domain = '{uri.netloc}'.format(uri=parsed_uri)

    if allowed_client_domain is None:
        allowed_client_domain = get_allowed_client_domain(next_page)

    if allowed_client_domain:
        secure = True
        if allowed_client_domain == "localhost":
            allowed_client_domain = None
            secure = False  # local Angular-testing environment 'http://localhost:4200' doesn't support TLS
        response.set_cookie(key='token', value=get_token(request.user), max_age=30, expires=None,
                            path='/', domain=allowed_client_domain, secure=secure, httponly=False, samesite='Lax')
    else:
        pass


def get_token(user):
    from rest_framework.authtoken.models import Token
    token = Token.objects.get_or_create(user=user)
    return token[0].key


def check_if_ip_not_allowed_for_admin_access(request):
    from ipaddress import ip_network, ip_address
    allowed_ips = []
    # We have the allowed IP-addresses listed in nginx-conf
    f = open(os.path.dirname(__file__) + '/../../conf/nginx/blockips.conf')
    file_lines = f.readlines()
    f.close()

    for line in file_lines:
        if "allow" in line:  # e.g. "allow 127.0.0.1;\n"
            allowed_ip = line.split(" ")[1].split(";")[0]
            allowed_ips.append(allowed_ip)

    for ip in allowed_ips:
        if len(ip) > 3 and ip[-3] == "/":  # network address, ending with e.g. /24
            try:
                net = ip_network(ip)
            except ValueError:
                logger.error("ip_network is set wrong: " + ip)
                continue
            if ip_address(request.META['HTTP_X_REAL_IP']) in net:
                return False  # This is OK, admin-user is allowed to access from this IP-network
        elif ip == request.META['HTTP_X_REAL_IP']:
            return False  # This is OK, admin-user is allowed to access from this IP-address
    return True
