from rest_framework import status

from varda.monkey_patch import oppija_cas_backends, oppija_cas_views


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
            # Since CAS-oppija has trouble with storing valtuudet to inner state (OPHVARDA-2181) so we have to attach it
            # to service parameter which is natively available. Since service is url encoded we need to use same format.
            # E.g.: /cas-oppija/login?service=http%3A%2F%2Flocalhost%3A8000%2Faccounts%2Fhuoltaja-login%3Fnext%3D%252Fapi%252Foppija%252Fv1%252F
            # Note: This is quick fix. Once CAS-oppija handles valtuudet parameter properly this should be reverted.
            separator = '%26' if '%3F' in response['Location'] else '%3F'
            response['Location'] += f'{separator}valtuudet%3D{"false" if valtuudet == "false" else "true"}'
        return response
    return wrap_decorator


# No need to override logout view settings since we can use the same one as normal CAS
# No need for fallback view since it's unlikely Varda would need to validate proxy granting tickets.
class OppijaCasLoginView(oppija_cas_views.LoginView):
    """
    django_cas_ng does not support multiple cas filters so we need to instantiate one by ourselves.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get = get_login_forward_decorator(self.get)


class OppijaCASBackend(oppija_cas_backends.CASBackend):
    """
    Backend that validates cas tickets against cas-oppija.
    """

    def authenticate(self, request, ticket, service):
        if request.resolver_match.view_name == 'oppija_cas_ng_login':
            # By changing the service parameter above (OPHVARDA-2181) we have to manually add it or we can't validate
            # service ticket (ST) because service differs from the one the ST was granted to.
            if (valtuudet := request.GET.get('valtuudet')) is not None:
                service += f'&valtuudet={"true" if valtuudet == "true" else "false"}'
            return super().authenticate(request, ticket, service)
        return None
