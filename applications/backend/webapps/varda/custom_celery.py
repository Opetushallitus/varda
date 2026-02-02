import logging
import re
from functools import wraps

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from kombu.transport.redis import Channel, Transport

from varda.custom_redis import IAMTokenCredentialProvider


logger = logging.getLogger(__name__)


def custom_shared_task(single_instance=False, timeout_in_seconds=8 * 60):
    """
    Allow rejecting tasks if identical task is already running.
    :param single_instance: Do not allow executing same task again if it is already running with matching ID.
    :param timeout_in_seconds: Time in seconds when lock will be released at latest.
        Should be greater than maximum task run time.
    :return: Decorated shared_task function.
    """

    def _custom_shared_task_decorator(original_function):
        @shared_task
        @wraps(original_function)
        def _custom_shared_task_wrapper(*args, **kwargs):
            # Generate a cache key for this specific task, whitespaces are not allowed
            cache_key_suffix = re.sub(r"\s+", "", f"{args}{kwargs}")
            lock_id = "celery-single-instance-{}-{}".format(original_function.__name__, cache_key_suffix)
            # Uses cache as non-persistent storage which could be culled or crash losing all locks!
            if single_instance and not cache.add(lock_id, "true", timeout_in_seconds):
                # Single instance task exists in cache so it is already running, do not execute it again
                logger.error(f"Task already running with lock_id {lock_id}")
                return None

            try:
                result = original_function(*args, **kwargs)
            finally:
                # Delete cache key whether task is single_instance or not, no error is raised from deletion
                cache.delete(lock_id)
            return result

        return _custom_shared_task_wrapper

    return _custom_shared_task_decorator


class RedisCredentialProviderChannel(Channel):
    def _connparams(self, asynchronous=False):
        # Use credential_provider instead of username and password so that password can be dynamically updated
        params = super()._connparams(asynchronous=asynchronous)

        if "password" in params:
            # Delete password parameter if it exists
            del params["password"]
        if "username" in params:
            # Delete username parameter if it exists
            del params["username"]

        params["credential_provider"] = IAMTokenCredentialProvider(settings.REDIS_REPLICATION_GROUP_ID, settings.REDIS_USER_ID)
        return params


class RedisCredentialProviderTransport(Transport):
    # Replace with custom Channel implementation
    Channel = RedisCredentialProviderChannel
