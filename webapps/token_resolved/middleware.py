import base64
import binascii
import re

from knox.auth import compare_digest
from knox.crypto import hash_token
from knox.models import AuthToken
from knox.settings import CONSTANTS


class AddTokenHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        username = user.username
        if 'HTTP_AUTHORIZATION' in request.environ.keys():
            # Try to get username based on Basic or Token authentication value even if authentication fails
            raw_value = request.environ['HTTP_AUTHORIZATION']
            raw_value_list = raw_value.split(' ')
            raw_value_list = [raw_value_item.strip() for raw_value_item in raw_value_list]
            if len(raw_value_list) == 2:
                auth_method = raw_value_list[0]
                auth_value = raw_value_list[1]
                match auth_method.lower():
                    case 'basic':
                        username = self.get_basic_auth_username(auth_value, user)
                    case 'token':
                        username = self.get_token_auth_username(auth_value, user)
        username = self.hide_oppija_cas_sensitive_data(username)
        response = self.get_response(request)
        response['X-Token-Resolved'] = username
        return response

    def get_basic_auth_username(self, auth_value, user):
        try:
            encoded_username_password = auth_value
            username_password = base64.b64decode(encoded_username_password, validate=True).decode('utf-8', 'ignore')
        except (binascii.Error, UnicodeDecodeError):
            return user.username
        return username_password.split(':')[0]

    def get_token_auth_username(self, auth_value, user):
        # Core functionality of knox.auth.TokenAuthentication.authenticate_credentials
        # AuthToken objects are not stored plain text so get tokens that match with start of auth_value
        # and compare digests
        for auth_token in AuthToken.objects.filter(token_key=auth_value[:CONSTANTS.TOKEN_KEY_LENGTH]):
            try:
                digest = hash_token(auth_value)
                if compare_digest(digest, auth_token.digest):
                    return auth_token.user.username
            except (TypeError, binascii.Error):
                # Don't raise error, just move to the next AuthToken as actual authentication is not done here
                pass
        return user.username

    def hide_oppija_cas_sensitive_data(self, username):
        hetu_regex = '\\d{6}[A+\\-]\\d{3}[0-9A-FHJ-NPR-Y]'
        if username:
            if not isinstance(username, str):
                username = str(username)
            if re.search('suomi\\.fi#{}#{}'.format(hetu_regex, hetu_regex), username):
                return re.compile(hetu_regex).sub('xxxxxxxxxxx', username)
        return username
