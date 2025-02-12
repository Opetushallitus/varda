"""
Original location: rest_framework.urls

Login and logout views for the browsable API.

Add these to your root URLconf if you're using the browsable API and
your API requires authentication:

    urlpatterns = [
        ...
        url(r'^auth/', include('rest_framework.urls'))
    ]

You should make sure your authentication settings include `SessionAuthentication`.
"""
from __future__ import unicode_literals

from django.contrib.auth import views
from django.urls import re_path

from . import custom_login_views

import django


if django.VERSION < (1, 11):  # We should never come here
    login = views.login
    login_kwargs = {'template_name': 'rest_framework/login.html'}
    logout = views.logout
else:
    login = custom_login_views.RatelimitedLoginView.as_view(template_name='rest_framework/login.html')
    login_kwargs = {}
    logout = custom_login_views.CustomLogoutView.as_view(template_name='rest_framework/logout.html')


app_name = 'rest_framework'
urlpatterns = [
    re_path(r'^login/$', login, login_kwargs, name='login'),
    re_path(r'^logout/$', logout, name='logout'),
]
