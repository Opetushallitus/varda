from __future__ import unicode_literals

import json
import logging
import os

import requests
import uuid

from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils.translation import gettext_lazy as _
from django.utils import timezone as django_timezone
from django_cas_ng.signals import cas_user_logout
from rest_framework import exceptions
from rest_framework.authentication import BasicAuthentication
from rest_framework.authtoken.models import Token

from varda import kayttooikeuspalvelu
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.kayttooikeuspalvelu import set_service_user_permissions
from varda.oph_yhteiskayttopalvelu_autentikaatio import get_authentication_header
from varda.models import Z3_AdditionalCasUserFields, Z7_AdditionalUserFields, LoginCertificate
from varda.permissions import get_certificate_login_info
from webapps.celery import app
from celery.signals import task_prerun
from log_request_id import local


logger = logging.getLogger(__name__)


def login_handler(sender, user, request, **kwargs):
    """
    Actions to be performed for the logged in user:
    - We need to check the user permissions for each non-local user explicitly from Kayttooikeuspalvelu.
    """
    if request.method == 'GET':  # GET-request means CAS / POST-request '/api-auth/login/' would mean local account.
        if request.resolver_match.view_name == 'oppija_cas_ng_login':
            _oppija_post_login_handler(user)
        else:
            kayttooikeuspalvelu.set_permissions_for_cas_user(user.id)


def _oppija_post_login_handler(user):
    """
    Handles oppija cas logged in user privileges givin parent. ALlows login even if lapsi or huoltaja oid doesn't exist.
    :param user: user with attributes personOid and impersonatorPersonOid
    :return: None
    """
    if getattr(user, 'personOid', None):
        # If user has impersonatorPersonOid-attribute, user has logged in with Valtuudet
        kayttajatyyppi = (Kayttajatyyppi.OPPIJA_CAS_VALTUUDET.value
                          if hasattr(user, 'impersonatorPersonOid')
                          else Kayttajatyyppi.OPPIJA_CAS.value)

        if kayttajatyyppi == Kayttajatyyppi.OPPIJA_CAS_VALTUUDET.value:
            etunimi = getattr(user, 'impersonatorGivenName', '')
            sukunimi = getattr(user, 'impersonatorSn', '')
            # Huoltaja OID
            henkilo_oid = getattr(user, 'impersonatorPersonOid', None)
            # Lapsi OID
            huollettava_oid_list = [user.personOid]
        else:
            etunimi = getattr(user, 'givenName', '')
            sukunimi = getattr(user, 'sn', '')
            henkilo_oid = user.personOid
            huollettava_oid_list = None

        # external service validates permissions for user
        Z3_AdditionalCasUserFields.objects.update_or_create(user=user,
                                                            defaults={
                                                                'etunimet': etunimi,
                                                                'kutsumanimi': etunimi,
                                                                'sukunimi': sukunimi,
                                                                'henkilo_oid': henkilo_oid,
                                                                'huollettava_oid_list': huollettava_oid_list,
                                                                'kayttajatyyppi': kayttajatyyppi,
                                                            })


def logout_handler(sender, user, request, **kwargs):
    """
    user - The user instance that just logged out or None if the user was not authenticated.

    Actions to be performed for the logged out user:
    - We need to delete the auth-token from the user.
    """
    if user is not None:
        Token.objects.get_or_create(user=user)[0].delete()


def cas_logout_handler(sender, user, session, ticket, **kwargs):
    if user is None or user.is_anonymous:
        pass
    else:
        Token.objects.get_or_create(user=user)[0].delete()


def celery_task_prerun_signal_handler(task_id, **kwargs):
    """
    Check for periodic tasks: we want to run periodic task only for varda-0 POD.
    See Kubernetes Statefulesets for more information.
    Additionally: New request_id for celery tasks from celery task_id.
    """
    splitted_hostname = os.environ['HOSTNAME'].split('-')
    if len(splitted_hostname) == 2:
        hostname = splitted_hostname[1]  # e.g. varda-0 --> 0
    else:
        hostname = None

    local.request_id = task_id.replace('-', '')
    if 'periodic_task' in kwargs and kwargs['periodic_task'] and hostname != '0':
        """
        If not the first (0) POD, cancel periodic task

        TODO: Seems like revoking is currently not working: https://github.com/celery/celery/issues/4300
        However, this is not a huge deal, since we stop running the task for others than pod-0.
        """
        app.control.revoke(task_id)


# Catch signals
user_logged_in.connect(login_handler)
user_logged_out.connect(logout_handler)
cas_user_logout.connect(cas_logout_handler)
task_prerun.connect(celery_task_prerun_signal_handler)


class CustomBasicAuthentication(BasicAuthentication):
    """
    Custom: allow basic authentication only for fetching token (apikey)
    This is used ONLY for palvelukayttaja-authentication.
    """
    def _authenticate_and_get_omattiedot(self, userid, password):
        service_name = 'kayttooikeus-service'
        try:
            omattiedot_url = settings.OPINTOPOLKU_DOMAIN + '/' + service_name + '/henkilo/current/omattiedot'
            r = requests.get(omattiedot_url, headers=get_authentication_header(service_name, userid, password))
        except requests.exceptions.RequestException as e:
            logger.error('User could not log in. Username: {}, Error: {}.'.format(userid, e))
            msg = _('Connection problems. Please try again later.')
            raise exceptions.AuthenticationFailed(msg)

        if r.status_code == 200:  # user was authenticated successfully from cas
            pass
        elif r.status_code == 401:
            msg = _('Authentication failed.')
            raise exceptions.AuthenticationFailed(msg)
        else:
            logger.error('User authentication failed with status_code: ' + str(r.status_code))
            msg = _('Authentication failed.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            omattiedot = json.loads(r.content)
        except json.JSONDecodeError:
            logger.error('Cas-authentication failed. Invalid json.')
            msg = _('An internal error occured. Team is investigating.')
            raise exceptions.AuthenticationFailed(msg)

        # Check we have all the necessary keys in the json
        required_keys = set(('kayttajaTyyppi', 'username', 'oidHenkilo', 'organisaatiot'))
        if set(omattiedot) >= required_keys:
            pass  # Correct. We have all info.
        else:
            logger.error('Cas-authentication failed. Missing parameters in json.')
            msg = _('An internal error occured. Team is investigating.')
            raise exceptions.AuthenticationFailed(msg)

        cas_henkilo_kayttajaTyyppi = omattiedot['kayttajaTyyppi']
        if cas_henkilo_kayttajaTyyppi != 'PALVELU':
            msg = _('Did not find an active palvelukayttaja-profile.')
            raise exceptions.AuthenticationFailed(msg)

        return omattiedot

    def authenticate_credentials(self, userid, password, request=None):
        """
        Basic authentication, in the first place, is only allowed for fetching the apikey-token.
        Never in any other situation. Except "local staff users", as commented below.
        """
        if request is not None:
            path = request.get_full_path()
            if path == '/api/user/apikey/':
                pass
            else:
                msg = _('Basic authentication not allowed.')
                raise exceptions.AuthenticationFailed(msg)

        """
        Allow fetching api-key for local staff users.

        https://github.com/encode/django-rest-framework/blob/3e956df6eb7e3b645d334fec372ad7f8a487d765/rest_framework/authentication.py#L89
        """
        credentials = {
            get_user_model().USERNAME_FIELD: userid,
            'password': password
        }
        user = authenticate(request=request, **credentials)
        if user is not None and user.is_active and user.is_staff:
            return (user, None)

        """
        Authenticate user via CAS, and get 'omattiedot' for the user.
        """
        omattiedot = self._authenticate_and_get_omattiedot(userid, password)
        cas_henkilo_kayttajaTyyppi = omattiedot['kayttajaTyyppi']

        cas_username = omattiedot['username']
        cas_henkilo_oid = omattiedot['oidHenkilo']
        cas_henkilo_organisaatiot = omattiedot['organisaatiot']

        # Do we have the user in our DB. If not, create it.
        try:
            user = User.objects.get(username=cas_username)
        except User.DoesNotExist:
            user = User.objects.create_user(username=cas_username, password=uuid.uuid4().hex)
            user.set_unusable_password()  # Because the user is authenticated via cas, we need to set the varda-password unusable
        except User.MultipleObjectsReturned:  # This should never be possible
            logger.error('Multiple of user-instances found.')
            msg = _('An internal error occured. Team is investigating.')
            raise exceptions.AuthenticationFailed(msg)

        if user is None:
            raise exceptions.AuthenticationFailed(_('Invalid username/password.'))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        """
        Should we ratelimit the user. We do not want to let the users call this api-endpoint too frequently.
        There should be no use case to fetch the token more frequently than ~once a day.
        """
        self.ratelimit_basic_auth_user(user)

        """
        Add/Update miscellaneous user-fields
        """
        Z3_AdditionalCasUserFields.objects.update_or_create(user=user, defaults={'kayttajatyyppi': cas_henkilo_kayttajaTyyppi, 'henkilo_oid': cas_henkilo_oid})

        set_service_user_permissions(user, permissions_by_organization=cas_henkilo_organisaatiot)

        is_cert_auth, common_name = get_certificate_login_info(request)
        # We are making sure user authenticates this way before accessing certificate required apis. This is cleared
        # on regular login.
        if is_cert_auth:
            LoginCertificate.objects.filter(common_name=common_name).update(user=user)
        else:
            LoginCertificate.objects.filter(user=user).update(user=None)

        return user, None

    def ratelimit_basic_auth_user(self, user):
        try:
            user_details_obj = Z3_AdditionalCasUserFields.objects.get(user=user)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            user_details_obj = None

        if user_details_obj is not None:
            user_details_last_modified = user_details_obj.last_modified
            time_now = datetime.now(timezone.utc)
            time_difference_in_seconds = (time_now - user_details_last_modified) / timedelta(seconds=1)
            if time_difference_in_seconds < settings.BASIC_AUTHENTICATION_LOGIN_INTERVAL_IN_SECONDS:
                available_in_seconds = int(settings.BASIC_AUTHENTICATION_LOGIN_INTERVAL_IN_SECONDS - time_difference_in_seconds)
                raise exceptions.Throttled(wait=available_in_seconds)


class PasswordExpirationModelBackend(ModelBackend):
    def user_can_authenticate(self, user):
        if user.is_staff and user.has_usable_password() and (settings.PRODUCTION_ENV or settings.QA_ENV):
            # Only check password expiration in production and QA where actual emails can be sent
            additional_user_fields = Z7_AdditionalUserFields.objects.filter(user=user).first()
            if not additional_user_fields:
                # AdditionalUserFields for this user are missing, force password change
                return False
            expiration_limit = django_timezone.now() - timedelta(days=200)
            if additional_user_fields.password_changed_timestamp < expiration_limit:
                # Password has not been changed in a defined time, force password change
                return False

        return super(PasswordExpirationModelBackend, self).user_can_authenticate(user)
