import json
import base64

from django.contrib.auth.models import User
from rest_framework.test import APIClient


def assert_status_code(response, expected_code, extra_message=None):
    if response.status_code != expected_code:
        content = response.content.decode('utf-8')

        try:
            content = json.loads(content)
        except ValueError:
            pass

        extra_message = extra_message and f'{extra_message}: ' or ''
        raise AssertionError(f'{extra_message}Returned status code {response.status_code} != {expected_code}', content)


def assert_validation_error(expected_key, expected_message, response, extra_message=None):
    """
    Assert that the given message can be found in the response's errors.
    The message is expected to be found in the path described by expected_key;
    it can be just a string in case the error is behind a single key,
    for example errors={'expected_key': ['expected_message']}.

    In a case where the error is nested behind multiple keys, the
    expected_key can be specified as a list,
    for example errors={'key': [{'subkey': 'expected_message'}]} for
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

            if not isinstance(messages_for_key, list):
                raise ValueError(f'Expected to find a list at {subkey}')

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

    if expected_message not in messages_for_key:
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
    return base64.b64encode(bytes(string_to_be_encoded, "utf-8")).decode("utf-8")
