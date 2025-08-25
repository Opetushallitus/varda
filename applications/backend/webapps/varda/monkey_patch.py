import re

from django.conf import settings

from varda.cas.cas_settings import settings as oppija_cas_settings
from varda.cas.cas_misc import get_redirect_url_decorator, get_service_url_decorator, is_local_url_decorator
from varda.constants import HETU_REGEX
from varda.misc import hash_string, load_in_new_module, TemporaryObject


def init_django_cas_ng_utils(utils_module, cas_settings):
    utils_module.django_settings = cas_settings

    # Override get_redirect_url to normalize URL by unquoting it
    # CAS-Oppija / Suomi.fi encodes URL differently in different scenarios
    utils_module.get_redirect_url = get_redirect_url_decorator(utils_module.get_redirect_url)

    # Override get_service_url to enable CAS_ACCEPT_PROXY_URL_FROM_HEADER
    utils_module.get_service_url = get_service_url_decorator(utils_module.get_service_url,
                                                             utils_module.get_redirect_url, cas_settings)


def init_django_cas_ng_views(views_module, utils_module, cas_settings):
    views_module.settings = cas_settings

    # Override utils imports
    views_module.get_cas_client = utils_module.get_cas_client
    views_module.get_redirect_url = utils_module.get_redirect_url
    views_module.get_service_url = utils_module.get_service_url

    # Override is_local_url to disallow redirection to third party sites
    views_module.is_local_url = is_local_url_decorator(views_module.is_local_url)

    class LoginView(views_module.LoginView):
        def successful_login(self, request, next_page):
            from varda.api_token import set_api_token_cookie

            response = super().successful_login(request, next_page)
            # Set API token to a cookie so it can be fetched by UI
            set_api_token_cookie(request, response, next_page)
            return response

    # Override LoginView so that API token is set to a cookie after login
    views_module.LoginView = LoginView


def init_django_cas_ng_backends(backends_module, utils_module, cas_settings):
    backends_module.settings = cas_settings

    # Override utils imports
    backends_module.get_cas_client = utils_module.get_cas_client

    class CASBackend(backends_module.CASBackend):
        def clean_username(self, username):
            username = super().clean_username(username)

            # Hash username if CAS username contains hetu (CAS oppija)
            if re.search(HETU_REGEX, username):
                username = f'cas#{hash_string(username)}'
            return username

    # Override CASBackend so that username is hashed
    backends_module.CASBackend = CASBackend


cas_utils = load_in_new_module('django_cas_ng.utils', 'varda_cas_ng.utils')
cas_views = load_in_new_module('django_cas_ng.views', 'varda_cas_ng.views')
cas_backends = load_in_new_module('django_cas_ng.backends', 'varda_cas_ng.backends')
init_django_cas_ng_utils(cas_utils, settings)
init_django_cas_ng_views(cas_views, cas_utils, settings)
init_django_cas_ng_backends(cas_backends, cas_utils, settings)


oppija_cas_utils = load_in_new_module('django_cas_ng.utils', 'varda_oppija_cas_ng.utils')
oppija_cas_views = load_in_new_module('varda_cas_ng.views', 'varda_oppija_cas_ng.views')
oppija_cas_backends = load_in_new_module('django_cas_ng.backends', 'varda_oppija_cas_ng.backends')
init_django_cas_ng_utils(oppija_cas_utils, oppija_cas_settings)
init_django_cas_ng_views(oppija_cas_views, oppija_cas_utils, oppija_cas_settings)
init_django_cas_ng_backends(oppija_cas_backends, oppija_cas_utils, oppija_cas_settings)


# Monkey patch knox.views so that user_logged_in and user_logged_out signals are not sent
knox_views = load_in_new_module('knox.views', 'varda_knox.views')
knox_views.user_logged_in = TemporaryObject(send=lambda *args, **kwargs: None)
knox_views.user_logged_out = TemporaryObject(send=lambda *args, **kwargs: None)
