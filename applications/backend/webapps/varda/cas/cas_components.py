import importlib
import logging
import re

from rest_framework import status
from urllib import parse

from varda.constants import HETU_REGEX
from varda.misc import hash_string
from varda.monkey_patch import cas_backends, oppija_cas_backends, oppija_cas_views


logger = logging.getLogger(__name__)


class CASBackend(cas_backends.CASBackend):
    pass


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
        valtuudet = query_params.get("valtuudet", None)
        response = function(*args, **kwargs)
        if valtuudet is not None and response.status_code == status.HTTP_302_FOUND and not request.user.is_authenticated:
            # Since CAS-oppija has trouble with storing valtuudet to inner state (OPHVARDA-2181) so we have to attach it
            # to service parameter which is natively available.
            # Note: This is quick fix. Once CAS-oppija handles valtuudet parameter properly this should be reverted.
            location = response["Location"]
            # Decode URL because CAS-Oppija / Suomi.fi encodes URL differently in different scenarios, so we
            # want to normalize the situation here. In case of double encoding, unquote twice.
            location = parse.unquote(parse.unquote(location))
            # Add valtuudet-parameter (with ? so that final redirection works -> /varda/&valtuudet... would need a new
            # matching url, /varda/?valtuudet ends up in /varda/
            location += f'?valtuudet={"false" if valtuudet == "false" else "true"}'
            # Split URL in half from ?service= and encode the latter half once so CAS-Oppija can handle it properly
            location_split = location.split("?service=", 1)
            response["Location"] = f'{location_split[0]}?service={parse.quote(location_split[1], safe="")}'
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
    Backend that handles CAS-Oppija authentication based on view_name.
    """

    oppija_cas_utils = importlib.import_module("varda_oppija_cas_ng.utils")
    get_cas_client = staticmethod(oppija_cas_utils.get_cas_client)

    def authenticate(self, request, ticket, service):
        if request.resolver_match.view_name == "oppija_cas_ng_login":
            # Validate CAS, retrieve username + attributes
            client = self.get_cas_client(service_url=service)
            username, attributes, pgtiou = client.verify_ticket(ticket)
            username = self.sanitize_username(username, attributes)

            # Store attrs in session so are available later
            if request:
                request.session["attributes"] = attributes

            user = oppija_cas_backends.CASBackend._get_or_create_user(self, username)
            return user
        return None

    def sanitize_username(self, username, attributes):
        if re.search(HETU_REGEX, username):
            return f"cas#{hash_string(username)}"

        henkilo_oid = attributes.get("personOid")
        if henkilo_oid:
            return f"cas_oid#{hash_string(henkilo_oid)}"

        # Username max length is 150 characters
        if len(username) > 150:
            logger.error(f"Oppija-CAS username > 150 characters. {attributes}")
            return hash_string(username)

        return username
