import datetime
import json

from unittest.mock import patch

import responses

from django.test import TestCase
from rest_framework import status

from varda import misc
from varda.helper_functions import hide_hetu
from varda.misc import is_date_within_timeframe
from varda.models import Henkilo
from varda.unit_tests.test_utils import SetUpTestClient, assert_status_code, assert_validation_error


class MiscTests(TestCase):
    fixtures = ["fixture_basics"]

    @responses.activate
    def test_hetu_crypting(self):
        hetu = "210669-043K"
        henkilo_id = self._create_henkilo(hetu)
        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))

        new_hetu = "111299-913S"
        new_henkilo_id = self._create_henkilo(new_hetu)
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        misc.decrypt_henkilotunnus(hetu_encrypted)
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        misc.decrypt_henkilotunnus(new_hetu_encrypted)

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        new_key_only_hetu = "111299-9255"
        new_key_only_henkilo_id = self._create_henkilo(new_key_only_hetu)
        new_key_only_hetu_encrypted = Henkilo.objects.get(id=new_key_only_henkilo_id).henkilotunnus
        self.assertEqual(new_key_only_hetu, misc.decrypt_henkilotunnus(new_key_only_hetu_encrypted))

    def _create_henkilo(self, hetu):
        responses.add(
            responses.POST,
            "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/",
            json="1.2.987654321",
            status=status.HTTP_201_CREATED,
        )
        henkilo = {"henkilotunnus": hetu, "etunimet": "Pauliina", "kutsumanimi": "Pauliina", "sukunimi": "Virtanen"}
        client = SetUpTestClient("tester").client()
        resp = client.post("/api/v1/henkilot/", henkilo)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.json()["id"]

    def test_decrypt_henkilotunnus_queries(self):
        encrypted_henkilotunnus = misc.encrypt_string("120386-909D")
        # Successful decryption must not query the database, henkilotunnus column has no index
        with self.assertNumQueries(0):
            self.assertEqual(misc.decrypt_henkilotunnus(encrypted_henkilotunnus), "120386-909D")

        henkilo = Henkilo.objects.exclude(henkilotunnus="").first()
        Henkilo.objects.filter(id=henkilo.id).update(henkilotunnus="invalid-token")
        # varda.misc logger is created before the test runner disables existing loggers
        with (
            patch.object(misc.logger, "disabled", False),
            self.assertLogs("varda.misc", level="ERROR") as logs,
            self.assertRaises(misc.CustomServerErrorException),
        ):
            misc.decrypt_henkilotunnus("invalid-token")
        self.assertIn(f"Henkilo.id: {henkilo.id}", logs.output[0])
        with self.assertNumQueries(0):
            self.assertIsNone(misc.decrypt_henkilotunnus("invalid-token", raise_error=False))

    def test_hide_hetu(self):
        # Century signs before 2023 (+, -, A) and since 2023 (B-F, U-Y)
        hetu_list = [
            "010181+900C",
            "210669-043K",
            "010594Y9021",
            "020594X903P",
            "030594W903B",
            "040594V9030",
            "050594U903M",
            "010516A900Y",
            "010516B903X",
            "010516C903Y",
            "010516D903A",
            "010516E903B",
            "010516F903C",
        ]
        for hetu in hetu_list:
            with self.subTest(hetu=hetu):
                masked = hide_hetu(f"/henkilo/{hetu}/?x=1")
                self.assertNotIn(hetu, masked)
                self.assertEqual(masked, f"/henkilo/DDMMYY{hetu[6:]}/?x=1")
                self.assertEqual(hide_hetu(hetu, hide_date=False), f"{hetu[:7]}XXXX")

        # Several hetus in one string, non-string input and values that are not hetus
        self.assertEqual(hide_hetu("210669-043K, 010594Y9021"), "DDMMYY-043K, DDMMYYY9021")
        self.assertEqual(hide_hetu(b"210669-043K"), "b'DDMMYY-043K'")
        self.assertIsNone(hide_hetu(None))
        self.assertEqual(hide_hetu("1.2.246.562.24.47279942650"), "1.2.246.562.24.47279942650")
        self.assertEqual(hide_hetu("010594G9021"), "010594G9021")

    def test_request_path_type(self):
        request_path_string = "/api/v1/toimipaikat/55/"
        request_path_bytes = b"/api/v1/toimipaikat/55/"
        request_path_empty_string = ""
        request_path_empty_byte = b""

        url_string, params_string = misc.path_parse(request_path_string)
        url_bytes, params_bytes = misc.path_parse(request_path_bytes)
        url_empty_string, params_empty_string = misc.path_parse(request_path_empty_string)
        url_empty_byte, params_empty_byte = misc.path_parse(request_path_empty_byte)

        self.assertEqual(url_string, request_path_string)
        self.assertEqual(url_bytes, request_path_string)
        self.assertEqual(url_empty_string, "")
        self.assertEqual(url_empty_byte, "")

    def test_dy011_error(self):
        client = SetUpTestClient("tester10").client()

        test_cases = [
            (
                "",
                "Invalid JSON payload. Expected a dictionary, but got str.",
            ),
            (
                1,
                "Invalid JSON payload. Expected a dictionary, but got int.",
            ),
            (
                1.1,
                "Invalid JSON payload. Expected a dictionary, but got float.",
            ),
            (
                False,
                "Invalid JSON payload. Expected a dictionary, but got bool.",
            ),
            (
                [""],
                "Invalid JSON payload. Expected a dictionary, but got list.",
            ),
        ]
        for test_case in test_cases:
            resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(test_case[0]), content_type="application/json")
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
            assert_validation_error(resp, "errors", "DY011", test_case[1])

    # Test is_date_within_timeframe
    def test_within_timeframe(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2024, 12, 31)
        self.assertTrue(is_date_within_timeframe(today, start_date, end_date))

    def test_outside_timeframe(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2024, 2, 1)
        self.assertFalse(is_date_within_timeframe(today, start_date, end_date))

    def test_on_timeframe(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(2024, 2, 2)
        end_date = datetime.date(2024, 2, 2)
        self.assertTrue(is_date_within_timeframe(today, start_date, end_date))

    def test_within_timeframe_span_across_two_years(self):
        today = datetime.date(2024, 12, 15)
        start_date = datetime.date(2024, 12, 1)
        end_date = datetime.date(2025, 1, 31)
        self.assertTrue(is_date_within_timeframe(today, start_date, end_date))
