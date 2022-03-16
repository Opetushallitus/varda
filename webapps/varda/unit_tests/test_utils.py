import base64
import datetime
import json
from functools import wraps
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from varda.misc import decrypt_henkilotunnus, hash_string
from varda.models import Henkilo


TEST_CACHE_SETTINGS = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}


def assert_status_code(response, expected_code, extra_message=None):
    if response.status_code != expected_code:
        content = response.content.decode('utf-8')

        try:
            content = json.loads(content)
        except ValueError:
            pass

        extra_message = extra_message and f'{extra_message}: ' or ''
        raise AssertionError(f'{extra_message}Returned status code {response.status_code} != {expected_code}', content)


def assert_validation_error(response, expected_key, expected_error_code, expected_message=None, extra_message=None):
    """
    Assert that the given message can be found in the response's errors.
    The message is expected to be found in the path described by expected_key;
    it can be just a string in case the error is behind a single key,
    for example errors={'expected_key': [{'error_code': expected_error_code, 'description': expected_message}]}.

    In a case where the error is nested behind multiple keys, the
    expected_key can be specified as a list,
    for example errors={'key': {'subkey': [{'error_code': expected_error_code, 'description': expected_message}]}} for
    expected_key=['key', 'subkey'].
    """

    messages = json.loads(response.content)
    if isinstance(expected_key, str):
        messages_for_key = messages.get(expected_key, [])
    else:
        messages_for_key = messages
        # The list for the final subkey is not flattened, as we need it as a list
        for subkey in expected_key[:-1]:
            messages_for_key = messages_for_key.get(subkey, [])

            if isinstance(messages_for_key, dict):
                pass
            elif not isinstance(messages_for_key, list):
                raise ValueError(f'Expected to find a list at {subkey}')
            else:
                # Each key contains a list of error dictionaries;
                # iterate the lists and merge the errors to a single dict.
                merged = {}
                for msg_dict in messages_for_key:
                    for key, value in msg_dict.items():
                        arr = merged.get(key, value.copy())
                        merged[key] = arr
                        arr.append(value)
                messages_for_key = merged
        messages_for_key = messages_for_key.get(expected_key[-1], [])

    for message in messages_for_key:
        if message.get('error_code', '') == expected_error_code:
            if expected_message and message.get('description', '') != expected_message:
                continue
            # Matching error message found
            return

    extra_message = extra_message and f'{extra_message}: ' or ''
    raise AssertionError(f'{extra_message}{expected_key!r}/{expected_message!r} not found in {messages}')


class SetUpTestClient:

    def __init__(self, name):
        self.name = name

    def client(self):
        user = User.objects.filter(username=self.name)[0]
        api_c = APIClient()
        api_c.force_authenticate(user=user)
        return api_c


def base64_encoding(string_to_be_encoded):
    return base64.b64encode(bytes(string_to_be_encoded, 'utf-8')).decode('utf-8')


def mock_admin_user(username):
    if not settings.PRODUCTION_ENV:
        mock_admin = User.objects.get(username=username)
        mock_admin.is_superuser = True
        mock_admin.is_staff = True
        mock_admin.save()


def post_henkilo_to_get_permissions(client, henkilo_id=None, hetu=None, henkilo_oid=None):
    if henkilo_id:
        henkilo = Henkilo.objects.get(id=henkilo_id)
    elif hetu:
        henkilo = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string(hetu))
    elif henkilo_oid:
        henkilo = Henkilo.objects.get(henkilo_oid=henkilo_oid)
    else:
        return

    henkilo_json = {
        'etunimet': henkilo.etunimet,
        'kutsumanimi': henkilo.kutsumanimi,
        'sukunimi': henkilo.sukunimi,
    }
    if henkilo.henkilo_oid:
        henkilo_json['henkilo_oid'] = henkilo.henkilo_oid
    elif henkilo.henkilotunnus:
        henkilo_json['henkilotunnus'] = decrypt_henkilotunnus(henkilo.henkilotunnus)
    else:
        return

    resp = client.post('/api/v1/henkilot/', henkilo_json)
    assert_status_code(resp, status.HTTP_200_OK)


def date_side_effect(*args, **kwargs):
    return datetime.date(*args, **kwargs)


def timedelta_side_effect(*args, **kwargs):
    return datetime.timedelta(*args, **kwargs)


def mock_date_decorator_factory(datetime_path, mock_date):
    def _mock_date_decorator(original_function):
        @wraps(original_function)
        def _mock_date_wrapper(*args, **kwargs):
            with patch(datetime_path) as mock_datetime:
                mock_datetime.date = MagicMock(side_effect=date_side_effect)
                mock_datetime.timedelta = MagicMock(side_effect=timedelta_side_effect)
                mock_datetime.date.today.return_value = datetime.datetime.strptime(mock_date, '%Y-%m-%d').date()
                return original_function(*args, **kwargs)
        return _mock_date_wrapper
    return _mock_date_decorator
