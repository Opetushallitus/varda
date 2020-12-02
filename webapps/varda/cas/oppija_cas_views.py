import importlib.util
import sys

from rest_framework import status

from varda.cas.cas_settings import settings


def load_in_new_module(library_name, name):
    spec = importlib.util.find_spec(library_name)
    cas_oppija_specific_library = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cas_oppija_specific_library)
    sys.modules['varda_cas_oppija_' + name] = cas_oppija_specific_library
    del spec
    return cas_oppija_specific_library


# Loading in separate module to avoid conflicting with django settings
cas_oppija_views = load_in_new_module('django_cas_ng.views', 'views')
cas_oppija_utils = load_in_new_module('django_cas_ng.utils', 'utils')
cas_oppija_backends = load_in_new_module('django_cas_ng.backends', 'backends')

# Overriding these for caller-id decoration
cas = load_in_new_module('cas', 'cas')
requests_api = load_in_new_module('requests.api', 'requests_api')


def get_with_callerid(url, params=None, **kwargs):
    kwargs.setdefault('allow_redirects', True)
    old_headers = kwargs.get('headers', {})
    headers = {**old_headers, **{'Caller-Id': 'csc.varda'}}
    return requests_api.request('get', url, params=params, headers=headers, **kwargs)


requests_api.get = get_with_callerid
cas.requests = requests_api


def get_login_forward_decorator(function):
    """
    This needs to be dynamically wrapped unless we want create whole new view with it's own dependencies that use
    decorated version of get_cas_client function that either adds valtuudet query param true or false through
    extra_login_params kwarg.
    :param function: decorated function
    :return: decorator function
    """
    def wrap_decorator(*args, **kwargs):
        request = args[0]
        query_params = request.GET
        valtuudet = query_params.get('valtuudet', None)
        response = function(*args, **kwargs)
        if valtuudet is not None and response.status_code == status.HTTP_302_FOUND and not request.user.is_authenticated:
            separator = '&' if '?' in response['Location'] else '?'
            response['Location'] += f'{separator}valtuudet={"false" if valtuudet == "false" else "true"}'
        return response
    return wrap_decorator


class OppijaCasLoginView(cas_oppija_views.LoginView):
    """
    django_cas_ng does not support multiple cas filters so we need to instantiate one by ourselves.
    """
    def __init__(self, **kwargs):
        super(OppijaCasLoginView, self).__init__(**kwargs)

        # Monkey patching django settings super class module uses
        cas_oppija_views.settings = settings
        cas_oppija_utils.django_settings = settings
        cas_oppija_views.get_cas_client = cas_oppija_utils.get_cas_client
        self.get = get_login_forward_decorator(self.get)


# No need to override logout view settings since we can use the same one as virkailija-cas

# No need for fallback view since it's unlikely varda would need to validate proxy granting tickets.


class OppijaCASBackend(cas_oppija_backends.CASBackend):
    """
    Backend that validates cas tickets against cas-oppija.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Monkey patch utils import to use our version
        cas_oppija_utils.django_settings = settings
        cas_oppija_utils.CASClient = cas.CASClient
        cas_oppija_backends.get_cas_client = cas_oppija_utils.get_cas_client
        cas_oppija_backends.settings = settings

    def authenticate(self, request, ticket, service):
        if request.resolver_match.view_name == 'oppija_cas_ng_login':
            return super().authenticate(request, ticket, service)
        return None
