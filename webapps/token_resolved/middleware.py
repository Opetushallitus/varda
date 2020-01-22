import base64
import binascii
import re

from django.contrib.auth.models import User


class AddTokenHeaderMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        username = user.username
        if 'HTTP_AUTHORIZATION' in request.environ.keys():
            raw_value = request.environ['HTTP_AUTHORIZATION']
            if raw_value.startswith("Basic "):
                username = self.get_basic_auth_username(raw_value, user)
            else:
                token = raw_value.strip().split(' ')
                if len(token) == 2 and token[0].lower() == 'token':
                    userlist = User.objects.filter(auth_token=token[1])
                    if userlist and len(userlist) > 0:
                        username = userlist[0].username
        username = self.hide_oppija_cas_sensitive_data(username)
        response = self.get_response(request)
        response['X-Token-Resolved'] = username
        return response

    def get_basic_auth_username(self, authorization_string, user):
        encoded_basic_auth = authorization_string.split("Basic ")
        if len(encoded_basic_auth) == 2:
            try:
                encoded_username_password = encoded_basic_auth[1]
                username_password = base64.b64decode(encoded_username_password, validate=True).decode('utf-8', 'ignore')
            except (binascii.Error, UnicodeDecodeError):
                return user.username
            return username_password.split(":")[0]
        else:
            return user.username

    def hide_oppija_cas_sensitive_data(self, username):
        hetu_regex = '\\d{6}[A+\\-]\\d{3}[0-9A-FHJ-NPR-Y]'
        if username:
            if not isinstance(username, str):
                username = str(username)
            if re.search('suomi\\.fi#{}#{}'.format(hetu_regex, hetu_regex), username):
                return re.compile(hetu_regex).sub('xxxxxxxxxxx', username)
        return username
