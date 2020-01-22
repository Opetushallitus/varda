import importlib.util
import sys

from varda.cas.cas_settings import settings

# Loading in separate module to avoid conflicting with django settings
VIEWS_SPEC = importlib.util.find_spec('django_cas_ng.views')
cas_oppija_views = importlib.util.module_from_spec(VIEWS_SPEC)
VIEWS_SPEC.loader.exec_module(cas_oppija_views)
sys.modules['varda_cas_oppija_views'] = cas_oppija_views
del VIEWS_SPEC

UTILS_SPEC = importlib.util.find_spec('django_cas_ng.utils')
cas_oppija_utils = importlib.util.module_from_spec(UTILS_SPEC)
UTILS_SPEC.loader.exec_module(cas_oppija_utils)
sys.modules['varda_cas_oppija_utils'] = cas_oppija_utils
del UTILS_SPEC

BACKENDS_SPEC = importlib.util.find_spec('django_cas_ng.backends')
cas_oppija_backends = importlib.util.module_from_spec(BACKENDS_SPEC)
BACKENDS_SPEC.loader.exec_module(cas_oppija_backends)
sys.modules['varda_cas_oppija_backends'] = cas_oppija_backends
del BACKENDS_SPEC


class OppijaCasLoginView(cas_oppija_views.LoginView):
    """
    django_cas_ng does not support multiple cas filters so we need to instantiate one by ourselves.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Monkey patching django settings super class module uses
        cas_oppija_views.settings = settings
        cas_oppija_utils.django_settings = settings
        cas_oppija_views.get_cas_client = cas_oppija_utils.get_cas_client


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
        cas_oppija_backends.get_cas_client = cas_oppija_utils.get_cas_client
        cas_oppija_backends.settings = settings

    def authenticate(self, request, ticket, service):
        if request.resolver_match.view_name == 'oppija_cas_ng_login':
            return super().authenticate(request, ticket, service)
        return None
