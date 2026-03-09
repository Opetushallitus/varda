from __future__ import unicode_literals

import json
import logging

import requests
import uuid

from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone as django_timezone
from knox.auth import TokenAuthentication
from rest_framework import exceptions
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.throttling import AnonRateThrottle

from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.kayttooikeuspalvelu import set_service_user_permissions
from varda.oph_yhteiskayttopalvelu_autentikaatio import get_authentication_header
from varda.models import Z3_AdditionalCasUserFields, Z7_AdditionalUserFields, LoginCertificate
from varda.permissions import get_certificate_login_info


logger = logging.getLogger(__name__)


def oppija_post_login_handler(user, cas_attrs):
    """
    Handles oppija cas logged in user privileges givin parent. Allows login even if lapsi or huoltaja oid doesn't exist.
    :param user: user with attributes personOid and impersonatorPersonOid
    :return: None
    """
    if cas_attrs.get("personOid"):
        # If user has impersonatorPersonOid-attribute, user has logged in with Valtuudet
        kayttajatyyppi = (
            Kayttajatyyppi.OPPIJA_CAS_VALTUUDET.value if "impersonatorPersonOid" in cas_attrs else Kayttajatyyppi.OPPIJA_CAS.value
        )

        if kayttajatyyppi == Kayttajatyyppi.OPPIJA_CAS_VALTUUDET.value:
            # impersonator-fields are in invalid array string format, e.g. '[Testi]', so remove [ and ] characters
            etunimi = cas_attrs.get("impersonatorGivenName", "").replace("[", "").replace("]", "")
            sukunimi = cas_attrs.get("impersonatorSn", "").replace("[", "").replace("]", "")

            # Huoltaja OID
            henkilo_oid = cas_attrs.get("impersonatorPersonOid")
            if isinstance(henkilo_oid, str):
                henkilo_oid = henkilo_oid.replace("[", "").replace("]", "")

            # Lapsi OID
            huollettava_oid_list = [cas_attrs.get("personOid")]
        else:
            if "givenName" in cas_attrs:
                etunimi = cas_attrs["givenName"]
            elif "firstName" in cas_attrs:
                etunimi = cas_attrs["firstName"]
            else:
                etunimi = ""

            if "sn" in cas_attrs:
                sukunimi = cas_attrs["sn"]
            elif "familyName" in cas_attrs:
                sukunimi = cas_attrs["familyName"]
            else:
                sukunimi = ""

            henkilo_oid = cas_attrs.get("personOid")
            huollettava_oid_list = None

        # external service validates permissions for user
        Z3_AdditionalCasUserFields.objects.update_or_create(
            user=user,
            defaults={
                "etunimet": etunimi,
                "kutsumanimi": etunimi,
                "sukunimi": sukunimi,
                "henkilo_oid": henkilo_oid,
                "huollettava_oid_list": huollettava_oid_list,
                "kayttajatyyppi": kayttajatyyppi,
            },
        )


class AuthenticateAnonThrottleMixin(AnonRateThrottle):
    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}

    def authenticate(self, request):
        """
        Function used to override rest_framework.authentication.BaseAuthentication.authenticate.
        Rest Framework only performs throttle after request has been authenticated, which means that throttle never
        kicks in if user uses invalid credentials. This function performs anonymous throttle before authentication.
        """
        # Check throttle before trying to authenticate
        allow_request = self.allow_request(request, None)
        if not allow_request:
            # Throttle exceeded
            wait_time = self.wait()
            raise Throttled(wait=wait_time)

        result = None
        exception = None
        try:
            result = super().authenticate(request)
        except AuthenticationFailed as e:
            exception = e

        if isinstance(self, CustomSessionAuthentication) and result is None and settings.SESSION_COOKIE_NAME in request.COOKIES:
            # Authentication was successful if no exception is raised. However, SessionAuthentication does not raise
            # exception, so make sure that if session cookie is present, result can't be None.
            exception = AuthenticationFailed()

        if exception:
            # Authentication has failed
            # Re-fetch history to combat race condition
            self.history = self.cache.get(self.key, [])
            # Update entry to cache so that it is counted against throttle in following requests
            self.history.insert(0, self.now)
            self.cache.set(self.key, self.history, self.duration)
            # Raise AuthenticationFailed exception
            raise exception

        # Authentication was successful and was not throttled
        return result

    def throttle_success(self):
        """
        Override SimpleRateThrottle.throttle_success so that timestamp is not added to cache here.
        Timestamp is only added on failed authentication request to prevent race condition from occurring
        in high volume production environment.
        """
        self.cache.set(self.key, self.history, self.duration)
        return True


class CustomBasicAuthentication(AuthenticateAnonThrottleMixin, BasicAuthentication):
    """
    Custom: allow basic authentication only for fetching token (apikey)
    This is used ONLY for palvelukayttaja-authentication.
    """

    def _authenticate_and_get_omattiedot(self, userid, password):
        service_name = "kayttooikeus-service"
        try:
            omattiedot_url = settings.OPINTOPOLKU_DOMAIN + "/" + service_name + "/henkilo/current/omattiedot"
            r = requests.get(omattiedot_url, headers=get_authentication_header(service_name, userid, password))
        except requests.exceptions.RequestException as e:
            logger.error("User could not log in. Username: {}, Error: {}.".format(userid, e))
            msg = _("Connection problems. Please try again later.")
            raise exceptions.AuthenticationFailed(msg)

        if r.status_code == 200:  # user was authenticated successfully from cas
            pass
        elif r.status_code == 401:
            msg = _("Authentication failed.")
            raise exceptions.AuthenticationFailed(msg)
        else:
            logger.error("User authentication failed with status_code: " + str(r.status_code))
            msg = _("Authentication failed.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            omattiedot = json.loads(r.content)
        except json.JSONDecodeError:
            logger.error("Cas-authentication failed. Invalid json.")
            msg = _("An internal error occured. Team is investigating.")
            raise exceptions.AuthenticationFailed(msg)

        # Check we have all the necessary keys in the json
        required_keys = set(("kayttajaTyyppi", "username", "oidHenkilo", "organisaatiot"))
        if set(omattiedot) >= required_keys:
            pass  # Correct. We have all info.
        else:
            logger.error("Cas-authentication failed. Missing parameters in json.")
            msg = _("An internal error occured. Team is investigating.")
            raise exceptions.AuthenticationFailed(msg)

        cas_henkilo_kayttajaTyyppi = omattiedot["kayttajaTyyppi"]
        if cas_henkilo_kayttajaTyyppi != Kayttajatyyppi.PALVELU.value:
            msg = _("Did not find an active palvelukayttaja-profile.")
            raise exceptions.AuthenticationFailed(msg)

        return omattiedot

    def authenticate_credentials(self, userid, password, request=None):
        """
        Basic authentication, in the first place, is only allowed for fetching the apikey-token.
        Never in any other situation. Except "local staff users", as commented below.
        """
        if request is not None:
            path = request.get_full_path()
            if path == "/api/user/apikey/":
                pass
            else:
                msg = _("Basic authentication not allowed.")
                raise exceptions.AuthenticationFailed(msg)

        """
        Allow fetching api-key for local staff users.

        https://github.com/encode/django-rest-framework/blob/3e956df6eb7e3b645d334fec372ad7f8a487d765/rest_framework/authentication.py#L89
        """
        credentials = {get_user_model().USERNAME_FIELD: userid, "password": password}
        user = authenticate(request=request, **credentials)
        if user is not None and user.is_active and user.is_staff:
            return (user, None)

        """
        Authenticate user via CAS, and get 'omattiedot' for the user.
        """
        omattiedot = self._authenticate_and_get_omattiedot(userid, password)
        cas_henkilo_kayttajaTyyppi = omattiedot["kayttajaTyyppi"]

        cas_username = omattiedot["username"]
        cas_henkilo_oid = omattiedot["oidHenkilo"]

        # Do we have the user in our DB. If not, create it.
        try:
            user = User.objects.get(username=cas_username)
        except User.DoesNotExist:
            user = User.objects.create_user(username=cas_username, password=uuid.uuid4().hex)
            user.set_unusable_password()  # Because the user is authenticated via cas, we need to set the varda-password unusable
        except User.MultipleObjectsReturned:  # This should never be possible
            logger.error("Multiple of user-instances found.")
            msg = _("An internal error occured. Team is investigating.")
            raise exceptions.AuthenticationFailed(msg)

        if user is None:
            raise exceptions.AuthenticationFailed(_("Invalid username/password."))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        """
        Add/Update miscellaneous user-fields
        """
        Z3_AdditionalCasUserFields.objects.update_or_create(
            user=user, defaults={"kayttajatyyppi": cas_henkilo_kayttajaTyyppi, "henkilo_oid": cas_henkilo_oid}
        )

        set_service_user_permissions(user, cas_henkilo_oid)

        is_cert_auth, common_name = get_certificate_login_info(request)
        # We are making sure user authenticates this way before accessing certificate required apis. This is cleared
        # on regular login.
        if is_cert_auth:
            LoginCertificate.objects.filter(common_name=common_name).update(user=user)
        else:
            LoginCertificate.objects.filter(user=user).update(user=None)

        return user, None


class CustomSessionAuthentication(SessionAuthentication):
    pass


class CustomTokenAuthentication(TokenAuthentication):
    pass


class PasswordExpirationModelBackend(ModelBackend):
    def user_can_authenticate(self, user):
        if user.is_staff and user.has_usable_password() and (settings.PRODUCTION_ENV or settings.QA_ENV):
            # Only check password expiration in production and QA where actual emails can be sent
            additional_user_fields = Z7_AdditionalUserFields.objects.filter(user=user).first()
            if not additional_user_fields:
                # AdditionalUserFields for this user are missing, force password change
                return False
            expiration_limit = django_timezone.now() - timedelta(days=200)
            # ANONYMIZATION_CHECKER_USER_NAME does automatic CI-verification. Do not require password_change.
            if (
                additional_user_fields.password_changed_timestamp < expiration_limit
                and user.username != settings.ANONYMIZATION_CHECKER_USER_NAME
            ):
                # Password has not been changed in a defined time, force password change
                return False

        return super(PasswordExpirationModelBackend, self).user_can_authenticate(user)
