import json


def assert_status_code(response, expected_code, extra_message=None):
    if response.status_code != expected_code:
        content = response.content.decode('utf-8')

        try:
            content = json.loads(content)
        except ValueError:
            pass

        extra_message = extra_message and f'{extra_message}: ' or ''
        raise AssertionError(f'{extra_message}Returned status code {response.status_code} != {expected_code}', content)
