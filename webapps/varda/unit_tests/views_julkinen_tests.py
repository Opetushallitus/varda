import json

from django.test import TestCase

from varda.unit_tests.test_utils import SetUpTestClient, assert_status_code


class VardaJulkinenViewSetTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_api_get_koodistot(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/julkinen/koodistot/v1/')
        assert_status_code(resp, 200)
        self.assertEqual(len(json.loads(resp.content)), 13)
