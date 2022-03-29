import logging
import os

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import views
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from ratelimit.decorators import ratelimit
from rest_framework import status


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
                logger.error('Ratelimit was reached! HTTP_X_REAL_IP=' + request.META['HTTP_X_REAL_IP'] + '.')
            return render(request, '429.html', status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
            return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Disallow admin-access from non-allowed IP-addresses."""
        request = self.request
        user = form.get_user()
        if user.is_staff and 'HTTP_X_REAL_IP' in request.META and check_if_ip_not_allowed_for_admin_access(request):
            logger.error('Security warning! ' + user.username + ' tried to log in from disallowed IP: HTTP_X_REAL_IP=' + request.META['HTTP_X_REAL_IP'] + '.')
            return render(request, '403.html', status=status.HTTP_403_FORBIDDEN)
        return super().form_valid(form)


def check_if_ip_not_allowed_for_admin_access(request):
    from ipaddress import ip_network, ip_address
    allowed_ips = []
    # We have the allowed IP-addresses listed in nginx-conf
    f = open(os.path.dirname(__file__) + '/../../conf/nginx/blockips.conf')
    file_lines = f.readlines()
    f.close()

    for line in file_lines:
        if 'allow' in line:  # e.g. 'allow 127.0.0.1;\n'
            allowed_ip = line.split(' ')[1].split(';')[0]
            allowed_ips.append(allowed_ip)

    for ip in allowed_ips:
        if len(ip) > 3 and ip[-3] == '/':  # network address, ending with e.g. /24
            try:
                net = ip_network(ip)
            except ValueError:
                logger.error('ip_network is set wrong: ' + ip)
                continue
            if ip_address(request.META['HTTP_X_REAL_IP']) in net:
                return False  # This is OK, admin-user is allowed to access from this IP-network
        elif ip == request.META['HTTP_X_REAL_IP']:
            return False  # This is OK, admin-user is allowed to access from this IP-address
    return True
