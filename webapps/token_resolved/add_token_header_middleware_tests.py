from django.contrib.auth.models import User
from django.test import TestCase

from requests import Response

from token_resolved.middleware import AddTokenHeaderMiddleware


class TestAddTokenHeaderMiddleware(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def setUp(self):
        response = Response()
        self.middleware = AddTokenHeaderMiddleware(response)

    def test_hide_oppija_cas_sensitive_data(self):
        username = 'suomi.fi#123456-023X#123456A023X'
        username = self.middleware.hide_oppija_cas_sensitive_data(username)
        self.assertEqual('suomi.fi#xxxxxxxxxxx#xxxxxxxxxxx', username)

    def test_do_not_hide_nil_username(self):
        username = None
        username = self.middleware.hide_oppija_cas_sensitive_data(username)
        self.assertEqual(None, username)

    def test_do_not_hide_empty_username(self):
        username = ''
        username = self.middleware.hide_oppija_cas_sensitive_data(username)
        self.assertEqual('', username)

    def test_do_not_hide_similar_username(self):
        username = 'suomi.fi#eihetu#eihetu'
        username = self.middleware.hide_oppija_cas_sensitive_data(username)
        self.assertEqual('suomi.fi#eihetu#eihetu', username)

    def test_do_not_hide_regular_username(self):
        username = 'username123'
        username = self.middleware.hide_oppija_cas_sensitive_data(username)
        self.assertEqual('username123', username)

    def test_binary_username(self):
        username = User()
        username.username = 'username'
        username = self.middleware.hide_oppija_cas_sensitive_data(username)
        self.assertEqual('username', username)
