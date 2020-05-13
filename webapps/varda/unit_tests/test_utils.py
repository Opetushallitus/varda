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
