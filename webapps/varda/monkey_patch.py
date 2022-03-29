from varda.cas.cas_settings import settings as oppija_cas_settings
from varda.cas.misc_cas import is_local_url_decorator
from varda.misc import load_in_new_module, TemporaryObject


def init_django_cas_ng_views(views_module):
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


cas_views = load_in_new_module('django_cas_ng.views', 'varda_cas_ng.views')
init_django_cas_ng_views(cas_views)


oppija_cas_backends = load_in_new_module('django_cas_ng.backends', 'varda_oppija_cas_ng.backends')
oppija_cas_utils = load_in_new_module('django_cas_ng.utils', 'varda_oppija_cas_ng.utils')
oppija_cas_views = load_in_new_module('varda_cas_ng.views', 'varda_oppija_cas_ng.views')
init_django_cas_ng_views(oppija_cas_views)

# Oppija CAS has different settings
oppija_cas_utils.django_settings = oppija_cas_settings

oppija_cas_backends.settings = oppija_cas_settings
oppija_cas_backends.get_cas_client = oppija_cas_utils.get_cas_client

oppija_cas_views.settings = oppija_cas_settings
oppija_cas_views.get_cas_client = oppija_cas_utils.get_cas_client
oppija_cas_views.get_redirect_url = oppija_cas_utils.get_redirect_url
oppija_cas_views.get_service_url = oppija_cas_utils.get_service_url


# Monkey patch knox.views so that user_logged_in and user_logged_out signals are not sent
knox_views = load_in_new_module('knox.views', 'varda_knox.views')
knox_views.user_logged_in = TemporaryObject(send=lambda *args, **kwargs: None)
knox_views.user_logged_out = TemporaryObject(send=lambda *args, **kwargs: None)
