import logging

from varda.custom_middleware import local_thread


logger = logging.getLogger(__name__)


def login_handler(sender, user, request, **kwargs):
    from varda.custom_auth import oppija_post_login_handler
    from varda.kayttooikeuspalvelu import set_permissions_for_cas_user

    # We need to check the user permissions for each non-local user explicitly from Kayttooikeuspalvelu.
    if request.method == "GET":
        # GET-request means CAS / POST-request '/api-auth/login/' would mean local account.
        if request.resolver_match.view_name == "oppija_cas_ng_login":
            cas_attrs = request.session.get("attributes", {})
            oppija_post_login_handler(user, cas_attrs)
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


def celery_task_prerun_signal_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra_kwargs):
    # New request_id for celery tasks from celery task_id.
    local_thread.request_id = task_id.replace("-", "")


def celery_task_failure_signal_handler(
    sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra_kwargs
):
    # Log Celery task exceptions
    logger.exception(f"Celery task with ID: {task_id} failed.", exc_info=exception)


def celery_setup_logging_signal_handler(sender=None, loglevel=None, logfile=None, format=None, colorize=None, **kwargs):
    pass
