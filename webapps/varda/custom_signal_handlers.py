import os

from webapps.celery import app
from log_request_id import local


def login_handler(sender, user, request, **kwargs):
    from varda.custom_auth import oppija_post_login_handler
    from varda.kayttooikeuspalvelu import set_permissions_for_cas_user

    # We need to check the user permissions for each non-local user explicitly from Kayttooikeuspalvelu.
    if request.method == 'GET':
        # GET-request means CAS / POST-request '/api-auth/login/' would mean local account.
        if request.resolver_match.view_name == 'oppija_cas_ng_login':
            oppija_post_login_handler(user)
        else:
            set_permissions_for_cas_user(user.id)


def logout_handler(sender, user, request, **kwargs):
    if user and not user.is_anonymous:
        # Logging out via Django LogoutView, we don't know which token was used so delete them all
        user.auth_token_set.all().delete()


def cas_logout_handler(sender, user, session, ticket, **kwargs):
    if user and not user.is_anonymous:
        # Logging out via Opintopolku CAS, we don't know which token was used so delete them all
        user.auth_token_set.all().delete()


def celery_task_prerun_signal_handler(task_id, **kwargs):
    """
    Check for periodic tasks: we want to run periodic task only for varda-0 POD.
    See Kubernetes Statefulesets for more information.
    Additionally: New request_id for celery tasks from celery task_id.
    """
    splitted_hostname = os.environ['HOSTNAME'].split('-')
    if len(splitted_hostname) == 2:
        # e.g. varda-0 --> 0
        hostname = splitted_hostname[1]
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
