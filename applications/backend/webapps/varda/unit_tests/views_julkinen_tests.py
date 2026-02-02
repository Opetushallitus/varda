import json

from django.test import TestCase
from rest_framework import status

from varda.unit_tests.test_utils import SetUpTestClient, assert_status_code


class VardaJulkinenViewSetTests(TestCase):
    fixtures = ["fixture_basics"]

    def test_api_get_koodistot(self):
        client = SetUpTestClient("tester").client()
        resp = client.get("/api/julkinen/v1/koodistot/")
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertGreater(len(json.loads(resp.content)), 0)

    def test_api_get_pulssi(self):
        client = SetUpTestClient("tester2").client()
        resp = client.get("/api/julkinen/v1/pulssi/")
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertGreater(json.loads(resp.content)["organisaatio_count"], 0)
